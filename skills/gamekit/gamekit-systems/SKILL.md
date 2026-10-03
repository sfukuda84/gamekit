---
name: "gamekit-systems"
description: "コアループとプロトタイプの結果から、ゲームのシステム設計を作るスキル。システムの一覧と相互作用（docs/game/systems.md）、資源ごとの入口と出口とインフレの防ぎ方（docs/game/economy.md）、成長曲線・解放の順番・難しさの曲線（docs/game/progression.md）を書き、そこから検算できる目標値の一覧（docs/balance/targets.md の BT-NNN とシナリオ）を作る。gamekit-bootstrap の G7。既存の設計資料やマスタデータから移し替える取り込み、設計の見直し（更新モード）にも使う。「システムを設計して」「経済を設計して」「成長曲線を決めて」「目標値を作って」と言われたとき、または /gamekit-systems と打たれたときに使う。"
argument-hint: "[systems | economy | progression | targets（一部だけ作り直すとき）] [--update <理由>] [--adopt <既存の資料のパス>] [--auto]"
compatibility: "Requires Python 3.9+. Uses docs/game/core-loop.md, docs/game/prototype/results.md; writes docs/balance/targets.md"
user-invocable: true
disable-model-invocation: false
---

# gamekit-systems スキル（G7: システム・経済・成長と目標値）

コアループ（G5）と、その検証（G6）を、作れる形の設計に落とす。ここで作る目標値（`docs/balance/targets.md`）が、機能の工程で数値を検算する基準になる（`gamekit-balance`）。

- **ここに書くのは設計の値と式である。** 値の正本は、実装の後はマスタデータ（`paths.data`）になる。機能ごとの調整値は `specs/<NNN>/tuning.md` に書く。
- **目標値は検算できる形にする。** 「ほどよい」「気持ちいい」は目標値にならない。時間、回数、割合、偏りに直す。

パスは `.gamekit/config.yaml` の `paths` で読み替える（既定は `docs/game/`、`docs/balance/`）。

## 1. 入力

- `docs/game/core-loop.md`（3 層、意思決定 D、資源の流れ、仮説の状態）、`docs/game/pillars.md`
- `docs/game/prototype/results.md`（わかったこと、使ったパラメータ）と `sim/*.py`
- `docs/concept/premises.md`（GP2 遊ぶ場面とセッション長、GP6 progression、GP7 経済、GP8 失敗、GP9 終わり方、GP10 スコープ）
- `docs/research/competitors.md`（参考作品の数値。出典つき）
- 引数の `--adopt <パス>`: 既存の設計資料（例: `docs/design/systems.md`、`docs/specs/01-combat-formulas.md`）やマスタデータ（`game/content/*.json`、`src/config/gameConfig.ts`）

`core-loop.md` に「棄却」の仮説が残っていれば、`gamekit-prototype` を案内して止まる。「保留」の仮説は、関わる設計に「未検証（H<n>）」と書いて進めてよい。

## 2. 手順

### ステップ 1: システム（`systems.md`）

1. コアループの 3 層と意思決定から、システムを洗い出す（例: 移動、戦闘、採取、クラフト、商店、成長、クエスト、セーブ）。セーブ、入力、設定のような共通の仕組みは、システムにせず G11（`000-game-foundation`）の候補として `systems.md` の「共通基盤に回す仕組み」の節に書く（G10 の `gamekit-features` が `docs/feature/premises.md` の「基盤の候補」に移す）。
2. 各システムに、プレイヤーにとっての役割、対応する柱、ループの層、主なデータを書く。対応する柱がないシステムは、入れる理由を書くか、backlog に移す。
3. システムどうしのつながり（何を渡すか）を表と Mermaid の図で書く。入力のないシステム、出力がどこにも使われないシステムを探して直す。
4. システムごとの規則（プレイヤーから見た決まり、意思決定、例外と上限）を書く。式と数値は書かない。
5. [templates/systems.md](templates/systems.md) の様式で書く。

### ステップ 2: 経済（`economy.md`）

1. 資源を洗い出す（通貨、素材、時間、体力、枠）。資源ごとに上限と、ため込みの扱いを決める。
2. 資源ごとの**入口と出口**を書き、1 時間あたりの目安を見積もる。見積もりは、`prototype/results.md` のパラメータか、参考作品の値（出典）から作る。
3. **狙う増え方**を、序盤・中盤・終盤で言葉と数値の両方で書く。インフレの防ぎ方（出口の伸び方、上限、目減り）を決める。
4. **抜け道**（買って売ると得をする、繰り返すだけで増える）を、交換の組み合わせごとに確かめる。見つかったら、式か上限で塞ぐ。
5. 式（EQ-01〜）と、変数のデータの場所の予定を書く。
6. [templates/economy.md](templates/economy.md) の様式で書く。

### ステップ 3: 成長と難しさ（`progression.md`）

1. 成長の軸（何が伸びるか、伸ばし方、上限）を書く。
2. 成長曲線の式を決め、主な点の表を計算する。表は手で書かず、式から計算する（短いものは Python をその場で実行し、長いものは `docs/game/prototype/sim/` にスクリプトを置く）。GP2 のセッション長と GP9 の終わり方から、全体の長さ（クリアまで何時間か）を先に決め、そこから逆算する。
3. 解放の順番を決める。新しい意思決定がどの時点で増えるかを並べ、何も増えない区間（中だるみ）が長すぎないかを確かめる。
4. 難しさの曲線を、区間ごとに、敵・課題の強さとプレイヤーの強さの比で書く。急な段差には対策（救済、寄り道での強化）を書く。
5. [templates/progression.md](templates/progression.md) の様式で書く。

### ステップ 4: 目標値（`docs/balance/targets.md`）

1. `docs/balance/targets.md` がなければ、[../gamekit-balance/templates/targets.md](../gamekit-balance/templates/targets.md) をコピーして作る（記入例の行は消す）。
2. ステップ 2・3 の狙いを、検算できる目標値に直して `BT-001` から書く。機能の列は `全体` にする。
   - 速さ: 「`minutes_to_level_5` が 20〜40」
   - 釣り合い: 「中盤の `gold_per_hour` が 400〜700」「終盤の所持金が、最も高い買い物の 3 倍以下」
   - 偏り: 「最も使われる武器の占有率 `top_weapon_share` が 0.5 以下」（支配戦略の検出）
   - 難しさ: 「ボス 1 の推奨レベルでの勝率 `boss1_win_rate` が 0.4〜0.8」
   - 抜け道: 「売買の往復での利益 `arbitrage_gain` が 0 以下」
3. 指標を測る条件を「シナリオ」の表に書く（方針、シード、打ち切り、主に見る指標）。方針は、最低でも「最も効率の良い選択を繰り返す」ものと、「普通のプレイヤーを想定したもの」を用意する。
4. 根拠の列に、どの文書のどの節から来たかを書く。
5. `balance.py targets` のエラーを 0 件にする。

   ```bash
   python3 <skills>/gamekit-balance/scripts/balance.py targets
   ```

### ステップ 5: 点検

- すべてのシステムが、コアループの層か意思決定に対応しているか。
- 経済の入口と出口の見積もりが、成長曲線の必要量と合っているか（例: レベル 10 までに必要な強化の費用を、その時間の入口で払えるか）。計算して確かめる。
- 各柱を、少なくとも 1 つの目標値かシステムの規則が支えているか。
- 目標値が、実装の後にシミュレーションで測れる指標になっているか（プレイヤーの気持ちを指標にしていないか）。

> 💬 全体の長さ、狙う増え方、難しさの手応えなど、体験の方向を決める論点は、推奨案を添えて質問する（最大 3 問）。

## 3. 出力と記録

| ファイル | 内容 |
|---|---|
| `docs/game/systems.md` | システムの一覧、つながり、規則 |
| `docs/game/economy.md` | 資源、入口と出口、釣り合い、式 |
| `docs/game/progression.md` | 成長の軸、成長曲線、解放の順番、難しさの曲線 |
| `docs/balance/targets.md` | 目標値（BT）とシナリオ |

`gamekit-bootstrap` から呼ばれたときは、bootstrap がコミットする。単独で実行したときも同じ形で記録する。

```bash
python3 <skills>/gamekit-status/scripts/gamekit.py checkpoint G7 "docs(bootstrap): G7 システムと経済と目標値を設計" --allow-empty
```

更新モード・取り込み（G7 の記録がすでにあるとき）は、subject を `docs(game): システム設計を更新` にし、trailer を付けない。

## 4. 更新モード（`--update`）と取り込み（`--adopt`）

- **更新**: 成果物がすでにあるときは更新モードで動く。引数で一部（`economy` など）を指定されたら、その文書と targets.md の関わる行だけを直す。変えた目標値は、targets.md の「変更の記録」に理由とともに書く。機能の行（機能の列が `全体` 以外）は、その機能の `tuning.md` と一緒に `gamekit-balance` で直すので、ここでは変えずに影響を報告する。
- **取り込み**: 既存の設計資料を読み、3 つの文書に移し替える（元のファイルは動かさず、消さない。出典を添える）。既存のマスタデータがあれば、その値を「今の値」として表に書き、式が分かれば式を書く。既存のプロジェクトでバランスの検算がまだないときは、今の値から目標値の案を作り、「今の値から作った案（未確定）」と根拠の列に書いて、見直しの優先度を「高」にする。

## 5. 自動モード（`--auto`）

`gamekit-bootstrap` の `--auto`・`--oneshot` から呼ばれたときは、bootstrap §7 の規則に従う。単独の `--auto` も同じ扱いにする。

| 論点 | 自動モードでの動作 |
|---|---|
| 全体の長さ、狙う増え方、難しさの手応え | GP2・GP9 と参考作品の値から推奨案を採用する。見直しの優先度を「高」にする |
| 式と初期値 | `prototype/results.md` のパラメータを優先し、なければ参考作品の値。根拠が推測だけの値は「仮」と書く |
| 目標値の幅 | 狭すぎると調整で迷うので、参考作品の値の ±25% 程度から始める |
| システムに柱が対応しない | backlog に移す |

自動で決めたことは `docs/auto-decisions.md` の「G7」の節に書く。

## 6. 完了報告

- システムの数と一覧、浮いていたシステムとその扱い
- 資源ごとの狙う増え方と、塞いだ抜け道
- 全体の長さ、成長曲線の式、解放の順番の要約、難しさの段差
- 目標値の件数とシナリオの一覧、`balance.py targets` の結果
- 共通基盤に回す仕組みとして `systems.md` に挙げたもの
- 次の案内: `gamekit-architecture`（bootstrap の中なら G8 に進む）。シミュレーションの実装は、エンジンを決めた後に `gamekit-balance setup` で行う

## 7. 規則

- 表の値は式から計算して書く。手で書いた値と式が食い違ったら、式を正とする。
- 参考作品の数値を使うときは、出典 URL と参照日を書く（steering の原則 9）。参考作品の式や数値表を丸ごと写さない（原則 8）。
- 目標値は、後で実測に合わせて緩めるためのものではない。緩めるときは体験の狙いから理由を書く（`gamekit-balance` §8）。
- 応答と成果物は、プロジェクトの言語ルール（`.kiro/steering/language.md`）に従う。
