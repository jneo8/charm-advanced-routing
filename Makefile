help:
	@echo "This project supports the following targets"
	@echo ""
	@echo " make help - show this text"
	@echo " make lint - run flake8"
	@echo " make test - run all tests: lint, unit and func tests"
	@echo " make unittest - run the tests defined in the unittest subdirectory"
	@echo " make functional - run the tests defined in the functional subdirectory"
	@echo " make release - build the charm"
	@echo " make clean - remove unneeded files"
	@echo ""

lint:
	@echo "Running flake8"
	@tox -e lint

test: lint unittest functional

unittest:
	@tox -e unit

functional: build
	@PYTEST_KEEP_MODEL=$(PYTEST_KEEP_MODEL) \
	    PYTEST_CLOUD_NAME=$(PYTEST_CLOUD_NAME) \
	    PYTEST_CLOUD_REGION=$(PYTEST_CLOUD_REGION) \
	    tox -e functional

build:
	@echo "Building charm to base directory $(JUJU_REPOSITORY)"
#	@-git describe --tags > ./repo-info
	@LAYER_PATH=./layers INTERFACE_PATH=./interfaces TERM=linux \
		JUJU_REPOSITORY=$(JUJU_REPOSITORY) charm build . --force

release: clean build
	@echo "Charm is built at $(JUJU_REPOSITORY)/builds"

clean:
	@echo "Cleaning files"
	@if [ -d .tox ] ; then rm -r .tox ; fi
	@if [ -d .pytest_cache ] ; then rm -r .pytest_cache ; fi
	@find . -type d -name '__pycache__' -prune -exec rm -rf "{}"

# The targets below don't depend on a file
.PHONY: lint test unittest functional build release clean help
