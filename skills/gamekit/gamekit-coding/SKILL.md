---
name: "gamekit-coding"
description: "ゲームの機能の実装工程を実行するスキル。Git worktree の準備（既存があれば再利用して続きから再開）、実装（speckit-implement。数値はマスタデータに置く）、仕様収束（speckit-converge）、バランス検証（gamekit-balance の verify。シミュレーションを回して目標値と突き合わせる）、5 軸レビュー（gamekit-review。Standards・Spec・Balance・Feel・Originality）と修正、再レビューと修正を行い、main へのマージ、引き継ぎ書の更新、後片付けまでを実行する。spec.md・tuning.md・plan.md・tasks.md が必要で、なければ gamekit-feature を案内する。「この機能を実装して」と言われたとき、または /gamekit-coding と打たれたときに使う。"
argument-hint: "フィーチャー番号または範囲と、任意の --auto と --until \"Phase N\"（例: 001, 002-005, all, all --auto, 001 --until \"Phase 1\", または省略して次の未実装）"
compatibility: "Requires git and Python 3.9+, spec-kit project structure with .specify/ and .gamekit/config.yaml"
user-invocable: true
disable-model-invocation: false
---

# gamekit-coding スキル（実装工程: S1 → S8〜S11 → S12）

仕様工程（[`gamekit-feature`](../gamekit-feature/SKILL.md)）で作った `spec.md`、`ui.md`、`tuning.md`、`plan.md`、`tasks.md` に基づき、実装、収束の検証、バランスの検証、2 回の 5 軸レビューと修正を行い、`main` にマージする。

- 仕様から実装までを 1 つの worktree で通して行う場合は [`gamekit-all`](../gamekit-all/SKILL.md) を使う。`gamekit-all` は、このファイルの「§3 本体」だけを実行する。

**ステップ番号、ヘルパースクリプト（`$HELPER`）、再開、安全規則、対話、引数の解釈は [`gamekit-worktree`](../gamekit-worktree/SKILL.md) に従う。** 作業を始める前に必ず読むこと。

パスは既定の配置で書いている。`.gamekit/config.yaml` の `paths` で読み替える。

## 1. ユーザー入力・引数

```text
$ARGUMENTS
```

引数の解釈と複数フィーチャーの進め方は `gamekit-worktree` の §5 に従う。`--auto` があるときは、下の 💬 の質問も含めて `gamekit-worktree` §6 の自動モードで進める。自動検出では `--phase coding` を使い、`main` の `tasks.md` に未完了のタスク（`- [ ]`）が残っているフィーチャーを対象にする。

引数に `--until "Phase N"` があるときは、ほかの機能の前提として、この機能の `tasks.md` のその Phase までだけを実装して止める（steering「ほかの機能の一部だけを先に作る」）。単一のフィーチャーの指定とだけ組み合わせる。

1. S1 は通常どおり（`$HELPER ensure <feature> --phase coding`）。
2. S8 の手順で、Phase 1 から指定の Phase までのタスクを実装し、`- [x]` にする。テスト・ビルド・品質ゲートを通す。その Phase の Checkpoint（`tasks.md` に書かれていれば）も確かめる。
3. S8 の `checkpoint` は記録しない（S8 は終わっていない）。区切りのコミットは trailer なしで作る。S9 以降は行わない。
4. worktree の外で `$HELPER finish <FEATURE_NAME> --phase coding --partial` を実行して `main` に入れる（`gamekit-worktree` §3「一部だけを先にマージする」）。
5. 完了報告で、実装した Phase と残りのタスクの件数、続きは `gamekit-coding <FEATURE_NAME>` で S8 から行うことを示す。

## 2. 実行の流れ（単独実行）

対象フィーチャーごとに、次を順に行う。

1. **S1 準備**: `gamekit-worktree` §3「S1 準備」に従い、`$HELPER ensure <feature> --phase coding` を実行する。
   - 仕様工程の途中の worktree がある場合は `SPEC_INCOMPLETE`、仕様がどこにもない場合は `SPEC_MISSING` で止まる。そのときは何も作らずに、`gamekit-feature` または `gamekit-all` の実行を案内する。
   - worktree がなく、仕様が `main` にマージ済みの場合は、`main` から新しい worktree を作る。
   - `gamekit-all` などで仕様工程を終えた worktree が残っている場合は、それを再利用する。
2. **本体**: 下の §3 の S8〜S11 のうち、`NEXT_STEP` 以降を順に実行する。
3. **S12 片付け**: `gamekit-worktree` §3「S12 片付け」に従い、`$HELPER finish <FEATURE_NAME> --phase coding` を実行し、引き継ぎ書を更新する。
4. 次のフィーチャーがあれば 1 に戻る。

## 3. 本体（S8〜S11）

作業場所は `WORKTREE_DIR`、仕様ディレクトリは `specs/<FEATURE_NAME>`（以下 `FEATURE_DIR`）である。各ステップの最後に `gamekit-worktree` §2 の subject で `checkpoint` を記録する。

テスト、ビルド、リンター、ヘッドレス実行のコマンドは `gamekit-worktree` §4 に従って判断する（`.gamekit/config.yaml` の `commands` が正）。以下、`$GK` は `python3 <skills>/gamekit-status/scripts/gamekit.py`、`$BAL` は `python3 <skills>/gamekit-balance/scripts/balance.py` である。

### S8: 実装（speckit-implement）

1. `speckit-implement` スキルの手順に従い、`FEATURE_DIR/tasks.md` の全タスクを実装する。
   - Phase 1（Setup）→ Phase 2（Foundational）→ Phase 3 以降（User Stories）→ Final Phase（Polish）の順を守る。
   - テストファースト（TDD）で進める。ゲームのロジック（ルール、計算、状態遷移）は、描画や入力から切り離してテストする。乱数はシードを固定してテストする。
   - **数値はマスタデータに置く**: `tuning.md` の調整値は、データの場所（`paths.data` の下）に初期値で書き、コードはそこから読む。コードに数値を直書きしない（定数として許されるのは、物理的な定義や配列の添字など調整の対象でないものだけ）。
   - 画面と HUD は `FEATURE_DIR/ui.md` と `docs/design/` に従って作る。色、文字、余白などの値はトークンから使う。
   - シーンやリソースは、テキストで書けるもの（Godot の `.tscn`・`.tres` など）は直接書く。エディタでしか作れないものは、手順を示して `[人]` のタスクにする（steering の「エージェントの行動規範」）。
   - `[人]` の付いたタスク（実機のプレイ確認など）は実行しない。手順を示して保留にし、依存しない後続のタスクを続ける。
   - タスクが終わるごとに `tasks.md` のチェックボックスを `- [x]` に更新する。区切りのよいところでは、trailer なしの通常のコミットを作ってよい。
2. テスト、ビルド、リンター、ヘッドレス実行（`commands.run_headless`。数フレーム回してエラーが出ないこと）を実行し、すべて通ることを確かめる。
3. `$BAL params specs/<FEATURE_NAME>/tuning.md` を実行し、データの場所がすべて解決し、初期値と一致することを確かめる（ERROR と WARN を 0 件にする）。
4. `checkpoint <FEATURE_NAME> S8` を記録する。

> 💬 実装中に仕様の隙間、例外時の挙動、設計方針の分岐が出てきた場合は、ユーザーに質問して合意を取る。仕様を変える場合は、コードだけでなく `spec.md`、`tuning.md`、`plan.md`、`tasks.md` にも反映する。

### S9: 仕様収束（speckit-converge）

1. `speckit-converge` スキルの手順に従い、コードベースとマスタデータを `spec.md`、`ui.md`、`tuning.md`、`plan.md`、`tasks.md`、憲章と照合する。
   - ギャップの種類（`missing`: 未実装、`partial`: 不完全、`contradicts`: 矛盾、`unrequested`: 仕様にない追加）を調べる。
   - コードに直書きされた調整値（`tuning.md` にあるのにデータから読んでいないもの、`tuning.md` にない数値で遊びに効くもの）も `contradicts` として扱う。
   - テストの不足や、考慮されていないエッジケース（S4 の例外系）も併せて調べる。
2. ギャップがある場合は、`tasks.md` の末尾に `## Phase N: Convergence` として不足タスクを追加し、S8 と同じ手順で実装とテストを行う。もう一度照合し、「✅ Converged」になるまで繰り返す。
3. 未達のギャップが 0 件になったら、`checkpoint <FEATURE_NAME> S9` を記録する。未完了の `[人]` のタスクはギャップに数えない。

> 💬 ギャップの解消方針や仕様との乖離について判断が必要な場合は、ユーザーに質問する。

### S9-1: バランス検証（gamekit-balance の verify）

[`gamekit-balance`](../gamekit-balance/SKILL.md) の verify モードの手順に従う。要点は次のとおりである。

1. `$BAL run --feature <FEATURE_NAME>` でシミュレーションを回し、`$BAL check --feature <FEATURE_NAME> --report specs/<FEATURE_NAME>/balance-report.md` で目標値と突き合わせる。
2. FAIL があれば、`tuning.md` の範囲の中でマスタデータを調整して直し、もう一度回す。範囲の外に出る、または目標値を変える必要があるときは、ユーザーに確かめる（自動モードでは止まる）。直した調整値は `tuning.md` の初期値にも反映する。
3. 基準値（`docs/balance/baseline/`）があれば `$BAL diff` で、この機能が既存の指標を動かしていないかを確かめ、動いた指標と理由を `balance-report.md` に書く。
4. シミュレーションの対象にならない機能、または `commands.balance_sim` がまだない（`PRECONDITION: NO_SIM_COMMAND`）ときは、`balance-report.md` に「シミュレーション対象外」とその理由、代わりに確かめたこと（テストでの検算など）を書く。
5. `checkpoint <FEATURE_NAME> S9-1` を記録する。

> 💬 調整の方針（どの値を動かすか）や、目標値の見直しに判断が必要な場合は、推奨案を添えてユーザーに質問する。

### S10: 5 軸レビュー 1 回目と修正（gamekit-review）

[`gamekit-review`](../gamekit-review/SKILL.md) スキルの手順に従い、5 軸（Standards・Spec・Balance・Feel・Originality）のレビューを行う。

1. レビュー対象の差分として `git diff main...HEAD` を取得する（マージ先が main 以外なら、その名前に読み替える。以下同じ）。
2. 5 軸でレビューし、記録を `FEATURE_DIR/reviews/review-1.md` に書く。可能なら、軸ごとに文脈を持たないサブエージェントで独立にレビューし、親が指摘の裏を取ってから採否を決める（`gamekit-review` §4）。
3. CRITICAL、HIGH、MEDIUM の指摘を直し、テストとヘッドレス実行が通ること、バランスの指摘を直したなら `$BAL check --feature <FEATURE_NAME>` が通ることを確かめる。体感の判定が要る Feel 軸の指摘は、`[人]` のプレイ確認のタスクの観点に足す。
4. `checkpoint <FEATURE_NAME> S10` を記録する。

> 💬 指摘への対応方針（リファクタリングの方針や優先度）に判断が必要な場合は、推奨案を添えて質問し、合意を取る。

### S11: 再レビューと修正（gamekit-review）

S10 の修正が既存のロジックや数値を壊していないか、新たな不整合やエッジケースの抜けがないかを確かめるため、2 回目のレビューを行う。

1. S10 の修正差分（`git diff HEAD~1`）と全体の差分（`git diff main...HEAD`）を対象に、もう一度 `gamekit-review` を実行し、記録を `FEATURE_DIR/reviews/review-2.md` に書く。1 回目と違うレンズ（`gamekit-review` §4 の「2 回目」）で見る。
2. 二次的な不整合、型の甘さ、考慮されていないエッジケース、テストの網羅性、バランスの退行を最終確認する。
3. 残っている指摘を直し、テストがすべて通ることを確かめる。修正がなくても次へ進む。
4. `checkpoint <FEATURE_NAME> S11` を記録する。

> 💬 残っている指摘への対応の要否について確認が必要な場合は、ユーザーに質問する。

## 4. 完了報告

各フィーチャーの完了時と、指定範囲の全体の完了時に、次を報告する。

- 完了したフィーチャー名と番号、マージコミット
- 実装の要約とテスト結果（ヘッドレス実行を含む）
- converge の検証結果（追加したタスクがあればその内容）
- バランス検証の結果（PASS / FAIL / MISSING の件数、調整した値、基準値からの変化）
- レビュー 2 回で見つかって直した指摘（軸ごと）と、採らなかった指摘とその理由
- 残っている `[人]` のタスク（`finish` の `HUMAN_TASKS_PENDING`。プレイ確認など）と、片付けた後の手順（`gamekit-worktree` §3「人のタスクの片付け」）
- 飛ばした、または中断したフィーチャーとその理由
- `--auto` のとき: 自動で採用した判断の要約（`auto-decisions.md`）と、止まったフィーチャーについてユーザーに判断してほしい事項
- 次の案内: `$HELPER next --phase coding` の結果（実装が未完了のフィーチャー）。プレイ確認が残っていれば、その記録の置き場（`docs/playtest/`）
