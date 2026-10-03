---
name: "gamekit-worktree"
description: "gamekit-feature・gamekit-coding・gamekit-all が共通で使う worktree 管理スキル。フィーチャーごとの Git worktree とブランチの準備（既存があれば再利用）、ステップ完了ごとの進捗コミット、main への --no-ff マージと片付け、中止、進捗の確認を行う。3 スキル共通の実行規則（ステップ番号、再開、安全規則、対話、引数の解釈、自動モード --auto）もここに定める。「フィーチャーの進捗を見せて」「worktree を破棄して」と言われたとき、または /gamekit-worktree と打たれたときにも使う。"
argument-hint: "status | next --phase spec|coding|all | human-tasks [<フィーチャー>] | deferred-tasks [<フィーチャー>] | sync-status <フィーチャー> | abort <フィーチャー>"
compatibility: "Requires git and Python 3.9+, spec-kit project structure with .specify/ directory"
user-invocable: true
disable-model-invocation: false
---

# gamekit-worktree スキル（worktree 管理と共通実行規則）

`gamekit-feature`（仕様工程）、`gamekit-coding`（実装工程）、`gamekit-all`（通し）の 3 スキルが共通で使う。フィーチャーの作業はすべて `.worktrees/<FEATURE_NAME>`（ブランチ `feature/<FEATURE_NAME>`）で行い、ステップが終わるたびにコミットして進捗を記録する。中断しても、どのスキルからでも続きのステップから再開できる。

Claude Code、Codex CLI、Antigravity、Kiro CLI、opencode のいずれでも同じ手順で動く。

## 1. ヘルパースクリプト

```bash
python3 <skills>/gamekit-worktree/scripts/worktree_helper.py <command> ...
```

以降、この呼び出しを `$HELPER` と書く。

- `<skills>` は、このスキルが置かれた skills ディレクトリ（`.claude/skills`、`.agents/skills`、`.kiro/skills` のいずれか）である。
- スクリプトは Python 3.9 以上の標準ライブラリだけで書かれており、macOS、Linux、Windows で動く。プロジェクトのルートからでも worktree の中からでも実行できる。
- `python3` がない環境（Windows など）では、`python` または `py -3` に読み替える。
- マージ先のブランチ（この文書の `main`）は、環境変数 `GAMEKIT_MAIN_BRANCH`（なければ speckit と共通の `SPECKIT_MAIN_BRANCH`）があればその名前、なければ `main` である。Claude Code のクラウドセッション（`CLAUDE_CODE_REMOTE=true`）では、`GAMEKIT_MAIN_BRANCH` も `SPECKIT_MAIN_BRANCH` もなければ、メインの作業ツリーの今のブランチ（セッションの作業ブランチ）をマージ先にする。`finish` はマージの後に、そのブランチを origin に push する。出力は `PUSHED`、`PUSH_SKIPPED`、`PUSH_FAILED` のいずれかである。`PUSH_FAILED` のときも、マージは済んでいる。規則はプロジェクトの steering（「Claude Code のクラウドセッション」）に従う。

| コマンド | 用途 |
|---|---|
| `$HELPER ensure <feature> --phase spec\|coding\|all [--weight 軽\|標準\|重]` | S1 準備。worktree があれば再利用し、なければ `main` から作る。機能の重さ（`WEIGHT`）も出す（§2「機能の重さ」） |
| `$HELPER state <feature> --phase spec\|coding\|all [--weight 軽\|標準\|重]` | 変更せずに進捗と機能の重さを表示する |
| `$HELPER checkpoint <feature> <step> "<subject>" [--skipped "<理由>" [--force]]` | worktree の変更をすべてコミットし、ステップの完了を記録する。`--skipped` は、機能の重さで省いたステップとして記録する（trailer `Gamekit-Skipped`。完了として数える。重さで省けないステップは止まり、`--force` でだけ通す） |
| `$HELPER finish <feature> --phase spec\|coding\|all [--allow-unchecked] [--commit-leftovers] [--switch] [--partial]` | S12 片付け。`main` に `--no-ff` でマージし、worktree とブランチを削除する。worktree の外で実行する。`--partial`（coding / all）は、最終ステップと未完了のタスクを確かめずに `merge(<feature>): partial` の件名でマージする（ほかの機能の前提として一部の Phase だけを先に入れるとき。進捗は進めない） |
| `$HELPER ensure\|state <feature> --phase deferred [--tasks T045,T046]` | 実装まで `main` にマージ済みの機能の、後の段階のタスク（`[後]`）を片付ける worktree（`.worktrees/<feature>-deferred`、ブランチ `feature/<feature>-deferred`）を作る・再開する。`--tasks` を省くと未完了の `[後]` をすべて対象にする。出力に `DEFERRED_TARGETS`・`RUN`・`NEXT_STEP`（S8・S9・S9-1・S10・S11）。`[後]` がなければ `NO_DEFERRED_TASKS`、実装が未マージなら `NOT_IMPLEMENTED` で止まる（§3「後の段階のタスク」） |
| `$HELPER checkpoint <feature> <step> "<subject>" --phase deferred [--skipped "<理由>"]` | 後の段階の作業のステップを記録する（trailer `Gamekit-Deferred-Step`・`Gamekit-Deferred-Run`。もとの機能の進捗〈`Speckit-Step`〉は変えない）。S9-1・S11 は重さに関わらず `--skipped` で省ける |
| `$HELPER finish <feature> --phase deferred [--commit-leftovers] [--switch]` | 対象のタスクが `- [x]` であることを確かめ（未完了なら `DEFERRED_TARGETS_UNCHECKED`）、`merge(<feature>): deferred` の件名で `main` にマージする（進捗の判定には使わない）。機能ファイルの状態を残りの `[人]`・`[後]` に合わせる。対象外の未完了のタスクでは止めない |
| `$HELPER abort <feature> [--phase deferred] [--yes]` | worktree とブランチを破棄する（`--phase deferred` で後の段階の作業のもの）。`--yes` がなければ対象を表示するだけ |
| `$HELPER list` | 全フィーチャー名を着手順（`spec_order.md` の並び、その後に番号順）で表示する |
| `$HELPER status` | 全フィーチャーの仕様・実装・worktree の状況と、残っている人のタスク（`[人]`）の件数を表示する。Pull Request などで取り込んだフィーチャーは `main` の `tasks.md` の完了状況で、Spec Kit 以前に実装した機能（`specs/` がなく、機能ファイルの状態欄が `実装済み` か `完了`）は状態欄で判定する。worktree を使わずに `NNN-slug` のブランチで作業中のフィーチャーも表示する（この 2 種類は `next` の候補にしない） |
| `$HELPER deferred-tasks [<feature>]` | 残っている後の段階のタスク（`[後]`）を一覧する。読む `tasks.md` は `human-tasks` と同じ |
| `$HELPER human-tasks [<feature>]` | 残っている人のタスクを一覧する。worktree があればその `tasks.md`、なければ `main` のもの（メインの作業ツリーが `main` にいれば、コミット前の変更も含む）を読む |
| `$HELPER sync-status <feature>` | `main` にマージ済みのフィーチャーの状態欄を、`tasks.md` に合わせて `完了` か `人の作業待ち` にする。`main` で実行し、変更はコミットしない |
| `$HELPER next --phase spec\|coding\|all [--skip <feature,...>]` | 次に着手すべきフィーチャーを表示する（途中の worktree を優先。`--skip` で除外） |
| `$HELPER resolve <query>` | 番号やスラッグからフィーチャー名を決める |

`ensure` と `state` は次の形で結果を出力する。

```text
REPO_ROOT: /path/to/repo
FEATURE_NAME: 001-todo-cli
BRANCH: feature/001-todo-cli
WORKTREE_DIR: /path/to/repo/.worktrees/001-todo-cli
WORKTREE_STATE: created | reused | reattached | present | absent
PHASE: spec
COMPLETED_STEPS: S2 S3
NEXT_STEP: S4
MISSING_ARTIFACTS: ui.md tuning.md
```

`MISSING_ARTIFACTS` は、`--phase coding` か `all` で仕様工程（S7-3）が済んでいるのに、`specs/<FEATURE_NAME>/` に `ui.md`・`tuning.md` がないときだけ出る（Spec Kit で仕様化してから取り込んだ機能など）。欠けがなければ、この行は出ない。

終了コードは、0 が成功、1 がエラー、3 が前提条件を満たさないことを表す。3 のときは標準エラーに `PRECONDITION: <code>` と案内文が出る。

| code | 意味 | 対応 |
|---|---|---|
| `ALREADY_SPECIFIED` | 仕様はすでに `main` にマージ済み | `gamekit-coding` を案内する |
| `ALREADY_IMPLEMENTED` | `main` の `tasks.md` がすべて完了済み | そのフィーチャーは完了として扱う |
| `CODING_IN_PROGRESS` | worktree がすでに実装工程に入っている | `gamekit-coding` か `gamekit-all` での再開を案内する |
| `SPEC_INCOMPLETE` | worktree の仕様工程が途中 | `gamekit-feature` か `gamekit-all` での再開を案内する |
| `SPEC_MISSING` | spec・plan・tasks がどこにもない | `gamekit-feature` か `gamekit-all` を案内する |
| `LEFTOVER_CHANGES` | `finish` で、worktree にどのステップのコミットにも含まれていない変更がある | 変更の一覧をユーザーに示す。マージに含めてよければ `--commit-leftovers` を付けて再実行する。含めない変更は、ユーザーの了承を得て取り除く |
| `NOT_ON_MAIN` | `finish` で、メインの作業ツリーが `main` 以外のブランチにいる | 切り替えてよいかをユーザーに確認し、よければ `--switch` を付けて再実行する |
| `UNCHECKED_TASKS` | `finish`（coding / all）で、`tasks.md` に `[人]`・`[後]` 以外の未完了のタスクが残っている | 未完了のタスクの一覧をユーザーに示す。実装するなら S8 の手順で片付けてから、残したままマージしてよいと確認できたら `--allow-unchecked` を付けて `finish` を再実行する |

`finish`（coding / all）は、未完了のタスクが `[人]`・`[後]` のものだけなら止めずにマージし、標準出力に `HUMAN_TASKS_PENDING: <件数>`・`DEFERRED_TASKS_PENDING: <件数>` と残りのタスクを出す。この一覧はユーザーに示し、§3「人のタスクの片付け」「後の段階のタスク」を案内する。

## 2. ステップ番号

ステップ番号は 3 スキルで共通の通し番号であり、進捗の記録と再開の判定に使う。

| ステップ | 内容 | 担当スキル | チェックポイントの subject |
|---|---|---|---|
| S1 | 準備（`ensure`） | 3 スキル共通 | （コミットなし） |
| S2 | specify（仕様作成） | gamekit-feature | `docs(<FEATURE_NAME>): 仕様を作成` |
| S3 | clarify 1 回目 | gamekit-feature | `docs(<FEATURE_NAME>): 仕様を明確化（1 回目）` |
| S4 | clarify 2 回目 | gamekit-feature | `docs(<FEATURE_NAME>): 仕様を明確化（2 回目）` |
| S4-1 | 画面と HUD の仕様（`gamekit-design` §3） | gamekit-feature | `docs(<FEATURE_NAME>): 画面仕様を作成` |
| S4-2 | 調整仕様（`gamekit-balance` の spec） | gamekit-feature | `docs(<FEATURE_NAME>): 調整仕様を作成` |
| S5 | plan（詳細設計） | gamekit-feature | `docs(<FEATURE_NAME>): 詳細設計を作成` |
| S6 | tasks（タスク分解） | gamekit-feature | `docs(<FEATURE_NAME>): タスクを分解` |
| S7-1 | analyze 1 回目 | gamekit-feature | `docs(<FEATURE_NAME>): 整合性を検証（1 回目）` |
| S7-2 | analyze 2 回目 | gamekit-feature | `docs(<FEATURE_NAME>): 整合性を検証（2 回目）` |
| S7-3 | analyze 3 回目 | gamekit-feature | `docs(<FEATURE_NAME>): 整合性を検証（3 回目）` |
| S8 | implement（実装） | gamekit-coding | `feat(<FEATURE_NAME>): タスクを実装` |
| S9 | converge（収束） | gamekit-coding | `feat(<FEATURE_NAME>): 実装を仕様に収束` |
| S9-1 | バランス検証（`gamekit-balance` の verify） | gamekit-coding | `fix(<FEATURE_NAME>): バランスを検証` |
| S10 | レビュー 1 回目と修正 | gamekit-coding | `fix(<FEATURE_NAME>): レビューの指摘を修正（1 回目）` |
| S11 | レビュー 2 回目と修正 | gamekit-coding | `fix(<FEATURE_NAME>): レビューの指摘を修正（2 回目）` |
| S12 | 片付け（`finish`） | 3 スキル共通 | `merge(<FEATURE_NAME>): <phase>`（自動。進捗の判定に使うため、この形は変えない） |

**後の段階の作業（`--phase deferred`）**: 実装まで `main` にマージ済みの機能の `[後]` のタスクを片付けるときは、S8・S9・S9-1・S10・S11 を同じ名前で使い、trailer `Gamekit-Deferred-Step: <step>` と `Gamekit-Deferred-Run: <回>` で記録する（`Speckit-Step` は使わないので、もとの機能の進捗は変わらない）。S1 は `ensure --phase deferred`、S12 は `finish --phase deferred`（件名 `merge(<FEATURE_NAME>): deferred`）。S9-1 と S11 は重さに関わらず省ける（§3「後の段階のタスク」）。

S4-1、S4-2、S9-1 は、speckit の番号を変えないように枝番で差し込んだステップである。speckit で作業を始め、これらの記録なしに後のステップへ進んだ worktree では、差し込んだステップは完了済みとみなされる（済んだ工程に戻らない。speckit から gamekit に取り込んだプロジェクトも同じ）。trailer（`Speckit-Step`、`Speckit-Feature`）は speckit と共通である。

画面のない機能・調整値のない機能の S4-1・S4-2 は、機能の重さで扱いが変わる（下の「機能の重さ」）。重の機能では飛ばさず、`ui.md` を「UI なし」、`tuning.md` を「調整値なし」として記録する。軽・標準の機能では、該当しなければ `--skipped` で省いてよい（ファイルは作らない）。シミュレーションの対象にならない機能でも S9-1 は飛ばさず、`balance-report.md` に「シミュレーション対象外」と理由を書いて記録する。

### 機能の重さ

機能ファイル（`docs/feature/<FEATURE_NAME>.md`）のヘッダの `**重さ**`（`軽` / `標準` / `重`）で、工程の重さを変える。判定の規則は `gamekit-features` の「重さ」（重 = 保存形式・調整値と目標値・柱に効く規則のどれかに触れる。軽 = 画面だけ・文言だけ・設定だけ。標準 = それ以外）。`ensure` と `state` が `WEIGHT:` で出す（欄がなければ `標準`）。ユーザーは各スキルの引数 `--weight 軽|標準|重` で上書きできる（`$HELPER` にも同じ指定を渡す）。

| 工程 | 軽 | 標準 | 重 |
|---|---|---|---|
| 質問の窓（`gamekit-feature` の「質問の窓」） | 1 つ（S2 の前） | 2 つ（S2 の前、S5 の前） | 2 つ |
| clarify（S3・S4） | 1 回、最大 3 問（S4 は省く） | 2 回 | 2 回 |
| 画面仕様・調整仕様（S4-1・S4-2） | 該当するときだけ（しないなら省く） | 該当するときだけ | 必ず（該当しなければ「UI なし」「調整値なし」と書く） |
| analyze（S7） | 1 回（S7-2・S7-3 は省く） | 2 回（S7-3 は省く） | 3 回 |
| レビュー（S10・S11） | 1 回、関係する軸だけ（S11 は省く） | 2 回。2 回目は修正の差分だけ | 2 回、5 軸 |

- 省くステップは、本体を行わずに `$HELPER checkpoint <FEATURE_NAME> <step> "<subject>" --skipped "<重さ>: <理由>"` で記録する（例: `--skipped "軽: clarify は 1 回"`）。完了として数えるので、再開と `finish` の判定は崩れない。`status` には「（省略: S4 S7-2）」のように出る。
- 省けるステップは、軽が S4・S4-1・S4-2・S7-2・S7-3・S11、標準が S4-1・S4-2・S7-3、重はなし。表の外のステップを省こうとすると `$HELPER` が止まる。理由を確かめたうえで `--force` を付けたときだけ通す（自動モードでは付けない）。
- 仕様化の途中で重さの条件に当たるもの（調整値、保存形式、柱に効く規則）が出てきたら、機能ファイルの重さを上げて、以降の工程を重い方に合わせる。下げるときはユーザーに確かめる。
- レビューの打ち切り（2 回目で CRITICAL・HIGH が 0 件なら終える）と軸の選び方は `gamekit-review` の「予算と打ち切り」に従う。

`checkpoint` はコミットに trailer `Speckit-Step: <step>` と `Speckit-Feature: <FEATURE_NAME>` を付ける。変更がないステップも空コミットで記録する。進捗は、`main` とブランチにあるこの trailer、`main` にマージ済みの `tasks.md`、`merge(<FEATURE_NAME>): coding|all` のマージコミットから判定する。フィーチャー名付きの trailer はマージの後も残るので、競合を手で解消してマージした後に `finish` を再実行しても進捗は失われない。

`checkpoint` は、機能ファイル（`docs/feature/<FEATURE_NAME>.md`）があれば、その状態欄と `docs/feature/README.md` の一覧の状態列も更新する。S2 で `spec化済み（specs/<FEATURE_NAME>）`、S11 で `完了` にする。S11 の時点で `tasks.md` に未完了の `[人]` のタスクが残っていれば、`完了` ではなく `人の作業待ち（specs/<FEATURE_NAME>）` にする。機能ファイルを手で書き換える必要はない。

## 3. 共通手順

### S1 準備

1. `$HELPER ensure <feature> --phase <phase>` を実行する。`<phase>` は、gamekit-feature が `spec`、gamekit-coding が `coding`、gamekit-all が `all` である。
2. 終了コードが 3 のときは、§1 の表に従って案内し、そのフィーチャーの作業を止める。
3. 出力から `FEATURE_NAME`、`WORKTREE_DIR`、`NEXT_STEP`、`WEIGHT` を控える。機能ファイルに `**重さ**` がなければ（`WEIGHT` が既定の `標準` のとき、ヘッダを確かめる）、`gamekit-features` の「重さ」の規則で判定して書き足し、trailer なしの通常のコミットにする。以降の工程は §2「機能の重さ」の表に従う。
4. `WORKTREE_STATE` が `reused` か `reattached` のときは、`COMPLETED_STEPS` と `NEXT_STEP` をユーザーに示し、`NEXT_STEP` から再開してよいか確認する。ユーザーが別のステップからのやり直しを指示した場合は、そのステップから進める（完了済みの記録は残したまま、成果物を更新する）。
5. `MISSING_ARTIFACTS` があれば、S8 の前に作る。ui.md は `gamekit-design` §3、tuning.md は `gamekit-balance` の spec モードで作る。作ったら trailer なしの通常のコミットにする（S4-1・S4-2 は推定で済んだ扱いのまま。`checkpoint` は記録しない）。
6. `NEXT_STEP` が自分の担当範囲の最後より後（`S12`）なら、本体のステップを飛ばして S12 に進む。

### 各ステップの作業場所

- 以降の作業は、すべて `WORKTREE_DIR` の中で行う。コマンドは `cd "$WORKTREE_DIR"` してから実行し、ファイルは `WORKTREE_DIR` 配下のパスで読み書きする。
- `WORKTREE_DIR/.specify/feature.json` は `ensure` が `specs/<FEATURE_NAME>` を指すように書いている。speckit の各スキルやスクリプトは、この値を対象フィーチャーとして使う。
- 1 つのステップが終わったら、そのステップのチェックポイントを必ず記録する。

  ```bash
  $HELPER checkpoint <FEATURE_NAME> <step> "<§2 の subject>"
  ```

- 長いステップ（特に S8）の途中では、trailer なしの通常のコミットを作ってよい。完了の記録はステップの最後の `checkpoint` だけで行う。

### S12 片付け

1. **worktree の外に出てから**、`$HELPER finish <FEATURE_NAME> --phase <phase>` を実行する（`cd "$REPO_ROOT"`。`REPO_ROOT` は `ensure` の出力にある）。worktree の中で実行すると、スクリプトは止まる。スクリプトは次を行う。
   - 担当範囲の最終ステップ（spec は S7-3、coding と all は S11）が完了していることを確かめる。
   - coding と all では、`tasks.md` に未完了のタスクがないことを確かめる（`[人]`・`[後]` 以外があれば `UNCHECKED_TASKS` で止まる。`[人]`・`[後]` だけなら続けて、最後に `HUMAN_TASKS_PENDING`・`DEFERRED_TASKS_PENDING` を出す）。
   - worktree の残りの変更をコミットする。
   - メインの作業ツリーに未コミットの変更がないことを確かめ、`main` に切り替える。
   - `git merge --no-ff -m "merge(<FEATURE_NAME>): <phase>"` でマージする。ブランチがすでにマージ済み（競合を手で解消した後など）なら、マージを飛ばして片付けだけを行う。
   - worktree とブランチを削除する。worktree にあった無視対象のファイル（`.env` など）も一緒に消えるので、出力の `REMOVED_IGNORED` に挙がったものはユーザーに知らせる。
   - クラウドセッションでは、マージ先のブランチを origin に push する（`PUSHED` など）。`PUSH_FAILED` なら、その内容をユーザーに伝える。
2. `--phase coding` と `--phase all` で、マージが済んだら（`finish` が成功したら）、メインの作業ツリー（`main`）で引き継ぎ書を更新してコミットする。trailer は付けない。

   ```bash
   python3 <skills>/gamekit-status/scripts/gamekit.py handover --note "<FEATURE_NAME> を完了"
   git add docs/handover && git commit -m "docs(handover): 引き継ぎ書を更新"
   ```

   クラウドセッションでは、コミットの後に作業ブランチを push する。`--phase spec` では更新しない（実装が終わってから更新する）。
3. マージで競合したときは、worktree とブランチが残る。競合の内容をユーザーに示し、解消方針を確認してから、メインの作業ツリーで解消してマージをコミットし、もう一度 `finish` を実行する。マージコミットのメッセージは `merge(<FEATURE_NAME>): <phase>` のままにする。

### 人のタスクの片付け

`[人]` のタスクは、マージの後に `main` で片付けてよい。規則はプロジェクトの steering（「人が行うタスク」）に従う。

1. `$HELPER human-tasks <FEATURE_NAME>` で残りを示す。
2. ユーザーが完了を伝えたら、そのタスクの「完了の確かめ方」で確かめられる部分を確かめ、`main` の `tasks.md` を `- [x]` にする。
3. `$HELPER sync-status <FEATURE_NAME>` で状態欄を合わせる。人のタスクがなくなれば `完了` になる。
4. `tasks.md` と機能ファイル、`docs/feature/README.md` の変更をまとめてコミットする（例: `docs(<FEATURE_NAME>): 人のタスクの完了を記録`）。

### 後の段階のタスク

`[後]` のタスクは、マージの後、その段階（「いつ: …」に書いたもの）が来たら片付ける。規則はプロジェクトの steering（「後の段階に回すタスク」）に従う。

1. `$HELPER deferred-tasks [<FEATURE_NAME>]` で残りを示す。
2. その段階が来たら `gamekit-coding <FEATURE_NAME> --deferred [T045,T046]` で片付ける（`gamekit-coding` §1「後の段階のタスク」）。実装までマージ済みの機能は `--phase coding` では `ALREADY_IMPLEMENTED` で止まるので、`--phase deferred` の専用の worktree で行う。
   - S1: `$HELPER ensure <FEATURE_NAME> --phase deferred [--tasks T045,T046]`（新しい worktree `.worktrees/<FEATURE_NAME>-deferred`。始めのコミットに対象と回の番号を記録する。worktree が残っていれば続きから）
   - S8〜S11: 対象のタスクだけを、S8 → S9 → S9-1 → S10 → S11 の順で行い、`checkpoint ... --phase deferred` で記録する（`Gamekit-Deferred-Step`。もとの機能の `Speckit-Step` の進捗は変えない）
   - S12: worktree の外で `$HELPER finish <FEATURE_NAME> --phase deferred`（件名 `merge(<FEATURE_NAME>): deferred`。対象が `- [x]` でなければ止まる。機能ファイルの状態も合わせるので `sync-status` は要らない）
3. **印の扱い**: 実装したタスクは `- [x]` にし、`[後]` の印は残す（いつ後回しにしたかの記録として。`[後]` の数え方は未完了のものだけなので、残しても数に入らない）。
4. **打ち切り**: 後の段階の作業は差分が小さいことが多いので、機能の重さに関わらず次のステップを省いてよい（`--skipped` で記録する）。S9-1 は、対象のタスクがその機能の調整値・目標値（`tuning.md`）に関わらないとき。S11 は、S10 で CRITICAL・HIGH が 0 件だったとき。S8・S9・S10 は省けない。

### 一部だけを先にマージする（`--partial`）

ほかの機能の前提として、この機能の一部の Phase だけを先に `main` に入れるときに使う（steering「ほかの機能の一部だけを先に作る」）。

1. `gamekit-coding <FEATURE_NAME> --until "Phase N"` で、`tasks.md` のその Phase までを実装し、テストとゲートを通す。S8 の `checkpoint` は記録しない（S8 はまだ終わっていない）。区切りのコミットは trailer なしで作る。
2. worktree の外で `$HELPER finish <FEATURE_NAME> --phase coding --partial` を実行する。件名は `merge(<FEATURE_NAME>): partial` で、進捗の判定には使わない。
3. 残りは、後で `gamekit-coding <FEATURE_NAME>` を実行すれば、`main` から新しい worktree を作って S8 から続ける（済んだタスクは `- [x]` のまま）。

### 中止

`$HELPER abort <FEATURE_NAME>` で削除対象を表示し、ユーザーの明示的な同意を得てから `--yes` を付けて実行する。ユーザーの指示なしに中止してはならない。

## 4. 共通規則

- **対話的な確認**: 仕様の曖昧さ、設計判断、実装方針の分岐、レビュー指摘の修正方針など、ユーザーの判断が必要な事項は、推奨案（`**Recommended:**`）を添えて質問し、合意を得てから進める。引数に `--auto` があるときは、質問せずに §6 の自動モードで進める（各スキル本文の 💬 の質問と、標準スキルの確認も含む）。
- **破壊的コマンドの禁止**: `rm -rf`、`git reset --hard`、`git clean -f`、`git push --force` などの破壊的コマンドは使わない。worktree とブランチの操作は `$HELPER` だけで行う。
- **言語**: 応答と成果物は、プロジェクトの言語ルール（`.kiro/steering/language.md` など）に従う。ルールがない場合も日本語で書く。
- **テスト・ビルド・リンター・ヘッドレス実行**: 実行するコマンドは、`.gamekit/config.yaml` の `commands`（`python3 <skills>/gamekit-status/scripts/gamekit.py config get commands.test` などで読む）を正とする。空なら `plan.md` の技術コンテキスト、`quickstart.md`、プロジェクトの設定ファイル（`project.godot`、`package.json`、`Makefile` など）から判断する。判断できない場合はユーザーに確認する。
- **エンジンのエディタ**: エディタでしかできない操作（シーンの配置、インポートの設定など）は、テキストのシーン・リソースファイルを直接書くか、手順を示して `[人]` のタスクにする（steering の「エージェントの行動規範」）。
- **コマンドの書き方**: speckit のスキル本文にある `$speckit-plan` のようなコマンド参照は、実行中のエージェントの呼び出し方に読み替える。
- **質問はまとめる**: 仕様工程の質問は `gamekit-feature` の「質問の窓」に、実装工程で決めたことは `FEATURE_DIR/decisions.md` に集め、S8 の終わりに 1 回で確かめる（`gamekit-coding` の S8）。窓の外で止めてよいのは、窓まで待つと作業が無駄になる前提の誤りだけである。

### 親と担当の役割

サブエージェント（Claude Code の Agent など）が使えるときは、実行中のエージェント（親）は指揮と裏取りに回り、量の多い作業を担当（サブエージェント）に任せる。1 人で全部を抱えると文脈が足りなくなる。依頼文の雛形は [references/delegation.md](references/delegation.md) にある。

| 役割 | 親が持つ | 担当に任せる |
|---|---|---|
| ユーザーとのやりとり | 質問（質問の窓、`decisions.md` の確認）、採否の判断、完了報告 | — |
| 進捗と git | `checkpoint`、`finish`（マージ）、push、`--skipped` の判断 | 区切りの通常のコミット（trailer なし） |
| 作業 | 仕様工程の成果物（S2〜S7。量が多ければ下書きを任せてよい） | S8（Phase ごとに分ける）、S9、S9-1 の調整、軸ごとのレビュー（`gamekit-review`）、指摘の修正 |
| 検証 | 担当の報告の後に、テスト・ゲート・`balance.py check` などを自分で再実行する | 自分の作業の範囲の検証 |

- 担当にさせないこと: `checkpoint`、マージ、push、ユーザーへの質問、ほかの担当の範囲の編集、破壊的な git の操作。担当が判断に迷ったら、推奨案で進めて `decisions.md` に書かせ、親がまとめて確かめる。
- 並行に走らせるのは、ファイルが重ならない作業だけにする（レビューの軸どうしは並行してよい。S8 の Phase は依存があるので順に）。
- サブエージェントがない環境では、親が同じ順で自分で行う。役割の区切り（報告の形、検証の再実行）は同じにする。

### 文脈の節約

- 親は差分そのものを読まず、担当の報告（件数、決めたこと、検証の結果）と、自分で再実行した検証の結果を見る。報告に疑問があるときだけ、該当するファイルの行を開いて裏を取る。
- 大きなステップ（とくに S8）は Phase の境目でコミットさせ、次の担当には「前の担当のコミット」と「決めたことの台帳」だけを渡す。
- 会話が長くなったら、ステップの境目で `python3 <skills>/gamekit-status/scripts/gamekit.py handover --note "<止めた理由と次の作業>"` を実行して区切り、新しいセッションで同じスキルを実行して再開する。

## 5. 引数の解釈と複数フィーチャーの進め方

| 指定 | 例 | 動作 |
|---|---|---|
| 単一 | `1`、`002`、`002-auth`、`auth` | `$HELPER resolve` で 1 件に決める |
| 範囲 | `002-005`、`002..005` | `$HELPER list` の結果から番号が範囲内のものを番号順に選ぶ |
| 全件 | `all` | `$HELPER next --phase <phase>` を、空になるまで繰り返す |
| なし | （空） | `$HELPER next --phase <phase>` の 1 件。空なら対象なしと報告する |
| 自動モード | `--auto`、`002-005 --auto`、`--auto all` | 上のいずれかと組み合わせる。質問せずに推奨案を採用して進める（§6） |
| モックを作る | `--with-mock`、`002 --with-mock --auto` | 上のいずれかと組み合わせる。S4-1 で、Claude Design のモックを作って案を選ぶ（`gamekit-design` のモックの節）。付けなければテキストの画面仕様だけを作る |
| 後の段階のタスク | `000 --deferred`、`000 --deferred T045,T046` | `gamekit-coding` だけで使う。実装までマージ済みの機能の `[後]` のタスクを `--phase deferred` で片付ける（§3「後の段階のタスク」）。単一のフィーチャーの指定とだけ組み合わせる |
| 重さを上書きする | `--weight 軽`、`003 --weight 重 --auto` | 上のいずれかと組み合わせる。機能ファイルの `**重さ**` の代わりに使う（§2「機能の重さ」） |

- `--auto` と `--with-mock` は位置を問わない。フィーチャーの指定を解釈する前に取り除き、`$HELPER` には渡さない。`--weight <重さ>` も位置を問わず、`$HELPER` の `ensure`・`state`・`checkpoint` にはそのまま渡す。
- 一覧にない新しいフィーチャーは、`001-short-name` の形の完全名で指定する。
- 複数のフィーチャーは 1 件ずつ直列に進める。前のフィーチャーの S12（マージ）が終わってから、次のフィーチャーの S1 に進む。後続のフィーチャーは、先行フィーチャーの成果を含む最新の `main` から分岐する。
- 範囲指定の途中で `ALREADY_SPECIFIED` や `ALREADY_IMPLEMENTED` になったフィーチャーは、飛ばしたことを記録して次に進む。それ以外の理由で止まったときは、飛ばして続けるか中断するかをユーザーに確認する（自動モードでは確認せずに飛ばす。§6「止まったときの扱い」）。
- `all` で飛ばしたフィーチャーは、以降の `next` に `--skip <飛ばしたもの,...>` を付けて除く（付けないと、途中の worktree が残っているフィーチャーがまた選ばれる）。

## 6. 自動モード（`--auto`）

引数に `--auto` があるときは、ユーザーに質問せず、エージェント自身が示す推奨案を採用して進める。範囲指定や `all` と組み合わせて、無人で続けて流す使い方を想定する。

仕様駆動開発の「曖昧さを推測で埋めない」に反しないよう、自動で決めたことはすべて推奨案として明示し、後から見直せる形で記録する（下の「記録」）。安全規則（§4 の破壊的コマンドの禁止など）は、自動モードでも変わらない。

### 推奨案を自動で採用する場面

| 場面 | 自動モードでの動作 |
|---|---|
| S1 の再開確認（`WORKTREE_STATE` が `reused` / `reattached`） | `NEXT_STEP` から再開する |
| S2〜S4 の前提条件・スコープの疑問、clarify の質問 | 推奨案（`**Recommended:**`）を回答として採用する。推奨案を 1 つに絞れない論点は、範囲が狭く後から広げやすい選択肢を採る |
| S4-1 の画面の構成、`--with-mock` の案の選択 | 推奨案を採用する（`gamekit-design` の自動モード）。既存のトークンや共通の決め事を変える必要があるときは止まる |
| S4-2 の調整値の初期値と範囲、目標値（BT）の追加 | `docs/game/` の式と既存の目標値から推奨値を採る。既存の目標値を変える必要があるときは止まる |
| S9-1 の FAIL の直し方 | マスタデータの調整で直す（`tuning.md` の範囲の中で）。範囲の外に出る、または目標値そのものを変える必要があるときは止まる |
| S10〜S11 の Feel 軸の指摘 | コードと演出で直せるものは直す。体感の判定が要るものは `[人]` のプレイ確認に回す |
| S5 のアーキテクチャのトレードオフ、ライブラリ・アドオンの選定 | 推奨案を採用し、`research.md` に Decision・Rationale・Alternatives considered を残す。`docs/architecture.md` と `docs/nfr.md` から外れる選択はしない |
| S7 の修正方針、`speckit-analyze` の「修正案を示しますか」 | 「はい」とみなし、推奨の修正を当てる |
| S8 の `speckit-implement` の「チェックリストに未完了の項目があるが続けるか」 | 続行する。未完了の項目を完了報告に挙げる |
| S8〜S11 の実装方針の分岐、ギャップの解消方針、レビュー指摘の対応方針 | 推奨案を採用する。仕様を変える場合は、コードだけでなく `spec.md`、`plan.md`、`tasks.md` にも反映する |
| `LEFTOVER_CHANGES` | worktree の変更はこのフィーチャーの作業で生じたものなので、`--commit-leftovers` を付けて `finish` を再実行する。含めた変更の一覧を完了報告に挙げる |
| `UNCHECKED_TASKS` | 未完了のタスクを S8 の手順で実装し、テストが通ったら `finish` を再実行する（`--allow-unchecked` は自動で付けない） |
| S8 の `[人]` のタスク | 実行せず、`[x]` にもしない。手順を示して保留にし、依存しない後続のタスクを続ける。保留にしたタスクを完了報告に挙げる |
| `HUMAN_TASKS_PENDING` | マージは済んでいる。残りの `[人]` のタスクを完了報告に挙げる（自動で完了にしない） |
| `DEFERRED_TASKS_PENDING` | マージは済んでいる。残りの `[後]` のタスクを、いつ行うかと一緒に完了報告に挙げる |

### 自動モードでも止まる場面

次の場面は、推奨案を選んでも取り返しがつかないか、推測で進めると危険なので、自動では進めない。

- `finish` でのマージの競合（自動で解消しない）
- 中止（`abort`）。ユーザーの明示的な同意が必要である
- `NOT_ON_MAIN`（メインの作業ツリーのブランチを自動で切り替えない）
- `UNCHECKED_TASKS` で、未完了のタスクを実装しても残る場合
- テスト・ビルド・リンターのコマンドが §4 の情報源から判断できない場合
- テストやビルドの失敗が、同じ原因に対して 3 回直しても解消しない場合
- S2 で、機能概要も追加指示もなく、何を作るかが決められない場合
- 憲章、デザインの柱（`docs/game/pillars.md`）、`docs/architecture.md`、`docs/nfr.md` の変更が必要になった場合（これらの改訂は自動で行わない）
- S4-2・S9-1 で、`docs/balance/targets.md` の既存の目標値や、`docs/game/` の式を変える必要がある場合（目標値を足すことは自動で行ってよい）
- S4-1 で、`docs/design/` の既存のトークンや共通の決め事の変更が必要になった場合（足すことは自動で行ってよい）

### 止まったときの扱い

1. worktree とブランチはそのまま残し、止まった理由、止まったステップ、ユーザーに判断してほしい事項（選択肢と推奨案）を記録する。
2. 単一のフィーチャーの指定なら、完了報告を出して終了する。
3. 範囲指定や `all` なら、そのフィーチャーを飛ばして次に進む（`all` では `next` の `--skip` に加える）。後続のフィーチャーの機能概要の `**依存**` に、飛ばしたフィーチャーが含まれる場合は、そのフィーチャーも飛ばす。
4. 止まったフィーチャーは、ユーザーが判断した後に、同じスキルをもう一度実行すれば（`--auto` の有無を問わない）続きのステップから再開できる。

### 記録

- **clarify（S3、S4）**: 見出しを `### Session YYYY-MM-DD (Round 1, auto)` のようにし、自動で採用した回答の行末に `(auto)` を付ける。
- **自動判断の一覧**: 自動で採用したすべての判断を `FEATURE_DIR/auto-decisions.md` に追記する。1 件ごとにステップ、論点、選択肢、採用した案、理由、反映したファイルを書く。clarify の回答もここに併記する。
- **完了報告**: 各スキルの完了報告に、`auto-decisions.md` の要約（見直しを勧める判断を先に）と、止まったフィーチャーとその理由、ユーザーに判断してほしい事項を加える。見直すときは `speckit-clarify` や該当するスキルを案内する。

## 7. 手動での利用

ユーザーからこのスキルを直接呼ばれたときは、引数に応じて次を行う。

- `status`（または引数なし）: `$HELPER status` の結果を表示し、途中の worktree があれば再開に使うスキルを案内する。人の作業が残っているフィーチャーがあれば、`human-tasks` での確認を案内する。
- `human-tasks [<feature>]`・`deferred-tasks [<feature>]`: 結果を表示する。
- `sync-status <feature>`: §3「人のタスクの片付け」の手順に従う。
- `next --phase <phase>`: 結果を表示する。
- `abort <feature>`: §3「中止」の手順に従う。
