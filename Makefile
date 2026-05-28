# 默认构建第一本书；或: make -C books/新交际一二年级

BOOK ?= 新交际一二年级

.PHONY: all pdf clean help
all pdf clean help:
	$(MAKE) -C books/$(BOOK) $@
