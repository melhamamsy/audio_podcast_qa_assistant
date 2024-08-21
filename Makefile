# Makefile
include .env

# Setting env variables
export $(shell sed 's/=.*//' .env)

# Define variables
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

# Docker-compose
compose:
	docker-compose up -d

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

# Download ollama models specified as CHAT_MODEL & EMBED_MODEL
setup_ollama:
	./scripts/setup_ollama.sh

# Start prefect server and worker
prefect_start_server:
	@if ! curl -s -o /dev/null localhost:4200; then \
		echo "Prefect server is not running. Starting the server..."; \
		conda run -n $(ENV_NAME) prefect server start & \
		for i in $$(seq 1 10); do \
			if curl -s -o /dev/null localhost:4200; then \
				echo "\033[0;32mPrefect server started successfully.\033[0m"; \
				exit 0; \
			else \
				echo "Waiting for Prefect server to start... ($$i/10)"; \
				sleep 5; \
			fi; \
		done; \
		echo "\033[0;31mFailed to start the Prefect server after multiple attempts.\033[0m"; \
	else \
		echo "\033[0;32mPrefect server is already running.\033[0m"; \
	fi

# Stop prefect server
prefect_stop_server:
	@if curl -s -o /dev/null localhost:4200; then \
		echo "Prefect server is running. Stopping the server..."; \
		kill $$(ps aux | grep "prefect server" | grep -v grep | awk '{print $$2}') 2>/dev/null || true; \
		for i in $$(seq 1 10); do \
			if ! curl -s -o /dev/null localhost:4200; then \
				echo "\033[0;32mPrefect server terminated successfully.\033[0m"; \
				exit 0; \
			else \
				echo "Waiting for Prefect server to terminate... ($$i/10)"; \
				sleep 2; \
			fi; \
		done; \
		echo "\033[0;31mFailed to terminate the Prefect server after multiple attempts.\033[0m"; \
	else \
		echo "\033[0;32mPrefect server is not running.\033[0m"; \
	fi

# Start a new prefect worker
prefect_start_worker:
	@conda run -n $(ENV_NAME) prefect worker start --pool ${WORK_POOL_NAME} &

# Kill all prefect workers
prefect_kill_workers:
	@./scripts/kill_prefect_workers.sh 

# Re-indexing es with defacto mode
reindex_es_defacto:
	conda run -n $(ENV_NAME) \
		prefect deployment run setup_es/ad-hoc \
		-p reindex_es=true \
		-p defacto=true
