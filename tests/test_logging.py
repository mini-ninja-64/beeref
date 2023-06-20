import logging
import os.path
from types import SimpleNamespace
from unittest.mock import patch

from PyQt6 import QtCore

from dreamboard.dreamb_logger import (
    DreambLogger,
    DreambRotatingFileHandler,
    qt_message_handler,
)


def test_sets_new_loglevel():
    assert logging.getLevelName(5) == 'TRACE'


@patch('dreamboard.dreamb_logger.DreambLogger.log')
def test_dreamblogger(log_mock):
    logger = DreambLogger('mylogger', logging.TRACE)
    logger.trace('blah: %s', 'spam', extra={'foo': 'bar'})
    log_mock.assert_called_once_with(
        logging.TRACE, 'blah: %s', 'spam', extra={'foo': 'bar'})


def test_rotating_file_handler_creates_new_dir(tmpdir):
    logfile = os.path.join(tmpdir, 'foo', 'bar.log')
    handler = DreambRotatingFileHandler(logfile)
    handler.emit(logging.LogRecord(
        'foo', logging.INFO, 'bar', 66, 'baz', [], None))
    handler.close()
    assert os.path.exists(logfile)


def testrotating_file_handler_uses_existing_dir(tmpdir):
    logfile = os.path.join(tmpdir, 'bar.log')
    handler = DreambRotatingFileHandler(logfile)
    handler.emit(logging.LogRecord(
        'foo', logging.INFO, 'bar', 66, 'baz', [], None))
    handler.close()
    assert os.path.exists(logfile)


@patch('dreamboard.dreamb_logger.qtlogger.info')
def test_qt_message_handler_without(log_mock, qapp):
    qt_message_handler(QtCore.QtMsgType.QtInfoMsg, None, 'foo')
    log_mock.assert_called_once_with('foo')


@patch('dreamboard.dreamb_logger.qtlogger.warning')
def test_qt_message_handler_with_context(log_mock, qapp):
    ctx = SimpleNamespace(file='bla.txt', line='1', function='myfunc')
    qt_message_handler(QtCore.QtMsgType.QtWarningMsg, ctx, 'foo')
    log_mock.assert_called_once_with('foo: File bla.txt, line 1, in myfunc')
