"""Replay annotated CALVIN debug demonstrations through the real simulator.

Uses recorded absolute actions, not MCIL predictions.  This checks action
format, environment stepping and the official task oracle independently.
"""

import argparse
import json
from pathlib import Path

import cv2
import hydra
import numpy as np
from omegaconf import OmegaConf

from calvin_env.envs.play_table_env import get_env


def load_episode(folder, index):
    with np.load(folder / f"episode_{index:07d}.npz") as episode:
        return {key: episode[key].copy() for key in episode.files}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    annotations = np.load(
        args.validation / "lang_annotations" / "auto_lang_ann.npy", allow_pickle=True
    ).item()
    task_cfg = OmegaConf.load(
        args.repo / "calvin_models" / "conf" / "callbacks" / "rollout" / "tasks" / "new_playtable_tasks.yaml"
    )
    task_oracle = hydra.utils.instantiate(task_cfg)
    # Match the MCIL static-RGB observation suite; the default suite also
    # enables an unrelated tactile renderer that needs obsolete NumPy APIs.
    obs_space = OmegaConf.create(
        {"rgb_obs": ["rgb_static"], "depth_obs": [], "state_obs": ["robot_obs"],
         "actions": ["actions"], "language": ["language"]}
    )
    env = get_env(args.validation, obs_space=obs_space, show_gui=False)

    candidates = []
    seen_tasks = set()
    for task, language, (start, end) in zip(
        annotations["language"]["task"],
        annotations["language"]["ann"],
        annotations["info"]["indx"],
    ):
        if task not in seen_tasks:
            candidates.append((task, language, int(start), int(end)))
            seen_tasks.add(task)
    results = []
    for task, language, start, end in candidates[: args.limit]:
        first = load_episode(args.validation, start)
        env.reset(robot_obs=first["robot_obs"], scene_obs=first["scene_obs"])
        initial = env.get_info()
        initial_obs = env.get_obs()
        sample_indices = {start, (start + end) // 2, end}
        trace_dir = args.output / f"{task}_{start}_{end}"
        trace_dir.mkdir(parents=True, exist_ok=True)
        action_rows = []
        oracle_first_success_step = None
        max_robot_error = 0.0
        max_scene_error = 0.0
        frame_checks = []
        cv2.imwrite(str(trace_dir / "start.png"), cv2.cvtColor(env.render(mode="rgb_array"), cv2.COLOR_RGB2BGR))

        for step, index in enumerate(range(start, end + 1)):
            record = load_episode(args.validation, index)
            action = record["actions"].astype(np.float32)
            assert action.shape == (7,)
            # Absolute-action API: [position xyz, Euler xyz, gripper].
            sim_action = (action[:3], action[3:6], action[6:7])
            env.step(sim_action)
            info = env.get_info()
            action_rows.append(action.tolist())
            current = task_oracle.get_task_info_for_set(initial, info, {task})
            if current and oracle_first_success_step is None:
                oracle_first_success_step = step
            if index in sample_indices:
                cv2.imwrite(str(trace_dir / f"step_{step:03d}.png"), cv2.cvtColor(env.render(mode="rgb_array"), cv2.COLOR_RGB2BGR))
                raw = env.get_obs()
                # The recorded episode is an observation before its action;
                # compare simulator state to the next recorded observation.
                if index < end:
                    next_record = load_episode(args.validation, index + 1)
                    robot_error = float(np.max(np.abs(raw["robot_obs"] - next_record["robot_obs"])))
                    scene_error = float(np.max(np.abs(raw["scene_obs"] - next_record["scene_obs"])))
                    max_robot_error = max(max_robot_error, robot_error)
                    max_scene_error = max(max_scene_error, scene_error)
                    frame_checks.append({"step": step, "robot_max_abs_error": robot_error, "scene_max_abs_error": scene_error})
        matrix = np.asarray(action_rows)
        result = {
            "task": task,
            "language": language,
            "start_index": start,
            "end_index": end,
            "action_count": len(action_rows),
            "action_format": "absolute Cartesian pose (xyz + Euler xyz + gripper)",
            "action_min": matrix.min(axis=0).tolist(),
            "action_max": matrix.max(axis=0).tolist(),
            "recorded_gripper_values": sorted(set(float(x) for x in matrix[:, -1])),
            "oracle_success": oracle_first_success_step is not None,
            "oracle_first_success_step": oracle_first_success_step,
            "frame_checks": frame_checks,
            "image_dir": str(trace_dir),
        }
        (trace_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        results.append(result)
        print(task, "oracle_success=", result["oracle_success"], "first_step=", oracle_first_success_step, flush=True)
    (args.output / "summary.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
