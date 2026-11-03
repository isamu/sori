# 棒グラフに縦軸の目盛りを付ける

Issue: https://github.com/isamu/sori/issues/16

## 目的

`site/tedori.html` の積み上げ棒グラフに縦軸の数字がなく、何の量か読めない。

## 決めたこと

- 共有の部品 `templates/stacked_columns.js` の左に縦軸を置き、0・点線（`gridlines`）の位置・上端（`max`）に `unit` 付きの数字を出す。部品を共有している `zaisei.html` の棒グラフにも付く
- 上端と下端の数字はグラフの内側に寄せる（小さなグラフで、上にある最初の年と最新年の数字とぶつからないように）
- 縦軸の幅は単位が 1 文字（%）なら狭く、2 文字以上（万円）なら広く。`zaisei.html` の最初の年と最新年の数字の行は、その幅だけ右に寄せて棒にそろえる

## 確かめ方

- 両ページを画面で見る。375px 幅で横にはみ出さない
- `python3 -m unittest discover -s test -p 'test_*.py'`（ページに埋めるデータは変わらない）
