"""Reactive charm hooks."""
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

from lib_routing import AdvancedRoutingHelper

hooks = Hooks()
advanced_routing = AdvancedRoutingHelper()


@when_not('advanced-routing.installed')
def install_routing():
    """Install the charm."""
    if config('enable-advanced-routing'):
        advanced_routing.setup()
        advanced_routing.apply_routes()
        set_flag('advanced-routing.installed')

    status_set('active', 'Unit is ready.')


@hook('upgrade-charm')
def upgrade_charm():
    """Handle resource-attach and config-changed events."""
    if config('enable-advanced-routing'):
        status_set('maintenance', 'Installing new static routes.')
        advanced_routing.remove_routes()
        advanced_routing.setup()
        advanced_routing.apply_routes()

    status_set('active', 'Unit is ready.')


@when('config.changed.enable-advanced-routing')
def reconfigure_routing():
    """Handle routing configuration change."""
    if config('enable-advanced-routing'):
        status_set('maintenance', 'Installing routes.')
        advanced_routing.remove_routes()
        advanced_routing.setup()
        advanced_routing.apply_routes()
    else:
        status_set('maintenance', 'Removing routes.')
        advanced_routing.remove_routes()

    status_set('active', 'Unit is ready.')