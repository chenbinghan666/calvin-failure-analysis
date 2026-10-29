# 面向长程机器人任务的失败模式分析与过程级评测

这是一个基于 [CALVIN](https://github.com/mees/calvin) 仿真环境和官方 MCIL 预训练模型完成的小规模研究项目。

项目关注的问题是：**当一条长程机器人任务的 Success Rate 为 0 时，机器人究竟失败在什么位置，为什么失败，以及失败后能否恢复？**

传统任务级成功率只保留最终的成功或失败，无法区分以下情况：

- 模型从第一步开始就不会；
- 模型能完成部分步骤，但错误在后续任务中累积；
- 模型理解了任务，但连续控制逐渐偏离；
- 模型只在少数初始状态下成功；
- 模型失败后无法自行恢复。

## 实验流程

1. 回放真实示范轨迹，验证环境、动作格式和成功判定。
2. 分别测试打开 LED、左移滑门和打开抽屉三类单任务。
3. 运行 100 条固定五步长程序列，记录 SR@1 至 SR@5。
4. 通过位置、姿态和夹爪动作替换定位直接失败环节。
5. 进行固定重试和失败后继续执行诊断。

## 主要结果

| 实验 | 结果 |
|---|---:|
| 打开 LED | 2/9 |
| 左移滑门 | 0/9 |
| 打开抽屉 | 0/9 |
| 100 条五步序列完整成功 | 0/100 |
| SR@1 | 1% |
| SR@2—SR@5 | 0% |
| 固定重试恢复 | 0/10 |
| 失败后继续执行 | 0/50 个步骤 |

一个 LED 成功条件独立复跑后仍在第 94 个动作步完成，说明模型不是完全没有能力，但对初始状态较敏感。动作分量对照显示，三类任务只替换位置动作后均失败；自由执行时，位置动作与示范轨迹的距离扩大到 72.9—194.2 mm。LED 案例还出现了关键步骤夹爪方向不一致。

![过程级实验结果](figures/process_level_results.png)

## 成功与失败案例

| LED 成功案例：开始 | LED 成功案例：结束 |
|---|---|
| ![](figures/led_success_start.png) | ![](figures/led_success_end.png) |

| LED 失败案例：开始 | LED 失败案例：执行 360 步后 |
|---|---|
| ![](figures/led_failure_start.png) | ![](figures/led_failure_end.png) |

## 结论

本实验说明，任务级 Success Rate 适合衡量最终完成情况，但不足以解释长程任务失败过程。至少还应记录首次失败步骤、连续完成长度、动作分量偏差和恢复结果。

当前证据支持“闭环位置偏离是三类任务共同的直接失败环节”，但不能据此确定模型内部唯一原因。该结论只适用于本项目使用的公开权重、debug 数据和实验条件。

## 项目结构

```text
.
├── README.md
├── docs/
│   ├── report.pdf                  # 中文实验报告
│   └── internship-summary.md       # 科研实习总结
├── figures/                        # 汇总图和案例截图
├── results/                        # JSON 与 CSV 实验结果
└── src/                            # 评测与诊断代码
```

完整中文报告：[docs/report.pdf](docs/report.pdf)

科研实习中的研究问题选择、本人完成的工作、排错过程和研究局限见：[docs/internship-summary.md](docs/internship-summary.md)

## 复现说明

代码需要在 CALVIN 官方环境中运行，并准备：

- CALVIN 环境与 `calvin_models`；
- 环境 D 数据或官方 debug 数据；
- 官方 `D_D_static_rgb_baseline` MCIL 检查点；
- Python 3.8、PyTorch 1.13.1、PyTorch Lightning 1.8.6 和 Hydra 1.1.1。

主要入口：

```bash
python src/run_calvin_mcil_cpu.py \
  --dataset-path /path/to/calvin_dataset \
  --train-folder /path/to/D_D_static_rgb_baseline \
  --checkpoint /path/to/mcil_baseline.ckpt \
  --num-sequences 100 \
  --output results/evaluation.json
```

单任务评测和各类诊断脚本的用途见 [src/README.md](src/README.md)。本仓库不重新分发 CALVIN 数据集或模型权重。

## 研究边界

- 只测试了一个 MCIL 公开检查点；
- 使用约 1.3 GB 的 debug 数据，没有使用完整数据集；
- 使用 CPU 推理，没有进行真实机器人实验；
- 结果属于可复现的阶段研究，不代表 CALVIN 官方排行榜成绩。

## 致谢

本项目使用 CALVIN 基准环境及其公开模型。请在使用相关数据、环境或模型时遵守原项目许可并引用 CALVIN 论文：

> Mees et al., *CALVIN: A Benchmark for Language-Conditioned Policy Learning for Long-Horizon Robot Manipulation Tasks*, IEEE Robotics and Automation Letters, 2022.

