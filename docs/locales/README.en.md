# CALVIN Failure Analysis

[简体中文](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/README.md) · **English** · [日本語](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/locales/README.ja.md) · [Deutsch](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/locales/README.de.md) · [Français](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/locales/README.fr.md) · [Español](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/locales/README.es.md) · [Português](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/locales/README.pt.md)

Where does a robot go wrong when every five-step sequence fails? This study uses the CALVIN simulator and a public MCIL model to inspect action deviations and test recovery after failure. Includes figures, data, and a Chinese report.

Python · CALVIN · MCIL · [View experiment report](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/report.pdf)

This is a small-scale research project based on the [CALVIN](https://github.com/mees/calvin) simulation environment and the official MCIL pre-training model.

The project focuses on the following questions: **When the Success Rate of a long-horizon robot task is 0, where exactly does the robot fail, why does it fail, and whether it can recover after failure?**

The traditional task-level success rate only retains the final success or failure and cannot distinguish between the following situations:

- The model cannot complete even the first step.
- The model can complete some steps, but errors accumulate in subsequent tasks;
- The model understands the task, but continuous control gradually drifts away;
- The model succeeds only in a few initial states;
- The model cannot recover on its own after failure.

## Experimental process

1. Play back the real demonstration trajectory to verify the environment, action format and success determination.
2. Three single tasks of opening the LED, moving the sliding door to the left and opening the drawer were tested respectively.
3. Run 100 fixed five-step program sequences and record SR@1 to SR@5.
4. Replace the direct failure link of positioning through position, attitude and gripper action.
5. Made fixed retry and continue diagnostics after failure.

## Main results

| experiment | result |
|---|---:|
| Turn on LED | 2/9 |
| sliding door left | 0/9 |
| open drawer | 0/9 |
| 100 five-step sequences completed successfully | 0/100 |
| SR@1 | 1% |
| SR@2—SR@5 | 0% |
| Fixed retry recovery | 0/10 |
| Continue execution after failure | 0/50 steps |

An LED success condition is still completed at the 94th action step after running independently, indicating that the model is not completely incapable, but is sensitive to the initial state. Comparison of action components showed that all three types of tasks failed after only replacing the position action; when freely executed, the distance between the position action and the demonstration trajectory expanded to 72.9-194.2 mm. The LED case also showed inconsistent gripper orientation at key steps.

![process level experimental results](../../figures/process_level_results.png)

## Success and failure cases

| LED Success Stories: Getting Started | LED Success Story: End |
|---|---|
| ![](../../figures/led_success_start.png) | ![](../../figures/led_success_end.png) |

| LED Failure Case: Getting Started | LED failure case: after executing 360 steps |
|---|---|
| ![](../../figures/led_failure_start.png) | ![](../../figures/led_failure_end.png) |

## Conclusion

This experiment shows that task-level Success Rate is suitable for measuring final completion, but it is not sufficient to explain the long-term task failure process. At a minimum, the first failed step, continuous completion length, movement component deviation, and recovery results should also be recorded.

Current evidence supports that "closed-loop position deviation is a direct failure link common to the three types of tasks", but it cannot be used to determine the only cause within the model. This conclusion only applies to the public weights, debug data and experimental conditions used in this project.

## Project structure

```text
.
├── README.md
├── docs/
│   ├── report.pdf                  # Chinese lab report
│   └── internship-summary.md       # Scientific research internship summary
├── figures/                        # Summary diagram and case screenshots
├── results/                        # JSON vs. CSV experiment results
└── src/                            # Evaluation and diagnostic code
```

Complete Chinese report: [docs/report.pdf](../../docs/report.pdf)

For the selection of research questions, work completed by me, debugging process and research limitations during scientific research internship, please see: [docs/internship-summary.md](../../docs/internship-summary.md)

## Reproduction instructions

The code needs to be run in the CALVIN official environment and prepare:

- CALVIN environment with `calvin_models`;
- Environment D data or official debug data;
- Official `D_D_static_rgb_baseline` MCIL checkpoint;
- Python 3.8, PyTorch 1.13.1, PyTorch Lightning 1.8.6, and Hydra 1.1.1.

Main entrance:

```bash
python src/run_calvin_mcil_cpu.py \
  --dataset-path /path/to/calvin_dataset \
  --train-folder /path/to/D_D_static_rgb_baseline \
  --checkpoint /path/to/mcil_baseline.ckpt \
  --num-sequences 100 \
  --output results/evaluation.json
```

For the purpose of single-task evaluation and various diagnostic scripts, see [src/README.md](../../src/README.md). This repository does not redistribute the CALVIN dataset or model weights.

## Study limitations

- Only one MCIL public checkpoint was tested;
- Uses ~1.3 GB of debug data, not the full dataset;
- Using CPU inference, no real robot experiments were performed;
- The results are reproducible stage studies and do not represent CALVIN official ranking results.

## Acknowledgments

This project uses the CALVIN benchmark environment and its public models. Please abide by the original project license and cite the CALVIN paper when using relevant data, environments or models:

> Mees et al., *CALVIN: A Benchmark for Language-Conditioned Policy Learning for Long-Horizon Robot Manipulation Tasks*, IEEE Robotics and Automation Letters, 2022.
