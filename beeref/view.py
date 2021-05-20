# This file is part of BeeRef.
#
# BeeRef is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BeeRef is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BeeRef.  If not, see <https://www.gnu.org/licenses/>.

import logging
import os

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt

from beeref.actions import ActionsMixin
from beeref import commands
from beeref.config import CommandlineArgs, BeeSettings
from beeref import constants
from beeref import fileio
from beeref import gui
from beeref.items import BeePixmapItem
from beeref.scene import BeeGraphicsScene


commandline_args = CommandlineArgs()
logger = logging.getLogger(__name__)


class BeeGraphicsView(QtWidgets.QGraphicsView, ActionsMixin):

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.settings = BeeSettings()
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(60, 60, 60)))

        self.undo_stack = QtGui.QUndoStack(self)
        self.undo_stack.setUndoLimit(100)
        self.undo_stack.canRedoChanged.connect(self.on_can_redo_changed)
        self.undo_stack.canUndoChanged.connect(self.on_can_undo_changed)
        self.undo_stack.cleanChanged.connect(self.on_undo_clean_changed)

        self.scene = BeeGraphicsScene(self.undo_stack)
        self.filename = None

        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setAcceptDrops(True)

        self.previous_transform = None
        self.pan_active = False
        self.zoom_active = False
        self.scene.changed.connect(self.on_scene_changed)
        self.scene.selectionChanged.connect(self.on_selection_changed)

        self.setScene(self.scene)

        # Context menu and actions
        self.build_menu_and_actions()
        self.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)

        self.welcome_overlay = gui.WelcomeOverlay(self)

        # Load file given via command line
        if commandline_args.filename:
            self.open_from_file(commandline_args.filename)
        self.update_window_title()

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, value):
        self._filename = value
        self.update_window_title()
        if value:
            self.settings.update_recent_files(value)
            self.update_menu_and_actions()

    def update_window_title(self):
        clean = self.undo_stack.isClean()
        if clean and not self.filename:
            title = constants.APPNAME
        else:
            name = os.path.basename(self.filename or '[Untitled]')
            clean = '' if clean else '*'
            title = f'{name}{clean} - {constants.APPNAME}'
        self.parent().setWindowTitle(title)

    def on_scene_changed(self, region):
        if not self.scene.items():
            logger.debug('No items in scene')
            self.setTransform(QtGui.QTransform())
            self.welcome_overlay.show()
        else:
            self.welcome_overlay.hide()
        self.recalc_scene_rect()

    def on_can_redo_changed(self, can_redo):
        self.actiongroup_set_enabled('active_when_can_redo', can_redo)

    def on_can_undo_changed(self, can_undo):
        self.actiongroup_set_enabled('active_when_can_undo', can_undo)

    def on_undo_clean_changed(self, clean):
        self.update_window_title()

    def on_context_menu(self, point):
        self.context_menu.exec(self.mapToGlobal(point))

    def get_supported_image_formats(self, cls):
        formats = map(lambda f: f'*.{f.data().decode()}',
                      cls.supportedImageFormats())
        return ' '.join(formats)

    def get_view_center(self):
        return QtCore.QPoint(round(self.size().width() / 2),
                             round(self.size().height() / 2))

    def clear_scene(self):
        logging.debug('Clearing scene...')
        self.scene.clear()
        self.undo_stack.clear()
        self.filename = None
        self.setTransform(QtGui.QTransform())

    def reset_previous_transform(self, toggle_item=None):
        if (self.previous_transform
                and self.previous_transform['toggle_item'] != toggle_item):
            self.previous_transform = None

    def fit_rect(self, rect, toggle_item=None):
        if toggle_item and self.previous_transform:
            logger.debug('Fit view: Reset to previous')
            self.setTransform(self.previous_transform['transform'])
            self.centerOn(self.previous_transform['center'])
            self.previous_transform = None
            return
        if toggle_item:
            self.previous_transform = {
                'toggle_item': toggle_item,
                'transform': QtGui.QTransform(self.transform()),
                'center': self.mapToScene(self.get_view_center()),
            }
        else:
            self.previous_transform = None

        logger.debug(f'Fit view: {rect}')
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        self.recalc_scene_rect()
        # It seems to be more reliable when we fit a second time
        # Sometimes a changing scene rect can mess up the fitting
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def on_action_fit_scene(self):
        self.fit_rect(self.scene.itemsBoundingRect())

    def on_action_fit_selection(self):
        self.fit_rect(self.scene.itemsBoundingRect(selection_only=True))

    def on_action_fullscreen(self, checked):
        if checked:
            self.parent().showFullScreen()
        else:
            self.parent().showNormal()

    def on_action_always_on_top(self, checked):
        self.parent().setWindowFlag(
            Qt.WindowType.WindowStaysOnTopHint, on=checked)
        self.parent().destroy()
        self.parent().create()
        self.parent().show()

    def on_action_show_scrollbars(self, checked):
        if checked:
            self.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def on_action_show_menubar(self, checked):
        if checked:
            self.parent().setMenuBar(self.create_menubar())
        else:
            self.parent().setMenuBar(None)

    def on_action_undo(self):
        logger.debug('Undo: %s' % self.undo_stack.undoText())
        self.undo_stack.undo()

    def on_action_redo(self):
        logger.debug('Redo: %s' % self.undo_stack.redoText())
        self.undo_stack.redo()

    def on_action_select_all(self):
        self.scene.set_selected_all_items(True)

    def on_action_deselect_all(self):
        self.scene.set_selected_all_items(False)

    def on_action_delete_items(self):
        logger.debug('Deleting items...')
        self.undo_stack.push(
            commands.DeleteItems(
                self.scene, self.scene.selectedItems(user_only=True)))

    def on_action_cut(self):
        logger.debug('Cutting items...')
        self.on_action_copy()
        self.undo_stack.push(
            commands.DeleteItems(
                self.scene, self.scene.selectedItems(user_only=True)))

    def on_action_normalize_height(self):
        self.scene.normalize_height()

    def on_action_normalize_width(self):
        self.scene.normalize_width()

    def on_action_normalize_size(self):
        self.scene.normalize_size()

    def on_action_arrange_horizontal(self):
        self.scene.arrange()

    def on_action_arrange_vertical(self):
        self.scene.arrange(vertical=True)

    def on_action_arrange_optimal(self):
        self.scene.arrange_optimal()

    def on_action_flip_horizontally(self):
        self.scene.flip_items(vertical=False)

    def on_action_flip_vertically(self):
        self.scene.flip_items(vertical=True)

    def on_action_reset_scale(self):
        self.undo_stack.push(commands.ResetScale(
            self.scene.selectedItems(user_only=True)))

    def on_action_reset_rotation(self):
        self.undo_stack.push(commands.ResetRotation(
            self.scene.selectedItems(user_only=True)))

    def on_action_reset_flip(self):
        self.undo_stack.push(commands.ResetFlip(
            self.scene.selectedItems(user_only=True)))

    def on_action_reset_transforms(self):
        self.undo_stack.push(commands.ResetTransforms(
            self.scene.selectedItems(user_only=True)))

    def on_items_loaded(self, value):
        logger.debug('On items loded: add queued images')
        self.scene.add_queued_items()

    def on_loading_finished(self, filename, errors):
        if filename:
            self.filename = filename
        if errors:
            QtWidgets.QMessageBox.warning(
                self,
                'Problem loading file',
                ('<p>Problem loading file %s</p>'
                 '<p>Not accessible or not a proper bee file</p>') % filename)
        else:
            self.scene.add_queued_items()
            self.on_action_fit_scene()
        self.progress.deleteLater()

    def open_from_file(self, filename):
        logger.info(f'Opening file {filename}')
        self.clear_scene()
        self.worker = fileio.ThreadedIO(
            fileio.load_bee, filename, self.scene)
        self.worker.progress.connect(self.on_items_loaded)
        self.worker.finished.connect(self.on_loading_finished)
        self.progress = gui.BeeProgressDialog(
            'Loading %s' % filename,
            worker=self.worker,
            parent=self)
        self.worker.start()

    def on_action_open(self):
        filename, f = QtWidgets.QFileDialog.getOpenFileName(
            parent=self,
            caption='Open file',
            filter=f'{constants.APPNAME} File (*.bee)')
        if filename:
            self.open_from_file(filename)
            self.filename = filename

    def on_saving_finished(self, filename, errors):
        if filename:
            self.filename = filename
            self.undo_stack.setClean()
        else:
            QtWidgets.QMessageBox.warning(
                self,
                'Problem saving file',
                ('<p>Problem saving file %s</p>'
                 '<p>File/directory not accessible</p>') % filename)
        self.progress.deleteLater()

    def do_save(self, filename, create_new):
        if not filename.endswith('.bee'):
            filename = f'{filename}.bee'
        self.worker = fileio.ThreadedIO(
            fileio.save_bee, filename, self.scene, create_new=create_new)
        self.worker.finished.connect(self.on_saving_finished)
        self.progress = gui.BeeProgressDialog(
            'Saving %s' % filename,
            worker=self.worker,
            parent=self)
        self.worker.start()

    def on_action_save_as(self):
        filename, f = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption='Save file',
            filter=f'{constants.APPNAME} File (*.bee)')
        if filename:
            self.do_save(filename, create_new=True)

    def on_action_save(self):
        if not self.filename:
            self.on_action_save_as()
        else:
            self.do_save(self.filename, create_new=False)

    def on_action_quit(self):
        logger.info('User quit. Exiting...')
        self.app.quit()

    def on_action_help(self):
        gui.HelpDialog(self)

    def on_action_about(self):
        QtWidgets.QMessageBox.about(
            self,
            f'About {constants.APPNAME}',
            (f'<h2>{constants.APPNAME} {constants.VERSION}</h2>'
             f'<p>{constants.APPNAME_FULL}</p>'
             f'<p>{constants.COPYRIGHT}</p>'
             f'<p><a href="{constants.WEBSITE}">'
             f'Visit the {constants.APPNAME} website</a></p>'))

    def on_action_debuglog(self):
        gui.DebugLogDialog(self)

    def on_insert_images_finished(self, filename, errors):
        logger.debug('Insert images finished')
        if errors:
            errornames = [
                f'<li>{fn}</li>' for fn in errors]
            errornames = '<ul>%s</ul>' % '\n'.join(errornames)
            msg = ('{errors} image(s) out of {total} '
                   'could not be opened:'.format(
                       errors=len(errors), total=len(errors)))
            QtWidgets.QMessageBox.warning(
                self,
                'Problem loading images',
                msg + errornames)
        self.scene.add_queued_items()
        self.scene.arrange_optimal()
        self.undo_stack.endMacro()
        self.progress.deleteLater()

    def do_insert_images(self, filenames, pos=None):
        if not pos:
            pos = self.get_view_center()
        self.scene.clearSelection()
        self.undo_stack.beginMacro('Insert Images')
        self.worker = fileio.ThreadedIO(
            fileio.load_images,
            filenames,
            self.mapToScene(pos),
            self.scene)
        self.worker.progress.connect(self.on_items_loaded)
        self.worker.finished.connect(self.on_insert_images_finished)
        self.progress = gui.BeeProgressDialog(
            'Loading images',
            worker=self.worker,
            parent=self)
        self.worker.start()

    def on_action_insert_images(self):
        formats = self.get_supported_image_formats(QtGui.QImageReader)
        filenames, f = QtWidgets.QFileDialog.getOpenFileNames(
            parent=self,
            caption='Select one ore more images to open',
            filter=f'Images ({formats})')
        self.do_insert_images(filenames)

    def on_action_copy(self):
        logger.debug('Copying to clipboard...')
        clipboard = QtWidgets.QApplication.clipboard()
        items = self.scene.selectedItems(user_only=True)

        # At the moment, we can only copy one image to the global
        # clipboard. (Later, we might create an image of the whole
        # selection for external copying.)
        clipboard.setPixmap(items[0].pixmap())

        # However, we can copy all items to the internal clipboard:
        self.scene.copy_selection_to_internal_clipboard()

        # We set a marker for ourselves in the global clipboard so
        # that we know to look up the internal clipboard when pasting:
        clipboard.mimeData().setData(
            'beeref/items', QtCore.QByteArray.number(len(items)))

    def on_action_paste(self):
        logger.debug('Pasting from clipboard...')
        clipboard = QtWidgets.QApplication.clipboard()
        pos = self.mapToScene(self.mapFromGlobal(self.cursor().pos()))

        # See if we need to look up the internal clipboard:
        data = clipboard.mimeData().data('beeref/items')
        logger.debug(f'Custom data in clipboard: {data}')
        if data:
            self.scene.paste_from_internal_clipboard(pos)
            return

        img = clipboard.image()
        if not img.isNull():
            item = BeePixmapItem(img)
            self.undo_stack.push(commands.InsertItems(self.scene, [item], pos))
            return
        logger.info('No image data in clipboard')

    def on_selection_changed(self):
        logger.debug('Currently selected items: %s',
                     len(self.scene.selectedItems(user_only=True)))
        self.actiongroup_set_enabled('active_when_selection',
                                     self.scene.has_selection())
        self.viewport().repaint()

    def recalc_scene_rect(self):
        """Resize the scene rectangle so that it is always one view width
        wider than all items' bounding box at each side and one view
        width higher on top and bottom. This gives the impression of
        an infinite canvas."""

        logger.debug('Recalculating scene rectangle...')
        try:
            topleft = self.mapFromScene(
                self.scene.itemsBoundingRect().topLeft())
            topleft = self.mapToScene(QtCore.QPoint(
                topleft.x() - self.size().width(),
                topleft.y() - self.size().height()))
            bottomright = self.mapFromScene(
                self.scene.itemsBoundingRect().bottomRight())
            bottomright = self.mapToScene(QtCore.QPoint(
                bottomright.x() + self.size().width(),
                bottomright.y() + self.size().height()))
            self.setSceneRect(QtCore.QRectF(topleft, bottomright))
        except OverflowError:
            logger.info('Maximum scene size reached')
        logger.debug('Done recalculating scene rectangle')

    def get_zoom_size(self, func):
        """Calculates the size of all items' bounding box in the view's
        coordinates.

        This helps ensure that we never zoom out too much (scene
        becomes so tiny that items become invisible) or zoom in too
        much (causing overflow errors).

        :param func: Function which takes the width and height as
        arguments and turns it into a number, for ex. ``min`` or ``max``.
        """

        topleft = self.mapFromScene(
            self.scene.itemsBoundingRect().topLeft())
        bottomright = self.mapFromScene(
            self.scene.itemsBoundingRect().bottomRight())
        return func(bottomright.x() - topleft.x(),
                    bottomright.y() - topleft.y())

    def scale(self, *args, **kwargs):
        super().scale(*args, **kwargs)
        self.scene.on_view_scale_change()
        self.recalc_scene_rect()

    def get_scale(self):
        return self.transform().m11()

    def pan(self, delta):
        if not self.scene.items():
            logger.debug('No items in scene; ignore pan')
            return

        hscroll = self.horizontalScrollBar()
        hscroll.setValue(hscroll.value() + delta.x())
        vscroll = self.verticalScrollBar()
        vscroll.setValue(vscroll.value() + delta.y())

    def zoom(self, delta, anchor):
        if not self.scene.items():
            logger.debug('No items in scene; ignore zoom')
            return

        # We caculate where the anchor is before and after the zoom
        # and then move the view accordingly to keep the anchor fixed
        # We can't use QGraphicsView's AnchorUnderMouse since it
        # uses the current cursor position while we need the inital mouse
        # press position for zooming with Ctrl + Middle Drag
        anchor = QtCore.QPoint(round(anchor.x()),
                               round(anchor.y()))
        ref_point = self.mapToScene(anchor)
        if delta == 0:
            return
        factor = 1 + abs(delta / 1000)
        if delta > 0:
            if self.get_zoom_size(max) < 10000000:
                self.scale(factor, factor)
            else:
                logger.debug('Maximum zoom size reached')
                return
        else:
            if self.get_zoom_size(min) > 50:
                self.scale(1/factor, 1/factor)
            else:
                logger.debug('Minimum zoom size reached')
                return

        self.pan(self.mapFromScene(ref_point) - anchor)
        self.reset_previous_transform()

    def wheelEvent(self, event):
        self.zoom(event.angleDelta().y(), event.position())
        event.accept()

    def mousePressEvent(self, event):
        if (event.button() == Qt.MouseButton.MiddleButton
                and event.modifiers() == Qt.KeyboardModifier.ControlModifier):
            self.zoom_active = True
            self.event_start = event.position()
            self.event_anchor = event.position()
            event.accept()
            return

        if (event.button() == Qt.MouseButton.MiddleButton
            or (event.button() == Qt.MouseButton.LeftButton
                and event.modifiers() == Qt.KeyboardModifier.AltModifier)):
            self.pan_active = True
            self.event_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.pan_active:
            self.reset_previous_transform()
            pos = event.position()
            self.pan(self.event_start - pos)
            self.event_start = pos
            event.accept()
            return

        if self.zoom_active:
            self.reset_previous_transform()
            pos = event.position()
            delta = (self.event_start - pos).y()
            self.event_start = pos
            self.zoom(delta * 20, self.event_anchor)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.pan_active:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.pan_active = False
            event.accept()
            return
        if self.zoom_active:
            self.zoom_active = False
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.recalc_scene_rect()
        self.welcome_overlay.resize(self.size())

    def dragEnterEvent(self, event):
        mimedata = event.mimeData()
        logger.debug(f'Drag enter event: {mimedata.formats()}')
        if mimedata.hasUrls():
            event.acceptProposedAction()
        elif mimedata.hasImage():
            event.acceptProposedAction()
        else:
            logger.info('Attempted drop not an image')

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        mimedata = event.mimeData()
        logger.debug(f'Handling file drop: {mimedata.formats()}')
        pos = QtCore.QPoint(round(event.position().x()),
                            round(event.position().y()))
        if mimedata.hasUrls():
            self.do_insert_images(mimedata.urls(), pos)
        elif mimedata.hasImage():
            img = QtGui.QImage(mimedata.imageData())
            item = BeePixmapItem(img)
            pos = self.mapToScene(pos)
            self.undo_stack.push(commands.InsertItems(self.scene, [item], pos))
        logger.info('Drop not an image')
