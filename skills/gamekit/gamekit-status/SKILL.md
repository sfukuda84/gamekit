---
name: "gamekit-status"
description: "gamekit の進捗確認・引き継ぎ書・環境の診断のスキル。ゲームの工程（gamekit-bootstrap の G1〜G14）と機能の工程（S1〜S12。gamekit-worktree）の進捗、最新のバランス検証の結果、残っている [人] のタスクを一覧し、次に実行すべきスキルを示す。引き継ぎ書（docs/handover/CURRENT_STATE.md の自動の節、sessions/、PITFALLS.md）を更新し、.gamekit/config.yaml・エンジンのコマンド・スキルのリンク・steering を診断する。設定の値の読み出し（config get）と初期化（init）もここで行う。「進捗を見せて」「次に何をすればいい」「引き継ぎ書を作って」「環境を確かめて」と言われたとき、または /gamekit-status と打たれたときに使う。"
argument-hint: "status | next | handover [--note <メモ>] | doctor | pitfall <内容> | init [--engine godot|web|other]"
compatibility: "Requires git and Python 3.9+"
user-invocable: true
disable-model-invocation: false
---

# gamekit-status スキル（進捗・引き継ぎ書・診断）

ゲームの工程と機能の工程の進み具合をまとめて示し、セッションをまたいで作業を引き継ぐための文書を保つ。進捗の判定はコミットの trailer だけから行うので、エージェントやセッションを変えても同じ結果になる。

## 1. ヘルパースクリプト

```bash
python3 <skills>/gamekit-status/scripts/gamekit.py [--root <dir>] <command> ...
```

以降、この呼び出しを `$GK` と書く。`<skills>` は、このスキルが置かれた skills ディレクトリ（`.claude/skills`、`.agents/skills`、`.kiro/skills` のいずれか）である。`python3` がない環境では `python` または `py -3` に読み替える。`--root` を省くと、`.gamekit/config.yaml`（なければ `.git`）を上へ探してプロジェクトのルートにする。worktree の中では worktree がルートになる。

| コマンド | 用途 |
|---|---|
| `$GK init [--config-only] [--title T] [--engine E] [--language L]` | `.gamekit/config.yaml` がなければテンプレートから作り、`paths` のディレクトリのうち無いものを作る（`paths.data`・`paths.specs`・憲章は作らない）。既存の値は上書きしない。`--config-only` は設定だけを作る（既存のプロジェクトで `paths` を合わせる前に使う） |
| `$GK config get <key.path>` | 設定の値を 1 行で出す（例: `commands.test`、`paths.data`、`balance.tolerance`）。値がなければ空行と終了コード 1 |
| `$GK bootstrap` | ゲームの工程の完了済みのステップ（`COMPLETED_STEPS`）と次のステップ（`NEXT_STEP`。すべて済んでいれば `DONE`） |
| `$GK status` | ゲームの工程、機能の一覧（`worktree_helper.py status`）、最新のバランスのレポートの PASS / FAIL / MISSING、引き継ぎ書の最終更新 |
| `$GK handover [--note <text>]` | 引き継ぎ書を更新する（§3）。コミットはしない |
| `$GK doctor` | 設定と環境を診断し、`OK` / `WARN` / `ERROR` の行と `SUMMARY` を出す（§4）。ERROR があれば終了コード 1 |

機能の工程の細かい操作（`next`、`human-tasks`、`sync-status`、`abort`）は [`gamekit-worktree`](../gamekit-worktree/SKILL.md) の `$HELPER` で行う。

## 2. 進捗の判定

| 工程 | 記録 | 判定 |
|---|---|---|
| ゲームの工程（G1〜G14） | `gamekit-bootstrap` のコミットの trailer `Gamekit-Bootstrap: G<n>` | `$GK bootstrap` |
| 機能の工程（S2〜S11） | `checkpoint` のコミットの trailer `Speckit-Step: <step>` と `Speckit-Feature: <name>`（speckit と共通） | `gamekit-worktree` の `$HELPER state` / `status` |
| バランス | `docs/balance/reports/*.md` と `specs/*/balance-report.md` のうち最新のもの | `$GK status` |

speckit で進めていたプロジェクトに gamekit を取り込んだときも、機能の工程の記録はそのまま読める（差し込んだステップ S4-1・S4-2・S9-1 は、後のステップの記録があれば済んだものとみなす）。ゲームの工程の記録はないので、`gamekit-bootstrap` の取り込みの手順（成果物がそろっているステップを確かめて記録する）で埋める。

## 3. 引き継ぎ書

置き場は `paths.handover`（既定は `docs/handover/`）である。

| ファイル | 書く人 | 中身 |
|---|---|---|
| `CURRENT_STATE.md` | 自動の節は `$GK handover`、ほかの節は人か AI | 今の目標、次にやること、判断待ち（手で書く）と、自動の節（更新日時とブランチ、ゲームの工程、バランス、機能の一覧、残っている `[人]` のタスク、見直しの優先度が「高」の自動判断、前回の引き継ぎ以降のコミット） |
| `sessions/<YYYYMMDD-HHMM>.md` | `$GK handover` | そのときの自動の節の写しと、`--note` のメモ。消さずに積み上げる |
| `PITFALLS.md` | 人か AI | 踏んだ罠と避け方。新しいものを上に書く。`$GK` は変えない |

### 更新する場面

- `gamekit-coding`・`gamekit-all` の S12（`finish`）の後。`gamekit-worktree` §3「S12 片付け」の手順で、main で更新してコミットする。
- `gamekit-bootstrap` の G14 の後。
- セッションを区切るとき（コンテキストが長くなった、人に引き継ぐ、止まった）。`--note` に、止めた理由と次の作業を書く。
- ユーザーに「引き継ぎ書を作って」と言われたとき。

### 手順

1. `$GK handover --note "<メモ>"` を実行する。
2. `CURRENT_STATE.md` の手で書く節（今の目標、次にやること、判断待ち）を、今の状況に合わせて直す。自動の節の印（`gamekit:auto:start`・`gamekit:auto:end` のコメント）の間は手で直さない（次の更新で消える）。
3. この作業で踏んだ罠があれば、`PITFALLS.md` の先頭に足す（日付、症状、原因、避け方、関係するファイル）。同じ罠がすでにあれば、足さずに既存の項目を直す。
4. `git add <paths.handover>` と `git commit -m "docs(handover): 引き継ぎ書を更新"` でコミットする（trailer は付けない）。worktree の作業の途中ならコミットせずに残してよい。クラウドセッションでは、コミットの後に push する。

### セッションの始め

新しいセッションで作業を始めるときは、まず `CURRENT_STATE.md` と `PITFALLS.md` を読み、`$GK status` で記録と食い違いがないかを確かめてから、「次にやること」を進める。

## 4. 診断（doctor）

`$GK doctor` は次を確かめる。

| 項目 | ERROR | WARN |
|---|---|---|
| `.gamekit/config.yaml` | ない、解釈できない | — |
| `engine`・`language` | — | 空、`godot` / `web` / `other` 以外 |
| `commands.*` | — | 空、先頭のプログラムが PATH にない |
| `paths.data` | — | まだない |
| `.claude/skills`・`.agents/skills`・`.kiro/skills` | ない、リンクが切れている、`gamekit-status`・`gamekit-worktree`・`speckit-specify` がない | — |
| `.specify/`、steering の 2 ファイル | ない | — |
| `CLAUDE.md`・`AGENTS.md`・`GEMINI.md` | — | ない、steering の 2 ファイルを参照していない |

WARN は、工程の途中では正常なこともある（例: G8 の前は `engine` と `commands` が空）。ERROR は直す。直し方の目安:

- リンクが切れている: scaffold の `scripts/new_project.py <プロジェクト> --adopt` を実行し直す（既存のファイルは上書きしない）。
- `commands` が空: `gamekit-architecture` の更新モードで埋める。エンジンが PATH にないなら、インストールの手順を示すか、絶対パスで書く（例: macOS の Godot は `/Applications/Godot.app/Contents/MacOS/Godot`）。

## 5. 手動での利用

ユーザーからこのスキルを直接呼ばれたときは、引数に応じて次を行う。

- `status`（または引数なし）: `$GK status` の結果を示し、次に実行すべきスキルを案内する。
  - ゲームの工程が `DONE` でなければ `gamekit-bootstrap`（`NEXT_STEP` から再開）。
  - 途中の worktree があれば、`gamekit-worktree` §3 に従って、そのステップを担当するスキル（S2〜S7-3 は `gamekit-feature`、S8〜S11 は `gamekit-coding`、どちらでも `gamekit-all`）。
  - なければ `$HELPER next --phase all` の結果で `gamekit-all <番号>`。
  - 残っている `[人]` のタスク（プレイ確認など）と、最新のバランスの FAIL があれば、それも挙げる。
- `next`: 上の案内だけを示す。
- `handover [--note <メモ>]`: §3 の手順に従う。
- `doctor`: 結果を示し、ERROR と、今の工程で直すべき WARN の直し方を案内する。
- `pitfall <内容>`: `PITFALLS.md` の先頭に、§3 の書き方で 1 件足す（コミットはユーザーに確かめてから）。
- `init [...]`: `$GK init` を実行し、作ったものを示す。

応答と成果物は、プロジェクトの言語ルール（`.kiro/steering/language.md`）に従う。
