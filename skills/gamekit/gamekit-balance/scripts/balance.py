#!/usr/bin/env python3
"""balance.py - gamekit のバランス検算（目標値の検査、調整値の参照の確認、シミュレーションの実行と判定、基準値との差分）

使い方:
  python3 balance.py [--root <dir>] targets
  python3 balance.py [--root <dir>] params <specs/NNN-name/tuning.md>
  python3 balance.py [--root <dir>] run [--scenario S]... [--feature NNN]
  python3 balance.py [--root <dir>] check [--feature NNN] [--report <path>]
  python3 balance.py [--root <dir>] baseline [--scenario S]...
  python3 balance.py [--root <dir>] diff [--scenario S]...
  python3 balance.py [--root <dir>] coverage

- 目標値: docs/balance/targets.md の表（ID | 指標 | シナリオ | 下限 | 上限 | 根拠 | 機能）
- シミュレーションの出力: <balance.out_dir>/<scenario>.json = {"scenario": str, "seed": int, "metrics": {指標: 数値}}
- 調整値: specs/<NNN>/tuning.md の表（ID | パラメータ | データの場所 | 初期値 | 範囲 | 効く指標 | 備考）。
  データの場所は「ファイル#JSON Pointer」（例: game/data/enemies.json#/slime/hp）
- params の判定: ERROR は表の形式の崩れ（ID の形・重複、データの場所の空欄、JSON として読めない）と、値が数値でないこと。
  ファイルや Pointer がまだない（実装前）、初期値と一致しない、は WARN
- coverage: docs/game/pillars.md の柱（「### 柱 N: …」）と docs/game/core-loop.md の仮説（表の ID が H<n>）が、
  targets.md の「柱と仮説の検算」の表（対象 | 検算の方法 | 根拠）で検算されているかを確かめる。
  行がない・検算の方法が空・存在しない BT を指す、は ERROR。プレイ確認・対象外だけのものは INFO
- 終了コード: 0 成功、1 エラーまたは FAIL（diff では許容を超えた変化）、2 MISSING だけ（check）、3 前提条件を満たさない
macOS / Linux / Windows で動くように、標準ライブラリだけで書く（Python 3.9 以上）。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "gamekit-status" / "scripts"))
import gklib  # noqa: E402

TARGET_ID_RE = re.compile(r"^BT-[0-9]{3,}$")
PARAM_ID_RE = re.compile(r"^TP-[0-9]{3,}$")
FEATURE_NUM_RE = re.compile(r"^([0-9]{3})")
TARGET_COLUMNS = ["ID", "指標", "シナリオ", "下限", "上限", "根拠", "機能"]
COVERAGE_COLUMNS = ["対象", "検算の方法", "根拠"]
PILLAR_HEADING_RE = re.compile(r"^#{2,4}\s*柱\s*([0-9]+)\s*[:：]?")
HYPOTHESIS_ID_RE = re.compile(r"^H[0-9]+$")
BT_REF_RE = re.compile(r"BT-[0-9]{3,}")
PLAYTEST_WORD = "プレイ確認"
EXEMPT_WORD = "対象外"
WHOLE = "全体"


class Precondition(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------- 共通

def to_number(text: str | None) -> float | None:
    """表のセルを数値にする。空・"-"・"—" は None。数値でなければ ValueError。"""
    t = (text or "").strip().replace(",", "").replace("`", "")
    if t in ("", "-", "—", "–"):
        return None
    return float(t)


def fmt(v: float | None) -> str:
    if v is None:
        return "-"
    if float(v).is_integer():
        return str(int(v))
    return f"{v:.4g}"


def is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def feature_num(text: str | None) -> str | None:
    m = FEATURE_NUM_RE.match((text or "").strip())
    return m.group(1) if m else None


def rel(root: Path, p: Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


class Ctx:
    def __init__(self, root: Path):
        self.root = root
        self.cfg = gklib.load_config(root)
        bal = self.cfg.get("balance") or {}
        self.targets_path = gklib.pth(root, self.cfg, "balance") / "targets.md"
        self.out_dir = root / (bal.get("out_dir") or "build/balance")
        self.baseline_dir = root / (bal.get("baseline_dir") or "docs/balance/baseline")
        tol = bal.get("tolerance")
        self.tolerance = float(tol) if is_number(tol) else 0.05

    def out_file(self, scenario: str) -> Path:
        return self.out_dir / f"{scenario}.json"


# ---------------------------------------------------------------- 目標値

def load_targets(ctx: Ctx) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """(正しい行, エラー, 警告)。正しい行は数値に直した下限・上限を持つ。"""
    if not ctx.targets_path.exists():
        raise Precondition("NO_TARGETS", f"{rel(ctx.root, ctx.targets_path)} がありません（gamekit-systems で作る）。")
    rows = gklib.read_table(ctx.targets_path, require="ID")
    errors: list[str] = []
    warns: list[str] = []
    good: list[dict[str, Any]] = []
    seen: dict[str, str] = {}
    if rows:
        missing_cols = [c for c in TARGET_COLUMNS if c not in rows[0]]
        if missing_cols:
            errors.append(f"targets.md の表に列がありません: {', '.join(missing_cols)}")
            return [], errors, warns
    for r in rows:
        line = r.get("_line", "?")
        rid = r.get("ID", "").strip()
        where = f"targets.md:{line} {rid or '(ID なし)'}"
        if not rid or rid.startswith("（") or rid.startswith("("):
            continue  # 記入例・空行
        bad = False
        if not TARGET_ID_RE.match(rid):
            errors.append(f"{where}: ID は BT-001 の形にする")
            bad = True
        elif rid in seen:
            errors.append(f"{where}: ID が重複している（{seen[rid]} 行目）")
            bad = True
        seen.setdefault(rid, line)
        metric = r.get("指標", "").strip().strip("`")
        scenario = r.get("シナリオ", "").strip().strip("`")
        if not metric:
            errors.append(f"{where}: 指標が空")
            bad = True
        if not scenario:
            errors.append(f"{where}: シナリオが空")
            bad = True
        try:
            lo = to_number(r.get("下限"))
            hi = to_number(r.get("上限"))
        except ValueError:
            errors.append(f"{where}: 下限・上限は数値か - にする（{r.get('下限')} / {r.get('上限')}）")
            continue
        if lo is None and hi is None:
            errors.append(f"{where}: 下限と上限の両方が - になっている")
            bad = True
        if lo is not None and hi is not None and lo > hi:
            errors.append(f"{where}: 下限 {fmt(lo)} が上限 {fmt(hi)} より大きい")
            bad = True
        feat = r.get("機能", "").strip()
        if not feat:
            warns.append(f"{where}: 機能が空（{WHOLE} か 001-xxx を書く）")
        elif feat != WHOLE and not feature_num(feat):
            warns.append(f"{where}: 機能は {WHOLE} か 001-xxx の形にする（{feat}）")
        if not r.get("根拠", "").strip():
            warns.append(f"{where}: 根拠が空（docs/game/progression.md の節など）")
        if not bad:
            good.append({"id": rid, "metric": metric, "scenario": scenario, "lo": lo, "hi": hi,
                         "feature": feat, "basis": r.get("根拠", "").strip(), "line": line})
    return good, errors, warns


def filter_feature(targets: list[dict[str, Any]], feature: str | None) -> list[dict[str, Any]]:
    if not feature:
        return targets
    num = feature_num(feature)
    if not num:
        raise Precondition("BAD_FEATURE", f"--feature は 001 か 001-xxx の形で指定する（{feature}）。")
    return [t for t in targets if t["feature"] == WHOLE or feature_num(t["feature"]) == num]


def scenarios_of(targets: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for t in targets:
        if t["scenario"] not in out:
            out.append(t["scenario"])
    return out


def cmd_targets(ctx: Ctx, args: argparse.Namespace) -> int:
    good, errors, warns = load_targets(ctx)
    for e in errors:
        print(f"ERROR: {e}")
    for w in warns:
        print(f"WARN: {w}")
    print(f"SUMMARY: targets={len(good)} scenarios={len(scenarios_of(good))} errors={len(errors)} warnings={len(warns)}")
    return 1 if errors else 0


# ---------------------------------------------------------------- 柱と仮説の検算（coverage）

def normalize_subject(text: str) -> str:
    """「柱 1」「柱1」「**柱 1**」→「柱1」、「H1」→「H1」。"""
    t = re.sub(r"[\s*`]", "", text or "")
    return t


def load_pillars(path: Path) -> list[str]:
    if not path.exists():
        return []
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = PILLAR_HEADING_RE.match(line.strip())
        if m and f"柱{m.group(1)}" not in out:
            out.append(f"柱{m.group(1)}")
    return out


def load_hypotheses(path: Path) -> list[str]:
    if not path.exists():
        return []
    out: list[str] = []
    for r in gklib.read_table(path, require="仮説"):
        hid = normalize_subject(r.get("ID", ""))
        if not HYPOTHESIS_ID_RE.match(hid):
            continue
        text = (r.get("仮説") or "").strip()
        if not text:
            continue  # テンプレートの空の行
        if hid not in out:
            out.append(hid)
    return out


def cmd_coverage(ctx: Ctx, args: argparse.Namespace) -> int:
    game = gklib.pth(ctx.root, ctx.cfg, "game")
    pillars_path, loop_path = game / "pillars.md", game / "core-loop.md"
    errors: list[str] = []
    infos: list[str] = []
    warns: list[str] = []
    pillars = load_pillars(pillars_path)
    hypotheses = load_hypotheses(loop_path)
    if not pillars_path.exists():
        warns.append(f"{rel(ctx.root, pillars_path)} がない（柱の検算を確かめない）")
    elif not pillars:
        warns.append(f"{rel(ctx.root, pillars_path)} に「### 柱 N: 名前」の見出しがない")
    if not loop_path.exists():
        warns.append(f"{rel(ctx.root, loop_path)} がない（仮説の検算を確かめない）")
    subjects = pillars + hypotheses

    if not ctx.targets_path.exists():
        raise Precondition("NO_TARGETS", f"{rel(ctx.root, ctx.targets_path)} がありません（gamekit-systems で作る）。")
    target_ids = {r.get("ID", "").strip() for r in gklib.read_table(ctx.targets_path, require="指標")}
    rows = gklib.read_table(ctx.targets_path, require="検算の方法")
    if rows:
        missing_cols = [c for c in COVERAGE_COLUMNS if c not in rows[0]]
        if missing_cols:
            errors.append(f"「柱と仮説の検算」の表に列がありません: {', '.join(missing_cols)}")
    table: dict[str, dict[str, str]] = {}
    for r in rows:
        subj = normalize_subject(r.get("対象", ""))
        if not subj or subj.startswith("（") or subj.startswith("("):
            continue  # 記入例・空行
        if subj in table:
            warns.append(f"targets.md:{r.get('_line', '?')} {subj}: 行が重複している（{table[subj]['_line']} 行目）")
            continue
        table[subj] = r
        if subj not in subjects:
            warns.append(f"targets.md:{r.get('_line', '?')} {subj}: pillars.md・core-loop.md にない対象")

    by_bt = 0
    for subj in subjects:
        r = table.get(subj)
        if r is None:
            errors.append(f"{subj}: 「柱と仮説の検算」の表に行がない（BT・プレイ確認・対象外のどれかを決める）")
            continue
        where = f"targets.md:{r.get('_line', '?')} {subj}"
        method = (r.get("検算の方法") or "").strip()
        refs = BT_REF_RE.findall(method)
        if refs:
            unknown = [b for b in refs if b not in target_ids]
            if unknown:
                errors.append(f"{where}: 目標値の表にない BT を指している（{', '.join(unknown)}）")
            else:
                by_bt += 1
            continue
        if PLAYTEST_WORD in method:
            infos.append(f"{where}: プレイ確認だけで検算する（{method}）")
        elif EXEMPT_WORD in method:
            infos.append(f"{where}: 対象外（{method}）")
        else:
            errors.append(f"{where}: 検算の方法が空か読めない（BT-NNN／プレイ確認（…）／対象外（理由）のどれかにする）")
    for e in errors:
        print(f"ERROR: {e}")
    for w in warns:
        print(f"WARN: {w}")
    for i in infos:
        print(f"INFO: {i}")
    total = len(subjects)
    rate = (by_bt / total * 100) if total else 0.0
    print(f"SUMMARY: pillars={len(pillars)} hypotheses={len(hypotheses)} covered_by_bt={by_bt} "
          f"bt_rate={rate:.0f}% playtest_or_exempt={len(infos)} errors={len(errors)} warnings={len(warns)}")
    return 1 if errors else 0


# ---------------------------------------------------------------- 調整値

def resolve_pointer(doc: Any, pointer: str) -> Any:
    """RFC 6901 の JSON Pointer を解決する。見つからなければ KeyError。"""
    if pointer in ("", "/"):
        return doc
    if not pointer.startswith("/"):
        raise KeyError(f"JSON Pointer は / で始める（{pointer}）")
    cur = doc
    for raw in pointer[1:].split("/"):
        key = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, list):
            if not re.fullmatch(r"[0-9]+", key) or int(key) >= len(cur):
                raise KeyError(f"配列の添字 {key} がない")
            cur = cur[int(key)]
        elif isinstance(cur, dict):
            if key not in cur:
                raise KeyError(f"キー {key} がない")
            cur = cur[key]
        else:
            raise KeyError(f"{key} の手前が値で、たどれない")
    return cur


def cmd_params(ctx: Ctx, args: argparse.Namespace) -> int:
    path = Path(args.tuning)
    if not path.is_absolute():
        path = (Path.cwd() / path) if (Path.cwd() / path).exists() else ctx.root / path
    if not path.exists():
        print(f"ERROR: {args.tuning} がありません")
        return 1
    rows = gklib.read_table(path, require="データの場所")
    if not rows:
        print(f"INFO: {path.name} に調整値の表がない（「調整値なし」の機能なら問題ない）")
        print("SUMMARY: params=0 errors=0 warnings=0")
        return 0
    errors = warns = ok = 0
    cache: dict[Path, Any] = {}
    seen: set[str] = set()
    for r in rows:
        pid = r.get("ID", "").strip()
        if not pid or pid.startswith("（") or pid.startswith("("):
            continue
        where = f"{path.name}:{r.get('_line')} {pid}"
        if not PARAM_ID_RE.match(pid) or pid in seen:
            print(f"ERROR: {where}: " + ("ID が重複している" if pid in seen else "ID は TP-001 の形にする"))
            errors += 1
            seen.add(pid)
            continue
        seen.add(pid)
        loc = r.get("データの場所", "").strip().strip("`")
        if not loc:
            print(f"ERROR: {where}: データの場所が空（調整値はマスタデータに置く）")
            errors += 1
            continue
        file_part, _, pointer = loc.partition("#")
        fpath = ctx.root / file_part
        if not fpath.exists():
            print(f"WARN: {where}: {file_part} がまだない（S8 で作るなら問題ない）")
            warns += 1
            continue
        if fpath.suffix.lower() != ".json":
            note = "（ポインタは未検証）" if pointer else ""
            print(f"INFO: {where}: {file_part} は JSON ではないので、存在だけを確かめた{note}")
            ok += 1
            continue
        if fpath not in cache:
            try:
                cache[fpath] = json.loads(fpath.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                print(f"ERROR: {where}: {file_part} を JSON として読めない（{exc}）")
                errors += 1
                cache[fpath] = None
                continue
        if cache[fpath] is None:
            errors += 1
            continue
        if not pointer:
            print(f"WARN: {where}: JSON Pointer がない（{file_part}#/key/... の形にする）")
            warns += 1
            continue
        try:
            value = resolve_pointer(cache[fpath], pointer)
        except KeyError as exc:
            print(f"WARN: {where}: {loc} がまだ解決しない（{exc.args[0]}。S8 で作るなら問題ない）")
            warns += 1
            continue
        if not is_number(value):
            print(f"ERROR: {where}: {loc} の値が数値ではない（{json.dumps(value, ensure_ascii=False)[:40]}）")
            errors += 1
            continue
        try:
            initial = to_number(r.get("初期値"))
        except ValueError:
            initial = None
        if initial is not None and not math.isclose(float(value), initial, rel_tol=1e-9, abs_tol=1e-12):
            print(f"WARN: {where}: データの値 {fmt(value)} と tuning.md の初期値 {fmt(initial)} が違う")
            warns += 1
            continue
        ok += 1
    print(f"SUMMARY: params={ok + errors + warns} ok={ok} errors={errors} warnings={warns}")
    return 1 if errors else 0


# ---------------------------------------------------------------- 実行と判定

def load_output(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "出力がない"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"JSON として読めない（{exc}）"
    if not isinstance(data, dict) or not isinstance(data.get("metrics"), dict):
        return None, "metrics の辞書がない"
    return data, None


def selected_scenarios(ctx: Ctx, args: argparse.Namespace) -> list[str]:
    if getattr(args, "scenario", None):
        return list(dict.fromkeys(args.scenario))
    good, errors, _ = load_targets(ctx)
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        raise Precondition("BAD_TARGETS", "targets.md にエラーがある（balance.py targets で確かめる）。")
    return scenarios_of(filter_feature(good, getattr(args, "feature", None)))


def cmd_run(ctx: Ctx, args: argparse.Namespace) -> int:
    template = gklib.config_get(ctx.cfg, "commands.balance_sim")
    if not template:
        raise Precondition("NO_SIM_COMMAND",
                           ".gamekit/config.yaml の commands.balance_sim が空（gamekit-balance の §5 で準備する）。")
    scenarios = selected_scenarios(ctx, args)
    if not scenarios:
        print("INFO: 対象のシナリオがない")
        return 0
    ctx.out_dir.mkdir(parents=True, exist_ok=True)
    failed = 0
    for sc in scenarios:
        out = ctx.out_file(sc)
        if out.exists():
            out.unlink()  # 古い出力で判定しないため
        out_arg = f'"{out}"' if " " in str(out) else str(out)  # 空白を含むパスでもシェルが 1 つの引数として渡す
        cmd = str(template).replace("{scenario}", sc).replace("{out}", out_arg)
        print(f"RUN: {sc}: {cmd}")
        proc = subprocess.run(cmd, shell=True, cwd=str(ctx.root))
        _, problem = load_output(out)
        if proc.returncode != 0:
            print(f"FAILED: {sc}: 終了コード {proc.returncode}")
            failed += 1
        elif problem:
            print(f"FAILED: {sc}: {rel(ctx.root, out)} の{problem}")
            failed += 1
        else:
            print(f"OK: {sc}: {rel(ctx.root, out)}")
    print(f"SUMMARY: scenarios={len(scenarios)} failed={failed}")
    return 1 if failed else 0


def cmd_check(ctx: Ctx, args: argparse.Namespace) -> int:
    good, errors, _ = load_targets(ctx)
    targets = filter_feature(good, args.feature)
    outputs: dict[str, tuple[dict[str, Any] | None, str | None]] = {}
    lines: list[str] = []
    counts = {"PASS": 0, "FAIL": 0, "MISSING": 0}
    for t in targets:
        sc = t["scenario"]
        if sc not in outputs:
            outputs[sc] = load_output(ctx.out_file(sc))
        data, problem = outputs[sc]
        value = None
        if data is None:
            verdict, note = "MISSING", problem or ""
        else:
            raw = data["metrics"].get(t["metric"])
            if raw is None:
                verdict, note = "MISSING", "指標がない"
            elif not is_number(raw):
                verdict, note = "MISSING", f"数値ではない（{raw}）"
            else:
                value = float(raw)
                low_ok = t["lo"] is None or value >= t["lo"]
                high_ok = t["hi"] is None or value <= t["hi"]
                verdict = "PASS" if low_ok and high_ok else "FAIL"
                note = "" if verdict == "PASS" else ("下限を下回る" if not low_ok else "上限を超える")
        counts[verdict] += 1
        lines.append(f"| {t['id']} | {t['metric']} | {sc} | {fmt(t['lo'])} | {fmt(t['hi'])} | {fmt(value)} | "
                     f"{verdict} | {note} | {t['feature']} |")
    seeds = ", ".join(f"{sc}={d.get('seed')}" for sc, (d, _) in outputs.items() if d is not None) or "-"
    head = [
        f"# バランスの判定（{dt.datetime.now().strftime('%Y-%m-%d %H:%M')}）",
        "",
        f"- 対象: {args.feature or '全体'}",
        f"- 目標値: {rel(ctx.root, ctx.targets_path)}（{len(targets)} 件）",
        f"- 出力: {rel(ctx.root, ctx.out_dir)}（シード: {seeds}）",
        f"- 結果: PASS {counts['PASS']} / FAIL {counts['FAIL']} / MISSING {counts['MISSING']}"
        + (f" / targets.md のエラー {len(errors)}" if errors else ""),
        "",
        "| ID | 指標 | シナリオ | 下限 | 上限 | 実測 | 判定 | 備考 | 機能 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    text = "\n".join(head + lines) + "\n"
    if errors:
        text += "\n## targets.md のエラー\n\n" + "\n".join(f"- {e}" for e in errors) + "\n"
    print(text, end="")
    if args.report:
        rp = Path(args.report)
        rp = rp if rp.is_absolute() else ctx.root / rp
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(text, encoding="utf-8")
        print(f"REPORT: {rel(ctx.root, rp)}")
    print(f"SUMMARY: pass={counts['PASS']} fail={counts['FAIL']} missing={counts['MISSING']} errors={len(errors)}")
    if counts["FAIL"] or errors:
        return 1
    return 2 if counts["MISSING"] else 0


def existing_outputs(ctx: Ctx, base: Path, args: argparse.Namespace) -> list[str]:
    if args.scenario:
        return list(dict.fromkeys(args.scenario))
    if not base.is_dir():
        return []
    return sorted(p.stem for p in base.glob("*.json"))


def cmd_baseline(ctx: Ctx, args: argparse.Namespace) -> int:
    scenarios = existing_outputs(ctx, ctx.out_dir, args)
    if not scenarios:
        print(f"ERROR: {rel(ctx.root, ctx.out_dir)} に出力がない（先に run を実行する）")
        return 1
    ctx.baseline_dir.mkdir(parents=True, exist_ok=True)
    bad = 0
    for sc in scenarios:
        src = ctx.out_file(sc)
        _, problem = load_output(src)
        if problem:
            print(f"ERROR: {sc}: {problem}")
            bad += 1
            continue
        dst = ctx.baseline_dir / f"{sc}.json"
        shutil.copyfile(src, dst)
        print(f"SAVED: {rel(ctx.root, dst)}")
    return 1 if bad else 0


def cmd_diff(ctx: Ctx, args: argparse.Namespace) -> int:
    scenarios = existing_outputs(ctx, ctx.out_dir, args)
    if not scenarios:
        print(f"ERROR: {rel(ctx.root, ctx.out_dir)} に出力がない（先に run を実行する）")
        return 1
    rows: list[str] = []
    changed = 0
    for sc in scenarios:
        cur, p1 = load_output(ctx.out_file(sc))
        base, p2 = load_output(ctx.baseline_dir / f"{sc}.json")
        if cur is None:
            rows.append(f"| {sc} | - | - | - | - | 出力の{p1} |")
            continue
        if base is None:
            rows.append(f"| {sc} | - | - | - | - | 基準値の{p2}（baseline で記録する） |")
            continue
        if cur.get("seed") != base.get("seed"):
            rows.append(f"| {sc} | (seed) | {base.get('seed')} | {cur.get('seed')} | - | シードが違う（比べる意味が薄い） |")
        for m in sorted(set(cur["metrics"]) | set(base["metrics"])):
            a, b = cur["metrics"].get(m), base["metrics"].get(m)
            if not (is_number(a) and is_number(b)):
                if a != b:
                    changed += 1
                    rows.append(f"| {sc} | {m} | {b} | {a} | - | 追加・削除・数値以外 |")
                continue
            denom = abs(b) if b != 0 else 1.0
            ratio = abs(a - b) / denom
            if (b == 0 and a != 0) or ratio > ctx.tolerance:
                changed += 1
                sign = "+" if a >= b else "-"
                rows.append(f"| {sc} | {m} | {fmt(b)} | {fmt(a)} | {sign}{ratio * 100:.1f}% | 許容 {ctx.tolerance * 100:g}% を超える |")
    print(f"# 基準値との差分（許容 {ctx.tolerance * 100:g}%）\n")
    if rows:
        print("| シナリオ | 指標 | 基準値 | 今回 | 変化 | 備考 |")
        print("|---|---|---|---|---|---|")
        print("\n".join(rows))
    else:
        print("許容を超えた変化はない。")
    print(f"SUMMARY: scenarios={len(scenarios)} changed={changed}")
    return 1 if changed else 0


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(prog="balance.py", description="gamekit のバランス検算")
    ap.add_argument("--root", default=None, help="プロジェクトのルート（省略時は .gamekit/config.yaml を上にたどって探す）")
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("targets", help="docs/balance/targets.md を検査する")
    p = sub.add_parser("params", help="tuning.md の調整値の参照を確かめる")
    p.add_argument("tuning")
    p = sub.add_parser("run", help="シミュレーションを実行する")
    p.add_argument("--scenario", action="append")
    p.add_argument("--feature")
    p = sub.add_parser("check", help="出力と目標値を突き合わせる")
    p.add_argument("--feature")
    p.add_argument("--report")
    sub.add_parser("coverage", help="柱と仮説が目標値・プレイ確認で検算されているかを確かめる")
    for name, hlp in (("baseline", "出力を基準値として記録する"), ("diff", "出力と基準値を比べる")):
        p = sub.add_parser(name, help=hlp)
        p.add_argument("--scenario", action="append")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve() if args.root else gklib.find_root()
    try:
        ctx = Ctx(root)
        handler = {"targets": cmd_targets, "params": cmd_params, "run": cmd_run, "check": cmd_check,
                   "baseline": cmd_baseline, "diff": cmd_diff, "coverage": cmd_coverage}[args.command]
        return handler(ctx, args)
    except Precondition as exc:
        print(f"PRECONDITION: {exc.code}", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 3
    except gklib.YamlError as exc:
        print(f"ERROR: .gamekit/config.yaml を解釈できない（{exc}）", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
