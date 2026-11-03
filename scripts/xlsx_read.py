"""xlsx を標準ライブラリだけで読む。read(path) が (シート名, 行のリスト) を返す。"""
import re, sys, zipfile
from xml.etree import ElementTree as ET
from raw_format import zip_size_problem

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def col_index(ref):
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def read(path):
    with zipfile.ZipFile(path) as z:
        if problem := zip_size_problem(z.infolist()):
            raise ValueError(f"{problem}: {path}")
        yield from read_sheets(z)


def read_sheets(z):
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        shared = ["".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")) for si in root.findall("m:si", NS)]
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    target = {r.get("Id"): r.get("Target") for r in rels}
    for sh in wb.find("m:sheets", NS):
        name = sh.get("name")
        p = target[sh.get(REL)].lstrip("/")
        p = p if p.startswith("xl/") else "xl/" + p
        root = ET.fromstring(z.read(p))
        rows = []
        for row in root.iter(f"{{{NS['m']}}}row"):
            cells = {}
            for c in row.findall("m:c", NS):
                v = c.find("m:v", NS)
                if v is None:
                    is_ = c.find("m:is", NS)
                    if is_ is None:
                        continue
                    val = "".join(t.text or "" for t in is_.iter(f"{{{NS['m']}}}t"))
                elif c.get("t") == "s":
                    val = shared[int(v.text)]
                elif c.get("t") in ("str", "b", "e"):
                    val = v.text
                else:
                    val = float(v.text)
                cells[col_index(c.get("r"))] = val
            if cells:
                rows.append([cells.get(i) for i in range(max(cells) + 1)])
        yield name, rows
