"""skills/gamekit のスクリプト（worktree_helper.py、validate_design.py、gamekit.py）のテスト。

一時的な git リポジトリを作り、スクリプトを別のプロセスで実行して、出力と終了コードを確かめる。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCAFFOLD = Path(__file__).resolve().parents[2]
SKILLS = SCAFFOLD / "skills" / "gamekit"
HELPER = SKILLS / "gamekit-worktree" / "scripts" / "worktree_helper.py"
VALIDATE_DESIGN = SKILLS / "gamekit-design" / "scripts" / "validate_design.py"
GAMEKIT = SKILLS / "gamekit-status" / "scripts" / "gamekit.py"
DESIGN_TEMPLATES = SKILLS / "gamekit-design" / "templates"

GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
}
ALL_STEPS = ["S2", "S3", "S4", "S4-1", "S4-2", "S5", "S6", "S7-1", "S7-2", "S7-3",
             "S8", "S9", "S9-1", "S10", "S11"]


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GAMEKIT_", "SPECKIT_", "CLAUDE_CODE_REMOTE"))}
    env.update(GIT_ENV)
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=env)


def git(cwd: Path, *args: str) -> str:
    proc = run(["git", *args], cwd)
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)}: {proc.stderr}")
    return proc.stdout.strip()


def helper(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return run([sys.executable, str(HELPER), *args], cwd)


class RepoCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.repo = self.tmp / "game"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / "README.md").write_text("# game\n", encoding="utf-8")
        (self.repo / ".gitignore").write_text(".worktrees/\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "init")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_specs(self, root: Path, name: str, tasks: str) -> None:
        d = root / "specs" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "spec.md").write_text("# spec\n", encoding="utf-8")
        (d / "plan.md").write_text("# plan\n", encoding="utf-8")
        (d / "tasks.md").write_text(tasks, encoding="utf-8")


class DeferredTasksTest(RepoCase):
    def test_finish_does_not_stop_on_deferred_and_reports_them(self) -> None:
        name = "001-foo"
        proc = helper(self.repo, "ensure", name, "--phase", "all")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        wt = self.repo / ".worktrees" / name
        self.write_specs(wt, name, "# tasks\n\n- [x] T001 済んだ\n"
                                   "- [ ] T002 [US1] [後] 保存を作る（いつ: 003 の前）\n"
                                   "- [ ] T003 [人] プレイ確認（完了の確かめ方: 記録がある）\n")
        for step in ALL_STEPS:
            proc = helper(wt, "checkpoint", name, step, f"docs({name}): {step}")
            self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = helper(self.repo, "finish", name, "--phase", "all")
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertIn("DEFERRED_TASKS_PENDING: 1", proc.stdout)
        self.assertIn("HUMAN_TASKS_PENDING: 1", proc.stdout)
        self.assertIn("T002", proc.stdout)

        status = helper(self.repo, "status")
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn("後の作業", status.stdout)
        row = next(line for line in status.stdout.splitlines() if line.startswith(f"| {name} "))
        self.assertTrue(row.rstrip().endswith("| 残り 1 件 | 残り 1 件 |"), row)

        listed = helper(self.repo, "deferred-tasks", name)
        self.assertIn("T002", listed.stdout)
        self.assertNotIn("T003", listed.stdout)

    def test_unchecked_ai_task_still_stops_finish(self) -> None:
        name = "001-foo"
        helper(self.repo, "ensure", name, "--phase", "all")
        wt = self.repo / ".worktrees" / name
        self.write_specs(wt, name, "- [x] T001 済んだ\n- [ ] T002 まだ\n- [ ] T003 [後] 後で（いつ: 公開時）\n")
        for step in ALL_STEPS:
            helper(wt, "checkpoint", name, step, f"docs({name}): {step}")
        proc = helper(self.repo, "finish", name, "--phase", "all")
        self.assertEqual(proc.returncode, 3)
        self.assertIn("UNCHECKED_TASKS", proc.stderr)
        self.assertIn("T002", proc.stderr)
        self.assertNotIn("T003", proc.stderr)


class PartialMergeTest(RepoCase):
    def test_partial_merges_without_advancing_progress(self) -> None:
        name = "002-bar"
        # 仕様は main にある（仕様工程を終えた機能）
        self.write_specs(self.repo, name, "## Phase 1\n- [ ] T001 ゲート\n## Phase 2\n- [ ] T002 本体\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "spec")
        proc = helper(self.repo, "ensure", name, "--phase", "coding")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        wt = self.repo / ".worktrees" / name
        tasks = wt / "specs" / name / "tasks.md"
        tasks.write_text(tasks.read_text(encoding="utf-8").replace("- [ ] T001", "- [x] T001"), encoding="utf-8")
        (wt / "gate.sh").write_text("echo ok\n", encoding="utf-8")
        git(wt, "add", "-A")
        git(wt, "commit", "-qm", "Phase 1 だけを実装")

        # --partial なしでは S8〜S11 が終わっていないので止まる
        proc = helper(self.repo, "finish", name, "--phase", "coding")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--partial", proc.stderr)

        proc = helper(self.repo, "finish", name, "--phase", "coding", "--partial")
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertIn("PARTIAL", proc.stdout)
        self.assertEqual(git(self.repo, "log", "-1", "--format=%s"), f"merge({name}): partial")
        self.assertTrue((self.repo / "gate.sh").is_file())
        self.assertFalse((self.repo / ".worktrees" / name).exists())

        state = helper(self.repo, "state", name, "--phase", "coding")
        self.assertIn("NEXT_STEP: S8", state.stdout)
        self.assertNotIn("S8", state.stdout.split("COMPLETED_STEPS:")[1].splitlines()[0])
        status = helper(self.repo, "status")
        row = next(line for line in status.stdout.splitlines() if line.startswith(f"| {name} "))
        self.assertIn("一部をマージ済み", row)

        # 続きは通常どおり main から worktree を作って S8 から
        proc = helper(self.repo, "ensure", name, "--phase", "coding")
        self.assertIn("NEXT_STEP: S8", proc.stdout)

    def test_partial_is_rejected_for_spec_phase(self) -> None:
        name = "003-baz"
        helper(self.repo, "ensure", name, "--phase", "spec")
        proc = helper(self.repo, "finish", name, "--phase", "spec", "--partial")
        self.assertNotEqual(proc.returncode, 0)


class ValidateDesignFrTest(unittest.TestCase):
    def test_references_to_other_specs_fr_are_not_warned(self) -> None:
        tmp = Path(tempfile.mkdtemp()).resolve()
        try:
            design = tmp / "docs" / "design"
            shutil.copytree(DESIGN_TEMPLATES, design)
            feature = tmp / "specs" / "000-x"
            feature.mkdir(parents=True)
            (feature / "spec.md").write_text(
                "# spec\n\n### Functional Requirements\n\n"
                "- **FR-001**: タイトルを出す。001 の FR-040〜FR-047 の保存形式を使う\n"
                "- **FR-002**: ログを出す（画面なし）\n", encoding="utf-8")
            ui = (DESIGN_TEMPLATES / "ui.md").read_text(encoding="utf-8")
            ui = ui.replace("FR-001, FR-002", "FR-001").replace("| FR-003 |", "| FR-001 |")
            (feature / "ui.md").write_text(ui, encoding="utf-8")
            proc = run([sys.executable, str(VALIDATE_DESIGN), str(design), "--feature", str(feature)], tmp)
            out = proc.stdout + proc.stderr
            self.assertIn("FR-002", out)  # 定義した要件に画面がない → 警告
            self.assertNotIn("「FR-040」", out)  # ほかの仕様の要件への参照は数えない
            self.assertNotIn("「FR-047」", out)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class GamekitCheckpointTest(RepoCase):
    def gk(self, *args: str) -> subprocess.CompletedProcess:
        return run([sys.executable, str(GAMEKIT), "--root", str(self.repo), *args], self.repo)

    def test_checkpoint_records_steps_that_bootstrap_counts(self) -> None:
        proc = self.gk("checkpoint", "G1", "docs(bootstrap): G1 種を作成", "--allow-empty")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("NEXT_STEP: G2", proc.stdout)
        (self.repo / "seed.md").write_text("seed\n", encoding="utf-8")
        proc = self.gk("checkpoint", "g2", "docs(bootstrap): G2 調査",
                       "--trailer", "Co-Authored-By: Someone <someone@example.com>")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = self.gk("bootstrap")
        self.assertIn("COMPLETED_STEPS: G1 G2", state.stdout)
        self.assertIn("NEXT_STEP: G3", state.stdout)
        trailers = git(self.repo, "log", "-1", "--format=%(trailers)")
        self.assertIn("Gamekit-Bootstrap: G2", trailers)
        self.assertIn("Co-Authored-By: Someone <someone@example.com>", trailers)
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_checkpoint_rejects_unknown_step_and_empty_without_flag(self) -> None:
        proc = self.gk("checkpoint", "G15", "x", "--allow-empty")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("G15", proc.stderr)
        proc = self.gk("checkpoint", "G1", "x")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--allow-empty", proc.stderr)


if __name__ == "__main__":
    unittest.main()
