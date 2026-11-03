"""財政（使い道・国民負担・年収別の負担）の元資料を raw/zaisei/ に取り込む。

使い方:
  python3 zaisei_fetch.py        # 取得済みは飛ばす。xls は soffice で xlsx に変換して raw/zaisei/conv/ へ
"""
import subprocess, sys, tempfile
from pathlib import Path
from config import ROOT
from raw_format import content_problem

RAW_DIR = ROOT / "raw" / "zaisei"
CONV_DIR = RAW_DIR / "conv"
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
ESRI = "https://www.esri.cao.go.jp/jp/sna/data/data_list/kakuhou/files"
ESTAT = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
ESTAT_CSV = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=1"

# 家計調査 年次 第 2-8 表（2018 年から第 2-5 表）: 二人以上の世帯のうち勤労者世帯、年間収入十分位階級別
KAKEI_DECILE_IDS = {
    2000: "0000003319DB", 2001: "000000331A16", 2002: "000000331A53", 2003: "000000331A8C",
    2004: "000000331AC5", 2005: "000000331AFE", 2006: "000000331D50", 2007: "000001158886",
    2008: "000002209375", 2009: "000007370311", 2010: "000008635810", 2011: "000012687851",
    2012: "000019023701", 2013: "000023621356", 2014: "000028352445", 2015: "000031370111",
    2016: "000031534674", 2017: "000031674316", 2018: "000031795450", 2019: "000031909537",
    2020: "000032048817", 2021: "000032167613", 2022: "000040015243", 2023: "000040140540",
    2024: "000040247071", 2025: "000040409528",
}
KAKEI_XLSX_YEARS = {2000} | set(range(2020, 2026))
# 家計調査 年次 第 3-2 表: 世帯主の年齢階級別（勤労者世帯のシートを使う）
KAKEI_AGE_IDS = {
    2000: "0000003319E0", 2001: "000000331A1B", 2002: "000000331A58", 2003: "000000331A91",
    2004: "000000331ACA", 2005: "000000331B03", 2006: "000000331D55", 2007: "000001158891",
    2008: "000002209380", 2009: "000007370316", 2010: "000008635815", 2011: "000012687856",
    2012: "000019023706", 2013: "000023621361", 2014: "000028352450", 2015: "000031370116",
    2016: "000031534679", 2017: "000031674321", 2018: "000031795455", 2019: "000031909542",
    2020: "000032048822", 2021: "000032167618", 2022: "000040015248", 2023: "000040140545",
    2024: "000040247076", 2025: "000040409533",
}


def sources():
    yield "esri/cofog_2020base_2024.xlsx", f"{ESRI}/2024/tables/2024s7_jp.xlsx"
    yield "esri/sector_2020base_2024.xlsx", f"{ESRI}/2024/tables/2024s6_jp.xlsx"
    yield "esri/cofog_2000base_2009.xls", f"{ESRI}/h21/tables/21s7_jp.xls"
    yield "mof/burden_ratio_fy2026.pdf", "https://www.mof.go.jp/policy/budget/topics/futanritsu/sy202603a.pdf"
    for year, stat_id in KAKEI_DECILE_IDS.items():
        ext = "xlsx" if year in KAKEI_XLSX_YEARS else "xls"
        yield f"kakei/kakei_decile_worker_{year}.{ext}", ESTAT.format(stat_id)
    for year, stat_id in KAKEI_AGE_IDS.items():
        ext = "xlsx" if year in KAKEI_XLSX_YEARS else "xls"
        yield f"kakei/kakei_age_worker_{year}.{ext}", ESTAT.format(stat_id)
    yield ("kakei/kakei_quintile_worker_nonfarm_1976-2007_20-07-c.xls",
           "https://www.stat.go.jp/data/kakei/longtime/zuhyou/20-07-c.xls")
    yield "esri/social_contributions_2020base_2024.xlsx", f"{ESRI}/2024/tables/2024s10_jp.xlsx"
    yield "cpi/cpi_2020base_calendar_year.csv", ESTAT_CSV.format("000032103936")
    yield "mof/tax_revenue_general_account.xls", "https://www.mof.go.jp/tax_policy/summary/condition/zeisyu.xls"
    yield ("soumu/local_tax_by_item_r08.xlsx",
           "https://www.soumu.go.jp/main_sosiki/jichi_zeisei/czaisei/czaisei_seido/xls/ichiran06_r08/10.xlsx")
    yield "maikin/real_wage_index_hon-t25.xls", ESTAT.format("000032189738").replace("fileKind=0", "fileKind=4")


def usable(path):
    """取得済み・変換済みとして飛ばしてよいのは、形式の確認を通ったファイルだけ。"""
    return path.exists() and content_problem(path.suffix, path.read_bytes()) is None


def fetch(rel, url):
    """確認を通らないファイルは最終の名前で置かない。前の実行で残った壊れたファイルは取り直す。"""
    path = RAW_DIR / rel
    if usable(path):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    r = subprocess.run(["curl", "-sSfL", "-m", "120", "--max-filesize", str(MAX_DOWNLOAD_BYTES), "-o", str(part), url], capture_output=True, text=True)
    problem = r.stderr.strip() if r.returncode != 0 else content_problem(path.suffix, part.read_bytes())
    if problem:
        part.unlink(missing_ok=True)
        sys.exit(f"取得に失敗: {url} → {path}: {problem}")
    part.replace(path)
    print("取得", rel)


def convert_xls(rel):
    """変換済みは飛ばすので、作業用のディレクトリで変換してから置く。"""
    src = RAW_DIR / rel
    dest = CONV_DIR / (src.stem + ".xlsx")
    if src.suffix != ".xls" or usable(dest):
        return
    if problem := content_problem(src.suffix, src.read_bytes()):
        sys.exit(f"変換しない（{problem}。エラーページを取得した可能性）: {src}")
    CONV_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=CONV_DIR) as work:
        r = subprocess.run(["soffice", "--headless", "--convert-to", "xlsx", "--outdir", work, str(src)], capture_output=True, text=True)
        out = Path(work) / dest.name
        problem = r.stderr.strip() or "出力がない" if r.returncode != 0 or not out.exists() else content_problem(out.suffix, out.read_bytes())
        if problem:
            sys.exit(f"変換に失敗: {src} → {dest}: {problem}")
        out.replace(dest)
    print("変換", dest.name)


def main():
    for rel, url in sources():
        fetch(rel, url)
        convert_xls(rel)


if __name__ == "__main__":
    main()
