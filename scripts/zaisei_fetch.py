"""財政（使い道・国民負担・年収別の負担）の元資料を raw/zaisei/ に取り込む。

使い方:
  python3 zaisei_fetch.py        # 取得済みは飛ばす。xls は soffice で xlsx に変換して raw/zaisei/conv/ へ
"""
import subprocess, sys, tempfile
from pathlib import Path
from config import ROOT

RAW_DIR = ROOT / "raw" / "zaisei"
CONV_DIR = RAW_DIR / "conv"
XLS_MAGIC = bytes.fromhex("d0cf11e0a1b11ae1")
ESRI = "https://www.esri.cao.go.jp/jp/sna/data/data_list/kakuhou/files"
ESTAT = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"

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


def sources():
    yield "esri/cofog_2020base_2024.xlsx", f"{ESRI}/2024/tables/2024s7_jp.xlsx"
    yield "esri/sector_2020base_2024.xlsx", f"{ESRI}/2024/tables/2024s6_jp.xlsx"
    yield "esri/cofog_2000base_2009.xls", f"{ESRI}/h21/tables/21s7_jp.xls"
    yield "mof/burden_ratio_fy2026.pdf", "https://www.mof.go.jp/policy/budget/topics/futanritsu/sy202603a.pdf"
    for year, stat_id in KAKEI_DECILE_IDS.items():
        ext = "xlsx" if year in KAKEI_XLSX_YEARS else "xls"
        yield f"kakei/kakei_decile_worker_{year}.{ext}", ESTAT.format(stat_id)
    yield ("kakei/kakei_quintile_worker_nonfarm_1976-2007_20-07-c.xls",
           "https://www.stat.go.jp/data/kakei/longtime/zuhyou/20-07-c.xls")


def fetch(rel, url):
    """取得済みは飛ばすので、途中で失敗した書きかけを最終の名前で残さない。"""
    path = RAW_DIR / rel
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    r = subprocess.run(["curl", "-sSfL", "-m", "120", "-o", str(part), url], capture_output=True, text=True)
    if r.returncode != 0:
        part.unlink(missing_ok=True)
        sys.exit(f"取得に失敗: {url} → {path}: {r.stderr.strip()}")
    part.replace(path)
    print("取得", rel)


def convert_xls(rel):
    """変換済みは飛ばすので、作業用のディレクトリで変換してから置く。"""
    src = RAW_DIR / rel
    dest = CONV_DIR / (src.stem + ".xlsx")
    if src.suffix != ".xls" or dest.exists():
        return
    if src.read_bytes()[:len(XLS_MAGIC)] != XLS_MAGIC:
        sys.exit(f"xls ではない（エラーページを取得した可能性）: {src}")
    CONV_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=CONV_DIR) as work:
        r = subprocess.run(["soffice", "--headless", "--convert-to", "xlsx", "--outdir", work, str(src)], capture_output=True, text=True)
        out = Path(work) / dest.name
        if r.returncode != 0 or not out.exists():
            sys.exit(f"変換に失敗: {src} → {dest}: {r.stderr.strip()}")
        out.replace(dest)
    print("変換", dest.name)


def main():
    for rel, url in sources():
        fetch(rel, url)
        convert_xls(rel)


if __name__ == "__main__":
    main()
