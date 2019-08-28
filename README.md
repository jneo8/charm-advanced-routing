# Overview

This subordinate charm allows for the configuration of simple policy routing rules on the deployed host
and adding routing to configured services via a JSON.

# Usage


# Build
```
cd charm-advanced-routing
make build
```

# Usage
Add to an existing application using juju-info relation.

Example:
```
juju deploy cs:~canonical-bootstack/routing
juju add-relation ubuntu advanced-routing
```

# Configuration                                                                 
The user can configure the following parameters:
* enable-advanced-routing: Enable routing. This requires for the charm to have JSON with routing information configured: ```juju config advanced-routing --file path/to/your/config```

A example_config.json file is provided with the codebase.

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
David O Neill <david.o.neill@canonical.com>

