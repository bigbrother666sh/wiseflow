---
name: ui-demo
description: 录制精美的产品 UI demo 视频（camoufox-cli 驱动）。当用户需要录制演示视频、功能演示、操作教程或利益相关方展示视频时使用。输出带可见鼠标、字幕和自然节奏的 WebM 视频。
metadata:
  openclaw:
    emoji: 🎥
    requires:
      bins:
      - node
      - camoufox-cli
---

# UI Demo Video Recorder

用 `camoufox-cli` 探查与演习，用本技能的录制执行器（`ui-demo` 命令）录制成片：注入可见鼠标光标、底部字幕条，配自然节奏，产出 WebM。

## 浏览器后端说明（先读）

本 skill 所有具体操作命令和示例**只针对 `target=camoufox`**（全局 `camoufox-cli` 命令 + 本技能 `ui-demo` 录制执行器）。若当前是 `target=host` 或 `target=node`：只按本 skill 的流程 / 步骤 / 提示事项执行，不要照搬下面的具体命令和示例，浏览器操作走当前后端自带的工具语义。

## When to Use

- 用户需要"演示视频"、"产品录屏"、"功能演示"或"操作教程"
- 需要制作用于文档、用户引导或投资人/客户展示的视频

## Three-Phase Process

**Discover → Rehearse → Record**。禁止跳过直接录制。

**有头/无头总原则**：全程默认无头。只有两种情况用有头：① 用户明确表示要旁观（见 Phase 2 的必问环节）；② 无头模式无法正常工作（页面渲染异常、必须人工过验证码等），此时改有头并告知用户原因。

---

## Phase 1: Discover（camoufox-cli 探查）

在写录制脚本之前，用 `camoufox-cli` 逐一导航到流程中的每个页面，了解真实的页面结构。

```bash
camoufox-cli --session ui-demo --json open <url>
camoufox-cli --session ui-demo --json snapshot
camoufox-cli --session ui-demo --json click @e5      # 探查交互
camoufox-cli --session ui-demo --json screenshot /tmp/ui-demo-check.png
```

- 目标应用**需要登录**时，session 加 `--persistent`（登录态存 profile，演习多轮不重复登录）；登录流程按 `browser-guide` 技能执行（扫码/验证码场景 `--headed`）。
- **目标：建立每个页面的字段映射表**，用于 Phase 3 脚本中的选择器。
- ⚠️ **字段映射必须落成 CSS / text 选择器**（如 `input[name="email"]`、`button:has-text("Submit")`）。snapshot 的 `@e1` ref 只在 camoufox-cli 会话内有效，**不能写进录制脚本**。定位到元素后用 snapshot 里的标签/属性信息推出稳定选择器，必要时 `eval` 验证。

每个页面重点关注：

- **表单字段类型**：是 `<input>`、`<textarea>`、`<select>` 还是自定义 combobox / contenteditable？
- **Select 选项**：确认实际选项值。Placeholder 选项（通常 value 为 `""` 或 `"0"`）看起来非空但实际无效，跳过。
- **按钮精确文本**：如 `"Submit"`、`"Submit Request"`、`"Save"`。
- **必填字段**：尝试提交空表单，观察验证报错。
- **动态字段**：填写某字段后，确认是否有新字段出现。

**输出**：整理每个页面的字段映射，例如：

```
/purchase-requests/new:
  - Budget Code: select#budget-code（4 个真实选项，第一个是 placeholder）
  - Desired Delivery: input[type="date"]
  - Context: textarea[name="context"]（不是 input）
  - Submit: button:has-text("Submit Request")
```

---

## Phase 2: Rehearse（演习 = 确认录制脚本）

不录制，用 `camoufox-cli` **手动走一遍完整流程**。演习的产物是**录制计划**——步骤序列、每步字幕文案、节奏、不录清单——这就是录制脚本，必须经用户确认后才进 Phase 3。

### Step 0：必问用户是否旁观（不许跳过）

演习开始前，先问用户：

> "我准备把整个演示流程演习一遍，确认录制内容。你要在浏览器窗口里**旁观演习**吗？旁观的话你可以随时提意见——重点录哪一块、不录哪一块、顺序怎么调。"

- **用户要旁观** → 先 `camoufox-cli --session ui-demo --json close`，再以有头模式重开演习（viewport 与录制分辨率一致，用户看到的就是录出来的构图）：

  ```bash
  camoufox-cli --session ui-demo --headed --viewport 1280x720 --json open <起始url>
  ```

  旁观模式下的演习纪律：
  - 每一步操作**前**，在聊天里先说这一步要做什么（对应未来的字幕文案），再执行；
  - 节奏放慢，步与步之间留出用户开口的时间；
  - 用户随时提出的意见（"这块重点录"、"这段跳过"、"先展示 X 再展示 Y"）**即时记入录制计划**，必要时当场重走调整后的顺序给用户看。

- **用户不旁观** → 无头演习（不带 `--headed`），照常逐步走完。
- 无头演习中发现页面无法正常工作（渲染异常、验证码等）→ 改有头继续，并告知用户原因。

### 演习内容

- 按照 Phase 1 的字段映射，逐步导航、填写、点击（`camoufox-cli --session ui-demo --json click/fill/type ...`）
- 每个操作后确认页面状态符合预期（`snapshot`）
- 发现不符时，修正字段映射再重试
- 需要上传文件的步骤：`camoufox-cli --session ui-demo --json upload @ref /path/to/file`

> 演习的价值在于消灭"脚本假设"——字段顺序、选择器、等待时机，都在这里确认，不留到录制时爆。

### 演习收尾（强制）

1. 把**录制计划**发给用户确认：步骤清单（每步一句话+字幕文案）、预计时长、明确不录的内容。用户认了才进 Phase 3。
2. 若 Phase 3 需要登录态，先导出 cookie（见下），再关演习 session：

   ```bash
   camoufox-cli --session ui-demo --json cookies export <project-dir>/cookies.json
   camoufox-cli --session ui-demo --json close
   ```

---

## Phase 3: Record（录制执行器）

按确认后的录制计划编写 demo-steps 文件，用 `ui-demo` 命令录制。**默认无头录制**（无头下 WebM 正常产出，不需要屏幕）；仅当用户要求旁观录制过程、或无头录制画面异常时加 `--headed`。

### 运行

```bash
ui-demo --steps <project-dir>/demo-steps.mjs \
        --output <project-dir>/output/demo-<feature>.webm \
        --base-url http://localhost:3000 \
        --cookies <project-dir>/cookies.json
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `--steps` | 必填 | demo-steps 文件路径（ESM，默认导出 async 函数） |
| `--output` | 必填 | 输出 WebM 路径 |
| `--headed` | 关 | 有头录制（仅用户要求旁观或无头异常时用） |
| `--viewport` | `1280x720` | 浏览器窗口尺寸。成片按窗口内容区实测裁定（略小于窗口高，如 1280x658），实际分辨率见输出报告 `resolution` 字段 |
| `--base-url` | env `BASE_URL` | 注入 steps 函数的 `baseURL` |
| `--cookies` | — | 演习 session 导出的 cookie 文件，录制前注入（跳过登录画面） |

退出码：0 成功 / 1 参数错或步骤出错（已录到的部分仍保存）/ 3 浏览器未装（先 `camoufox-cli install`）。

### demo-steps 文件模板

```javascript
export default async function run(demo) {
  const { page, baseURL, showSubtitle, moveAndClick, typeSlowly,
          smoothScroll, pause } = demo;

  // Step 1 - 登录（cookies 已注入通常直接跳过；失效则走表单登录）
  await page.goto(`${baseURL}/dashboard`);
  await pause(3000);
  const loggedIn = await page.locator('.user-menu, .avatar').first()
    .isVisible().catch(() => false);
  if (!loggedIn) {
    await showSubtitle('Step 1 - 登录');
    await typeSlowly('input[name="email"]',    'demo@example.com', 'Email');
    await typeSlowly('input[name="password"]', 'demo-password',    'Password');
    await moveAndClick('button[type="submit"]', 'Login');
    await pause(4000);
    await showSubtitle('');
  }

  await showSubtitle('Step 2 - 概览');
  await smoothScroll(400);

  await showSubtitle('Step 3 - 主要流程');
  // 按录制计划的操作序列……

  await showSubtitle('Step 4 - 结果');
  await pause(3000);
  await showSubtitle('');
}
```

### 内置 helper（执行器提供，不要在 steps 里自己实现）

| helper | 签名 | 行为 |
|--------|------|------|
| `showSubtitle` | `(text)` | 底部字幕条显示 text，置空 `''` 隐藏；显示后自动停 800ms |
| `moveAndClick` | `(locator, label, {postClickDelay=800})` | scrollIntoView → 光标平滑移动到元素中心 → 点击 → 停顿；失败打 WARNING 返回 false |
| `typeSlowly` | `(locator, text, label, charDelay=35)` | 点击聚焦 → 清空 → 逐字输入 |
| `smoothScroll` | `(top)` | smooth 滚动到指定位置 + 停 1.5s |
| `pause` | `(ms)` | 等待 |
| `injectOverlays` | `()` | 手动重注入光标/字幕层。整页导航后执行器已自动重注入；SPA 内部路由切换若丢失覆盖层可手动补 |

`locator` 参数接受 CSS/text 选择器字符串或 `page.locator(...)` 对象。

### Recording Principles

#### 1. Storytelling Flow

将视频规划为一个故事，默认结构：

- **Entry**：登录或导航到起始点
- **Context**：浏览周围环境让观众先定向
- **Action**：执行主要工作流步骤
- **Variation**：展示次要功能（可选）
- **Result**：展示结果或最终状态

#### 2. Pacing（节奏）

| 时机 | 等待时长 |
|------|---------|
| 登录后 | 4s |
| 导航后 | 3s |
| 点击按钮后 | 2s |
| 主要步骤之间 | 1.5-2s |
| 最后一个动作后 | 3s |
| 打字延迟 | 25-40ms / 字符 |

#### 3. Subtitles（字幕）

字幕规范：不超过 60 字符，使用 `Step N - 动作` 格式，UI 已能说明问题时置空隐藏。

#### 4. 富文本编辑器处理（重要）

对于 `contenteditable` 富文本编辑器（如 Quill、TinyMCE 等）：

- **禁止使用 `fill()` 填充内容**！`fill()` 会导致编辑器无法识别内容，提交时可能丢失
- 正确做法：先 `click()` 聚焦，再 `pressSequentially()` 逐字输入（或直接用 `typeSlowly`）
- 清空内容可用 `fill('')`，但填充内容必须逐字输入
- 示例选择器：`div.ql-editor`、`div[contenteditable="true"]`

---

## 交付

1. 录完先看一遍关键帧确认画面正常（可 `video-review <demo.webm>` 自检辅助）
2. 把视频文件本体发给用户，附时长与分辨率
3. 需要转格式、与其他素材拼接、加 BGM/旁白 → 交给 `video-edit` 技能

---

## Checklist Before Recording

- [ ] Phase 1 完成，每个页面字段映射已确认（CSS/text 选择器，不是 @ref）
- [ ] Phase 2 完成：已问过用户是否旁观；全流程走通无报错
- [ ] 录制计划（步骤+字幕+不录清单）已经用户确认
- [ ] 脚本选择器来自 Phase 1/2 的实际观察，无假设
- [ ] 所有点击使用 `moveAndClick`（含描述性 label）
- [ ] 可见输入使用 `typeSlowly`
- [ ] 滚动使用 `smoothScroll`
- [ ] 关键过渡点有 `showSubtitle`
- [ ] 需要登录态时 cookies.json 已从演习 session 导出

## Common Pitfalls

1. 视频速度太快 → 增加停顿
2. Select placeholder 看起来非空 → Phase 1 时确认 value 是否为 `""` 或 `"0"`
3. 弹窗感觉突兀 → 确认前增加阅读停顿
4. **把 snapshot 的 `@ref` 写进 demo-steps** → ref 只在 camoufox-cli 会话内有效，脚本必须用 CSS/text 选择器
5. **富文本编辑器用 `fill()` 填充** → 必须用 `typeSlowly` / `pressSequentially()`
6. **混淆标题和正文输入框** → Phase 1 必须明确区分，标题和正文通常是独立的元素
7. SPA 路由切换后覆盖层丢失 → steps 里调 `injectOverlays()` 手动补
8. 演习完不 close session → daemon + Firefox 常驻吃内存，演习收尾必须 close

---

## 浏览器操作最佳实践（Phase 1/2 探查演习时）

### 1. 超时与 session 正忙

- camoufox-cli 命令超时：**不要立即重启浏览器或放弃任务**。等待 30 秒后原 session 继续；仍失败再等 30 秒；60 秒后仍报错才 `close` 重开；重开后仍报错才停下反馈用户。
- 命令返回 "session ui-demo 正忙" → 有上一条命令还在跑，等待片刻重试，不要并发下发命令。

### 2. 文件上传

演习中需要测试上传功能时：`camoufox-cli --session ui-demo --json upload @ref /path/to/file`。上传后用 `snapshot` 检查页面状态（进度条、缩略图、处理状态文字）确认结果，不要靠命令返回猜成败。

### 3. 页面状态检查

- 操作后用 `snapshot` 检查关键元素是否存在、错误提示、URL 变化
- 找不到元素时先 `snapshot` 看真实 DOM 结构再改选择器，不要盲试
