.PHONY: help default install uninstall

help: default

WORKDIR=$(shell pwd)

default:
	@echo "install                install kflow to /usr/bin/"
	@echo "uninstall              uninstall kflow"
	@echo "neo4j-daemon           start neo4j daemon"
	@echo "neo4j-destroy          destroy neo4j container"

install:
	ln -f kflow.py /usr/bin/kflow

uninstall:
	rm -f /usr/bin/kflow

pull-image:
	docker pull neo4j:enterprise
	#docker pull neo4j:latest


neo4j-daemon:
	# https://neo4j.com/developer/docker-run-neo4j/
	docker run -d \
    --name neo4j \
    -p7474:7474 -p7687:7687 \
    -v $(WORKDIR)/neo4j/data:/data \
    -v $(WORKDIR)/neo4j/logs:/logs \
    -v $(WORKDIR)/neo4j/import:/var/lib/neo4j/import \
    -v $(WORKDIR)/neo4j/plugins:/plugins \
    -v $(WORKDIR):/kernel \
    -e NEO4J_ACCEPT_LICENSE_AGREEMENT=yes \
    -e NEO4J_AUTH="neo4j/yifengyou" \
    neo4j:enterprise
	@docker ps -a



neo4j-destroy:
	@docker container rm --force neo4j
	@docker container prune -f
	@rm -rf neo4j
	@echo "neo4j-destroy done!"



neo4j-attach:
	@docker exec -it neo4j /bin/bash
	@echo "neo4j-attach done!"




