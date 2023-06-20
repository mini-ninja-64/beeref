import os.path
import tempfile
from unittest.mock import MagicMock, patch

from PyQt6 import QtCore

from dreamboard import fileio
from dreamboard import commands
from ..utils import queue2list


@patch('dreamboard.fileio.sql.SQLiteIO.write')
def test_save_dreamb_create_new_false(write_mock):
    with tempfile.TemporaryDirectory() as dirname:
        fname = os.path.join(dirname, 'test.dreamb')
        fileio.save_dreamb(fname, 'myscene', create_new=False)
        write_mock.assert_called_once()


@patch('dreamboard.fileio.sql.SQLiteIO.read')
def test_read_dreamb(read_mock):
    with tempfile.TemporaryDirectory() as dirname:
        fname = os.path.join(dirname, 'test.dreamb')
        fileio.load_dreamb(fname, 'myscene')
        read_mock.assert_called_once()


def test_load_images_loads(view, imgfilename3x3):
    view.scene.undo_stack = MagicMock()
    worker = MagicMock(canceled=False)
    fileio.load_images([imgfilename3x3],
                       QtCore.QPointF(5, 6), view.scene, worker)
    worker.begin_processing.emit.assert_called_once_with(1)
    worker.progress.emit.assert_called_once_with(0)
    worker.finished.emit.assert_called_once_with('', [])
    itemdata = queue2list(view.scene.items_to_add)
    assert len(itemdata) == 1
    item = itemdata[0][0]['item']
    args = view.scene.undo_stack.push.call_args_list[0][0]
    cmd = args[0]
    assert isinstance(cmd, commands.InsertItems)
    assert cmd.items == [item]
    assert cmd.scene == view.scene
    assert cmd.ignore_first_redo is True
    assert item.pos() == QtCore.QPointF(3.5, 4.5)


def test_load_images_canceled(view, imgfilename3x3):
    view.scene.undo_stack = MagicMock()
    worker = MagicMock(canceled=True)
    fileio.load_images([imgfilename3x3, imgfilename3x3],
                       QtCore.QPointF(5, 6), view.scene, worker)
    worker.begin_processing.emit.assert_called_once_with(2)
    worker.progress.emit.assert_called_once_with(0)
    worker.finished.emit.assert_called_once_with('', [])
    itemdata = queue2list(view.scene.items_to_add)
    assert len(itemdata) == 1
    item = itemdata[0][0]['item']
    args = view.scene.undo_stack.push.call_args_list[0][0]
    cmd = args[0]
    assert isinstance(cmd, commands.InsertItems)
    assert cmd.items == [item]
    assert cmd.scene == view.scene
    assert cmd.ignore_first_redo is True
    assert item.pos() == QtCore.QPointF(3.5, 4.5)


def test_load_images_error(view, imgfilename3x3):
    view.scene.undo_stack = MagicMock()
    worker = MagicMock(canceled=False)
    fileio.load_images(['foo.jpg', imgfilename3x3],
                       QtCore.QPointF(5, 6), view.scene, worker)
    worker.begin_processing.emit.assert_called_once_with(2)
    worker.progress.emit.assert_any_call(0)
    worker.progress.emit.assert_any_call(1)
    worker.finished.emit.assert_called_once_with('', ['foo.jpg'])
    itemdata = queue2list(view.scene.items_to_add)
    assert len(itemdata) == 1
    item = itemdata[0][0]['item']
    args = view.scene.undo_stack.push.call_args_list[0][0]
    cmd = args[0]
    assert isinstance(cmd, commands.InsertItems)
    assert cmd.items == [item]
    assert cmd.scene == view.scene
    assert cmd.ignore_first_redo is True
    assert item.pos() == QtCore.QPointF(3.5, 4.5)
