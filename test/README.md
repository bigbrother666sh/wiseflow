# 回归测试

测试及夹具统一放在本目录，按组件分组。测试使用 mock、临时工作区或本地浏览器页面，不执行真实发布。

从仓根运行：

```bash
# Python 技能测试；DOM 测试需要已安装 camoufox-cli 和浏览器
python3 -m unittest discover -s test/skills -p 'test_*.py'
python3 test/skills/check_fill_browser.py

# Node.js 原生测试（使用支持 TypeScript strip-types 的 Node.js）
node --experimental-strip-types --test test/skills/test-upstream-catchup.ts
node test/test-douyin-metrics.mjs

# camoufox-cli 与 Awada；先安装 patches/camoufox-cli 的开发依赖
# Awada accounts 测试需要仓内 openclaw 已构建 dist/plugin-sdk
patches/camoufox-cli/node_modules/.bin/vitest run --config test/vitest.config.mts
```

`patches/camoufox-cli` 中的 `npm test` / `npm run test:watch` 也指向这份统一配置。

`skills/`、`crews/`、`awada/src/` 不放测试脚本。`patches/` 中用于修改上游测试的补丁材料保留在补丁包内。

## 火山生图与视频接口

离线回归（不请求外部生成服务）：

```bash
python3 -m unittest discover -s test/skills -p test_img_gen.py
python3 -m unittest discover -s test/skills -p test_video_volc.py
```

使用当前环境的 `AWK_GEN_KEY` 检查视频创建端点：

```bash
python3 test/skills/check_ark_api.py
```

探测使用空 content，不能创建视频任务；认证错误只证明端点可达，不代表模型权限可用。缺少 key 时退出码为 2。显式加 `--generate-image` 可实际生成一张图片（会计费），默认输出到 `tmp/ark-smoke-image/`，始终不生成视频。

## deck-talk 与自定义音色

```bash
python3 -m unittest discover -s test/deck-talk -p 'test_*.py'
python3 -m unittest discover -s test/skills -p test_voice_customization.py
DECK_RENDER_BROWSER_TEST=1 python3 -m unittest discover -s test/deck-talk -p 'test_*.py'
```

deck-talk 测试用本地临时媒体核验三模式合成与唯一音轨；浏览器预览测试默认跳过，显式启用后才调用本机 Chrome。音色测试模拟供应商响应，不占用真实音色槽位。

## video-producer 视觉片段与拼贴

```bash
python3 -m unittest discover -s test/video-producer -p 'test_*.py'
VIDEO_PRODUCER_BROWSER_TEST=1 python3 -m unittest discover -s test/video-producer -p 'test_*.py'
```

默认测试脚手架、可选 i2v 批量调度及无损去音轨；显式启用浏览器测试时，用本地三层纸片样例检查预览时间轴与 HyperFrames 成片，不调用生成 API。
