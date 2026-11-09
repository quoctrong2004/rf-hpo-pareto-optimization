"""Đồ án Nhập môn Tối ưu hóa: Random Forest HPO và Pareto.

Chạy từ thư mục gốc dự án bằng: python run_project.py
Toàn bộ kết quả được ghi vào results/ và figures/ để có thể kiểm tra, tái lập.
"""
from __future__ import annotations

import json
import os
import platform
import sys
import time
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Any

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import optuna
import pandas as pd
import sklearn
from optuna.samplers import NSGAIISampler, TPESampler
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    ParameterGrid,
    ParameterSampler,
    StratifiedKFold,
    cross_val_score,
    train_test_split,
)
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = ROOT / "figures"
MODELS_DIR = ROOT / "models"

# Ngân sách được giữ giống nhau giữa ba phương pháp HPO đơn mục tiêu.
SEARCH_SEEDS = [17, 42, 73]
CV_FOLDS = 5
TRIALS_PER_METHOD_PER_SEED = 24

# 3 x 2 x 2 x 2 = 24 cấu hình. Các giá trị đủ nhỏ để chạy trên máy cá nhân.
SEARCH_SPACE = {
    "n_estimators": [20, 40, 60],
    "max_depth": [None, 10],
    "min_samples_split": [2, 5],
    "max_features": ["sqrt", "log2"],
}

# NSGA-II dùng miền rộng hơn để tạo nhiều phương án đánh đổi.
NSGA2_TRIALS = 20
NSGA2_POPULATION_SIZE = 10


def ensure_directories() -> None:
    """Tạo các thư mục đầu ra nếu chúng chưa tồn tại."""
    for folder in (RESULTS_DIR, FIGURES_DIR, MODELS_DIR):
        folder.mkdir(parents=True, exist_ok=True)


def load_data() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Tải dataset từ scikit-learn và khóa 20% dữ liệu test."""
    X, y = load_breast_cancer(return_X_y=True)
    X_dev, X_test, y_dev, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        stratify=y,
        random_state=42,
    )
    return X_dev, X_test, y_dev, y_test


def build_model(params: dict[str, Any] | None, seed: int) -> RandomForestClassifier:
    """Tạo Random Forest với random_state được kiểm soát."""
    config = dict(params or {})
    config["random_state"] = seed
    config["n_jobs"] = 1
    return RandomForestClassifier(**config)


def evaluate_cv(
    params: dict[str, Any] | None,
    X_dev: np.ndarray,
    y_dev: np.ndarray,
    seed: int,
) -> tuple[float, float, list[float], float]:
    """Đánh giá một cấu hình bằng Stratified 5-fold CV.

    Hàm này tuyệt đối không nhận X_test hoặc y_test, do đó test không thể lọt
    vào quá trình tuning.
    """
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=seed)
    model = build_model(params, seed)
    start = time.perf_counter()
    scores = cross_val_score(
        model,
        X_dev,
        y_dev,
        scoring="accuracy",
        cv=cv,
        n_jobs=1,
        error_score="raise",
    )
    elapsed = time.perf_counter() - start
    return float(np.mean(scores)), float(np.std(scores, ddof=1)), scores.tolist(), elapsed


def config_to_json(params: dict[str, Any]) -> str:
    """Chuyển cấu hình thành JSON dễ lưu trong CSV."""
    return json.dumps(params, ensure_ascii=False, sort_keys=True)


def run_single_objective_searches(
    X_dev: np.ndarray,
    y_dev: np.ndarray,
    methods: tuple[str, ...] | list[str] = ("Grid Search", "Random Search", "Optuna TPE"),
    seeds: list[int] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Chạy Grid Search, Random Search và TPE với budget bằng nhau.

    Mỗi thuật toán chạy 24 trial x 3 random seeds. Mỗi trial đều dùng cùng
    5-fold CV và cùng miền hyperparameter.
    """
    all_rows: list[dict[str, Any]] = []
    seed_rows: list[dict[str, Any]] = []

    grid_configs = list(ParameterGrid(SEARCH_SPACE))
    if len(grid_configs) != TRIALS_PER_METHOD_PER_SEED:
        raise ValueError("Search space không khớp evaluation budget đã khai báo.")

    run_seeds = seeds if seeds is not None else SEARCH_SEEDS
    for method in methods:
        for seed in run_seeds:
            print(f"[HPO] {method} | seed={seed} | budget={TRIALS_PER_METHOD_PER_SEED}", flush=True)
            method_start = time.perf_counter()
            rows_for_run: list[dict[str, Any]] = []

            if method == "Grid Search":
                configs = grid_configs
                for index, params in enumerate(configs, start=1):
                    mean_score, std_score, fold_scores, eval_time = evaluate_cv(
                        params, X_dev, y_dev, seed
                    )
                    rows_for_run.append({
                        "method": method,
                        "seed": seed,
                        "trial": index,
                        "params": config_to_json(params),
                        "cv_accuracy": mean_score,
                        "cv_std": std_score,
                        "fold_scores": json.dumps(fold_scores),
                        "evaluation_time_sec": eval_time,
                    })

            elif method == "Random Search":
                # Vì mọi phân phối đều là danh sách hữu hạn và n_iter bằng
                # tổng số tổ hợp, ParameterSampler lấy đủ 24 cấu hình.
                configs = list(ParameterSampler(
                    SEARCH_SPACE,
                    n_iter=TRIALS_PER_METHOD_PER_SEED,
                    random_state=seed,
                ))
                for index, params in enumerate(configs, start=1):
                    mean_score, std_score, fold_scores, eval_time = evaluate_cv(
                        params, X_dev, y_dev, seed
                    )
                    rows_for_run.append({
                        "method": method,
                        "seed": seed,
                        "trial": index,
                        "params": config_to_json(params),
                        "cv_accuracy": mean_score,
                        "cv_std": std_score,
                        "fold_scores": json.dumps(fold_scores),
                        "evaluation_time_sec": eval_time,
                    })

            else:
                sampler = TPESampler(seed=seed, n_startup_trials=8)
                study = optuna.create_study(direction="maximize", sampler=sampler)

                def objective(trial: optuna.Trial) -> float:
                    params = {
                        "n_estimators": trial.suggest_categorical(
                            "n_estimators", SEARCH_SPACE["n_estimators"]
                        ),
                        "max_depth": trial.suggest_categorical(
                            "max_depth", SEARCH_SPACE["max_depth"]
                        ),
                        "min_samples_split": trial.suggest_categorical(
                            "min_samples_split", SEARCH_SPACE["min_samples_split"]
                        ),
                        "max_features": trial.suggest_categorical(
                            "max_features", SEARCH_SPACE["max_features"]
                        ),
                    }
                    mean_score, std_score, fold_scores, eval_time = evaluate_cv(
                        params, X_dev, y_dev, seed
                    )
                    trial.set_user_attr("cv_std", std_score)
                    trial.set_user_attr("fold_scores", fold_scores)
                    trial.set_user_attr("evaluation_time_sec", eval_time)
                    return mean_score

                study.optimize(
                    objective,
                    n_trials=TRIALS_PER_METHOD_PER_SEED,
                    show_progress_bar=False,
                    n_jobs=1,
                )
                for trial in study.trials:
                    rows_for_run.append({
                        "method": method,
                        "seed": seed,
                        "trial": trial.number + 1,
                        "params": config_to_json(trial.params),
                        "cv_accuracy": float(trial.value),
                        "cv_std": float(trial.user_attrs["cv_std"]),
                        "fold_scores": json.dumps(trial.user_attrs["fold_scores"]),
                        "evaluation_time_sec": float(trial.user_attrs["evaluation_time_sec"]),
                    })

            rows_for_run.sort(key=lambda row: row["trial"])
            best_so_far = -np.inf
            elapsed_so_far = 0.0
            for row in rows_for_run:
                best_so_far = max(best_so_far, row["cv_accuracy"])
                elapsed_so_far += row["evaluation_time_sec"]
                row["best_so_far"] = best_so_far
                row["elapsed_total_sec"] = elapsed_so_far
                all_rows.append(row)

            best_row = max(rows_for_run, key=lambda row: row["cv_accuracy"])
            seed_rows.append({
                "method": method,
                "seed": seed,
                "best_cv_accuracy": best_row["cv_accuracy"],
                "best_cv_std": best_row["cv_std"],
                "best_trial": best_row["trial"],
                "best_params": best_row["params"],
                "evaluation_budget": len(rows_for_run),
                "search_time_sec": time.perf_counter() - method_start,
                "sum_fit_evaluation_sec": sum(
                    row["evaluation_time_sec"] for row in rows_for_run
                ),
            })

    history = pd.DataFrame(all_rows)
    seed_summary = pd.DataFrame(seed_rows)
    method_summary = (
        seed_summary.groupby("method", as_index=False)
        .agg(
            best_cv_accuracy_mean=("best_cv_accuracy", "mean"),
            best_cv_accuracy_std=("best_cv_accuracy", "std"),
            search_time_mean_sec=("search_time_sec", "mean"),
            search_time_std_sec=("search_time_sec", "std"),
            evaluations_per_seed=("evaluation_budget", "mean"),
        )
    )
    method_summary["total_evaluations"] = (
        method_summary["evaluations_per_seed"] * len(SEARCH_SEEDS)
    ).astype(int)

    if len(methods) == 1:
        slug = methods[0].lower().replace(" ", "_")
        history.to_csv(RESULTS_DIR / f"cv_search_history_{slug}.csv", index=False)
        seed_summary.to_csv(RESULTS_DIR / f"search_seed_summary_{slug}.csv", index=False)
        method_summary.to_csv(RESULTS_DIR / f"search_method_summary_{slug}.csv", index=False)
    else:
        history.to_csv(RESULTS_DIR / "cv_search_history.csv", index=False)
        seed_summary.to_csv(RESULTS_DIR / "search_seed_summary.csv", index=False)
        method_summary.to_csv(RESULTS_DIR / "search_method_summary.csv", index=False)
    return history, seed_summary, method_summary


def measure_latency(
    model: RandomForestClassifier,
    X_sample: np.ndarray,
    warmup_runs: int = 10,
    measured_runs: int = 60,
) -> tuple[float, float, list[float]]:
    """Đo latency dự đoán cho một mẫu sau warm-up.

    Đơn vị là mili giây/lần dự đoán cho một mẫu. Đây là phép đo trên máy đang
    chạy đồ án, không phải cam kết latency trên mọi máy tính.
    """
    for _ in range(warmup_runs):
        model.predict(X_sample)

    samples: list[float] = []
    for _ in range(measured_runs):
        start = time.perf_counter_ns()
        model.predict(X_sample)
        end = time.perf_counter_ns()
        samples.append((end - start) / 1_000_000.0)
    return float(np.median(samples)), float(np.percentile(samples, 95)), samples


def total_tree_nodes(model: RandomForestClassifier) -> int:
    """Đếm tổng số node của tất cả cây, dùng làm proxy cho complexity."""
    return int(sum(tree.tree_.node_count for tree in model.estimators_))


def is_dominated(candidate: dict[str, float], others: list[dict[str, float]]) -> bool:
    """Kiểm tra dominance cho accuracy (maximize), latency/nodes (minimize)."""
    for other in others:
        no_worse = (
            other["accuracy"] >= candidate["accuracy"]
            and other["latency_ms"] <= candidate["latency_ms"]
            and other["total_nodes"] <= candidate["total_nodes"]
        )
        strictly_better = (
            other["accuracy"] > candidate["accuracy"]
            or other["latency_ms"] < candidate["latency_ms"]
            or other["total_nodes"] < candidate["total_nodes"]
        )
        if no_worse and strictly_better:
            return True
    return False


def run_nsga2(
    X_dev: np.ndarray, y_dev: np.ndarray
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Chạy NSGA-II để tối ưu đồng thời accuracy, latency và complexity."""
    db_path = RESULTS_DIR / "nsga2_study.db"
    if db_path.exists():
        db_path.unlink()
    storage_url = f"sqlite:///{db_path.as_posix()}"

    sampler = NSGAIISampler(
        seed=42,
        population_size=NSGA2_POPULATION_SIZE,
    )
    study = optuna.create_study(
        study_name="random_forest_accuracy_latency_complexity",
        directions=["maximize", "minimize", "minimize"],
        sampler=sampler,
        storage=storage_url,
        load_if_exists=False,
    )

    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=42)
    print(f"[NSGA-II] budget={NSGA2_TRIALS}", flush=True)

    def objective(trial: optuna.Trial) -> tuple[float, float, int]:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 20, 80, step=10),
            "max_depth": trial.suggest_categorical(
                "max_depth", [None, 4, 6, 8, 10, 12, 16, 20]
            ),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 12),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 5),
            "max_features": trial.suggest_categorical(
                "max_features", ["sqrt", "log2", None]
            ),
        }

        cv_start = time.perf_counter()
        scores = cross_val_score(
            build_model(params, 42),
            X_dev,
            y_dev,
            scoring="accuracy",
            cv=cv,
            n_jobs=1,
            error_score="raise",
        )
        cv_elapsed = time.perf_counter() - cv_start
        accuracy = float(np.mean(scores))

        # Latency và complexity được đo trên model fit bằng development set.
        # Test set không xuất hiện trong objective.
        model = build_model(params, 42)
        fit_start = time.perf_counter()
        model.fit(X_dev, y_dev)
        fit_elapsed = time.perf_counter() - fit_start
        latency_median, latency_p95, _ = measure_latency(
            model, X_dev[:1], warmup_runs=5, measured_runs=15
        )
        nodes = total_tree_nodes(model)

        trial.set_user_attr("cv_std", float(np.std(scores, ddof=1)))
        trial.set_user_attr("cv_time_sec", cv_elapsed)
        trial.set_user_attr("fit_time_sec", fit_elapsed)
        trial.set_user_attr("latency_p95_ms", latency_p95)
        trial.set_user_attr("total_nodes", nodes)
        return accuracy, latency_median, nodes

    study.optimize(objective, n_trials=NSGA2_TRIALS, show_progress_bar=False, n_jobs=1)

    trial_rows: list[dict[str, Any]] = []
    for trial in study.trials:
        if trial.values is None:
            continue
        trial_rows.append({
            "trial": trial.number + 1,
            "state": trial.state.name,
            "cv_accuracy": float(trial.values[0]),
            "latency_median_ms": float(trial.values[1]),
            "total_nodes": int(trial.values[2]),
            "latency_p95_ms": float(trial.user_attrs["latency_p95_ms"]),
            "cv_std": float(trial.user_attrs["cv_std"]),
            "cv_time_sec": float(trial.user_attrs["cv_time_sec"]),
            "fit_time_sec": float(trial.user_attrs["fit_time_sec"]),
            "params": config_to_json(trial.params),
        })

    trials_df = pd.DataFrame(trial_rows)
    objectives = [
        {
            "accuracy": float(row.cv_accuracy),
            "latency_ms": float(row.latency_median_ms),
            "total_nodes": int(row.total_nodes),
        }
        for row in trials_df.itertuples()
    ]
    non_dominated_indices = []
    for index, candidate in enumerate(objectives):
        if not is_dominated(candidate, objectives[:index] + objectives[index + 1:]):
            non_dominated_indices.append(index)
    trials_df["pareto_optimal"] = False
    if non_dominated_indices:
        trials_df.loc[non_dominated_indices, "pareto_optimal"] = True
    pareto_df = trials_df[trials_df["pareto_optimal"]].copy()

    # Chọn knee thực dụng: chuẩn hóa 3 mục tiêu, rồi lấy nghiệm gần điểm lý tưởng.
    # Error = 1-accuracy; hai mục tiêu còn lại đã theo hướng minimize.
    pareto_df["error"] = 1.0 - pareto_df["cv_accuracy"]
    objective_cols = ["error", "latency_median_ms", "total_nodes"]
    normalized = pareto_df[objective_cols].copy()
    for column in objective_cols:
        low = normalized[column].min()
        high = normalized[column].max()
        if high > low:
            normalized[column] = (normalized[column] - low) / (high - low)
        else:
            normalized[column] = 0.0
    pareto_df["distance_to_ideal"] = np.sqrt(
        (normalized ** 2).sum(axis=1)
    ).to_numpy()
    knee_row = pareto_df.sort_values(
        ["distance_to_ideal", "cv_accuracy"], ascending=[True, False]
    ).iloc[0]
    knee = {
        "trial": int(knee_row["trial"]),
        "params": json.loads(knee_row["params"]),
        "cv_accuracy": float(knee_row["cv_accuracy"]),
        "latency_median_ms": float(knee_row["latency_median_ms"]),
        "latency_p95_ms": float(knee_row["latency_p95_ms"]),
        "total_nodes": int(knee_row["total_nodes"]),
        "distance_to_ideal": float(knee_row["distance_to_ideal"]),
    }

    trials_df.to_csv(RESULTS_DIR / "nsga2_all_trials.csv", index=False)
    pareto_df.to_csv(RESULTS_DIR / "pareto_front.csv", index=False)
    with open(RESULTS_DIR / "pareto_knee_selection.json", "w", encoding="utf-8") as f:
        json.dump(knee, f, ensure_ascii=False, indent=2)

    return trials_df, pareto_df, knee


def fit_and_evaluate_final_models(
    X_dev: np.ndarray,
    X_test: np.ndarray,
    y_dev: np.ndarray,
    y_test: np.ndarray,
    baseline_cv: dict[str, float],
    best_hpo: dict[str, Any],
    knee: dict[str, Any],
) -> pd.DataFrame:
    """Refit các lựa chọn đã khóa và đánh giá test ở bước cuối."""
    candidates = [
        ("Baseline mặc định", {}, 42),
        ("Best HPO (CV cao nhất)", best_hpo["params"], best_hpo["seed"]),
        ("Pareto knee (NSGA-II)", knee["params"], 42),
    ]
    metric_rows: list[dict[str, Any]] = []

    for name, params, seed in candidates:
        model = build_model(params, seed)
        start = time.perf_counter()
        model.fit(X_dev, y_dev)
        fit_time = time.perf_counter() - start

        # Đây là lần đánh giá test cuối cùng sau khi lựa chọn đã hoàn tất.
        predictions = model.predict(X_test)
        probabilities = model.predict_proba(X_test)[:, 1]
        accuracy = accuracy_score(y_test, predictions)
        precision = precision_score(y_test, predictions, zero_division=0)
        recall = recall_score(y_test, predictions, zero_division=0)
        f1 = f1_score(y_test, predictions, zero_division=0)
        roc_auc = roc_auc_score(y_test, probabilities)
        latency_median, latency_p95, _ = measure_latency(
            model, X_test[:1], warmup_runs=10, measured_runs=100
        )
        nodes = total_tree_nodes(model)

        safe_name = {
            "Baseline mặc định": "baseline",
            "Best HPO (CV cao nhất)": "best_hpo",
            "Pareto knee (NSGA-II)": "final_pareto_model",
        }[name]
        model_path = MODELS_DIR / f"{safe_name}.joblib"
        joblib.dump(model, model_path)
        model_size_mb = model_path.stat().st_size / (1024 ** 2)

        metric_rows.append({
            "model": name,
            "params": config_to_json(params),
            "cv_accuracy_mean": baseline_cv["mean"] if name == "Baseline mặc định" else (
                best_hpo["cv_accuracy"] if name == "Best HPO (CV cao nhất)" else knee["cv_accuracy"]
            ),
            "test_accuracy": float(accuracy),
            "test_precision": float(precision),
            "test_recall": float(recall),
            "test_f1": float(f1),
            "test_roc_auc": float(roc_auc),
            "fit_time_sec": fit_time,
            "latency_median_ms": latency_median,
            "latency_p95_ms": latency_p95,
            "total_nodes": nodes,
            "model_size_mb": model_size_mb,
            "model_file": str(model_path.relative_to(ROOT)),
        })

    metrics_df = pd.DataFrame(metric_rows)
    metrics_df.to_csv(RESULTS_DIR / "final_model_metrics.csv", index=False)
    with open(RESULTS_DIR / "selected_configs.json", "w", encoding="utf-8") as f:
        json.dump({
            "best_hpo": best_hpo,
            "pareto_knee": knee,
        }, f, ensure_ascii=False, indent=2)
    return metrics_df


def create_figures(
    history: pd.DataFrame,
    method_summary: pd.DataFrame,
    trials_df: pd.DataFrame,
    pareto_df: pd.DataFrame,
    knee: dict[str, Any],
) -> None:
    """Vẽ biểu đồ hội tụ, so sánh phương pháp và Pareto front."""
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.titleweight": "bold",
        "figure.dpi": 140,
    })

    fig, ax = plt.subplots(figsize=(9, 5.2))
    for method in ("Grid Search", "Random Search", "Optuna TPE"):
        subset = history[history["method"] == method]
        pivot = subset.pivot(index="trial", columns="seed", values="best_so_far")
        mean = pivot.mean(axis=1)
        std = pivot.std(axis=1).fillna(0.0)
        ax.plot(mean.index, mean.values, label=method, linewidth=2)
        ax.fill_between(mean.index, mean.values - std.values, mean.values + std.values, alpha=0.12)
    ax.set_title("Best-so-far validation accuracy theo số lần đánh giá")
    ax.set_xlabel("Số trial đã thực hiện")
    ax.set_ylabel("Best-so-far 5-fold CV accuracy")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "01_best_so_far.png", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.8, 5.5))
    ax.scatter(
        trials_df["latency_median_ms"],
        trials_df["cv_accuracy"],
        alpha=0.35,
        label="Tất cả trial NSGA-II",
    )
    ax.scatter(
        pareto_df["latency_median_ms"],
        pareto_df["cv_accuracy"],
        s=55,
        label="Pareto front",
    )
    ax.scatter(
        [knee["latency_median_ms"]],
        [knee["cv_accuracy"]],
        marker="*",
        s=220,
        label="Knee được chọn",
    )
    ax.set_title("Pareto trade-off: Accuracy và Inference Latency")
    ax.set_xlabel("Median latency (ms / 1 mẫu, máy chạy thí nghiệm)")
    ax.set_ylabel("5-fold CV accuracy")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "02_pareto_accuracy_latency.png", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.8, 5.5))
    ax.scatter(
        trials_df["total_nodes"],
        trials_df["cv_accuracy"],
        alpha=0.35,
        label="Tất cả trial NSGA-II",
    )
    ax.scatter(
        pareto_df["total_nodes"],
        pareto_df["cv_accuracy"],
        s=55,
        label="Pareto front",
    )
    ax.scatter(
        [knee["total_nodes"]],
        [knee["cv_accuracy"]],
        marker="*",
        s=220,
        label="Knee được chọn",
    )
    ax.set_title("Pareto trade-off: Accuracy và Complexity")
    ax.set_xlabel("Tổng số node của các cây")
    ax.set_ylabel("5-fold CV accuracy")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "03_pareto_accuracy_complexity.png", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.5, 5.0))
    ordered = method_summary.set_index("method").loc[
        ["Grid Search", "Random Search", "Optuna TPE"]
    ].reset_index()
    ax.bar(
        ordered["method"],
        ordered["best_cv_accuracy_mean"],
        yerr=ordered["best_cv_accuracy_std"],
        capsize=5,
    )
    ax.set_title("So sánh best CV accuracy trung bình qua 3 seeds")
    ax.set_ylabel("Best 5-fold CV accuracy (mean ± std)")
    ax.set_ylim(max(0.0, ordered["best_cv_accuracy_mean"].min() - 0.03), 1.0)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "04_method_comparison.png", bbox_inches="tight")
    plt.close(fig)


def write_run_metadata(X_dev: np.ndarray, X_test: np.ndarray) -> None:
    """Ghi cấu hình và phiên bản thư viện để tái lập thí nghiệm."""
    metadata = {
        "project": "Random Forest HPO and Pareto Optimization",
        "run_timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "python_version": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor() or "Not reported",
        "cpu_count": os.cpu_count(),
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "scikit_learn_version": sklearn.__version__,
        "optuna_version": optuna.__version__,
        "development_samples": int(X_dev.shape[0]),
        "test_samples": int(X_test.shape[0]),
        "number_of_features": int(X_dev.shape[1]),
        "test_split": 0.20,
        "split_random_state": 42,
        "cv_folds": CV_FOLDS,
        "search_seeds": SEARCH_SEEDS,
        "trials_per_method_per_seed": TRIALS_PER_METHOD_PER_SEED,
        "nsga2_trials": NSGA2_TRIALS,
        "nsga2_population_size": NSGA2_POPULATION_SIZE,
        "single_objective_search_space": SEARCH_SPACE,
        "multi_objective_directions": ["maximize accuracy", "minimize latency_ms", "minimize total_nodes"],
        "latency_protocol": "NSGA-II trials: 5 warm-up runs + 15 measured runs, median is objective; final models: 10 warm-up runs + 100 measured runs",
        "complexity_proxy": "sum of node counts across all trees in RandomForest",
        "test_usage": "locked during tuning; used only for final report of pre-selected candidates",
    }
    with open(RESULTS_DIR / "run_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def write_results_summary(
    method_summary: pd.DataFrame,
    metrics_df: pd.DataFrame,
    pareto_df: pd.DataFrame,
    knee: dict[str, Any],
) -> None:
    """Ghi phần tóm tắt kết quả dựa trên số liệu thực tế vừa chạy."""
    method_lines = []
    for row in method_summary.itertuples():
        method_lines.append(
            f"- {row.method}: best CV accuracy = {row.best_cv_accuracy_mean:.4f} "
            f"± {row.best_cv_accuracy_std:.4f}; average wall time = {row.search_time_mean_sec:.2f} s."
        )
    metric_lines = []
    for row in metrics_df.itertuples():
        metric_lines.append(
            f"- {row.model}: test accuracy = {row.test_accuracy:.4f}; "
            f"median latency = {row.latency_median_ms:.4f} ms; "
            f"total nodes = {row.total_nodes:,}; model size = {row.model_size_mb:.3f} MB."
        )
    content = [
        "# Tóm tắt kết quả thực nghiệm",
        "",
        "## HPO đơn mục tiêu (3 seeds, mỗi seed 24 trial, 5-fold CV)",
        *method_lines,
        "",
        f"## NSGA-II",
        f"- Tổng trial: {NSGA2_TRIALS}",
        f"- Số nghiệm Pareto: {len(pareto_df)}",
        f"- Nghiệm knee: trial {knee['trial']}, CV accuracy {knee['cv_accuracy']:.4f}, "
        f"latency median {knee['latency_median_ms']:.4f} ms, total nodes {knee['total_nodes']:,}.",
        "",
        "## Đánh giá cuối trên test set đã khóa",
        *metric_lines,
        "",
        "Lưu ý: latency phụ thuộc máy chạy, hệ điều hành, tải nền và cách triển khai. "
        "Không xem latency đo trong đồ án là cam kết hiệu năng trên thiết bị khác.",
    ]
    (RESULTS_DIR / "RESULTS_SUMMARY.md").write_text("\n".join(content), encoding="utf-8")


def run_experiments() -> None:
    """Chạy toàn bộ đồ án từ dữ liệu đến bảng kết quả và biểu đồ."""
    ensure_directories()
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    print("[1/6] Nạp Breast Cancer Wisconsin và tách development/test...", flush=True)
    X_dev, X_test, y_dev, y_test = load_data()

    print(f"[2/6] Tính baseline mặc định bằng 5-fold CV qua {len(SEARCH_SEEDS)} seeds...", flush=True)
    baseline_scores = []
    for seed in SEARCH_SEEDS:
        mean_score, std_score, fold_scores, elapsed = evaluate_cv(
            None, X_dev, y_dev, seed
        )
        baseline_scores.append({
            "seed": seed,
            "cv_accuracy": mean_score,
            "cv_std": std_score,
            "fold_scores": json.dumps(fold_scores),
            "evaluation_time_sec": elapsed,
        })
    baseline_df = pd.DataFrame(baseline_scores)
    baseline_df.to_csv(RESULTS_DIR / "baseline_cv.csv", index=False)
    baseline_cv = {
        "mean": float(baseline_df["cv_accuracy"].mean()),
        "std": float(baseline_df["cv_accuracy"].std(ddof=1)),
    }

    print("[3/6] So sánh Grid Search, Random Search và Optuna/TPE...", flush=True)
    history, seed_summary, method_summary = run_single_objective_searches(X_dev, y_dev)

    print("[4/6] Chạy NSGA-II cho 3 mục tiêu...", flush=True)
    trials_df, pareto_df, knee = run_nsga2(X_dev, y_dev)

    # Lựa chọn cấu hình HPO tốt nhất chỉ bằng CV trên development set.
    best_row = history.sort_values(
        ["cv_accuracy", "cv_std"], ascending=[False, True]
    ).iloc[0]
    best_hpo = {
        "method": str(best_row["method"]),
        "seed": int(best_row["seed"]),
        "trial": int(best_row["trial"]),
        "cv_accuracy": float(best_row["cv_accuracy"]),
        "cv_std": float(best_row["cv_std"]),
        "params": json.loads(best_row["params"]),
    }

    print("[5/6] Refit các cấu hình đã khóa và đánh giá test ở cuối...", flush=True)
    metrics_df = fit_and_evaluate_final_models(
        X_dev, X_test, y_dev, y_test, baseline_cv, best_hpo, knee
    )

    print("[6/6] Tạo biểu đồ, metadata và tóm tắt...", flush=True)
    create_figures(history, method_summary, trials_df, pareto_df, knee)
    write_run_metadata(X_dev, X_test)
    write_results_summary(method_summary, metrics_df, pareto_df, knee)

    print("\nHOÀN TẤT. Các bảng nằm trong results/ và biểu đồ trong figures/.", flush=True)
    print(f"Baseline CV: {baseline_cv['mean']:.4f} ± {baseline_cv['std']:.4f}")
    print(f"Best HPO CV: {best_hpo['cv_accuracy']:.4f} ({best_hpo['method']})")
    print(f"Pareto front: {len(pareto_df)} nghiệm; knee trial={knee['trial']}")
    print(metrics_df[["model", "test_accuracy", "latency_median_ms", "total_nodes"]].to_string(index=False))


if __name__ == "__main__":
    with threadpool_limits(limits=1):
        run_experiments()
