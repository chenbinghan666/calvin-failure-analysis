"""Test MCIL actions on recorded demonstration states, without rollout drift."""

import argparse
import json
from pathlib import Path

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
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    seed_everything(0, workers=True)
    folder = args.dataset_path / args.split
    if args.start_index is not None and args.end_index is not None:
        start, end = args.start_index, args.end_index
    else:
        ann = np.load(folder / "lang_annotations" / "auto_lang_ann.npy", allow_pickle=True).item()
        chosen = None
        for task, bounds in zip(ann["language"]["task"], ann["info"]["indx"]):
            if task == args.task:
                chosen = (int(bounds[0]), int(bounds[1]))
                break
        if chosen is None:
            raise RuntimeError(f"No annotated demonstration for {args.task}")
        start, end = chosen
    model, env = load_model_and_environment(args.train_folder, args.dataset_path, args.checkpoint)
    official = OmegaConf.load(
        Path(__import__("calvin_agent").__file__).resolve().parent.parent
        / "conf/annotations/new_playtable_validation.yaml"
    )
    language = official[args.task][0]
    model.reset()
    rows = []
    for step, index in enumerate(range(start, end + 1)):
        record = episode(folder, index)
        env.reset(robot_obs=record["robot_obs"], scene_obs=record["scene_obs"])
        with torch.no_grad():
            predicted = model.step(env.get_obs(), language)
        pred = predicted.detach().cpu().numpy().reshape(-1)
        demo = record["actions"].reshape(-1)
        rows.append({
            "step": step,
            "demo_action": demo.tolist(),
            "mcil_action": pred.tolist(),
            "position_error": float(np.linalg.norm(pred[:3] - demo[:3])),
            "orientation_error": float(np.linalg.norm(pred[3:6] - demo[3:6])),
            "gripper_sign_match": bool(np.sign(pred[-1]) == np.sign(demo[-1])),
        })
    summary = {
        "task": args.task,
        "split": args.split,
        "start_index": start,
        "end_index": end,
        "language": language,
        "steps": len(rows),
        "position_error_mean": float(np.mean([x["position_error"] for x in rows])),
        "orientation_error_mean": float(np.mean([x["orientation_error"] for x in rows])),
        "gripper_sign_accuracy": float(np.mean([x["gripper_sign_match"] for x in rows])),
        "position_errors_first_10": [x["position_error"] for x in rows[:10]],
        "gripper_first_mismatch_step": next((x["step"] for x in rows if not x["gripper_sign_match"]), None),
        "rows": rows,
    }
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2), flush=True)


if __name__ == "__main__":
    main()
