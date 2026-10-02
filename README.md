# gamekit

AI と一緒にゲームを作るためのスキルセット。[my-speckit-scaffold](../speckit/README.md)（仕様駆動開発）を土台に、[novelkit](../novelkit/README.md) の「作品全体の工程」の作りを取り入れ、ゲームの企画、コアループの検証、システムと経済の設計、バランス調整、手触りと類似性のレビューを足したものである。

- 1 文のコンセプトから、調査、方向性、壁打ち、デザインの柱、コアループの机上検証、システム設計、エンジンの選定、機能の切り出しまでを `gamekit-bootstrap` で通しで進める（G1〜G14）。
- 機能ごとの仕様から実装までは、speckit と同じ worktree の工程に、調整仕様（S4-2）とバランス検証（S9-1）と 5 軸のレビューを足した `gamekit-all` で進める。
- 数値はマスタデータに置き、目標値（`docs/balance/targets.md`）とシミュレーションの出力を `balance.py` で突き合わせる。
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

## 使い方

### 新しいゲーム

```bash
python3 ~/.myai/scaffold/gamekit/scripts/new_project.py ~/games/my-game --title "仮題" --engine godot
cd ~/games/my-game
claude "/gamekit-bootstrap 借金を抱えた農家が、痩せた土を再生しながら村の経済を立て直す経営シム"
```

または、起動までまとめて行う。

```bash
ln -s ~/.myai/scaffold/gamekit/scripts/new-gamekit-project ~/.local/bin/   # 初回だけ
new-gamekit-project ~/games/my-game --engine godot -m "1 文のコンセプト" --oneshot
```

- スキルはプロジェクトの `skills/` にコピーされる。`--link` を付けると、scaffold へのシンボリックリンクになる（scaffold の更新がすぐ反映される）。
- 立ち上げが終わったら `/gamekit-all` で `000-game-foundation` から 1 件ずつ進める。`/gamekit-all all --auto` で全機能を無人で進めることもできる（プレイ確認の `[人]` のタスクは残る）。

### 既存のプロジェクトに取り込む

```bash
python3 ~/.myai/scaffold/gamekit/scripts/new_project.py ~/projects/private/game/metal --adopt --link
```

- 既存のファイルは上書きしない。`.claude/skills/` などに同名のスキル（speckit をコピーで入れていたものなど）があれば残し、`CONFLICT` として表示する。gamekit 版に揃えるなら、既存のものを消してから `--relink` で張り直す。
- 既存の `CLAUDE.md` などは上書きしないので、表示された行（`@.kiro/steering/game-development.md` など）を足す。
- `.gamekit/config.yaml` の `paths`・`engine`・`commands` を既存の配置に合わせ、`gamekit.py doctor` で確かめる。
- `/gamekit-bootstrap --adopt` で、既存の資料（企画書、システム設計、競合調査など）から足りない成果物だけを作る。元のファイルは動かさない。
- speckit で作った `specs/` と、コミットの trailer の進捗はそのまま引き継がれる。S4-2 と S9-1 は、それより後のステップまで進んでいた機能では済んだものとみなされる。

### 進捗の確認と引き継ぎ

```bash
python3 skills/gamekit/gamekit-status/scripts/gamekit.py status     # ゲームの工程と機能の工程の進捗
python3 skills/gamekit/gamekit-status/scripts/gamekit.py handover   # 引き継ぎ書（docs/handover/）
python3 skills/gamekit/gamekit-status/scripts/gamekit.py doctor     # 設定とリンクの診断
```

または `/gamekit-status` を実行する。

### バランスの確認

```bash
B=skills/gamekit/gamekit-balance/scripts/balance.py
python3 $B run            # config.yaml の commands.balance_sim をシナリオごとに実行する
python3 $B check          # 目標値（docs/balance/targets.md）と突き合わせる
python3 $B diff           # 基準値（docs/balance/baseline/）からの動きを見る
python3 $B baseline       # 今の出力を基準値として記録する
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
│   └── gamekit/                        # gamekit のスキル（21 本）
│       ├── gamekit-status/scripts/     #   gamekit.py（進捗・引き継ぎ書・診断）、gklib.py（共通ライブラリ）
│       ├── gamekit-worktree/scripts/   #   worktree_helper.py（speckit 版の拡張）
│       ├── gamekit-balance/scripts/    #   balance.py（目標値・調整値・シミュレーション・基準値）
│       ├── gamekit-features/scripts/   #   validate.py（機能一式の検証）
│       └── gamekit-design/scripts/     #   validate_design.py（デザインの要件の検証）
├── scripts/
│   ├── new_project.py                  # プロジェクトを作る・既存のプロジェクトに取り込む
│   └── new-gamekit-project             # 作って Claude Code で立ち上げを始める
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
