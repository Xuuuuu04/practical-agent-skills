"""检查全局词表与示例范围，不用词语匹配代替整句话的含义判断。"""

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
    # 用临时文件读取词表，测试不写入源文件或已安装内容。
    def read_list(self, content):
        with tempfile.TemporaryDirectory() as directory:
            agents = Path(directory) / "AGENTS.md"
            agents.write_text(content)
            return WORDING["load_wording"](agents)

    # 构造全局词表的格式，不再维护另一份完整词表。
    def list_text(self, words):
        return "<!-- wording:list:start -->\n" + "、".join(words) + "\n<!-- wording:list:end -->"

    # 同一词表允许顺序不同；这里不把顺序当作表达要求。
    def test_same_words_are_accepted(self):
        self.assertEqual(self.read_list(self.list_text(sorted(WORDS))), sorted(WORDS))

    # 增删词语只修改全局规范，读取结果立即随之变化。
    def test_global_list_is_the_only_source(self):
        for words in [set(WORDS) - {SAMPLE_WORD}, set(WORDS) | {"新增示例词"}]:
            with self.subTest(words=words):
                self.assertEqual(set(self.read_list(self.list_text(sorted(words)))), words)

    # 空项、重复项与错误分隔符会造成错误匹配，不能继续安装。
    def test_invalid_words_are_rejected(self):
        for words in [[], [SAMPLE_WORD, ""], [SAMPLE_WORD, SAMPLE_WORD], ["示例词，另一个词"]]:
            with self.subTest(words=words), self.assertRaises(ValueError):
                self.read_list(self.list_text(words))

    # 全局规范中的符号名称仍展开成实际需要匹配的两个符号。
    def test_quote_name_is_expanded(self):
        content = self.list_text([SAMPLE_WORD + "，以及直角引号。"])
        self.assertEqual(self.read_list(content), [SAMPLE_WORD, "「", "」"])

    # 没有标明范围或标了两份，都无法确定全局词表。
    def test_missing_or_duplicate_lists_are_rejected(self):
        for content in ["普通说明", self.list_text(WORDS) * 2, self.list_text(WORDS).replace("\n", "")]:
            with self.subTest(content=content), self.assertRaises(ValueError):
                self.read_list(content)

    # 来源、Claude 和 TRAE 从配套全局规范取词，与当前项目无关。
    def test_source_and_installed_locations(self):
        locations = [
            ("harness", "harness/AGENTS.md"),
            (".claude", ".claude/AGENTS.md"),
            (".trae-cn", ".trae-cn/user_rules/practical-agent-skills.md"),
        ]
        for skill_root, agents_name in locations:
            with self.subTest(location=skill_root, agents=agents_name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                script = root / skill_root / "skills/pre-delivery-check/scripts/wording_checks.py"
                agents = root / agents_name
                agents.parent.mkdir(parents=True, exist_ok=True)
                agents.write_text(self.list_text([SAMPLE_WORD]))
                globals_ = WORDING["find_agents_file"].__globals__
                with patch.dict(globals_, __file__=str(script)):
                    self.assertEqual(WORDING["load_wording"](), [SAMPLE_WORD])

    # 安装副本没有配套全局规范时，不能从其他项目悄悄补出一份词表。
    def test_missing_global_file_stops_checking(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "harness/skills/pre-delivery-check/scripts/wording_checks.py"
            with patch.dict(WORDING["find_agents_file"].__globals__, __file__=str(script)), \
                    self.assertRaises(FileNotFoundError):
                WORDING["load_wording"]()

    # 两个工具规范并存时只读取指定文件，缺少指定或指定文件无效都不能借用另一份。
    def test_shared_skill_uses_only_explicit_global_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / ".agents/skills/pre-delivery-check/scripts"
            scripts.mkdir(parents=True)
            for name in ["change_health.py", "wording_checks.py"]:
                shutil.copy2(SCRIPTS / name, scripts / name)
            global_files = {}
            for config, word in [(".codex", SAMPLE_WORD), (".pi/agent", "示例词")]:
                agents = root / config / "AGENTS.md"
                agents.parent.mkdir(parents=True)
                agents.write_text(self.list_text([word]))
                global_files[config] = agents
            project = root / "project"
            project.mkdir()
            subprocess.run(["git", "init", "-q", str(project)], check=True)
            (project / "example.md").write_text(SAMPLE_WORD + "和示例词")
            command = [sys.executable, str(scripts / "change_health.py"), "--repo", str(project), "--package", "."]
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("--agents", result.stdout)
            for config, word, other in [(".codex", SAMPLE_WORD, "示例词"), (".pi/agent", "示例词", SAMPLE_WORD)]:
                with self.subTest(config=config):
                    result = subprocess.run(command + ["--agents", str(global_files[config])],
                                            text=True, capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn(f'"{word}"', result.stdout)
                    self.assertNotIn(f'"{other}"', result.stdout)
            pi_agents = global_files[".pi/agent"]
            pi_agents.write_text("普通说明，没有词表。")
            result = subprocess.run(command + ["--agents", str(pi_agents)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("词表标记", result.stdout)
            pi_agents.unlink()
            result = subprocess.run(command + ["--agents", str(pi_agents)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("检查未完成", result.stdout)

    # 只有示例不提示；同一个词出现在后面的正文中仍提示。
    def test_document_examples_do_not_hide_prose(self):
        source = f"<!-- wording:examples:start -->\n{SAMPLE_WORD}\n<!-- wording:examples:end -->\n{SAMPLE_WORD}\n"
        findings = CHECKS["inspect_document"](
            "example.md", source.splitlines(), lambda lines: "本次改动", LIMITS, WORDS)
        self.assertEqual(len(findings), 1)
        self.assertIn("example.md:4", findings[0][1])

    # 全局规范中的普通正文仍需要检查。
    def test_document_name_does_not_disable_checking(self):
        with tempfile.TemporaryDirectory() as directory:
            document = Path(directory) / "AGENTS.md"
            document.write_text(SAMPLE_WORD)
            findings = CHECKS["inspect_file"]("AGENTS.md", str(document), None, set(), LIMITS, WORDS)
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
            (target / "harness/AGENTS.md").write_text(self.list_text([SAMPLE_WORD, SAMPLE_WORD]))
            result = subprocess.run(["bash", str(target / "install.sh"), "--dry-run", "codex"],
                                    text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("词表包含重复项", result.stderr)
            self.assertNotIn("[codex]", result.stdout)


if __name__ == "__main__":
    unittest.main()
