"""Check a project-level AGENTS.md against the format of the project-agents-md skill.

Read-only. Checks: line limit, required sections, whether paths written in backticks
exist, and whether log-style lines (dates, change records) have crept in.
Exit code 0 when everything passes, 1 otherwise.
"""

import argparse
import os
import re
import sys

REQUIRED_SECTIONS = [
    "这个项目是什么",
    "怎么运行",
    "目录地图",
    "去哪里找",
    "数据怎么流动",
    "本项目的约定",
    "不要做的事",
    "已知的坑",
]
LOG_STYLE_PATTERNS = [
    (re.compile(r"^\s*[-*]?\s*\d{4}[-/.]\d{1,2}[-/.]\d{1,2}"), "以日期开头，像是改动记录"),
    (re.compile(r"更新记录|修改记录|变更记录|本次修改|本次更新|最近更新|changelog", re.IGNORECASE),
     "像是改动记录"),
    (re.compile(r"^\s*[-*]?\s*(已完成|进行中|待办)[：:]"), "像是任务进度，项目说明只保留长期有效的信息"),
]
BACKTICK_TEXT = re.compile(r"`([^`\n]+)`")
PATH_LIKE = re.compile(r"^[\w.\-/]+$")


def looks_like_path(text):
    if not PATH_LIKE.match(text) or text.startswith("-") or "/" not in text:
        return False
    return not text.startswith(("http", "www."))


def check_file(project_root, max_lines):
    agents_path = os.path.join(project_root, "AGENTS.md")
    if not os.path.isfile(agents_path):
        return [f"找不到 {agents_path}。第一次创建请按 Skill 里的“第一次创建”步骤做。"]

    with open(agents_path, encoding="utf-8") as file:
        lines = file.read().splitlines()
    problems = []

    if len(lines) > max_lines:
        problems.append(f"全文 {len(lines)} 行，超过上限 {max_lines} 行。先压缩目录地图和已知的坑。")

    headings = [line.lstrip("#").strip() for line in lines if line.startswith("## ")]
    for section in REQUIRED_SECTIONS:
        if section not in headings:
            problems.append(f"缺少小节：## {section}（没有内容时写“暂无”）")
    extra_sections = [heading for heading in headings if heading not in REQUIRED_SECTIONS]
    for heading in extra_sections:
        problems.append(f"出现了固定格式以外的小节：## {heading}。请把内容并入已有小节。")

    for line_number, line in enumerate(lines, start=1):
        for pattern, reason in LOG_STYLE_PATTERNS:
            if pattern.search(line):
                problems.append(f"第 {line_number} 行{reason}：{line.strip()[:60]}")
                break
        for text in BACKTICK_TEXT.findall(line):
            candidate = text.rstrip("/")
            if looks_like_path(candidate) and not os.path.exists(os.path.join(project_root, candidate)):
                problems.append(f"第 {line_number} 行写到的路径不存在：{text}")
    return problems


def main():
    parser = argparse.ArgumentParser(description="检查项目级 AGENTS.md（只读）")
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--max-lines", type=int, default=150)
    arguments = parser.parse_args()

    problems = check_file(arguments.project_root, arguments.max_lines)
    if problems:
        print(f"发现 {len(problems)} 处需要修改：")
        for problem in problems:
            print(f"- {problem}")
        sys.exit(1)
    print("AGENTS.md 检查通过。")


if __name__ == "__main__":
    main()
