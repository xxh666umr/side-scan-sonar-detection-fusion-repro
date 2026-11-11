# 侧扫声呐图像目标检测 · 三篇开源论文融合复现

本项目把三篇开源工作（KD-YOLOX-ViT、DCBD、ROSAR）的**方法思路融合成一个检测器**，并在公开侧扫声呐数据集 SWDD 上完成复现与评测。

> 这是**复现/学习性质**的项目，不是任何论文的官方实现。基座代码来自 [remaro-network/KD-YOLOX-ViT](https://github.com/remaro-network/KD-YOLOX-ViT)（Apache-2.0），上游原始 README 见 `README_upstream.md`。

## 做了什么

| 模块 | 来源 | 在本项目中的作用 |
|---|---|---|
| 检测器 YOLOX-Nano-ViT | P1 KD-YOLOX-ViT | 轻量底座（约 1.4M 参数） |
| 知识蒸馏（教师 L-ViT → 学生 Nano-ViT） | P1 | 提升小模型精度 |
| 无监督域自适应 / 伪标签自训练 | P2 DCBD | 缓解侧扫标注数据少的问题 |
| PGD 对抗样本 + 对抗重训练 | P3 ROSAR | 提升噪声 / 攻击下的鲁棒性 |

训练链：**E0 基线 → E1 +KD → E2 +域自适应 → E3 +对抗重训练（最终）**，每一步只加一个模块，做消融。

## 主要结果

### test split（130 张，416 输入，COCO 指标）

| 模型 | mAP@0.5 | mAP@0.5:0.95 | Recall@0.5 | BestF1 P / R |
|---|---|---|---|---|
| E0 基线 | 0.2273 | 0.1187 | 0.7460 | 0.222 / 0.601 |
| E1 + KD | 0.2544 | 0.1431 | 0.8606 | 0.236 / 0.697 |
| E2 + DA | 0.1567 | 0.0702 | 0.8591 | 0.154 / 0.775 |
| E3 + 对抗（最终） | **0.2600** | **0.1537** | 0.8584 | 0.218 / 0.615 |

### 视频帧对齐（6244 帧，640 输入，论文同款 OD-Metrics）

| 模型 | AP50（wall） |
|---|---|
| 论文 Nano-ViT | 0.42 |
| 官方 Nano-ViT 权重（640） | **0.438** |
| 自训 Nano-ViT 200ep / 300ep | 0.240 / 0.153 |
| 融合模型 E3（640） | **0.508** |

**结论**：评测协议可以对齐（0.438 vs 0.42），训练侧因论文配置未完整公开无法逐位复刻；融合模型在同协议下最好。

### 推理复杂度（同一张 RTX 4060，交替测 4 轮取最小）

| 模型 | 结构 | 参数量 | 延迟 | mAP@0.5 |
|---|---|---|---|---|
| E0 | YOLOX-Nano-ViT | 1.39 M | 34.65 ms | 0.2273 |
| E3 | YOLOX-Nano-ViT | 1.39 M | 33.98 ms | 0.2600 |

→ 同结构、同参数量、同速度，提升来自训练策略而非推理复杂度。

## 目录结构

```
.
├─ exps/swdd/                  # 本项目新增的实验配置（nano / nano_vit / l / l_vit / KD）
├─ tools/
│   ├─ fusion_eval.py          # test split 评估（P/R/mAP）
│   ├─ fusion_predict.py       # 教师/学生模型生成伪标签
│   ├─ fusion_merge.py         # 多源 COCO 标注合并
│   ├─ fusion_make_target.py   # 模拟域偏移目标域 + 域偏移测试集
│   ├─ fusion_pgd.py           # PGD 对抗样本生成
│   ├─ eval_video_od_metrics.py# 视频帧 + OD-Metrics 评估
│   ├─ eval_video_modes.py     # 多预处理/输入尺寸评估（带缓存）
│   ├─ show_video_alignment.py # 打印“论文 vs 官方 vs 我们”对齐表
│   └─ measure_complexity.py   # 参数量 / 延迟测量
├─ scripts/                    # 数据下载、流水线、转换等辅助脚本
├─ results/                    # 评测结果（json / md）
├─ docs/                       # 复现报告与汇报 PPT
├─ yolox/                      # YOLOX 基座代码（Apache-2.0，来自上游仓库）
├─ run_pipeline.py             # E0→E1→E2→E3 一键流程 + 三套测试评估
├─ requirements_fusion.txt     # 本项目依赖
├─ LICENSE                     # Apache-2.0（继承上游）
└─ NOTICE                      # 第三方归属与数据许可
```

## 快速开始

### 1. 环境

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate ; Linux: source .venv/bin/activate
pip install -r requirements_fusion.txt
```

`requirements_fusion.txt` 中的 torch 需要 CUDA 版；若默认源装成 CPU 版，请按
`https://download.pytorch.org/whl/cu121` 安装 torch / torchvision。

### 2. 数据（SWDD，不随仓库分发）

从 Zenodo 下载（CC-BY-4.0）：<https://zenodo.org/records/10528135>

整理为：

```
datasets/COCO/SWDD/
  train2017/  val2017/  test2017/
  annotations/instances_{train,val,test}2017.json
```

### 3. 权重

官方权重在 [KD-YOLOX-ViT Releases](https://github.com/remaro-network/KD-YOLOX-ViT/releases)；
本项目训练得到的权重建议放 GitHub Releases，不建议直接提交到仓库。

### 4. 评估

```bash
python tools/fusion_eval.py -f exps/swdd/nano_vit.py \
  -c path/to/swdd-nano-ViT.pth \
  --data_dir datasets/COCO/SWDD \
  --ann datasets/COCO/SWDD/annotations/instances_test2017.json \
  --img_dir datasets/COCO/SWDD/test2017 --tsize 416 \
  --out outputs/e3_test.json
```

### 5. 训练 / 融合流水线

```bash
# 训练 E0（示例）
python tools/train.py -f exps/swdd/nano_vit.py -b 8 --fp16 -expn e0 \
  -o data_num_workers 4 max_epoch 200 no_aug_epochs 10 eval_interval 10

# 一键融合消融（E1→E3，需先有 E0 权重）
python run_pipeline.py --e0_ckpt YOLOX_outputs/e0/best_ckpt.pth --epochs 20
```


## 复现说明与已知局限

- 论文视频帧评测需要 **640 输入 + letterbox**；416 会明显低估（对比见 `results/video_alignment.md`）。
- DCBD 的方法与 Faster R-CNN 强耦合，本项目用“伪标签自训练”做了**方法迁移**，不是逐行复现。
- 论文训练配置未完整公开，自训模型（200 / 300 轮）AP50 为 0.240 / 0.153，低于官方权重 0.438。
- 域偏移测试集是人工模拟的（噪声 / 模糊 / 黑线 / 光照），不是真实组内数据。
- 单卡 8GB 环境，未做多种子重复实验。

## 引用

如果本项目对你有帮助，请引用原始论文：

1. Aubard et al. *Knowledge Distillation in YOLOX-ViT for Side-Scan Sonar Object Detection*. arXiv:2403.09313, 2024.
2. Wei et al. *Unsupervised underwater shipwreck detection in side-scan sonar images based on domain-adaptive techniques*. Scientific Reports 14:12687, 2024. DOI: 10.1038/s41598-024-63501-1.
3. Aubard et al. *ROSAR: An Adversarial Re-Training Framework for Robust Side-Scan Sonar Object Detection*. arXiv:2410.10554, 2024.

## 许可与致谢

- 代码基座：Apache-2.0，来自 [remaro-network/KD-YOLOX-ViT](https://github.com/remaro-network/KD-YOLOX-ViT)，详见 `LICENSE` 与 `NOTICE`。
- 数据集 SWDD：CC-BY-4.0，使用 / 再发布时请保留其版权声明（见 `NOTICE`）。
- 本项目未分发数据集、论文 PDF 与官方模型权重，请通过原文 / 官方链接获取。

## 免责声明

本项目为个人学习 / 复现用途，实验结果与论文原始数值不可直接比较（评测协议不同），详见 `results/` 中的说明。

## 环境适配说明（Windows / 受限账户）

为在 Windows 受限账户下跑通，本仓库对上游代码做了两处兼容性修改：
- yolox/utils/logger.py：loguru 文件日志的 enqueue=True 改为 False（避免命名管道权限问题）
- yolox/evaluators/coco_evaluator.py：强制使用标准的 pycocotools.COOeval，避免编译 C++ 扩展（fast_cocoeval）

普通个人电脑一般不需要这两处修改；若想恢复上游行为，可按上游原文件还原。
另外训练时如遇 DataLoader 权限错误，可加 -o data_num_workers 0。

