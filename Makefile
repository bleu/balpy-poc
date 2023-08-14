PROJECTS := $(notdir $(wildcard workspaces/*))


.clean-venv:
	rm -rf .venv

.venv:
	pipx run poetry config virtualenvs.create true --local
	pipx run poetry install --sync

.ensure-deployments-module:
	@if [ ! -d "workspaces/deployments/src/balpy/deployments/__init__.py" ]; then \
		echo "workspaces/deployments/src/balpy/deployments/__init__.py does not exist. Creating it to ensure the submodule is accessible."; \
		touch workspaces/deployments/src/balpy/deployments/__init__.py; \
		exit 0; \
	fi

init: .clean-venv .ensure-deployments-module .venv

test-%: .venv
	pipx run poetry install --sync --with $*
	pipx run poetry run pytest workspaces/$*

tests: .venv $(addprefix test-, $(PROJECTS))

test-isolated-%: .venv
	pipx run poetry install --sync --only $*
	pipx run poetry run pytest workspaces/$*
