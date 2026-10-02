# 機能の一覧

**<ゲーム名>（<1 文のピッチ>）の機能概要**を 1 機能 1 ファイルで置く場所。
`/speckit-specify` に渡す入力素材であり、詳細な要件定義やタスク分解は spec 化（`specs/`）の段階で詰める。

## 使い方

1. 着手する機能のファイルを読む
2. `gamekit-feature` / `gamekit-all` に想定順序の番号を渡す（末尾の「`/speckit-specify` に渡す記述案」が S2 の入力になる）
3. 状態は、`gamekit-feature` / `gamekit-all` が S2 で `spec化済み（specs/NNN-<slug>）`、S11 で `完了`（`[人]` のタスクが残っていれば `人の作業待ち（specs/NNN-<slug>）`）に自動で更新する。人のタスクを片付けた後は `gamekit-worktree` の `sync-status` で `完了` にする。手で進めるときは、ファイルの状態と下の一覧表の状態欄を同時に直す
4. **以降その機能の正本は `specs/` 側。** このファイルは追記せず、素材・履歴として残す

## 運用ルール

- **ここは進捗管理の場所ではない。** 進捗の正本は `specs/` 配下の spec と tasks
- 記述は**広く浅く**。クラス名・データの項目・具体的な数値は書かず、`/speckit-clarify`、調整仕様（S4-2 の `tuning.md`）、`/speckit-plan` で決める
- 根拠は `docs/concept/`（とくに [../concept/premises.md](../concept/premises.md) の GP）と `docs/game/` に置く。仕分けで決めた前提は [premises.md](./premises.md) に追記する
- 区分は **垂直スライス**（最初に遊べる形にする最小の組み合わせ）→ **MVP**（最初に出すまでに要るもの）→ **拡張** の順。前の区分の機能は、後の区分の機能に依存しない
- ファイル名は `NNN-<slug>.md`。`NNN` は想定順序で、`specs/NNN-<slug>` とブランチ名にそのまま対応する。`000` は共通基盤（`gamekit-foundation`）、`999` はリリース基盤（`gamekit-nfr`）の予約番号
- 機能を追加・分割したら、同じ様式でファイルを足し、**一覧表に行を足す**。**番号は振り直さない**。新しい機能は既存の最大値の次から振る
- **区分・状態・依存欄は各ファイルのヘッダ行をそのまま写す**（依存は `001-core-combat` のような完全名）。表記を変えると検証で不一致になる

## メタ文書（機能ファイルではない）

| ファイル | 何が書いてあるか |
|---|---|
| [../concept/premises.md](../concept/premises.md) | **ゲームの前提の正本。** GP1〜GP12 と、壁打ちの質疑記録 |
| [premises.md](./premises.md) | **仕分けの前提。** 入力の仕分け、基盤の候補（000・999 に渡すもの）、仕分けで追加した質疑 |
| [spec_order.md](./spec_order.md) | **着手順序の正本。** 区分ごとの段階分け、被参照数、依存グラフ |
| [../concept/backlog.md](../concept/backlog.md) | **機能候補の正本。** まだ機能化していない候補と却下した候補。`gamekit-features --backlog <ID>` で機能化する |

## 一覧

**# は想定順序（採番）。着手順序は [spec_order.md](./spec_order.md) が正本。**

| # | 機能 | 区分 | 状態 | 依存 | 一言 |
|---|---|---|---|---|---|
| 1 | [<機能名>](./001-<slug>.md) | 垂直スライス | 未着手 | — | <一言> |

**件数**: 機能ファイル **<N> 件**（垂直スライス <a> / MVP <b> / 拡張 <c>）。

## 検証

```bash
python3 <validate.py のパス> docs/feature
```
