"""Check whether MCIL stochastic plan/action sampling explains zero success.

Deterministic variants are diagnostic interventions, not the official baseline.
"""

import argparse
import json
from pathlib import Path
from types import MethodType

import hydra
import numpy as np
from omegaconf import OmegaConf
from pytorch_lightning import seed_everything
import torch

from run_calvin_mcil_cpu import load_model_and_environment


def plan_mean(self, obs, goal):
    with torch.no_grad():
        perceptual = self.perceptual_encoder(obs["rgb_obs"], obs["depth_obs"], obs["robot_obs"])
        latent_goal = self.language_goal(goal)
        distribution = self.plan_proposal(perceptual[:, 0], latent_goal)
        plan = distribution.mean
    self.action_decoder.clear_hidden_state()
    return plan, latent_goal


def action_mode(self, logits, log_scales, means):
    selected = torch.argmax(logits, dim=-1, keepdim=True)
    return torch.gather(means, -1, selected).squeeze(-1)


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
    parser.add_argument("--steps", type=int, default=360)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    validation = args.dataset_path / "validation"
    annotations = np.load(validation / "lang_annotations/auto_lang_ann.npy", allow_pickle=True).item()
    start = next(int(bounds[0]) for task, bounds in zip(annotations["language"]["task"], annotations["info"]["indx"]) if task == args.task)
    initial = episode(validation, start)
    seed_everything(0, workers=True)
    model, env = load_model_and_environment(args.train_folder, args.dataset_path, args.checkpoint)
    conf = Path(__import__("calvin_agent").__file__).resolve().parent.parent / "conf"
    oracle = hydra.utils.instantiate(OmegaConf.load(conf / "callbacks/rollout/tasks/new_playtable_tasks.yaml"))
    language = OmegaConf.load(conf / "annotations/new_playtable_validation.yaml")[args.task][0]
    original_plan = model.get_pp_plan_lang
    original_sample = model.action_decoder._sample
    rows = []
    for name, mean_plan, mode_action in (
        ("official_stochastic", False, False),
        ("mean_plan", True, False),
        ("mode_action", False, True),
        ("mean_plan_mode_action", True, True),
    ):
        seed_everything(0, workers=True)
        model.get_pp_plan_lang = MethodType(plan_mean, model) if mean_plan else original_plan
        model.action_decoder._sample = MethodType(action_mode, model.action_decoder) if mode_action else original_sample
        env.reset(robot_obs=initial["robot_obs"], scene_obs=initial["scene_obs"])
        start_info = env.get_info()
        model.reset()
        success_step = None
        actions = []
        for step in range(args.steps):
            with torch.no_grad():
                action = model.step(env.get_obs(), language)
            actions.append(action.detach().cpu().numpy().reshape(-1).tolist())
            _, _, _, info = env.step(action)
            if oracle.get_task_info_for_set(start_info, info, {args.task}):
                success_step = step
                break
        row = {"setting": name, "task": args.task, "success": success_step is not None,
               "success_step": success_step, "executed_steps": len(actions), "actions": actions}
        rows.append(row)
        args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{name}: success={row['success']}, step={success_step}", flush=True)


if __name__ == "__main__":
    main()
