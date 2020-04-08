

lint:
	isort -y
	black $(shell pwd)
	flake8 $(shell pwd)
	mypy $(shell pwd)
