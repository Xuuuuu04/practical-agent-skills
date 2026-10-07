# Practical Agent Skills

## 项目是什么
木木的全局规范与八个 Skill，供维护者在各 Agent 工具中使用，公开内容供阅读，许可见 README。

## 业务概要
维护者改进协作规范与任务方法，经安装脚本供工具读取；读者通过公开仓库了解内容。

## 设计概要
共同规则在全局规范，任务方法在 Skill，脚本与测试在对应目录。harness 是内容来源，安装副本供工具读取。

## 怎么运行
- 依赖：bash、python3。安装用 `./install.sh`，选择工具用 `./install.sh claude codex`，预览用 `./install.sh --dry-run`。
- 项目说明：`python3 harness/skills/project-agents-md/scripts/check_agents_md.py .`
- 脚本测试：`python3 -m unittest discover -s harness/skills/pre-delivery-check/tests -v`
- 安装语法：`bash -n install.sh`
- 词表：`python3 harness/skills/pre-delivery-check/scripts/wording_checks.py --agents harness/AGENTS.md`，安装前自动执行。
- 情境检查：按 pre-delivery-check 在临时目录选相关场景；已配置工具各尝试，失败记原因。
- 安装后新开会话；TRAE SOLO CN 重启后在规则与技能管理中查看识别情况。GLMX、MiniMax 为独立配置，目录不存在时跳过。

## 目录地图
- `harness/AGENTS.md`：共同规则。
- `harness/skills/`：八个 Skill；scripts 放工具，tests 放工具测试。
- `install.sh`：安装；README.md：公开入口与许可；CONTRIBUTING.md：维护写法。

## 去哪里找
- 任务方法：`harness/skills/` 下各 SKILL.md；读 README 的用途表选择。
- 中文写法与词表：`harness/AGENTS.md` 第 9 节。
- 长度默认值：`harness/skills/pre-delivery-check/scripts/change_health.py`；变化时更新 code-refactor 的提示值表。
- 项目说明：`harness/skills/project-agents-md/SKILL.md`；小节与检查脚本 SUPPORTED_SECTIONS 一致。
- 安装位置：install.sh 的 TARGETS；旧文件备份在家目录的 prompt-skill-backup-时间目录。

## 数据流动概要
install.sh 将 harness 复制到工具配置目录。Claude 的 CLAUDE.md 用导入行读取全局规范；Claude、TRAE 使用独立 Skill 目录，Codex、两个独立 Codex、ZCode、pi 使用共享目录。安装副本不直接修改。

公开仓库 [practical-agent-skills](https://github.com/Xuuuuu04/practical-agent-skills) 从来源选择文件同步，使用独立历史。

## 本项目的约定
- 写法按 CONTRIBUTING.md，不使用强调词催促模型，不追加改动日志。
- 执行者参与设计与实现，不设按模型强弱分档的常驻角色。
- 安装只替换本项目同名 Skill，保留其他内容；Claude 只加导入行，共享 Skill 不重复安装。
- 一次性试验放临时目录，必要证据按全局第 5 节保留，不添加提示词测试框架。
- 发布限 harness 的 Markdown、Python 源文件及根目录 AGENTS.md、README.md、CONTRIBUTING.md、install.sh、.gitignore；排除缓存、符号链接和本机资料，与来源逐文件比较。
- 许可沿用 README，不自行增加许可证。文件复制、实际读取、情境表现与真实项目效果分别报告。
