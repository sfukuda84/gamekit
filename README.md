# gamekit

AI と一緒にゲームを作るためのスキルセット。[my-speckit-scaffold](../speckit/README.md)（仕様駆動開発）を土台に、[novelkit](../novelkit/README.md) の「作品全体の工程」の作りを取り入れ、ゲームの企画、コアループの検証、システムと経済の設計、バランス調整、手触りと類似性のレビューを足したものである。

- 1 文のコンセプトから、調査、方向性、壁打ち、デザインの柱、コアループの机上検証、システム設計、エンジンの選定、機能の切り出しまでを `gamekit-bootstrap` で通しで進める（G1〜G14）。
- 機能ごとの仕様から実装までは、speckit と同じ worktree の工程に、調整仕様（S4-2）とバランス検証（S9-1）と 5 軸のレビューを足した `gamekit-all` で進める。
- 数値はマスタデータに置き、目標値（`docs/balance/targets.md`）とシミュレーションの出力を `balance.py` で突き合わせる。デザインの柱とコアループの仮説を何で検算するか（目標値・プレイ確認・対象外）も targets.md に決め、`balance.py coverage` で抜けを確かめる。
- Claude Code、Codex CLI、Antigravity、Kiro CLI、opencode で同じスキルと規則を使う（規則の正本は `.kiro/steering/`、スキルの本体は `skills/`）。
- ステップが終わるたびにコミットし、trailer から進捗を判定する。中断しても続きから再開できる。機能の工程の trailer（`Speckit-Step`、`Speckit-Feature`）とステップ番号は speckit と共通なので、speckit で進めていたプロジェクトに取り込んでも進捗を引き継げる。
- スクリプトは Python（標準ライブラリのみ、3.9 以上）で、macOS、Linux、Windows で動く。

## 工程

```text
ゲームの工程（gamekit-bootstrap）
 G1 種 → G2 競合調査 → G3 方向性の 3 案 → G4 壁打ち（前提 GP1〜GP12）
 → G5 デザインの柱とコアループ → G6 机上検証（仮説を数値で確かめる）
 → G7 システム・経済・成長曲線と目標値 → G8 エンジンと構成 → G9 憲章
 → G10 機能の切り出し → G11 共通基盤（000） → G12 非機能要件とリリース基盤（999）
 → G13 見た目・画面・手触り → G14 検証

機能の工程（gamekit-feature → gamekit-coding、通しは gamekit-all）
 S1 worktree → S2 specify → S3・S4 clarify ×2 → S4-1 画面と HUD → S4-2 調整仕様
 → S5 plan → S6 tasks → S7 analyze ×3 → S8 implement → S9 converge
 → S9-1 バランス検証 → S10・S11 5 軸レビュー ×2 → S12 マージと引き継ぎ書
```

| 区分 | スキル | 工程 | 元 |
|---|---|---|---|
| 統括 | `gamekit-bootstrap` | G0〜G14（`--auto`、`--oneshot`、`--adopt`） | speckit-bootstrap、novelkit-bootstrap |
| 統括 | `gamekit-feature` | S1〜S7-3、S12 | speckit-feature |
| 統括 | `gamekit-coding` | S1、S8〜S12 | speckit-coding |
| 統括 | `gamekit-all` | S1〜S12 | speckit-all |
| 共通 | `gamekit-worktree` | worktree、ステップ番号、自動モード | speckit-worktree |
| 共通 | `gamekit-status` | 進捗、引き継ぎ書、環境の診断 | novelkit-status |
| 企画 | `gamekit-seed` | G1 | novelkit-seed |
| 企画 | `gamekit-research` | G2 | novelkit-research-wide、concept-2-feature の競合調査 |
| 企画 | `gamekit-direction` | G3 | novelkit-direction |
| 企画 | `gamekit-sparring` | G4 | novelkit-sparring、sparring-game |
| 設計 | `gamekit-core` | G5 | — |
| 設計 | `gamekit-prototype` | G6 | — |
| 設計 | `gamekit-systems` | G7 | — |
| 設計 | `gamekit-architecture` | G8 | speckit-architecture |
| 設計 | `speckit-constitution` | G9 | （Spec Kit の標準） |
| 設計 | `gamekit-features` | G10 | speckit-concept-2-feature |
| 設計 | `gamekit-foundation` | G11 | speckit-common-feature |
| 設計 | `gamekit-nfr` | G12 | speckit-nfr-feature |
| 設計 | `gamekit-design` | G13、S4-1 | speckit-design |
| 機能 | `gamekit-balance` | S4-2、S9-1、単独 | — |
| 機能 | `gamekit-review` | S10、S11、単独 | speckit-review |

Spec Kit の標準スキル（`speckit-specify`、`speckit-clarify`、`speckit-plan`、`speckit-tasks`、`speckit-analyze`、`speckit-implement`、`speckit-converge`、`speckit-checklist`、`speckit-constitution`、`speckit-taskstoissues`）は `skills/speckit/` にあり、統括スキルから呼ばれる。

## speckit との違い

| 観点 | speckit | gamekit |
|---|---|---|
| 立ち上げの入口 | コアコンセプト → 機能の仕分け | 種 → 調査 → 方向性 → 壁打ち → 柱とコアループ → 机上検証 → システム設計 → 機能の切り出し |
| 共通基盤（000） | 認証、メール送信など | ゲームループとシーン、入力、セーブとバージョン、マスタデータ、乱数とシード、デバッグ |
| 運用基盤（999） | 監視、バックアップ、CI/CD | CI（テスト・ヘッドレス・シミュレーション）、export とビルド、配布先、クラッシュの記録 |
| アーキテクチャ | SaaS/PaaS・クラウド・VPS の 3 系統 | エンジン（Godot GDScript / Godot C# / Web など）の比較、データ駆動、決定性 |
| デザイン | `DESIGN.md`、`EXPERIENCE.md` | ＋ `FEEL.md`（手触り。プレイ確認の観点） |
| 機能の工程 | S2〜S11 | ＋ S4-2 調整仕様、S9-1 バランス検証 |
| レビュー | Standards・Spec の 2 軸 | ＋ Balance・Feel・Originality の 5 軸 |
| 人のタスク（`[人]`） | 契約、管理画面の操作など | ＋ 実機でのプレイ確認、ストアの審査と公開、アセットのライセンス |

## モード

| | 通常モード（既定） | 自動モード（`--auto`） |
|---|---|---|
| 質問 | 推奨案を添えて質問し、合意を得てから進める | 質問せず推奨案を採用し、`auto-decisions.md` に記録する |
| 手触り | プレイ確認は `[人]` のタスクにする | 同じ（自動で完了にしない） |

`gamekit-bootstrap` には、最初に一度だけ質問して以降を自動で進める `--oneshot` と、既存のプロジェクトの資料から足りない成果物だけを作る `--adopt` もある。

## 機能の重さと、質問・レビューの量

1 機能を通すと、質問とレビューの指摘が多くなりがちなので、機能の重さで工程を軽くし、質問とレビューに予算を設けている。

- **重さ**: 機能ファイルのヘッダの `**重さ**`（`軽` / `標準` / `重`）。重 = 保存形式・調整値と目標値・柱に効く規則に触れる、軽 = 画面だけ・文言だけ・設定だけ、標準 = それ以外。軽は clarify 1 回・analyze 1 回・レビュー 1 回（関係する軸だけ）、標準は analyze 2 回・レビューの 2 回目は修正の差分だけ、重は今までどおり。省いたステップは `worktree_helper.py checkpoint … --skipped "<理由>"` で記録し、`status` に「（省略: …）」と出る。引数 `--weight` で上書きできる。
- **質問の窓**: 仕様工程の質問は、仕様の前と計画の前の 2 回（各最大 4 問。軽は 1 回）にまとめる。実装中に推奨案で決めたことは `specs/<NNN>/decisions.md` に記録し、実装の後（S8 の終わり）とマージの前（S9〜S11 で足された分）の 2 回で確かめる。
- **レビューの予算**: 変更の種類で審査する軸を選び（UI がなければ Feel は表示の層への影響だけ、調整値・規則の変更がなければ Balance を省く、など）、1 軸あたり最大 8 件、LOW は `reviews/backlog.md` に送って直さない。2 回目で CRITICAL・HIGH が 0 件なら打ち切る。
- **担当への任せ方**: サブエージェントが使えるときは、親（実行中のエージェント）は質問・採否・`checkpoint`・マージ・検証の再実行を持ち、実装（Phase ごと）・収束・軸ごとのレビュー・修正を担当に任せる。依頼文の雛形は `skills/gamekit/gamekit-worktree/references/delegation.md`。

## コマンドの導入と更新

[speckit](https://github.com/sfukuda84/my-speckit-scaffold) の `new-speckit-project` と同じく、uv のツールとして入れる。

```bash
uv tool install "git+https://github.com/sfukuda84/gamekit#subdirectory=tool"   # 導入（初回だけ）
uv tool upgrade new-gamekit-project                                                     # コマンドの更新
new-gamekit-project update [プロジェクトのディレクトリ]                                   # 作成済みのプロジェクトに scaffold の新しい版を取り込む
```

- `new-gamekit-project` は、実行のたびに scaffold を GitHub から取得してプロジェクトを作る（`--ref` でブランチやタグ、`--repo` でリポジトリを指定できる）。
- `update` は、scaffold の持ち物（スキル、ルールなど）だけを取り込み、1 つのコミットにする。scaffold のどの版とも中身が一致しないファイルは手で直したものとみなして上書きせず、新しい版を `.scaffold-new/` に置く。取り込みで残した同名のスキルにも触らない。`--dry-run` で、何が変わるかだけを見られる。
- スキルを scaffold へのリンクで置いたプロジェクト（`--link`）は、スキルがすでに最新なので、`update` はリンクの外（ルールなど）だけを更新する。
- 手元の scaffold（このリポジトリの clone）から使うときは、`scripts/new-gamekit-project` を直接実行するか、`--scaffold <ディレクトリ>` を付ける。`--link` は手元の scaffold を使うときだけ使える。
- 以前に `~/.local/bin/new-gamekit-project` を `scripts/new-gamekit-project` へのシンボリックリンクで入れていたなら、リンクを消してから uv で入れる（`rm ~/.local/bin/new-gamekit-project`）。
- オプションの一覧は [tool/README.md](tool/README.md) にある。

## 使い方

### 新しいゲーム

```bash
new-gamekit-project ~/games/my-game --title "仮題" --engine godot -m "借金を抱えた農家が、痩せた土を再生しながら村の経済を立て直す経営シム"
```

- プロジェクトを作り、Claude Code で `/gamekit-bootstrap <コンセプト>` を始める。`-m` を省くと対話でコンセプトを聞く。`--auto`・`--oneshot` を付けると、そのモードで始める。
- スキルはプロジェクトの `skills/` にコピーされる。手元の scaffold を使い `--link` を付けると、scaffold へのシンボリックリンクになる（scaffold の更新がすぐ反映される）。コピーのプロジェクトは `new-gamekit-project update` で新しい版にする。
- 立ち上げが終わったら `/gamekit-all` で `000-game-foundation` から 1 件ずつ進める。`/gamekit-all all --auto` で全機能を無人で進めることもできる（プレイ確認の `[人]` のタスクは残る）。

### 既存のプロジェクトに取り込む

```bash
new-gamekit-project ~/projects/private/game/metal --adopt
```

- 既存のファイルは上書きしない。`.claude/skills/` などに同名のスキル（speckit をコピーで入れていたものなど）があれば残し、`CONFLICT` として表示する。gamekit 版に揃えるなら、既存のものを消してから、手元の scaffold の `python3 scripts/new_project.py --relink <プロジェクト>` で張り直す。
- 既存の `CLAUDE.md` などは上書きしないので、表示された行（`@.kiro/steering/game-development.md` など）を足す。
- `.gamekit/config.yaml` の `paths`・`engine`・`commands` を既存の配置に合わせ、`gamekit.py doctor` で確かめる。
- `/gamekit-bootstrap --adopt` で、既存の資料（企画書、システム設計、競合調査など）から足りない成果物だけを作る。元のファイルは動かさない。
- speckit で作った `specs/` と、コミットの trailer の進捗はそのまま引き継がれる。S4-2 と S9-1 は、それより後のステップまで進んでいた機能では済んだものとみなされる。そのような機能に `ui.md`・`tuning.md` がなければ、`gamekit-coding` の S1 で `MISSING_ARTIFACTS` が出るので、S8 の前に作る。

### 進捗の確認と引き継ぎ

```bash
python3 skills/gamekit/gamekit-status/scripts/gamekit.py status     # ゲームの工程と機能の工程の進捗
python3 skills/gamekit/gamekit-status/scripts/gamekit.py handover   # 引き継ぎ書（docs/handover/）
python3 skills/gamekit/gamekit-status/scripts/gamekit.py doctor     # 設定とリンクの診断
python3 skills/gamekit/gamekit-status/scripts/gamekit.py checkpoint G5 "docs(bootstrap): G5 …" --allow-empty   # ゲームの工程の記録
```

または `/gamekit-status` を実行する。ゲームの工程の記録は `checkpoint` で行い、コミットを手で書かない（trailer `Gamekit-Bootstrap: G<n>` を最後の段落に置かないと、完了として数えられない）。

### 後の段階に回すタスクと、一部だけを先にマージする

- **`[後]`**: 仕様で段階を分けると決めたタスク（垂直スライスに要らない分、ほかの機能の実装を待つ分など）には `tasks.md` で `[後]` を付け、「（いつ: …）」を書く。`finish` は `[人]` と同じく止まらずにマージし、`DEFERRED_TASKS_PENDING` で残りを示す。残りは `worktree_helper.py deferred-tasks` と `gamekit.py status` で見える。その段階が来たら `gamekit-coding <機能> --deferred [T045,T046]` で片付ける（実装までマージ済みの機能でも、専用の worktree `<機能>-deferred` で S8〜S11 を対象のタスクだけに行い、`merge(<機能>): deferred` でマージする。もとの機能の進捗は変えない）。
- **`--until` と `--partial`**: ある機能の前提として、別の機能の一部の Phase だけを先に入れるときは、`/gamekit-coding 001 --until "Phase 1"` で実装し、`worktree_helper.py finish 001 --phase coding --partial` で `main` に入れる。件名は `merge(001): partial` で、001 の進捗は進まない（残りは後で `/gamekit-coding 001` で S8 から続ける）。

### バランスの確認

```bash
B=skills/gamekit/gamekit-balance/scripts/balance.py
python3 $B run            # config.yaml の commands.balance_sim をシナリオごとに実行する
python3 $B check          # 目標値（docs/balance/targets.md）と突き合わせる
python3 $B diff           # 基準値（docs/balance/baseline/）からの動きを見る
python3 $B baseline       # 今の出力を基準値として記録する
python3 $B coverage       # 柱と仮説が、目標値・プレイ確認で検算されているかを確かめる
```

数値だけを直したいときは、マスタデータと `tuning.md` を直して `check` を通せばよい（仕様化は要らない）。

## ディレクトリ構成（scaffold）

```text
.
├── README.md
├── CLAUDE.md / AGENTS.md / GEMINI.md / opencode.json   # .kiro/steering を読むよう指示するだけ
├── .kiro/steering/                     # エージェント共通ルールの正本
│   ├── language.md                     #   応答と成果物は日本語
│   └── game-development.md             #   gamekit の工程とルール（Spec Kit の規則を含む）
├── .specify/                           # Spec Kit の憲章の雛形、テンプレート、スクリプト（Specify CLI 1.0.10 が生成）
├── .opencode/commands/                 # opencode 用の Spec Kit コマンド
├── .claude/skills/ .agents/skills/ .kiro/skills/   # → skills/*/* へのシンボリックリンク
├── skills/
│   ├── speckit/                        # Spec Kit の標準スキル（10 本。編集しない）
│   └── gamekit/                        # gamekit のスキル（20 本）
│       ├── gamekit-status/scripts/     #   gamekit.py（進捗・引き継ぎ書・診断）、gklib.py（共通ライブラリ）
│       ├── gamekit-worktree/scripts/   #   worktree_helper.py（speckit 版の拡張）。references/delegation.md（担当への依頼文の雛形）
│       ├── gamekit-balance/scripts/    #   balance.py（目標値・調整値・シミュレーション・基準値・柱と仮説の検算）
│       ├── gamekit-features/scripts/   #   validate.py（機能一式の検証）
│       └── gamekit-design/scripts/     #   validate_design.py（デザインの要件の検証）
├── scripts/
│   ├── new_project.py                  # プロジェクトを作る・既存のプロジェクトに取り込む・リンクを張り直す（--relink）
│   └── new-gamekit-project             # 手元の scaffold から使うときの入口（本体は tool/）
├── tool/                               # uv で入れるコマンド new-gamekit-project（作成・取り込み・update）とテスト
└── THIRD_PARTY_NOTICES.md
```

## プロジェクトのディレクトリ構成

```text
.gamekit/config.yaml          # エンジン、パスの対応、コマンド、バランスの設定
.specify/memory/constitution.md   # 憲章
docs/concept/                 # core-concept.md、seed.md、direction.md、premises.md、backlog.md
docs/research/                # competitors.md、competitors/
docs/game/                    # pillars.md、core-loop.md、systems.md、economy.md、progression.md、prototype/
docs/balance/                 # targets.md、baseline/、reports/
docs/architecture.md、docs/nfr.md
docs/feature/                 # 000-game-foundation.md、001-*.md、999-game-release.md、spec_order.md
docs/design/                  # DESIGN.md、EXPERIENCE.md、FEEL.md、tokens.tokens.json
docs/playtest/                # プレイ確認の記録
docs/handover/                # CURRENT_STATE.md、PITFALLS.md、sessions/
specs/<NNN-name>/             # spec.md、ui.md、tuning.md、plan.md、tasks.md、balance-report.md、reviews/
```

## 対応するエンジン

最初の版では、Godot 4（GDScript / C#）と Web（TypeScript）について、テスト、ヘッドレス実行、バランスのシミュレーション、ビルドの定石を `gamekit-architecture/references/` に持つ。それ以外のエンジンや言語（Go のサーバーなど）は `engine: other` とし、`commands` を手で埋めれば同じ工程で使える。

## まだないもの

- プレイテストの専用スキル（いまは `[人]` のタスクと `docs/playtest/` の記録で扱う）
- ストアの掲載文・スクリーンショットなど公開の準備（novelkit-publish に当たるもの）
- 事業計画と企画書（speckit-project、speckit-presentation に当たるもの。必要なら speckit のものを使う）
- Web 検索の回数の予算管理（novelkit の `budget` に当たるもの）
