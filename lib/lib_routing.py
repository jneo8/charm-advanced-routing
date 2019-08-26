"""Routing module."""
import os
import errno
import subprocess

from charmhelpers.core import hookenv
from charmhelpers.core.host import (
    lsb_release,
    CompareHostReleases,
)
from RoutingEntry import RoutingEntryType
from RoutingValidator import RoutingConfigValidator

IF_SCRIPT = '95-juju_routing'
COMMON_LOCATION = '/usr/local/sbin/'


class AdvancedRoutingHelper:
    """Helper class for routing"""

    def __init__(self):
        """Init function."""
        hookenv.log('Init %s' % self.__class__.__name__, level=hookenv.INFO)
        self.pre_setup()

    def pre_setup(self):
        # create folder path for the ifup/down scripts
        if not os.path.exists(COMMON_LOCATION + 'if-up/'):
            os.makedirs(COMMON_LOCATION + 'if-up/')
            hookenv.log('Created %s' % COMMON_LOCATION + 'if-up/', level=hookenv.INFO)
        if not os.path.exists(COMMON_LOCATION + 'if-down/'):
            os.makedirs(COMMON_LOCATION + 'if-down/')
            hookenv.log('Created %s' % COMMON_LOCATION + 'if-down/', level=hookenv.INFO)

        self.ifup_path = (COMMON_LOCATION + 'if-up/{}').format(IF_SCRIPT)
        self.ifdown_path = (COMMON_LOCATION + 'if-down/{}').format(IF_SCRIPT)

        # check for service file of charm-policy-routing, and block if its present
        if os.path.exists("/etc/systemd/system/charm-pre-install-policy-routing.service"):
            hookenv.log('It looks like chamr-policy-routing is enabled.  charm-pre-install-policy-routing.service', 'WARNING')
            hookenv.status_set('blocked', 'Please disable charm-policy-routing')

    def post_setup(self):
        """Symlinks the up/down scripts from the if.up/down or netplan scripts location"""
        hookenv.log('Symlinking into distro specific netowrk manager', level=hookenv.INFO)
        release = lsb_release()['DISTRIB_CODENAME'].lower()
        if CompareHostReleases(release) < "bionic":
            self.symlink_force(self.ifup_path, '/etc/network/if-up.d/{}'.format(IF_SCRIPT))
            self.symlink_force(self.ifdown_path, '/etc/network/if-down.d/{}'.format(IF_SCRIPT))
        if CompareHostReleases(release) > "artful":
            self.symlink_force(self.ifup_path, '/etc/networkd-dispatcher/routable.d/{}'.format(IF_SCRIPT))
            self.symlink_force(self.ifdown_path, '/etc/networkd-dispatcher/off.d/{}'.format(IF_SCRIPT))

    def setup(self):
        """Modify the interfaces configurations."""
        RoutingConfigValidator()

        hookenv.log('Writing %s' % self.ifup_path, level=hookenv.INFO)
        # Modify if-up.d
        with open(self.ifup_path, 'w') as ifup:
            ifup.write("# This file is managed by Juju.\n")
            ifup.write("sudo ip route flush cache\n")
            # Note this will clear all rules
            #ifdown.write("ip rule flush\n")
            #ifdown.write("ip rule add priority 32767 lookup default")
            for entry in RoutingEntryType.entries:
                ifup.write(entry.addLine)
        os.chmod(self.ifup_path, 0o755)

        hookenv.log('Writing %s' % self.ifdown_path, level=hookenv.INFO)
        # Modify if-down.d
        with open(self.ifdown_path, 'w') as ifdown:
            ifdown.write("# This file is managed by Juju.\n")
            for entry in list(reversed(RoutingEntryType.entries)):
                ifdown.write(entry.removeLine)
            ifdown.write("sudo ip route flush cache\n")
            # Note this will clear all rules
            #ifdown.write("ip rule flush\n")
            #ifdown.write("ip rule add priority 32767 lookup default")
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
                cmd = ["sudo", "sh", "-c", self.ifdown_path]
                subprocess.check_call(cmd)
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
                os.remove('/etc/network/if-up.d/{}'.format(IF_SCRIPT))
                os.remove('/etc/network/if-down.d/{}'.format(IF_SCRIPT))
            if CompareHostReleases(release) > "artful":
                os.remove('/etc/networkd-dispatcher/routable.d/{}'.format(IF_SCRIPT))
                os.remove('/etc/networkd-dispatcher/off.d/{}'.format(IF_SCRIPT))
        except:
            hookenv.log('Nothing to clean up', 'WARNING')

    def symlink_force(self, target, link_name):
        """Ensures accute symlink by removing any existing links"""
        try:
            os.symlink(target, link_name)
        except OSError as e:
            if e.errno == errno.EEXIST:
                os.remove(link_name)
                os.symlink(target, link_name)
            else:
                raise e
