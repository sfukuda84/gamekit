# Web（TypeScript）の定石（gamekit 向け）

`gamekit-architecture` が構成を決めるとき、各機能の `plan.md` と実装が参照する。事実は 2026-10 時点のもの。**実行のたびに、使うバージョンの公式文書で確かめる。** 「確かめる」と書いた項目は、まだ確かめていない。

## 構成の例

| 層 | 例 | 注意 |
|---|---|---|
| ビルド | Vite | `npm run build` で `dist/` に書き出す |
| 描画 | Canvas 2D / PixiJS / Phaser / React（UI が中心のゲーム） | 版と API は確かめる。UI の多い経営シムは React などの UI ライブラリで十分なことがある（trade の例） |
| ロジック | 描画に依存しない TypeScript のモジュール（`src/game/`） | テストとシミュレーションから直接呼ぶ |
| データ | `src/data/*.json`（または `*.ts`） | JSON なら `gamekit-balance params` が確かめられる。`*.ts` は存在だけを確かめる |
| セーブ | `localStorage` / IndexedDB | バージョン番号とマイグレーションを持つ。容量の上限はブラウザで違う（確かめる） |
| テスト | Vitest | `vitest run` は監視モードに入らず 1 回だけ実行して終わる。`vitest` だけだと、対話的な端末では監視モードに入る。出典: [Vitest CLI](https://vitest.dev/guide/cli)（参照日 2026-10-03。v5 系） |
| 画面のテスト | Playwright | 入力と表示の結合テスト。数を絞る |
| リンター | ESLint、`tsc --noEmit` | 型の確認を `lint` に含める |

## コマンドの例（`.gamekit/config.yaml` の `commands`）

| キー | 例 |
|---|---|
| `test` | `npx vitest run` |
| `lint` | `npx eslint . && npx tsc --noEmit` |
| `build` | `npm run build` |
| `run_headless` | `npx vitest run tests/smoke`（ロジックを数千フレーム回して例外が出ないことを確かめるテストを置く）。画面まで確かめるなら Playwright |
| `balance_sim` | `npx tsx tools/balance-sim.ts --scenario {scenario} --out {out}`（`tsx` を使うか、ビルドした JS を `node` で実行する。確かめる） |

## 決定性

- `Math.random()` を使わず、シードを取る乱数の生成器（mulberry32、xoshiro など）を 1 つ作って持ち回る。
- ゲームの時間は `requestAnimationFrame` の経過時間ではなく、固定のタイムステップで進める。シミュレーションでは描画を呼ばない。

## 配布

- 自分のサーバー、itch.io、Steam（Electron や Tauri で包む）など。各ストアの条件と手数料は確かめる。
- ブラウザの自動再生の制限（音は利用者の操作の後でないと鳴らない）を、`FEEL.md` の音の設計に入れる。

## 確かめること（構成を決めるとき）

- 描画ライブラリの版と、対象のブラウザ・端末での性能
- セーブの容量の上限と、消える条件（プライベートブラウズ、ストレージの退避）
- Steam などに出す場合の包み方（Electron / Tauri）と、その費用・ライセンス
- サーバーがある場合（例: Go + WebSocket の 4x）、サーバーのテストとシミュレーションの分け方（`engine: other` として `commands` を埋める）
