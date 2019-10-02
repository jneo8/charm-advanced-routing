#!/usr/bin/python3
"""Configurations for tests."""
import subprocess
import unittest.mock as mock

import pytest


@pytest.fixture
def mock_layers(monkeypatch):
    """Layers mock."""
    import sys
    sys.modules['charms.layer'] = mock.Mock()
    sys.modules['reactive'] = mock.Mock()

    # Mock any functions in layers that need to be mocked here
    def options(layer):
        # mock options for layers here
        if layer == 'example-layer':
            options = {'port': 9999}
            return options
        else:
            return None

    monkeypatch.setattr('AdvancedRoutingHelper.layer.options', options)


@pytest.fixture
def mock_hookenv_config(monkeypatch):
    """Hookenv mock."""
    import yaml

    def mock_config():
        cfg = {}
        yml = yaml.load(open('./config.yaml'))

        # Load all defaults
        for key, value in yml['options'].items():
            cfg[key] = value['default']

        # Manually add cfg from other layers
        # cfg['my-other-layer'] = 'mock'
        return cfg

    monkeypatch.setattr('AdvancedRoutingHelper.hookenv.config', mock_config)


@pytest.fixture
def mock_remote_unit(monkeypatch):
    """Remote unit mock."""
    monkeypatch.setattr('AdvancedRoutingHelper.hookenv.remote_unit', lambda: 'unit-mock/0')


@pytest.fixture
def mock_charm_dir(monkeypatch):
    """Charm dir mock."""
    monkeypatch.setattr('AdvancedRoutingHelper.hookenv.charm_dir', lambda: '/mock/charm/dir')


@pytest.fixture
def advanced_routing_helper(tmpdir, mock_hookenv_config, mock_charm_dir, monkeypatch):
    """Routing fixture."""
    from AdvancedRoutingHelper import AdvancedRoutingHelper
    helper = AdvancedRoutingHelper

    monkeypatch.setattr('AdvancedRoutingHelper.AdvancedRoutingHelper', lambda: helper)

    return helper


@pytest.fixture
def mock_check_call(monkeypatch):
    """Requests.get() mocked to return {'mock_key':'mock_response'}."""
    def mock_get(*args, **kwargs):
        return True

    monkeypatch.setattr(subprocess, "check_call", mock_get)
