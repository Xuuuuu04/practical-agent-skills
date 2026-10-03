"""检查中文用词、明确标注的示例和安装前的词表一致性。"""

import argparse
import ast
from pathlib import Path
import re

# 全局规范与扫描脚本共用这份改写建议，安装前检查全局副本是否一致。
WORDING_FILE = Path(__file__).resolve().parent.parent / "references" / "wording.md"

# 取出代码中的文字：Python 按语法读取字符串，其他语言近似读取字符串和界面文字
def code_text_lines(source, suffix):
    if suffix == ".py":
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return {}
        return {node.lineno: node.value for node in ast.walk(tree)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    # 其他语言按行检查，动态拼接和跨行界面文字仍需页面检查
    pattern = re.compile(r"([\"'`])((?:\\.|(?!\1).)*?)\1|>([^<>]+)<")
    return {number: " ".join(match.group(2) or match.group(3) or ""
                            for match in pattern.finditer(line))
            for number, line in enumerate(source.splitlines(), start=1)}


# 读取晦涩用词表；缺少文件时不能声称完成了用词检查
def load_wording():
    words = {}
    with open(WORDING_FILE, encoding="utf-8") as file:
        for line in file:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not line.startswith("|") or len(cells) != 2 or cells[0] in ("词", "---"):
                continue
            for word in cells[0].split("、"):
                words[word.strip()] = cells[1]
    return words


# 代码名字和常见技术含义不算用词问题；其余匹配交给人工判断
def wording_hits(text, wording):
    prose = re.sub(r"`[^`]*`", "", text)
    prose = re.sub(r"(?:Docker|docker|容器|磁盘|文件系统)[^。；\n]{0,16}挂载", "", prose)
    prose = re.sub(r"(?:输入框|文本框|光标|焦点)[^。；\n]{0,12}聚焦", "", prose)
    return [f'"{word}"（可换成：{plain}）' for word, plain in wording.items() if word in prose]


# 用词只产生提示，是否属于业务用语、引用或技术含义需要人工判断
def wording_finding(path, number, prose, origin, wording):
    hits = wording_hits(prose, wording)
    if not hits:
        return []
    return [("待人工检查", f"{path}:{number}：{origin([number])}用词提示：{'、'.join(hits)}")]


# 示例只跳过中文匹配；成对标记写错时停止检查，避免误跳过后面的正文。
def example_lines(lines):
    pattern = re.compile(r"^(?:<!-- |# |// )wording:(examples|list):(start|end)(?: -->)?$")
    ignored, active = set(), None
    for number, line in enumerate(lines, start=1):
        match = pattern.fullmatch(line.strip())
        if match:
            kind, action = match.groups()
            if action == "start" and active is None:
                active = kind
            elif action == "end" and active == kind:
                active = None
            else:
                raise ValueError(f"第 {number} 行用词示例标记不成对")
            ignored.add(number)
        elif active:
            ignored.add(number)
    if active:
        raise ValueError("用词示例缺少结束标记")
    return ignored


# 安装前比较全局词表与详细词表，只允许符号名称与符号本身的表示差异。
def check_wording_list(agents_path):
    source = Path(agents_path).read_text(encoding="utf-8")
    example_lines(source.splitlines())
    start, end = "<!-- wording:list:start -->", "<!-- wording:list:end -->"
    if source.count(start) != 1 or source.count(end) != 1:
        raise ValueError("全局规范需要且只能有一对词表标记")
    content = source.split(start, 1)[1].split(end, 1)[0].strip().rstrip("。")
    content = content.replace("，以及直角引号", "、「、」")
    actual = {word.strip() for word in content.split("、")}
    expected = set(load_wording())
    if not expected:
        raise ValueError("详细词表没有有效内容")
    missing, extra = sorted(expected - actual), sorted(actual - expected)
    if missing or extra:
        raise ValueError(f"词表不一致；全局缺少：{missing}；全局多出：{extra}")
    return len(expected)


# 安装脚本调用这个入口；失败发生在替换任何已安装文件之前。
def main():
    parser = argparse.ArgumentParser(description="检查全局规范与详细词表是否一致")
    parser.add_argument("--agents", required=True)
    args = parser.parse_args()
    try:
        count = check_wording_list(args.agents)
    except (OSError, ValueError) as error:
        parser.exit(1, f"用词检查未完成：{error}\n")
    print(f"中文词表一致，共 {count} 个词和符号。")


if __name__ == "__main__":
    main()
