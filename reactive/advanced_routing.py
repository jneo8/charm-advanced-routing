"""Reactive charm hooks."""
from AdvancedRoutingHelper import AdvancedRoutingHelper

from charmhelpers.core.hookenv import (
    Hooks,
    config,
    status_set,
)

from charms.reactive import (
    hook,
    set_flag,
    when,
    when_not,
)


hooks = Hooks()
advanced_routing = AdvancedRoutingHelper()


@when_not('advanced-routing.installed')
def install_routing():
    """Install the charm."""
    if config('enable-advanced-routing'):
        try:
            advanced_routing.setup()
            advanced_routing.apply_routes()
            set_flag('advanced-routing.installed')
        except Exception as ex:
            status_set('blocked', 'Error: {}'.format(str(ex)))

    status_set('active', 'Unit is ready.')


@hook('upgrade-charm')
def upgrade_charm():
    """Handle resource-attach and config-changed events."""
    if config('enable-advanced-routing'):
        status_set('maintenance', 'Installing new static routes.')
        try:
            advanced_routing.remove_routes()
            advanced_routing.setup()
            advanced_routing.apply_routes()
        except Exception as ex:
            status_set('blocked', 'Error: {}'.format(str(ex)))

    status_set('active', 'Unit is ready.')


@when('config.changed.enable-advanced-routing')
def reconfigure_routing():
    """Handle routing configuration change."""
    if config('enable-advanced-routing'):
        status_set('maintenance', 'Installing routes.')
        try:
            advanced_routing.remove_routes()
            advanced_routing.setup()
            advanced_routing.apply_routes()
        except Exception as ex:
            status_set('blocked', 'Error: {}'.format(str(ex)))
    else:
        status_set('maintenance', 'Removing routes.')
        try:
            advanced_routing.remove_routes()
        except Exception as ex:
            status_set('blocked', 'Error: {}'.format(str(ex)))

    status_set('active', 'Unit is ready.')
