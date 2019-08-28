"""Routing module."""
import errno
import os
import subprocess

from RoutingEntry import RoutingEntryType

from RoutingValidator import RoutingConfigValidator

from charmhelpers.core import hookenv
from charmhelpers.core.host import (
    CompareHostReleases,
    lsb_release,
)


class AdvancedRoutingHelper:
    """Helper class for routing."""

    if_script = '95-juju_routing'
    common_location = '/usr/local/sbin/'  # trailing slash
    net_tools_up_path = '/etc/network/if-up.d/'  # trailing slash
    net_tools_down_path = '/etc/network/if-down.d/'  # trailing slash
    netplan_up_path = '/etc/networkd-dispatcher/routable.d/'  # trailing slash
    netplan_down_path = '/etc/networkd-dispatcher/off.d/'  # trailing slash
    policy_routing_service_path = '/etc/systemd/system/'  # trailing slash
    ifup_path = None
    ifdown_path = None

    def __init__(self):
        """Init function."""
        hookenv.log('Init {}'.format(self.__class__.__name__), level=hookenv.INFO)
        self.pre_setup()

    def pre_setup(self):
        """Create folder path for the ifup/down scripts."""
        if not os.path.exists(self.common_location + 'if-up/'):
            os.makedirs(self.common_location + 'if-up/')
            hookenv.log('Created {}'.format(self.common_location + 'if-up/'), level=hookenv.INFO)
        if not os.path.exists(self.common_location + 'if-down/'):
            os.makedirs(self.common_location + 'if-down/')
            hookenv.log('Created {}'.format(self.common_location + 'if-down/'), level=hookenv.INFO)

        self.ifup_path = '{}if-up/{}'.format(self.common_location, self.if_script)
        self.ifdown_path = '{}if-down/{}'.format(self.common_location, self.if_script)

        # check for service file of charm-policy-routing, and block if its present
        if os.path.exists(self.policy_routing_service_path + 'charm-pre-install-policy-routing.service'):
            hookenv.log('It looks like charm-policy-routing is enabled. '
                        ' charm-pre-install-policy-routing.service', 'WARNING')
            hookenv.status_set('blocked', 'Please disable charm-policy-routing')
            raise Exception('Please disable charm-policy-routing')

    def post_setup(self):
        """Symlinks the up/down scripts from the if.up/down or netplan scripts location."""
        hookenv.log('Symlinking into distro specific network manager', level=hookenv.INFO)
        release = lsb_release()['DISTRIB_CODENAME'].lower()
        if CompareHostReleases(release) < "bionic":
            self.symlink_force(self.ifup_path, '{}{}'.format(self.net_tools_up_path, self.if_script))
            self.symlink_force(self.ifdown_path, '{}{}'.format(self.net_tools_down_path, self.if_script))
        else:
            self.symlink_force(self.ifup_path, '{}{}'.format(self.netplan_up_path, self.if_script))
            self.symlink_force(self.ifdown_path, '{}{}'.format(self.netplan_down_path, self.if_script))

    def setup(self):
        """Modify the interfaces configurations."""
        RoutingConfigValidator()

        hookenv.log('Writing {}'.format(self.ifup_path), level=hookenv.INFO)
        # Modify if-up.d
        with open(self.ifup_path, 'w') as ifup:
            ifup.write("# This file is managed by Juju.\n")
            ifup.write("ip route flush cache\n")
            for entry in RoutingEntryType.entries:
                ifup.write(entry.addline)
            os.chmod(self.ifup_path, 0o755)

        hookenv.log('Writing {}'.format(self.ifdown_path), level=hookenv.INFO)
        # Modify if-down.d
        with open(self.ifdown_path, 'w') as ifdown:
            ifdown.write("# This file is managed by Juju.\n")
            for entry in list(reversed(RoutingEntryType.entries)):
                ifdown.write(entry.removeline)
            ifdown.write("ip route flush cache\n")
            os.chmod(self.ifdown_path, 0o755)

        self.post_setup()

    def apply_routes(self):
        """Apply the new routes to the system."""
        hookenv.log('Applying routing rules', level=hookenv.INFO)
        for entry in RoutingEntryType.entries:
            entry.apply()

    def remove_routes(self):
        """Cleanup job."""
        hookenv.log('Removing routing rules', level=hookenv.INFO)
        if os.path.exists(self.ifdown_path):
            try:
                subprocess.check_call(["sh", "-c", self.ifdown_path], shell=True)
            except subprocess.CalledProcessError:
                # Either rules are removed or not valid
                hookenv.log('ifdown script failed. Maybe rules are already gone?', 'WARNING')

        # remove files
        if os.path.exists(self.ifup_path):
            os.remove(self.ifup_path)
        if os.path.exists(self.ifdown_path):
            os.remove(self.ifdown_path)

        # remove symlinks
        release = lsb_release()['DISTRIB_CODENAME'].lower()
        try:
            if CompareHostReleases(release) < "bionic":
                os.remove('{}{}'.format(self.net_tools_up_path, self.if_script))
                os.remove('{}{}'.format(self.net_tools_down_path, self.if_script))
            else:
                os.remove('{}{}'.format(self.netplan_up_path, self.if_script))
                os.remove('{}{}'.format(self.netplan_down_path, self.if_script))
        except Exception:
            hookenv.log('Nothing to clean up', 'WARNING')

    def symlink_force(self, target, link_name):
        """Ensures accute symlink by removing any existing links."""
        try:
            os.symlink(target, link_name)
        except OSError as e:
            if e.errno == errno.EEXIST:
                os.remove(link_name)
                os.symlink(target, link_name)
            else:
                raise e
