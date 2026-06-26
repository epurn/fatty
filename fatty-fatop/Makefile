BINARY := fatop
PREFIX ?= $(HOME)/.local/bin

.PHONY: build tidy test install run fmt vet clean

build: tidy
	go build -o $(BINARY) .

tidy:
	go mod tidy

test:
	go test ./...

fmt:
	go fmt ./...

vet:
	go vet ./...

install: build
	mkdir -p $(PREFIX)
	install -m 0755 $(BINARY) $(PREFIX)/$(BINARY)
	@echo "installed $(PREFIX)/$(BINARY) (ensure $(PREFIX) is on your PATH)"

run: build
	./$(BINARY)

clean:
	rm -f $(BINARY)
