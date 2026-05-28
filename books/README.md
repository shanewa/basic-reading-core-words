# 词汇本目录

每个子文件夹是一本独立的词汇本，自带 `Makefile` 与 `book.json`。

## 生成 PDF

```bash
cd books/新交际一二年级
make
```

## 新增一本词汇本

1. 复制 `新交际一二年级` 文件夹并重命名，例如 `books/我的词汇本/`
2. 放入 `*.md` 词汇文件
3. 编辑 `book.json`（输出文件名、来源列表与解析器）
4. 在 `Makefile` 里更新 `VOCAB` 文件列表
5. 在该目录执行 `make`

### book.json 说明

| 字段 | 含义 |
|------|------|
| `name` | 显示用名称（日志） |
| `output` | 生成的 PDF 文件名 |
| `seed` | 打乱顺序的随机种子 |
| `sources[].path` | 词汇 md 文件（相对本目录） |
| `sources[].parser` | `grade_table`（单元表格）或 `word_list`（每行一词） |
| `sources[].label` | 出处列中的书名标签 |
