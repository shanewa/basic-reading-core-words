# 词汇本目录

每个子文件夹是一本独立的词汇本，自带 `Makefile` 与 `book.json`。

## 生成 PDF

若需使用 **Google 在线翻译**（`book.json` 里 `translate_missing: true`），请先测连通性。

项目根目录的 `proxy.env` 已配置公司代理（`make` 会自动加载）。也可在 shell 里自行 `export HTTP_PROXY=...`。

```bash
# 在项目根目录
make test-network
```

通过后再：

```bash
cd books/新交际一二年级和基础阅读
make          # 源文件有改动时才重建 PDF
make rebuild  # 强制重新生成（PDF 已存在但想全量重做时用）
```

## 新增一本词汇本

1. 复制 `新交际一二年级和基础阅读` 文件夹并重命名，例如 `books/我的词汇本/`
2. 放入 `*.md` 词汇文件
3. 编辑 `book.json`（输出文件名、来源列表与解析器）
4. 在 `Makefile` 里更新 `VOCAB` 文件列表
5. 在该目录执行 `make`

### book.json 说明

| 字段 | 含义 |
|------|------|
| `name` | 显示用名称（日志） |
| `output` | PDF 文件名；`auto`（默认）= 用所有 `sources[].path` 的 md 主文件名用 `_` 连接，如 `一年级词汇_二年级词汇_基础阅读400词汇.pdf` |
| `seed` | 打乱顺序的随机种子 |
| `sources[].path` | 词汇 md 文件（相对本目录） |
| `sources[].parser` | `grade_table`（单元表格）或 `word_list`（每行一词） |
| `sources[].label` | 出处列中的书名标签 |
| `translate_missing` | `true` 时对缺中文词条调用在线翻译（默认 `false`） |
| `fetch_ipa` | `true` 且能联网时，音标**先**查 free dictionary API（Wiktionary 美式，例 *alligator* `/ˈælɪɡeɪtɚ/`，更接近常见「美音」教材）；失败再回退 eng-to-ipa（CMU，例 *alligator* 常为 `/ˈæləˌgeɪtər/`）。`false` 则仅用 CMU。音节间的 `.` 在写入前会去掉以便阅读。音标列格式如 `b-ee-f  /biːf/` |

### translations.json

与 `book.json` 同目录，格式 `{"english": "中文", ...}`，用于无中文出处的词条（如「基础阅读400」）。**推荐离线构建，不依赖 Google 翻译。**

在线翻译失败时可把 `translate_missing` 设为 `false`，并维护此文件。也可运行：

```bash
python ../../src/scripts/generate_vocab_pdf.py --book-dir . --offline
```
