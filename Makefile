# 默认构建第一本书；或: make -C books/新交际一二年级

REPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PYTHON    ?= python3
BOOK      ?= 新交际一二年级

# Load proxy.env (HTTP_PROXY / HTTPS_PROXY) for make test-network and book builds
ifneq ($(wildcard $(REPO_ROOT)/proxy.env),)
include $(REPO_ROOT)/proxy.env
export HTTP_PROXY HTTPS_PROXY http_proxy https_proxy NO_PROXY
endif

.PHONY: all pdf clean help rebuild test-network web web-run web-build-wordbanks web-install help-web
all pdf clean help rebuild:
	$(MAKE) -C books/$(BOOK) $@

# 先测 Google 翻译 / 词典 API 是否可达，再决定是否开在线翻译
test-network:
	$(PYTHON) "$(REPO_ROOT)/src/scripts/test_connectivity.py"

# --- Web app targets ---

help-web:
	@echo "Web App:"
	@echo "  make web-install         -> 安装运行 Web 所需依赖"
	@echo "  make web-build-wordbanks -> 为 books/* 生成 wordbank.web.json"
	@echo "  make web-run             -> 启动本地 Web 服务 (http://127.0.0.1:5000)"
	@echo "  make web                 -> 先构建词库再启动 Web 服务"

web-install:
	$(PYTHON) -m pip install -r "$(REPO_ROOT)/requirements.txt"

web-build-wordbanks:
	$(PYTHON) "$(REPO_ROOT)/src/backend/build_wordbanks.py"

web-run:
	$(PYTHON) "$(REPO_ROOT)/src/backend/app.py"

web: web-build-wordbanks web-run

help: help-web
