---
inclusion: always
---

# ゲーム開発ルール（gamekit）

このプロジェクトは gamekit でゲームを作る。gamekit は、GitHub Spec Kit による仕様駆動開発（`speckit-*` の標準スキル）に、ゲームの企画・コアループの検証・システムと経済の設計・バランス調整・手触りのレビューを足したものである。コードは仕様から導き、仕様は「遊びの設計」から導く。

## 基本原則

1. **面白さを先に確かめる**: 機能を作り込む前に、コアループと主要な意思決定を `docs/game/core-loop.md` に書き、机上の検証（`gamekit-prototype`）で仮説を確かめる。検証していない仮説の上に機能を積まない。
2. **デザインの柱と憲章が最上位**: `docs/game/pillars.md`（デザインの柱）と `.specify/memory/constitution.md`（憲章）をすべての判断の基準とする。機能の追加や変更が柱に反するときは、機能を変えるか、先に柱を見直す（`gamekit-core` の更新モード）。
3. **仕様は「何を・なぜ」、計画は「どう作るか」**: `spec.md` にはプレイヤーの体験と要件を書き、エンジンや実装の詳細は `plan.md` に書く。
4. **数値はデータに置く**: 敵の強さ、価格、成長曲線、確率などの調整値は、コードに直接書かず、マスタデータ（`.gamekit/config.yaml` の `paths.data`）に置く。機能ごとの調整値は `specs/<NNN>/tuning.md` に、全体の目標値は `docs/balance/targets.md` に書き、`gamekit-balance` で検算する。デザインの柱とコアループの仮説は、それぞれ何で検算するか（目標値・プレイ確認・対象外）を targets.md の「柱と仮説の検算」に決め、`balance.py coverage` で抜けを確かめる。目標値がすべて PASS でも、柱を表す目標値がなければ柱の崩れに気づけない。
5. **曖昧さは推測で埋めない**: 決まっていないことは `[NEEDS CLARIFICATION: ...]` として明示し、質問で解消する。自動モード（`--auto`、`--oneshot`）では、推奨案を明示して採用し、`auto-decisions.md` に記録することで確認に代える。
6. **成果物と実装を同期させる**: 実装中やバランス検証で設計の誤りが見つかったら、コードやデータだけを直さず、`spec.md`・`tuning.md`・`docs/game/`・`docs/balance/targets.md` にも反映する。
7. **手触りは人が確かめる**: 操作の気持ちよさ、読みやすさ、難しさの感じ方は、AI のレビューだけで合格にしない。実機でのプレイ確認は `[人]` のタスクにする（下の「人が行うタスク」）。
8. **オマージュと盗用を分ける**: 参考作品（`docs/research/competitors.md`）の名前、固有の用語、アセット、テキスト、特徴的な仕組みの組み合わせを、そのまま持ち込まない。機能ごとに類似性の軸（`gamekit-review` の Originality 軸）で確かめる。AI の判定は一次のふるい分けであり、疑わしいものは人か専門家が確かめる。
9. **出典を残す**: 調査の事実（作品の仕組み、売上、ストアの規約など）には、出典 URL と参照日を付ける。AI が挙げた作品名と仕組みは、実在を確かめてから使う。

## 工程

### ゲームの工程（`gamekit-bootstrap` が G1〜G14 を通しで行う）

| ステップ | スキル | 成果物 |
|---|---|---|
| G1 | `gamekit-seed` | `docs/concept/seed.md`（コアファンタジーと 1 文のピッチ） |
| G2 | `gamekit-research` | `docs/research/competitors.md`（参考作品・ジャンルの定石・差別化・IP の注意点） |
| G3 | `gamekit-direction` | `docs/concept/direction.md`（方向性の 3 案と選択） |
| G4 | `gamekit-sparring` | `docs/concept/premises.md`（GP1〜GP12）、`docs/concept/backlog.md` |
| G5 | `gamekit-core` | `docs/game/pillars.md`（デザインの柱）、`docs/game/core-loop.md`（コアループ） |
| G6 | `gamekit-prototype` | `docs/game/prototype/`（検証の計画、仮説、机上検証の結果） |
| G7 | `gamekit-systems` | `docs/game/systems.md`、`economy.md`、`progression.md`、`docs/balance/targets.md`（目標値と「柱と仮説の検算」） |
| G8 | `gamekit-architecture` | `docs/architecture.md`（エンジンと構成）、`.gamekit/config.yaml` の `engine` と `commands` |
| G9 | `speckit-constitution` | `.specify/memory/constitution.md` |
| G10 | `gamekit-features` | `docs/feature/`（機能概要 `001-*.md` 以降、`README.md`、`spec_order.md`） |
| G11 | `gamekit-foundation` | `docs/feature/000-game-foundation.md`（ゲームループ、入力、セーブ、データ読み込み、乱数、デバッグ） |
| G12 | `gamekit-nfr` | `docs/nfr.md`（フレームレート、読み込み時間、メモリ、対応端末）、`docs/feature/999-game-release.md`（ビルド、CI、配布） |
| G13 | `gamekit-design` | `docs/design/`（`DESIGN.md` 見た目、`EXPERIENCE.md` 画面と HUD、`FEEL.md` 手触り、トークン） |
| G14 | （`gamekit-bootstrap`） | 全体の検証 |

### 機能の工程（`gamekit-feature`・`gamekit-coding`・`gamekit-all`）

ステップ番号とコミットの trailer（`Speckit-Step`、`Speckit-Feature`）は speckit と共通である。ゲーム向けのステップは枝番で差し込んである。

| ステップ | スキル | 成果物 |
|---|---|---|
| S1 | `gamekit-worktree` | `.worktrees/<NNN-name>`（ブランチ `feature/<NNN-name>`） |
| S2 | `speckit-specify` | `specs/<NNN-name>/spec.md` |
| S3〜S4 | `speckit-clarify` ×2 | `spec.md`（2 回目はゲーム特有の例外系: 中断と再開、入力の競合、極端な数値、抜け道） |
| S4-1 | `gamekit-design`（§3） | `specs/<NNN-name>/ui.md`（画面と HUD の仕様） |
| S4-2 | `gamekit-balance`（spec） | `specs/<NNN-name>/tuning.md`（調整値と目標値） |
| S5 | `speckit-plan` | `plan.md`、`research.md`、`data-model.md`、`contracts/`、`quickstart.md` |
| S6 | `speckit-tasks` | `tasks.md` |
| S7-1〜3 | `speckit-analyze` ×3 | 整合性の検証 |
| S8 | `speckit-implement` | コード、マスタデータ、`tasks.md`（進捗） |
| S9 | `speckit-converge` | `tasks.md`（残作業の追記） |
| S9-1 | `gamekit-balance`（verify） | `specs/<NNN-name>/balance-report.md` |
| S10〜S11 | `gamekit-review` ×2 | `specs/<NNN-name>/reviews/review-<n>.md`（5 軸） |
| S12 | `gamekit-worktree` | `main` への `--no-ff` マージ、引き継ぎ書の更新 |

機能の番号のうち、`000` は共通基盤（`000-game-foundation`）、`999` はリリース基盤（`999-game-release`）の予約番号である。ゲームの中身の機能は `001` から振る。

### 機能の重さ（軽・標準・重）

上の表は「重」の機能の工程である。機能ファイルのヘッダの `**重さ**` で工程を軽くする（判定は `gamekit-features` の「重さ」、工程の表は `gamekit-worktree` §2「機能の重さ」）。

| 重さ | 条件 | 工程 |
|---|---|---|
| 重 | 保存形式、調整値と目標値、デザインの柱に効く規則のどれかに触れる | 上の表のとおり（clarify 2 回、analyze 3 回、5 軸レビュー 2 回） |
| 標準 | それ以外 | clarify 2 回、画面仕様・調整仕様は該当するときだけ、analyze 2 回、レビュー 2 回（2 回目は修正の差分だけ） |
| 軽 | 画面だけ、文言だけ、設定だけ | clarify 1 回（最大 3 問）、画面仕様・調整仕様は該当するときだけ、analyze 1 回、レビュー 1 回（関係する軸だけ） |

省いたステップは `checkpoint --skipped "<理由>"` で記録し、完了として数える（再開と `finish` の判定は崩れない）。迷ったら重い方にする。

### 質問と決めたこと

- 仕様工程の質問は、ステップごとに出さず「質問の窓」（仕様の前、計画の前。各 1 回、最大 4 問。軽は 1 つ）にまとめる（`gamekit-feature`）。
- 実装工程で推奨案で決めたことは `specs/<NNN-name>/decisions.md` に記録し、S8 の終わりと、マージの前（S12 の前。S9〜S11 で足された分）の 2 回にまとめて確かめる（`gamekit-coding`）。S9〜S11 で足されたものがなければ、2 回目は行わない。
- レビューの採否は実行中のエージェントが裏を取って決め、ユーザーに聞くのは仕様・柱・憲章・目標値を変えるものだけにする。

### 担当への任せ方

サブエージェントが使えるときは、実行中のエージェント（親）は指揮と裏取り（ユーザーへの質問、採否、`checkpoint`、マージと push、検証の再実行）を持ち、量の多い作業（S8 の Phase、S9、軸ごとのレビュー、指摘の修正）を担当に任せる。担当には `checkpoint`・マージ・push・ユーザーへの質問をさせない。親は差分を読まず、担当の報告と自分で再実行した検証の結果を見る（`gamekit-worktree` §4「親と担当の役割」「文脈の節約」、依頼文の雛形は `gamekit-worktree/references/delegation.md`）。

### 共通

- `gamekit-status`: 進捗の確認（ゲームの工程と機能の工程）、引き継ぎ書（`docs/handover/`）、環境の診断、ゲームの工程の記録（`gamekit.py checkpoint G<n>`）。
- `gamekit-balance`: 調整仕様（S4-2）、バランス検証（S9-1）のほか、単独でシミュレーションの準備、基準値の記録、差分の確認に使う。
- `gamekit-review`: 5 軸のレビュー。機能の工程の外で、任意の差分のレビューにも使う。

## レビューの 5 軸（`gamekit-review`）

| 軸 | 見ること |
|---|---|
| Standards | エンジンの作法、性能（毎フレームの割り当て、不要な処理）、決定性（乱数のシード）、型安全、コードの匂い |
| Spec | `spec.md`・`ui.md`・`tuning.md`・`plan.md`・憲章・デザインの柱との整合、仕様外の追加 |
| Balance | 数値がデータにあるか（直書きがないか）、目標値（`docs/balance/targets.md`）を満たすか、柱を表す目標値があるか（`balance.py coverage`）、支配戦略と抜け道、経済の入口と出口の釣り合い |
| Feel | 入力から反応までの遅れ、フィードバック（音・演出）、読みやすさ、難しさの段差、アクセシビリティ（`docs/design/FEEL.md`、`EXPERIENCE.md`） |
| Originality | 参考作品と、名前・用語・テキスト・アセット・特徴的な仕組みの組み合わせが一致していないか（Web で確かめる） |

審査する軸は変更の種類と機能の重さで選び、1 軸あたり最大 8 件、LOW は `specs/<NNN-name>/reviews/backlog.md` に送って直さない。2 回目で CRITICAL・HIGH が 0 件なら打ち切る（`gamekit-review` の「予算と打ち切り」）。

レビューの記録は `specs/<NNN-name>/reviews/` に置く。機能の工程の外のレビューは `docs/reviews/<YYYYMMDD>-<対象>.md` に置く。

## 人が行うタスク（`[人]`）

`tasks.md` の書式と規則は speckit と同じである（印は `[Story]` の後、末尾に「（完了の確かめ方: …）」）。ゲームでは、次のタスクに `[人]` を付ける。

- 実機でのプレイ確認（手触り、難しさ、読みやすさ）。確かめる観点は `docs/design/FEEL.md` と `tuning.md` から書き写す。
- ストア（Steam、App Store、Google Play など）のアカウント、審査、価格、公開の判断。
- 有料アセット・フォント・音源の購入とライセンスの確認、外注との契約。
- 署名鍵、証明書、API キーなどの秘密情報の作成と入力。

AI は `[人]` のタスクを実行せず、自動モードでも `- [x]` にしない。プレイ確認の結果は、人が `docs/playtest/<YYYYMMDD>-<対象>.md` に書くか、AI に伝えて書き写してもらう。結果から設計を直すときは、原則 6 に従う。

## 後の段階に回すタスク（`[後]`）

垂直スライスに要らない分、ほかの機能の実装を待つ分など、**この機能のマージの後に、別の段階で行うと決めたタスク**には `[後]` を付ける。書式は `[人]` と同じで、印は `[Story]` の後、末尾に「（いつ: 003 の前 / 公開時 / 001 の実装の後 など）」を書く。

- `[後]` にするのは、仕様（spec.md の Assumptions や Clarifications）で段階を分けると決めたタスクだけにする。実装が間に合わなかったタスクを `[後]` にしない（その場合は `--allow-unchecked` の確認を経る）。
- `gamekit-worktree` の `finish` は、未完了が `[人]`・`[後]` だけなら止めずにマージし、`DEFERRED_TASKS_PENDING` で残りを示す。機能ファイルの状態は `完了（後の作業 N 件）` になる（`[人]` が残れば `人の作業待ち`）。
- `speckit-converge`・`speckit-analyze`・`gamekit-review` は、未完了の `[後]` のタスクを実装漏れや不整合として扱わない。そのタスクと重なる新しいタスクも足さない。
- 残りは `$HELPER deferred-tasks` と `gamekit-status` で確かめ、その段階が来たら `gamekit-coding <機能> --deferred [T045,T046]` で片付ける。実装までマージ済みの機能は、専用の worktree（`.worktrees/<機能>-deferred`、ブランチ `feature/<機能>-deferred`）で S8〜S11 を対象のタスクだけに行い、`merge(<機能>): deferred` の件名でマージする。進捗は別の trailer（`Gamekit-Deferred-Step`）で記録し、もとの機能の進捗は変えない。
- 片付けたタスクは `- [x]` にし、`[後]` の印は残す（後回しにした記録として）。後の段階の作業は差分が小さいことが多いので、機能の重さに関わらず、S9-1（調整値・目標値に関わらないとき）と S11（S10 で CRITICAL・HIGH が 0 件のとき）を省いてよい。

## ほかの機能の一部だけを先に作る（`--until`・`--partial`）

ある機能の前提として、別の機能の一部（例: 001 の Phase 1 の品質ゲート）だけを先に入れたいときは、`gamekit-coding <機能> --until "Phase N"` で、`tasks.md` のその Phase までを実装して止め、`$HELPER finish <機能> --phase coding --partial` で `main` に入れる。件名は `merge(<機能>): partial` になり、その機能の進捗（S8 以降）は進まない。残りは後で同じ `gamekit-coding <機能>` で続ける（S8 から）。`status` の実装の列に「一部をマージ済み」と出る。

## 既存のプロジェクトへの取り込み

既存のプロジェクトには `new-gamekit-project <dir> --adopt` で gamekit を入れ、`gamekit-bootstrap --adopt` で既存の資料から成果物を作る（計画は `docs/adopt-plan.md`）。元の資料は動かさない・消さない・書き換えない。

- 取り込む前に Spec Kit で仕様化した機能には、`ui.md` と `tuning.md` がないことがある。`gamekit-coding`・`gamekit-all` の S1 で `ensure` が `MISSING_ARTIFACTS` を出したら、S8 の前に作る（`ui.md` は `gamekit-design` §3、`tuning.md` は `gamekit-balance` の spec モード）。作ったら trailer なしの通常のコミットにする（S4-1・S4-2 は推定で済んだ扱いのまま）。

## モード

| | 通常モード（既定） | 自動モード（`--auto`） |
|---|---|---|
| 質問 | 推奨案を添えて質問し、合意を得てから進める。機能の工程では、質問の窓と決めたことの確認にまとめる | 質問せず推奨案を採用し、`auto-decisions.md` に記録する |
| 止まる場面 | — | マージの競合、中止、憲章・デザインの柱・`docs/architecture.md` の変更が要るとき、同じ原因の失敗が 3 回続いたとき |

`gamekit-bootstrap` には、最初に一度だけ質問して以降を自動で進める `--oneshot` もある。

## エージェントの行動規範

- ユーザーが機能の追加や変更を頼み、対応する `specs/` のフィーチャーがまだないときは、いきなり実装せず、`gamekit-feature`（または `speckit-specify`）から始めることを提案する。
- ユーザーが数値の調整だけを頼んだときは、マスタデータと `tuning.md` を直し、`gamekit-balance tune`（`balance.py run` と `check`）で目標値を確かめる。仕様化は省いてよい。
- 各スキルは前の工程の成果物を前提にする。前提の成果物がなければ、欠けている工程を案内する。
- 1 つの工程が終わったら結果を要約し、次に実行すべきスキルを示す。
- 誤字の修正、依存関係の更新、設定の微調整など、遊びを変えない軽微な変更は仕様化を省いてよい。判断に迷ったらユーザーに確かめる。
- スクリプトは Python（3.9 以上、標準ライブラリのみ）で書かれており、`python3 <スクリプト>` の形で呼ぶ。`python3` がない環境では `python` または `py -3` に読み替える。
- テスト、ビルド、ヘッドレス実行、バランスのシミュレーションのコマンドは、`.gamekit/config.yaml` の `commands` を正とする。空なら `plan.md`、`quickstart.md`、プロジェクトの設定ファイルから判断し、判断できなければユーザーに確かめる。
- エンジンのエディタでしかできない操作（シーンの配置、インポートの設定など）は、手順を示して `[人]` のタスクにするか、テキストのシーン・リソースファイル（Godot の `.tscn`・`.tres` など）を直接書く。バイナリのアセットを生成したふりをしない。

## コマンドの呼び出し方

| エージェント | スキルの場所 | 呼び出し例 |
|---|---|---|
| Claude Code | `.claude/skills/` | `/gamekit-all 001` |
| Codex CLI | `.agents/skills/` | `$gamekit-all 001` |
| Antigravity (agy) | `.agents/skills/` | `/gamekit-all 001` |
| Kiro CLI | `.kiro/skills/` | スキル `gamekit-all` を指定して依頼する |
| opencode | `.opencode/commands/`（Spec Kit の標準のみ） | `/speckit.specify`。gamekit のスキルは「`gamekit-all` スキルで…」と依頼する |

各エージェントのスキルディレクトリにあるのは、`skills/speckit/`（Spec Kit の標準スキル）と `skills/gamekit/`（gamekit のスキル）への相対シンボリックリンクである。編集は `skills/` 側で行う。スキルの本文にある `$speckit-plan` のような Codex の書き方のコマンド参照は、自分のエージェントの呼び出し方に読み替える。

スキルの本文にある `AskUserQuestion`（選択肢付きの質問）、`WebSearch` / `WebFetch`（Web 検索とページの取得）、Agent（サブエージェント）は Claude Code のツール名である。ほかのエージェントでは同じ働きのツールを使う。質問のツールがなければ、選択肢と推奨案を文章で示して回答を待つ。Web を調べられない環境では、推測で埋めずに、調査が必要な項目と理由を伝える。

Claude Code のクラウドセッション（`CLAUDE_CODE_REMOTE=true`）では、speckit と同じく、マージ先をセッションの作業ブランチにし、コミットのたびに push する（`gamekit-worktree` §1）。

## ディレクトリ構成

```text
.gamekit/config.yaml         # エンジン、パスの対応、コマンド（テスト・ビルド・ヘッドレス実行・シミュレーション）、バランスの設定
.specify/                    # Spec Kit の憲章、テンプレート、スクリプト（直接編集しない。memory/constitution.md は除く）
docs/
├── auto-decisions.md        # 自動モードで決めたこと（ゲームの工程）。機能の工程の分は specs/<NNN>/auto-decisions.md
├── adopt-plan.md            # 既存のプロジェクトへの取り込みの計画（gamekit-bootstrap --adopt）
├── concept/                 # core-concept.md（入力）、seed.md、direction.md、premises.md、backlog.md
├── research/                # competitors.md、competitors/<作品>.md
├── game/                    # pillars.md、core-loop.md、systems.md、economy.md、progression.md、prototype/
├── balance/                 # targets.md（目標値）、baseline/（基準値）、reports/
├── architecture.md          # エンジンと構成（gamekit-architecture）
├── nfr.md                   # 非機能要件（gamekit-nfr）
├── feature/                 # 機能概要（000 は共通基盤、999 はリリース基盤）と spec_order.md
├── design/                  # DESIGN.md、EXPERIENCE.md、FEEL.md、tokens.tokens.json
├── playtest/                # プレイ確認の記録（人が書く）
├── reviews/                 # 機能の工程の外のレビュー
└── handover/                # CURRENT_STATE.md、PITFALLS.md、sessions/
specs/<NNN-name>/            # spec.md、ui.md、tuning.md、plan.md、tasks.md、balance-report.md、reviews/ など
```

パスは `.gamekit/config.yaml` の `paths` で既存の配置に合わせられる。スキルは、上の既定のパスを `paths` に読み替えて使う。

このプロジェクトでは `specify init --here --force`、`specify integration install` / `upgrade` / `switch` / `uninstall` を実行しない。スキルがシンボリックリンクのため、リンク先の共有スキルが上書きされるか、削除される。
