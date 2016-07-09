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
	rm -rf test/output
	rm -rf output
	rm -rf mrbavii.egg-info
	find mrbavii -type f -name "*.py[co]" -delete
	find mrbavii -type d -name "__pycache__" -delete

output: check
	mkdir -p output

.PHONY: tarball
tarball: NAME:=mrbaviirc-$(shell date +%Y%m%d)-$(shell git describe --always)
tarball: output
	git archive --format=tar --prefix=$(NAME)/ HEAD | xz > output/$(NAME).tar.xz

.PHONY: wheel
wheel: output
	python setup.py bdist_wheel

.PHONY: dist
dist: wheel


