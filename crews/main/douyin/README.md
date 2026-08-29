# douyin — 抖音平台运营文件夹

该平台全部运营数据存于此，子目录专款专用、不混放：

| 子目录 | 内容 |
|--------|------|
| `ref/` | 参考材料（对标视频转录、评论摘要等） |
| `outputs/` | 成片与素材（每条一个 `<video-name>/`：成片、封面、简报、dna-meta.json） |
| `dna/` | DNA 运行资产（每 `<dna-id>/`：reports / dna 文档 / template / evals） |
| `calibration/` | 校准与复盘数据（baseline、受众画像、对标记录、平台状态） |

`calibration/` 默认含 `audience.md`（受众画像）与 `platform-state.json`（平台状态）；其余文件（对标记录等）由相应 workflow 按需生成。

数据存储总约定见工作区 `AGENTS.md`「数据存储」段。
