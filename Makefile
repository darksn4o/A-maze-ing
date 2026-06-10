PYTHON     := python3
VENV_DIR   := .venv
PIP        := $(VENV_DIR)/bin/pip
PYTHON_ENV := $(VENV_DIR)/bin/python

.PHONY: all venv install activate deactivate run clean 

all: venv

## Cria a virtual environment
venv:
	@echo "Loading $(VENV_DIR)..."
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "venv Created!"

## Instala dependências do requirements.txt
install: venv
	@echo "Downloading dependencs..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "dependencs installed ready to go!"

## Mostra o comando para entrar na venv
activate:
	@echo "Run this command to activate the venv:"
	@echo "source $(VENV_DIR)/bin/activate"

## Mostra o comando para sair da venv
deactivate:
	@echo "Run this command to deactivate the venv:"
	@echo "deactivate"

## Corre o projecto (ajusta o main.py ao teu ficheiro principal)
run: venv
	$(PYTHON_ENV) main.py

## Pergunta se quer limpar o terminal
clear_bash:
	@read -p "Do you want to clear the terminal? [y/N]: " ans; \
	if [ "$$ans" = "y" ] || [ "$$ans" = "Y" ]; then \
		clear; \
	fi

## Limpa a venv
clean: clear_bash
	clear
	@echo "Removing $(VENV_DIR)..."
	rm -rf $(VENV_DIR)
	@echo "All done!"

