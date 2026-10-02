---
name: "gamekit-balance"
description: "ゲームの数値を、目標値とシミュレーションで検算するスキル。機能の工程の S4-2（spec モード: specs/<NNN>/tuning.md に調整値と狙う体験を書き、docs/balance/targets.md に検算できる目標値 BT を足す）と S9-1（verify モード: シミュレーションを実行して目標値と突き合わせ、FAIL をデータか仕様の見直しで直し、balance-report.md に残す）を担う。単独では、シミュレーションの準備（Godot・Web の雛形と config.yaml の commands.balance_sim）、基準値の記録、基準値との差分、数値の調整だけの依頼に使う。判定は balance.py（targets / params / run / check / baseline / diff）が行う。「バランスを確かめて」「数値を調整して」「シミュレーションを用意して」「基準値を取って」と言われたとき、または /gamekit-balance と打たれたときに使う。"
argument-hint: "spec <機能> | verify <機能> | setup | check [--feature <機能>] | baseline | diff | tune <調整の依頼> [--auto]"
compatibility: "Requires Python 3.9+. Uses .gamekit/config.yaml, docs/balance/targets.md, specs/<NNN>/tuning.md"
user-invocable: true
disable-model-invocation: false
---

# gamekit-balance スキル（調整仕様・バランス検証・シミュレーション）

ゲームの数値は「何となく」で決めると、後から誰も理由を説明できなくなる。このスキルは、数値を **狙う体験 → 目標値（BT）→ 調整値（TP）→ シミュレーションでの判定** の順につなぎ、どの数値がどの体験のためにあるかを追えるようにする。

- 値の正本はマスタデータ（`.gamekit/config.yaml` の `paths.data`）である。`tuning.md` は「何を・なぜ・どこまで動かしてよいか」を書き、値そのものはデータを指す。
- 判定は `balance.py` が機械的に行う（`check` の表の「判定」の列は `PASS` / `FAIL` / `MISSING` の文字だけで、`gamekit.py status` が数える。理由は「備考」の列に出る）。AI は判定の結果を読み、原因を考え、直す。
- シミュレーションで測れるのは数値の性質（速さ、偏り、支配戦略）までである。手触りと難しさの感じ方は、`[人]` のプレイ確認で確かめる（steering の原則 7）。

パスは `.gamekit/config.yaml` の `paths` と `balance` で読み替える（既定は `docs/balance/`、`build/balance/`、`docs/balance/baseline/`）。

## 1. 引数とモード

```text
$ARGUMENTS
```

| 指定 | モード | 呼び出し元 |
|---|---|---|
| `spec <機能>` | 調整仕様を作る（§3） | `gamekit-feature` の S4-2 |
| `verify <機能>` | バランス検証（§4） | `gamekit-coding` の S9-1 |
| `setup` | シミュレーションの準備（§5） | 単独。`000-game-foundation` の実装や、初めて検証する機能の前 |
| `check [--feature <機能>]` | 判定だけを行い、結果を示す（§6） | 単独 |
| `baseline` | 今の出力を基準値として記録する（§6） | 単独。調整を確定したとき |
| `diff` | 基準値との差分を示す（§6） | 単独。データやコードを変えた後 |
| `tune <調整の依頼>` | 数値の調整だけを行う（§6） | 単独。「序盤をもう少し楽に」など |
| `--auto` | 自動モード（§7） | 位置を問わない |

引数がなければ、`check` として扱う。`<機能>` は `003` や `003-crafting` の形である。worktree の中で呼ばれたときは、worktree のディレクトリで作業する。

## 2. ヘルパースクリプトとファイルの形式

```bash
python3 <skills>/gamekit-balance/scripts/balance.py [--root <dir>] <command>
```

以降、この呼び出しを `$BAL` と書く。`<skills>` は、このスキルが置かれた skills ディレクトリである。`python3` がない環境では `python` または `py -3` に読み替える。

| コマンド | 用途 | 終了コード |
|---|---|---|
| `$BAL targets` | `targets.md` の検査（ID の形と重複、下限 ≤ 上限、空欄） | 0 / 1（エラー） |
| `$BAL params <tuning.md>` | 調整値の「データの場所」が解決し、値が数値で、初期値と一致するか。ERROR は表の形式の崩れと、値が数値でないこと。ファイルや Pointer がまだない（実装前）・初期値と違う、は WARN | 0 / 1（ERROR） |
| `$BAL run [--scenario S]... [--feature NNN]` | `commands.balance_sim` をシナリオごとに実行する | 0 / 1 / 3（`NO_SIM_COMMAND` など） |
| `$BAL check [--feature NNN] [--report <path>]` | 出力と目標値を突き合わせ、PASS / FAIL / MISSING の表を出す | 0 / 1（FAIL）/ 2（MISSING だけ）/ 3 |
| `$BAL baseline [--scenario S]...` | 出力を基準値の置き場にコピーする | 0 / 1 |
| `$BAL diff [--scenario S]...` | 出力と基準値を比べ、`balance.tolerance` を超えた変化を出す | 0 / 1（変化あり） |

終了コード 3 のときは、標準エラーに `PRECONDITION: <code>` が出る。`NO_TARGETS`（`targets.md` がない → `gamekit-systems`）、`NO_SIM_COMMAND`（→ §5）、`BAD_TARGETS`（→ `$BAL targets` のエラーを直す）、`BAD_FEATURE`（引数の形）である。

### 目標値（`docs/balance/targets.md`）

様式は [templates/targets.md](templates/targets.md)。`gamekit-systems`（G7）が全体の行を作り、spec モードが機能の行を足す。

| 列 | 書き方 |
|---|---|
| ID | `BT-001` から通し番号。欠番にしてよいが、使い回さない |
| 指標 | シミュレーションの出力の `metrics` のキー（英数字と `_`。単位を名前に入れる: `minutes_to_level_5`） |
| シナリオ | 出力のファイル名になる条件の名前。同じファイルの「シナリオ」の表に方針・シード・打ち切りを書く |
| 下限・上限 | 数値。片側だけなら、もう一方を `-` |
| 根拠 | どの設計から来たか（`progression.md §2`、`pillars.md 柱 2`、`GP8`、`spec.md SC-003`） |
| 機能 | `全体` か `003-crafting`。`check --feature 003` は、その機能の行と `全体` の行を見る |

### シミュレーションの出力

`<balance.out_dir>/<シナリオ>.json`（既定は `build/balance/`。コミットしない）。

```json
{"scenario": "early_game", "seed": 1, "metrics": {"minutes_to_level_5": 31.5, "gold_per_hour": 520}}
```

- `metrics` の値は数値だけにする。真偽は 0 / 1、割合は 0〜1 か千分率のどちらかにそろえ、指標の名前で分かるようにする（`win_rate`、`win_permille`）。
- 同じシナリオとシードなら、何度実行しても同じ値になること（決定性）。乱数はシナリオのシードから作り、ゲームの処理に引数で渡す。

### 調整仕様（`specs/<NNN>/tuning.md`）

様式は [templates/tuning.md](templates/tuning.md)。調整値の表の列は `ID | パラメータ | データの場所 | 初期値 | 範囲 | 効く指標 | 備考`（`balance.py params` が読む）。データの場所は `ファイル#JSON Pointer`（例: `game/data/enemies.json#/slime/hp`、配列は `#/waves/0/count`）である。JSON 以外（Godot の `.tres`、TypeScript の設定オブジェクトなど）は、ファイルのパスだけを書き、中の位置を備考に書く（存在だけを確かめる）。

## 3. spec モード（S4-2: 調整仕様）

入力: `spec.md`（明確化済み）、`ui.md`、`docs/game/`（`pillars.md`、`core-loop.md`、`systems.md`、`economy.md`、`progression.md`）、`docs/balance/targets.md`、機能概要 `docs/feature/<NNN>.md`（関わる BT の記載）、マスタデータの今の中身。

1. **調整値があるかを決める。** プレイヤーの体験を左右する数値（強さ、価格、時間、確率、量、上限）が、この機能で増えるか変わるか。ない機能（タイトル画面、設定画面、セーブの仕組みなど）は、`tuning.md` を「調整値なし（理由: …）」の 1 段落にして 6 に進む。
2. **狙う体験を書く。** `spec.md` のユーザーストーリーと柱から、この機能でどう感じてほしいかと、崩れたときの症状を書く。
3. **調整値を洗い出す。** `TP-001` から番号を振る。
   - データの場所は、既存のマスタデータにあればそのキー、なければ置く予定のファイルとキー（S8 で作る）。plan の前なので、形式は `docs/architecture.md` の「データ駆動」の節に合わせる。
   - 初期値は、`progression.md` の式や表、参考作品の値（出典つき）、既存のデータとの釣り合いから決め、決め方を備考に書く。勘で決めた値は「仮」と書く。
   - 範囲は「この範囲なら仕様を変えずに調整してよい」幅である。
4. **目標値を決める。** 調整値が効く指標を、検算できる形で `docs/balance/targets.md` に足す（機能の列にこの機能名）。全体の BT で足りるなら、使う ID を書くだけにする。
   - 「楽しい」「ほどよい」は目標値にならない。時間、回数、割合、偏り（最も使われる選択肢の占有率など）に直す。
   - 支配戦略と抜け道（繰り返すだけで得をする、1 つの選択だけが強い）を挙げ、検出する指標とシナリオを決める。
5. **シミュレーションとプレイ確認を決める。** 対象のシナリオ（新しく要るなら targets.md の「シナリオ」の表に足す）、シミュレーションから呼ぶ仕組みと出す指標を書く（S6 でタスクになる）。測れないことは「プレイ確認の観点」に書く（S6 で `[人]` のタスクになる）。
6. **検査する。** `$BAL targets` のエラーを 0 件にする。`$BAL params specs/<NNN>/tuning.md` の ERROR を 0 件にする。まだ作っていないデータの WARN（ファイルや Pointer がない）は、備考に「S8 で作る」と書いて残してよい。

呼び出し元（`gamekit-feature`）が `checkpoint <FEATURE_NAME> S4-2` を記録する。単独で呼ばれたときは、`docs(<FEATURE_NAME>): 調整仕様を作成` でコミットしてよいかを確かめる。

> 💬 体験の狙い、初期値の決め方、目標値の幅に判断が要るときは、推奨案を添えて質問する（最大 3 問）。

## 4. verify モード（S9-1: バランス検証）

入力: `tuning.md`、`docs/balance/targets.md`、S8・S9 で実装したコードとデータ、`.gamekit/config.yaml` の `commands.balance_sim`。

1. **対象かを決める。** `tuning.md` が「調整値なし」、または「シミュレーション: 対象外」の機能は、`balance-report.md` を「対象外（理由: …）」にして 6 に進む。
2. **前提を確かめる。**
   - `$BAL params specs/<NNN>/tuning.md` の ERROR と WARN を 0 件にする（実装の後なので、まだないデータの WARN も残さない）。データの場所がずれていれば、`tuning.md` かデータを直す（コードに数値が直書きされていたら、データに移す）。
   - `commands.balance_sim` が空（`NO_SIM_COMMAND`）なら、§5 の手順で準備する。準備がこの機能の範囲を超える（エンジンに仕組みがまだない）ときは、止まって `000-game-foundation` か専用の機能での準備を提案する。自動モードでは、`balance-report.md` に「未検証（シミュレーションなし）」と書き、見直しの優先度を「高」にして記録して進む。
3. **実行して判定する。**

   ```bash
   $BAL run --feature <NNN>
   $BAL check --feature <NNN> --report specs/<NNN>/balance-check.md
   ```

4. **FAIL と MISSING を直す。** 1 件ごとに原因を考えてから直す。直す順は次のとおり。
   1. **測り方の誤り**（指標を出していない、シナリオの方針が仕様と違う、シードが固定されていない）→ シミュレーションを直す。MISSING の多くはこれである。
   2. **調整値の範囲内で合う** → データを直し、`tuning.md` の初期値を同じ値に更新する。
   3. **範囲を外れないと合わない、または目標値そのものが体験と食い違う** → 仕様の見直しである。`tuning.md` の範囲か targets.md の目標値を変え、理由を targets.md の「変更の記録」に書く。`docs/game/` の式や表から来た値なら、その文書も直す（steering の原則 6）。
   4. **式や仕組みの誤り** → コードを直し、テストを足す。

   直したら 3 に戻る。同じ ID の FAIL が 3 回直しても消えなければ、止まって判断を仰ぐ（自動モードでは §7）。
5. **基準値と比べる。** 基準値（`docs/balance/baseline/`）があれば `$BAL diff` を実行し、この機能で意図して動かした指標と、意図せず動いた指標（ほかの機能の目標値が崩れていないか）を分ける。`$BAL check`（`--feature` なし）で全体の FAIL がないことも確かめる。意図した変化だけなら、`$BAL baseline` で基準値を更新する。
6. **記録する。** [templates/balance-report.md](templates/balance-report.md) の様式で `specs/<NNN>/balance-report.md` を書く（最後の判定の表、直したこと、差分、残る懸念）。`balance-check.md` は消してよい（中身は report に貼る）。

呼び出し元（`gamekit-coding`）が `checkpoint <FEATURE_NAME> S9-1` を記録する。

> 💬 目標値や範囲を変える（仕様の見直し）ときは、推奨案を添えて質問する。データの範囲内の調整は質問せずに進め、report に書く。

## 5. シミュレーションの準備（setup）

シミュレーションは、ゲームの本物の処理を、画面なしで決まった方針のプレイヤーに遊ばせ、指標を JSON で出すプログラムである。

### 規則

- **ゲームの式を書き写さない。** ダメージ、価格、成長の計算は、ゲーム本体の関数を呼ぶ。シミュレーション側に同じ式を書くと、片方だけが直されて食い違う。
- **乱数はシミュレーションが作り、ゲームの処理に渡す。** シナリオのシードから乱数器を作る。ゲームの中心の処理（core）は、乱数器を引数で受け取る形にする（`000-game-foundation` の乱数とシード）。
- **プレイヤーの方針はシミュレーションに書く。** 「最短で進む」「いちばん安い装備を買う」「全部の選択肢を均等に試す」など、targets.md の「シナリオ」の表に書いた方針を、関数として書く。
- **テストから呼べる形にする。** 引数の配列を受け取って終了コードを返す関数を公開し、起動の処理はそれを呼ぶだけにする（e2e のテストでプロセスを起動しなくて済む）。
- **判定はシミュレーションに書かない。** 合否は targets.md と `balance.py check` が持つ。シミュレーションは測って書き出すだけにする（独自の門を持たせるなら、終了コードを分けて、その意味を `docs/architecture.md` に書く）。

### エンジンごとの雛形

| エンジン | 雛形 | `commands.balance_sim` の例 |
|---|---|---|
| Godot（GDScript） | [templates/balance_sim.gd](templates/balance_sim.gd) を `res://tools/balance_sim.gd` に | `godot --headless --path . --script res://tools/balance_sim.gd -- --scenario {scenario} --out {out}` |
| Godot（C#） | 同じ構成を C# のコンソール用のエントリー、または GDScript の雛形から C# のゲーム処理を呼ぶ形で | 同上、または `dotnet run --project tools/BalanceSim -- --scenario {scenario} --out {out}` |
| Web（TypeScript） | [templates/balance-sim.ts](templates/balance-sim.ts) を `tools/balance-sim.ts` に | `npx tsx tools/balance-sim.ts --scenario {scenario} --out {out}` |
| その他（Go のサーバーなど） | 同じ入出力（`--scenario`、`--out`、出力の JSON）のコマンドを用意する | `go run ./cmd/balancesim --scenario {scenario} --out {out}` |

手順:

1. `docs/architecture.md` のエンジン、`paths.data`、テストの方式を読む。
2. 雛形を置き、`SCENARIOS` を targets.md の「シナリオ」の表に合わせ、`simulate` からゲーム本体の処理を呼ぶ。まだ処理がなければ、指標を出さない空のシミュレーションにして、MISSING が出ることを確かめる。
3. `.gamekit/config.yaml` の `commands.balance_sim` を書く。`{scenario}` と `{out}` は `balance.py run` が置き換える。`{out}` には絶対パスが入る。
4. `$BAL run` → `$BAL check` が通る（終了コード 0 か、まだ指標のない行だけの MISSING）ことを確かめる。
5. 同じシナリオを 2 回実行して、出力が同じになることを確かめる（決定性）。
6. CI に載せるときは、`999-game-release` の CI のタスクに `balance.py run` と `check` を足す。

## 6. 単独の利用

- **check**: `$BAL targets` → `$BAL run`（`commands.balance_sim` があれば）→ `$BAL check [--feature]` の順に実行し、FAIL と MISSING を要約して、§4 の 4 の順で直し方の案を示す。直すのは、ユーザーが頼んだときだけにする。
- **baseline**: `$BAL run` の後に `$BAL check` が FAIL なしであることを確かめてから `$BAL baseline` を実行し、`docs(balance): 基準値を更新` でコミットしてよいかを確かめる。FAIL があるときは、基準値にしてよいかを先に確かめる。
- **diff**: `$BAL run` → `$BAL diff` を実行し、動いた指標ごとに、原因になった変更（`git log` と `git diff` のデータとコード）を挙げる。
- **tune**: 数値の調整だけの依頼（steering の行動規範）。依頼を目標値の言葉に直し（「序盤を楽に」→ BT-001 の上限に寄せる、など）、対象の調整値を `tuning.md` から探す。範囲内でデータを直し、`tuning.md` の初期値を更新し、`$BAL params` と `$BAL run` → `check` → `diff` で、狙った指標が動き、ほかの目標値が崩れていないことを確かめる。範囲を外れる、または目標値を変える依頼は、仕様の見直しとして `tuning.md`・targets.md の「変更の記録」まで直す。最後に `[人]` のプレイ確認を勧める。

## 7. 自動モード（`--auto`）

機能の工程から呼ばれたときは `gamekit-worktree` §6 に従い、自動で決めたことを `specs/<NNN>/auto-decisions.md` に記録する。

| 場面 | 自動モードでの動作 |
|---|---|
| spec の体験の狙い、初期値、範囲、目標値の幅 | `docs/game/` と参考作品から推奨案を作って採用する。根拠が推測だけの値は「仮」と書き、見直しの優先度を「高」にする |
| verify の FAIL（範囲内の調整で合う） | データを直して進む |
| verify の FAIL（目標値か範囲を変える必要がある） | 変えずに止まる（仕様の見直しは自動で行わない）。範囲指定の実行なら、その機能を飛ばす |
| シミュレーションがない | report を「未検証」にして進み、見直しの優先度を「高」にする |
| 基準値の更新 | 意図した変化だけのときに限り更新する。意図しない変化があれば更新せず、report に書く |

## 8. 規則

- 数値をコードに直書きしない。見つけたらデータに移し、`tuning.md` に足す。
- 目標値を、実測に合わせて後から緩めない。緩めるときは、体験の狙いから理由を書き、「変更の記録」に残す。
- シミュレーションの出力（`build/balance/`）はコミットしない。基準値（`docs/balance/baseline/`）と report はコミットする。
- 合否の判定を AI の目分量で代えない。`balance.py check` の結果を正とする。
- 応答と成果物は、プロジェクトの言語ルール（`.kiro/steering/language.md`）に従う。
