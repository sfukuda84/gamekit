#!/usr/bin/env python3
"""gklib.py - gamekit の共通ライブラリ（gamekit.py と balance.py が使う）

プロジェクトの設定（.gamekit/config.yaml）、Markdown の表、git の呼び出しを扱う。
macOS / Linux / Windows で動くように、標準ライブラリだけで書く（Python 3.9 以上）。
YAML は config.yaml に必要な範囲（入れ子の辞書、ブロックとインラインのリスト、スカラー）だけを解釈する。
（novelkit の nklib.py から、YAML と表の読み込みを移したもの）
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

CONFIG_REL = ".gamekit/config.yaml"
TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "config.yaml"

DEFAULT_CONFIG: dict[str, Any] = {
    "title": "",
    "engine": None,
    "language": None,
    "paths": {
        "concept": "docs/concept",
        "research": "docs/research",
        "game": "docs/game",
        "balance": "docs/balance",
        "feature": "docs/feature",
        "design": "docs/design",
        "playtest": "docs/playtest",
        "reviews": "docs/reviews",
        "handover": "docs/handover",
        "specs": "specs",
        "data": "game/data",
        "constitution": ".specify/memory/constitution.md",
    },
    "commands": {"test": None, "lint": None, "build": None, "run_headless": None, "balance_sim": None},
    "balance": {"out_dir": "build/balance", "baseline_dir": "docs/balance/baseline", "tolerance": 0.05},
}


# ---------------------------------------------------------------- mini YAML

class YamlError(Exception):
    pass


def _strip_comment(line: str) -> str:
    out, quote = [], None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _scalar(text: str) -> Any:
    t = text.strip()
    if t == "":
        return None
    if (t[0] == t[-1]) and t[0] in ("'", '"') and len(t) >= 2:
        return t[1:-1]
    if t.startswith("[") and t.endswith("]"):
        inner = t[1:-1].strip()
        if not inner:
            return []
        return [_scalar(p) for p in _split_inline(inner)]
    if t in ("true", "True", "yes"):
        return True
    if t in ("false", "False", "no"):
        return False
    if t in ("null", "~"):
        return None
    if re.fullmatch(r"-?\d+", t) and not (len(t) > 1 and t.lstrip("-").startswith("0")):
        return int(t)
    if re.fullmatch(r"-?\d+\.\d+", t):
        return float(t)
    return t


def _split_inline(inner: str) -> list[str]:
    parts, buf, quote = [], [], None
    for ch in inner:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            buf.append(ch)
        elif ch in (",", "、"):
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def parse_yaml(text: str) -> Any:
    lines = []
    for raw in text.splitlines():
        line = _strip_comment(raw.replace("\t", "  "))
        if line.strip():
            lines.append((len(line) - len(line.lstrip(" ")), line.strip()))
    if not lines:
        return {}
    value, pos = _parse_block(lines, 0, lines[0][0])
    if pos != len(lines):
        raise YamlError(f"解釈できない行があります: {lines[pos][1]}")
    return value


def _parse_block(lines, pos, indent):
    if lines[pos][1].startswith("- ") or lines[pos][1] == "-":
        result: list[Any] = []
        while pos < len(lines) and lines[pos][0] == indent and (lines[pos][1].startswith("- ") or lines[pos][1] == "-"):
            item = lines[pos][1][1:].strip()
            pos += 1
            if item == "":
                if pos < len(lines) and lines[pos][0] > indent:
                    val, pos = _parse_block(lines, pos, lines[pos][0])
                    result.append(val)
                else:
                    result.append(None)
            elif re.match(r"^[^\[\]{}\"']+?:(\s|$)", item) and not item.startswith("["):
                # "- key: value" 形式の辞書の要素
                sub = [(indent + 2, item)]
                while pos < len(lines) and lines[pos][0] > indent:
                    sub.append(lines[pos])
                    pos += 1
                val, _ = _parse_block(sub, 0, indent + 2)
                result.append(val)
            else:
                result.append(_scalar(item))
        return result, pos
    result_d: dict[str, Any] = {}
    while pos < len(lines) and lines[pos][0] == indent:
        text = lines[pos][1]
        m = re.match(r"^(.+?):(\s+(.*))?$", text)
        if not m:
            raise YamlError(f"「キー: 値」の形ではありません: {text}")
        key, rest = m.group(1).strip().strip("'\""), (m.group(3) or "").strip()
        pos += 1
        if rest == "" and pos < len(lines) and lines[pos][0] > indent:
            val, pos = _parse_block(lines, pos, lines[pos][0])
        elif rest == "" and pos < len(lines) and lines[pos][0] == indent and lines[pos][1].startswith("- "):
            val, pos = _parse_block(lines, pos, indent)
        else:
            val = _scalar(rest)
        result_d[key] = val
    return result_d, pos


def deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [p for p in _split_inline(str(value))]


# ---------------------------------------------------------------- プロジェクト

def find_root(start: Path | None = None) -> Path:
    """.gamekit/config.yaml のあるディレクトリ。なければ git のルート、それもなければ start。

    worktree（.worktrees/<name>）の中では、worktree 自身が config.yaml を持つので、worktree がルートになる。
    """
    cur = (start or Path.cwd()).resolve()
    for p in [cur, *cur.parents]:
        if (p / CONFIG_REL).exists():
            return p
    for p in [cur, *cur.parents]:
        if (p / ".git").exists():
            return p
    return cur


def load_config(root: Path) -> dict[str, Any]:
    path = root / CONFIG_REL
    if not path.exists():
        return deep_merge(DEFAULT_CONFIG, {})
    loaded = parse_yaml(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise YamlError(f"{CONFIG_REL} の最上位が辞書ではありません。")
    return deep_merge(DEFAULT_CONFIG, loaded)


def pth(root: Path, cfg: dict, key: str) -> Path:
    return root / cfg["paths"][key]


def config_get(cfg: dict, dotted: str) -> Any:
    """"commands.test" のようなキーで値を取り出す。なければ None。"""
    cur: Any = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def set_top_scalar(text: str, key: str, value: str) -> str:
    """config.yaml の最上位の「key:」の行の値を書き換える（コメントは残す）。行がなければ末尾に足す。"""
    pat = re.compile(rf"^{re.escape(key)}:[ \t]*([^#\n]*?)([ \t]*#.*)?$", re.MULTILINE)
    m = pat.search(text)
    if not m:
        return text.rstrip("\n") + f"\n{key}: {value}\n"
    comment = (m.group(2) or "").strip()
    comment = f"  {comment}" if comment else ""
    return text[: m.start()] + f"{key}: {value}{comment}" + text[m.end():]


# ---------------------------------------------------------------- Markdown

def read_table(path: Path, require: str | None = None) -> list[dict[str, str]]:
    """Markdown の表を辞書の列にする（見出し行をキーにする）。行番号は "_line" に入れる。

    require を指定すると、その列を見出しに持つ最初の表を読む（説明用の表を読み飛ばすため）。
    指定しなければ、最初の表を読む。
    """
    if not path.exists():
        return []
    tables: list[tuple[list[str], list[dict[str, str]]]] = []
    header: list[str] | None = None
    rows: list[dict[str, str]] = []
    for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if not (s.startswith("|") and s.endswith("|")):
            if header is not None:
                tables.append((header, rows))
            header, rows = None, []
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            header = [re.sub(r"\*", "", c) for c in cells]
            continue
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            continue
        row = {header[i]: (cells[i] if i < len(cells) else "") for i in range(len(header))}
        row["_line"] = str(no)
        rows.append(row)
    if header is not None:
        tables.append((header, rows))
    for hdr, rws in tables:
        if require is None or require in hdr:
            return rws
    return []


# ---------------------------------------------------------------- git

def git(root: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} が失敗しました: {proc.stderr.strip()}")
    return proc


def is_git_repo(root: Path) -> bool:
    return git(root, ["rev-parse", "--is-inside-work-tree"], check=False).returncode == 0


