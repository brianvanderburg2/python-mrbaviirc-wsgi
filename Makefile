override SHELL:=/bin/bash
override SHELLOPTS:=errexit:pipefail
export SHELLOPTS
override DATE:=$(shell date -u "+%Y%m%d-%H%M")


.PHONY: check
check:

.PHONY: test
test: check

.PHONY: clean
clean: check
	rm -rf output
	rm -rf mrbaviirc.egg-info
	find -type f -name "*.py[co]" -delete
	find -type d -name "__pycache__" -delete

output: check
	mkdir -p output

.PHONY: tarball
tarball: NAME:=mrbaviirc-$(shell date +%Y%m%d)-$(shell git describe --always)
tarball: output
	git archive --format=tar --prefix=$(NAME)/ HEAD | xz > output/$(NAME).tar.xz

.PHONY: test
test: output
	python -m mrbaviirc.template.tests

.PHONY: wheel
wheel: output
	python setup.py bdist_wheel

.PHONY: dist
dist: wheel


