# Practical Agent Skills

Xuuuuu04 的 AI 编程设计资产：一份全局协作规范和七个 Skill，覆盖业务规则、后端架构、界面设计、代码整理、项目说明、交付检查与会话交接。

以小团队的实际交付为使用背景。人决定业务规则、优先顺序和重要代价；Agent 查证、提建议、实现并说明结果。设计与测试做到足以支持当前目标，不为形式增加流程。

## 1. 内容

| 资产 | 用途 |
| --- | --- |
| [全局协作规范](harness/AGENTS.md) | 平级协作、主动纠错、何时等待、时间与进度、中文表达、Git 提交 |
| [业务规则与验收样例](harness/skills/business-rules/SKILL.md) | 用具体输入和结果明确业务规则，供实现与检查共用 |
| [后端架构设计](harness/skills/backend-architecture-design/SKILL.md) | FastAPI 单体后端的模块组织、数据处理与旧系统迁移 |
| [界面设计](harness/skills/interface-design/SKILL.md) | 按使用任务安排页面、导航、操作过程与视觉样式 |
| [代码重构与整理](harness/skills/code-refactor/SKILL.md) | 处理指定包中的真实问题，比较整理前后的行为 |
| [维护项目说明](harness/skills/project-agents-md/SKILL.md) | 维护项目根目录 AGENTS.md 的运行与阅读入口 |
| [交付前检查](harness/skills/pre-delivery-check/SKILL.md) | 检查功能、业务结果和受影响页面，如实报告完成程度 |
| [会话交接](harness/skills/session-handoff/SKILL.md) | 换会话前直接输出项目理解、全部相关工作状态、信息缺口与下一步，不生成交接文件 |

这套内容配合使用。公共协作规则写在全局 AGENTS.md，Skill 只补充对应任务的处理办法；部分 Skill 会调用同目录中其他 Skill 的脚本。单独取出一个文件可能缺少引用内容。

## 2. 文件组织

以 harness 为内容来源。harness/AGENTS.md 是供工具读取的全局规则，harness/skills 保存七个 Skill；根目录 AGENTS.md 说明如何维护本仓库，CONTRIBUTING.md 规定写法与检查要求，install.sh 负责本机安装。

Skill 使用直接指导执行的写法，作者背景与聊天记录不进入指令。英文名称用于文件与工具识别，正文使用中文。

## 3. 维护者的安装方式

安装脚本依赖 bash、python3，本机已在 macOS 执行；Linux 和 Windows 原生环境尚未实测。支持 Claude Code、Codex、ZCode、pi，也识别维护者自定义的 GLMX 和 MiniMax Codex 配置目录；后两者不是通用安装要求。

```bash
# 先查看目标位置，预览不会修改安装目录
./install.sh --dry-run

# 按已有工具选择安装
./install.sh claude codex

# 或安装到全部已存在的目标配置目录
./install.sh
```

安装会替换所选工具的全局 AGENTS.md，以及本仓库同名 Skill；先备份到家目录中的 prompt-skill-backup-时间。Claude 的 CLAUDE.md 保留原内容，通过导入行读取规则。其他 Skill 不替换；目标配置目录不存在时跳过。

Codex、ZCode 和 pi 共用 ~/.agents/skills，Claude 使用 ~/.claude/skills。不要再把同一 Skill 放进 Codex 或 ZCode 的私有 Skill 目录。安装后新开会话；工具实际读取行为可能随版本变化，需要分别检查。

## 4. 维护与验证

维护办法见 [CONTRIBUTING.md](CONTRIBUTING.md)，具体命令见 [项目说明](AGENTS.md)。安装检查只能证明文件已复制；情境回答只能说明该次表现，不能证明长期任务或真实客户交付一定正确。

一次性试验与本机记录不进入仓库。不默认新增 CI/CD；已有必要的检查照常执行。

## 5. 公开范围与使用许可

Copyright © 2026 Xuuuuu04。

本仓库公开供阅读，暂未提供开源许可证，也未授予额外的使用、修改或分发许可。需要这些授权时，请联系作者。README 中的安装说明记录维护者的工作方式，不表示授予使用许可。
