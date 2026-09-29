"""Small MCIL single-task smoke test on official CALVIN initial states.

This does not estimate leaderboard performance. It checks whether the loaded
pretrained checkpoint can succeed at least once on selected task types.
"""

import argparse
import json
from pathlib import Path

import cv2
import hydra
import numpy as np
from omegaconf import OmegaConf
from pytorch_lightning import seed_everything
import torch

from calvin_agent.evaluation.multistep_sequences import get_sequences
from calvin_agent.evaluation.utils import get_env_state_for_initial_condition
from run_calvin_mcil_cpu import load_model_and_environment


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-path", type=Path, required=True)
    parser.add_argument("--train-folder", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples-per-task", type=int, default=3)
    parser.add_argument("--skip-first", type=int, default=0)
    parser.add_argument("--sequence-pool", type=int, default=120)
    parser.add_argument(
        "--tasks",
        nargs="+",
        default=["turn_on_led", "move_slider_left", "open_drawer"],
        choices=["turn_on_led", "move_slider_left", "open_drawer"],
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    seed_everything(0, workers=True)
    model, env = load_model_and_environment(args.train_folder, args.dataset_path, args.checkpoint)

    conf = Path(__import__("calvin_agent").__file__).resolve().parent.parent / "conf"
    task_oracle = hydra.utils.instantiate(OmegaConf.load(conf / "callbacks/rollout/tasks/new_playtable_tasks.yaml"))
    annotations = OmegaConf.load(conf / "annotations/new_playtable_validation.yaml")
    target_tasks = args.tasks
    candidates = get_sequences(args.sequence_pool, num_workers=2)
    results = []
    for task in target_tasks:
        task_candidates = [(i, initial) for i, (initial, sequence) in enumerate(candidates) if sequence[0] == task]
        if len(task_candidates) < args.skip_first + args.samples_per_task:
            raise RuntimeError(f"Not enough official initial states for {task}: {len(task_candidates)}")
        for sample_no, (sequence_index, initial) in enumerate(task_candidates[args.skip_first : args.skip_first + args.samples_per_task], start=args.skip_first):
            robot_obs, scene_obs = get_env_state_for_initial_condition(initial)
            env.reset(robot_obs=robot_obs, scene_obs=scene_obs)
            start_info = env.get_info()
            obs = env.get_obs()
            model.reset()
            language = annotations[task][0]
            sample_dir = args.output / f"{task}_{sample_no:02d}"
            sample_dir.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(sample_dir / "start.png"), cv2.cvtColor(env.render(mode="rgb_array"), cv2.COLOR_RGB2BGR))
            actions = []
            success_step = None
            for step in range(360):
                with torch.no_grad():
                    action = model.step(obs, language)
                values = action.detach().cpu().numpy().reshape(-1)
                actions.append(values.tolist())
                obs, _, _, current_info = env.step(action)
                if step in {29, 59, 89, 119, 179, 239, 359}:
                    cv2.imwrite(
                        str(sample_dir / f"frame_{step:03d}.png"),
                        cv2.cvtColor(env.render(mode="rgb_array"), cv2.COLOR_RGB2BGR),
                    )
                if task_oracle.get_task_info_for_set(start_info, current_info, {task}):
                    success_step = step
                    break
            cv2.imwrite(str(sample_dir / "end.png"), cv2.cvtColor(env.render(mode="rgb_array"), cv2.COLOR_RGB2BGR))
            matrix = np.asarray(actions)
            result = {
                "task": task,
                "language": language,
                "sample_no": sample_no,
                "official_sequence_index": sequence_index,
                "initial_condition": initial,
                "success": success_step is not None,
                "success_step": success_step,
                "executed_steps": len(actions),
                "action_min": matrix.min(axis=0).tolist(),
                "action_max": matrix.max(axis=0).tolist(),
                "action_mean": matrix.mean(axis=0).tolist(),
                "gripper_positive_fraction": float(np.mean(matrix[:, -1] > 0)),
                "gripper_sign_changes": int(np.count_nonzero(np.diff(np.sign(matrix[:, -1])))),
                "gripper_abs_above_one_fraction": float(np.mean(np.abs(matrix[:, -1]) > 1)),
                "result_dir": str(sample_dir),
            }
            (sample_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            (sample_dir / "actions.json").write_text(json.dumps(actions, ensure_ascii=False), encoding="utf-8")
            results.append(result)
            (args.output / "summary.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{task} sample {sample_no}: success={result['success']} steps={len(actions)}", flush=True)


if __name__ == "__main__":
    main()
