# Overview

This subordinate charm allows for the configuration of policy routing rules on the deployed host,
as well as routes to configured services. A list of hash maps, in JSON format, is expected.

Charm supports IPv4 addressing.


# Build
```
cd charm-advanced-routing
make build
```

# Usage
Add to an existing application using juju-info relation.

Example:
```
juju deploy cs:advanced-routing
juju add-relation ubuntu advanced-routing
```

# Configuration                                                                 
The user can configure the following parameters:
 * `enable-advanced-routing`: Enable routing. This requires for the charm to have routing information configured in JSON format: ```juju config advanced-routing --file path/to/your/config```

 * `advanced-routing-config` parameter contains 3 types of entities: 'table', 'route', 'rule'. The 'type' parameter is always required.

table: routing table to put the rules in (used in rules)

route: defines a static route with the following params:
 - default_route: should this be a default route or not (boolean: true|false) (optional)
 - net:           IPv4 CIDR for a destination network (string) (required)
 - gateway:       IPv4 gateway address (string) (required)
 - table:         routing table name (string) (optional)
 - metric:        metric for the route (int) (optional)
 - device:        device (interface) (string) (optional)

rule:
 - from-net: IPv4 CIDR source network (string) (required)
 - to-net: IPv4 CIDR destination network (string) (required)
 - table: routing table name (string) (required)
 - priority: priority (int) (optional)

An example yaml config file below:

```yaml
settings:
  advanced-routing-config:
    value: |-
      [ {
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
  enable-advanced-routing:
    value: true
```

The `example_config.yaml` file is also provided with the codebase.

# Testing                                                                       
To run lint tests:
```bash
tox -e lint

```
To run unit tests:
```bash
tox -e unit
```
Functional tests have been developed using python-libjuju, deploying a simple ubuntu charm and adding the charm as a subordinate.

To run tests using python-libjuju:
```bash
tox -e functional
```

# Contact Information

 * LMA Charmers <llama-charmers@lists.launchpad.net>
