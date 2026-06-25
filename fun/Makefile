PYTHON := python3
MAIN   := a_maze_ing.py
CONFIG := config.txt

.PHONY: install run debug lint lint-strict clean

## Install project dependencies (flake8, mypy)
install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

## Run the main script
run:
	$(PYTHON) $(MAIN) $(CONFIG)

## Run the main script under the Python debugger
debug:
	$(PYTHON) -m pdb $(MAIN) $(CONFIG)

## Lint with flake8 and mypy (mandatory flags)
lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

## Stricter type checking
lint-strict:
	flake8 .
	mypy . --strict

## Remove temporary files and caches
clean:
	rm -rf __pycache__ .mypy_cache .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
