override SHELL:=/bin/bash
override SHELLOPTS:=errexit:pipefail
export SHELLOPTS
override DATE:=$(shell date -u "+%Y%m%d-%H%M")


.PHONY: clean
clean: 
	rm -rf output
	rm -rf mrbaviirc*.egg-info
	find -type f -name "*.py[co]" -delete
	find -depth \( -path "*/__pycache__/*" -o -name __pycache__ \) -delete

.PHONY: tarball
tarball: NAME:=mrbaviirc-wsgi-$(shell git symbolic-ref --short HEAD)-$(shell date +%Y%m%d)-$(shell git describe --always)
tarball: OUTDIR=./output
tarball:
	mkdir -p $(OUTDIR)
	git archive --format=tar --prefix=$(NAME)/ HEAD | xz > $(OUTDIR)/$(NAME).tar.xz


