SHELL=/bin/bash

init:
	terraform init

plan: init
	terraform plan

apply: init
	terraform apply