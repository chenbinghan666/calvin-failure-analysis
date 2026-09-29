"""Check whether simulator reset recreates recorded CALVIN demo observations."""

import argparse
import json
from pathlib import Path

import numpy as np
from omegaconf import OmegaConf

from calvin_env.envs.play_table_env import get_env


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    validation = args.dataset_path / "validation"
    annotations = np.load(validation / "lang_annotations/auto_lang_ann.npy", allow_pickle=True).item()
    obs_space = OmegaConf.create({
        "rgb_obs": ["rgb_static"], "depth_obs": [], "state_obs": ["robot_obs"],
        "actions": ["actions"], "language": ["language"],
    })
    env = get_env(validation, obs_space=obs_space, show_gui=False)
    seen = set()
    rows = []
    for task, bounds in zip(annotations["language"]["task"], annotations["info"]["indx"]):
        if task in seen:
            continue
        seen.add(task)
        start = int(bounds[0])
        with np.load(validation / f"episode_{start:07d}.npz") as item:
            record = {key: item[key].copy() for key in item.files}
        reset_obs = env.reset(robot_obs=record["robot_obs"], scene_obs=record["scene_obs"])
        image = reset_obs["rgb_obs"]["rgb_static"].astype(np.float32)
        saved = record["rgb_static"].astype(np.float32)
        diff = np.abs(image - saved)
        rows.append({
            "task": task,
            "episode": start,
            "image_mean_abs_error": float(diff.mean()),
            "image_max_abs_error": float(diff.max()),
            "robot_max_abs_error": float(np.abs(reset_obs["robot_obs"] - record["robot_obs"]).max()),
            "scene_max_abs_error": float(np.abs(reset_obs["scene_obs"] - record["scene_obs"]).max()),
            "image_shape": list(image.shape),
        })
        if len(rows) >= 3:
            break
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(rows, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
