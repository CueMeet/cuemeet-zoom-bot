poetry-shell:
	@echo 'Starting poetry shell. Press Ctrl-d to exit from the shell'
	poetry shell

install:
	@if command -v poetry >/dev/null 2>&1; then \
		echo "Poetry already installed"; \
	else \
		python3 -m pip install --user poetry; \
	fi
	poetry config virtualenvs.in-project true
	poetry install

build: 
	docker build -t zoom-bot .