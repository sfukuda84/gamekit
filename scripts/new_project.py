#!/usr/bin/env python3
"""new_project.py - gamekit のゲームのプロジェクトを作る（既存のプロジェクトへの取り込みにも使う）

使い方:
  python3 new_project.py <プロジェクトのディレクトリ> [--title <仮題>] [--engine godot|web|other] [--language <言語>]
                         [--link] [--adopt]
  python3 new_project.py --relink <ディレクトリ>   # 各エージェントのスキルディレクトリのリンクだけを作り直す

- 新しいディレクトリなら、scaffold の規則ファイル（CLAUDE.md、AGENTS.md、GEMINI.md、opencode.json、.kiro/steering/）、
  Spec Kit の .specify/ と .opencode/commands/、スキル（skills/speckit/、skills/gamekit/）を置き、
  各エージェントのスキルディレクトリ（.claude/skills/ など）からリンクし、git init と初回コミットを行う。
- --adopt: 既存のプロジェクトに取り込む。既存のファイルは上書きせず、衝突したものは一覧にするだけにする。
  .gitignore は、gamekit が動くのに要る行（scripts/gitignore-required.txt）のうち足りないものだけを足す。
  git リポジトリなら初回コミットは作らない（変更は人が確かめてからコミットする）。
- --link: スキルをコピーせず、scaffold のスキルへのシンボリックリンクにする（scaffold の更新がすぐ反映される）。
- --engine は .gamekit/config.yaml の engine に書く（あとで gamekit-architecture が見直す）。
標準ライブラリだけで書く（Python 3.9 以上）。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCAFFOLD = Path(__file__).resolve().parents[1]
RULE_FILES = ["CLAUDE.md", "AGENTS.md", "GEMINI.md", "opencode.json",
              ".kiro/steering/language.md", ".kiro/steering/game-development.md"]
# scaffold のライセンス表示は、ゲームのリポジトリのルートに置かず .gamekit/ に置く（ゲーム自体のライセンスと混ぜない）
NOTICE = ("THIRD_PARTY_NOTICES.md", ".gamekit/THIRD_PARTY_NOTICES.md")
TREES = [".specify", ".opencode/commands"]
SKILL_SETS = ["speckit", "gamekit"]
AGENT_SKILL_DIRS = [".claude/skills", ".agents/skills", ".kiro/skills"]
STEERING_IMPORTS = ["@.kiro/steering/language.md", "@.kiro/steering/game-development.md"]
GITIGNORE_MARK = "# ===== gamekit が使う行（new_project.py --adopt が追記） ====="
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", ".cache", "feature.json")


def copy_tree_missing(src: Path, dst: Path, rel_base: str, added: list[str], skipped: list[str]) -> None:
    """src の下のファイルを、dst に無いものだけコピーする（既存のファイルは上書きしない）。"""
    for path in sorted(src.rglob("*")):
        rel = path.relative_to(src)
        if any(part in ("__pycache__", ".cache") for part in rel.parts) or path.name in (".DS_Store", "feature.json"):
            continue
        if path.suffix == ".pyc":
            continue
        out = dst / rel
        if path.is_dir():
            continue
        if out.exists():
            skipped.append(f"{rel_base}/{rel.as_posix()}")
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, out)
    added.append(rel_base + "/")


def place_skills(target: Path, link: bool, added: list[str], skipped: list[str]) -> None:
    for name in SKILL_SETS:
        src = SCAFFOLD / "skills" / name
        dst = target / "skills" / name
        if dst.exists() or dst.is_symlink():
            skipped.append(f"skills/{name}/")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if link:
            dst.symlink_to(src, target_is_directory=True)
        else:
            shutil.copytree(src, dst, ignore=IGNORE)
        added.append(f"skills/{name}/" + ("（リンク）" if link else ""))


def link_agent_dirs(target: Path, conflicts: list[str]) -> int:
    """各エージェントのスキルディレクトリから skills/<set>/<skill> へ相対リンクを張る。作った数を返す。

    すでにある同名のディレクトリ（speckit をコピーで入れていたプロジェクトなど）は残し、conflicts に挙げる。
    リンクを作れない環境（Windows で開発者モードがオフなど）では、実体をコピーする。
    """
    made = 0
    for base in AGENT_SKILL_DIRS:
        d = target / base
        d.mkdir(parents=True, exist_ok=True)
        for name in SKILL_SETS:
            skills_dir = target / "skills" / name
            if not skills_dir.is_dir():
                continue
            for s in sorted(p.name for p in skills_dir.iterdir() if p.is_dir() and not p.name.startswith("__")):
                link = d / s
                want = os.path.relpath(skills_dir / s, d)
                if link.is_symlink():
                    if os.readlink(link) == want:
                        continue
                    conflicts.append(f"{base}/{s}（別の場所へのリンク: {os.readlink(link)}）")
                    continue
                if link.exists():
                    conflicts.append(f"{base}/{s}（既存のディレクトリ）")
                    continue
                try:
                    link.symlink_to(want, target_is_directory=True)
                except OSError:
                    shutil.copytree(skills_dir / s, link, ignore=IGNORE)
                    print(f"WARN: {base}/{s} はリンクを作れなかったため、実体をコピーしました。", file=sys.stderr)
                made += 1
    return made


def required_gitignore_lines(scaffold: Path) -> list[str]:
    """gamekit が動くのに要る .gitignore の行（scripts/gitignore-required.txt）。"""
    path = scaffold / "scripts" / "gitignore-required.txt"
    if not path.is_file():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def merge_gitignore(target: Path, added: list[str], skipped: list[str]) -> None:
    """.gitignore がなければ scaffold のものをコピーする。あれば、gamekit が動くのに要る行のうち足りないものだけを足す。

    scaffold の .gitignore のほかの行（OS、エディタ、言語ごとの生成物など）は、既存のプロジェクトの事情に任せて足さない。
    """
    src, dst = SCAFFOLD / ".gitignore", target / ".gitignore"
    if not dst.exists():
        shutil.copy2(src, dst)
        added.append(".gitignore")
        return
    current = {line.strip() for line in dst.read_text(encoding="utf-8", errors="replace").splitlines()}
    wanted = [line for line in required_gitignore_lines(SCAFFOLD) if line not in current]
    if not wanted:
        skipped.append(".gitignore")
        return
    text = dst.read_text(encoding="utf-8", errors="replace")
    if text and not text.endswith("\n"):
        text += "\n"
    dst.write_text(text + f"\n{GITIGNORE_MARK}\n" + "\n".join(wanted) + "\n", encoding="utf-8")
    added.append(f".gitignore（{len(wanted)} 行を追記）")


def steering_hints(target: Path) -> list[str]:
    """既存の CLAUDE.md などが gamekit の steering を読み込んでいなければ、足す行を案内する。"""
    hints = []
    for name in ("CLAUDE.md", "GEMINI.md"):
        p = target / name
        if p.exists():
            text = p.read_text(encoding="utf-8", errors="replace")
            missing = [line for line in STEERING_IMPORTS if line not in text]
            if missing:
                hints.append(f"{name} に次の行を足す: " + " / ".join(missing))
    p = target / "AGENTS.md"
    if p.exists() and ".kiro/steering/game-development.md" not in p.read_text(encoding="utf-8", errors="replace"):
        hints.append("AGENTS.md の読み込みリストに `.kiro/steering/game-development.md` を足す")
    return hints


def relink_command(target: Path) -> str:
    """リンクを張り直すコマンド。uv で入れた new-gamekit-project から呼ばれたときは、scaffold が一時的な場所にあって
    終わると消えるので、このファイルのパスではなく、取り込みをもう一度実行するコマンドを示す（足りないリンクだけを作る）。"""
    launcher = os.environ.get("GAMEKIT_LAUNCHER")
    if launcher:
        return f'{launcher} "{target}" --adopt'
    return f"python3 {Path(__file__).resolve()} --relink {target}"


def main() -> None:
    ap = argparse.ArgumentParser(description="gamekit のゲームのプロジェクトを作る")
    ap.add_argument("target")
    ap.add_argument("--title", default="")
    ap.add_argument("--engine", choices=["godot", "web", "other"], default=None)
    ap.add_argument("--language", default=None, help="gdscript / csharp / typescript など")
    ap.add_argument("--link", action="store_true", help="スキルを scaffold へのシンボリックリンクにする")
    ap.add_argument("--adopt", action="store_true", help="既存のプロジェクトに取り込む（上書きしない）")
    ap.add_argument("--relink", action="store_true", help="各エージェントのスキルディレクトリのリンクだけを作り直す")
    args = ap.parse_args()

    target = Path(args.target).expanduser().resolve()
    if args.relink:
        conflicts: list[str] = []
        made = link_agent_dirs(target, conflicts)
        print(f"LINKED: {made}")
        for c in conflicts:
            print(f"CONFLICT: {c}")
        return
    if target.exists() and any(target.iterdir()) and not args.adopt:
        sys.exit(f"{target} は空ではありません。既存のプロジェクトに取り込むなら --adopt を付けてください。")
    target.mkdir(parents=True, exist_ok=True)
    added: list[str] = []
    skipped: list[str] = []
    conflicts = []

    for rel in RULE_FILES:
        src, dst = SCAFFOLD / rel, target / rel
        if dst.exists():
            skipped.append(rel)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        added.append(rel)
    merge_gitignore(target, added, skipped)
    src, dst = SCAFFOLD / NOTICE[0], target / NOTICE[1]
    if src.exists() and not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        added.append(NOTICE[1])

    for rel in TREES:
        copy_tree_missing(SCAFFOLD / rel, target / rel, rel, added, skipped)

    place_skills(target, args.link, added, skipped)
    link_agent_dirs(target, conflicts)
    added.append("、".join(d + "/" for d in AGENT_SKILL_DIRS) + "（リンク）")

    is_repo = (target / ".git").exists()
    if not is_repo:
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=target, check=True)
    helper = target / "skills" / "gamekit" / "gamekit-status" / "scripts" / "gamekit.py"
    cmd = [sys.executable, str(helper), "--root", str(target), "init"]
    if args.adopt:
        cmd.append("--config-only")  # paths を既存の配置に合わせる前に、空のディレクトリを作らない
    for flag, value in (("--title", args.title), ("--engine", args.engine), ("--language", args.language)):
        if value:
            cmd += [flag, value]
    subprocess.run(cmd, check=True)
    added.append(".gamekit/config.yaml")

    if not is_repo:
        subprocess.run(["git", "add", "-A"], cwd=target, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "chore(game): gamekit を初期化"], cwd=target, check=True)

    print(f"TARGET: {target}")
    print("ADDED: " + ", ".join(added))
    if skipped:
        shown = skipped[:15]
        more = f" ほか {len(skipped) - len(shown)} 件" if len(skipped) > len(shown) else ""
        print("SKIPPED（既存のため変更していない）: " + ", ".join(shown) + more)
    if conflicts:
        print(f"CONFLICT（同名のスキルが既にあるため残した。{len(conflicts)} 件）:")
        for c in conflicts[:6]:
            print(f"  {c}")
        if len(conflicts) > 6:
            print(f"  ほか {len(conflicts) - 6} 件")
    print("\n次の手順:")
    if args.adopt:
        step = 1
        print(f"  {step}. 追加されたファイルを確かめてコミットする"); step += 1
        for hint in steering_hints(target):
            print(f"  {step}. {hint}"); step += 1
        if conflicts:
            print(f"  {step}. CONFLICT のスキルは既存のものを残した。gamekit 版に揃えるなら、既存のものを消してから "
                  f"`{relink_command(target)}` を実行する（足りないリンクだけを作る）"); step += 1
        print(f"  {step}. .gamekit/config.yaml の paths・engine・commands を既存の配置に合わせる"); step += 1
        print(f"  {step}. python3 skills/gamekit/gamekit-status/scripts/gamekit.py doctor で確かめる"); step += 1
        print(f"  {step}. /gamekit-bootstrap --adopt で、既存の資料から足りない成果物だけを作る"
              "（speckit の specs/ と進捗の記録はそのまま引き継がれる）")
    else:
        print(f'  cd "{target}" && claude "/gamekit-bootstrap <1 文のコンセプト>"')


if __name__ == "__main__":
    main()
