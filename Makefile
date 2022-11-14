# Keith Briggs 2022-11-11 AIMM_simulator-2.0
# Do "make install_local" before running tests 

test:
	python3 examples/basic_test.py

run_all_examples:
	bash examples/run_all_examples.sh

install_local:
	make build
	pip3 install --force-reinstall dist/aimm_simulator-2.0.0-py3-none-any.whl

build:
	python3 -m build

doc: doc/sphinx_source/*
	sphinx-build -b html doc/sphinx_source doc/sphinx_build
