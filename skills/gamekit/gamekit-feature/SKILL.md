---
name: "gamekit-feature"
description: "ゲームの機能の仕様工程を実行するスキル。Git worktree の準備（既存があれば再利用して続きから再開）、仕様作成（speckit-specify）、仕様明確化（speckit-clarify x 2。2 回目は中断と再開・入力の競合・極端な数値・抜け道などゲーム特有の例外系）、画面と HUD の仕様（gamekit-design）、調整仕様（gamekit-balance の spec。調整値と目標値）、詳細設計（speckit-plan）、タスク分解（speckit-tasks。プレイ確認は [人] のタスク）、整合性検証（speckit-analyze x 3）を行い、main へのマージと後片付けまでを実行する。実装は gamekit-coding、通しは gamekit-all で行う。「この機能の仕様を作って」と言われたとき、または /gamekit-feature と打たれたときに使う。"
argument-hint: "フィーチャー番号または範囲と、任意の --auto、--with-mock、--weight（例: 001, 002-005, all, all --auto, 003 --with-mock, 004 --weight 軽, または省略して次の未着手）"
compatibility: "Requires git and Python 3.9+, spec-kit project structure with .specify/ and .gamekit/config.yaml"
user-invocable: true
disable-model-invocation: false
---

# gamekit-feature スキル（仕様工程: S1 → S2〜S7-3 → S12）

機能ごとに、worktree の準備、仕様作成、明確化 2 回、画面と HUD の仕様、調整仕様、詳細設計、タスク分解、整合性検証 3 回を行い、仕様・設計・タスクを `main` にマージする。

- 実装工程（S8〜S11）は [`gamekit-coding`](../gamekit-coding/SKILL.md) が担当する。
- 仕様から実装までを 1 つの worktree で通して行う場合は [`gamekit-all`](../gamekit-all/SKILL.md) を使う。`gamekit-all` は、このファイルの「§3 本体」だけを実行する。

**ステップ番号、ヘルパースクリプト（`$HELPER`）、再開、安全規則、対話、引数の解釈は [`gamekit-worktree`](../gamekit-worktree/SKILL.md) に従う。** 作業を始める前に必ず読むこと。

パスは既定の配置で書いている。`.gamekit/config.yaml` の `paths` で読み替える。

## 1. ユーザー入力・引数

```text
$ARGUMENTS
```

引数の解釈と複数フィーチャーの進め方は `gamekit-worktree` の §5 に従う。`--auto` があるときは、下の質問の窓も含めて `gamekit-worktree` §6 の自動モードで進める。`--weight 軽|標準|重` があるときは、機能ファイルの重さの代わりに使う。`--with-mock` があるときは、S4-1 でモックを作る（`gamekit-design`）。自動検出では `--phase spec` を使う。

## 2. 実行の流れ（単独実行）

対象フィーチャーごとに、次を順に行う。

1. **S1 準備**: `gamekit-worktree` §3「S1 準備」に従い、`$HELPER ensure <feature> --phase spec` を実行する。
2. **本体**: 下の §3 の S2〜S7-3 のうち、`NEXT_STEP` 以降を順に実行する。
3. **S12 片付け**: `gamekit-worktree` §3「S12 片付け」に従い、`$HELPER finish <FEATURE_NAME> --phase spec` を実行する。
4. 次のフィーチャーがあれば 1 に戻る。

## 3. 本体（S2〜S7-3）

作業場所は `WORKTREE_DIR`、仕様ディレクトリは `specs/<FEATURE_NAME>`（以下 `FEATURE_DIR`）である。各ステップの最後に `gamekit-worktree` §2 の subject で `checkpoint` を記録する。

**機能の重さ**: S1 の `WEIGHT` に従って工程を変える（`gamekit-worktree` §2「機能の重さ」）。軽は S4・S7-2・S7-3 を省き、S3 は最大 3 問にする。標準は S7-3 を省く。軽・標準で画面や調整値がなければ S4-1・S4-2 も省く。省くステップは本体を行わず、`checkpoint <FEATURE_NAME> <step> "<subject>" --skipped "<重さ>: <理由>"` で記録する。

### 質問の窓

ユーザーへの質問は、ステップごとに出さず、次の「窓」にまとめる。1 つの窓では 1 回だけ、最大 4 問を、推奨案（`**Recommended:**`）と理由を添えて AskUserQuestion などで聞く（答えやすいよう、選択肢と推奨案で答えられる形にする）。

| 窓 | 時機 | 集める論点 |
|---|---|---|
| 窓 1（仕様の前） | S2 の前（機能概要と入力を読んだ直後） | スコープ、柱との関係、前提条件、遊びの範囲。S3 の clarify で出しそうな最重要の論点も先に聞いてよい |
| 窓 2（計画の前） | S5 の前（S4-2 の後） | clarify の残り（S3・S4 で出た論点）、画面の構成（S4-1）、初期値・範囲・目標値の置き方（S4-2）、アーキテクチャの分岐の見込み |

- 軽の機能は窓を 1 つ（窓 1）にし、それ以降の論点は推奨案で決めて `FEATURE_DIR/decisions.md` に書き、S8 の終わりの確認（`gamekit-coding` の S8）にまとめる。
- 窓と窓のあいだに出た論点は、推奨案で仮に進め、次の窓で確かめる。clarify の質問（S3・S4）も、ステップの中で聞かずに窓に回す（窓 1 で聞けなかったものは窓 2 で聞き、回答を `## Clarifications` に記録してから該当箇所を直す）。
- S5〜S7 で出た判断（ライブラリの選定、analyze の修正方針のトレードオフ）は、推奨案で進めて `decisions.md` に記録し、S8 の終わりの確認にまとめる。
- 窓の外でユーザーに聞いてよいのは、窓まで待つと作業が無駄になる前提の誤り（作る対象の取り違え、柱に反する要求など）だけである。
- 自動モード（`--auto`）では窓を開かず、推奨案を採用して `auto-decisions.md` に記録する。

### 入力情報

各ステップで、存在するものを参照する。

- 機能概要 `docs/feature/<FEATURE_NAME>.md`。`gamekit-features` の出力で、末尾の「`speckit-specify` に渡す記述案」を S2 の入力に使う。関わるシステム、デザインの柱、目標値（`BT-NNN`）の欄も読む。
- 前提メモ `docs/concept/premises.md`（GP1〜GP12）、着手順序 `docs/feature/spec_order.md`
- デザインの柱 `docs/game/pillars.md`、コアループ `docs/game/core-loop.md`、システム `docs/game/systems.md`、経済 `economy.md`、成長 `progression.md`
- 目標値 `docs/balance/targets.md`（この機能の行と `全体` の行）
- 憲章 `.specify/memory/constitution.md`、構成 `docs/architecture.md`、非機能要件 `docs/nfr.md`
- デザインの共通の決め事 `docs/design/`（`DESIGN.md`、`EXPERIENCE.md`、`FEEL.md`、トークン）
- 引数やプロンプトで与えられた追加指示

機能概要がなく、追加指示もない場合は、何を作るかをユーザーに質問してから S2 に進む。

### S2: 仕様作成（speckit-specify）

1. `speckit-specify` スキルの手順に従い、仕様書 `FEATURE_DIR/spec.md` を作る。
   - `SPECIFY_FEATURE_DIRECTORY` には `specs/<FEATURE_NAME>` を明示的に指定する。worktree はすでにこのディレクトリを前提に作られているため、新しい番号のディレクトリを作らない。
   - **WHAT（プレイヤーが何を体験するか）と WHY（どの柱とコアループのどこに効くか）**に集中し、HOW（エンジン、ノードの構成、クラス、データの形式）は書かない。
   - ユーザーストーリーは「プレイヤーとして〜したい」の形で、優先順（P1、P2、P3…）に並べる。受入基準には、プレイして確かめられる形（「〜の操作をすると、〜秒以内に〜が表示される」）を含める。
   - 機能要件（FR-001…）は検証可能に書く。数値（ダメージ、価格、確率、時間）は要件に固定せず、「調整値として扱う」と書いて S4-2 の `tuning.md` に回す。目標として守る数値は `BT-NNN` で参照する。
   - 測定可能な成功基準（SC-001…）には、目標値（`BT-NNN`）と、プレイ確認で判定する体験の基準（例: 初見のプレイヤーが説明なしで 3 分以内に最初の収穫を終える）を入れる。
   - 主要エンティティ（ゲームの中の物と状態）、エッジケース、前提条件
2. 品質チェックリスト `FEATURE_DIR/checklists/requirements.md` を作り、初回の検証を行う。デザインの柱に反する要件がないかも確かめる。
3. `checkpoint <FEATURE_NAME> S2` を記録する。

> 💬 仕様上の前提条件やスコープ、柱との関係の疑問は、窓 1 で聞く（窓のあとに出たものは窓 2 に回す）。

### S3: 仕様の明確化 1 回目（コアの遊び・振る舞い）

1. `speckit-clarify` スキルの手順で `spec.md` をスキャンし、遊びの範囲、プレイヤーの操作の流れ、意思決定と報酬、状態とデータのまとまり、ほかのシステムとの入出力の曖昧さと決定漏れを特定する。
2. 最重要の論点を、推奨選択肢（`**Recommended:**`）とその理由を添えてまとめる。推奨の根拠には、柱、コアループ、参考作品（`docs/research/competitors.md`）の定石を使う。窓 1 で聞いていなければ窓 2 で聞く（軽の機能は最大 3 問。窓 2 がないので推奨案で決めて `decisions.md` に書く）。回答が出るまでは推奨案で仮に反映する。
3. 確定した回答を `spec.md` の `## Clarifications` > `### Session YYYY-MM-DD (Round 1)` に記録し、本文の該当箇所に反映する。
4. `checklists/requirements.md` を再評価して更新する。
5. `checkpoint <FEATURE_NAME> S3` を記録する。

### S4: 仕様の明確化 2 回目（ゲーム特有の例外系・非機能）

1. 1 回目の決定事項を前提に、一段深い境界条件と例外系を洗い出す。
   - **中断と再開**: 遊んでいる途中のセーブとロード、アプリの中断・バックグラウンド・強制終了、古いセーブデータとの互換
   - **入力**: 連打、同時押し、入力の競合（メニューを開きながらの操作など）、入力機器の切り替え、キー割り当ての変更
   - **極端な数値**: 0、負の値、上限、桁あふれ、所持数の上限、長時間遊んだ後の値
   - **抜け道と支配戦略**: 無限に稼げる手順、ひとつの選択肢が常に最善になる状況、ソフトロック（進めなくなる状態）
   - **難しさ**: 詰まったときの救済、失敗の代償、再挑戦までの時間
   - **非機能**: フレームレートへの影響、読み込み時間、メモリ（`docs/nfr.md`）、決定性（同じシードで同じ結果になるか）
   - **ローカライズとアクセシビリティ**: 翻訳で長くなる文言、色だけに頼る表示、字幕、操作の代替（`docs/design/EXPERIENCE.md`、`FEEL.md`）
2. 残る重要な論点を、推奨選択肢とともに窓 2 にまとめる（軽の機能は S4 を省く）。
3. 回答を `### Session YYYY-MM-DD (Round 2)` に記録して本文に反映し、`checklists/requirements.md` を最終更新する。
4. `checkpoint <FEATURE_NAME> S4` を記録する。

### S4-1: 画面と HUD の仕様（gamekit-design）

[`gamekit-design`](../gamekit-design/SKILL.md) の §3 の手順に従い、`FEATURE_DIR/ui.md` を作る。

1. 画面も HUD も持たない機能（内部のシステムだけの機能など）では、`ui.md` を「**対象**: UI なし」にして理由を 1 行書く。
2. 画面や HUD のある機能では、`spec.md` の要件（FR）と画面・HUD の要素を対応づけ、表示、操作、状態、演出（フィードバック）を書く。技術は書かない。
3. `--with-mock` のときは、`gamekit-design` のモックの手順で主な画面のモックを作り、案を選んで `ui.md` に反映する。使えない環境では、テキストの仕様だけで進める。
4. `docs/design/EXPERIENCE.md` の画面一覧の、この機能の行を更新する。
5. `python3 <skills>/gamekit-design/scripts/validate_design.py docs/design --feature specs/<FEATURE_NAME>` のエラーを 0 件にする。
6. `checkpoint <FEATURE_NAME> S4-1` を記録する。

> 💬 画面の構成や要件の読み方の判断は、窓 2 に回す。

### S4-2: 調整仕様（gamekit-balance の spec）

[`gamekit-balance`](../gamekit-balance/SKILL.md) の spec モードの手順に従い、`FEATURE_DIR/tuning.md` を作る。

1. `spec.md` の「調整値として扱う」数値を、調整値の表（`TP-NNN`。パラメータ、データの場所、初期値、範囲、効く指標）にする。初期値は `docs/game/progression.md`・`economy.md` の式から導き、導き方を書く。
2. この機能で守る目標値を `docs/balance/targets.md` に `BT-NNN` で足す（機能の列は `<FEATURE_NAME>`）。既存の目標値は変えない（変える必要があれば、ユーザーに確かめる）。
3. 目標値を確かめるシミュレーションのシナリオ（名前、初期状態、プレイヤーの方策、回す時間、出す指標）を書く。
4. 調整値のない機能では、`tuning.md` を「**対象**: 調整値なし」にして理由を 1 行書く。
5. `python3 <skills>/gamekit-balance/scripts/balance.py targets` のエラーを 0 件にする。
6. `checkpoint <FEATURE_NAME> S4-2` を記録する。

> 💬 初期値や範囲、目標値の置き方の判断は、窓 2 に回す。

### S5: 詳細設計と憲章チェック（speckit-plan）

`speckit-plan` スキルの手順に従い、明確化を経た `spec.md`、`ui.md`、`tuning.md`、憲章、`docs/architecture.md` に基づいて次の成果物を作る。

1. `FEATURE_DIR/plan.md`: 技術コンテキスト（エンジン、言語、使うノード・モジュール・アドオン、テスト・ビルド・ヘッドレス実行のコマンド。`.gamekit/config.yaml` の `commands` に合わせる）と憲章チェック（各原則、デザインの柱との整合）。次を必ず書く。
   - **数値をデータに置く設計**: `tuning.md` の各調整値を、どのマスタデータ（`paths.data` の下のファイルとキー）に置き、どう読み込み、どう検証するか。コードに数値を直書きしない。
   - **決定性**: 乱数をどこで生成し、シードをどう渡すか。テストとシミュレーションで同じ結果を再現できるか。
   - **セーブ**: この機能が足す状態と、セーブデータのバージョン・移行（`000-game-foundation` の仕組みに乗る）。
   - **画面**: `ui.md` の画面・HUD を、どのシーン・コンポーネントで実現するか。値は `docs/design/` のトークンから使う。
   - **シミュレーション**: S4-2 のシナリオを、`commands.balance_sim` のどの入口で実行するか（`gamekit-balance` §2 の出力形式）。
2. `FEATURE_DIR/research.md`: 不明点の調査、技術選定の決定事項（Decision）、選定理由（Rationale）、比較した代替案（Alternatives considered）
3. `FEATURE_DIR/data-model.md`: エンティティ、属性と型、状態遷移、マスタデータのスキーマ
4. `FEATURE_DIR/contracts/`: ほかのシステムとのインターフェース（シグナル、イベント、公開メソッド、データのスキーマ）の契約
5. `FEATURE_DIR/quickstart.md`: 動作確認のシナリオ（起動してから確かめるまでの操作）、テストとシミュレーションの実行手順、期待結果

作り終えたら `checkpoint <FEATURE_NAME> S5` を記録する。

> 💬 アーキテクチャのトレードオフや、アドオン・ライブラリの選定の判断は、見込めるものは窓 2 で聞き、S5 で出たものは推奨案で進めて `decisions.md` に記録する（S8 の終わりに確かめる）。

### S6: タスク分解（speckit-tasks）

`speckit-tasks` スキルの手順に従い、設計成果物と `spec.md` のユーザーストーリーに基づいて `FEATURE_DIR/tasks.md` を作る。

- 形式: `- [ ] [TaskID] [P?] [Story?] 説明とファイルパス`
- フェーズ構成: Phase 1 Setup → Phase 2 Foundational → Phase 3 以降 User Stories（優先順）→ Final Phase Polish & Cross-Cutting Concerns
- マスタデータの作成・更新（`tuning.md` の調整値）を、それを使うコードのタスクの前に置く。
- シミュレーションのシナリオの実装が要るなら、タスクにする（S9-1 で使う）。
- 手触りの関わる機能（操作、演出、難しさ、読みやすさ）では、Final Phase に `[人]` の実機プレイ確認のタスクを置く。確かめる観点は `FEATURE_DIR/ui.md` の「プレイ確認の観点」の節を元に、`docs/design/FEEL.md` と `tuning.md` から補って書き写し、末尾に「（完了の確かめ方: `docs/playtest/<YYYYMMDD>-<FEATURE_NAME>.md` に観点ごとの結果がある）」と書く。
- エンジンのエディタでしかできない操作は、テキストで書けないものだけ `[人]` にする（steering の「エージェントの行動規範」）。
- 仕様で段階を分けると決めたタスク（垂直スライスに要らない分、ほかの機能の実装を待つ分など）には `[後]` を付け、末尾に「（いつ: …）」を書く（steering の「後の段階に回すタスク」）。`[後]` のタスクは `finish` を止めない。
- ストーリー間の依存関係、`[P]` タスクの並行実行例、MVP の範囲を示す。

作り終えたら `checkpoint <FEATURE_NAME> S6` を記録する。

### S7-1〜S7-3: 整合性検証 3 回（speckit-analyze）

`tasks.md`、`spec.md`、`ui.md`、`tuning.md`、`plan.md`、憲章、デザインの柱を対象に、`speckit-analyze` スキルの手順で分析と是正を、機能の重さに応じた回数（軽 1 回、標準 2 回、重 3 回）だけ直列に行う。行わない回（軽の S7-2・S7-3、標準の S7-3）は `--skipped` で記録する。最後に行う回で、下の S7-3 の条件（CRITICAL・HIGH・MEDIUM 0 件、憲章違反 0 件、カバレッジ 100%）を確かめる。各回の終わりに、次の検証のエラーを 0 件にし、`checkpoint` を記録する。指摘が 0 件で変更がなくても記録する。

```bash
python3 <skills>/gamekit-design/scripts/validate_design.py docs/design --feature specs/<FEATURE_NAME>
python3 <skills>/gamekit-balance/scripts/balance.py targets
python3 <skills>/gamekit-balance/scripts/balance.py params specs/<FEATURE_NAME>/tuning.md
```

`params` は、データの場所がまだない（S8 で作る）調整値を WARN にする。S7 では WARN は残してよい。

1. **S7-1（重大課題・憲章と柱の整合・カバレッジ）**: 憲章の MUST 原則やデザインの柱との矛盾（CRITICAL）、要件（FR-、SC-）と調整値（TP-）と目標値（BT-）に対応するタスクの未割り当て、仕様と設計の大きな乖離を検出して直す。
2. **S7-2（詳細整合・依存関係・ファイルパス）**: 用語の揺れ、エンティティとマスタデータのスキーマの不一致、`tuning.md` のデータの場所と `plan.md`・`data-model.md` の食い違い、タスクの依存順序の矛盾、ファイルパスの参照のずれを直す。
3. **S7-3（最終確認）**: CRITICAL、HIGH、MEDIUM の不整合が 0 件、憲章違反が 0 件、タスクのカバレッジが 100% であることを確かめる。満たさない場合は直してから記録する。

> 💬 修正方針のトレードオフは、推奨案で直して `decisions.md` に記録する（S8 の終わりに確かめる）。憲章や柱の変更が要るときだけ、その場で止めて聞く。

## 4. 完了報告

各フィーチャーの完了時と、指定範囲の全体の完了時に、次を報告する。

- 完了したフィーチャー名と番号、マージコミット
- 各ステップの要約（仕様、設計、タスクの成果物）
- clarify 2 回で確定した重要な決定事項
- 画面と HUD の仕様の要約（画面の数、`--with-mock` ならモックの URL。作れなかった場合はその理由）
- 調整仕様の要約（調整値の件数、足した目標値 `BT-NNN`、シミュレーションのシナリオ）
- analyze 3 回の検証結果
- `[人]` のタスク（プレイ確認など）の件数
- 飛ばした、または中断したフィーチャーとその理由
- `--auto` のとき: 自動で採用した判断の要約（`auto-decisions.md`）と、止まったフィーチャーについてユーザーに判断してほしい事項
- 次の案内: 実装は `gamekit-coding <FEATURE_NAME>`。仕様が未着手のフィーチャーは `$HELPER next --phase spec` の結果
