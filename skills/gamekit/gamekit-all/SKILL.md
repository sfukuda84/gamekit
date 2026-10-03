---
name: "gamekit-all"
description: "ゲームの機能の仕様工程と実装工程を 1 つの Git worktree で通して実行するスキル。worktree の準備（既存があれば再利用して続きから再開）、gamekit-feature の仕様工程（specify・clarify x 2・画面と HUD の仕様・調整仕様・plan・tasks・analyze x 3）、gamekit-coding の実装工程（implement・converge・バランス検証・5 軸レビュー x 2）を途中でマージせずに続けて行い、最後に main へのマージ、引き継ぎ書の更新、後片付けを行う。--auto を付けると、質問せずに推奨案を採用して進める。--with-mock を付けると、画面仕様でモックも作る。「次の機能を進めて」「001 を作って」と言われたとき、または /gamekit-all と打たれたときに使う。"
argument-hint: "フィーチャー番号または範囲と、任意の --auto と --with-mock（例: 001, 002-005, all, all --auto, 003 --with-mock, または省略して次の未完了）"
compatibility: "Requires git and Python 3.9+, spec-kit project structure with .specify/ and .gamekit/config.yaml"
user-invocable: true
disable-model-invocation: false
---

# gamekit-all スキル（通し: S1 → S2〜S11 → S12）

仕様工程と実装工程を、1 つの worktree の中で途中マージなしに通して実行する。本体の手順はこのファイルには書かず、次の 2 つのファイルの「§3 本体」をそのまま使う。

- 仕様工程 S2〜S7-3（S4-1、S4-2 を含む）: [`gamekit-feature` の §3](../gamekit-feature/SKILL.md)
- 実装工程 S8〜S11（S9-1 を含む）: [`gamekit-coding` の §3](../gamekit-coding/SKILL.md)

**ステップ番号、ヘルパースクリプト（`$HELPER`）、再開、安全規則、対話、引数の解釈は [`gamekit-worktree`](../gamekit-worktree/SKILL.md) に従う。** 作業を始める前に、`gamekit-worktree`、`gamekit-feature`、`gamekit-coding` の 3 つの SKILL.md を読むこと。

## 1. ユーザー入力・引数

```text
$ARGUMENTS
```

引数の解釈と複数フィーチャーの進め方は `gamekit-worktree` の §5 に従う。自動検出では `--phase all` を使う。

引数に `--auto` があるときは、仕様工程から実装工程、S12 までのすべての質問を `gamekit-worktree` §6 の自動モードで扱う。`gamekit-feature` と `gamekit-coding` の本文にある 💬 の質問も、質問せずに推奨案を採用する。自動モードでも止まる場面（マージの競合、目標値の変更が要るときなど）では、§6「止まったときの扱い」に従う。

引数に `--with-mock` があるときは、仕様工程の S4-1（画面と HUD の仕様）でモックを作る（`gamekit-design`）。

## 2. 実行の流れ

始める前に、ゲームの工程（`gamekit-bootstrap`）が終わっていることを確かめる。`python3 <skills>/gamekit-status/scripts/gamekit.py bootstrap` の `NEXT_STEP` が `DONE` でなければ、残っているステップを示し、先に `gamekit-bootstrap` を実行するよう案内する。既存のプロジェクトに取り込んだ（`--adopt`）などで工程の記録がないときは、`docs/feature/` と憲章があれば、ユーザーに確かめて進めてよい（自動モードでは、機能概要と憲章があれば進める）。

対象フィーチャーごとに、次を順に行う。

1. **S1 準備**: `gamekit-worktree` §3「S1 準備」に従い、`$HELPER ensure <feature> --phase all` を実行する。
   - 仕様がすでに `main` にマージ済みのフィーチャーは、S2〜S7-3 が完了済みと判定され、`NEXT_STEP` が S8 になる。
2. **仕様工程**: `gamekit-feature` の §3 の S2〜S7-3 のうち、`NEXT_STEP` 以降を順に実行する。
   - `gamekit-feature` の §2（S1 と S12）は実行しない。**S7-3 の後で `finish` を実行せず、マージしないこと。**
3. **実装工程**: 同じ worktree のまま、`gamekit-coding` の §3 の S8〜S11 を順に実行する。
   - `gamekit-coding` の §2（S1 と S12）は実行しない。worktree を作り直さないこと。
4. **S12 片付け**: `gamekit-worktree` §3「S12 片付け」に従い、`$HELPER finish <FEATURE_NAME> --phase all` を実行し、引き継ぎ書を更新してコミットする。
5. 次のフィーチャーがあれば 1 に戻る。

途中で中断した場合は、もう一度 `gamekit-all` を実行すれば、残っている worktree を使って続きのステップから再開する。仕様工程の途中なら `gamekit-feature`、実装工程の途中なら `gamekit-coding` で再開することもできる。その場合は、再開したスキルの S12 で `main` にマージされる。

セッションを区切るとき（コンテキストが長くなった、作業を人に引き継ぐなど）は、ステップの境目で止め、`gamekit.py handover --note "<止めた理由と次の作業>"` で引き継ぎ書を更新する。worktree の中で止めたときは、引き継ぎ書は main ではなく、その場でコミットせずに残してよい（次の S12 の更新で上書きされる）。

## 3. 完了報告

各フィーチャーの完了時と、指定範囲の全体の完了時に、`gamekit-feature` §4 と `gamekit-coding` §4 の項目をまとめて報告する。

- 完了したフィーチャー名と番号、マージコミット
- 仕様工程の要約（clarify で確定した決定事項、調整仕様と目標値、analyze の検証結果）
- 実装工程の要約（実装内容、テスト結果、converge の結果、バランス検証の結果、レビューで直した指摘）
- 残っている `[人]` のタスク（プレイ確認など。`finish` の `HUMAN_TASKS_PENDING`）と、片付けた後の手順（`gamekit-worktree` §3「人のタスクの片付け」）
- 残っている `[後]` のタスク（`finish` の `DEFERRED_TASKS_PENDING`）と、それぞれをいつ行うか（`gamekit-worktree` §3「後の段階のタスク」）
- 飛ばした、または中断したフィーチャーとその理由
- `--auto` のとき: 自動で採用した判断の要約（`auto-decisions.md`）と、止まったフィーチャーについてユーザーに判断してほしい事項
- 次の案内: `$HELPER next --phase all` の結果。最初の垂直スライス（`docs/feature/spec_order.md` で印のある範囲）を終えたときは、プレイ確認とコアループの仮説の見直し（`gamekit-prototype` の更新モード）を勧める
