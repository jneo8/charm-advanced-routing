"""Main module for functional testing."""

import json
import os

import cfg_opts

import pytest

pytestmark = pytest.mark.asyncio
SERIES = [
    'bionic',
]
CHARM_BUILD_DIR = os.getenv('JUJU_REPOSITORY', '/tmp/charm-builds/advanced-routing').rstrip('/')

############
# FIXTURES #
############


@pytest.fixture(scope='module', params=SERIES)
async def deploy_app(request, model):
    """Deploy the advanced-routing charm as a subordinate of ubuntu."""
    release = request.param

    await model.deploy(
        'ubuntu',
        application_name='ubuntu-{}'.format(release),
        series=release,
        channel='stable'
    )
    advanced_routing = await model.deploy(
        CHARM_BUILD_DIR,
        application_name='advanced-routing-{}'.format(release),
        series=release,
        num_units=0,
    )
    await model.add_relation(
        'ubuntu-{}'.format(release),
        'advanced-routing-{}'.format(release),
    )

    yield advanced_routing


@pytest.fixture(scope='module')
async def unit(deploy_app):
    """Return the advanced-routing unit we've deployed."""
    return deploy_app.units.pop()

#########
# TESTS #
#########


async def test_deploy(deploy_app, model):
    """Test the deployment."""
    status, message = "blocked", "Advanced routing is disabled"
    await model.block_until(
        lambda: (deploy_app.status == status
                 and all(unit.workload_status_message == message
                         for unit in deploy_app.units)),
        timeout=300,
    )
    assert True


@pytest.mark.parametrize(
    "cfg",
    [pytest.param(cfg, id="cfg-{}".format(i))
     for i, cfg in enumerate(cfg_opts.JSON_CONFIGS)],
)
async def test_juju_routing(cfg, file_contents, file_exists, deploy_app, model):
    """Test juju routing file contents with config."""
    json_config = cfg["input"]
    await deploy_app.set_config({
        'advanced-routing-config': json.dumps(json_config),
        'enable-advanced-routing': 'true',
    })

    status, agent_status, message = "active", "idle", "Unit is ready"
    await model.block_until(
        lambda: (deploy_app.status == status
                 and all(unit.agent_status == agent_status
                         and unit.workload_status_message == message
                         for unit in deploy_app.units)),
        timeout=300,
    )

    common_path = "/usr/local/lib/juju-charm-advanced-routing"
    up_path = "{}/if-up/95-juju_routing".format(common_path)
    down_path = "{}/if-down/95-juju_routing".format(common_path)
    unit = deploy_app.units.pop()

    if_up_content = await file_contents(path=up_path, target=unit)
    if_down_content = await file_contents(path=down_path, target=unit)

    if_up_expected_content = cfg["expected_ifup"]
    if_down_expected_content = cfg["expected_ifdown"]

    assert if_up_expected_content == if_up_content
    assert if_down_expected_content == if_down_content

    series = deploy_app.name.split("-")[-1]
    ifup_path = ("/etc/network/if-up.d"
                 if series >= "xenial" or series < "bionic"
                 else "/etc/networkd-dispatcher/routable.d")
    ifup_filename = "{}/95-juju_routing".format(ifup_path)
    ifup_exists = await file_exists(path=ifup_filename, target=unit)

    assert ifup_exists == "1\n"


async def test_juju_routing_disable(file_exists, unit, deploy_app, model):
    """Test juju routing file non-existance when conf disabled."""
    status, message = "blocked", "Advanced routing is disabled"

    await deploy_app.set_config({'enable-advanced-routing': 'false'})
    await model.block_until(
        lambda: (deploy_app.status == status
                 and all(unit.workload_status_message == message
                         for unit in deploy_app.units)),
        timeout=300,
    )

    series = deploy_app.name.split("-")[-1]
    ifup_path = ("/etc/network/if-up.d"
                 if "xenial" <= series < "bionic"
                 else "/etc/networkd-dispatcher/routable.d")
    ifup_filename = "{}/95-juju_routing".format(ifup_path)
    ifup_exists = await file_exists(path=ifup_filename, target=unit)

    assert ifup_exists == "0\n"
