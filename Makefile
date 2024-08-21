# Makefile

# Define variables
ENV_NAME = dummy-dtc-env
PYTHON_VERSION = 3.11.5
DEV_REQUIREMENTS = requirements-dev.txt
PY_FILES = $(shell find . -name "*.py")

# Export the variable for all targets
.EXPORT_ALL_VARIABLES: 
PYDEVD_DISABLE_FILE_VALIDATION=1

# Target to create a conda environment and install dependencies
create_local_env:
	conda create -y -n $(ENV_NAME) python=$(PYTHON_VERSION)
	conda run -n $(ENV_NAME) pip install -r requirements.txt
	conda run -n $(ENV_NAME) pip install -r $(DEV_REQUIREMENTS)
	conda run -n $(ENV_NAME) python -m ipykernel install --user --name=$(ENV_NAME) --display-name "Python ($(ENV_NAME))"

# Target to remove the Jupyter kernel and delete the conda environment
remove_local_env:
	@if jupyter kernelspec list | grep -q $(ENV_NAME); then \
		jupyter kernelspec remove -f $(ENV_NAME); \
	else \
		echo "Jupyter kernel '$(ENV_NAME)' not found."; \
	fi
	@if conda info --envs | grep -q $(ENV_NAME); then \
		conda env remove -n $(ENV_NAME); \
	else \
		echo "Conda environment '$(ENV_NAME)' not found."; \
	fi

# Format py files
format_py:
	isort $(PY_FILES)
	black $(PY_FILES)

# Linting py files
lint_py:
	pylint $(PY_FILES) --exit-zero

# Running unit_tests
unit_tests:
	pytest ./tests

# Running integration_tests
integration_tests:
	./integration_tests/connectivity_check.sh

.PHONY: create_local_env remove_local_env format_py lint_py unit_tests integration_tests
