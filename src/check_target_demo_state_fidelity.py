"""Measure simulator drift when replaying exact recorded target-task actions."""

import argparse
import json
from pathlib import Path

import numpy as np
from omegaconf import OmegaConf

from calvin_env.envs.play_table_env import get_env


def episode(folder, index):
    with np.load(folder / f"episode_{index:07d}.npz") as item:
        return {key: item[key].copy() for key in item.files}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    folder = args.dataset_path / "training"
    obs_space = OmegaConf.create({
        "rgb_obs": ["rgb_static"], "depth_obs": [], "state_obs": ["robot_obs"],
        "actions": ["actions"], "language": ["language"],
    })
    env = get_env(folder, obs_space=obs_space, show_gui=False)
    rows = []
    for task, start, end in (
        ("turn_on_led", 359180, 359244),
        ("move_slider_left", 359812, 359876),
        ("open_drawer", 359133, 359197),
    ):
        first = episode(folder, start)
        env.reset(robot_obs=first["robot_obs"], scene_obs=first["scene_obs"])
        position_errors = []
        scene_errors = []
        for index in range(start, end):
            current = episode(folder, index)
            next_record = episode(folder, index + 1)
            action = current["actions"].astype(np.float32)
            sim = (action[:3], action[3:6], action[6:7])
            obs, _, _, _ = env.step(sim)
            position_errors.append(float(np.linalg.norm(obs["robot_obs"][:3] - next_record["robot_obs"][:3])))
            scene_errors.append(float(np.max(np.abs(obs["scene_obs"][:6] - next_record["scene_obs"][:6]))))
        rows.append({
            "task": task,
            "position_error_mean_mm": float(np.mean(position_errors) * 1000),
            "position_error_max_mm": float(np.max(position_errors) * 1000),
            "scene_first6_max_abs_error": float(np.max(scene_errors)),
            "position_errors_mm": [x * 1000 for x in position_errors],
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps([{k: v for k, v in row.items() if k != "position_errors_mm"} for row in rows], indent=2), flush=True)


if __name__ == "__main__":
    main()
