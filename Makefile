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

.PHONY: release
release: lint test ## tag and push a release (usage: make release TAG=0.2.0)
	@if [ -z "$(TAG)" ]; then \
		echo "Usage: make release TAG=0.2.0 (or TAG=v0.2.0-rc.1)"; \
		exit 1; \
	fi
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Error: working tree is not clean. Commit or stash changes first."; \
		exit 1; \
	fi
	@tag="$(TAG)"; \
	case "$$tag" in v*) ;; *) tag="v$$tag" ;; esac; \
	if git rev-parse -q --verify "refs/tags/$$tag" >/dev/null; then \
		if [ "$$(git rev-parse "refs/tags/$$tag^{commit}")" != "$$(git rev-parse HEAD)" ]; then \
			echo "Error: tag $$tag already exists on a different commit."; \
			exit 1; \
		fi; \
		echo "Tag $$tag already points to HEAD; pushing..."; \
	else \
		git tag -a "$$tag" -m "$$tag"; \
	fi; \
	git push origin HEAD && git push origin "$$tag"

.PHONY: push
push: ## push branch, or tag & release when TAG is set (make push TAG=0.2.0)
	@if [ -n "$(TAG)" ]; then \
		$(MAKE) release TAG="$(TAG)"; \
	else \
		git push origin HEAD; \
	fi

.PHONY: help
help: ## show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_0-9-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort

.DEFAULT_GOAL := help
