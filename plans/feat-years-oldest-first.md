# all.html の年の並びを古い順にする

Issue: https://github.com/isamu/sori/issues/6

## 目的

「2011 年以降の全部」として時系列に読めるよう、草の年を古い順に並べる。先頭が 2011 年（3.11 から）になり、取りかけの今年は最後に来る。

## 変更

- `scripts/build_pages.py`: `years_covered` の並びをそのまま使う（`reversed` をやめる）
- `scripts/by_year.py`: `event_list` を古い順にし、下部の出来事一覧も年の並びとそろえる。テストの期待値を合わせる
- 順位付け（1 位 2 位）と年換算は並びに依存しないので変更なし
- `site/all.html` を再生成し、Playwright で節の順と一覧の順を確認する

## 範囲外

- description / OGP の文言、index.html
