# 担当への依頼文の雛形

`gamekit-worktree` §4「親と担当の役割」で、親（実行中のエージェント）がサブエージェント（担当）に作業を任せるときの依頼文の雛形。`<…>` を埋めて使う。farm（Godot .NET のゲーム）で 000・001 を通したときの依頼文を元にしている。

共通の決め事:

- **渡すもの**: 作業場所（worktree の絶対パスとブランチ）、範囲（ステップ・Phase・指摘の ID）、守る規則（憲章、steering、`tuning.md`、決めたことの台帳）、検証のコマンド、報告の形。
- **渡さないもの**: 実装の経緯や親の見立て（とくにレビュー担当には「たぶん問題ない」を渡さない）。
- **させないこと**: `checkpoint`、マージ、push、ユーザーへの質問、範囲の外の編集、破壊的な git の操作。
- **報告の形**: 件数、決めたこと（`decisions.md` に書いた番号）、検証の結果、止まったことがあればその理由だけ。差分や全文を貼らせない（親の文脈を守る）。
- 親は報告を受けたら、検証のコマンドを自分でもう一度実行し、疑問のある箇所だけファイルの行を開いて裏を取る。

## 1. 実装担当（S8・S9）

```text
あなたは <FEATURE_NAME> の S8（実装）の第 <N> 弾の担当。worktree <WORKTREE_DIR>（ブランチ feature/<FEATURE_NAME>。前の弾はコミット <hash> まで）。
specs/<FEATURE_NAME>/tasks.md の <Phase の範囲（例: Phase 2 と Phase 3）> を実装する。
- 手順: speckit-implement と gamekit-coding の S8 の規則。設計は specs/<FEATURE_NAME>/ の spec・plan・data-model・contracts・tuning・ui と、
  憲章 .specify/memory/constitution.md を厳守する（<とくに守る原則。例: 数値はデータに置く、決定性>）。テストを先に書く。
- 数値は <paths.data> のデータに置き、コードに直書きしない。
- 区切りごとに <commands.test>、<commands.lint>、<品質ゲートのスクリプト> を通す。
- tasks.md の完了したタスクを [x] にする。仕様の隙間は推奨案で決め、specs/<FEATURE_NAME>/decisions.md に続き番号で記録する
  （# | 決めたこと | 理由 | 反映先 | 確認の結果。確認の結果は空欄のまま。親がユーザーに確かめる）。
- 普通のコミット（trailer なし）は区切りでしてよい。checkpoint・マージ・push・ユーザーへの質問はしない。
  範囲の外の Phase には手を付けない（範囲の完了に必要な最小限を除く）。
終わったら、完了したタスクの範囲、テストとゲートの結果、decisions.md に足した番号と要点だけを短く報告する。
```

S9（収束）の担当も同じ形にし、範囲を「speckit-converge と gamekit-coding の S9 の手順で、コードとデータを spec・plan・tasks・contracts・憲章と照合し、ギャップを `## Phase N: Convergence` として足して実装し、✅ Converged まで繰り返す」にする。

## 2. レビュー担当（S10・S11、軸ごと）

軸ごとに 1 人ずつ、文脈を持たない担当（Claude Code では general-purpose のサブエージェント）にする。並行に走らせてよい。

```text
Independent reviewer, round <1|2>, axis "<Standards|Spec|Balance|Feel|Originality>" only. Read-only (do NOT edit or commit).
Worktree: <WORKTREE_DIR>. Diff: `git diff main...HEAD`<2 回目: , primary `git diff <S10 の前のコミット>..HEAD`>.
Criteria: section "### 軸 <A〜E>" in <skills>/gamekit-review/SKILL.md and its "予算と打ち切り".
Baselines: <軸ごとの基準の文書。例: Spec → specs/<FEATURE_NAME>/{spec,ui,tuning,plan,data-model,contracts}, constitution, pillars>.
<2 回目: Read specs/<FEATURE_NAME>/reviews/review-1.md first; verify the R1 fixes and look for regressions. Round-2 lens: <軸ごとのレンズ>.>
Stance: look for reasons to reject. Every finding needs evidence (file:line, doc location, URL for web checks).
Budget: at most 8 findings, CRITICAL/HIGH first; list remaining LOW items in one line each under "backlog".
Output in Japanese, IDs R<round>-<S|P|B|F|O>01..., form:
### R1-S01: [CRITICAL/HIGH/MEDIUM/LOW] 題
- **対象**: file#Lx-Ly
- **根拠**: ...
- **直し方**: ...（体感の判定が要るものは「プレイ確認へ」）
Then a one-line count. Under ~600 words.
```

- Balance 軸の担当には、シミュレーションを worktree の外の写しで回させる（`<commands.balance_sim>` と種の範囲を書く）。数値の妥当性は実測で示させる。
- Originality 軸の担当は Web 検索を使える担当にする。「問題なし」と言い切らせない。

## 3. 修正担当（S10・S11 の修正）

```text
あなたは <FEATURE_NAME> の S<10|11>（レビュー <1|2> 回目）の修正担当。worktree <WORKTREE_DIR>（<直前の checkpoint のコミット>）。
次の採否の表のとおりに対応する（親が裏を取って決めた）:
| ID | 採否 | 直し方（親の決定） |
|---|---|---|
| R1-S01 | 採用 | <…> |
| R1-F08 | プレイ確認へ | tasks.md の [人] のプレイ確認の観点に足す |
| R1-O01 | 保留 | <申し送り先> に記録する |
- 重複（<ID=ID>）は 1 回で直す。ユーザーの決定: <あれば>。
- 仕様・計画を変えたら spec.md（Clarifications に `### Session <日付> (Review <n>)`）・plan・contracts・tuning・tasks にも反映する。
  tasks.md の末尾に `## Phase N: Review <n>` として直したタスクを [x] で記録する。LOW で直さないものは reviews/backlog.md に送る。
- specs/<FEATURE_NAME>/reviews/review-<n>.md を gamekit-review §5 の様式で書く（要約の表、指摘ごとの採否、テストの結果）。
- 検証: <commands.test>、<ゲート>、<balance.py check>、<run_headless>。普通のコミットはしてよい。checkpoint は親。
- 止める条件: <例: ユーザーの決定どおりに直しても目標値が PASS しないとき（理由と実測を報告する）>。
終わったら、直した件数、指摘の案から変えたもの、検証の結果だけを短く報告する。
```
