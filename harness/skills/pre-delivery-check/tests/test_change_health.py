"""用已经发现的错误检查质量脚本，预期来自协作规范与业务样例。"""

import contextlib
import io
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

# 读取同一个 Skill 中的脚本，测试不依赖安装后的副本
SCRIPT = Path(__file__).resolve().parents[1] / "scripts/change_health.py"
with patch.object(sys, "path", [str(SCRIPT.parent), *sys.path]):
    CHECKS = runpy.run_path(str(SCRIPT))
WORDS = CHECKS["load_wording"]()
LIMITS = SimpleNamespace(max_file_lines=400, max_script_lines=200,
                         max_function_lines=60, max_doc_lines=300)


# 这些样例检查用户关心的文字提示、改动归属和检查完成程度
class ChangeHealthTests(unittest.TestCase):
    # 从新代码样例取出检查结果，不创建项目文件
    def code_findings(self, source, suffix=".py"):
        return CHECKS["inspect_code_lines"](
            "example" + suffix, suffix, source.splitlines(), source,
            lambda lines: "本次改动", WORDS,
        )

    # Docker 的技术含义和输入框行为允许保留
    def test_technical_meaning_is_preserved(self):
        for source in ["# Docker 的挂载目录\n", "# 输入框聚焦时显示提示\n"]:
            with self.subTest(source=source):
                self.assertEqual(self.code_findings(source), [])

    # 注释描述当前操作时，不把动作词当成历史记录
    def test_current_action_is_not_change_history(self):
        for source in ["# 更新订单状态\n", "# 删除过期记录\n"]:
            with self.subTest(source=source):
                self.assertEqual(self.code_findings(source), [])

    # 明确的历史记录提醒人工查看，不直接要求删除
    def test_change_history_requires_human_check(self):
        findings = self.code_findings("# 修改：替换了旧实现\n")
        self.assertEqual(findings[0][0], "待人工检查")
        self.assertIn("记录改动", findings[0][1])

    # 界面和日志中的文字要提示检查，不能只扫描注释
    def test_display_and_log_text_are_checked(self):
        # wording:examples:start
        examples = [
            ('.js', 'const label = "完成核对";\n'),
            ('.tsx', '<span>完成核对</span>\n'),
            ('.py', 'logger.info("完成核对")\n'),
        ]
        for suffix, source in examples:
            with self.subTest(suffix=suffix):
                findings = self.code_findings(source, suffix)
                self.assertTrue(any("核对" in item[1] for item in findings))
                self.assertTrue(all(item[0] == "待人工检查" for item in findings))
        # wording:examples:end

    # 已经超长的文件继续增加，属于本次加重的问题
    def test_long_file_growth_is_a_new_problem(self):
        findings = CHECKS["inspect_code_size"](
            "example.py", ".py", ["pass"] * 900, "pass\n" * 401, LIMITS,
        )
        self.assertEqual(findings[0][0], "本次改动")

    # 原有超长文件没有增长时，不强迫扩大整理范围
    def test_unchanged_or_shortened_file_is_existing(self):
        for count in [500, 450]:
            with self.subTest(count=count):
                findings = CHECKS["inspect_code_size"](
                    "example.py", ".py", ["pass"] * count, "pass\n" * 500, LIMITS,
                )
                self.assertEqual(findings[0][0], "原有")

    # 文件第一次超过长度限制，仍然阻止通过
    def test_new_length_overflow_is_a_problem(self):
        findings = CHECKS["inspect_code_size"](
            "example.py", ".py", ["pass"] * 401, "pass\n" * 400, LIMITS,
        )
        self.assertEqual(findings[0][0], "本次改动")

    # 文档引用代码名字与展示代码时，不改代码内容
    def test_document_code_is_not_reworded(self):
        source = "代码名字 `核对记录`。\n```python\n核对记录 = 1\n```\n"
        findings = CHECKS["inspect_document"](
            "example.md", source.splitlines(), lambda lines: "本次改动", LIMITS, WORDS,
        )
        self.assertEqual(findings, [])

    # Python 语法错误不能悄悄变成空的问题清单
    def test_invalid_python_is_reported(self):
        findings = CHECKS["inspect_python"]("example.py", "def broken(:\n", None, LIMITS)
        self.assertEqual(findings[0][0], "本次改动")
        self.assertIn("语法错误", findings[0][1])

    # 用词匹配需要语义判断，提示本身不让脚本失败
    def test_wording_hint_does_not_fail_the_check(self):
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as result:
            CHECKS["print_findings"]([("待人工检查", "用户业务用语待确认")])
        self.assertEqual(result.exception.code, 0)

    # 确定的本次问题仍然让脚本失败
    def test_new_problem_fails_the_check(self):
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as result:
            CHECKS["print_findings"]([("本次改动", "文件第一次超长")])
        self.assertEqual(result.exception.code, 1)

    # 缺少词表时不能声称完成了检查
    def test_missing_word_list_is_not_ignored(self):
        with patch.dict(CHECKS["load_wording"].__globals__, WORDING_FILE="/missing/wording.md"):
            with self.assertRaises(FileNotFoundError):
                CHECKS["load_wording"]()

    # 框架记录后继续抛出，或转成约定的失败结果，不能仅凭捕获范围判失败。
    def test_error_reporting_requires_context(self):
        for handling in [
            'logger.exception("执行失败")\n    raise',
            'raise StepFailure("执行失败") from error',
        ]:
            with self.subTest(handling=handling):
                source = f"try:\n    execute_step()\nexcept Exception as error:\n    {handling}\n"
                findings = self.code_findings(source)
                self.assertEqual(len(findings), 1)
                self.assertEqual(findings[0][0], "待人工检查")

    # 没有记录、上报或重新抛出，直接忽略所有错误时仍然阻止通过。
    def test_ignored_errors_fail_the_check(self):
        for catching in ["Exception", "BaseException", "(ValueError, Exception)", ""]:
            for body in ["pass", "..."]:
                with self.subTest(catching=catching, body=body):
                    source = f"try:\n    execute_step()\nexcept {catching}:\n    {body}\n"
                    findings = self.code_findings(source)
                    self.assertEqual(len(findings), 1)
                    self.assertEqual(findings[0][0], "本次改动")

    # 普通字符串中的代码写法不能被误认为实际的错误处理。
    def test_exception_examples_are_not_executed_code(self):
        source = 'example = """\nexcept Exception:\n    pass\n"""\n'
        self.assertEqual(self.code_findings(source), [])

    # 特定的可预期错误不属于这个宽泛错误检查项。
    def test_specific_errors_are_not_broad(self):
        source = "try:\n    execute_step()\nexcept ValueError:\n    raise\n"
        self.assertEqual(self.code_findings(source), [])

    # 只改处理内容时，也要识别这次新造成的错误遗漏。
    def test_changed_error_body_is_a_new_problem(self):
        source = "try:\n    execute_step()\nexcept Exception:\n    pass\n"
        findings = CHECKS["exception_findings"](
            "example.py", source, lambda lines: "本次改动" if 4 in lines else "原有")
        self.assertEqual(findings[0][0], "本次改动")


if __name__ == "__main__":
    unittest.main()
