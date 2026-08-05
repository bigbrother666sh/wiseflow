---
name: design-full
description: 平面设计全案——完整网页/落地页、APP/产品界面、品牌视觉体系。从需求 brief 到设计系统选取、素材获取、HTML/CSS 编写、视觉 review、交付归档的完整工作流。接到"做网页/落地页/APP 界面/品牌视觉"类平面设计需求时走本技能。
metadata:
  openclaw:
    emoji: 🎨
    requires:
      bins:
        - python3
---

# 平面设计全案（design-full）

## 适用场景

用户要做以下任一平面设计工作：

- 完整网页 / 落地页 / 团队介绍页 / 404 页等
- APP / 产品界面 / 管理后台 / SaaS 面板原型
- 品牌视觉体系（色彩 / 字体 / 组件 / 间距规范）

不适用：视频制作（→ `video-producer` / `collage-broll` / `manim-explainer`）。

---

## 工作流

### Step 1：建工作区（强制起点）

每项设计任务开始前**必须**先建独立文件夹，所有产出归档其中：

```bash
design-full init <任务名>
```

产出目录结构（落在工作区根的 `design_assets/` 下）：

```
design_assets/YYYY-MM-DD-<任务名>/
├── brief.md        # 设计需求模板（待填写，确认后不可跳过）
├── prompts.json    # 生图参数记录
├── source/         # 原始素材（参考图、品牌资产等）
└── output/         # 成品输出（HTML/CSS 文件、组件预览页）
```

`design_assets/` 同时建 `references/` 与 `brand/` 两个共享子目录（跨任务复用参考素材与品牌资产）。

### Step 2：Brief 确认（强制闸门）

把需求整理写入 `brief.md`，**发给用户确认，等待明确同意**。确认前不得进入后续步骤。后续视觉 review 以 brief 为基准对照。

brief 至少含：产品类型 / 页面或界面清单 / 功能范围 / 风格方向 / 品牌约束 / 参考素材。

### Step 3：设计系统选取

每项任务在 brief 确认后、进具体设计前**必须**调本技能确定设计系统：

```bash
design-full pick "<风格描述>"
```

按风格描述从内置 14 套设计系统库匹配最合适的 1–3 套，展示匹配结果及推荐理由给用户，**等待确认选定**。用户也可指定参考品牌或自定义风格，本技能据此生成定制 DESIGN.md。

选定后把该设计系统规范写入任务 `DESIGN.md`，后续所有 HTML/CSS 产出的色彩、字体、间距、组件样式都遵循该规范。

### Step 4：素材获取

页面所需配图 / 背景图 / 参考图：

- **优先**：公共 `pexels-footage` / `pixabay-footage` 搜索下载
- **备选**：公共 `siliconflow-img-gen` 生成
- 下载或生成的素材保存到 `source/` 目录

### Step 5：HTML + CSS 编写

- CSS custom properties 定义设计 token（颜色、间距、字号、阴影）——严格遵循 DESIGN.md
- 语义化标签（header / main / section / footer）
- 响应式（min-width: 768px / 1024px 断点）
- hover / focus / active 状态完备
- 图片引用 `source/` 中的素材

### Step 6：视觉 Review（强制闸门）

生成页面 / 组件后**必须**调视觉模型 review，不得跳过：

1. 用 `image` 工具查看生成结果
2. 对照 `brief.md` 和 `DESIGN.md` 逐项检查：风格一致性、组件规范遵循度、响应式表现、交互状态完整性
3. 发现偏差 → 调整 CSS token 或 HTML 结构后重新输出（**最多 3 轮**）
4. Review 通过 → 发送给用户

### Step 7：交付归档

最终确认后把文件保存到任务文件夹 `output/` 目录，归档并更新 `index.md`。

---

## 三条子工作流（按任务类型择）

按 brief 里的产品类型择一条子工作流执行。Step 1/2/3/6/7 是三条共用骨架，下面只列各子工作流的 Step 4/5 差异。

### 工作流 A：完整网页 / 落地页设计

```
Step 2 brief 含：
  - 页面类型（产品介绍页/活动落地页/团队介绍/404 页...）
  - 页面清单与信息架构（Sections 列表）
  - 交互功能范围（纯静态展示/含表单/含轮播...）
  - 风格参考（可提供品牌名或描述词）
  - 是否需要深色模式
  - 品牌约束（品牌色、字体、LOGO — 从 MEMORY.md 获取）
Step 4 素材：页面所需配图/背景图 → pexels-footage / pixabay-footage 优先，siliconflow-img-gen 备选
Step 5 编写：
  - CSS custom properties 定义设计 token —— 严格遵循 DESIGN.md
  - 语义化标签（header / main / section / footer）
  - 响应式（min-width: 768px / 1024px 断点）
  - hover / focus / active 状态
  - 图片引用 source/ 中的素材
最终交付：HTML/CSS 文件 → output/，归档更新 index.md
```

### 工作流 B：APP / 产品界面设计

```
Step 2 brief 含：
  - 产品类型（移动 APP / Web APP / 管理后台 / SaaS 面板...）
  - 核心页面清单（登录/首页/列表/详情/设置...）
  - 交互模式（导航方式、手势支持、状态管理...）
  - 风格参考
  - 品牌约束
Step 3 后另写 DESIGN.md 设计规范：
  - 色彩系统（语义色名 + hex + 用途：primary/secondary/surface/error/...）
  - 字体系统（font-family + 层级表：display/heading/body/caption/overline）
  - 间距系统（4px/8px/12px/16px/24px/32px/48px 基准）
  - 组件样式规范（Button/Input/Card/Nav/Modal/Toast 等，含各状态）
  - 阴影/圆角/动效规范
Step 5 编写关键页面 HTML + CSS 原型：
  - 严格遵循 DESIGN.md 中的 token
  - 移动端优先（如为 APP 界面，按 375px 基准设计）
  - 包含交互状态（hover/focus/disabled/loading）
最终交付：DESIGN.md + 所有页面 HTML/CSS → output/
```

### 工作流 C：品牌视觉体系构建

```
Step 2 brief 含：
  - 品牌定位（行业、目标客群、核心价值）
  - 风格方向（1-3 个关键词，如"专业+科技+温暖"）
  - 现有品牌资产（Logo、已有色彩偏好等）
  - 应用场景（官网/APP/社交媒体/印刷品...）
Step 5 构建完整 DESIGN.md：
  - Visual Theme & Atmosphere：设计哲学、情感基调、密度
  - Color Palette & Roles：语义名 + hex + 功能角色
  - Typography Rules：字体族 + 完整层级表
  - Component Stylings：核心组件样式 + 状态
  - Layout Principles：间距系统、网格、留白哲学
  - Depth & Elevation：阴影系统、表面层级
  - Responsive Behavior：断点、触控目标、折叠策略
  - Do's and Don'ts：设计护栏
Step 5 另编写组件预览页面（preview.html）：
  - 展示色彩色板、字体层级、按钮/卡片/输入框等核心组件
  - 包含亮色和暗色两种表面
最终交付：DESIGN.md + preview.html → output/
  - 将 DESIGN.md 核心信息同步到 MEMORY.md 的 Brand Assets 区
```

---

## CSS 设计 Token 规范

所有 HTML/CSS 产出必须使用 CSS Custom Properties 定义设计 token：

```css
:root {
  /* 语义色彩 */
  --color-primary: oklch(...);
  --color-surface: oklch(...);
  --color-text: oklch(...);

  /* 字体层级 */
  --text-display: clamp(3rem, 1rem + 7vw, 8rem);
  --text-body: clamp(1rem, 0.9rem + 0.5vw, 1.125rem);

  /* 间距系统 */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;

  /* 动效 */
  --duration-normal: 300ms;
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
}
```

---

## 品牌规范应用原则

- 若 MEMORY.md 中有品牌色 / 字体记录 → 在 DESIGN.md 和 CSS token 中**强制指定**
- 若无 → 第一次设计后询问用户是否认可当前色彩体系，认可则记入 MEMORY.md
- 核心品牌色 / Logo 不得随意替换，其余设计 token 可根据设计系统适配

---

## 内置设计系统库

14 套知名品牌设计系统，每套 8 段规范（Visual Theme / Color / Typography / Components / Layout / Depth / Do's & Don'ts / Responsive）：

| 设计系统 | 风格关键词 | 适用场景 |
|---------|----------|---------|
| Stripe | 紫色渐变、优雅、金融科技 | SaaS 产品页、支付/金融科技落地页 |
| Vercel | 黑白极简、精密、Geist | 开发者工具、技术产品官网 |
| Linear | 超极简、紫色点缀、精确 | 项目管理、效率工具 |
| Notion | 暖色极简、衬线标题、柔和 | 知识管理、内容平台 |
| Apple | 极致留白、电影级影像 | 消费电子、高端品牌官网 |
| Supabase | 暗色翡翠绿、代码优先 | 数据库/后端服务、开源工具 |
| Shopify | 暗色电影感、霓虹绿 | 电商平台、商业服务 |
| Figma | 多彩活泼、专业、创意 | 创意工具、设计平台 |
| Spotify | 鲜明绿、大胆排版 | 媒体/娱乐平台 |
| Tesla | 极致减法、全屏影像 | 汽车/硬件、极简品牌 |
| Framer | 黑蓝、动效优先 | 网站构建、交互展示 |
| Airbnb | 暖色珊瑚、摄影驱动 | 旅游/生活服务、社区平台 |
| BMW | 巴伐利亚蓝、暗色奢华、金属质感 | 奢侈品牌、高端产品 |
| IBM | 企业蓝、Carbon 系统、数据密集 | 企业级产品、B2B 服务、数据平台 |
| Starbucks | Siren 绿、温暖社区、自然质感 | 生活品牌、餐饮/零售、社区平台 |

库文件落在本技能目录 `design-systems/<name>.md`，索引 `design-systems/index.json`。

### 自定义设计系统

内置库无法覆盖所有风格需求时，基于用户描述自行构建设计系统，输出格式参照内置 DESIGN.md 的标准 8 段结构。

也可从上游仓库 [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md) 查找并导入：

1. 访问上述仓库查看完整设计系统列表，或直接访问 `https://getdesign.md/<brand-name>/design-md` 查看特定品牌
2. 选取匹配的设计系统后，将内容下载为 `design-systems/<name>.md`，补全缺失段落确保 8 段完整
3. 在 `design-systems/index.json` 中添加条目（字段：`id` / `name` / `category` / `keywords` / `description` / `colorPrimary` / `darkMode` / `bestFor` / `file`）

完成后即可通过 `design-full pick` 搜索到该设计系统。

---

## 子命令清单

| 子命令 | 用途 | 退出码 |
|--------|------|--------|
| `design-full init <任务名>` | 建任务文件夹 + brief 模板 | 0 成功 / 1 参数错 |
| `design-full pick "<风格描述>"` | 从内置库匹配 1–3 套设计系统 | 0 成功 / 1 参数错 |

> Step 2（brief 确认）/ Step 4（素材获取）/ Step 5（HTML+CSS 编写）/ Step 6（视觉 review）/ Step 7（交付归档）由 agent 按 SKILL.md 工作流直接执行，不经本 wrapper——这些是创意判断与对话协作环节，不上脚本。

---

## 禁止事项（强制）

- **禁止 brief 未确认就动手**：Step 2 闸门强制，确认前不得进 Step 3
- **禁止跳过设计系统选取**：每项任务 Step 3 必跑 `design-full pick`，不得凭印象直接写 CSS
- **禁止跳过视觉 Review 交付**：Step 6 闸门强制，对照 brief + DESIGN.md 逐项查，不得裸交
- **禁止凭空捏造品牌色**：MEMORY.md 有记录则强制遵循，无记录则设计后问用户认可才记入
