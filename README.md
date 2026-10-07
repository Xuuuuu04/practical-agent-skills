# Practical Agent Skills

Xuuuuu04 的 AI 编程设计资产：全局规范和八个手写 Skill。共同规则说明如何协作，Skill 提供任务方法。

## 内容

| 资产 | 用途 |
| --- | --- |
| [全局规范](harness/AGENTS.md) | 开发理念、时间与进度、中文表达、Git 提交与子代理使用 |
| [业务规则与验收样例](harness/skills/business-rules/SKILL.md) | 用具体输入和结果明确业务规则，供实现与检查共用 |
| [排错与修复](harness/skills/debug/SKILL.md) | 顺着实际数据定位原因，选择合适修法，验证同一原因影响的部分并改善定位能力 |
| [后端架构设计](harness/skills/backend-architecture-design/SKILL.md) | FastAPI 单体后端的模块组织、数据处理与旧系统迁移 |
| [界面设计](harness/skills/interface-design/SKILL.md) | 按使用任务安排页面、导航、操作过程与视觉样式 |
| [代码重构与整理](harness/skills/code-refactor/SKILL.md) | 处理指定包中的真实问题，比较整理前后的行为 |
| [维护项目说明](harness/skills/project-agents-md/SKILL.md) | 维护项目根目录 AGENTS.md 的运行与阅读入口 |
| [交付前检查](harness/skills/pre-delivery-check/SKILL.md) | 检查功能、业务结果和受影响页面，如实报告完成程度 |
| [会话交接](harness/skills/session-handoff/SKILL.md) | 换会话前直接输出项目理解、全部相关工作状态、信息缺口与下一步，不生成交接文件 |

## 组织与维护

harness 是手写内容来源，根目录 AGENTS.md 提供项目入口，CONTRIBUTING.md 说明维护写法，install.sh 负责安装。

## 安装

维护者安装依赖 bash，macOS 已执行；Linux 与 Windows 原生环境未实测。

```bash
./install.sh --dry-run        # 预览
./install.sh claude codex     # 选择工具
./install.sh trae-cn          # TRAE SOLO CN
./install.sh                  # 全部已有目标目录
```

支持 Claude Code、Codex、ZCode、pi、TRAE SOLO CN，另识别维护者自定义 GLMX 与 MiniMax Codex。目标目录不存在时跳过；被替换内容先备份到家目录的 prompt-skill-backup-时间目录。

Claude 的 CLAUDE.md 保留原内容并导入全局规范；其他个人 Skill 保留。Codex、ZCode、pi 使用共享目录，Claude 与 TRAE 各用自己的目录。

安装后新开会话，TRAE 重启后查看规则与技能识别。安装成功不证明模型实际遵守，检查办法见项目入口。

## 公开范围与许可

Copyright © 2026 Xuuuuu04。

本仓库公开供阅读，暂未授予额外的使用、修改或分发许可。需要授权请联系作者；安装说明记录维护者的方式，不表示授予使用许可。
