"""Compare one MCIL rollout with a replayed demonstration from the same state.

This is a diagnostic check, not an official single-task score.
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

from run_calvin_mcil_cpu import load_model_and_environment


def episode(folder, index):
    with np.load(folder / f"episode_{index:07d}.npz") as item:
        return {key: item[key].copy() for key in item.files}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-path", type=Path, required=True)
    parser.add_argument("--train-folder", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task", default="turn_on_lightbulb")
    parser.add_argument("--steps", type=int, default=65)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    seed_everything(0, workers=True)
    validation = args.dataset_path / "validation"
    ann = np.load(validation / "lang_annotations" / "auto_lang_ann.npy", allow_pickle=True).item()
    chosen = None
    for task, language, bounds in zip(
        ann["language"]["task"], ann["language"]["ann"], ann["info"]["indx"]
    ):
        if task == args.task:
            chosen = (language, int(bounds[0]), int(bounds[1]))
            break
    if chosen is None:
        raise RuntimeError(f"No annotated demonstration for {args.task}")
    demo_language, start, end = chosen
    record = episode(validation, start)
    model, env = load_model_and_environment(args.train_folder, args.dataset_path, args.checkpoint)
    official_annotations = OmegaConf.load(
        Path(__import__("calvin_agent").__file__).resolve().parent.parent
        / "conf/annotations/new_playtable_validation.yaml"
    )
    language = official_annotations[args.task][0]
    env.reset(robot_obs=record["robot_obs"], scene_obs=record["scene_obs"])
    initial_info = env.get_info()
    initial_obs = env.get_obs()
    initial_pose = initial_obs["robot_obs_raw"].detach().cpu().numpy().reshape(-1)[:3].astype(float)
    model.reset()
    oracle_config = Path(__import__("calvin_agent").__file__).resolve().parent.parent / "conf/callbacks/rollout/tasks/new_playtable_tasks.yaml"
    oracle = hydra.utils.instantiate(OmegaConf.load(oracle_config))
    actions = []
    robot_positions = [initial_pose.tolist()]
    demo_actions = [episode(validation, index)["actions"].astype(float).tolist() for index in range(start, min(end + 1, start + args.steps))]
    success_step = None
    cv2.imwrite(str(args.output / "start.png"), cv2.cvtColor(env.render(mode="rgb_array"), cv2.COLOR_RGB2BGR))
    for step in range(args.steps):
        with torch.no_grad():
            action = model.step(env.get_obs(), language)
        actions.append(action.detach().cpu().numpy().reshape(-1).tolist())
        _, _, _, info = env.step(action)
        robot_positions.append(env.get_obs()["robot_obs_raw"].detach().cpu().numpy().reshape(-1)[:3].astype(float).tolist())
        if oracle.get_task_info_for_set(initial_info, info, {args.task}) and success_step is None:
            success_step = step
    cv2.imwrite(str(args.output / "end.png"), cv2.cvtColor(env.render(mode="rgb_array"), cv2.COLOR_RGB2BGR))
    demo_first = record["actions"].astype(float)
    demo_delta = demo_first[:3] - initial_pose
    matrix = np.asarray(actions)
    demo_matrix = np.asarray(demo_actions)
    pose_errors = np.linalg.norm(matrix[:, :3] - demo_matrix[:, :3], axis=1)
    grip_mismatches = np.flatnonzero(np.sign(matrix[:, -1]) != np.sign(demo_matrix[:, -1]))
    result = {
        "task": args.task,
        "language": language,
        "demonstration_language": demo_language,
        "demo_start_index": start,
        "same_initial_state": True,
        "demo_first_absolute_action": demo_first.tolist(),
        "initial_robot_position": initial_pose.tolist(),
        "demo_first_position_delta": demo_delta.tolist(),
        "mcil_first_action": actions[0],
        "mcil_first_10_action_mean": matrix[:10].mean(axis=0).tolist(),
        "mcil_action_min": matrix.min(axis=0).tolist(),
        "mcil_action_max": matrix.max(axis=0).tolist(),
        "mcil_robot_position_after_10": robot_positions[10],
        "mcil_robot_position_final": robot_positions[-1],
        "mcil_success_step": success_step,
        "mcil_steps": args.steps,
        "pose_action_error_first_10": pose_errors[:10].tolist(),
        "pose_action_error_mean_first_10": float(pose_errors[:10].mean()),
        "pose_action_error_mean_all": float(pose_errors.mean()),
        "gripper_first_sign_mismatch_step": int(grip_mismatches[0]) if len(grip_mismatches) else None,
        "gripper_sign_mismatch_count": int(len(grip_mismatches)),
        "demo_gripper_sign_changes": int(np.count_nonzero(np.diff(np.sign(demo_matrix[:, -1])))),
        "mcil_gripper_sign_changes": int(np.count_nonzero(np.diff(np.sign(matrix[:, -1])))),
        "demo_actions": demo_actions,
        "mcil_actions": actions,
    }
    (args.output / "comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
