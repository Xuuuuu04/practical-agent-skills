"""检查词表同步和示例范围，不用词语匹配代替整句话的含义判断。"""

from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
with patch.object(sys, "path", [str(SCRIPTS), *sys.path]):
    CHECKS = runpy.run_path(str(SCRIPTS / "change_health.py"))
    WORDING = runpy.run_path(str(SCRIPTS / "wording_checks.py"))
WORDS = WORDING["load_wording"]()
# wording:examples:start
SAMPLE_WORD = "赋能"
# wording:examples:end
LIMITS = SimpleNamespace(max_doc_lines=300)


# 规则示例需要保留被检查的词，普通正文仍要检查。
class WordingChecksTests(unittest.TestCase):
    # 用临时文件比较词表，测试不写入源文件或已安装内容。
    def check_list(self, content):
        with tempfile.TemporaryDirectory() as directory:
            agents = Path(directory) / "AGENTS.md"
            agents.write_text(content)
            return WORDING["check_wording_list"](agents)

    # 构造全局词表的格式，内容来自明确的详细词表。
    def list_text(self, words):
        return "<!-- wording:list:start -->\n" + "、".join(words) + "\n<!-- wording:list:end -->"

    # 同一词表允许顺序不同；这里不把顺序当作表达要求。
    def test_same_words_are_accepted(self):
        self.assertEqual(self.check_list(self.list_text(sorted(WORDS))), len(WORDS))

    # 少了或多了一个词，都不能安装，避免只检查某一方向。
    def test_missing_or_extra_words_stop_installation(self):
        for words in [set(WORDS) - {SAMPLE_WORD}, set(WORDS) | {"新增示例词"}]:
            with self.subTest(words=words), self.assertRaisesRegex(ValueError, "词表不一致"):
                self.check_list(self.list_text(sorted(words)))

    # 没有标明范围或标了两份，都无法确定全局词表。
    def test_missing_or_duplicate_lists_are_rejected(self):
        for content in ["普通说明", self.list_text(WORDS) * 2]:
            with self.subTest(content=content), self.assertRaises(ValueError):
                self.check_list(content)

    # 只有示例不提示；同一个词出现在后面的正文中仍提示。
    def test_document_examples_do_not_hide_prose(self):
        source = f"<!-- wording:examples:start -->\n{SAMPLE_WORD}\n<!-- wording:examples:end -->\n{SAMPLE_WORD}\n"
        findings = CHECKS["inspect_document"](
            "example.md", source.splitlines(), lambda lines: "本次改动", LIMITS, WORDS)
        self.assertEqual(len(findings), 1)
        self.assertIn("example.md:4", findings[0][1])

    # 文档叫 wording.md 也不能绕过正文检查。
    def test_document_name_does_not_disable_checking(self):
        with tempfile.TemporaryDirectory() as directory:
            document = Path(directory) / "wording.md"
            document.write_text(SAMPLE_WORD)
            findings = CHECKS["inspect_file"]("wording.md", str(document), None, set(), LIMITS, WORDS)
            self.assertEqual(len(findings), 1)

    # 用词示例不免除错误处理检查，也不影响后面的正常代码检查。
    def test_code_examples_only_skip_wording(self):
        source = (f'# wording:examples:start\nlabel = "{SAMPLE_WORD}"\n'
                  'try:\n    execute_step()\nexcept Exception:\n    pass\n'
                  f'# wording:examples:end\nlabel = "{SAMPLE_WORD}"\n')
        findings = CHECKS["inspect_code_lines"](
            "example.py", ".py", source.splitlines(), source, lambda lines: "本次改动", WORDS)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0][0], "本次改动")
        self.assertIn("example.py:8", findings[1][1])

    # 少结束、多结束或交错的标记不能静默跳过后续正文。
    def test_unpaired_markers_stop_checking(self):
        for source in ["# wording:examples:start", "# wording:examples:end",
                       "# wording:list:start\n# wording:examples:end"]:
            with self.subTest(source=source), self.assertRaises(ValueError):
                WORDING["example_lines"](source.splitlines())

    # 源项目内验证安装入口；已安装副本不带安装脚本，因此跳过这一项。
    def test_installation_checks_before_copying(self):
        root = SCRIPTS.parents[3]
        if not (root / "install.sh").exists():
            self.skipTest("安装副本没有项目安装脚本")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            shutil.copy2(root / "install.sh", target / "install.sh")
            shutil.copytree(SCRIPTS.parent, target / "harness/skills/pre-delivery-check")
            (target / "harness/AGENTS.md").write_text(self.list_text(set(WORDS) - {SAMPLE_WORD}))
            result = subprocess.run(["bash", str(target / "install.sh"), "--dry-run", "codex"],
                                    text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("词表不一致", result.stderr)
            self.assertNotIn("[codex]", result.stdout)


if __name__ == "__main__":
    unittest.main()
