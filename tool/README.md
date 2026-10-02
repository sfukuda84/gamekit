# new-gamekit-project

[gamekit](https://github.com/sfukuda84/gamekit) のプロジェクトを作り、Claude Code で立ち上げ（`gamekit-bootstrap`）を始めるコマンド。既存のプロジェクトへの取り込みと、作成済みのプロジェクトの更新もできる。macOS、Linux、Windows で動く（Python 3.9 以上、依存なし）。

## 導入と更新

```bash
uv tool install "git+https://github.com/sfukuda84/gamekit#subdirectory=tool"
uv tool upgrade new-gamekit-project
```

## プロジェクトを作る・取り込む

```bash
new-gamekit-project <ディレクトリ> [--title <仮題>] [-m "1 文のコンセプト"] [--auto | --oneshot] [--adopt] [--no-launch]
```

| オプション | 内容 |
|---|---|
| `--title` | 仮題 |
| `--engine` | エンジンの見込み（`godot` / `web` / `other`。`.gamekit/config.yaml` の `engine`） |
| `--language` | 言語（`gdscript` / `csharp` / `typescript` など） |
| `-m`, `--message` | 1 文のコンセプト。省略すると対話で入力を受ける。空なら起動せずに手順だけを表示する |
| `--auto` / `--oneshot` | 立ち上げを質問なしで進める / 最初に一度だけ質問して進める |
| `--adopt` | 既存のプロジェクトに取り込む（既存のファイルは上書きしない。エージェントは起動しない。続きは `/gamekit-bootstrap --adopt`） |
| `--no-launch` | エージェントを起動せず、手順だけを表示する |
| `--ref` / `--repo` | 取得する scaffold のブランチまたはタグ / リポジトリ（環境変数 `GAMEKIT_SCAFFOLD_REF` / `GAMEKIT_SCAFFOLD_REPO`） |
| `--scaffold` | GitHub から取得せず、手元の scaffold を使う |
| `--link` | スキルを scaffold へのシンボリックリンクにする（`--scaffold` を使うときだけ） |

作ったプロジェクトには、使った scaffold の版を `.gamekit/scaffold.json` に記録する。

## 作成済みのプロジェクトを更新する

```bash
new-gamekit-project update [プロジェクトのディレクトリ] [--dry-run] [--ref <ブランチまたはタグ>] [--repo <リポジトリ>] [--scaffold <ディレクトリ>]
```

scaffold の持ち物（スキル、ルールなど）だけを取り込み、1 つのコミットにする（`main` で、未コミットの変更がないときだけ動く。既定のブランチが別なら環境変数 `GAMEKIT_MAIN_BRANCH`）。

- scaffold の全履歴のどれかの版と一致するファイルは、新しい版で上書きする。scaffold から消えたファイルは削除する。
- どの版とも一致しないファイルは手で直したものとみなして上書きせず、新しい版を `.scaffold-new/` に置く。比べるときは `git diff --no-index <ファイル> .scaffold-new/<ファイル>`。
- 取り込み（`--adopt`）で残した同名のスキルや、追跡していない既存のファイルには触らない。
- スキルを scaffold へのリンクで置いたプロジェクトは、スキルを更新しない（すでに最新）。
- プロジェクトの成果物（設定、本文、docs/ など）は対象外。

## テスト

```bash
cd tool && python3 -m unittest discover -s tests
```
