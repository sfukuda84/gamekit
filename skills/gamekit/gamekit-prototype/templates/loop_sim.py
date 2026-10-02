#!/usr/bin/env python3
"""loop_sim.py - コアループの机上シミュレーション（gamekit-prototype）

仮説: H<n> <仮説の要約>（docs/game/core-loop.md）
判定の基準: <支持 / 棄却の条件>（docs/game/prototype/plan.md）

使い方:
  python3 docs/game/prototype/sim/<名前>.py [--seeds 200] [--json]

- パラメータは PARAMS にまとめる。仮の値には「仮」と書き、G7（gamekit-systems）で systems.md・economy.md に移す。
- 方針（POLICIES）ごとに、シードを変えて試行し、指標の平均と分布を出す。
- 標準ライブラリだけで書く（Python 3.9 以上）。
"""

from __future__ import annotations

import argparse
import json
import random
import statistics

# ---- パラメータ（仮の値。根拠を右に書く）
PARAMS = {
    "session_minutes": 30,      # GP2 の 1 回のプレイ時間
    "action_seconds": 20,       # 1 回の行動にかかる時間（仮）
    "reward_base": 10,          # 1 回の行動の報酬（仮）
    "upgrade_cost_base": 50,    # 最初の強化の値段（仮）
    "upgrade_cost_growth": 1.5, # 強化のたびに値段が何倍になるか（仮）
    "upgrade_bonus": 0.25,      # 1 回の強化で報酬が何割増えるか（仮）
}


def new_state() -> dict:
    return {"money": 0.0, "upgrades": 0, "elapsed": 0.0, "first_upgrade_at": None}


def upgrade_cost(p: dict, n: int) -> float:
    return p["upgrade_cost_base"] * p["upgrade_cost_growth"] ** n


def act(state: dict, p: dict, rng: random.Random) -> None:
    """1 回の行動。報酬はゆらぎを持たせる。"""
    gain = p["reward_base"] * (1 + p["upgrade_bonus"] * state["upgrades"]) * rng.uniform(0.8, 1.2)
    state["money"] += gain
    state["elapsed"] += p["action_seconds"]


# ---- 方針（シミュレーションのプレイヤー）
def policy_greedy(state: dict, p: dict, rng: random.Random) -> None:
    """買えるならすぐ強化する。"""
    act(state, p, rng)
    while state["money"] >= upgrade_cost(p, state["upgrades"]):
        state["money"] -= upgrade_cost(p, state["upgrades"])
        state["upgrades"] += 1
        if state["first_upgrade_at"] is None:
            state["first_upgrade_at"] = state["elapsed"]


def policy_saver(state: dict, p: dict, rng: random.Random) -> None:
    """強化せずにため込む（比較のため）。"""
    act(state, p, rng)


POLICIES = {"greedy": policy_greedy, "saver": policy_saver}


def run_once(policy, p: dict, seed: int) -> dict:
    rng = random.Random(seed)
    state = new_state()
    while state["elapsed"] < p["session_minutes"] * 60:
        policy(state, p, rng)
    return {
        "money_end": state["money"],
        "upgrades": state["upgrades"],
        "first_upgrade_min": (state["first_upgrade_at"] or 0) / 60,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--json", action="store_true", help="結果を JSON で出す")
    args = ap.parse_args()
    summary: dict = {}
    for name, policy in POLICIES.items():
        runs = [run_once(policy, PARAMS, seed) for seed in range(1, args.seeds + 1)]
        summary[name] = {
            k: {"mean": statistics.mean(r[k] for r in runs), "p10": sorted(r[k] for r in runs)[len(runs) // 10],
                "p90": sorted(r[k] for r in runs)[len(runs) * 9 // 10]}
            for k in runs[0]
        }
    if args.json:
        print(json.dumps({"params": PARAMS, "seeds": args.seeds, "summary": summary}, ensure_ascii=False, indent=2))
        return
    print(f"試行: 方針ごとに {args.seeds} シード")
    print("| 方針 | 指標 | 平均 | 下位 10% | 上位 10% |")
    print("|---|---|---|---|---|")
    for name, metrics in summary.items():
        for k, v in metrics.items():
            print(f"| {name} | {k} | {v['mean']:.2f} | {v['p10']:.2f} | {v['p90']:.2f} |")


if __name__ == "__main__":
    main()
