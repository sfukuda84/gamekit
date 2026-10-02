/**
 * バランスのシミュレーション（gamekit-balance §5）。
 *
 * 使い方:
 *   npx tsx tools/balance-sim.ts --scenario early_game --out build/balance/early_game.json
 *
 * - 出力: {"scenario": string, "seed": number, "metrics": {指標: 数値}}（balance.py check が読む）
 * - ⚠ ゲームの式を書き写さない。ダメージ・価格・成長の計算は、ゲーム本体（src/core など）の関数を import して呼ぶ。
 * - ⚠ 乱数はここでシードから作り、core には引数で渡す（Math.random を core で使わない）。
 * - ⚠ 合否の判定は書かない。判定は docs/balance/targets.md と balance.py check が持つ。
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { pathToFileURL } from "node:url";

type Rng = () => number;
type Metrics = Record<string, number>;
interface Scenario {
  seed: number;
  policy: string;
  minutes: number;
}

/** シナリオの定義。docs/balance/targets.md の「シナリオ」の表（方針・シード・打ち切り）と一致させる。 */
export const SCENARIOS: Record<string, Scenario> = {
  early_game: { seed: 1, policy: "rush", minutes: 60 },
};

/** シード付きの乱数（mulberry32）。core が別の乱数器を持つなら、そちらを使う。 */
export function makeRng(seed: number): Rng {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** 方針どおりにプレイヤーを動かし、指標を集める。ゲーム本体の処理を呼ぶ。 */
export function simulate(scenario: Scenario, rng: Rng): Metrics {
  const metrics: Metrics = {};
  // 例:
  // const state = newGame(masterData, rng);
  // let elapsed = 0;
  // while (elapsed < scenario.minutes * 60) {
  //   elapsed += policies[scenario.policy](state, rng);
  //   if (state.level >= 5 && metrics.minutes_to_level_5 === undefined) metrics.minutes_to_level_5 = elapsed / 60;
  // }
  // metrics.gold_per_hour = state.gold / (elapsed / 3600);
  void scenario;
  void rng;
  return metrics;
}

/** テストから直接呼べるよう、引数の配列を受け取って終了コードを返す。 */
export function run(argv: string[]): number {
  const opts: Record<string, string> = {};
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i]?.replace(/^--/, "");
    if ((key !== "scenario" && key !== "out") || argv[i + 1] === undefined) {
      console.error(`知らない引数です: ${argv[i]}`);
      return 1;
    }
    opts[key] = argv[i + 1];
  }
  const scenario = SCENARIOS[opts.scenario ?? ""];
  if (!scenario || !opts.out) {
    console.error("--scenario（定義済みの名前）と --out が必要です");
    return 1;
  }
  const result = { scenario: opts.scenario, seed: scenario.seed, metrics: simulate(scenario, makeRng(scenario.seed)) };
  mkdirSync(dirname(opts.out), { recursive: true });
  writeFileSync(opts.out, JSON.stringify(result, null, 2));
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  process.exit(run(process.argv.slice(2)));
}
