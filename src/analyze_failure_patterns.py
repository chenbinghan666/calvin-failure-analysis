from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def safe_rate(numerator: float, denominator: float) -> float | None:
    return None if denominator == 0 else numerator / denominator


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    numeric = [
        "task_length", "completed_steps", "task_success", "first_failure_step",
        "propagation_observed", "propagation_length", "recovery_attempted",
        "recovery_success", "recovery_extra_actions",
    ]
    for column in numeric:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df[df["task_success"].notna()].copy()
    if df.empty:
        raise ValueError("序列记录中还没有可分析的数据，请先填写task_success。")
    df["progress_rate"] = df["completed_steps"] / df["task_length"]
    return df


def overall(df: pd.DataFrame) -> pd.DataFrame:
    failures = df[df["task_success"] == 0]
    propagation = df[df["propagation_observed"].notna()]
    recovery = df[df["recovery_attempted"] == 1]
    annotated = failures[
        failures["root_cause"].notna() & (failures["root_cause"] != "UNC")
    ]
    rows = [
        ("有效运行数", len(df)),
        ("任务级Success Rate", df["task_success"].mean()),
        ("平均完成比例", df["progress_rate"].mean()),
        ("失败运行数", len(failures)),
        ("失败标注覆盖率", safe_rate(len(annotated), len(failures))),
        ("传播可观察样本数", len(propagation)),
        ("传播发生比例", propagation["propagation_observed"].mean() if len(propagation) else None),
        ("平均传播长度", df["propagation_length"].mean()),
        ("恢复尝试数", len(recovery)),
        ("恢复成功率", recovery["recovery_success"].mean() if len(recovery) else None),
    ]
    return pd.DataFrame(rows, columns=["metric", "value"])


def by_length(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for length in range(1, 6):
        rows.append({
            "task_length": length,
            "n": len(df),
            "prefix_success_rate": (df["completed_steps"] >= length).mean(),
            "first_failure_count": (df["first_failure_step"] == length).sum(),
            "cumulative_failure_count": (df["completed_steps"] < length).sum(),
            "propagation_count": ((df["first_failure_step"] == length) & (df["propagation_observed"] == 1)).sum(),
            "recovery_success_count": ((df["first_failure_step"] == length) & (df["recovery_attempted"] == 1) & (df["recovery_success"] == 1)).sum(),
        })
    return pd.DataFrame(rows)


def by_group(df: pd.DataFrame, column: str) -> pd.DataFrame:
    rows = []
    for name, group in df.groupby(column, dropna=False):
        propagation = group[group["propagation_observed"].notna()]
        recovery = group[group["recovery_attempted"] == 1]
        rows.append({
            column: "未填写" if pd.isna(name) else name,
            "n": len(group),
            "task_success_rate": group["task_success"].mean(),
            "mean_progress_rate": group["progress_rate"].mean(),
            "mean_first_failure_step": group["first_failure_step"].mean(),
            "propagation_rate": propagation["propagation_observed"].mean() if len(propagation) else None,
            "recovery_success_rate": recovery["recovery_success"].mean() if len(recovery) else None,
        })
    return pd.DataFrame(rows)


def make_plots(length_df: pd.DataFrame, failure_df: pd.DataFrame, out_dir: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("未安装matplotlib，CSV统计已经生成，暂不输出图片。")
        return
    plt.figure(figsize=(6, 4))
    plt.plot(length_df["task_length"], length_df["prefix_success_rate"], marker="o")
    plt.xticks(range(1, 6))
    plt.ylim(0, 1)
    plt.xlabel("Task length")
    plt.ylabel("Prefix success rate")
    plt.tight_layout()
    plt.savefig(out_dir / "task_length_success.png", dpi=180)
    plt.close()

    counts = failure_df[failure_df["root_cause"] != "未填写"].set_index("root_cause")["n"]
    if not counts.empty:
        plt.figure(figsize=(7, 4))
        counts.plot(kind="bar")
        plt.xlabel("Root cause")
        plt.ylabel("Count")
        plt.tight_layout()
        plt.savefig(out_dir / "failure_type_count.png", dpi=180)
        plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="统计CALVIN长程任务的失败位置、类型、传播和恢复。")
    parser.add_argument("workbook", type=Path, help="第一基线失败模式记录与统计表xlsx路径")
    parser.add_argument("--output", type=Path, default=Path("analysis_output"), help="结果目录")
    args = parser.parse_args()

    raw = pd.read_excel(args.workbook, sheet_name="序列记录", header=3)
    data = prepare(raw)
    args.output.mkdir(parents=True, exist_ok=True)

    overall_df = overall(data)
    length_df = by_length(data)
    failure_df = by_group(data[data["task_success"] == 0], "root_cause")
    model_df = by_group(data, "model_name")

    overall_df.to_csv(args.output / "overall_metrics.csv", index=False, encoding="utf-8-sig")
    length_df.to_csv(args.output / "task_length_metrics.csv", index=False, encoding="utf-8-sig")
    failure_df.to_csv(args.output / "failure_type_metrics.csv", index=False, encoding="utf-8-sig")
    model_df.to_csv(args.output / "model_metrics.csv", index=False, encoding="utf-8-sig")
    make_plots(length_df, failure_df, args.output)
    print(f"有效运行数：{len(data)}")
    print(f"结果目录：{args.output.resolve()}")


if __name__ == "__main__":
    main()
