"""Diagnostic action-component ablation on one annotated CALVIN demo."""

import argparse
import json
from pathlib import Path

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
    parser.add_argument("--start-index", type=int)
    parser.add_argument("--end-index", type=int)
    parser.add_argument("--split", choices=["training", "validation"], default="validation")
    parser.add_argument("--model-max-steps", type=int, default=0)
    parser.add_argument("--modes", nargs="+")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    folder = args.dataset_path / args.split
    if args.start_index is not None and args.end_index is not None:
        start, end = args.start_index, args.end_index
    else:
        annotations = np.load(folder / "lang_annotations" / "auto_lang_ann.npy", allow_pickle=True).item()
        chosen = None
        for task, bounds in zip(annotations["language"]["task"], annotations["info"]["indx"]):
            if task == args.task:
                chosen = (int(bounds[0]), int(bounds[1]))
                break
        if chosen is None:
            raise RuntimeError(f"No annotated demonstration for {args.task}")
        start, end = chosen
    initial_record = episode(folder, start)
    demos = [episode(folder, index)["actions"].astype(np.float32) for index in range(start, end + 1)]
    model, env = load_model_and_environment(args.train_folder, args.dataset_path, args.checkpoint)
    conf_dir = Path(__import__("calvin_agent").__file__).resolve().parent.parent / "conf"
    language = OmegaConf.load(conf_dir / "annotations/new_playtable_validation.yaml")[args.task][0]
    oracle = hydra.utils.instantiate(OmegaConf.load(conf_dir / "callbacks/rollout/tasks/new_playtable_tasks.yaml"))
    modes = ["demo", "model", "demo_pose_model_gripper", "model_pose_demo_gripper",
             "model_position_demo_orientation_gripper", "demo_position_model_orientation_demo_gripper"]
    if args.modes:
        modes = args.modes
    results = []
    for mode in modes:
        seed_everything(0, workers=True)
        env.reset(robot_obs=initial_record["robot_obs"], scene_obs=initial_record["scene_obs"])
        initial_info = env.get_info()
        model.reset()
        success_step = None
        raw_model_actions = []
        executed_actions = []
        n_steps = args.model_max_steps if mode == "model" and args.model_max_steps else len(demos)
        for step in range(n_steps):
            demo = demos[min(step, len(demos) - 1)]
            if mode == "demo":
                action = torch.from_numpy(demo).reshape(1, 1, 7)
            else:
                with torch.no_grad():
                    model_action = model.step(env.get_obs(), language)
                raw = model_action.detach().cpu().numpy().reshape(-1)
                raw_model_actions.append(raw.tolist())
                if mode == "model":
                    action = model_action
                elif mode == "demo_pose_model_gripper":
                    combined = np.concatenate((demo[:6], raw[6:7]))
                    action = torch.from_numpy(combined).reshape(1, 1, 7)
                elif mode == "model_pose_demo_gripper":
                    combined = np.concatenate((raw[:6], demo[6:7]))
                    action = torch.from_numpy(combined).reshape(1, 1, 7)
                elif mode == "model_position_demo_orientation_gripper":
                    combined = np.concatenate((raw[:3], demo[3:7]))
                    action = torch.from_numpy(combined).reshape(1, 1, 7)
                else:
                    combined = np.concatenate((demo[:3], raw[3:6], demo[6:7]))
                    action = torch.from_numpy(combined).reshape(1, 1, 7)
            executed_actions.append(action.detach().cpu().numpy().reshape(-1).tolist())
            _, _, _, info = env.step(action)
            if oracle.get_task_info_for_set(initial_info, info, {args.task}) and success_step is None:
                success_step = step
        result = {
            "mode": mode,
            "task": args.task,
            "split": args.split,
            "start_index": start,
            "end_index": end,
            "steps": n_steps,
            "success": success_step is not None,
            "success_step": success_step,
            "executed_actions": executed_actions,
            "raw_model_actions": raw_model_actions,
        }
        results.append(result)
        args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{mode}: success={result['success']}, step={success_step}", flush=True)


if __name__ == "__main__":
    main()
