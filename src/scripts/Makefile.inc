# Shared rules for vocabulary book builds.
# Include from books/<name>/Makefile after setting REPO_ROOT, OUTPUT, VOCAB.

ifndef REPO_ROOT
$(error REPO_ROOT is not set)
endif

PYTHON ?= python3
SCRIPT ?= $(REPO_ROOT)/src/scripts/generate_vocab_pdf.py
OUTPUT_NAME_SCRIPT ?= $(REPO_ROOT)/src/scripts/book_output_name.py
SCRIPT_DEPS := $(wildcard $(REPO_ROOT)/src/scripts/vocab_pdf/*.py) $(REPO_ROOT)/proxy.env
ifndef OUTPUT
OUTPUT := $(shell $(PYTHON) "$(OUTPUT_NAME_SCRIPT)" "$(CURDIR)")
endif

.PHONY: all pdf clean help rebuild

all: pdf

help:
	@echo "词汇本: $(CURDIR)"
	@echo "  make          -> $(OUTPUT)（有更新才重建）"
	@echo "  make rebuild  -> 强制重新生成 $(OUTPUT)"
	@echo "  make pdf      -> 同 make"
	@echo "  make clean    -> 删除 $(OUTPUT)"
	@echo ""
	@echo "项目根目录: make test-network  (测试 Google 翻译等连通性)"
	@echo "依赖: pip install -r $(REPO_ROOT)/requirements.txt"

pdf: $(OUTPUT)

$(OUTPUT): book.json $(VOCAB) $(SCRIPT) $(SCRIPT_DEPS)
	$(PYTHON) "$(SCRIPT)" --book-dir "$(CURDIR)"

rebuild: clean pdf

clean:
	rm -f "$(OUTPUT)"
