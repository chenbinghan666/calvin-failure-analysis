# 脚本说明

| 脚本 | 用途 |
|---|---|
| `run_calvin_mcil_cpu.py` | 运行固定数量的 CALVIN 五步序列，可启用一次重试或失败后继续执行。 |
| `evaluate_calvin_single_tasks_cpu.py` | 对 LED、slider、drawer 等单任务进行小规模评测。 |
| `replay_calvin_demonstrations.py` | 回放真实示范轨迹，验证环境、动作格式和成功判定。 |
| `ablate_mcil_demo_actions.py` | 分别替换位置、姿态和夹爪动作。 |
| `teacher_forced_mcil_diagnostic.py` | 在正确示范状态下检查模型动作。 |
| `compare_mcil_to_demo_start.py` | 对比模型自由执行和示范动作。 |
| `test_mcil_sampling_diagnostic.py` | 检查动作采样方式。 |
| `check_calvin_observation_match.py` | 核对 CALVIN 观察量。 |
| `check_target_demo_state_fidelity.py` | 检查筛选出的示范状态是否符合目标任务。 |
| `scan_debug_scene_transitions.py` | 从 debug 数据中扫描场景状态变化。 |
| `analyze_failure_patterns.py` | 从人工标注表生成过程级失败统计。 |

这些脚本依赖 CALVIN 官方包及其配置文件。数据路径、模型目录和输出路径均通过命令行参数传入，不需要写入个人本机路径。

