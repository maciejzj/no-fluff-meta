SRC_DIR := it_jobs_meta
TEST_DIR := tests
ALL_PYTHON_CODE_DIRS := $(SRC_DIR) $(TEST_DIR)

# QA

.PHONY: all
all: format remove-unused check test

.PHONY: format
format: $(ALL_PYTHON_CODE_DIRS)
	isort $(ALL_PYTHON_CODE_DIRS)
	black $(ALL_PYTHON_CODE_DIRS)
	pydocstringformatter --write $(ALL_PYTHON_CODE_DIRS)

.PHONY: remove-unused
remove-unused: $(ALL_PYTHON_CODE_DIRS)
	autoflake --remove-all-unused-imports --in-place --recursive $(ALL_PYTHON_CODE_DIRS)

.PHONY: check
check: format-check lint type-check

.PHONY: lint
lint:
	flake8 $(ALL_PYTHON_CODE_DIRS)

.PHONY: type-check
type-check:
	mypy $(ALL_PYTHON_CODE_DIRS)

.PHONY: format-check
format-check:
	isort --check-only --diff $(ALL_PYTHON_CODE_DIRS)
	black --check --diff $(ALL_PYTHON_CODE_DIRS)
	pydocstringformatter --exit-code $(ALL_PYTHON_CODE_DIRS)

# Test

.PHONY: test
test:
	pytest

# Cleanup

.PHONY: clean
clean: 
	rm -rf $(SRC_DIR).egg-info

# Dependencies management

requirements.txt: pyproject.toml
	pip-compile --all-extras --output-file $@ $<

.PHONY: sync-requirements
sync-requirements: requirements.txt
	pip-sync $<
