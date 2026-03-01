IMAGE_NAME := dotfiles-test
CONTAINER_NAME := dotfiles-test
VNC_PORT := 5901

.PHONY: build run validate vnc stop clean

build:
	podman build -t $(IMAGE_NAME) .

validate:
	podman run --rm \
		-v $(CURDIR):/dotfiles:ro \
		$(IMAGE_NAME) \
		-c "echo 'zsh started successfully'"

run:
	podman run -d --rm \
		--name $(CONTAINER_NAME) \
		-p $(VNC_PORT):5901 \
		-v $(CURDIR):/dotfiles:ro \
		$(IMAGE_NAME) vnc

vnc:
	@echo "Connecting to VNC on localhost:$(VNC_PORT)..."
	open vnc://localhost:$(VNC_PORT) 2>/dev/null || \
		echo "Open a VNC viewer and connect to localhost:$(VNC_PORT)"

stop:
	podman stop $(CONTAINER_NAME) 2>/dev/null || true

clean: stop
	podman rmi $(IMAGE_NAME) 2>/dev/null || true
