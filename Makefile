# 默认构建第一本书；或: make -C books/新交际一二年级

REPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PYTHON    ?= python3
BOOK      ?= 新交际一二年级

# Load proxy.env (HTTP_PROXY / HTTPS_PROXY) for make test-network and book builds
ifneq ($(wildcard $(REPO_ROOT)/proxy.env),)
include $(REPO_ROOT)/proxy.env
export HTTP_PROXY HTTPS_PROXY http_proxy https_proxy NO_PROXY
endif

.PHONY: all pdf clean help rebuild test-network
all pdf clean help rebuild:
	$(MAKE) -C books/$(BOOK) $@

# 先测 Google 翻译 / 词典 API 是否可达，再决定是否开在线翻译
test-network:
	$(PYTHON) "$(REPO_ROOT)/scripts/test_connectivity.py"
