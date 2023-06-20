import os.path
import tempfile
from unittest.mock import patch

import pytest

from dreamboard.config import CommandlineArgs


def test_command_line_args_singleton():
    assert CommandlineArgs() is CommandlineArgs()
    assert CommandlineArgs()._args is CommandlineArgs()._args
    CommandlineArgs._instance = None


@patch('dreamboard.config.parser.parse_args')
def test_command_line_args_with_check_forces_new_parsing(parse_mock):
    args1 = CommandlineArgs()
    args2 = CommandlineArgs(with_check=True)
    parse_mock.assert_called_once()
    assert args1 is not args2
    CommandlineArgs._instance = None


def test_command_line_args_get():
    args = CommandlineArgs()
    assert args.loglevel == 'INFO'
    CommandlineArgs._instance = None


def test_command_line_args_get_unknown():
    args = CommandlineArgs()
    with pytest.raises(AttributeError):
        args.foo
    CommandlineArgs._instance = None


def test_settings_recent_files_get_empty(settings):
    settings.get_recent_files() == []


def test_settings_recent_files_get_existing_only(settings):
    with tempfile.NamedTemporaryFile() as f:
        settings.update_recent_files('foo.dreamb')
        settings.update_recent_files(f.name)
    settings.get_recent_files(existing_only=True) == [f.name]


def test_settings_recent_files_update(settings):
    settings.update_recent_files('foo.dreamb')
    settings.update_recent_files('bar.dreamb')
    assert settings.get_recent_files() == [
        os.path.abspath('bar.dreamb'),
        os.path.abspath('foo.dreamb')]


def test_settings_recent_files_update_existing(settings):
    settings.update_recent_files('foo.dreamb')
    settings.update_recent_files('bar.dreamb')
    settings.update_recent_files('foo.dreamb')
    assert settings.get_recent_files() == [
        os.path.abspath('foo.dreamb'),
        os.path.abspath('bar.dreamb')]


def test_settings_recent_files_update_respects_max_num(settings):
    for i in range(15):
        settings.update_recent_files(f'{i}.dreamb')

    recent = settings.get_recent_files()
    assert len(recent) == 10
    assert recent[0] == os.path.abspath('14.dreamb')
    assert recent[-1] == os.path.abspath('5.dreamb')


def test_keyboardsettings_set_shortcuts(kbsettings):
    kbsettings.set_shortcuts('Actions', 'foo', ['Ctrl+F'])
    assert kbsettings.get_shortcuts('Actions', 'foo') == ['Ctrl+F']


def test_keyboardsettings_set_shortcuts_multiple(kbsettings):
    kbsettings.set_shortcuts('Actions', 'foo', ['Ctrl+F', 'Alt+O'])
    assert kbsettings.get_shortcuts('Actions', 'foo') == ['Ctrl+F', 'Alt+O']


def test_keyboardsettings_get_shortcuts_existing(kbsettings):
    kbsettings.set_shortcuts('Actions', 'bar', ['Ctrl+R'])
    with patch.object(kbsettings, 'set_shortcuts') as set_mock:
        with patch.object(kbsettings, 'save_unknown_shortcuts', True):
            shortcuts = kbsettings.get_shortcuts('Actions', 'bar', ['Ctrl+B'])
            assert shortcuts == ['Ctrl+R']
            set_mock.assert_not_called()


def test_keyboardsettings_get_shortcuts_default(kbsettings):
    with patch.object(kbsettings, 'set_shortcuts') as set_mock:
        with patch.object(kbsettings, 'save_unknown_shortcuts', True):
            shortcuts = kbsettings.get_shortcuts('Actions', 'bar', ['Ctrl+B'])
            assert shortcuts == ['Ctrl+B']
            set_mock.assert_called_once_with('Actions', 'bar', ['Ctrl+B'])


def test_keyboardsettings_get_shortcuts_default_doesnt_override_empty(
        kbsettings):
    kbsettings.set_shortcuts('Actions', 'bar', [])
    with patch.object(kbsettings, 'set_shortcuts') as set_mock:
        with patch.object(kbsettings, 'save_unknown_shortcuts', True):
            shortcuts = kbsettings.get_shortcuts('Actions', 'bar', ['Ctrl+B'])
            assert shortcuts == []
            set_mock.assert_not_called()


def test_keyboardsettings_get_shortcuts_not_set_no_defaults(kbsettings):
    with patch('dreamboard.config.KeyboardSettings.set_shortcuts') as set_mock:
        with patch.object(kbsettings, 'save_unknown_shortcuts', True):
            shortcuts = kbsettings.get_shortcuts('Actions', 'baz')
            assert shortcuts == []
            set_mock.assert_called_once_with('Actions', 'baz', [])
