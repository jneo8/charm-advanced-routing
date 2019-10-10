"""Reactive charm hooks."""
from advanced_routing_helper import AdvancedRoutingHelper

from charmhelpers.core.hookenv import (
    config,
    status_set,
)

from charms.reactive import (
    set_flag,
    when,
    when_not,
)


advanced_routing = AdvancedRoutingHelper()


@when_not('advanced-routing.installed')
def install_routing():
    """Install the charm."""
    if config('enable-advanced-routing'):
        advanced_routing.setup()
        advanced_routing.apply_config()
        set_flag('advanced-routing.installed')

    status_set('active', 'Unit is ready.')


@when('config.changed')
def reconfigure_routing():
    """Handle routing configuration change."""
    if config('enable-advanced-routing'):
        status_set('maintenance', 'Installing routes.')
        advanced_routing.remove_routes()
        advanced_routing.setup()
        advanced_routing.apply_config()
    else:
        status_set('maintenance', 'Removing routes.')
        advanced_routing.remove_routes()

    status_set('active', 'Unit is ready.')
