"""Run a small, reproducible CALVIN MCIL baseline on CPU.

The official CALVIN release fixes inference to CUDA.  Its PyTorch 1.13 build
cannot execute on an RTX 5060 (sm_120), so this runner keeps the official
checkpoint, data pipeline, task oracle and rollout logic but moves the model
to CPU.  It is intended for the first 1/10-sequence verification runs.
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path
from pydoc import locate

import hydra
import cv2
import numpy as np
from hydra.core.global_hydra import GlobalHydra
from omegaconf import OmegaConf
from pytorch_lightning import seed_everything
import torch

from calvin_agent.evaluation import evaluate_policy as official_eval
from calvin_agent.evaluation.multistep_sequences import get_sequences
from calvin_agent.evaluation.utils import get_env_state_for_initial_condition


def load_model_and_environment(train_folder: Path, dataset_path: Path, checkpoint: Path):
    """Load the official MCIL checkpoint and CALVIN validation environment on CPU."""
    cfg = OmegaConf.load(train_folder / ".hydra" / "config.yaml")
    lang_folder = cfg.datamodule.datasets.lang_dataset.lang_folder

    if GlobalHydra.instance().is_initialized():
        GlobalHydra.instance().clear()
    datasets_conf = Path(official_eval.__file__).resolve().parents[2] / "conf" / "datamodule" / "datasets"
    with hydra.initialize_config_dir(config_dir=str(datasets_conf)):
        datasets_cfg = hydra.compose("vision_lang.yaml", overrides=[f"lang_dataset.lang_folder={lang_folder}"])

    cfg.datamodule.datasets = datasets_cfg
    cfg.datamodule.root_data_dir = str(dataset_path)
    data_module = hydra.utils.instantiate(cfg.datamodule, num_workers=0)
    data_module.prepare_data()
    data_module.setup()
    dataset = data_module.val_dataloader().dataset.datasets["lang"]

    rollout_cfg = OmegaConf.load(
        Path(official_eval.__file__).resolve().parents[2] / "conf" / "callbacks" / "rollout" / "default.yaml"
    )
    device = torch.device("cpu")
    env = hydra.utils.instantiate(rollout_cfg.env_cfg, dataset, device, show_gui=False)

    model_cls = locate(cfg.model._target_)
    model = model_cls.load_from_checkpoint(str(checkpoint), map_location=device)
    model.load_lang_embeddings(dataset.abs_datasets_dir / dataset.lang_folder / "embeddings.npy")
    model.freeze()
    if cfg.model.action_decoder.get("load_action_bounds", False):
        model.action_decoder._setup_action_bounds(str(dataset_path), None, None, True)
    model = model.to(device)
    return model, env


def traced_rollout(env, model, task_oracle, subtask, annotations, trace_dir: Path):
    """Run one official-length subtask while retaining sparse frames and actions."""
    trace_dir.mkdir(parents=True, exist_ok=True)
    obs = env.get_obs()
    model.reset()
    start_info = env.get_info()
    language = annotations[subtask][0]
    actions = []
    frame_steps = {0, 29, 59, 119, 179, 239, 359}
    success_step = None
    for step in range(official_eval.EP_LEN):
        with torch.no_grad():
            action = model.step(obs, language)
        action_array = action.detach().cpu().numpy() if torch.is_tensor(action) else np.asarray(action)
        actions.append(action_array.reshape(-1).tolist())
        obs, _, _, current_info = env.step(action)
        if step in frame_steps:
            rgb = env.render(mode="rgb_array")
            cv2.imwrite(str(trace_dir / f"frame_{step:03d}.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        solved = task_oracle.get_task_info_for_set(start_info, current_info, {subtask})
        if solved:
            success_step = step
            break
    action_matrix = np.asarray(actions, dtype=float)
    trace = {
        "language": language,
        "executed_frames": len(actions),
        "success_step": success_step,
        "action_min": action_matrix.min(axis=0).tolist(),
        "action_max": action_matrix.max(axis=0).tolist(),
        "action_mean": action_matrix.mean(axis=0).tolist(),
        "actions": actions,
    }
    (trace_dir / "trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    return success_step is not None, trace


def run_sequences(
    model,
    env,
    count: int,
    output_path: Path,
    trace_dir=None,
    retry_once=False,
    continue_after_failure=False,
):
    """Evaluate the first fixed sequences with the official stop-on-first-failure rule."""
    conf_dir = Path(official_eval.__file__).resolve().parents[2] / "conf"
    task_cfg = OmegaConf.load(conf_dir / "callbacks" / "rollout" / "tasks" / "new_playtable_tasks.yaml")
    task_oracle = hydra.utils.instantiate(task_cfg)
    annotations = OmegaConf.load(conf_dir / "annotations" / "new_playtable_validation.yaml")

    records = []
    plans = defaultdict(list)
    for sequence_index, (initial_state, subtasks) in enumerate(get_sequences(count)):
        robot_obs, scene_obs = get_env_state_for_initial_condition(initial_state)
        env.reset(robot_obs=robot_obs, scene_obs=scene_obs)
        completed = 0
        step_results = []
        for step_index, subtask in enumerate(subtasks, start=1):
            trace = None
            if trace_dir is not None and sequence_index == 0 and step_index == 1:
                success, trace = traced_rollout(env, model, task_oracle, subtask, annotations, trace_dir)
            else:
                success = official_eval.rollout(env, model, task_oracle, subtask, annotations, plans, False)
            step_result = {"step": step_index, "subtask": subtask, "success": bool(success)}
            if trace is not None:
                step_result["trace_summary"] = {k: v for k, v in trace.items() if k != "actions"}
            if not success and retry_once:
                retry_success = official_eval.rollout(
                    env, model, task_oracle, subtask, annotations, plans, False
                )
                step_result["recovery_attempted"] = True
                step_result["recovery_success"] = bool(retry_success)
            step_results.append(step_result)
            if success:
                completed += 1
            elif not continue_after_failure:
                break
        record = {
            "sequence_index": sequence_index,
            "subtasks": list(subtasks),
            "completed_steps": completed,
            "sequence_success": completed == len(subtasks),
            "step_results": step_results,
        }
        records.append(record)
        print(f"sequence {sequence_index}: completed {completed}/{len(subtasks)}", flush=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-path", type=Path, required=True)
    parser.add_argument("--train-folder", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--num-sequences", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trace-dir", type=Path)
    parser.add_argument("--retry-once", action="store_true")
    parser.add_argument("--continue-after-failure", action="store_true")
    parser.add_argument("--load-only", action="store_true")
    args = parser.parse_args()

    seed_everything(0, workers=True)
    model, env = load_model_and_environment(args.train_folder, args.dataset_path, args.checkpoint)
    print("MCIL model and CALVIN environment loaded on CPU", flush=True)
    if not args.load_only:
        run_sequences(
            model,
            env,
            args.num_sequences,
            args.output,
            args.trace_dir,
            args.retry_once,
            args.continue_after_failure,
        )


if __name__ == "__main__":
    main()
