# sori — 首相動静の元データと「草」ページ

歴代総理の首相動静（分単位の行動記録）を官邸ログから取り込み、公務 1 時間 = 1 commit として GitHub の草に描くプロジェクト。
この CLAUDE.md が引き継ぎ資料。README はない。

## 置き場所

| パス | 中身 |
|---|---|
| `dousei/<pm>/<YYYY-MM-DD>.json` | **git に入れるのはここだけ。** 動静の事実部分（時刻・内容・場所・分類・時間配分の数値）。官邸ログの要約文やページの見た目は入れない |
| `raw/html/<pm>/<YYYY-MM-DD>.html.gz` | 官邸ログ日別ページの HTML そのまま（gzip）。**手元だけ、`.gitignore` 済み。** 他人のページの複製なので公開リポジトリに入れない |
| `parsed/pms-first-year.json` | 総理ごとに就任日から 365 日分を `dousei/` からまとめたもの |
| `templates/` | Vue 3 + Tailwind v4（どちらも CDN）の単一 HTML テンプレート。`__DATA__` に JSON を埋める。高市単独版は削除済み（タイトルや OGP に個人名を出さず「歴代」で通す方針） |
| `site/index.html` | 公開用トップ「総理の１年」。歴代 1 年目の草と各総理の統計行、決め方だけ（比較表・commit log なし、時系列データも埋めない）。SEO/OGP/JSON-LD 入り。`build_pages.py index` で生成 |
| `site/og.png` | OGP 画像（1986×938）。ユーザーが用意した草のスクリーンショット。上書きしない |
| `site/og-grass.png` | `build_og.py` が作る代替の OGP 画像（1200×630、7 人分の草を 2 列）。使うなら index の og:image を差し替える |
| `site/pm-first-year-grass.html` | 歴代総理 1 年目の草を 1 枚に並べたもの |
| `scripts/` | 取り込み → 解析 → 生成 |

`<pm>` は `config.py` の `PMS` の id: hatoyama / kan / noda / abe / suga / kishida / ishiba / takaichi。

## パイプライン

```sh
cd scripts
python3 fetch_days.py <pm>            # 就任日から 365 日を raw/html/<pm>/ へ（取得済みは飛ばす）
python3 fetch_days.py takaichi 2026-10-21 2026-12-31   # 範囲指定（現職の追加取り込み）
python3 extract_days.py <pm>          # raw/html/<pm>/ → dousei/<pm>/<date>.json（事実部分だけ）
python3 parse_all.py                  # dousei/ → parsed/pms-first-year.json
python3 build_pages.py index          # site/index.html（草だけ）
python3 build_pages.py multi          # site/pm-first-year-grass.html（比較表と commit log つき）
python3 build_og.py                   # site/og-grass.png（代替 OGP 画像。og.png は手製なので触らない）
python3 parse_days.py <raw/html/.../x.html.gz>   # 1 ページ分の解析結果を眺める（デバッグ用）
```

ページはブラウザで `site/*.html` を直接開けば動く（CDN に届く必要あり）。
mulmoclaude の画面に出すときは `~/mulmoclaude/artifacts/html/2026/10/` にコピーして presentHtml の `path` で指す。

## データ源と作法

- 官邸ログ https://www.kanteilog.com/day/YYYY-MM-DD 。時事通信・日経・朝日の首相動静を構造化している第三者サイトで、収録は **2011-03-11 から**。鳩山政権はデータなし、菅直人政権は 1 年目のうち 2011-03-11 以降の 89 日だけ。
- 原文の確認は時事ドットコム `https://www.jiji.com/jc/article?k=YYYYMMDD00NNN&g=pol`（全文無料だが一覧を辿れない）。NHK の首相動静は本文が冒頭 4 行で切れていて使えない。
- **取り込みは毎分 50 件以内**。2 本並行（毎分 150 件）で 403（Vercel の制限）が返った。`fetch_days.py` は 1.5 秒間隔、403/429/503 なら 90 秒待って再試行。
- 著作権は各報道機関と官邸ログにある。公開するなら出典を明示し、原文の転載はしない。

## 1 日分のフィールド（`dousei/<pm>/<date>.json`）

| フィールド | 内容 |
|---|---|
| `date` / `pm` / `source` | 日付、総理名、出典（古い日は出典表示なし） |
| `work_min` | 公務の合計時間（分）= 24 時間 − 居所滞在。外遊中は終日 1440 |
| `residence_min` | 居所（公邸・私邸・議員宿舎）滞在（分） |
| `meetings` / `first_work` | 面会・会談件数、最初の公務の時刻 |
| `events[]` | 時系列の各行: `time`, `label`, `place`, `category` |
| `intervals[]` | 一日の時間配分バーの区間: `start`, `end`, `category`, `label`, `minutes`（1 日の合計 1440） |
| `alloc_min` | 分類ごとの分数（`intervals` を分類で合計） |

分類（官邸ログの 14 種）: 居所 / 官邸執務 / 面会・会談 / 視察 / 式典・行事 / 国会 / 党務 / 外遊 / 取材・会見 / 会食 / 移動 / 公務（内容未詳） / 個人 / その他。定義は https://www.kanteilog.com/about 。

官邸ログの数値は時事の原文と突き合わせ済み（2026-10-26: 公邸発 10:29 → 公邸着 18:26 = 7 時間 57 分、2026-10-27: 8:13 → 17:06 = 8 時間 53 分、ともに一致）。

## ページの決め事

- 1 commit = 公務 1 時間（分 ÷ 60 を四捨五入）。
- 色は 4 時間ごとに一段濃く、**16 時間以上は同じ最濃色**（一日の仕事の上限を 16 時間程度とみなす、というユーザー指示）。外遊の 24 時間扱いが色を独占しないため。
- 収録のない日は点線のマス。
- 「最も長い一日」は外遊日と空港利用日（ラベルに 空港 / 政府専用機 / チャーター機）を除いた国内の日。
- 1 年目 = 就任日から 365 日。安倍は第 2 次政権の 1 年目。
- テンプレートは Composition API、`:key` は日付などの識別子、`<style>` は Tailwind の `@theme` と `v-cloak` だけ。文言は直書き（単一 HTML なので vue-i18n は使っていない）。

## 状態（2026-10-28 時点）

- 取り込み・抽出済み: takaichi 2025-10-21〜2026-10-27（全日）、kan 89 日（収録分すべて）、noda / abe / suga / kishida / ishiba 各 1 年目 365 日。制限待ちも欠損もなし。
- `site/index.html`（草だけ）と `site/pm-first-year-grass.html`（詳細版）に 7 人分を並べてある。収録が 1 日もない鳩山はページに出さない（`build_pages.py` の `with_data`）。トップの一文は「データが確認できた 2011/3/11 以降、総理就任からの 1 年のみ」。
- 1 年目の公務時間は 野田 3,717 / 安倍 4,385 / 菅義偉 3,532 / 岸田 3,891 / 石破 4,072 / 高市 2,961 時間（菅直人は 89 日で 1,088 時間）。高市だけ 0 commit の日が 69 日と多い（他は 4〜28 日）。公邸住まいで「終日、公邸」が週末に多いためか、媒体の書き方の違いかは未確認。比べるときはこの点に注意。
- 次にやりたいこと（ユーザーの意向）: 分類別の集計。面会・国会・会食などを総理ごと・月ごとに比べる。材料は `alloc_min` と `intervals`。

## 公開（GitHub Pages）

`site/` を GitHub Pages で公開している: https://isamu.github.io/sori/ 。
`.github/workflows/pages.yml` が main への push（`site/**` の変更）で `site/` をそのまま配信する。Pages の配信元は「GitHub Actions」に設定済み。
ページを更新したら `build_pages.py` で生成 → コミット → push で自動反映。

## git

このディレクトリは単独の git リポジトリ（https://github.com/isamu/sori 、公開）。
最初に raw の HTML ごと push してしまったため履歴を作り直した。**raw/ は二度と入れない**（`.gitignore` 済み）。
取り込みが進んだら `extract_days.py` → `parse_all.py` → `build_pages.py` を回して `dousei/`・`parsed/`・`site/` をコミットする。
