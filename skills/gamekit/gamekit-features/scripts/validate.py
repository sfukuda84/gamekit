#!/usr/bin/env python3
"""docs/feature/ の機能概要一式を検証する（gamekit-features。speckit-concept-2-feature の validate.py をゲーム向けにしたもの）。

使い方:
    python3 validate.py <docs/feature のパス>           # 検証のみ
    python3 validate.py <docs/feature のパス> --graph   # 被参照数と段階分けも表示
    python3 validate.py <docs/feature のパス> --lenient # 既存のプロジェクトへの取り込み用。エラーを警告に落とし、
                                                        # 番号のないファイル（NNN-slug.md でないもの）は検証の対象から外す
    # README.md の「メタ文書（機能ファイルではない）」の表に載せたファイル（取り込みで残した元の資料など）は、
    # --lenient がなくても機能ファイルとして検証しない
    python3 validate.py <docs/feature のパス> --backlog-file <backlog.md のパス>
    python3 validate.py <docs/feature のパス> --premises-file <premises.md のパス>
    python3 validate.py <docs/feature のパス> --targets-file <targets.md のパス>
        # 省略時、backlog.md は docs/feature と同階層の concept/（なければ conpect/）から探す。
        # premises.md は concept/premises.md（GP）と docs/feature/premises.md（仕分けの前提）の両方を読む。
        # targets.md は同階層の balance/ から探す

検証すること（speckit 版に加えて）:
    - 区分は 垂直スライス / MVP / 拡張。前の区分の機能は後の区分の機能に依存しない。spec_order.md の並びも区分の順
    - 000-*（共通基盤）と 999-*（リリース基盤）は名前を問わない（speckit の 000-app-basic・999-app-nfr もそのまま扱う）。
      それぞれ複数あれば警告
    - 「## 関わるシステムと目標値」の BT-NNN が docs/balance/targets.md にあるか（警告）
    - premises.md の GP・F（または speckit の P）の未決（警告）

終了コード: エラーが 1 件以上なら 1、なければ 0（警告は終了コードに影響しない。--lenient では常に 0）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

META_FILES = {"README.md", "spec_order.md", "premises.md"}
REQUIRED_SECTIONS = [
    "## 概要",
    "## プレイヤー体験",
    "## 位置づけ",
    "## 主な要求",
    "## 関わるシステムと目標値",
    "## 前提・設計原則との関係",
    "## スコープ外",
    "## 根拠",
    "## /speckit-specify に渡す記述案",
]
# 000（共通基盤）と 999（リリース基盤）は、ゲームのシステムや目標値を持たないことが多いので求めない
RESERVED_OPTIONAL_SECTIONS = {"## プレイヤー体験", "## 関わるシステムと目標値"}
STATUS_RE = re.compile(r"^(未着手|実装済み（spec なし）|一部実装（spec なし）|spec化済み（specs/[^）]+）|人の作業待ち（specs/[^）]+）|完了)$")
IMPLEMENTED_STATUSES = ("実装済み（spec なし）", "一部実装（spec なし）")
# 区分は前から順に作る。前の区分の機能は、後の区分の機能に依存しない
CATEGORIES = ("垂直スライス", "MVP", "拡張")
TIER = {c: i for i, c in enumerate(CATEGORIES)}
NONE_DEPS = {"—", "-", "なし", ""}
# ファイル名は NNN-<slug>（例: 001-clinic-setup）。specs/ とブランチ名にそのまま対応する
NAME_RE = re.compile(r"^(\d{3})-[a-z0-9]+(-[a-z0-9]+)*$")
# 予約番号: 000 は共通基盤（gamekit-foundation。既定の名前は 000-game-foundation）、
# 999 はリリース基盤（gamekit-nfr。既定の名前は 999-game-release）。名前は問わない（speckit の 000-app-basic なども可）
BASIC_ORDER = 0
NFR_ORDER = 999
RESERVED_ORDERS = (BASIC_ORDER, NFR_ORDER)
BT_RE = re.compile(r"\bBT-\d{3}\b")
BACKLOG_STATUS_RE = re.compile(r"^(候補|却下|機能化済み（docs/feature/(\d{3}-[a-z0-9-]+)\.md）)$")
# speckit-worktree の worktree_helper.py が読む行形式: - **1. [名前](./slug.md)**
ORDER_LINE_RE = re.compile(r"\*\*\s*(\d+)\.\s*\[([^\]]*)\]\(\./([^.)]+)\.md\)")
README_ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|\s*\[([^\]]*)\]\(\./([^.)]+)\.md\)\s*\|(.*)\|\s*$")
# 「広く浅く」に反しがちな記述（警告のみ）
DEPTH_PATTERNS = [
    (re.compile(r"\b(VARCHAR|BIGSERIAL|SERIAL|INTEGER|BIGINT|TIMESTAMPTZ|BOOLEAN|DOUBLE PRECISION|JSONB|TEXT\b\()"), "カラム型"),
    (re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+/"), "API のメソッドとパス"),
    (re.compile(r"`/api/[^`]*`"), "API パス"),
    (re.compile(r"^\s*(func|extends|class_name|public class|export default|const \w+ =)\b", re.M), "コード"),
    (re.compile(r"(?<![A-Za-z0-9-])\d+(?:\.\d+)?\s*(?:%|％|秒|フレーム|ダメージ|ゴールド|HP|MP|G)(?![A-Za-z])(?![^\n]*\bQ\d+\b)"),
     "具体的な数値（調整値は S4-2 の tuning.md で決める。ユーザーが決めた値なら同じ行に Q-ID を付ける）"),
]

errors: list[str] = []
warnings: list[str] = []
LENIENT = "--lenient" in sys.argv


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def parse_deps(value: str) -> list[str]:
    value = value.strip()
    if value in NONE_DEPS:
        return []
    return [d.strip() for d in value.split(",") if d.strip()]


WEIGHTS = ("軽", "標準", "重")


def parse_header(path: Path, text: str) -> dict | None:
    """`**状態**: … | **区分**: … | **想定順序**: … | **依存**: … | **重さ**: …` 行を読む（重さは任意）。"""
    line = next((l for l in text.splitlines() if l.startswith("**状態**")), None)
    if line is None:
        err(f"{path.name}: ヘッダ行（**状態** で始まる行）がない")
        return None
    fields = {}
    for part in line.split(" | "):
        m = re.match(r"\*\*(.+?)\*\*:\s*(.*)$", part.strip())
        if m:
            fields[m.group(1)] = m.group(2).strip()
    for key in ("状態", "区分", "想定順序", "依存"):
        if key not in fields:
            err(f"{path.name}: ヘッダ行に **{key}** がない")
    if any(k not in fields for k in ("状態", "区分", "想定順序", "依存")):
        return None
    if not STATUS_RE.match(fields["状態"]):
        err(f"{path.name}: 状態「{fields['状態']}」は 未着手 / 実装済み（spec なし） / 一部実装（spec なし） / spec化済み（specs/…） / 人の作業待ち（specs/…） / 完了 のいずれかにする")
    if fields["区分"] not in CATEGORIES:
        err(f"{path.name}: 区分「{fields['区分']}」は 垂直スライス / MVP / 拡張 のいずれかにする")
    if not fields["想定順序"].isdigit():
        err(f"{path.name}: 想定順序「{fields['想定順序']}」が整数でない")
    # 機能の重さ（軽 / 標準 / 重）。工程の重さを決める（gamekit-worktree の「機能の重さ」）。欠けは標準として扱う
    if "重さ" not in fields:
        warn(f"{path.name}: ヘッダ行に **重さ** がない（標準として扱う。軽 / 標準 / 重 のどれかを書く）")
    elif fields["重さ"] not in WEIGHTS:
        err(f"{path.name}: 重さ「{fields['重さ']}」は 軽 / 標準 / 重 のいずれかにする")
    return fields


def section_body(text: str, heading: str) -> str:
    lines = text.splitlines()
    try:
        start = lines.index(heading) + 1
    except ValueError:
        return ""
    body = []
    for l in lines[start:]:
        if l.startswith("## "):
            break
        body.append(l)
    return "\n".join(body).strip()


all_slugs: set[str] = set()
META_SECTION = "## メタ文書"
LOCAL_LINK_RE = re.compile(r"\]\((?:\./)?([^/()#\s]+\.md)\)")


def listed_meta_files(feature_dir: Path) -> set[str]:
    """README.md の「メタ文書（機能ファイルではない）」の節に載っている、docs/feature 直下のファイル名。

    取り込み（--adopt）で残した元の資料（例: 番号のない mvp1.md）をこの表に載せれば、機能ファイルとして検証しない。
    """
    path = feature_dir / "README.md"
    if not path.exists():
        return set()
    names: set[str] = set()
    inside = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            inside = line.startswith(META_SECTION)
            continue
        if inside and line.lstrip().startswith("|"):
            first_cell = line.strip().strip("|").split("|")[0]
            names.update(LOCAL_LINK_RE.findall(first_cell))
    return names


def load_features(feature_dir: Path) -> dict[str, dict]:
    features = {}
    meta = META_FILES | listed_meta_files(feature_dir)
    for path in sorted(feature_dir.glob("*.md")):
        if path.name in meta:
            continue
        slug = path.stem
        text = path.read_text(encoding="utf-8")
        name_m = NAME_RE.match(slug)
        if not name_m:
            if LENIENT:
                warn(f"{path.name}: 番号のないファイル名（NNN-<slug>.md でない）なので検証の対象から外した。"
                     "gamekit の機能として扱うには、gamekit-features の取り込みの手順で NNN-<slug>.md の機能ファイルを作る")
                continue
            err(f"{path.name}: ファイル名は NNN-<英小文字のケバブケース>.md にする（例: 001-core-combat.md）")
        all_slugs.add(slug)
        title_line = next((l for l in text.splitlines() if l.startswith("# ")), None)
        if title_line is None:
            err(f"{path.name}: H1 見出し（# 機能名）がない")
        header = parse_header(path, text)
        reserved = bool(name_m) and int(name_m.group(1)) in RESERVED_ORDERS
        # spec 化した後の機能ファイルは書き換えない（正本は specs/）。ゲーム向けに足した節がなくても警告にとどめる
        frozen = bool(header) and not header["状態"].startswith("未着手")
        for sec in REQUIRED_SECTIONS:
            if sec not in text.splitlines():
                if reserved and sec in RESERVED_OPTIONAL_SECTIONS:
                    continue
                if frozen and sec in RESERVED_OPTIONAL_SECTIONS:
                    warn(f"{path.name}: 見出し「{sec}」がない（状態が「{header['状態']}」なので書き換えない。正本は specs/）")
                    continue
                err(f"{path.name}: 見出し「{sec}」がない")
        position = section_body(text, "## 位置づけ")
        if position and not reserved and not re.search(r"柱|pillars\.md", position):
            warn(f"{path.name}: 位置づけ節にデザインの柱（docs/game/pillars.md）への言及がない")
        if header and header["状態"] in IMPLEMENTED_STATUSES:
            if not section_body(text, "## 現状の実装"):
                err(f"{path.name}: 状態が「{header['状態']}」なのに「## 現状の実装」節がないか空")
        elif "## 現状の実装" in text.splitlines():
            warn(f"{path.name}: 状態が「{header['状態'] if header else '?'}」なのに「## 現状の実装」節がある（既存実装がなければ削除する）")
        basis = section_body(text, "## 根拠")
        if basis and not re.search(r"concept/|game/|premises\.md|competitors?\.md|core-loop\.md|systems\.md|\bG?P\d+\b|\bQ\d+\b", basis):
            warn(f"{path.name}: 根拠節に concept・game / premises（GP-ID・Q-ID）への参照がない")
        elif not basis and "## 根拠" in text.splitlines():
            err(f"{path.name}: 根拠節が空")
        for pat, label in DEPTH_PATTERNS:
            for m in pat.finditer(text):
                warn(f"{path.name}: {label}らしき記述「{m.group(0)}」— 広く浅くの方針では clarify/plan で決める")
                break
        if header is None:
            continue
        if name_m and header["想定順序"].isdigit() and int(name_m.group(1)) != int(header["想定順序"]):
            err(f"{path.name}: ファイル名の番号 {name_m.group(1)} と想定順序 {header['想定順序']} が違う")
        features[slug] = {
            "title": title_line[2:].strip() if title_line else "",
            "status": header["状態"],
            "category": header["区分"],
            "order": int(header["想定順序"]) if header["想定順序"].isdigit() else None,
            "deps_raw": header["依存"],
            "deps": parse_deps(header["依存"]),
            "bts": sorted(set(BT_RE.findall(section_body(text, "## 関わるシステムと目標値")))),
        }
    return features


def check_graph(features: dict[str, dict]) -> None:
    for slug, f in features.items():
        for d in f["deps"]:
            if d not in features:
                if d not in all_slugs:
                    err(f"{slug}.md: 依存「{d}」に対応する機能ファイルがない")
            elif d == slug:
                err(f"{slug}.md: 自分自身に依存している")
            elif (f["category"] in TIER and features[d]["category"] in TIER
                  and TIER[f["category"]] < TIER[features[d]["category"]]):
                err(f"{slug}.md: {f['category']}の機能が{features[d]['category']}の機能「{d}」に依存している")

    # 循環依存の検出（白・灰・黒の DFS）
    color = {s: 0 for s in features}
    cycles = []

    def dfs(node: str, stack: list[str]) -> None:
        color[node] = 1
        for d in features[node]["deps"]:
            if d not in features:
                continue
            if color[d] == 1:
                cycles.append(stack[stack.index(d):] + [d])
            elif color[d] == 0:
                dfs(d, stack + [d])
        color[node] = 2

    for s in features:
        if color[s] == 0:
            dfs(s, [s])
    for c in cycles:
        err(f"循環依存: {' -> '.join(c)}")

    orders = [f["order"] for f in features.values() if f["order"] is not None]
    # 000 と 999 が複数あるときは check_reserved が警告する（speckit から取り込んだプロジェクトでは起こりうる）
    dup = sorted({o for o in orders if orders.count(o) > 1 and o not in RESERVED_ORDERS})
    if dup:
        err(f"想定順序が重複している: {dup}")
    core_orders = sorted(o for o in orders if o not in RESERVED_ORDERS)
    if core_orders and core_orders != list(range(1, len(core_orders) + 1)):
        warn(f"想定順序が 1 からの連番になっていない: {core_orders}（再実行で機能を削除した場合は想定どおり）")
    check_reserved(features)


def depends_on(features: dict[str, dict], slug: str, target: str) -> bool:
    """slug が target に（間接的にでも）依存しているか。"""
    seen: set[str] = set()
    stack = list(features[slug]["deps"])
    while stack:
        d = stack.pop()
        if d == target:
            return True
        if d in seen or d not in features:
            continue
        seen.add(d)
        stack.extend(features[d]["deps"])
    return False


def check_reserved(features: dict[str, dict]) -> None:
    """予約番号 000（共通基盤）と 999（運用基盤・非機能要件）の規則。"""
    basic = [s for s, f in features.items() if f["order"] == BASIC_ORDER]
    nfr = [s for s, f in features.items() if f["order"] == NFR_ORDER]
    if len(basic) > 1:
        warn(f"共通基盤（000）が複数ある: {', '.join(basic)}（gamekit-foundation の更新モードで 1 つにまとめるか、意図を README に書く）")
    if len(nfr) > 1:
        warn(f"リリース基盤（999）が複数ある: {', '.join(nfr)}")
    first_tier = min((TIER[f["category"]] for f in features.values() if f["category"] in TIER), default=0)
    for slug in basic:
        if features[slug]["category"] in TIER and TIER[features[slug]["category"]] > first_tier:
            err(f"{slug}.md: 共通基盤（000）の区分は、いちばん前の区分（{CATEGORIES[first_tier]}）にする")
        if features[slug]["deps"]:
            err(f"{slug}.md: 共通基盤（000）はほかの機能に依存できない")
        for other, f in features.items():
            if other != slug and f["order"] != BASIC_ORDER and not depends_on(features, other, slug):
                warn(f"{other}.md: 共通基盤 {slug} に（間接的にも）依存していない。セーブや入力などを前提にするなら依存に加える")
    for slug in nfr:
        for other, f in features.items():
            if slug in f["deps"]:
                warn(f"{other}.md: リリース基盤 {slug} に依存している。999 はほかの機能から依存されない前提")


def check_readme(feature_dir: Path, features: dict[str, dict]) -> None:
    path = feature_dir / "README.md"
    if not path.exists():
        err("README.md がない")
        return
    seen = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = README_ROW_RE.match(line)
        if not m:
            continue
        num, title, slug, rest = m.groups()
        cols = [c.strip() for c in rest.split("|")]
        if slug in seen:
            err(f"README.md: {slug} の行が重複している")
        seen[slug] = True
        if slug not in features:
            if slug not in all_slugs:
                err(f"README.md: 一覧の {slug} に対応する機能ファイルがない")
            continue
        f = features[slug]
        if len(cols) < 4:
            err(f"README.md: {slug} の行の列が足りない（# | 機能 | 区分 | 状態 | 依存 | 一言）")
            continue
        category, status, deps = cols[0], cols[1], cols[2]
        if int(num) != f["order"]:
            err(f"README.md: {slug} の # が {num}、ファイルの想定順序は {f['order']}")
        if title != f["title"]:
            err(f"README.md: {slug} のリンク文言「{title}」が H1「{f['title']}」と違う")
        if category != f["category"]:
            err(f"README.md: {slug} の区分「{category}」がファイル（{f['category']}）と違う")
        if status != f["status"]:
            err(f"README.md: {slug} の状態「{status}」がファイル（{f['status']}）と違う")
        if deps != f["deps_raw"]:
            err(f"README.md: {slug} の依存「{deps}」がファイル（{f['deps_raw']}）と違う")
    for slug in features:
        if slug not in seen:
            err(f"README.md: 一覧に {slug} の行がない")
    text = path.read_text(encoding="utf-8")
    m = re.search(r"機能ファイル\s*\*\*(\d+)\s*件\*\*", text)
    if m and int(m.group(1)) != len(all_slugs):
        err(f"README.md: 件数が {m.group(1)} 件、実測は {len(all_slugs)} 件")


def check_spec_order(feature_dir: Path, features: dict[str, dict]) -> None:
    path = feature_dir / "spec_order.md"
    if not path.exists():
        err("spec_order.md がない")
        return
    seen = {}
    position = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("- **"):
            continue
        m = ORDER_LINE_RE.search(line)
        if not m:
            continue
        num, title, slug = int(m.group(1)), m.group(2), m.group(3)
        if slug in seen:
            err(f"spec_order.md: {slug} の行が重複している")
        seen[slug] = num
        position.append(slug)
        if slug not in features:
            if slug not in all_slugs:
                err(f"spec_order.md: {slug} に対応する機能ファイルがない")
            continue
        if num != features[slug]["order"]:
            err(f"spec_order.md: {slug} の番号 {num} がファイルの想定順序 {features[slug]['order']} と違う")
    for slug in features:
        if slug not in seen:
            err(f"spec_order.md: `- **N. [名前](./{slug}.md)**` 形式の行がない（gamekit-worktree が読めない）")
    # 並び順が依存と区分に反していないか
    idx = {s: i for i, s in enumerate(position)}
    for slug, f in features.items():
        if slug not in idx:
            continue
        for d in f["deps"]:
            if d in idx and idx[d] > idx[slug]:
                err(f"spec_order.md: {slug} が依存先 {d} より前に並んでいる")
    for slug, f in features.items():
        if f["order"] == BASIC_ORDER and slug in idx and idx[slug] != 0:
            err(f"spec_order.md: 共通基盤 {slug} は先頭に並べる")
    for i, earlier in enumerate(CATEGORIES):
        for later in CATEGORIES[i + 1:]:
            e_pos = [idx[s] for s, f in features.items() if s in idx and f["category"] == earlier]
            l_pos = [idx[s] for s, f in features.items() if s in idx and f["category"] == later]
            if e_pos and l_pos and max(e_pos) > min(l_pos):
                err(f"spec_order.md: {later}の機能が{earlier}の機能より前に並んでいる")


def option(name: str) -> str | None:
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


def premises_files(feature_dir: Path) -> list[Path]:
    """ゲームの前提（docs/concept/premises.md の GP）と、仕分けの前提（docs/feature/premises.md）。"""
    given = option("--premises-file")
    if given:
        return [Path(given)]
    return [c for c in (feature_dir.parent / "concept" / "premises.md", feature_dir.parent / "conpect" / "premises.md",
                        feature_dir / "premises.md") if c.exists()]


def check_premises(feature_dir: Path) -> None:
    """GP（gamekit-sparring）、F（仕分けの前提）、P（speckit の旧様式）の行で、状態の列が「未決」のものを警告する。"""
    paths = premises_files(feature_dir)
    if not paths:
        err("premises.md がない（docs/concept/premises.md は gamekit-sparring、docs/feature/premises.md は gamekit-features が作る）")
        return
    if not (feature_dir / "premises.md").exists() and not option("--premises-file"):
        warn("docs/feature/premises.md がない（基盤の候補と仕分けの質疑の置き場所。gamekit-features が作る）")
    for path in paths:
        undecided = []
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\|\s*((?:GP|F|P)\d+)\s*\|([^|]*)\|(.*)\|\s*$", line)
            if m and re.search(r"\|\s*未決\s*\|", "|" + m.group(3) + "|"):
                undecided.append(f"{m.group(1)}（{m.group(2).strip()}）")
        if undecided:
            warn(f"{path}: 未決の項目が残っている: {', '.join(undecided)}")


def find_targets(feature_dir: Path) -> Path | None:
    given = option("--targets-file")
    if given:
        return Path(given)
    cand = feature_dir.parent / "balance" / "targets.md"
    return cand if cand.exists() else None


def check_targets(feature_dir: Path, features: dict[str, dict]) -> None:
    """機能ファイルが挙げた BT-NNN が targets.md にあるか（警告）。"""
    path = find_targets(feature_dir)
    used = {bt for f in features.values() for bt in f["bts"]}
    if not used:
        return
    if path is None:
        warn("docs/balance/targets.md がないので、機能ファイルの BT-NNN を確かめていない（gamekit-systems が作る）")
        return
    known = set(BT_RE.findall(path.read_text(encoding="utf-8")))
    for slug, f in features.items():
        for bt in f["bts"]:
            if bt not in known:
                warn(f"{slug}.md: 目標値 {bt} が {path} にない")


def find_backlog(feature_dir: Path) -> Path | None:
    given = option("--backlog-file")
    if given:
        return Path(given)
    for name in ("concept", "conpect"):
        cand = feature_dir.parent / name / "backlog.md"
        if cand.exists():
            return cand
    return None


def check_backlog(path: Path | None, features: dict[str, dict]) -> dict[str, int]:
    """backlog.md の様式、状態、機能化済みのリンク先、一覧表との一致を確かめる。"""
    counts = {"候補": 0, "却下": 0, "機能化済み": 0}
    if path is None or not path.exists():
        warn("backlog.md がない（機能化しなかった候補がなければ問題ない）")
        return counts
    text = path.read_text(encoding="utf-8")
    sections = re.split(r"^### ", text, flags=re.M)[1:]
    seen: dict[str, str] = {}
    for sec in sections:
        lines = sec.splitlines()
        m = re.match(r"^(BL-\d{3})\s+(.+)$", lines[0])
        if not m:
            err(f"backlog.md: 見出し「### {lines[0]}」は「### BL-NNN 候補名」にする")
            continue
        bid = m.group(1)
        if bid in seen:
            err(f"backlog.md: {bid} が重複している")
        header = next((l for l in lines if l.startswith("**状態**")), None)
        if header is None:
            err(f"backlog.md: {bid} にヘッダ行（**状態** で始まる行）がない")
            continue
        fields = {}
        for part in header.split(" | "):
            fm = re.match(r"\*\*(.+?)\*\*:\s*(.*)$", part.strip())
            if fm:
                fields[fm.group(1)] = fm.group(2).strip()
        status = fields.get("状態", "")
        seen[bid] = status
        sm = BACKLOG_STATUS_RE.match(status)
        if not sm:
            err(f"backlog.md: {bid} の状態「{status}」は 候補 / 却下 / 機能化済み（docs/feature/NNN-slug.md） のいずれかにする")
            continue
        kind = "機能化済み" if sm.group(2) else status
        counts[kind] += 1
        if sm.group(2) and sm.group(2) not in all_slugs:
            err(f"backlog.md: {bid} の機能化先 {sm.group(2)}.md がない")
        body = "\n".join(lines)
        for label in ("要件概要", "出典"):
            if f"**{label}**" not in body:
                err(f"backlog.md: {bid} に「{label}」がない")
        if kind == "候補" and "**機能化するときに決めること**" not in body:
            warn(f"backlog.md: {bid} に「機能化するときに決めること」がない")
        if kind == "却下" and "**却下の理由**" not in body:
            err(f"backlog.md: {bid} は却下なのに「却下の理由」がない")
        for rel in parse_deps(fields.get("関連機能", "—")):
            if rel not in all_slugs:
                warn(f"backlog.md: {bid} の関連機能 {rel} に対応する機能ファイルがない")
    # 一覧表の状態と各候補の状態の一致
    for line in text.splitlines():
        rm = re.match(r"^\|\s*(BL-\d{3})\s*\|[^|]*\|\s*([^|]+?)\s*\|", line)
        if not rm:
            continue
        bid, st = rm.groups()
        if bid not in seen:
            err(f"backlog.md: 一覧の {bid} に対応する候補の節がない")
        elif st != seen[bid]:
            err(f"backlog.md: 一覧の {bid} の状態「{st}」が節の状態（{seen[bid]}）と違う")
    return counts


RANK_ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|\s*`([^`]+)`\s*\|\s*(.*?)\s*\|\s*$")


def ranking(features: dict[str, dict]) -> list[tuple[str, int]]:
    """被参照数が 1 以上の機能を、多い順（同数なら想定順序順）に並べる。"""
    ref = {s: 0 for s in features}
    for f in features.values():
        for d in f["deps"]:
            if d in ref:
                ref[d] += 1
    return [(s, n) for s, n in sorted(ref.items(), key=lambda x: (-x[1], features[x[0]]["order"] or 0)) if n > 0]


def read_rank_table(feature_dir: Path) -> list[tuple[str, int, str]]:
    """spec_order.md の被参照数の表（| n | `slug` | 意味 |）を読む。"""
    path = feature_dir / "spec_order.md"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = RANK_ROW_RE.match(line)
        if m:
            rows.append((m.group(2), int(m.group(1)), m.group(3)))
    return rows


def check_rank_table(feature_dir: Path, features: dict[str, dict]) -> None:
    table = [(s, n) for s, n, _ in read_rank_table(feature_dir)]
    if table and table != ranking(features):
        warn("spec_order.md: 被参照数の表が実測と違う（--graph の出力で置き換える）")


def read_oneliners(feature_dir: Path) -> dict[str, str]:
    """README.md の一覧から、機能ごとの「一言」を読む。"""
    path = feature_dir / "README.md"
    result = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = README_ROW_RE.match(line)
            if m:
                cols = [c.strip() for c in m.group(4).split("|")]
                if len(cols) >= 4:
                    result[m.group(3)] = cols[3]
    return result


def print_graph(feature_dir: Path, features: dict[str, dict]) -> None:
    """spec_order.md にそのまま貼れる形で、被参照数の表と段階ごとの機能行を出す。"""
    meanings = {s: m for s, _, m in read_rank_table(feature_dir)}
    print("\n## 被参照数（spec_order.md「被参照数の多い順」の表にそのまま使う。意味の列は既存の記述を引き継ぐ）\n")
    print("| 被参照 | 機能 | 意味 |")
    print("|---|---|---|")
    for s, n in ranking(features):
        print(f"| {n} | `{s}` | {meanings.get(s, '<なぜ多くの機能の土台になるか>')} |")

    # 段階 = 同じ区分内の依存の深さ。後の区分の機能から見た前の区分の依存は完了済みとして数えない。
    stage: dict[str, int] = {}

    def depth(s: str, trail: tuple = ()) -> int:
        if s in stage:
            return stage[s]
        if s in trail:
            return 1  # 循環はエラーとして別途報告済み
        same = [d for d in features[s]["deps"]
                if d in features and features[d]["category"] == features[s]["category"]]
        stage[s] = 1 + max((depth(d, trail + (s,)) for d in same), default=0)
        return stage[s]

    for s in features:
        depth(s)
    oneliners = read_oneliners(feature_dir)
    print("\n## 段階分け（spec_order.md の機能行の形。段階の性格の見出しは手で付ける）")
    for cat in CATEGORIES:
        members = [s for s in features if features[s]["category"] == cat]
        if not members:
            continue
        print(f"\n### {cat}")
        for st in sorted({stage[s] for s in members}):
            print(f"\n#### {cat}-S{st}: <段階の性格>\n")
            for s in sorted((s for s in members if stage[s] == st), key=lambda s: features[s]["order"] or 0):
                f = features[s]
                print(f"- **{f['order']}. [{f['title']}](./{s}.md)**: {oneliners.get(s, '<一言>')}")


def main() -> int:
    # Windows の日本語環境では標準出力が cp932 になり、— などを出力すると落ちるため UTF-8 に固定する
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    argv = sys.argv[1:]
    valued = ("--backlog-file", "--premises-file", "--targets-file")
    args = [a for i, a in enumerate(argv)
            if not a.startswith("--") and not (i > 0 and argv[i - 1] in valued)]
    if len(args) != 1:
        print(__doc__)
        return 2
    feature_dir = Path(args[0]).resolve()
    if not feature_dir.is_dir():
        print(f"ディレクトリがない: {feature_dir}")
        return 2

    features = load_features(feature_dir)
    check_graph(features)
    check_readme(feature_dir, features)
    check_spec_order(feature_dir, features)
    check_rank_table(feature_dir, features)
    check_premises(feature_dir)
    check_targets(feature_dir, features)
    backlog_path = find_backlog(feature_dir)
    bl = check_backlog(backlog_path, features)

    if LENIENT and errors:
        warnings.extend(f"（--lenient でエラーから警告に落とした）{e}" for e in errors)
        errors.clear()
    counts = " / ".join(f"{c} {sum(1 for f in features.values() if f['category'] == c)}" for c in CATEGORIES)
    print(f"機能ファイル: {len(features)} 件（{counts}）")
    if backlog_path and backlog_path.exists():
        print(f"backlog: 候補 {bl['候補']} / 却下 {bl['却下']} / 機能化済み {bl['機能化済み']}（{backlog_path}）")
    for w in warnings:
        print(f"[警告] {w}")
    for e in errors:
        print(f"[エラー] {e}")
    print(f"エラー {len(errors)} 件 / 警告 {len(warnings)} 件")
    if "--graph" in sys.argv:
        print_graph(feature_dir, features)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
