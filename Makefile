.PHONY: info
info: ## show alfred workflow info
	ak alfred info

.PHONY: link
link: ## link alfred workflow
	ak alfred link

.PHONY: unlink
unlink: ## unlink alfred workflow
	ak alfred unlink

.PHONY: pack
pack: ## pack alfred workflow
	ak alfred pack

.PHONY: help
help: ## this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_0-9-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort

.PHONY: commit
commit: ## commit changes
	codegpt commit --no_confirm

.PHONY: push
push: ## push changes
	git push origin

.PHONY: changelog
changelog: ## generate changelog
	git cliff -o CHANGELOG.md

.DEFAULT_GOAL := help