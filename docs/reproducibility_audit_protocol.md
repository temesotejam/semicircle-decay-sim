# Model B reproducibility audit protocol

## 目的

V62をさらに調整する前に、受動自由減衰の基準モデルを実測で固定する。

この監査では、同一の同期済みrunから同一のイベント表を作り、以下を明確に分離して評価する。

- **Model A**: 完全円（R=150 mm）を仮定した従来モデル
- **Model B**: STEPから得た中央10 mm欠損を含む剛体piecewise形状モデル
- **経験map**: 実機校正で用いている半周期振幅map（比例 `rA` またはアフィン `rA+c`）

経験mapはModel Bの代用ではない。形状モデルとは独立した実測ベースラインとして扱う。

## STEP由来で固定する項目

現行 `model/rocker_geometry.py` の形状パラメータを正本とする。

- 円弧半径 `R = 150 mm`
- 内側端 `|X| = 5 mm`
- 外側端 `|X| = 45 mm`
- 中央欠損幅 `10 mm`
- 内側端支点 -> 円弧転がり切替 `theta_inner = asin(5/150) = 1.910213 deg`
- 円弧外側限界 `theta_outer = asin(45/150) = 17.457603 deg`

この監査ではCADの密度・質量特性は使用しない。質量・重心・有効慣性は実測由来の値または実測データから同定する。

## 同じrunから作るイベント表

1行を「前ピーク -> ゼロクロス -> 次ピーク」の1半周期イベントとする。

最低限必要な列:

```text
run_id,event_id,prev_peak_side,prev_peak_deg,zero_cross_rate_dps,next_peak_deg
```

- `prev_peak_side`: `-1` または `+1`
- `prev_peak_deg`: 符号付きでも絶対値でも可。side列を優先する
- `zero_cross_rate_dps`: 符号付きでも可。評価には絶対値を使う
- `next_peak_deg`: 経験map評価に使用。空欄ならModel A/Bのゼロクロス監査だけ実行可能

イベント抽出規則そのものも固定する。V61/V62で抽出閾値を変えない。

## Model A/Bの再現性監査

各前ピーク側ごとに、

```text
omega_zero ~= sqrt(2 * DeltaU(A_prev) / J_side)
```

の `J_side` を1個だけフィットする。

- Model Aは完全円の `DeltaU_A`
- Model BはSTEP piecewise形状の `DeltaU_B`

まず**同一run内フィット**で過去文書のRMSEを再現する。これは過去結果の再現確認であり、汎化性能の証明ではない。

次に、runを跨いで

- 1 runで同定 -> 別runで評価
- 初期振幅帯を分けて同定 -> 別振幅帯で評価

を行い、Model Bの物理的な移植性を確認する。

出力にはin-sample RMSEだけでなくLOOCV RMSEも残す。

## 経験mapの監査

実機側の自由減衰校正と同様に、各前ピーク側について

```text
A_next = r * A_prev
```

と

```text
A_next = r * A_prev + c
```

を候補にする。

選択条件:

1. 半周期mapが正の単調増加
2. 実測 `A_prev` 支持範囲内のみ使用
3. 両側mapを合成した同側full-cycle mapが、その合成可能範囲で `0 < F(A) < A`
4. 条件を満たす候補のうちLOOCV RMSEが小さい組を選ぶ
5. 支持範囲外へ外挿しない

## 指標を混ぜない

Model A/Bの基本RMSEは**ゼロクロス角速度 [deg/s]**を評価する。

経験mapの基本RMSEは**次ピーク振幅 [deg]**を評価する。

同じrun・同じイベント表を使うが、この2種類のRMSEの数値を直接比較して「どのモデルが一番良い」と順位付けしてはいけない。

Model A/Bで次ピークまで比較する場合は、別途損失モデルを明示的に追加し、その時点で初めて同じ出力変数上で比較する。

## 現在の文書値について

`docs/2026-08-24_geometry_audit.md` にはV61 run 2について、完全円からSTEP形状へ変更するとゼロクロスRMSEが大きく低下したという結果が記録されている。

ただし現時点の `semicircle-decay-sim` には、そのRMSEを生成したV61イベント表が保存されていない。

したがって現在の文書値は**再現対象**であり、まだこのリポジトリだけで再計算可能な確定値ではない。

第1段階の完了条件は、V61/V62の元イベントCSVを追加し、

```bash
python -m analysis.audit_free_decay data/<events>.csv --out-dir audit/<run>
```

だけでRMSE・`J_side`・接触モード・経験map支持範囲を再生成できる状態にすること。

## V63へ渡す条件

V63は制御変更ではなくshadow loggingのみとする。

Model B監査で定義が固定した後に、最低限以下を並列ログへ追加する。

- `contact_mode_geom`
- Model A/Bの位置エネルギー
- `J_eff(theta)` または、まずは監査で採用した `J_side` とその適用範囲
- Model Bのゼロクロス速度予測
- Model Bの次ピーク予測（損失モデル確定後）
- `I0`
- 実効Q
- パルス後経過時間
- 取得可能ならwheel速度またはwheel角運動量のproxy

固定Q、既存H/C/rateゲート、制御指令はこの段階では変更しない。
