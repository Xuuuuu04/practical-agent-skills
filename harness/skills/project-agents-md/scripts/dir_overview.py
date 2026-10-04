"""Print a compact overview of a project's directories for writing the directory map.

Read-only: walks the project and prints each directory up to a given depth with
its file count and total line count. It never writes anything.
"""

import argparse
import os
import sys

SKIPPED_DIRECTORIES = {
    ".git", ".hg", ".svn", ".agents", ".claude", ".codex", ".zcode",
    ".idea", ".vscode", ".venv", "venv", "env", "node_modules", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build", ".next",
    ".nuxt", "coverage", "htmlcov", ".tox",
}
TEXT_FILE_SUFFIXES = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".vue", ".java", ".go", ".rs", ".sql",
    ".md", ".yaml", ".yml", ".toml", ".json", ".html", ".css", ".scss", ".sh",
}


def count_lines(file_path):
    try:
        with open(file_path, "rb") as file:
            return sum(1 for _ in file)
    except OSError:
        return 0


def collect_directory_totals(project_root):
    totals = {}
    for current_path, directory_names, file_names in os.walk(project_root):
        directory_names[:] = sorted(
            name for name in directory_names if name not in SKIPPED_DIRECTORIES
        )
        relative_path = os.path.relpath(current_path, project_root)
        file_count = len(file_names)
        line_count = sum(
            count_lines(os.path.join(current_path, name))
            for name in file_names
            if os.path.splitext(name)[1] in TEXT_FILE_SUFFIXES
        )
        has_readme = any(name.lower() == "readme.md" for name in file_names)
        totals[relative_path] = [file_count, line_count, has_readme]

    for relative_path in sorted(totals, key=lambda path: path.count(os.sep), reverse=True):
        if relative_path == ".":
            continue
        parent_path = os.path.dirname(relative_path) or "."
        totals[parent_path][0] += totals[relative_path][0]
        totals[parent_path][1] += totals[relative_path][1]
    return totals


def print_overview(project_root, max_depth, max_output_lines):
    totals = collect_directory_totals(project_root)
    printed_lines = 0
    for relative_path in sorted(totals):
        depth = 0 if relative_path == "." else relative_path.count(os.sep) + 1
        if depth > max_depth:
            continue
        file_count, line_count, has_readme = totals[relative_path]
        name = "." if relative_path == "." else os.path.basename(relative_path) + "/"
        readme_mark = "  有 README" if has_readme else ""
        print(f"{'  ' * depth}{name}  文件 {file_count} 个，{line_count} 行{readme_mark}")
        printed_lines += 1
        if printed_lines >= max_output_lines:
            print(f"……输出超过 {max_output_lines} 行，已截断。可以用 --depth 减小层数。")
            return


def main():
    parser = argparse.ArgumentParser(description="输出项目目录概览（只读）")
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--depth", type=int, default=3, help="显示的目录层数，默认 3")
    parser.add_argument("--max-output-lines", type=int, default=200)
    arguments = parser.parse_args()
    if not os.path.isdir(arguments.project_root):
        print(f"找不到目录：{arguments.project_root}")
        sys.exit(1)
    print("说明：文件数和行数包含所有子目录；行数只统计代码和文本文件。")
    print_overview(arguments.project_root, arguments.depth, arguments.max_output_lines)


if __name__ == "__main__":
    main()
