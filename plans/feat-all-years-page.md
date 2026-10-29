# all.html: 2011 年以降の全期間を暦年ごとの草で見せる

Issue: https://github.com/isamu/sori/issues/1

## 目的

`site/index.html` は総理ごとの就任 1 年目。それとは別に、官邸ログに収録のある 2011-03-11 以降を暦年ごとに 1 枚の草として並べた `site/all.html` を作る。

## データ

- 各総理の残りの在任期間を `fetch_days.py <pm> <start> <end>` で取り込む。1 本だけ、毎分 50 件以内。未取得の範囲は `dousei/<pm>/` にない日付で分かる
- `extract_days.py <pm>` で `dousei/` に落とす。`parsed/` は使わず、`build_pages.py all` が `dousei/` を直接読む（全期間の中間ファイルを git に積まないため）

## 生成

- `scripts/by_year.py`: 暦年への振り分け、年ごとの有効範囲（2011 年は収録開始日から、今年は取得日まで）、年ごとの在任区間。ファイルも現在日時も受け取る純粋関数。`test/test_by_year.py` で検証
- `scripts/build_pages.py all`: `templates/vue_all_template.html` に埋めて `site/all.html` を書く
- テンプレートは index と同じ決め事（1 commit = 公務 1 時間、色の段階、外遊日の扱い）。年ごとに草・在任バー・5 タイル。1 位 2 位は 1 月〜12 月そろった年の中で
- 1 月〜12 月そろっていない年（2011 年と今年）には、取得済みの日数から 1 年分に引き伸ばした年換算の値を commit 数と数えるタイル（稼働日・休養日・外遊・面会）に添える。最長連続稼働は引き伸ばさない。年の日数は `by_year.days_in_year`（うるう年対応）、引き伸ばしはテンプレートの `annualized`

## 範囲外

- `index.html` からのリンク（別途相談）
- 分類別の集計
- index / multi テンプレートと重複する JS の共通化（単一 HTML の方針を崩すので別途）
