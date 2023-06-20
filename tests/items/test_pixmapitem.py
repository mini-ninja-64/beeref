import pytest
from unittest.mock import patch, MagicMock

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt

from dreamboard.items import DreambPixmapItem, item_registry


def test_in_item_registry():
    assert item_registry['pixmap'] == DreambPixmapItem


@patch('dreamboard.selection.SelectableMixin.init_selectable')
def test_init(selectable_mock, qapp, imgfilename3x3):
    item = DreambPixmapItem(QtGui.QImage(imgfilename3x3), imgfilename3x3)
    assert item.save_id is None
    assert item.width == 3
    assert item.height == 3
    assert item.scale() == 1
    assert item.filename == imgfilename3x3
    assert item.crop == QtCore.QRectF(0, 0, 3, 3)
    assert item.is_croppable is True
    assert item.crop_mode is False
    selectable_mock.assert_called_once()


def test_set_pos_center(qapp, item):
    with patch.object(item, 'bounding_rect_unselected',
                      return_value=QtCore.QRectF(0, 0, 200, 100)):
        item.set_pos_center(QtCore.QPointF(0, 0))
        assert item.pos().x() == -100
        assert item.pos().y() == -50


def test_set_pos_center_when_scaled(qapp, item):
    item.setScale(2)
    with patch.object(item, 'bounding_rect_unselected',
                      return_value=QtCore.QRectF(0, 0, 200, 100)):
        item.set_pos_center(QtCore.QPointF(0, 0))
        assert item.pos().x() == -200
        assert item.pos().y() == -100


def test_set_pos_center_when_rotated(qapp, item):
    item.setRotation(90)
    with patch.object(item, 'bounding_rect_unselected',
                      return_value=QtCore.QRectF(0, 0, 200, 100)):
        item.set_pos_center(QtCore.QPointF(0, 0))
        assert item.pos().x() == 50
        assert item.pos().y() == -100


def test_set_crop(qapp, item):
    item.update = MagicMock()
    item.prepareGeometryChange = MagicMock()
    item.crop = QtCore.QRectF(10, 20, 30, 40)
    item.update.assert_called_once_with()
    item.prepareGeometryChange.assert_called_once_with()


def test_bounding_rect_unselected(qapp, imgfilename3x3):
    item = DreambPixmapItem(QtGui.QImage(imgfilename3x3))
    item.crop = QtCore.QRectF(1, 1, 2, 2)
    assert item.bounding_rect_unselected() == QtCore.QRectF(1, 1, 2, 2)


def test_bounding_rect_unselected_in_crop_mode(qapp, imgfilename3x3):
    item = DreambPixmapItem(QtGui.QImage(imgfilename3x3))
    item.crop = QtCore.QRectF(1, 1, 2, 2)
    item.crop_mode = True
    assert item.bounding_rect_unselected() == QtCore.QRectF(-0.5, -0.5, 4, 4)


def test_get_extra_save_data(item):
    item.filename = 'foobar.png'
    item.crop = QtCore.QRectF(10, 20, 30, 40)
    assert item.get_extra_save_data() == {
        'filename': 'foobar.png',
        'crop': [10, 20, 30, 40],
    }


def test_pixmap_to_bytes(qapp, imgfilename3x3):
    item = DreambPixmapItem(QtGui.QImage(imgfilename3x3))
    assert item.pixmap_to_bytes().startswith(b'\x89PNG')


def test_pixmap_from_bytes(qapp, item, imgfilename3x3):
    with open(imgfilename3x3, 'rb') as f:
        imgdata = f.read()
    item.pixmap_from_bytes(imgdata)
    assert item.width == 3
    assert item.height == 3
    assert item.crop == QtCore.QRectF(0, 0, 3, 3)


def test_has_selection_outline_when_not_selected(view, item):
    view.scene.addItem(item)
    item.setSelected(False)
    item.has_selection_outline() is False


def test_has_selection_outline_when_selected(view, item):
    view.scene.addItem(item)
    item.setSelected(True)
    item.has_selection_outline() is True


def test_has_selection_handles_when_not_selected(view, item):
    view.scene.addItem(item)
    item.setSelected(False)
    item2 = DreambPixmapItem(QtGui.QImage())
    view.scene.addItem(item2)
    item2.setSelected(False)
    item.has_selection_handles() is False


def test_has_selection_handles_when_selected_single(view, item):
    view.scene.addItem(item)
    item.setSelected(True)
    item2 = DreambPixmapItem(QtGui.QImage())
    view.scene.addItem(item2)
    item2.setSelected(False)
    item.has_selection_handles() is True


def test_has_selection_handles_when_selected_multi(view, item):
    view.scene.addItem(item)
    item.setSelected(True)
    item2 = DreambPixmapItem(QtGui.QImage())
    view.scene.addItem(item2)
    item2.setSelected(True)
    item.has_selection_handles() is False


def test_selection_action_items(qapp):
    item = DreambPixmapItem(QtGui.QImage())
    assert item.selection_action_items() == [item]


def test_update_from_data(item):
    item.update_from_data(
        save_id=3,
        x=11,
        y=22,
        z=1.2,
        scale=2.5,
        rotation=45,
        flip=-1)
    assert item.save_id == 3
    assert item.pos() == QtCore.QPointF(11, 22)
    assert item.zValue() == 1.2
    assert item.rotation() == 45
    assert item.flip() == -1


def test_update_from_data_keeps_flip(item):
    item.do_flip()
    item.update_from_data(flip=-1)
    assert item.flip() == -1


def test_update_from_data_keeps_unset_values(item):
    item.setScale(3)
    item.update_from_data(rotation=45)
    assert item.scale() == 3
    assert item.flip() == 1


def test_create_from_data(item):
    new_item = DreambPixmapItem.create_from_data(
        item=item, data={'filename': 'foobar.png'})
    assert new_item is item
    assert item.filename == 'foobar.png'


def test_create_from_data_with_crop(item):
    new_item = DreambPixmapItem.create_from_data(
        item=item, data={'filename': 'foobar.png', 'crop': [10, 20, 30, 40]})
    assert new_item is item
    assert item.filename == 'foobar.png'
    assert item.crop == QtCore.QRectF(10, 20, 30, 40)


def test_create_copy(qapp, imgfilename3x3):
    item = DreambPixmapItem(QtGui.QImage(imgfilename3x3), 'foo.png')
    item.setPos(20, 30)
    item.setRotation(33)
    item.do_flip()
    item.setZValue(0.5)
    item.setScale(2.2)
    item.crop = QtCore.QRectF(10, 20, 30, 40)

    copy = item.create_copy()
    assert copy.pixmap_to_bytes() == item.pixmap_to_bytes()
    assert copy.filename == 'foo.png'
    assert copy.pos() == QtCore.QPointF(20, 30)
    assert copy.rotation() == 33
    assert copy.flip() == -1
    assert copy.zValue() == 0.5
    assert copy.scale() == 2.2
    assert copy.crop == QtCore.QRectF(10, 20, 30, 40)


def test_copy_to_clipboard(qapp, imgfilename3x3):
    clipboard = QtWidgets.QApplication.clipboard()
    item = DreambPixmapItem(QtGui.QImage(imgfilename3x3), 'foo.png')
    item.copy_to_clipboard(clipboard)
    assert clipboard.pixmap().size() == item.pixmap().size()


def test_reset_crop(qapp, imgfilename3x3):
    item = DreambPixmapItem(QtGui.QImage(imgfilename3x3))
    item.crop = QtCore.QRectF(10, 20, 30, 40)
    item.reset_crop()
    assert item.crop == QtCore.QRectF(0, 0, 3, 3)


def test_crop_handle_topleft(qapp, item):
    item.crop_temp = QtCore.QRectF(100, 200, 300, 400)
    assert item.crop_handle_topleft() == QtCore.QRectF(100, 200, 15, 15)


def test_crop_handle_bottomleft(qapp, item):
    item.crop_temp = QtCore.QRectF(100, 200, 300, 400)
    assert item.crop_handle_bottomleft() == QtCore.QRectF(100, 585, 15, 15)


def test_crop_handle_bottomright(qapp, item):
    item.crop_temp = QtCore.QRectF(100, 200, 300, 400)
    assert item.crop_handle_bottomright() == QtCore.QRectF(385, 585, 15, 15)


def test_crop_handle_topright(qapp, item):
    item.crop_temp = QtCore.QRectF(100, 200, 300, 400)
    assert item.crop_handle_topright() == QtCore.QRectF(385, 200, 15, 15)


@pytest.mark.parametrize('edge,rotation,expected',
                         [('crop_edge_top', 0, 'SizeVerCursor'),
                          ('crop_edge_top', 90, 'SizeHorCursor'),
                          ('crop_edge_top', 180, 'SizeVerCursor'),
                          ('crop_edge_top', 270, 'SizeHorCursor'),
                          ('crop_edge_bottom', 0, 'SizeVerCursor'),
                          ('crop_edge_bottom', 90, 'SizeHorCursor'),
                          ('crop_edge_bottom', 180, 'SizeVerCursor'),
                          ('crop_edge_bottom', 270, 'SizeHorCursor'),
                          ('crop_edge_left', 0, 'SizeHorCursor'),
                          ('crop_edge_left', 90, 'SizeVerCursor'),
                          ('crop_edge_left', 180, 'SizeHorCursor'),
                          ('crop_edge_left', 270, 'SizeVerCursor'),
                          ('crop_edge_right', 0, 'SizeHorCursor'),
                          ('crop_edge_right', 90, 'SizeVerCursor'),
                          ('crop_edge_right', 180, 'SizeHorCursor'),
                          ('crop_edge_right', 270, 'SizeVerCursor')])
def test_get_crop_edge_cursor(edge, rotation, expected, qapp, item):
    item.setRotation(rotation)
    cursor = item.get_crop_edge_cursor(getattr(item, edge))
    assert cursor == getattr(Qt.CursorShape, expected)


def test_paint(qapp, item):
    item.pixmap = MagicMock()
    item.paint_selectable = MagicMock()
    item.crop = QtCore.QRectF(10, 20, 30, 40)
    painter = MagicMock()
    item.paint(painter, None, None)
    item.paint_selectable.assert_called_once()
    painter.drawPixmap.assert_called_with(
        QtCore.QRectF(10, 20, 30, 40),
        item.pixmap(),
        QtCore.QRectF(10, 20, 30, 40))


def test_paint_when_crop_mode(qapp, item):
    item.pixmap = MagicMock()
    item.paint_selectable = MagicMock()
    item.crop = QtCore.QRectF(10, 20, 30, 40)
    item.crop_mode = True
    item.crop_temp = QtCore.QRectF(11, 22, 29, 39)
    painter = MagicMock()
    item.paint(painter, None, None)
    item.paint_selectable.assert_not_called()
    painter.drawPixmap.assert_called_with(0, 0, item.pixmap())


def test_enter_crop_mode(view, item):
    view.scene.addItem(item)
    item.crop = QtCore.QRectF(10, 20, 30, 40)
    item.update = MagicMock()
    item.prepareGeometryChange = MagicMock()
    item.grabKeyboard = MagicMock()

    item.enter_crop_mode()
    assert item.crop_mode is True
    assert item.crop_temp == QtCore.QRectF(10, 20, 30, 40)
    assert item.crop_mode_move is None
    assert item.crop_mode_event_start is None
    item.update.assert_called_once_with()
    item.prepareGeometryChange.assert_called_once_with()
    item.grabKeyboard.assert_called_once_with()
    assert view.scene.crop_item == item


def test_exit_crop_mode_confirmed(view, item):
    view.scene.addItem(item)
    item.update = MagicMock()
    item.prepareGeometryChange = MagicMock()
    item.ungrabKeyboard = MagicMock()
    item.crop = QtCore.QRectF(0, 0, 100, 80)
    item.crop_temp = QtCore.QRectF(10, 20, 30, 40)
    item.crop_mode = True
    item.crop_mode_move = 'topleft'
    item.crop_mode_event_start = QtCore.QRectF(1, 1, 1, 1)

    item.exit_crop_mode(confirm=True)
    item.crop == QtCore.QRectF(10, 20, 30, 40)
    assert item.crop_mode is False
    assert item.crop_temp is None
    assert item.crop_mode_move is None
    assert item.crop_mode_event_start is None
    item.update.assert_called()
    item.prepareGeometryChange.assert_called()
    item.ungrabKeyboard.assert_called_once_with()
    assert view.scene.crop_item is None
    view.scene.undo_stack.canUndo() is True


def test_exit_crop_mode_confirmed_no_change(view, item):
    view.scene.addItem(item)
    item.crop = QtCore.QRectF(0, 0, 100, 80)
    item.crop_temp = QtCore.QRectF(0, 0, 100, 80)
    item.crop_mode = True

    item.exit_crop_mode(confirm=True)
    assert item.crop == QtCore.QRectF(0, 0, 100, 80)
    view.scene.undo_stack.canUndo() is False


def test_exit_crop_mode_not_confirmed(view, item):
    view.scene.addItem(item)
    item.update = MagicMock()
    item.prepareGeometryChange = MagicMock()
    item.ungrabKeyboard = MagicMock()
    item.crop = QtCore.QRectF(0, 0, 100, 80)
    item.crop_temp = QtCore.QRectF(10, 20, 30, 40)
    item.crop_mode = True
    item.crop_mode_move = 'topleft'
    item.crop_mode_event_start = QtCore.QRectF(1, 1, 1, 1)

    item.exit_crop_mode(confirm=False)
    item.crop == QtCore.QRectF(0, 0, 100, 80)
    assert item.crop_mode is False
    assert item.crop_temp is None
    assert item.crop_mode_move is None
    assert item.crop_mode_event_start is None
    item.update.assert_called()
    item.prepareGeometryChange.assert_called()
    item.ungrabKeyboard.assert_called_once_with()
    assert view.scene.crop_item is None
    view.scene.undo_stack.canUndo() is False


@patch('PyQt6.QtWidgets.QGraphicsPixmapItem.keyPressEvent')
def test_key_press_event_return(key_mock, qapp, item):
    item.exit_crop_mode = MagicMock()
    event = MagicMock()
    event.key.return_value = Qt.Key.Key_Return
    item.keyPressEvent(event)
    item.exit_crop_mode.assert_called_once_with(confirm=True)
    key_mock.assert_not_called()


@patch('PyQt6.QtWidgets.QGraphicsPixmapItem.keyPressEvent')
def test_key_press_event_escape(key_mock, qapp, item):
    item.exit_crop_mode = MagicMock()
    event = MagicMock()
    event.key.return_value = Qt.Key.Key_Escape
    item.keyPressEvent(event)
    item.exit_crop_mode.assert_called_once_with(confirm=False)
    key_mock.assert_not_called()


@patch('PyQt6.QtWidgets.QGraphicsPixmapItem.keyPressEvent')
def test_key_press_event_other(key_mock, qapp, item):
    item.exit_crop_mode = MagicMock()
    event = MagicMock()
    event.key.return_value = Qt.Key.Key_Space
    item.keyPressEvent(event)
    item.exit_crop_mode.assert_not_called()
    key_mock.assert_called_once_with(event)


@patch('dreamboard.selection.SelectableMixin.hoverMoveEvent')
def test_hover_move_event_when_not_crop_mode(hover_mock, qapp, item):
    item.crop_mode = False
    event = MagicMock()

    item.hoverMoveEvent(event)
    hover_mock.assert_called_once_with(event)


@patch('dreamboard.selection.SelectableMixin.hoverMoveEvent')
def test_hover_move_event_crop_mode_inside_handle(hover_mock, qapp, item):
    item.crop_mode = True
    item.crop_temp = QtCore.QRectF(0, 0, 100, 80)
    event = MagicMock()
    event.pos.return_value = QtCore.QPointF(5, 5)

    item.hoverMoveEvent(event)
    item.cursor() == Qt.CursorShape.SizeFDiagCursor
    hover_mock.assert_not_called()


@patch('dreamboard.selection.SelectableMixin.hoverMoveEvent')
def test_hover_move_event_crop_mode_inside_edge(hover_mock, qapp, item):
    item.crop_mode = True
    item.crop_temp = QtCore.QRectF(0, 0, 100, 80)
    event = MagicMock()
    event.pos.return_value = QtCore.QPointF(5, 40)

    item.hoverMoveEvent(event)
    item.cursor() == Qt.CursorShape.SizeHorCursor
    hover_mock.assert_not_called()


@patch('dreamboard.selection.SelectableMixin.hoverMoveEvent')
def test_hover_move_event_crop_mode_outside_handle(hover_mock, qapp, item):
    item.crop_mode = True
    item.crop_temp = QtCore.QRectF(0, 0, 100, 80)
    item.setCursor(Qt.CursorShape.SizeFDiagCursor)
    event = MagicMock()
    event.pos.return_value = QtCore.QPointF(50, 50)

    item.hoverMoveEvent(event)
    item.cursor() == Qt.CursorShape.ArrowCursor
    hover_mock.assert_not_called()


@patch('dreamboard.selection.SelectableMixin.mousePressEvent')
def test_mouse_press_event_when_not_crop_mode(mouse_mock, qapp, item):
    item.crop_mode = False
    item.crop_mode_move = None
    item.exit_crop_mode = MagicMock()
    event = MagicMock()

    item.mousePressEvent(event)
    assert item.crop_mode_move is None
    item.exit_crop_mode.assert_not_called()
    mouse_mock.assert_called_once_with(event)
    event.accept.assert_not_called()


@patch('dreamboard.selection.SelectableMixin.mousePressEvent')
def test_mouse_press_event_crop_mode_inside_handle(mouse_mock, qapp, item):
    item.crop_mode = True
    item.crop_temp = QtCore.QRectF(0, 0, 100, 80)
    item.crop_mode_move = None
    item.exit_crop_mode = MagicMock()
    event = MagicMock()
    event.pos.return_value = QtCore.QPointF(5, 5)

    item.mousePressEvent(event)
    assert item.crop_mode_move == item.crop_handle_topleft
    assert item.crop_mode_event_start == QtCore.QPointF(5, 5)
    item.exit_crop_mode.assert_not_called()
    mouse_mock.assert_not_called()
    event.accept.assert_called_once_with()


@patch('dreamboard.selection.SelectableMixin.mousePressEvent')
def test_mouse_press_event_crop_mode_inside_edge(mouse_mock, qapp, item):
    item.crop_mode = True
    item.crop_temp = QtCore.QRectF(0, 0, 100, 80)
    item.crop_mode_move = None
    item.exit_crop_mode = MagicMock()
    event = MagicMock()
    event.pos.return_value = QtCore.QPointF(5, 40)

    item.mousePressEvent(event)
    assert item.crop_mode_move == item.crop_edge_left
    assert item.crop_mode_event_start == QtCore.QPointF(5, 40)
    item.exit_crop_mode.assert_not_called()
    mouse_mock.assert_not_called()
    event.accept.assert_called_once_with()


@patch('dreamboard.selection.SelectableMixin.mousePressEvent')
def test_mouse_press_event_crop_mode_outside_handle_inside_crop(
        mouse_mock, qapp, item):
    item.crop_mode = True
    item.crop_temp = QtCore.QRectF(0, 0, 100, 80)
    item.crop_mode_move = None
    item.exit_crop_mode = MagicMock()
    event = MagicMock()
    event.pos.return_value = QtCore.QPointF(50, 50)

    item.mousePressEvent(event)
    assert item.crop_mode_move is None
    item.exit_crop_mode.assert_called_once_with(confirm=True)
    mouse_mock.assert_not_called()
    event.accept.assert_called_once_with()


@patch('dreamboard.selection.SelectableMixin.mousePressEvent')
def test_mouse_press_event_crop_mode_outside_handle_outside_crop(
        mouse_mock, qapp, item):
    item.crop_mode = True
    item.crop_temp = QtCore.QRectF(0, 0, 100, 80)
    item.crop_mode_move = None
    item.exit_crop_mode = MagicMock()
    event = MagicMock()
    event.pos.return_value = QtCore.QPointF(150, 150)

    item.mousePressEvent(event)
    assert item.crop_mode_move is None
    item.exit_crop_mode.assert_called_once_with(confirm=False)
    mouse_mock.assert_not_called()
    event.accept.assert_called_once_with()


@pytest.mark.parametrize('point,expected',
                         [((45, 56), (45, 56)),
                          ((0, 0), (0, 0)),
                          ((-5, -5), (0, 0)),
                          ((100, 80), (100, 80)),
                          ((105, 85), (100, 80))])
def test_ensure_point_within_pixmap_bounds_inside(point, expected, qapp, item):
    pixmap = MagicMock()
    pixmap.size.return_value = QtCore.QRectF(0, 0, 100, 80)
    item.pixmap = MagicMock(return_value=pixmap)
    result = item.ensure_point_within_pixmap_bounds(QtCore.QPointF(*point))
    assert result == QtCore.QPointF(*expected)


@pytest.mark.parametrize(
    'start,pos,handle,expected',
    [[(10, 10), (5, 5), 'crop_handle_topleft', (5, 15, 35, 45)],
     [(10, 60), (5, 55), 'crop_handle_bottomleft', (5, 20, 35, 35)],
     [(40, 60), (35, 55), 'crop_handle_bottomright', (10, 20, 25, 35)],
     [(40, 10), (35, 5), 'crop_handle_topright', (10, 15, 25, 45)],
     [(25, 10), (20, 5), 'crop_edge_top', (10, 15, 30, 45)],
     [(10, 40), (5, 35), 'crop_edge_left', (5, 20, 35, 40)],
     [(35, 25), (30, 20), 'crop_edge_bottom', (10, 20, 30, 35)],
     [(40, 40), (35, 35), 'crop_edge_right', (10, 20, 25, 40)]])
@patch('dreamboard.selection.SelectableMixin.mouseMoveEvent')
def test_mouse_move_when_crop_mode_inside_handle(
        mouse_mock, start, pos, handle, expected, qapp, item):
    pixmap = MagicMock()
    pixmap.size.return_value = QtCore.QRectF(0, 0, 100, 80)
    item.crop_mode = True
    item.pixmap = MagicMock(return_value=pixmap)
    item.crop_temp = QtCore.QRectF(10, 20, 30, 40)
    item.crop_mode_event_start = QtCore.QPointF(*start)
    item.crop_mode_move = getattr(item, handle)
    event = MagicMock()
    event.pos.return_value = QtCore.QPointF(*pos)

    item.mouseMoveEvent(event)
    assert item.crop_temp == QtCore.QRectF(*expected)
    event.accept.assert_called_once()
    mouse_mock.assert_not_called()


@patch('dreamboard.selection.SelectableMixin.mouseMoveEvent')
def test_mouse_move_when_not_crop_mode(mouse_mock, qapp, item):
    event = MagicMock()
    event.pos.return_value = QtCore.QPointF(30, 50)

    item.mouseMoveEvent(event)
    event.accept.assert_not_called()
    mouse_mock.assert_called_once_with(event)


@patch('dreamboard.selection.SelectableMixin.mouseReleaseEvent')
def test_mouse_release_event_when_crop_mode(mouse_mock, qapp, item):
    event = MagicMock()
    item.crop_mode = True
    item.crop_mode_move = item.crop_handle_topright
    item.crop_mode_event_start = QtCore.QPointF(44, 55)

    item.mouseReleaseEvent(event)
    assert item.crop_mode is True
    assert item.crop_mode_move is None
    assert item.crop_mode_event_start is None
    event.accept.assert_called_once()
    mouse_mock.assert_not_called()


@patch('dreamboard.selection.SelectableMixin.mouseReleaseEvent')
def test_mouse_release_event_when_not_crop_mode(mouse_mock, qapp, item):
    event = MagicMock()
    item.crop_mode = False

    item.mouseReleaseEvent(event)
    assert item.crop_mode is False
    event.accept.assert_not_called()
    mouse_mock.assert_called_once_with(event)
