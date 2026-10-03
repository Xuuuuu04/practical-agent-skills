# Practical Agent Skills

## 这个项目是什么
一份全局协作规范和六个 Skill，覆盖业务规则、后端架构、界面设计、代码整理、项目说明与交付检查。内容公开供阅读，使用许可见 README。维护已有设计资产，按真实使用中的问题改进，不扩成通用工具集合。

## 怎么运行
- 依赖：bash、python3。安装到本机用 `./install.sh`；选择工具用 `./install.sh claude codex`；预览用 `./install.sh --dry-run`。修改 harness 下文件后重新安装，新开会话才生效。
- GLMX 和 MiniMax Codex 是自定义的独立配置：`./install.sh codex-glm codex-minimax`。对应配置目录不存在时跳过。
- 项目说明检查：`python3 harness/skills/project-agents-md/scripts/check_agents_md.py .`
- 脚本测试：`python3 -m unittest discover -s harness/skills/pre-delivery-check/tests -v`
- 安装语法：`bash -n install.sh`
- 词表检查：`python3 harness/skills/pre-delivery-check/scripts/wording_checks.py --agents harness/AGENTS.md`；安装和预览都会先执行，不一致时停止。
- 情境检查：在系统临时目录新开会话，按 `harness/skills/pre-delivery-check/references/behavior-checks.md` 选与改动有关的少量场景。已配置的六个工具各尝试一次；没有配置或调用失败，记录原因，不能当作通过。比较前后效果时使用同一模型和设置，保留原回答与不符合要求的结果。
  - Claude Code：`claude -p "<问题>"`
  - Codex：`codex exec --skip-git-repo-check -s read-only "<问题>"`
  - GLMX / MiniMax Codex：分别设置 CODEX_HOME 指向独立目录，使用对应应用内的 codex 命令执行同一问题；按配置和服务端结果判断型号，不靠模型自述。
  - ZCode：用当前版本的 CLI 列出 Skill，再用 `-p "<问题>" --mode plan` 检查；桌面应用入口说明见本机维护记录。
  - pi：`pi --model <厂商/模型> --tools read -p "<问题>"`，先用 `pi --list-models` 确认已有模型。

## 目录地图
- `harness/AGENTS.md`：全局协作规范，供各工具读取。
- `harness/skills/business-rules/`：业务规则与验收样例。
- `harness/skills/backend-architecture-design/`：FastAPI 单体后端设计；references 保存模板和检查说明。
- `harness/skills/interface-design/`：页面与交互设计；references 保存情境与资料。
- `harness/skills/code-refactor/`：按明确指定的包整理代码。
- `harness/skills/project-agents-md/`：项目说明维护；scripts 保存目录概览和格式检查。
- `harness/skills/pre-delivery-check/`：交付检查；scripts 保存改动与用词检查，references 保存中文示例和行为检查办法，tests 保存脚本测试。
- `install.sh`：安装脚本；README.md：内容入口与许可；CONTRIBUTING.md：长期写法和检查约定。
- .agent：按任务需要在本机创建，保留任务、决定、环境说明与公开仓库的工作目录，不公开。

## 去哪里找
- 协作、授权、中文和 Git：全局 `harness/AGENTS.md`；共同规则不复制进各 Skill。
- Skill 统一视角和后续维护：CONTRIBUTING.md；正文直接指导执行，不加人物背景或口述经历。
- 字段含义、未定规则与验收样例：`harness/skills/business-rules/SKILL.md`。
- 中文写法：全局第 9 节及 `harness/skills/pre-delivery-check/references/wording.md`。
- 默认长度限制：`harness/skills/pre-delivery-check/scripts/change_health.py`；改变默认值时同时修改 code-refactor 的长度表。
- 项目说明格式：`harness/skills/project-agents-md/SKILL.md`；八个小节与检查脚本 REQUIRED_SECTIONS 保持一致。
- 安装位置：install.sh 中的 TARGETS；备份在家目录的 prompt-skill-backup-时间目录。

## 数据怎么流动
harness 是内容来源。install.sh 把全局规范复制到各工具的配置目录；Claude 的 CLAUDE.md 用导入行读取。六个 Skill 复制到 Claude 的 Skill 目录和共享的 ~/.agents/skills，后者供 Codex、两个独立 Codex、ZCode、pi 使用。安装副本不直接修改。

公开仓库只接收明确选择的发布文件，以独立历史开始。原开发仓库保留历史与本机资料；后续仍从 harness 修改、检查后同步公开副本，不把本机工作目录整体推送。公开副本保存在本机 .agent/public-repo，其远程地址以实际 Git 配置为准。

## 本项目的约定
- 新增和修改 Skill 遵循 CONTRIBUTING.md。新规则来自真实问题，保留必要原因与例子；过时和重复内容原处删除。
- 不使用强调词催促模型，不写改动日志。设计与检查做到满足当前目标，影响交付的问题处理完后停止。
- 等待条件只在全局第 8 节定义，Skill 只补充任务步骤；中文词表保留在全局与详细说明中，由安装检查比较。
- 改完重新安装，在已配置的六个工具中各尝试实测；交付写明问了什么、结果如何。文件复制、实际读取、情境回答和真实项目效果分别报告。
- 一次性测试放系统临时目录，不在项目中添加提示词测试框架；密钥、本机路径、账号配置、客户数据和会话记录不公开。
- 发布文件限 harness 中的 Markdown、Python 源文件，以及根目录的 AGENTS.md、README.md、CONTRIBUTING.md、install.sh、.gitignore；新增类型时先检查用途与内容。排除 Python 缓存、符号链接和本机记录；公开副本与来源逐文件比较。
- 保留公开阅读、暂不授予额外使用许可的决定；不自行添加开源许可证。

## 不要做的事
- 恢复按模型强弱划分的常驻架构、审查和实现 Agent。长任务会因交接丢失信息，重复审查也容易无休止扩展。
- 删除或覆盖本项目以外的 Skill。安装只替换同名目录，其他工具安装的内容保持原样。
- 把同一个 Skill 同时装进共享目录与 Codex 或 ZCode 的私有 Skill 目录，会造成重复读取。
- 整份覆盖 Claude 的 CLAUDE.md；只加导入行，保留已有内容。
- 将旧仓库历史、本机 .agent 或临时检查结果直接公开。

## 已知的坑
- 工具读取位置可能随版本变化；查看实际登记路径和读取动作，不用正文提及次数代替独立条目数。
- code-refactor 调用同级 pre-delivery-check 的脚本，手工只复制一个 Skill 会缺少依赖。
- bash 变量后面紧接中文标点时，用花括号包住变量名，避免 set -u 将标点当作变量名的一部分。
- 命令行不一定使用系统代理。连接失败时检查系统代理与进程变量；只按需要设置本次进程，不改长期配置。
- pi 缺少权限确认与沙箱时，命令以当前用户权限执行；只读情境测试限制为 read 工具，不连接生产数据。
- GitHub SSH 22 端口受限时可使用 ssh.github.com 的 443 端口；是否需要调整以实际连接结果为准。
