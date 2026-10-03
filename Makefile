SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

CONTAINER_ENGINE ?= podman
IMAGE := dotfiles-test
CONTAINER_NAME := dotfiles-test
VNC_PORT := 5901

.PHONY: ci lint lint-shell lint-zsh unit integration integration-native image run vnc stop clean

ci: lint unit integration

lint: lint-shell lint-zsh

# Every tracked file with a bash shebang or a .sh/.bash suffix. Templates are not shell before
# rendering, and quick-access/ holds symlinks to files that are already covered.
lint-shell:
	git ls-files -z -- ':!quick-access' ':!*.tmpl' | while IFS= read -r -d '' file; do \
	  if [[ $$file == *.sh || $$file == *.bash ]] || head -n 1 "$$file" | grep -qE '^#!.*bash'; then printf '%s\0' "$$file"; fi; \
	done | xargs -0 shellcheck

lint-zsh:
	git ls-files -z -- 'home/**/*.zsh' | xargs -0 -n 1 zsh -n

unit:
	uv run --locked pytest -m "not integration"
	node --test tests/

integration:
	uv run --locked pytest tests/integration/test_apply_container.py

integration-native:
	uv run --locked pytest tests/integration/test_apply_native.py

image:
	$(CONTAINER_ENGINE) build --target base -t $(IMAGE):base .

run:
	$(CONTAINER_ENGINE) build --target vnc -t $(IMAGE):vnc .
	$(CONTAINER_ENGINE) run -d --rm \
		--name $(CONTAINER_NAME) \
		-p $(VNC_PORT):5901 \
		-v $(CURDIR):/dotfiles:ro \
		$(IMAGE):vnc vnc

vnc:
	@echo "Connecting to VNC on localhost:$(VNC_PORT)..."
	open vnc://localhost:$(VNC_PORT) 2>/dev/null || \
		echo "Open a VNC viewer and connect to localhost:$(VNC_PORT)"

stop:
	$(CONTAINER_ENGINE) stop $(CONTAINER_NAME) 2>/dev/null || true

clean: stop
	$(CONTAINER_ENGINE) rmi $(IMAGE):base $(IMAGE):vnc 2>/dev/null || true
