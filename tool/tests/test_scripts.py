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
BALANCE = SKILLS / "gamekit-balance" / "scripts" / "balance.py"
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


class MissingArtifactsTest(RepoCase):
    def test_ensure_reports_missing_ui_and_tuning_for_specified_feature(self) -> None:
        name = "001-core"
        # Spec Kit で仕様化してから取り込んだ機能（tasks.md はあるが ui.md・tuning.md がない）
        self.write_specs(self.repo, name, "- [ ] T001 実装\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "spec")
        proc = helper(self.repo, "ensure", name, "--phase", "coding")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("MISSING_ARTIFACTS: ui.md tuning.md", proc.stdout)
        state = helper(self.repo, "state", name, "--phase", "all")
        self.assertIn("MISSING_ARTIFACTS: ui.md tuning.md", state.stdout)

        wt = self.repo / ".worktrees" / name
        (wt / "specs" / name / "ui.md").write_text("**対象**: UI なし\n", encoding="utf-8")
        state = helper(self.repo, "state", name, "--phase", "coding")
        self.assertIn("MISSING_ARTIFACTS: tuning.md", state.stdout)
        (wt / "specs" / name / "tuning.md").write_text("調整値なし\n", encoding="utf-8")
        state = helper(self.repo, "state", name, "--phase", "coding")
        self.assertNotIn("MISSING_ARTIFACTS", state.stdout)

    def test_spec_phase_and_unspecified_feature_do_not_report(self) -> None:
        name = "002-new"
        proc = helper(self.repo, "ensure", name, "--phase", "spec")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("MISSING_ARTIFACTS", proc.stdout)
        proc = helper(self.repo, "state", name, "--phase", "all")
        self.assertNotIn("MISSING_ARTIFACTS", proc.stdout)


class CoverageTest(unittest.TestCase):
    TARGETS_HEAD = (
        "# バランスの目標値\n\n"
        "| ID | 指標 | シナリオ | 下限 | 上限 | 根拠 | 機能 |\n|---|---|---|---|---|---|---|\n"
        "| BT-001 | gold | early | 1 | - | economy.md | 全体 |\n\n"
        "## 柱と仮説の検算\n\n| 対象 | 検算の方法 | 根拠 |\n|---|---|---|\n"
        "| （例）柱 1 | BT-001 | 例 |\n"
    )

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        (self.tmp / ".gamekit").mkdir()
        (self.tmp / ".gamekit" / "config.yaml").write_text("title: t\n", encoding="utf-8")
        game = self.tmp / "docs" / "game"
        game.mkdir(parents=True)
        (game / "pillars.md").write_text(
            "# デザインの柱\n\n## 柱\n\n### 柱 1: 土が主役\n\n本文\n\n### 柱 2: 手が希少\n\n### 柱 3: 取り返しがつく\n",
            encoding="utf-8")
        (game / "core-loop.md").write_text(
            "# コアループ\n\n## 主要な意思決定\n\n| ID | 意思決定 |\n|---|---|\n| D1 | 区画を選ぶ |\n\n"
            "## 仮説\n\n| ID | 仮説 | 反証の条件 | 確かめ方の案 | 状態 |\n|---|---|---|---|---|\n"
            "| H1 | 判断が成り立つ | 一択になる | MVP1 | 未検証 |\n| H2 | 塩害が起きる | 起きない | sim | 未検証 |\n"
            "| H3 | | | | 未検証 |\n",
            encoding="utf-8")
        (self.tmp / "docs" / "balance").mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def coverage(self, rows: str) -> subprocess.CompletedProcess:
        (self.tmp / "docs" / "balance" / "targets.md").write_text(self.TARGETS_HEAD + rows, encoding="utf-8")
        return run([sys.executable, str(BALANCE), "--root", str(self.tmp), "coverage"], self.tmp)

    def test_missing_rows_and_unknown_bt_are_errors_playtest_and_exempt_are_info(self) -> None:
        proc = self.coverage(
            "| 柱 1 | BT-001 | gold が土の良さを表す |\n"
            "| 柱 2 | プレイ確認（002 の T041） | 判断は遊んで確かめる |\n"
            "| H1 | 対象外（MVP1 の範囲） | 001 では測れない |\n"
            "| H2 | BT-099 | 存在しない |\n")
        self.assertEqual(proc.returncode, 1, proc.stdout)
        out = proc.stdout
        self.assertIn("ERROR: 柱3: 「柱と仮説の検算」の表に行がない", out)
        self.assertIn("BT-099", out)
        self.assertRegex(out, r"ERROR: .*H2: 目標値の表にない BT")
        self.assertRegex(out, r"INFO: .*柱2: プレイ確認だけで検算する")
        self.assertRegex(out, r"INFO: .*H1: 対象外")
        self.assertNotIn("H3", out)  # テンプレートの空の行は仮説に数えない
        self.assertIn("pillars=3 hypotheses=2 covered_by_bt=1", out)

    def test_all_covered_passes(self) -> None:
        proc = self.coverage(
            "| 柱 1 | BT-001 | a |\n| 柱 2 | BT-001 | b |\n| 柱 3 | プレイ確認（T041） | c |\n"
            "| H1 | プレイ確認（MVP1） | d |\n| H2 | BT-001 | e |\n")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("errors=0", proc.stdout)
        self.assertIn("bt_rate=60%", proc.stdout)

    def test_empty_method_is_error(self) -> None:
        proc = self.coverage("| 柱 1 | | a |\n| 柱 2 | BT-001 | b |\n| 柱 3 | BT-001 | c |\n"
                             "| H1 | BT-001 | d |\n| H2 | BT-001 | e |\n")
        self.assertEqual(proc.returncode, 1)
        self.assertRegex(proc.stdout, r"ERROR: .*柱1: 検算の方法が空か読めない")


if __name__ == "__main__":
    unittest.main()


VALIDATE_FEATURES = SKILLS / "gamekit-features" / "scripts" / "validate.py"


def write_feature(root: Path, name: str, weight: str | None) -> None:
    d = root / "docs" / "feature"
    d.mkdir(parents=True, exist_ok=True)
    header = "**状態**: 未着手 | **区分**: 垂直スライス | **想定順序**: 1 | **依存**: —"
    if weight is not None:
        header += f" | **重さ**: {weight}"
    (d / f"{name}.md").write_text(f"# 機能\n\n{header}\n\n## 概要\n\nx\n", encoding="utf-8")


class WeightTest(RepoCase):
    def test_ensure_and_state_report_weight_from_feature_file_or_default(self) -> None:
        write_feature(self.repo, "001-foo", "軽")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "feature")
        proc = helper(self.repo, "ensure", "001-foo", "--phase", "all")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("WEIGHT: 軽", proc.stdout)
        proc = helper(self.repo, "state", "001-foo", "--phase", "all", "--weight", "重")
        self.assertIn("WEIGHT: 重", proc.stdout)
        # 機能ファイルがない（重さの欄がない）機能は 標準
        proc = helper(self.repo, "state", "002-bar", "--phase", "all")
        self.assertIn("WEIGHT: 標準", proc.stdout)
        proc = helper(self.repo, "state", "001-foo", "--phase", "all", "--weight", "超重")
        self.assertNotEqual(proc.returncode, 0)

    def test_skipped_counts_as_done_and_status_shows_it(self) -> None:
        name = "001-foo"
        write_feature(self.repo, name, "軽")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "feature")
        helper(self.repo, "ensure", name, "--phase", "all")
        wt = self.repo / ".worktrees" / name
        for step in ("S2", "S3"):
            self.assertEqual(helper(wt, "checkpoint", name, step, f"docs: {step}").returncode, 0)
        proc = helper(wt, "checkpoint", name, "S4", "docs: S4", "--skipped", "軽: clarify は 1 回")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("（省略）", proc.stdout)
        self.assertIn("Gamekit-Skipped: S4 軽: clarify は 1 回", git(wt, "log", "-1", "--format=%B"))
        proc = helper(self.repo, "state", name, "--phase", "all")
        self.assertIn("COMPLETED_STEPS: S2 S3 S4", proc.stdout)
        self.assertIn("NEXT_STEP: S4-1", proc.stdout)
        self.assertIn("SKIPPED_STEPS: S4", proc.stdout)
        status = helper(self.repo, "status")
        row = next(line for line in status.stdout.splitlines() if line.startswith(f"| {name} "))
        self.assertIn("（省略: S4）", row)

    def test_heavy_feature_cannot_skip_without_force(self) -> None:
        name = "001-foo"
        write_feature(self.repo, name, "重")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "feature")
        helper(self.repo, "ensure", name, "--phase", "all")
        wt = self.repo / ".worktrees" / name
        for step in ("S2", "S3"):
            helper(wt, "checkpoint", name, step, f"docs: {step}")
        proc = helper(wt, "checkpoint", name, "S4", "docs: S4", "--skipped", "省きたい")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("省けません", proc.stderr)
        # 標準でも S7-1 は省けない
        proc = helper(wt, "checkpoint", name, "S4", "docs: S4", "--skipped", "省きたい", "--weight", "標準")
        self.assertNotEqual(proc.returncode, 0)
        proc = helper(wt, "checkpoint", name, "S4", "docs: S4", "--skipped", "理由を確かめた", "--force")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("S4", helper(self.repo, "state", name, "--phase", "all").stdout)


class ValidateWeightTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp()).resolve()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def validate(self) -> subprocess.CompletedProcess:
        return run([sys.executable, str(VALIDATE_FEATURES), str(self.tmp / "docs" / "feature")], self.tmp)

    def test_missing_weight_is_warning(self) -> None:
        write_feature(self.tmp, "001-foo", None)
        out = self.validate()
        line = next((l for l in (out.stdout + out.stderr).splitlines() if "**重さ** がない" in l), "")
        self.assertIn("警告", line)

    def test_invalid_weight_is_error_and_valid_weight_is_silent(self) -> None:
        write_feature(self.tmp, "001-foo", "超重")
        out = self.validate()
        line = next((l for l in (out.stdout + out.stderr).splitlines() if "重さ「超重」" in l), "")
        self.assertIn("エラー", line)
        write_feature(self.tmp, "001-foo", "標準")
        out = self.validate()
        self.assertNotIn("重さ", out.stdout + out.stderr)
