#!/usr/bin/python3.6
"""Main module for functional testing."""

import os

import pytest

pytestmark = pytest.mark.asyncio
SERIES = ['bionic', 'xenial']

############
# FIXTURES #
############


@pytest.fixture(scope='module', params=SERIES)
async def deploy_app(request, model):
    """Deploy the advanced-routing charm as a subordinate of ubuntu."""
    release = request.param

    await model.deploy(
        'ubuntu',
        application_name='ubuntu-' + release,
        series=release,
        channel='stable'
    )
    advanced_routing = await model.deploy(
        '{}/builds/advanced-routing'.format(os.getenv('JUJU_REPOSITORY')),
        application_name='advanced-routing-' + release,
        series=release,
        num_units=0,
    )
    await model.add_relation(
        'ubuntu-' + release,
        'advanced-routing-' + release
    )

    await model.block_until(lambda: advanced_routing.status == 'active')
    yield advanced_routing


@pytest.fixture(scope='module')
async def unit(deploy_app):
    """Return the advanced-routing unit we've deployed."""
    return deploy_app.units.pop()

#########
# TESTS #
#########


async def test_deploy(deploy_app):
    """Test the deployment."""
    assert deploy_app.status == 'active'


async def test_juju_routing(reconfigure_app, file_contents, file_exists, unit, deploy_app):
    """Test juju routing file contents with config."""
    json_config = """[{
    "type": "table",
    "table": "SF1"
}, {
    "type": "route",
    "default_route": true,
    "net": "192.170.1.0/24",
    "gateway": "10.191.86.2",
    "table": "SF1",
    "metric": 101,
    "device": "eth0"
}, {
    "type": "route",
    "net": "6.6.6.0/24",
    "gateway": "10.191.86.2"
}, {
    "type": "rule",
    "from-net": "192.170.2.0/24",
    "to-net": "192.170.2.0/24",
    "table": "SF1",
    "priority": 101
} ]
"""
    await reconfigure_app(cfg={'advanced-routing-config': json_config}, target=deploy_app)
    await reconfigure_app(cfg={'enable-advanced-routing': 'true'}, target=deploy_app)

    up_path = '/usr/local/lib/juju-charm-advanced-routing/if-up/95-juju_routing'
    down_path = '/usr/local/lib/juju-charm-advanced-routing/if-down/95-juju_routing'

    if_up_content = await file_contents(path=up_path, target=unit)
    if_down_content = await file_contents(path=down_path, target=unit)

    if_up_expected_content = """# This file is managed by Juju.
ip route flush cache
# Table: name SF1
ip route replace default via 10.191.86.2 table SF1 dev eth0
ip route replace 6.6.6.0/24 via 10.191.86.2
ip rule add from 192.170.2.0/24 to 192.170.2.0/24 lookup SF1
"""

    if_down_expected_content = """# This file is managed by Juju.
ip rule del from 192.170.2.0/24 to 192.170.2.0/24 lookup SF1
ip route del 6.6.6.0/24 via 10.191.86.2
ip route del default via 10.191.86.2 table SF1 dev eth0
ip route flush table SF1
ip rule del table SF1
ip route flush cache
"""

    if_up_exists = await file_exists(path=up_path, target=unit)
    if_down_exists = await file_exists(path=down_path, target=unit)

    assert if_up_exists == "1\n"
    assert if_down_exists == "1\n"
    assert if_up_expected_content == if_up_content
    assert if_down_expected_content == if_down_content


async def test_juju_routing_disable(reconfigure_app, file_exists, unit, deploy_app):
    """Test juju routing file non-existance when conf disabled."""
    await reconfigure_app(cfg={'enable-advanced-routing': 'false'}, target=deploy_app)
    path = '/etc/networkd-dispatcher/routable.d/95-juju_routing'
    exists = await file_exists(path=path, target=unit)
    assert exists == "0\n"
