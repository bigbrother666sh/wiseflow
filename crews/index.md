# Crew 模板注册表

> 本文件是**开发者参考**，综合列出项目中所有 Crew 模板。
> 产品拆分后（D5/D8/D15）addons/ 结构销毁，crew 全部扁平化在 `crews/` 下。
> Crew 类型说明详见 `CREW_TYPES.md`。

## 对内 Crew 模板（Internal — sub-agent，无 channel）

| 模板 ID | 名称 | 简介 | 类型 | 版本 |
|---------|------|------|------|------|
| it-engineer | IT Engineer | wiseflow 系统部署、维护、升级、排障；main + sales-cs 的 sub-agent | internal | wiseflow built-in |

## 对外 Crew 模板（External — 绑 channel，对用户）

| 模板 ID | 名称 | 简介 | 默认 | 版本 |
|---------|------|------|------|------|
| main | 新媒体运营（创业伴侣） | 内容发布 + 素材运营 + IR 三模式 + BD 三能力，绑 openclaw-weixin | ✅ default | wiseflow official |
| content-producer | 内容制作者 | html-video / manim / tts / video-gen / ui-demo | — | wiseflow official |
| sales-cs | 销售型客服 | 客户咨询、问题解答、成交导向、客户调研，绑 awada，bind-only | 默认禁用 | wiseflow official |

## 用户自建模板（User-created）

| 模板 ID | 名称 | 类型 | 简介 | 创建日期 |
|---------|------|------|------|----------|
| _(暂无)_ | | | | |
