.PHONY: help default install uninstall

help: default


default:
	@echo "install                install kflow to /usr/bin/"
	@echo "uninstall              uninstall kflow"

install:
	ln -f kflow.py /usr/bin/kflow

uninstall:
	rm -f /usr/bin/kflow

