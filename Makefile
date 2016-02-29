
PROJECT_NAME := $(shell python setup.py --name)

SHELL := /bin/bash
BOLD := \033[1m
DIM := \033[2m
RESET := \033[0m

all: test clean

uninstall:
	@echo -e "$(BOLD)uninstalling '$(PROJECT_NAME)'$(RESET)"
	-@pip uninstall -y $(PROJECT_NAME) 2> /dev/null

install:
	@echo -e "$(BOLD)installing '$(PROJECT_NAME)'$(RESET)"
	@echo -e -n "$(DIM)"
	@python setup.py install
	@echo -e -n "$(RESET)"

test: uninstall install
	@echo -e "$(BOLD)running test units for '$(PROJECT_NAME)'$(RESET)"
	@python -m unittest discover \
		-s tests -p 'tests_*.py' \
		--verbose
	@rm -rf tests/*.pyc

dist:
	@echo -e "$(BOLD)packaging '$(PROJECT_NAME)'$(RESET)"
	@python setup.py sdist --formats=zip --dist-dir=.

clean:
	@echo -e "$(BOLD)cleaning '$(PROJECT_NAME)' repository$(RESET)"
	@rm -rf build
	@rm -rf dist
	@rm -rf **/$(PROJECT_NAME).egg-info
	@rm -rf $(PROJECT_NAME).egg-info
	@rm -rf .eggs

publish:
	@echo -e "$(BOLD)publishing '$(PROJECT_NAME)' on pypi$(RESET)"
	-@python setup.py sdist upload
	@$(MAKE) clean
