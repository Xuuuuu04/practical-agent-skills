"""只读检查改动或指定包，分别报告确定问题和待人工判断的提示。"""

import argparse
import ast
import os
import re
import subprocess
import sys

from wording_checks import code_text_lines, example_lines, load_wording, wording_finding

# 检查长度、注释和用词的代码文件类型
CODE_SUFFIXES = {".py", ".js", ".ts", ".tsx", ".jsx", ".vue", ".java", ".go"}
# 只检查长度和用词的文档类型
DOC_SUFFIXES = {".md"}
# shell 脚本，按脚本长度上限检查
SCRIPT_SUFFIXES = {".sh"}
# SQL 文件，按单条语句的长度检查
SQL_SUFFIXES = {".sql"}
# 用 # 写注释的文件类型
HASH_COMMENT_SUFFIXES = {".py", ".sh"}
# 匹配没做完的事项标记
TODO_PATTERN = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
# 匹配"看起来像代码"的注释，用来发现被注释掉的代码
COMMENTED_CODE_PATTERN = re.compile(
    r"^(def |class |import |from \S+ import |return\b|if .*:\s*$|for .*:\s*$|while .*:\s*$|"
    r"print\(|await |const |let |var |function |\w+(\.\w+)*\s*=\s*[^=]|\w+(\.\w+)*\(.*\)\s*;?\s*$)"
)
# 只匹配明确带记录格式的注释，不把“更新订单状态”等功能说明当成历史
CHANGE_NOTE_PATTERN = re.compile(
    r"^(?:(?:修改|修复|改动|更新|新增|删除|调整)(?:记录)?[：:]|(?:fix|change|update)[：:])",
    re.IGNORECASE,
)
# 匹配 JavaScript 里捕获异常后什么都不做
BROAD_CATCH_PATTERN = re.compile(r"catch\s*\(\s*\w*\s*\)\s*\{\s*\}|catch\s*\{\s*\}")


# 运行一条 git 命令并返回输出，失败时抛出带原因的错误
def run_git(repository, arguments):
    result = subprocess.run(
        ["git", "-C", repository, *arguments],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git 命令失败")
    return result.stdout


# 列出和起点相比有改动的文件，以及每个文件是新增、修改、移动还是删除
def list_changed_files(repository, base):
    changed = {}
    for line in run_git(repository, ["diff", "--name-status", "-M", base]).splitlines():
        parts = line.split("\t")
        status = parts[0][0]
        path = parts[-1]
        changed[path] = {"A": "新增", "D": "删除", "R": "移动"}.get(status, "修改")
    for path in run_git(repository, ["ls-files", "--others", "--exclude-standard"]).splitlines():
        changed[path] = "新增"
    return {path: status for path, status in changed.items() if not path.startswith(".agent/")}


# 列出指定包目录下的全部文件（已跟踪的和还没加入 git 的），整理一个包之前用它看现状
def list_package_files(repository, package):
    output = run_git(repository, ["ls-files", "--cached", "--others", "--exclude-standard", "--", package])
    return {path: "范围内" for path in output.splitlines() if not path.startswith(".agent/")}


# 找出一个文件里被这次改动动过的行号，用来区分"本次改动"和"原有"的问题
def changed_line_numbers(repository, base, path):
    diff_text = run_git(repository, ["diff", "-U0", base, "--", path])
    numbers = set()
    for match in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", diff_text, re.MULTILINE):
        start = int(match.group(1))
        length = int(match.group(2) or 1)
        numbers.update(range(start, start + length))
    return numbers


# 读取文件在起点提交里的内容；起点里没有这个文件时返回 None
def read_base_version(repository, base, path):
    try:
        return run_git(repository, ["show", f"{base}:{path}"])
    except RuntimeError:
        return None


# 取出一行里的注释文字；这一行不是注释时返回 None
def comment_text(line, suffix):
    stripped = line.strip()
    if suffix in HASH_COMMENT_SUFFIXES:
        return stripped[1:].strip() if stripped.startswith("#") else None
    if stripped.startswith("//"):
        return stripped[2:].strip()
    return None


# 统计 Python 文件里每个函数的名字、起始行号和行数
def python_function_lengths(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return [
        (node.name, node.lineno, node.end_lineno - node.lineno + 1)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


# 找出没有注释的 Python 类和函数：要么有说明文字，要么紧挨着上一行有 # 注释
def python_missing_comments(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    lines = source.splitlines()
    missing = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if ast.get_docstring(node):
            continue
        # 有装饰器时，注释应该写在装饰器上面
        first_line = min([node.lineno] + [decorator.lineno for decorator in node.decorator_list])
        line_above = lines[first_line - 2].strip() if first_line >= 2 else ""
        if not line_above.startswith("#"):
            kind = "类" if isinstance(node, ast.ClassDef) else "函数"
            missing.append((kind, node.name, node.lineno))
    return missing


# 检查文档长度与正文；示例代码不作为自然语言，避免修改代码名字
def inspect_document(path, lines, origin, limits, wording):
    findings = []
    if len(lines) > limits.max_doc_lines:
        findings.append((origin(range(1, len(lines) + 1)),
                         f"{path}：文档 {len(lines)} 行，超过 {limits.max_doc_lines}，考虑压缩"))
    fence = None
    ignored = example_lines(lines)
    for number, line in enumerate(lines, start=1):
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            if fence is None:
                fence = marker.group(1)[0]
            elif marker.group(1)[0] == fence:
                fence = None
            continue
        if fence is None and number not in ignored:
            findings += wording_finding(path, number, line, origin, wording)
    return findings


# 检查 SQL 文件：每条语句（以分号结尾）的行数，是近似值，不解析存储过程
def inspect_sql(path, lines, origin, limits):
    findings = []
    start = None
    # 末尾补一行分号，让最后一条没写分号的语句也能收尾
    for line_number, line in enumerate(lines + [";"], start=1):
        if not line.strip() or line.strip().startswith("--"):
            continue
        if start is None:
            start = line_number
        if line.rstrip().endswith(";"):
            length = min(line_number, len(lines)) - start + 1
            if length > limits.max_sql_lines:
                findings.append((origin(range(start, start + length)),
                                 f"{path}:{start}：SQL 语句有 {length} 行，超过 {limits.max_sql_lines}"))
            start = None
    return findings


# 检查代码和脚本长度；已经超长且本次继续增长，属于本次加重的问题
def inspect_code_size(path, suffix, lines, base_source, limits):
    line_limit = limits.max_script_lines if suffix in SCRIPT_SUFFIXES else limits.max_file_lines
    if len(lines) <= line_limit:
        return []
    old_line_count = 0 if base_source is None else len(base_source.splitlines())
    file_origin = "原有" if old_line_count > line_limit and len(lines) <= old_line_count else "本次改动"
    kind = "脚本" if suffix in SCRIPT_SUFFIXES else "文件"
    return [(file_origin, f"{path}：{kind} {len(lines)} 行（改动前 {old_line_count}），超过 {line_limit}")]


# 检查 Python 文件：函数长度，以及类和函数有没有注释；按名字对比起点版本，区分"原有"
def inspect_python(path, source, base_source, limits):
    findings = []
    try:
        ast.parse(source)
    except SyntaxError as error:
        return [("本次改动", f"{path}:{error.lineno}：Python 语法错误：{error.msg}")]
    old_lengths = {} if base_source is None else {
        name: length for name, _, length in python_function_lengths(base_source)
    }
    for name, start, length in python_function_lengths(source):
        if length <= limits.max_function_lines:
            continue
        old_length = old_lengths.get(name, 0)
        function_origin = "原有" if old_length > limits.max_function_lines and length <= old_length else "本次改动"
        findings.append((function_origin,
                         f"{path}:{start}：函数 {name} 有 {length} 行，超过 {limits.max_function_lines}"))
    old_missing = set() if base_source is None else {
        (kind, name) for kind, name, _ in python_missing_comments(base_source)
    }
    for kind, name, start in python_missing_comments(source):
        missing_origin = "原有" if (kind, name) in old_missing else "本次改动"
        findings.append(("待人工检查", f"{path}:{start}：{missing_origin}{kind} {name} 没有说明，检查是否需要业务解释"))
    return findings


# 逐行检查注释、异常捕获和用词
def inspect_code_lines(path, suffix, lines, source, origin, wording):
    findings = []
    prose_lines = code_text_lines(source, suffix)
    ignored = example_lines(lines)
    if suffix == ".py":
        findings += exception_findings(path, source, origin)
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        text = comment_text(line, suffix)
        if text is not None:
            if TODO_PATTERN.search(text):
                findings.append((origin([line_number]), f"{path}:{line_number}：残留 TODO 类标记"))
            elif COMMENTED_CODE_PATTERN.match(text):
                findings.append(("待人工检查", f"{path}:{line_number}：{origin([line_number])}疑似注释掉的代码"))
            elif CHANGE_NOTE_PATTERN.match(text):
                findings.append(("待人工检查", f"{path}:{line_number}：{origin([line_number])}疑似记录改动的注释"))
        if suffix != ".py" and BROAD_CATCH_PATTERN.search(line):
            findings.append((origin([line_number]), f"{path}:{line_number}：捕获异常后什么都不做"))
        prose = " ".join(part for part in (text, prose_lines.get(line_number)) if part)
        if prose and line_number not in ignored:
            findings += wording_finding(path, line_number, prose, origin, wording)
    return findings


# 忽略错误的空处理算问题；统一记录、继续抛出或转换错误的处理交给人工判断。
def exception_findings(path, source, origin):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        names = {part.id for part in ast.walk(node.type) if isinstance(part, ast.Name)} if node.type else set()
        if node.type is not None and not names.intersection({"Exception", "BaseException"}):
            continue
        empty = all(isinstance(part, ast.Pass) or (
            isinstance(part, ast.Expr) and isinstance(part.value, ast.Constant)
            and part.value.value is Ellipsis) for part in node.body)
        # 处理内容被改成忽略错误时，即使捕获那一行没改，也属于本次影响。
        changed_origin = origin(range(node.lineno, node.end_lineno + 1))
        kind = changed_origin if empty else "待人工检查"
        detail = "宽泛的异常捕获后忽略错误" if empty else "宽泛的异常捕获，检查是否掩盖错误；按项目规则判断"
        findings.append((kind, f"{path}:{node.lineno}：{changed_origin}{detail}"))
    return findings


# 检查一个文件，返回这个文件的问题列表，每项是（"本次改动"或"原有"，问题描述）
def inspect_file(path, full_path, base_source, changed_lines, limits, wording):
    suffix = os.path.splitext(path)[1]
    with open(full_path, encoding="utf-8", errors="replace") as file:
        source = file.read()
    lines = source.splitlines()

    # 判断一组行号里有没有被这次改动动过；起点里没有这个文件时，是新文件，问题都算本次改动
    def origin(line_numbers):
        if base_source is None or any(number in changed_lines for number in line_numbers):
            return "本次改动"
        return "原有"

    if suffix in DOC_SUFFIXES:
        return inspect_document(path, lines, origin, limits, wording)
    if suffix in SQL_SUFFIXES:
        return inspect_sql(path, lines, origin, limits)
    findings = inspect_code_size(path, suffix, lines, base_source, limits)
    if suffix == ".py":
        findings += inspect_python(path, source, base_source, limits)
    return findings + inspect_code_lines(path, suffix, lines, source, origin, wording)


# 定义命令行参数：项目根目录、对比起点、是否检查整个包，以及各类内容的长度上限
def parse_arguments():
    parser = argparse.ArgumentParser(description="检查本次改动涉及文件的健康状况（只读）")
    parser.add_argument("--repo", default=".", help="项目根目录")
    parser.add_argument("--base", default="HEAD", help="对比的起点，默认 HEAD（包括未提交的改动）")
    parser.add_argument("--package", help="检查这个包目录下的全部文件，而不是只看改动（整理一个包时用）")
    # 下面几项是各类内容的长度上限，改动时要同步改 code-refactor Skill 里的表格
    parser.add_argument("--max-file-lines", type=int, default=400)
    parser.add_argument("--max-function-lines", type=int, default=60)
    parser.add_argument("--max-doc-lines", type=int, default=300)
    parser.add_argument("--max-script-lines", type=int, default=200)
    parser.add_argument("--max-sql-lines", type=int, default=80)
    return parser.parse_args()


# 逐个文件检查，返回全部问题；顺带打印新增和删除的文件
def collect_findings(changed, limits, wording):
    findings = []
    checked_suffixes = CODE_SUFFIXES | DOC_SUFFIXES | SCRIPT_SUFFIXES | SQL_SUFFIXES
    for path, status in sorted(changed.items()):
        full_path = os.path.join(limits.repo, path)
        if status == "删除":
            print(f"  删除：{path}")
            continue
        if status == "新增":
            line_count = 0
            if os.path.isfile(full_path):
                with open(full_path, "rb") as file:
                    line_count = sum(1 for _ in file)
            print(f"  新增：{path}（{line_count} 行）")
        if os.path.splitext(path)[1] not in checked_suffixes or not os.path.isfile(full_path):
            continue
        # 检查整个包时，所有内容都当作新文件，问题全部算"本次改动"
        base_source = None if status in ("新增", "范围内") else read_base_version(limits.repo, limits.base, path)
        changed_lines = set() if base_source is None else changed_line_numbers(limits.repo, limits.base, path)
        findings.extend(inspect_file(path, full_path, base_source, changed_lines, limits, wording))
    return findings


# 分组打印确定问题和待人工检查项；提示不自动算失败
def print_findings(findings):
    groups = [
        ("本次改动", "本次新增或加重的问题，这次处理", None),
        ("原有", "原有问题，不扩大处理", 20),
        ("待人工检查", "待人工检查，提示不自动算失败", None),
    ]
    for kind, title, limit in groups:
        items = [message for origin, message in findings if origin == kind]
        if not items:
            continue
        print(f"\n{title}（{len(items)} 条）：")
        for message in items[:limit]:
            print(f"  - {message}")
        if limit and len(items) > limit:
            print(f"  ……另有 {len(items) - limit} 条未列出")
    if not findings:
        print("\n检查的文件没有发现问题。")
    sys.exit(1 if any(kind == "本次改动" for kind, _ in findings) else 0)


# 入口：找出要检查的文件，逐个检查，打印结果
def main():
    limits = parse_arguments()
    try:
        changed = (list_package_files(limits.repo, limits.package) if limits.package
                   else list_changed_files(limits.repo, limits.base))
    except RuntimeError as error:
        print(f"无法读取 git 改动：{error}")
        sys.exit(2)
    if not changed:
        if limits.package:
            print(f"目录 {limits.package} 下没有文件。")
        else:
            print(f"相对 {limits.base} 没有改动。改动已经提交时，用 --base main 或 --base HEAD~1 指定起点。")
        return
    scope = limits.package or f"相对 {limits.base} 的改动"
    print(f"检查范围：{scope}，共 {len(changed)} 个文件")
    try:
        wording = load_wording()
    except OSError as error:
        print(f"无法读取用词表，检查未完成：{error}")
        sys.exit(2)
    if not wording:
        print("用词表没有有效内容，检查未完成。")
        sys.exit(2)
    try:
        findings = collect_findings(changed, limits, wording)
    except (OSError, ValueError) as error:
        print(f"检查未完成：{error}")
        sys.exit(2)
    print_findings(findings)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(0)
