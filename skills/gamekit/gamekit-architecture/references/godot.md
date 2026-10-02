# Godot 4 の定石（gamekit 向け）

`gamekit-architecture` が構成を決めるとき、各機能の `plan.md` と実装が参照する。事実は 2026-10 時点で、Godot 4.7 の公式文書を確かめたものである。**実行のたびに、使うバージョンの公式文書で確かめる。** 「確かめる」と書いた項目は、まだ確かめていない。

## コマンドライン（エディタを開かずに回す）

出典: [Command line tutorial（Godot 4.7）](https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html)（参照日 2026-10-03）

| オプション | 動作 | gamekit での使い道 |
|---|---|---|
| `--headless` | `--display-driver headless --audio-driver Dummy` と同じ。画面と音を出さない | テスト、ヘッドレス実行、シミュレーション |
| `--path <dir>` | `project.godot` のあるディレクトリを指定する | リポジトリのルートから実行するとき |
| `--script <path>`（`-s`） | GDScript を実行する（プロジェクトからの相対パスか絶対パス） | バランスのシミュレーション、テストの起動 |
| `--check-only` | 構文の誤りだけを調べて終わる（多くは `--script` と組み合わせる） | リンターの代わりの簡易な確認 |
| `--quit` | 最初の反復の後に終わる | 起動できるかの確認 |
| `--quit-after <N>` | N 回の反復の後に終わる（0 で無効） | `run_headless`（数フレーム回してエラーがないか） |
| `--import` | エディタを起動し、リソースのインポートを待って終わる | CI で最初にインポートを済ませる |
| `--export-release <preset> <path>` | `export_presets.cfg` のプリセット名で、リリース版を書き出す | `build` |
| `--export-debug <preset> <path>` | デバッグのテンプレートで書き出す（`--import` を含む） | 確認用のビルド |
| `--export-pack <preset> <path>` | ゲームのパック（PCK か ZIP）だけを書き出す | 更新の配布 |
| `--fixed-fps <fps>`、`--write-movie <file>` | 固定のフレームレートで、映像を書き出す | 手触りの確認用の録画（`[人]` が見る） |

- `run_headless` の例: `godot --headless --path game --quit-after 120`
- `balance_sim` の例: `godot --headless --path game --script res://tools/balance_sim.gd -- --scenario {scenario} --out {out}`（`--` の後ろの引数は `OS.get_cmdline_user_args()` で読む。確かめる）
- 書き出しには、エンジンのバージョンに合った書き出しのテンプレートを入れておく必要がある（`[人]` の作業になりやすい）。

## テスト

| フレームワーク | 言語 | コマンドラインでの実行 | 出典 |
|---|---|---|---|
| GUT | GDScript | `godot --headless -s addons/gut/gut_cmdln.gd -d --path "$PWD" -gdir=res://tests -gexit`（`-gtest=<ファイル>` で 1 本だけ） | [GUT Command Line](https://gut.readthedocs.io/en/latest/Command-Line.html)（参照日 2026-10-03）。Godot 4 に対応する版（9.x 系）を使う。確かめる |
| gdUnit4 | GDScript / C# | 同梱の `addons/gdUnit4/runtest.sh -a res://tests`（環境変数 `GODOT_BIN` にエンジンのパス） | 確かめる |
| gdUnit4Net / xUnit など | C# | `dotnet test`（ロジックをエンジンから切り離したライブラリにすれば、普通の .NET のテストで回せる） | 確かめる |

- ロジック（ダメージの計算、経済、成長曲線）は、ノードに依存しないクラス（GDScript なら `RefCounted` を継承したクラス、C# なら普通のクラス）に置くと、テストとシミュレーションから直接呼べる。
- シーンの結合テストは遅く壊れやすいので、数を絞る。

## C#（Godot .NET）の注意

- .NET 版のエディタと .NET SDK が要る。
- **Web には書き出せない**（2026-09 時点の Godot 4.7。早くても 4.8 の見込みと言われている）。出典: [Godot Forum](https://forum.godotengine.org/t/is-there-an-update-on-exporting-c-projects-to-web/128821)、[Current state of C# platform support in Godot 4.2](https://godotengine.org/article/platform-state-in-csharp-for-godot-4-2/)（参照日 2026-10-03）。Web に出すなら GDScript にする。
- モバイル（iOS、Android）への書き出しの状態は、使うバージョンで確かめる。
- NativeAOT などの書き出しの設定は、端末ごとに確かめる（farm で `PublishAot` を検証した記録がある）。

## データ

| 形式 | 長所 | 短所 |
|---|---|---|
| JSON（`res://data/*.json`） | テキストで差分が見やすい。`gamekit-balance params` が JSON Pointer で確かめられる。Node や Python のツールでも読める | 型がない。スキーマ（JSON Schema）か読み込み時の検証を別に作る |
| `.tres`（Resource） | エディタのインスペクタで編集できる。型がある | `gamekit-balance params` は存在だけを確かめる（中身は読まない） |
| CSV | 表計算ソフトで編集できる | 入れ子を表せない |

- 既定は JSON。エディタで編集したい項目だけ `.tres` にする場合は、その範囲を `docs/architecture.md` に書く。
- 読み込みは、起動時に 1 か所でまとめて行い、型と範囲を検証する（000 の要求）。

## シーンとリソースをテキストで書くとき

- `.tscn`・`.tres` はテキストの形式で、エージェントが直接書ける。ただし `uid://` と外部リソースの `id` の整合を壊しやすい。新しいシーンは、なるべく小さく、スクリプトからノードを組む形にする。
- 書いた後は `godot --headless --path <dir> --import` か `--quit` で読み込めることを確かめる。
- インポートの設定（画像のフィルタ、音のループ）は `.import` ファイルに入る。エディタで決めるなら `[人]` のタスクにする。

## 決定性

- 乱数は `RandomNumberGenerator` を 1 つのシードで作って持ち回り、グローバルの `randi()` などを使わない（シミュレーションで同じ結果にするため）。
- 物理と時間は `_physics_process` の固定のタイムステップに乗せる。シミュレーションでは描画の `delta` に依存しない。

## 確かめること（構成を決めるとき）

- 使う安定版のバージョンと、書き出しのテンプレートの入手方法
- 対象の端末（Steam、iOS、Android、Web、家庭用ゲーム機）への書き出しの条件。家庭用ゲーム機は公式には書き出せず、各社の許諾と移植の業者が要る
- テストのフレームワークの、そのバージョンへの対応
- CI でエンジンを入れる方法（公式のバイナリ、コンテナのイメージ）
