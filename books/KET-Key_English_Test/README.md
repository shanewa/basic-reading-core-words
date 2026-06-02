# Source

[Cambridge English: KET Vocabulary List](https://www.cambridgeenglish.org/images/23387-ket-schools-vocabulary-list.pdf)

将官方 PDF 放在本目录下，文件名：`23387-ket-schools-vocabulary-list.pdf`。

<!-- vocab-stats:auto-begin -->
## 词汇概览与分类

### 概览

| 词汇表 | 词条数（去重） |
|--------|----------------|
| KET词汇.md | 1239 |


以下统计基于本目录 `KET词汇.md`（`word_list` 一行一词，与 `vocab_stats.py` 中「纯英文列表」解析一致）。分类规则与 `books/新交际一二年级和基础阅读` 所用脚本相同，**按整行词条与关键词表精确匹配**，短语、带 `/` 或括号变体的行多落入「其他」。

### 主题分类（近似）

| 分类 | 数量 | 示例 |
|------|------|------|
| 动作 | 66 | bring, buy, call, catch, clean, climb, close, come, cook, dance, draw, drink, … |
| 描述 | 25 | beautiful, big, busy, clean, cold, different, fast, heavy, hot, little, long, loud, … |
| 食物 | 25 | apple, banana, bread, breakfast, butter, cake, carrot, cheese, chips, chocolate, dinner, egg, … |
| 情感 | 19 | amazing, angry, bad, cool, exciting, fun, funny, good, great, happy, hungry, love, … |
| 人称代词 | 18 | he, her, him, his, i, it, its, me, mine, my, our, she, … |
| 学校 | 17 | art, book, chair, class, classroom, desk, learn, lesson, music, paper, pen, pencil, … |
| 家居 | 17 | bath, bed, blanket, box, clock, door, garden, home, house, kitchen, room, sofa, … |
| 地点 | 15 | beach, camp, classroom, farm, forest, garden, home, house, kitchen, mountain, park, room, … |
| 玩具与物品 | 15 | ball, basketball, box, camera, card, football, glasses, guitar, kite, paper, picture, purse, … |
| 运动 | 15 | basketball, catch, climb, dance, fly, football, jump, move, play, run, sing, skateboard, … |
| 动物 | 13 | animal, bear, bird, cat, chicken, cow, dog, fish, horse, lion, monkey, pet, … |
| 天气与季节 | 13 | autumn, cloud, cold, rain, snow, spring, summer, sun, sunny, warm, weather, windy, … |
| 衣物 | 12 | clothes, coat, dress, hat, put on, raincoat, shirt, shoe, shorts, skirt, umbrella, wear |
| 身体部位 | 12 | arm, body, ear, face, foot, hair, hand, head, leg, mouth, nose, tooth |
| 时间 | 11 | clock, day, later, month, morning, night, now, o'clock, time, week, year |
| 家庭 | 8 | baby, brother, child, family, grandma, grandpa, man, sister |
| 颜色 | 7 | black, blue, colour, green, red, white, yellow |
| 交通工具 | 5 | bike, bus, car, plane, train |
| 职业 | 4 | doctor, job, nurse, queen |
| 数字 | 3 | half, number, one |
| 其他 | 951 | a, an, a.m., able, about, above, accident, across, act, … |

更新上表与分类：在仓库根目录执行  
`python src/scripts/vocab_stats.py books/KET-Key_English_Test --write-readme`
<!-- vocab-stats:auto-end -->



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

## 文件说明

- `KET词汇.md` — Cambridge KET 词表（`word_list` 一行一词，可由 `extract_ket_pdf_to_md.py` 自 PDF 生成）
- `book.json` — 词汇库与 Web 导出配置
- `Makefile` — 本地 PDF 构建入口
- `wordbank.web.json` — 由后端/脚本从 `book.json` 与词表生成（若存在）
