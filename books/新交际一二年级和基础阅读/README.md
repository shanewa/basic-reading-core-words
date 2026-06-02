# 外研社新交际英语 + 基础阅读400 词汇库

本目录包含三套英语词汇表，适用于小学低年级英语启蒙与阅读训练。

## 概览

| 词汇表 | 学期/分册 | 单元数 | 词条数 |
|--------|----------|--------|--------|
| 一年级词汇（上） | 一上 | 6 | 76 |
| 一年级词汇（下） | 一下 | 6 | 97 |
| **一年级小计** | | **12** | **173** |
| 二年级词汇（上） | 二上 | 6 | 67 |
| 二年级词汇（下） | 二下 | 6 | 60 |
| **二年级小计** | | **12** | **127** |
| **年级合计** | | **24** | **300** |
| 基础阅读400词汇 | — | — | 239 |

- 一年级+二年级（外研社新交际英语）合计 **300 词条**（24 个单元）
- 基础阅读400词汇收录 **239 词条**，其中 68 个与一二年级重叠，**171 个为独有词汇**

## 分类统计

以下为一年级+二年级 300 词的分类分布：

| 分类 | 数量 | 示例 |
|------|------|------|
| 动作 | 21 | go, come, look, see, eat, run, swim, sing, jump, make, open, put, read, draw, dance |
| 学校 | 18 | classroom, blackboard, desk, chair, book, pencil, teacher, English, maths, music, art |
| 动物 | 16 | bird, dog, cat, fish, rabbit, tiger, lion, bear, monkey, panda, cow, chicken, sheep, wolf |
| 描述 | 16 | big, small, tall, short, long, fast, slow, new, old, clean, tidy, strong, different, same |
| 情感 | 16 | happy, sad, angry, tired, hungry, fun, cute, cool, amazing, lucky, great, good, love |
| 时间 | 16 | Monday–Sunday, time, clock, day, week, year, now, later |
| 人称代词 | 15 | I, you, he, she, it, we, they, me, him, her, us, them, my, your, our |
| 食物 | 14 | apple, banana, rice, noodle, milk, bread, cake, egg, ice cream, lunch, dinner |
| 数字 | 13 | one–twelve, number |
| 天气与季节 | 12 | spring, summer, autumn, winter, sunny, rainy, windy, snowy, weather, season |
| 玩具与物品 | 12 | balloon, toy, robot, kite, football, basketball, photo, picture, umbrella |
| 身体部位 | 11 | face, eye, ear, nose, mouth, head, hand, arm, leg, body, hair |
| 家居 | 10 | home, house, room, bed, table, sofa, door, window, clock, box |
| 家庭 | 9 | family, mum, dad, grandpa, grandma, sister, brother, aunt, twin |
| 衣物 | 8 | clothes, shirt, skirt, coat, shoe, hat, umbrella |
| 地点 | 7 | school, classroom, home, zoo, farm, house, room |
| 职业 | 6 | doctor, nurse, driver, farmer, worker, job |
| 交通工具 | 5 | bus, car, train, plane, van |
| 颜色 | 7 | red, green, blue, black, white, yellow, colour |
| 运动 | 10 | basketball, football, swim, run, jump, kick, dance, sing, play |

基础阅读400词汇涵盖更广泛的日常生活与阅读场景，包括动物（alligator, hippo, cricket 等）、食物（chocolate, cookie, tomato 等）、衣物（boots, sandals, gloves 等）、运动（soccer, tennis, skateboard 等）等扩展词汇。

## 文件说明

- `一年级词汇.md` —— 外研社新交际英语一年级（上/下）各 6 单元，中英对照表格
- `二年级词汇.md` —— 外研社新交际英语二年级（上/下）各 6 单元，中英对照表格
- `基础阅读400词汇.md` —— 基础阅读 400 词，纯英文列表
- `book.json` —— 词汇库配置文件
- `translations.json` —— 中文翻译数据
- `ipa.json` —— 国际音标数据
- `wordbank.web.json` —— Web 端词库配置
- 词汇统计脚本：`src/scripts/vocab_stats.py`（对本目录执行 `python src/scripts/vocab_stats.py books/新交际一二年级和基础阅读/`）；KET 词表目录可用 `python src/scripts/vocab_stats.py books/KET-Key_English_Test/ --write-readme` 更新该书的统计说明。
