"""Tests for dev/prod data-directory selection. No GUI is required."""

import os

from hexlog import constants as C


def test_defaults_to_dev_without_appimage():
    assert C.data_subdir({}) == "dev"


def test_appimage_runtime_selects_prod():
    assert C.data_subdir({"APPIMAGE": "/tmp/hexlog-0.3.3-x86_64.AppImage"}) == "prod"


def test_explicit_override_wins():
    assert C.data_subdir({"APPIMAGE": "/tmp/x.AppImage", "HEXLOG_ENV": "dev"}) == "dev"
    assert C.data_subdir({"HEXLOG_ENV": "prod"}) == "prod"


def test_data_paths_use_selected_subdir():
    assert C.DATA_SUBDIR == C.data_subdir()
    assert C.DATA_DIR == os.path.join(C.APP_CONFIG_DIR, C.DATA_SUBDIR)
    assert C.DATA_FILE == os.path.join(C.DATA_DIR, "data.json")
    assert C.MAPS_DIR == os.path.join(C.DATA_DIR, "maps")
    assert C.TOKENS_DIR == os.path.join(C.DATA_DIR, "tokens")


def test_config_root_defaults_to_home_config():
    assert C.config_root_dir({}) == os.path.join(os.path.expanduser("~"), ".config")


def test_config_root_respects_xdg_config_home():
    assert C.config_root_dir({"XDG_CONFIG_HOME": "/custom/cfg"}) == "/custom/cfg"


def test_app_config_dir_under_config_root():
    assert C.APP_CONFIG_DIR == os.path.join(C.config_root_dir(), "hexlog")
    assert C.LEGACY_DATA_DIR == os.path.join(os.path.expanduser("~"), ".hexlog")
