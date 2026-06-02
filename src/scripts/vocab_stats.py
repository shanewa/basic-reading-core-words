#!/usr/bin/env python3
"""统计词汇库中英文词汇的数量和分类分布。

用法:
  python vocab_stats.py <词汇目录路径> [--write-readme]

  目录中应包含以下文件（按命名匹配）：
    - *一年级词汇*.md  (外研社新交际英语一年级，中英表格格式)
    - *二年级词汇*.md  (外研社新交际英语二年级，中英表格格式)
    - *基础阅读*词汇*.md 或 *400*词汇*.md  (基础阅读400词，纯英文列表格式)
    - KET词汇.md  (Cambridge KET 词表，纯英文列表，与 word_list 解析器一致)

  示例:
  python vocab_stats.py books/新交际一二年级和基础阅读/
  python vocab_stats.py books/KET-Key_English_Test/
  python vocab_stats.py books/KET-Key_English_Test/ --write-readme
    将「概览 + 分类统计」写入该目录 README.md（<!-- vocab-stats:auto-begin/end --> 块内）。
"""

import argparse
import re
import sys
from pathlib import Path


# —— 分类关键词 ——
CATEGORIES = {
    "动作": [
        "open", "close", "look", "see", "hear", "listen", "say", "tell", "talk",
        "go", "come", "stop", "sit", "sit down", "stand", "put", "put on", "get",
        "give", "take", "bring", "find", "make", "do", "have", "want", "like",
        "eat", "drink", "feed", "help", "try", "use", "buy", "grow", "paint",
        "draw", "wash", "brush", "clean", "dig", "share", "travel", "call",
        "bark", "bite", "sting", "sleep", "wake", "wait", "stay", "live",
        "read", "run", "swim", "jump", "kick", "dance", "sing", "fly", "climb",
        "catch", "chase", "walk", "move", "play", "touch", "smell", "feel",
        "learn", "teach", "understand", "watch", "bake", "set the table",
        "cook", "show", "meet", "know", "think", "worry",
    ],
    "动物": [
        "bird", "dog", "cat", "fish", "rabbit", "tiger", "lion", "bear",
        "monkey", "panda", "wolf", "cow", "chicken", "sheep", "horse",
        "alligator", "rat", "hippo", "puppy", "bee", "butterfly", "frog",
        "spider", "cricket", "bug", "snap", "pet", "animal",
    ],
    "食物": [
        "apple", "banana", "rice", "noodle", "milk", "bread", "cake", "sweet",
        "egg", "chocolate", "cookie", "candy", "ice cream", "jelly bean",
        "cheese", "jam", "grapes", "pear", "carrot", "tomato", "potato",
        "bean", "lettuce", "ketchup", "meat", "butter", "lunch", "dinner",
        "breakfast", "food", "chips", "lollipop", "fruit", "delicious",
        "yummy", "water", "ice",
    ],
    "颜色": [
        "red", "green", "blue", "black", "white", "yellow", "colour", "color",
    ],
    "身体部位": [
        "face", "eye", "ear", "nose", "mouth", "head", "hand", "arm", "leg",
        "foot", "feet", "body", "hair", "lips", "teeth", "tooth",
    ],
    "数字": [
        "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "ten", "eleven", "twelve", "number", "half",
    ],
    "家庭": [
        "family", "mum", "mom", "dad", "grandpa", "grandma", "sister",
        "brother", "aunt", "child", "children", "twin", "man", "baby",
    ],
    "学校": [
        "classroom", "blackboard", "desk", "chair", "teacher", "schoolbag",
        "pencil case", "pencil", "book", "class", "in class", "English",
        "maths", "music", "PE", "art", "student", "pen", "read", "school",
        "learn", "teach", "paper", "lesson",
    ],
    "衣物": [
        "clothes", "shirt", "skirt", "coat", "shoe", "hat", "dress", "socks",
        "boots", "pants", "shorts", "gloves", "raincoat", "sandals", "wear",
        "put on", "umbrella",
    ],
    "天气与季节": [
        "weather", "windy", "snowy", "rainy", "sunny", "spring", "summer",
        "autumn", "winter", "season", "snow", "sun", "cold", "warm", "rain",
        "cloud",
    ],
    "交通工具": [
        "bus", "car", "train", "plane", "boat", "van", "elevator", "bike",
    ],
    "职业": [
        "job", "driver", "farmer", "worker", "doctor", "nurse", "queen",
    ],
    "运动": [
        "basketball", "football", "swim", "run", "jump", "kick", "dance",
        "sing", "soccer", "tennis", "walk", "climb", "fly", "play", "move",
        "catch", "chase", "inline skates", "skateboard",
    ],
    "情感": [
        "happy", "sad", "angry", "tired", "hungry", "fun", "love", "cute",
        "cool", "amazing", "lucky", "great", "good", "bad", "worry", "sorry",
        "feeling", "scary", "surprise", "exciting", "funny", "sick",
    ],
    "家居": [
        "home", "bed", "table", "sofa", "room", "house", "door", "window",
        "kitchen", "bath", "stairs", "wall", "garden", "yard", "blanket",
        "broom", "clock", "box", "log", "ground", "top",
    ],
    "人称代词": [
        "i", "you", "he", "she", "it", "we", "they", "me", "us", "them",
        "him", "her", "his", "my", "your", "our", "its", "mine",
    ],
    "时间": [
        "time", "clock", "day", "week", "month", "year", "monday", "tuesday",
        "wednesday", "thursday", "friday", "saturday", "sunday", "every day",
        "night", "morning", "later", "now", "o'clock", "good night",
    ],
    "描述": [
        "big", "small", "tall", "short", "long", "fast", "slow", "new", "old",
        "clean", "tidy", "busy", "strong", "heavy", "loud", "hot", "cold",
        "different", "same", "safe", "cozy", "sticky", "little", "well",
        "nice", "beautiful", "pretty",
    ],
    "地点": [
        "school", "classroom", "home", "house", "room", "zoo", "farm",
        "beach", "mountain", "forest", "desert", "park", "store", "garden",
        "yard", "kitchen", "london", "camp",
    ],
    "玩具与物品": [
        "balloon", "photo", "picture", "toy", "robot", "kite", "ball", "gift",
        "camera", "guitar", "skateboard", "basketball", "football",
        "inline skates", "boat", "card", "box", "paper", "umbrella", "glasses",
        "purse", "helmet", "broom", "doll", "puzzle",
    ],
}


def parse_textbook_table(filepath: str) -> dict[str, list[str]]:
    """解析外研社新交际英语词汇表（中英对照表格格式）。"""
    semesters: dict[str, list[str]] = {"一上": [], "一下": [], "二上": [], "二下": [], "全部": []}
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.strip().split("\n")
    current = None

    for line in lines:
        line = line.strip()
        if line.startswith("## 一上"):
            current = "一上"
        elif line.startswith("## 一下"):
            current = "一下"
        elif line.startswith("## 二上"):
            current = "二上"
        elif line.startswith("## 二下"):
            current = "二下"
        elif (
            line.startswith("|")
            and "|" in line[1:]
            and not line.startswith("|------")
            and not line.startswith("| 英文")
            and not line.startswith("| English")
        ):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if parts and current:
                word = parts[0].lower()
                # 跳过括号注释中的替换形式，如 "foot (feet)" -> "foot"
                word = re.sub(r"\s*\(.*?\)", "", word)
                semesters[current].append(word)
                semesters["全部"].append(word)

    return semesters


def parse_flat_list(filepath: str) -> list[str]:
    """解析纯英文列表格式（基础阅读400词汇）。"""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.read().strip().split("\n")
    return [line.strip().lower() for line in lines if line.strip() and not line.startswith("#")]


def count_units(filepath: str) -> int:
    with open(filepath, "r", encoding="utf-8") as f:
        return len(re.findall(r"^### Unit \d", f.read(), re.M))


def find_files(directory: str) -> dict[str, str]:
    """在目录中按文件名模式匹配词汇文件。"""
    p = Path(directory)
    result: dict[str, str] = {}
    for f in p.glob("*.md"):
        name = f.name
        if "一年级" in name and "词汇" in name:
            result["一年级词汇"] = str(f)
        elif "二年级" in name and "词汇" in name:
            result["二年级词汇"] = str(f)
        elif ("基础阅读" in name and "词汇" in name) or ("400" in name and "词汇" in name):
            result["基础阅读400词汇"] = str(f)
        elif name == "KET词汇.md":
            result["KET词汇"] = str(f)
    return result


STATS_BEGIN = "<!-- vocab-stats:auto-begin -->"
STATS_END = "<!-- vocab-stats:auto-end -->"
README_ANCHOR = "## 生成"


def _example_cell(words: list[str], limit: int = 12) -> str:
    parts = words[:limit]
    s = ", ".join(parts)
    if len(words) > limit:
        s += ", …"
    return s.replace("|", "\\|")


def format_ket_readme_section(words: set[str], *, raw_lines: int) -> str:
    """生成与新交际 README 风格相近的 Markdown 片段（不含外层注释标记）。"""
    cats = categorize(words, CATEGORIES)
    unique = len(words)
    dup_note = ""
    if raw_lines != unique:
        dup_note = f"\n\n- 列表行数 **{raw_lines}**，去重后 **{unique}** 词条（行级重复已合并统计）。"
    rows: list[tuple[str, int, str]] = []
    for name, wlist in cats.items():
        if name == "其他":
            continue
        if wlist:
            rows.append((name, len(wlist), _example_cell(wlist)))
    rows.sort(key=lambda x: (-x[1], x[0]))
    other_n = len(cats.get("其他", []))
    rows.append(("其他", other_n, _example_cell(cats.get("其他", []), limit=8)))

    table = ["| 分类 | 数量 | 示例 |", "|------|------|------|"]
    for cat_name, n, ex in rows:
        table.append(f"| {cat_name} | {n} | {ex} |")
    table_s = "\n".join(table)

    return (
        "## 词汇概览与分类\n\n"
        "### 概览\n\n"
        "| 词汇表 | 词条数（去重） |\n"
        "|--------|----------------|\n"
        f"| KET词汇.md | {unique} |\n"
        f"{dup_note}\n\n"
        "以下统计基于本目录 `KET词汇.md`（`word_list` 一行一词，与 `vocab_stats.py` 中「纯英文列表」解析一致）。"
        "分类规则与 `books/新交际一二年级和基础阅读` 所用脚本相同，**按整行词条与关键词表精确匹配**，"
        "短语、带 `/` 或括号变体的行多落入「其他」。\n\n"
        "### 主题分类（近似）\n\n"
        f"{table_s}\n\n"
        "更新上表与分类：在仓库根目录执行  \n"
        "`python src/scripts/vocab_stats.py books/KET-Key_English_Test --write-readme`\n"
    )


def merge_readme_stats(readme_path: Path, section: str) -> None:
    """将 section 写入 README 中 STATS 块；若无标记则在 `## 生成` 之前插入。"""
    block = f"{STATS_BEGIN}\n{section.rstrip()}\n{STATS_END}\n"
    text = readme_path.read_text(encoding="utf-8")
    if STATS_BEGIN in text and STATS_END in text:
        pre, _, rest = text.partition(STATS_BEGIN)
        _, _, post = rest.partition(STATS_END)
        new_text = pre + block + post
    elif README_ANCHOR in text:
        new_text = text.replace(README_ANCHOR, block + "\n" + README_ANCHOR, 1)
    else:
        new_text = text.rstrip() + "\n\n" + block
    readme_path.write_text(new_text, encoding="utf-8")


def print_ket_report(ket_path: str) -> tuple[set[str], int]:
    raw = parse_flat_list(ket_path)
    words = set(raw)
    print(f"\nKET 词汇表 ({Path(ket_path).name}): 列表行 {len(raw)}，唯一词 {len(words)}")
    print("\n--- KET 分类统计 ---")
    cats = categorize(words, CATEGORIES)
    for cat_name, wlist in sorted(cats.items(), key=lambda x: (-len(x[1]), x[0])):
        if cat_name == "其他":
            print(f"\n{cat_name}: {len(wlist)} 词")
        elif len(wlist) >= 1:
            preview = ", ".join(wlist[:8])
            tail = " …" if len(wlist) > 8 else ""
            print(f"  {cat_name}: {len(wlist)} 词  [{preview}{tail}]")
    return words, len(raw)


def categorize(words: set[str], categories: dict[str, list[str]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    all_categorized: set[str] = set()
    for cat_name, keywords in categories.items():
        matched = [w for w in words if w in keywords]
        if matched:
            result[cat_name] = sorted(matched)
            all_categorized.update(matched)
    result["其他"] = sorted(words - all_categorized)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="词汇表统计（新交际 / KET 等）")
    parser.add_argument("directory", nargs="?", default=".", help="含词汇 .md 的目录")
    parser.add_argument(
        "--write-readme",
        action="store_true",
        help="KET 专用：将概览与分类表写入该目录 README.md（自动块内）",
    )
    args = parser.parse_args()
    directory = args.directory
    files = find_files(directory)

    if not files:
        print(f"错误：在目录 '{directory}' 中未找到词汇文件")
        print("文件名应包含：一年级词汇、二年级词汇、基础阅读/400词汇，或 KET词汇.md")
        sys.exit(1)

    ket_only = "KET词汇" in files and not (
        {"一年级词汇", "二年级词汇", "基础阅读400词汇"} & set(files.keys())
    )

    if ket_only:
        print("=" * 60)
        print("KET 词汇库统计报告")
        print("=" * 60)
        path_ket = files["KET词汇"]
        words, raw_len = print_ket_report(path_ket)
        if args.write_readme:
            readme = Path(directory).resolve() / "README.md"
            section = format_ket_readme_section(words, raw_lines=raw_len)
            merge_readme_stats(readme, section)
            print(f"\n已写入: {readme}")
        print()
        return

    if args.write_readme:
        print("提示：--write-readme 仅适用于仅含 KET词汇.md 的目录，已忽略。", file=sys.stderr)

    # —— 解析各文件 ——
    g1 = g2 = b400 = None
    g1_sem = g2_sem = {}

    if "一年级词汇" in files:
        g1_sem = parse_textbook_table(files["一年级词汇"])
        g1 = g1_sem["全部"]
    if "二年级词汇" in files:
        g2_sem = parse_textbook_table(files["二年级词汇"])
        g2 = g2_sem["全部"]
    if "基础阅读400词汇" in files:
        b400 = parse_flat_list(files["基础阅读400词汇"])

    # —— 输出统计 ——
    print("=" * 60)
    print("词汇库统计报告")
    print("=" * 60)

    total_g12 = (len(g1) if g1 else 0) + (len(g2) if g2 else 0)
    g12_set = set(g1 or []) | set(g2 or [])
    b400_set = set(b400 or [])

    print(f"\n一年级+二年级教材词汇合计: {total_g12} 词条 ({len(g12_set)} 唯一词)")
    if b400:
        print(f"基础阅读400词汇: {len(b400)} 词条")

    # 分册明细
    if g1_sem:
        print("\n--- 一年级分册 ---")
        for sem in ["一上", "一下"]:
            print(f"  {sem}: {len(g1_sem[sem])} 词条")
        if "一年级词汇" in files:
            print(f"  单元数: {count_units(files['一年级词汇'])}")

    if g2_sem:
        print("\n--- 二年级分册 ---")
        for sem in ["二上", "二下"]:
            print(f"  {sem}: {len(g2_sem[sem])} 词条")
        if "二年级词汇" in files:
            print(f"  单元数: {count_units(files['二年级词汇'])}")

    # 重叠
    if b400 and g12_set:
        overlap = g12_set & b400_set
        print(f"\n教材与基础阅读400重叠词条: {len(overlap)}")
        print(f"基础阅读400独有词条: {len(b400_set - g12_set)}")

    # 分类统计（教材）
    if g12_set:
        print("\n--- 教材词汇分类统计 ---")
        cats = categorize(g12_set, CATEGORIES)
        for cat_name, words in cats.items():
            if cat_name == "其他":
                print(f"\n{cat_name}: {len(words)} 词")
            else:
                print(f"  {cat_name}: {len(words)} 词  [{', '.join(words[:8])}{',' if len(words) > 8 else ''} ...]" if len(words) > 8 else f"  {cat_name}: {len(words)} 词  [{', '.join(words)}]")

    # 分类统计（基础阅读400）
    if b400_set:
        print("\n--- 基础阅读400分类统计 ---")
        cats = categorize(b400_set, CATEGORIES)
        for cat_name, words in cats.items():
            if cat_name == "其他":
                print(f"\n{cat_name}: {len(words)} 词")
            elif len(words) >= 3:
                print(f"  {cat_name}: {len(words)} 词  [{', '.join(words[:8])}{',' if len(words) > 8 else ''} ...]" if len(words) > 8 else f"  {cat_name}: {len(words)} 词  [{', '.join(words)}]")

    print()


if __name__ == "__main__":
    main()
