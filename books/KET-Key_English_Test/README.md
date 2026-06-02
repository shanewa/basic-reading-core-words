# Source

[Cambridge English: KET Vocabulary List](https://www.cambridgeenglish.org/images/23387-ket-schools-vocabulary-list.pdf)

将官方 PDF 放在本目录下，文件名：`23387-ket-schools-vocabulary-list.pdf`。

## 生成 `KET词汇.md`

在项目根目录（或已安装依赖的环境中）执行：

```bash
python src/scripts/extract_ket_pdf_to_md.py
```

可选参数：`python src/scripts/extract_ket_pdf_to_md.py /path/to.pdf /path/to/KET词汇.md`

依赖：`pypdf`（已写入仓库根目录 `requirements.txt`）。

## 在本目录生成 PDF（可选）

本目录已提供 **`Makefile`** 与 **`book.json`**（与 `books/新交际一二年级和基础阅读` 相同用法）。若要在本地生成可打印 PDF，在 WSL/Linux 下进入本目录执行：

```bash
cd books/KET-Key_English_Test
make          # 有变更才重建 PDF
make rebuild  # 强制全量重建
```

或在仓库根目录：`make BOOK=KET-Key_English_Test pdf`
