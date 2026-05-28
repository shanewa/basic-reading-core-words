# Shared rules for vocabulary book builds.
# Include from books/<name>/Makefile after setting REPO_ROOT, OUTPUT, VOCAB.

ifndef REPO_ROOT
$(error REPO_ROOT is not set)
endif

PYTHON ?= python3
SCRIPT ?= $(REPO_ROOT)/scripts/generate_vocab_pdf.py
OUTPUT ?= 词汇表（打印版）.pdf

.PHONY: all pdf clean help

all: pdf

help:
	@echo "词汇本: $(CURDIR)"
	@echo "  make       -> $(OUTPUT)"
	@echo "  make pdf   -> $(OUTPUT)"
	@echo "  make clean -> remove $(OUTPUT)"
	@echo ""
	@echo "依赖: pip install -r $(REPO_ROOT)/requirements.txt"

pdf: $(OUTPUT)

$(OUTPUT): book.json $(VOCAB) $(SCRIPT)
	$(PYTHON) "$(SCRIPT)" --book-dir "$(CURDIR)"

clean:
	rm -f "$(OUTPUT)"
