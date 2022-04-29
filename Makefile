build:
	python -m build

deploy-test:
	twine upload --repository testpypi ./dist/*