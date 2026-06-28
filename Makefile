# A-Maze-ing -- automation of common tasks.
# A virtual environment is created in .venv and all tools live inside it,
# keeping the host system clean (delete .venv with `make fclean`).

VENV    := .venv
PYTHON  := $(VENV)/bin/python
PIP     := $(VENV)/bin/pip
CONFIG  := config.txt

.DEFAULT_GOAL := run

$(VENV):
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

## install: create the venv and install dev dependencies
install: $(VENV)
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

## run: generate a maze from $(CONFIG) and open the display
run: install
	$(PYTHON) a_maze_ing.py $(CONFIG)

## debug: run the main script under pdb
debug: install
	$(PYTHON) -m pdb a_maze_ing.py $(CONFIG)

## test: run the unit test-suite
test: install
	$(PYTHON) -m pytest -q

## lint: flake8 + mypy (mandatory checks)
lint: install
	$(VENV)/bin/flake8 .
	$(VENV)/bin/mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

## lint-strict: flake8 + mypy in strict mode (optional, stronger)
lint-strict: install
	$(VENV)/bin/flake8 .
	$(VENV)/bin/mypy . --strict

## build: build the reusable mazegen package (.tar.gz and .whl)
build: install
	$(PIP) install --upgrade build
	$(PYTHON) -m build

## clean: remove caches and Python artifacts
clean:
	rm -rf __pycache__ */__pycache__ .mypy_cache .pytest_cache
	rm -rf build dist *.egg-info
	find . -name '*.pyc' -delete

## fclean: clean + remove the virtual environment and generated output
fclean: clean
	rm -rf $(VENV)
	rm -f maze.txt

.PHONY: install run debug test lint lint-strict build clean fclean
