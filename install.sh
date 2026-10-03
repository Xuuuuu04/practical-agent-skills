#!/usr/bin/env bash
# 把 harness/ 下的全局规范和 Skill 安装到 Claude Code、Codex（含 GLMX、MiniMax）、ZCode、pi。
# 用法：
#   ./install.sh                 安装到全部工具
#   ./install.sh claude codex    只安装到指定工具
#   ./install.sh codex-glm codex-minimax  安装到两个独立 Codex
#   ./install.sh --dry-run       只打印将要做的操作，不改文件
# 被替换的文件先备份到 ~/prompt-skill-backup-<时间>/，保持相对于家目录的路径。
# 只替换和本项目同名的 Skill，其他 Skill 一律不动。
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "$0")/harness" && pwd)"
PROMPT_FILE="$SOURCE_DIR/AGENTS.md"
SKILLS_DIR="$SOURCE_DIR/skills"

# 工具名|全局规范路径|Skill 目录
# Codex、ZCode、pi 都会读取 ~/.agents/skills，所以 Skill 只在那里放一份；
# Codex 和 ZCode 还读自己的 Skill 目录，两处各放一份，同一个 Skill 会被加载两次。
TARGETS=(
  "claude|$HOME/.claude/AGENTS.md|$HOME/.claude/skills"
  "codex|$HOME/.codex/AGENTS.md|$HOME/.agents/skills"
  "codex-glm|$HOME/.glm-codex/AGENTS.md|$HOME/.agents/skills"
  "codex-minimax|$HOME/.minimax-codex/AGENTS.md|$HOME/.agents/skills"
  "zcode|$HOME/.zcode/AGENTS.md|$HOME/.agents/skills"
  "pi|$HOME/.pi/agent/AGENTS.md|$HOME/.agents/skills"
)

# Claude Code 只读 CLAUDE.md。全局规范通过这一行导入，CLAUDE.md 里用户自己写的内容保留。
CLAUDE_MEMORY="$HOME/.claude/CLAUDE.md"
CLAUDE_IMPORT="@~/.claude/AGENTS.md"

DRY_RUN=0
SELECTED=()
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) SELECTED+=("$arg") ;;
  esac
done

BACKUP_DIR="$HOME/prompt-skill-backup-$(date +%Y%m%d-%H%M%S)"
INSTALLED_SKILL_DIRS=" "

run() {
  echo "  $*"
  [ "$DRY_RUN" -eq 1 ] || "$@"
}

backup() {
  local path="$1" relative
  [ -e "$path" ] || [ -L "$path" ] || return 0
  relative="${path#"$HOME"/}"
  run mkdir -p "$BACKUP_DIR/$(dirname "$relative")"
  run cp -a "$path" "$BACKUP_DIR/$relative"
}

install_skills() {
  local dir="$1" skill name
  [[ "$INSTALLED_SKILL_DIRS" == *" $dir "* ]] && return 0
  INSTALLED_SKILL_DIRS+="$dir "
  run mkdir -p "$dir"
  for skill in "$SKILLS_DIR"/*/; do
    name="$(basename "$skill")"
    backup "$dir/$name"
    run rm -rf "${dir:?}/$name"
    run cp -R "${skill%/}" "$dir/$name"
  done
}

ensure_claude_import() {
  if [ -f "$CLAUDE_MEMORY" ] && grep -qxF "$CLAUDE_IMPORT" "$CLAUDE_MEMORY"; then
    return 0
  fi
  backup "$CLAUDE_MEMORY"
  echo "  在 ${CLAUDE_MEMORY} 末尾加一行 ${CLAUDE_IMPORT}，原有内容保留"
  [ "$DRY_RUN" -eq 1 ] || printf '\n%s\n' "$CLAUDE_IMPORT" >> "$CLAUDE_MEMORY"
}

[ -f "$PROMPT_FILE" ] || { echo "找不到全局规范：$PROMPT_FILE" >&2; exit 1; }
[ -d "$SKILLS_DIR" ] || { echo "找不到 Skill 目录：$SKILLS_DIR" >&2; exit 1; }
python3 "$SKILLS_DIR/pre-delivery-check/scripts/wording_checks.py" --agents "$PROMPT_FILE"
[ "$DRY_RUN" -eq 1 ] && echo "只预览，不修改文件。"

for target in "${TARGETS[@]}"; do
  IFS='|' read -r name prompt skills <<< "$target"
  if [ ${#SELECTED[@]} -gt 0 ] && [[ ! " ${SELECTED[*]} " =~ " $name " ]]; then
    continue
  fi
  if [ ! -d "$(dirname "$prompt")" ]; then
    echo "[$name] 本机没有安装，跳过。"
    continue
  fi
  echo "[$name]"
  backup "$prompt"
  run cp "$PROMPT_FILE" "$prompt"
  [ "$name" = "claude" ] && ensure_claude_import
  install_skills "$skills"
done

if [ "$DRY_RUN" -eq 0 ] && [ -d "$BACKUP_DIR" ]; then
  echo "原有内容已备份到：$BACKUP_DIR"
fi
echo "完成。新开会话后生效。"
