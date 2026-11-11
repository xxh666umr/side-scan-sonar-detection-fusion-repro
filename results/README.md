# results 目录说明

| 文件 | 内容 |
|---|---|
| `results.json` | E0–E3 在清洁 / 域偏移 / PGD 三套测试上的完整指标 |
| `results.md` | 上面结果的表格版 |
| `video_alignment.md` | 视频帧同协议对齐说明（416 / 拉伸 / 640 对比、训练侧尝试） |
| `video_modes.json` | 视频帧各模型、各预处理的 AP50 / AP / Precision 原始值 |
| `advisor_metrics.md` | 按 P / R / mAP 口径整理的 test split 结果表 |
| `advisor_metrics.csv` | 同上，CSV 格式 |
| `complexity.md` | E0 与 E3 的参数量 / 延迟对比（证明推理复杂度未增加） |

指标口径：
- `test split`：130 张，416 输入，pycocotools COCO 指标（mAP@0.5、mAP@0.5:0.95、Recall@0.5），P/R 另给固定阈值 0.25 / 0.5 与 Best-F1 点。
- `视频帧`：6244 帧，640 输入，论文同款 OD-Metrics（Padilla 2021），11 点插值，只统计有 GT 的 wall 类。
- **两套评测不可直接比较**（数据与协议不同）。
