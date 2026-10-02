#!/usr/bin/env python3
"""gamekit.py - gamekit の進捗確認・引き継ぎ書・環境の診断

使い方:
  python3 gamekit.py [--root <dir>] init [--config-only] [--title T] [--engine E] [--language L]
  python3 gamekit.py [--root <dir>] config get <key.path>
  python3 gamekit.py [--root <dir>] bootstrap
  python3 gamekit.py [--root <dir>] status
  python3 gamekit.py [--root <dir>] handover [--note <text>]
  python3 gamekit.py [--root <dir>] doctor

- ゲームの工程（gamekit-bootstrap の G1〜G14）の進捗は、コミットの trailer "Gamekit-Bootstrap: G<n>" から判定する。
- 機能の工程（S1〜S12）の進捗は、gamekit-worktree の worktree_helper.py に任せる。
- 引き継ぎ書は docs/handover/CURRENT_STATE.md の自動の節と、docs/handover/sessions/<YYYYMMDD-HHMM>.md に書く。コミットはしない。
macOS / Linux / Windows で動くように、標準ライブラリだけで書く（Python 3.9 以上）。
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gklib  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATES = SKILL_DIR / "templates"
SKILLS_ROOT = Path(__file__).resolve().parents[2]
WORKTREE_HELPER = SKILLS_ROOT / "gamekit-worktree" / "scripts" / "worktree_helper.py"

BOOTSTRAP_STEPS = [f"G{i}" for i in range(1, 15)]
BOOTSTRAP_TRAILER = "Gamekit-Bootstrap"
AUTO_START = "<!-- gamekit:auto:start -->"
AUTO_END = "<!-- gamekit:auto:end -->"
# init で作らないパス（中身はエンジンや Spec Kit が作る）
NO_MKDIR_KEYS = ("data", "specs", "constitution")
STEERING = (".kiro/steering/language.md", ".kiro/steering/game-development.md")
AGENT_SKILL_DIRS = (".claude/skills", ".agents/skills", ".kiro/skills")


class GkError(Exception):
    pass


def out(line: str = "") -> None:
    print(line)


# ---------------------------------------------------------------- init

def cmd_init(root: Path, args: argparse.Namespace) -> int:
    cfg_path = root / gklib.CONFIG_REL
    created: list[str] = []
    if not cfg_path.exists():
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(gklib.TEMPLATE, cfg_path)
        created.append(gklib.CONFIG_REL)
    text = cfg_path.read_text(encoding="utf-8")
    current = gklib.parse_yaml(text) or {}
    changed = False
    for key, value in (("title", args.title), ("engine", args.engine), ("language", args.language)):
        if value and not current.get(key):
            text = gklib.set_top_scalar(text, key, value)
            changed = True
        elif value and str(current.get(key)) != value:
            print(f"SKIPPED: {key} はすでに '{current.get(key)}' です（上書きしない）", file=sys.stderr)
    if changed:
        cfg_path.write_text(text, encoding="utf-8")
        if gklib.CONFIG_REL not in created:
            created.append(f"{gklib.CONFIG_REL}（値を反映）")
    cfg = gklib.load_config(root)
    if not args.config_only:
        for key, rel in cfg["paths"].items():
            if key in NO_MKDIR_KEYS or not rel:
                continue
            d = root / rel
            if not d.exists():
                d.mkdir(parents=True, exist_ok=True)
                created.append(f"{rel}/")
            if d.is_dir() and not any(d.iterdir()):
                (d / ".gitkeep").touch()
        handover = gklib.pth(root, cfg, "handover")
        pit = handover / "PITFALLS.md"
        if not pit.exists():
            handover.mkdir(parents=True, exist_ok=True)
            shutil.copy2(TEMPLATES / "PITFALLS.md", pit)
            gk = handover / ".gitkeep"
            if gk.exists():
                gk.unlink()
            created.append(str(pit.relative_to(root)))
    for c in created:
        out(f"CREATED: {c}")
    if not created:
        out("CREATED: （なし。すべてそろっている）")
    return 0


# ---------------------------------------------------------------- config

def cmd_config(root: Path, args: argparse.Namespace) -> int:
    if args.action != "get" or not args.key:
        raise GkError("使い方: config get <key.path>")
    value = gklib.config_get(gklib.load_config(root), args.key)
    if value is None or value == "":
        out("")
        return 1
    if isinstance(value, (dict, list)):
        out(repr(value))
    else:
        out(str(value).lower() if isinstance(value, bool) else str(value))
    return 0


# ---------------------------------------------------------------- bootstrap

def bootstrap_done(root: Path) -> list[str]:
    if not gklib.is_git_repo(root):
        return []
    proc = gklib.git(root, ["log", "--all", f"--format=%(trailers:key={BOOTSTRAP_TRAILER},valueonly)"], check=False)
    if proc.returncode != 0:  # コミットがまだない
        return []
    found = {line.strip() for line in proc.stdout.splitlines() if line.strip()}
    return [s for s in BOOTSTRAP_STEPS if s in found]


def bootstrap_state(root: Path) -> tuple[list[str], str]:
    done = bootstrap_done(root)
    for step in BOOTSTRAP_STEPS:
        if step not in done:
            return done, step
    return done, "DONE"


def cmd_bootstrap(root: Path, args: argparse.Namespace) -> int:
    done, nxt = bootstrap_state(root)
    out(f"COMPLETED_STEPS: {' '.join(done)}")
    out(f"NEXT_STEP: {nxt}")
    return 0


# ---------------------------------------------------------------- status

def run_helper(root: Path, *helper_args: str) -> tuple[int, str]:
    if not WORKTREE_HELPER.exists():
        return 1, f"（{WORKTREE_HELPER} がありません）"
    proc = subprocess.run([sys.executable, str(WORKTREE_HELPER), *helper_args], cwd=str(root),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    text = (proc.stdout or "").strip()
    if proc.returncode != 0:
        err = (proc.stderr or "").strip()
        text = (text + "\n" if text else "") + f"（worktree_helper.py {' '.join(helper_args)} が失敗しました: {err}）"
    return proc.returncode, text


def latest_balance(root: Path, cfg: dict) -> tuple[Path | None, dict[str, int]]:
    candidates = list((gklib.pth(root, cfg, "balance") / "reports").glob("*.md"))
    candidates += list(gklib.pth(root, cfg, "specs").glob("*/balance-report.md"))
    candidates = [p for p in candidates if p.is_file()]
    if not candidates:
        return None, {}
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    counts = {"PASS": 0, "FAIL": 0, "MISSING": 0}
    for line in latest.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("|"):
            for cell in (c.strip().strip("*") for c in line.strip().strip("|").split("|")):
                if cell in counts:
                    counts[cell] += 1
    return latest, counts


def last_handover(root: Path, cfg: dict) -> str:
    path = gklib.pth(root, cfg, "handover") / "CURRENT_STATE.md"
    if not path.exists():
        return "なし"
    if gklib.is_git_repo(root):
        proc = gklib.git(root, ["log", "-1", "--format=%cs %h", "--", str(path.relative_to(root))], check=False)
        if proc.returncode == 0 and proc.stdout.strip():
            return f"{proc.stdout.strip()}（コミット）"
    return dt.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M") + "（ファイルの更新日時）"


def balance_line(root: Path, cfg: dict) -> str:
    path, counts = latest_balance(root, cfg)
    if path is None:
        return "レポートなし"
    return (f"{path.relative_to(root).as_posix()}: PASS {counts['PASS']} / FAIL {counts['FAIL']}"
            f" / MISSING {counts['MISSING']}")


def cmd_status(root: Path, args: argparse.Namespace) -> int:
    cfg = gklib.load_config(root)
    done, nxt = bootstrap_state(root)
    out(f"# gamekit の進捗: {cfg.get('title') or root.name}")
    out()
    out("## ゲームの工程（gamekit-bootstrap）")
    out()
    out(f"- 完了: {' '.join(done) or 'なし'}")
    out(f"- 次: {nxt}")
    out()
    out("## 機能の工程")
    out()
    _, text = run_helper(root, "status")
    out(text or "（フィーチャーなし）")
    out()
    out("## バランス")
    out()
    out(f"- 最新のレポート: {balance_line(root, cfg)}")
    out()
    out("## 引き継ぎ書")
    out()
    out(f"- 最終更新: {last_handover(root, cfg)}")
    return 0


# ---------------------------------------------------------------- handover

def high_priority_decisions(root: Path, cfg: dict) -> list[str]:
    files = [root / "docs" / "auto-decisions.md"]
    files += sorted(gklib.pth(root, cfg, "specs").glob("*/auto-decisions.md"))
    found: list[str] = []
    for f in files:
        if not f.exists():
            continue
        heading = ""
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                heading = line.lstrip("#").strip()
            elif re.search(r"優先度[^|\n]*?[:：|]\s*\**高", line) or re.search(r"\|\s*高\s*\|", line):
                label = heading or line.strip()
                entry = f"{f.relative_to(root).as_posix()}: {label}"
                if entry not in found:
                    found.append(entry)
    return found


def commits_since_handover(root: Path, cfg: dict) -> list[str]:
    if not gklib.is_git_repo(root):
        return []
    rel = (gklib.pth(root, cfg, "handover") / "CURRENT_STATE.md").relative_to(root).as_posix()
    last = gklib.git(root, ["log", "-1", "--format=%H", "--", rel], check=False).stdout.strip()
    rng = [f"{last}..HEAD"] if last else ["-n", "15"]
    proc = gklib.git(root, ["log", "--format=%h %cs %s", "-n", "30", *rng], check=False)
    return [l for l in proc.stdout.splitlines() if l.strip()] if proc.returncode == 0 else []


def build_state(root: Path, cfg: dict, now: dt.datetime) -> str:
    lines: list[str] = []
    branch, head = "-", "-"
    if gklib.is_git_repo(root):
        branch = gklib.git(root, ["rev-parse", "--abbrev-ref", "HEAD"], check=False).stdout.strip() or "-"
        head = gklib.git(root, ["rev-parse", "--short", "HEAD"], check=False).stdout.strip() or "-"
    done, nxt = bootstrap_state(root)
    lines += [f"- **更新**: {now.strftime('%Y-%m-%d %H:%M')}（ブランチ `{branch}`、`{head}`）",
              f"- **ゲームの工程**: 完了 {' '.join(done) or 'なし'} / 次 {nxt}",
              f"- **バランス**: {balance_line(root, cfg)}",
              "", "### 機能", ""]
    _, status = run_helper(root, "status")
    lines += [status or "（フィーチャーなし）", "", "### 残っている人のタスク（[人]）", ""]
    _, human = run_helper(root, "human-tasks")
    lines += [human or "（なし）", "", "### 見直しの優先度が「高」の自動判断", ""]
    decisions = high_priority_decisions(root, cfg)
    lines += [f"- {d}" for d in decisions] or ["（なし）"]
    lines += ["", "### 前回の引き継ぎ以降のコミット", ""]
    commits = commits_since_handover(root, cfg)
    lines += [f"- {c}" for c in commits] or ["（なし）"]
    return "\n".join(lines)


def cmd_handover(root: Path, args: argparse.Namespace) -> int:
    cfg = gklib.load_config(root)
    now = dt.datetime.now()
    state = build_state(root, cfg, now)
    handover = gklib.pth(root, cfg, "handover")
    handover.mkdir(parents=True, exist_ok=True)
    current = handover / "CURRENT_STATE.md"
    text = current.read_text(encoding="utf-8") if current.exists() else (TEMPLATES / "CURRENT_STATE.md").read_text(encoding="utf-8")
    block = f"{AUTO_START}\n{state}\n{AUTO_END}"
    # 印は行の単独の行だけを数える（本文の説明に印の文字列が出てきても取り違えない）
    start = re.search(rf"^{re.escape(AUTO_START)}[ \t]*$", text, re.MULTILINE)
    end = re.search(rf"^{re.escape(AUTO_END)}[ \t]*$", text, re.MULTILINE)
    if start and end and start.start() < end.start():
        text = text[: start.start()] + block + text[end.end():]
    else:
        text = text.rstrip("\n") + "\n\n## 自動で更新する節\n\n" + block + "\n"
    current.write_text(text, encoding="utf-8")
    if not (handover / "PITFALLS.md").exists():
        shutil.copy2(TEMPLATES / "PITFALLS.md", handover / "PITFALLS.md")
    sessions = handover / "sessions"
    sessions.mkdir(exist_ok=True)
    stamp = now.strftime("%Y%m%d-%H%M")
    session = sessions / f"{stamp}.md"
    n = 2
    while session.exists():
        session = sessions / f"{stamp}-{n}.md"
        n += 1
    tmpl = (TEMPLATES / "session.md").read_text(encoding="utf-8")
    session.write_text(tmpl.replace("{timestamp}", now.strftime("%Y-%m-%d %H:%M"))
                       .replace("{note}", args.note or "（なし）").replace("{state}", state), encoding="utf-8")
    gk = handover / ".gitkeep"
    if gk.exists():
        gk.unlink()
    out(f"UPDATED: {current.relative_to(root).as_posix()}")
    out(f"CREATED: {session.relative_to(root).as_posix()}")
    return 0


# ---------------------------------------------------------------- doctor

def first_program(command: str) -> str:
    tokens = command.strip().split()
    for t in tokens:
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", t):  # 先頭の環境変数の代入
            continue
        return t.strip("'\"")
    return ""


def cmd_doctor(root: Path, args: argparse.Namespace) -> int:
    results: list[tuple[str, str]] = []
    cfg_path = root / gklib.CONFIG_REL
    cfg = None
    if not cfg_path.exists():
        results.append(("ERROR", f"{gklib.CONFIG_REL} がありません（gamekit.py init で作る）"))
    else:
        try:
            cfg = gklib.load_config(root)
            results.append(("OK", f"{gklib.CONFIG_REL} を解釈できる"))
        except gklib.YamlError as e:
            results.append(("ERROR", f"{gklib.CONFIG_REL} を解釈できません: {e}"))
    if cfg is not None:
        engine = cfg.get("engine")
        if not engine:
            results.append(("WARN", "engine が空です（gamekit-architecture（G8）で決める）"))
        elif engine not in ("godot", "web", "other"):
            results.append(("WARN", f"engine '{engine}' は godot / web / other のどれでもありません"))
        else:
            results.append(("OK", f"engine: {engine}" + (f" / {cfg.get('language')}" if cfg.get("language") else "")))
        for key, cmd in (cfg.get("commands") or {}).items():
            if not cmd:
                results.append(("WARN", f"commands.{key} が空です"))
                continue
            prog = first_program(str(cmd))
            if prog and (shutil.which(prog) or (root / prog).exists()):
                results.append(("OK", f"commands.{key}: {prog} がある"))
            else:
                results.append(("WARN", f"commands.{key}: '{prog}' が PATH にありません"))
        data = gklib.pth(root, cfg, "data")
        results.append(("OK", f"paths.data: {cfg['paths']['data']}") if data.exists()
                       else ("WARN", f"paths.data（{cfg['paths']['data']}）がまだありません"))
    for base in AGENT_SKILL_DIRS:
        d = root / base
        if not d.is_dir():
            results.append(("ERROR", f"{base}/ がありません"))
            continue
        broken = [p.name for p in d.iterdir() if p.is_symlink() and not p.exists()]
        names = {p.name for p in d.iterdir()}
        if broken:
            results.append(("ERROR", f"{base}/ のリンクが切れています: {', '.join(sorted(broken))}"))
        missing = [s for s in ("gamekit-status", "gamekit-worktree", "speckit-specify") if s not in names]
        if missing:
            results.append(("ERROR", f"{base}/ に {', '.join(missing)} がありません"))
        if not broken and not missing:
            results.append(("OK", f"{base}/ のスキル {len(names)} 件"))
    results.append(("OK", ".specify/ がある") if (root / ".specify").is_dir()
                   else ("ERROR", ".specify/ がありません"))
    for rel in STEERING:
        if not (root / rel).exists():
            results.append(("ERROR", f"{rel} がありません"))
    for rel in ("CLAUDE.md", "AGENTS.md", "GEMINI.md"):
        p = root / rel
        if not p.exists():
            results.append(("WARN", f"{rel} がありません"))
            continue
        body = p.read_text(encoding="utf-8")
        lacking = [s for s in STEERING if s not in body]
        if lacking:
            results.append(("WARN", f"{rel} が {', '.join(lacking)} を参照していません"))
        else:
            results.append(("OK", f"{rel} が steering を参照している"))
    for level, msg in results:
        out(f"{level}: {msg}")
    errors = sum(1 for level, _ in results if level == "ERROR")
    warns = sum(1 for level, _ in results if level == "WARN")
    out(f"SUMMARY: ERROR {errors} / WARN {warns}")
    return 1 if errors else 0


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(prog="gamekit.py", description="gamekit の進捗確認・引き継ぎ書・環境の診断")
    ap.add_argument("--root", default=None, help="プロジェクトのルート（省略時は .gamekit/config.yaml か .git を上へ探す）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init", help=".gamekit/config.yaml とディレクトリを作る（既存は変えない）")
    p.add_argument("--config-only", action="store_true")
    p.add_argument("--title", default="")
    p.add_argument("--engine", default="")
    p.add_argument("--language", default="")
    p = sub.add_parser("config", help="設定の値を読む")
    p.add_argument("action", choices=["get"])
    p.add_argument("key", nargs="?")
    sub.add_parser("bootstrap", help="ゲームの工程（G1〜G14）の進捗")
    sub.add_parser("status", help="ゲームの工程・機能・バランス・引き継ぎ書の状況")
    p = sub.add_parser("handover", help="引き継ぎ書を更新する（コミットしない）")
    p.add_argument("--note", default="")
    sub.add_parser("doctor", help="設定と環境の診断")
    args = ap.parse_args()
    root = Path(args.root).expanduser().resolve() if args.root else gklib.find_root()
    handlers = {"init": cmd_init, "config": cmd_config, "bootstrap": cmd_bootstrap, "status": cmd_status,
                "handover": cmd_handover, "doctor": cmd_doctor}
    try:
        return handlers[args.cmd](root, args)
    except (GkError, gklib.YamlError, RuntimeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
