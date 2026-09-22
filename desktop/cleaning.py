"""
Logic lam sach / chuan hoa file danh sach doi tuong truoc khi nap vao extension
"Cap nhat CCCD hang loat". Tach rieng khoi giao dien (clean_app.py) de co the
test doc lap va khong keo theo dependency Tkinter khi chi can xu ly du lieu.

Dau vao: .xlsx / .xls / .csv voi ten cot linh hoat (vd "Mã/ID", "Số ĐDCN/CCCD").
Dau ra: danh sach ban ghi hop le (san sang ghi CSV dung dinh dang extension can:
cot "Mã đối tượng", "Tên đối tượng", "Mã định danh (đề xuất)") + danh sach dong
bi loai kem ly do, de nguoi dung tu kiem tra tay.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

OUTPUT_HEADER = ["Mã đối tượng", "Tên đối tượng", "Mã định danh (đề xuất)"]
WARNING_HEADER = ["Mã đối tượng", "Tên đối tượng", "Số định danh/CCCD (nguyên gốc)", "Lý do"]

_VN_MAP = str.maketrans({"đ": "d", "Đ": "D"})


def strip_accents(text: str) -> str:
    text = text.translate(_VN_MAP)
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", text)


def normalize_header(h) -> str:
    h = "" if h is None else str(h)
    h = strip_accents(h).lower()
    return re.sub(r"[^a-z0-9]", "", h)


# Danh sach tu khoa (da chuan hoa) dung de nhan dien cot theo cac bien the
# ten cot thuong gap trong cac file xuat khac nhau. Day la quy tac co dinh,
# khong doi theo tung file - moi lan them bien the moi chi can bo sung o day.
ID_ALIASES = ["madoituong", "maid", "madt", "masodoituong"]
CCCD_ALIASES = ["dinhdanh", "cccd", "ddcn"]
TEN_ALIASES = ["tendoituong", "hovaten", "hoten"]


def detect_columns(header: list) -> tuple[int, int, int]:
    id_idx = cccd_idx = ten_idx = -1
    for i, h in enumerate(header):
        hn = normalize_header(h)
        if id_idx == -1 and any(a in hn for a in ID_ALIASES):
            id_idx = i
        elif cccd_idx == -1 and any(a in hn for a in CCCD_ALIASES):
            cccd_idx = i
        elif ten_idx == -1 and any(a in hn for a in TEN_ALIASES):
            ten_idx = i
    return id_idx, cccd_idx, ten_idx


def clean_cccd(raw) -> str:
    """Phuc hoi so CCCD/dinh danh ve du 12 so.

    Excel thuong luu cot nay dang number nen tu dong nuot mat so 0 dau (12 so
    dinh danh VN bi rut con 9-11 so). Neu chuoi toan la so va dai 9-12, dem 0
    vao dau cho du 12 -- cung logic voi clean_id() trong src/match_cccd.py,
    da doi chieu tay tren nhieu dong de xac nhan dung.
    """
    if raw is None:
        return ""
    text = str(raw).strip()
    text = re.sub(r"\.0$", "", text)
    if text.isdigit() and 9 <= len(text) <= 12:
        text = text.zfill(12)
    return text


@dataclass
class ConvertResult:
    records: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)
    header_error: str | None = None
    detected_header: list | None = None


def _read_rows(path: Path) -> list[list]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with open(path, newline="", encoding="utf-8-sig") as f:
            return [row for row in csv.reader(f) if any(c.strip() for c in row)]
    if suffix in (".xlsx", ".xlsm"):
        import openpyxl

        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.worksheets[0]
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        wb.close()
        return [r for r in rows if any(c is not None and str(c).strip() for c in r)]
    if suffix == ".xls":
        import xlrd

        wb = xlrd.open_workbook(str(path))
        ws = wb.sheet_by_index(0)
        rows = [ws.row_values(i) for i in range(ws.nrows)]
        return [r for r in rows if any(str(c).strip() for c in r)]
    raise ValueError(f"Không hỗ trợ định dạng file: {suffix}")


def convert(path: str | Path) -> ConvertResult:
    path = Path(path)
    rows = _read_rows(path)
    if len(rows) < 2:
        return ConvertResult(header_error="File không có dữ liệu (cần ít nhất 1 dòng tiêu đề + 1 dòng dữ liệu).")

    header = rows[0]
    id_idx, cccd_idx, ten_idx = detect_columns(header)
    if id_idx == -1 or cccd_idx == -1:
        return ConvertResult(
            header_error=(
                "Không nhận diện được cột Mã đối tượng / Mã định danh. "
                "Chấp nhận các tên cột như 'Mã đối tượng', 'Mã/ID', "
                "'Mã định danh', 'Số ĐDCN/CCCD', 'CCCD'."
            ),
            detected_header=list(header),
        )

    candidates = []
    for r in rows[1:]:
        ma = str(r[id_idx]).strip() if id_idx < len(r) and r[id_idx] is not None else ""
        raw_cccd = str(r[cccd_idx]).strip() if cccd_idx < len(r) and r[cccd_idx] is not None else ""
        ten = ""
        if 0 <= ten_idx < len(r) and r[ten_idx] is not None:
            ten = str(r[ten_idx]).strip()
        if ma and raw_cccd:
            candidates.append({"ma": ma, "raw_cccd": raw_cccd, "ten": ten})

    warnings = []
    cleaned = []
    for c in candidates:
        cccd = clean_cccd(c["raw_cccd"])
        if not re.fullmatch(r"\d{12}", cccd):
            warnings.append({
                "ma": c["ma"], "ten": c["ten"], "raw_cccd": c["raw_cccd"],
                "reason": "Mã định danh sau khi chuẩn hoá không đủ 12 số hoặc có ký tự lạ",
            })
            continue
        cleaned.append({"ma": c["ma"], "cccd": cccd, "ten": c["ten"]})

    id_counts: dict[str, int] = {}
    for c in cleaned:
        id_counts[c["ma"]] = id_counts.get(c["ma"], 0) + 1

    records = []
    for c in cleaned:
        if id_counts[c["ma"]] > 1:
            warnings.append({
                "ma": c["ma"], "ten": c["ten"], "raw_cccd": c["cccd"],
                "reason": "Trùng Mã đối tượng với (các) dòng khác trong file — cần kiểm tra tay",
            })
            continue
        records.append(c)

    return ConvertResult(records=records, warnings=warnings)


def write_records_csv(path: str | Path, records: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(OUTPUT_HEADER)
        for r in records:
            w.writerow([r["ma"], r["ten"], r["cccd"]])


def write_warnings_csv(path: str | Path, warnings: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(WARNING_HEADER)
        for wr in warnings:
            w.writerow([wr["ma"], wr["ten"], wr["raw_cccd"], wr["reason"]])
