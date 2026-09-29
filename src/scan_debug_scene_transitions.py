"""Find unlabeled LED, slider, and drawer transitions in the small debug set."""

import argparse
import json
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bounds = np.load(args.folder / "ep_start_end_ids.npy")
    all_records = []
    for start, end in bounds:
        states = []
        for index in range(int(start), int(end) + 1):
            with np.load(args.folder / f"episode_{index:07d}.npz") as item:
                states.append(item["scene_obs"][:6].astype(float))
        states = np.asarray(states)
        changes = np.diff(states, axis=0)
        for name, column, threshold in (
            ("slider", 0, 0.15),
            ("drawer", 1, 0.12),
            ("led", 5, 0.5),
        ):
            candidates = []
            for i in range(len(states) - 65):
                delta = states[i + 64, column] - states[i, column]
                if abs(delta) >= threshold:
                    candidates.append({"start_index": int(start + i), "end_index": int(start + i + 64), "delta": float(delta)})
            top = sorted(candidates, key=lambda x: abs(x["delta"]), reverse=True)[:5]
            all_records.append({"name": name, "min": float(states[:, column].min()),
                                "max": float(states[:, column].max()), "max_step_change": float(np.max(np.abs(changes[:, column]))),
                                "candidates": top})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(all_records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(all_records, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
