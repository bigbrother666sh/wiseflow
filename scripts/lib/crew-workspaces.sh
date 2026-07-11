#!/bin/bash
# crew-workspaces.sh - shared helpers for deploying crew template directories

copy_crew_template_contents() {
  local source_dir="$1"
  local dest_dir="$2"

  if [ ! -d "$source_dir" ]; then
    echo "❌ Crew template directory not found: $source_dir" >&2
    return 1
  fi

  mkdir -p "$dest_dir"
  cp -R "$source_dir/." "$dest_dir/"
}

# 同步 crew 专属 skill 到已部署 workspace（spec §2.3）。
#   src_crew：仓库 crews/<id>/
#   dest_ws：~/.openclaw/workspace-<id>/
# 语义：
#   - 对仓库里每个合法 skill（含 SKILL.md），rm -rf + cp -R 覆盖到 dest_ws/skills/<name>/
#   - 不删除 dest_ws/skills/ 里仓库没有的 skill（保留部署实例自定义 skill）
#   - 不碰 dest_ws 下的 AGENTS.md / TOOLS.md / Memory 等（保留用户编辑）
#   - 对带 package.json 的 skill 跑 npm install --production
# 幂等：每次调用都把仓库 skill 当前内容刷下去，供 skill 更新传播到已部署 workspace。
sync_crew_skills() {
  local src_crew="$1"
  local dest_ws="$2"
  local src_skills="$src_crew/skills"
  local dest_skills="$dest_ws/skills"

  [ -d "$src_skills" ] || return 0
  mkdir -p "$dest_skills"

  local skill_dir=""
  local skill_name=""
  local synced=0
  for skill_dir in "$src_skills"/*/; do
    [ -d "$skill_dir" ] || continue
    [ -f "${skill_dir}SKILL.md" ] || continue
    skill_name="$(basename "$skill_dir")"
    rm -rf "$dest_skills/$skill_name"
    cp -R "${skill_dir%/}" "$dest_skills/$skill_name"
    synced=$((synced + 1))
  done

  # 安装带 package.json 的 skill 依赖
  local skill_pkg=""
  for skill_pkg in "$dest_skills"/*/package.json; do
    [ -f "$skill_pkg" ] || continue
    skill_dir="$(dirname "$skill_pkg")"
    skill_name="$(basename "$skill_dir")"
    echo "  📦 installing deps for skill: $skill_name"
    (cd "$skill_dir" && npm install --production --silent 2>/dev/null) || \
      echo "  ⚠️  npm install failed for skill: $skill_name" >&2
  done

  [ "$synced" -gt 0 ] && echo "  ✅ synced $synced crew skill(s) → $(basename "$dest_ws")"
}

ensure_soul_crew_type() {
  local soul_file="$1"
  local crew_type="$2"

  [ -f "$soul_file" ] || return 0

  case "$crew_type" in
    internal|external) ;;
    *)
      echo "❌ Invalid crew-type: $crew_type" >&2
      return 1
      ;;
  esac

  if grep -qi '^crew-type:' "$soul_file" 2>/dev/null; then
    sed -i.bak "s/^[Cc]rew-[Tt]ype:.*$/crew-type: $crew_type/" "$soul_file"
    rm -f "$soul_file.bak"
  else
    printf '\ncrew-type: %s\n' "$crew_type" >> "$soul_file"
  fi
}
