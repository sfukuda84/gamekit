extends SceneTree

## バランスのシミュレーション（gamekit-balance §5）。
##
## 使い方:
##   godot --headless --path . --script res://tools/balance_sim.gd -- --scenario early_game --out build/balance/early_game.json
##
## - 出力: {"scenario": String, "seed": int, "metrics": {指標: 数値}}（balance.py check が読む）
## - ⚠ ゲームの式を書き写さない。ダメージ・価格・成長の計算は、ゲーム本体（core）の関数を呼ぶ。
## - ⚠ 乱数器はここで作り、core には引数で渡す（同じシナリオとシードなら、何度実行しても同じ出力になる）。
## - ⚠ 合否の判定は書かない。判定は docs/balance/targets.md と balance.py check が持つ。

const EXIT_OK := 0
const EXIT_INVALID := 1  ## 引数の不正、知らないシナリオ、書き出しの失敗

## シナリオの定義。docs/balance/targets.md の「シナリオ」の表（方針・シード・打ち切り）と一致させる。
const SCENARIOS := {
	"early_game": {"seed": 1, "policy": "rush", "minutes": 60},
}


func _init() -> void:
	quit(run(OS.get_cmdline_user_args()))


## テストから直接呼べるよう、引数の配列を受け取って終了コードを返す。
static func run(argv: PackedStringArray) -> int:
	var opts := parse_args(argv)
	if opts.is_empty():
		return EXIT_INVALID
	var name: String = opts["scenario"]
	if not SCENARIOS.has(name):
		push_error("知らないシナリオです: %s" % name)
		return EXIT_INVALID
	var scenario: Dictionary = SCENARIOS[name]
	var rng := RandomNumberGenerator.new()
	rng.seed = int(scenario["seed"])
	var result := {"scenario": name, "seed": int(scenario["seed"]), "metrics": simulate(scenario, rng)}
	return write_json(opts["out"], result)


static func parse_args(argv: PackedStringArray) -> Dictionary:
	var opts := {"scenario": "", "out": ""}
	var i := 0
	while i < argv.size():
		var key := argv[i].trim_prefix("--")
		if opts.has(key) and i + 1 < argv.size():
			opts[key] = argv[i + 1]
			i += 2
		else:
			push_error("知らない引数です: %s" % argv[i])
			return {}
	if opts["scenario"] == "" or opts["out"] == "":
		push_error("--scenario と --out が必要です")
		return {}
	return opts


## 方針どおりにプレイヤーを動かし、指標を集める。ゲーム本体の処理を呼ぶ。
static func simulate(scenario: Dictionary, rng: RandomNumberGenerator) -> Dictionary:
	var metrics := {}
	# 例:
	# var state := GameCore.new_game(load_master_data(), rng)
	# var elapsed := 0.0
	# while elapsed < scenario["minutes"] * 60.0:
	#     elapsed += Policies.step(scenario["policy"], state, rng)
	#     if state.level >= 5 and not metrics.has("minutes_to_level_5"):
	#         metrics["minutes_to_level_5"] = elapsed / 60.0
	# metrics["gold_per_hour"] = state.gold / (elapsed / 3600.0)
	return metrics


static func write_json(path: String, data: Dictionary) -> int:
	var err := DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	if err != OK and err != ERR_ALREADY_EXISTS:
		push_error("出力のディレクトリを作れません: %s" % path.get_base_dir())
		return EXIT_INVALID
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		push_error("書き出せません: %s" % path)
		return EXIT_INVALID
	f.store_string(JSON.stringify(data, "  "))
	f.close()
	return EXIT_OK
