WORKFLOW_DIR := .workflow
BUNDLE_ID := $(shell /usr/libexec/PlistBuddy -c "Print :bundleid" $(WORKFLOW_DIR)/info.plist)
CHECK_UI := $(HOME)/.gemini/config/skills/alfred-ui/scripts/check_ui.py

.PHONY: lint
lint: ## validate info.plist and Alfred UI bundle
	plutil -lint $(WORKFLOW_DIR)/info.plist
	@if [ -f "$(CHECK_UI)" ]; then python3 "$(CHECK_UI)" $(WORKFLOW_DIR); fi

.PHONY: test
test: ## run Python unit and end-to-end script tests
	python3 -m unittest discover -s tests -v

.PHONY: clean
clean: ## remove Python caches
	find $(WORKFLOW_DIR) tests -name "__pycache__" -type d -exec rm -rf {} +

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
pack: clean lint ## pack alfred workflow via ak
	ak alfred pack

.PHONY: reload
reload: ## reload workflow in Alfred 6
	osascript -e 'tell application id "com.runningwithcrayons.Alfred" to reload workflow "$(BUNDLE_ID)"'

.PHONY: help
help: ## show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_0-9-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort

.DEFAULT_GOAL := help
