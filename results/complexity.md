# 推理复杂度对比（E0 基线 vs E3 融合模型）

## 结论

E0 与 E3 是**同一个网络结构**（YOLOX-Nano-ViT），参数量、推理延迟完全一致，精度提升来自训练策略（蒸馏 / 伪标签 / 对抗样本）而非增加推理复杂度。

## 测量结果

硬件：RTX 4060 Laptop 8GB，Windows，PyTorch 2.5.1+cu121。
输入 416×416，batch=1，fp16 autocast，同一进程内交替测量 4 轮、每轮 100 次取最小值。

| 模型 | 结构 | 参数量（直接统计） | 推理延迟 | test mAP@0.5 |
|---|---|---|---|---|
| E0（官方 Nano-ViT 权重） | YOLOX-Nano-ViT | 1.39 M | 34.65 ms | 0.2273 |
| E3（融合最终模型） | YOLOX-Nano-ViT | 1.39 M | 33.98 ms | **0.2600** |

> 说明：`thop` 统计显示 0.96M，是因为 ViT 层的部分算子在 thop 中未计入；
> 以 `sum(p.numel() for p in model.parameters())` 直接统计为准，为 1.39M。
> 非 ViT 的 YOLOX-Nano 为 0.897M，加 ViT 层后为 1.393M。

## 复现方式

```bash
python tools/measure_complexity.py
```

脚本会加载 E0/E3 权重，打印参数量与单张推理延迟（可在自己的机器上复测）。
