"""取得した元資料の中身が、拡張子どおりの形式かを確かめる純粋関数（エラーページを保存しないため）。"""
import io, zipfile

XLS_MAGIC = bytes.fromhex("d0cf11e0a1b11ae1")
PDF_MAGIC = b"%PDF-"
XLSX_REQUIRED = "xl/workbook.xml"
UTF8_BOM = b"\xef\xbb\xbf"


MAX_ZIP_ENTRIES = 10000
MAX_UNCOMPRESSED_BYTES = 500 * 1024 * 1024


def zip_size_problem(infos):
    """展開後の大きさに上限を置く（壊れた・悪意のある zip でメモリやディスクを使い切らないため）。"""
    total = sum(i.file_size for i in infos)
    if len(infos) > MAX_ZIP_ENTRIES or total > MAX_UNCOMPRESSED_BYTES:
        return f"zip が大きすぎる（{len(infos)} 個、展開後 {total} バイト）"
    return None


def xlsx_problem(data):
    if not zipfile.is_zipfile(io.BytesIO(data)):
        return "zip ではない"
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if problem := zip_size_problem(z.infolist()):
            return problem
        return None if XLSX_REQUIRED in z.namelist() else f"{XLSX_REQUIRED} がない"


def content_problem(suffix, data):
    """形式が合わなければ理由の文字列、合えば None。知らない拡張子は理由を返す（黙って通さない）。"""
    if not data:
        return "空のファイル"
    if suffix == ".xls":
        return None if data.startswith(XLS_MAGIC) else "xls の署名がない"
    if suffix == ".xlsx":
        return xlsx_problem(data)
    if suffix == ".pdf":
        return None if data.startswith(PDF_MAGIC) else "pdf の署名がない"
    if suffix == ".csv":
        return "HTML のように見える" if data.removeprefix(UTF8_BOM).lstrip().startswith(b"<") else None
    return f"確かめ方を知らない拡張子: {suffix}"
