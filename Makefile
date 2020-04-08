

lint:
	pipenv run isort -y
	pipenv run black $(shell pwd)
	pipenv run flake8 $(shell pwd)
	pipenv run mypy $(shell pwd)
