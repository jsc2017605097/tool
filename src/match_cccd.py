"""
Doi chieu (match) So dinh danh ca nhan / CCCD cho danh sach doi tuong tiem chung.

Nguon:
  - Danh sach doi tuong (co "Ma doi tuong", thieu "Ma dinh danh"):
      Copy of danh sach chua lam sach cac diem tram 22.9.26 (1).xls / DanhSachDoiTuong
  - 2 file tra cuu CCCD (nguon du lieu dan cu):
      CCCD BAU CU TOAN PHUONG 2026 (DU).xlsx  (sheet "toan phuong", "DUOI 16")
      ioo.ods (nhieu sheet theo nam sinh / to dan pho)

Cach khop: vi phan lon ban ghi la tre so sinh chua co ten chinh thuc (ten dang
"M_<ten me>"), khop chinh theo (ten me, ngay sinh cua tre). Neu khong ra ket qua,
thu khop theo (ten doi tuong, ngay sinh) truc tiep (danh cho cac ban ghi da co ten).

Ket qua la mot file Excel review — KHONG tu dong ghi de "Ma dinh danh" goc, chi
de xuat gia tri va do tin cay de nguoi dung kiem tra truoc khi nhap vao phan mem.
"""

from __future__ import annotations

import datetime as dt
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl
import pandas as pd

DOWNLOADS = Path("/Users/cuongnd/Downloads")
TARGET_FILE = DOWNLOADS / "Copy of danh sách chưa làm sạch các điểm trạm 22.9.26 (1).xls"
CCCD_XLSX = DOWNLOADS / "CCCD BẦU CỬ TOÀN PHƯỜNG 2026 (ĐỦ).xlsx"
CCCD_ODS = DOWNLOADS / "ioo.ods"

OUT_DIR = Path(__file__).resolve().parent.parent / "output"
OUT_FILE = OUT_DIR / "danh_sach_doi_tuong_doi_chieu_CCCD.xlsx"


# --------------------------------------------------------------------------
# Chuan hoa chuoi / ngay thang
# --------------------------------------------------------------------------

_VN_MAP = str.maketrans({"đ": "d", "Đ": "D"})


def strip_accents(text: str) -> str:
    text = text.translate(_VN_MAP)
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", text)


def norm_name(name) -> str:
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    name = str(name).strip()
    name = re.sub(r"^M_\s*", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name)
    name = strip_accents(name).upper()
    return name.strip()


def has_placeholder_prefix(name) -> bool:
    return bool(name) and str(name).strip().upper().startswith("M_")


def norm_date(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (dt.datetime, dt.date)):
        return dt.date(value.year, value.month, value.day)
    text = str(value).strip()
    if not text or text.lower() == "nat":
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    # thu pandas parser lam phuong an cuoi
    try:
        parsed = pd.to_datetime(text, dayfirst=True, errors="raise")
        return parsed.date()
    except Exception:
        return None


def clean_id(value) -> str:
    """Chuan hoa So DDCN/CCCD tu file tham chieu ve du 12 so.

    File tham chieu luu cot nay dang so (Excel), nen Excel tu dong nuot mat
    cac so 0 dau (co dong mat 1 so, co dong mat 2 so). Ma dinh danh VN luon
    du 12 so, nen zfill lai la khoi phuc dung gia tri goc -- da doi chieu tay
    (ngay sinh + gioi tinh + ma tinh giai ma duoc) tren nhieu dong de xac nhan.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, float):
        text = str(int(value))
    else:
        text = str(value).strip()
        text = re.sub(r"\.0$", "", text)
    if text.isdigit() and 9 <= len(text) <= 12:
        text = text.zfill(12)
    return text


# --------------------------------------------------------------------------
# Nap du lieu tham chieu (cac nguon co CCCD / ma dinh danh)
# --------------------------------------------------------------------------

@dataclass
class RefRow:
    full_name: str
    dob: object
    gender: str
    so_ddcn: str
    mother: str
    father: str
    address: str
    source: str


def load_xlsx_toan_phuong() -> list[RefRow]:
    wb = openpyxl.load_workbook(CCCD_XLSX, read_only=True, data_only=True)
    ws = wb["toàn phường"]
    rows: list[RefRow] = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        if not row or row[1] is None:
            continue
        rows.append(RefRow(
            full_name=row[1], dob=row[2], gender=row[3] or "",
            so_ddcn=clean_id(row[4]), mother="", father=row[5] or "",
            address=row[6] or "", source="CCCD_xlsx:toàn phường",
        ))
    wb.close()
    return rows


def load_xlsx_duoi16() -> list[RefRow]:
    wb = openpyxl.load_workbook(CCCD_XLSX, read_only=True, data_only=True)
    ws = wb["DƯỚI 16"]
    rows: list[RefRow] = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0 or row[2] is None:
            continue
        # cols: STT, None, Ho va ten, Ngay sinh, Gioi tinh, So DDCN,
        #       Chu ho, Chu ho(2), Ho ten me, Dia chi, None
        rows.append(RefRow(
            full_name=row[2], dob=row[3], gender=row[4] or "",
            so_ddcn=clean_id(row[5]), mother=row[8] or "", father=row[6] or "",
            address=row[9] or "", source="CCCD_xlsx:DƯỚI 16",
        ))
    wb.close()
    return rows


def load_ods_children() -> list[RefRow]:
    sheets_9col = ["Sheet2", "Sheet3", "Sheet4", "Sheet6", "Sheet7", "Sheet8",
                   "2022", "2024", "2025", "2026"]
    sheets_10col = ["Sheet1"]
    rows: list[RefRow] = []

    for sn in sheets_10col:
        df = pd.read_excel(CCCD_ODS, sheet_name=sn, engine="odf", header=0)
        for _, r in df.iterrows():
            name = r.get("Họ và tên")
            if pd.isna(name):
                continue
            rows.append(RefRow(
                full_name=name, dob=r.get("Năm sinh"), gender=r.get("Giới tính") or "",
                so_ddcn=clean_id(r.get("Số ĐDCN")), mother=r.get("Hoọ tên mẹ") or "",
                father=r.get("Hoọ tên bố") or "", address=r.get("Địa chỉ") or "",
                source=f"ioo.ods:{sn}",
            ))

    for sn in sheets_9col:
        raw = pd.read_excel(CCCD_ODS, sheet_name=sn, engine="odf", header=None)
        header_row_idx = None
        for i in range(min(5, len(raw))):
            if str(raw.iloc[i, 0]).strip() == "STT":
                header_row_idx = i
                break
        if header_row_idx is None:
            continue
        df = pd.read_excel(CCCD_ODS, sheet_name=sn, engine="odf", header=header_row_idx)
        for _, r in df.iterrows():
            name = r.get("Họ và tên")
            if pd.isna(name):
                continue
            rows.append(RefRow(
                full_name=name, dob=r.get("Năm sinh"), gender=r.get("Giới tính") or "",
                so_ddcn=clean_id(r.get("Số ĐDCN")), mother=r.get("Hoọ tên mẹ") or "",
                father=r.get("Hoọ tên bố") or "", address=r.get("Địa chỉ") or "",
                source=f"ioo.ods:{sn}",
            ))
    return rows


def build_reference_indexes():
    all_rows = load_xlsx_toan_phuong() + load_xlsx_duoi16() + load_ods_children()

    # loai bo cac dong khong co so dinh danh (vo dung cho viec doi chieu)
    all_rows = [r for r in all_rows if r.so_ddcn]

    by_mother_dob: dict[tuple[str, object], list[RefRow]] = {}
    by_name_dob: dict[tuple[str, object], list[RefRow]] = {}
    by_mother_only: dict[str, list[RefRow]] = {}
    by_name_only: dict[str, list[RefRow]] = {}

    for r in all_rows:
        dob = norm_date(r.dob)
        name_n = norm_name(r.full_name)
        mother_n = norm_name(r.mother)

        if mother_n and dob:
            by_mother_dob.setdefault((mother_n, dob), []).append(r)
        if name_n and dob:
            by_name_dob.setdefault((name_n, dob), []).append(r)
        if mother_n:
            by_mother_only.setdefault(mother_n, []).append(r)
        if name_n:
            by_name_only.setdefault(name_n, []).append(r)

    return all_rows, by_mother_dob, by_name_dob, by_mother_only, by_name_only


def dedup_candidates(cands: list[RefRow]) -> list[RefRow]:
    seen = {}
    for c in cands:
        seen.setdefault(c.so_ddcn, c)
    return list(seen.values())


# --------------------------------------------------------------------------
# Doi chieu chinh
# --------------------------------------------------------------------------

@dataclass
class MatchResult:
    proposed_id: str = ""
    matched_name: str = ""
    method: str = ""
    confidence: str = ""
    sources: str = ""
    note: str = ""


def match_row(ten_doi_tuong, ten_me, dob_raw, indexes) -> MatchResult:
    _, by_mother_dob, by_name_dob, by_mother_only, by_name_only = indexes

    dob = norm_date(dob_raw)
    mother_n = norm_name(ten_me)
    name_n = norm_name(ten_doi_tuong)
    is_placeholder = has_placeholder_prefix(ten_doi_tuong)

    # 1) khop theo (me, ngay sinh cua tre) -- dang tin cay nhat cho tre so sinh
    if mother_n and dob:
        cands = dedup_candidates(by_mother_dob.get((mother_n, dob), []))
        if len(cands) == 1:
            c = cands[0]
            return MatchResult(c.so_ddcn, c.full_name, "Tên mẹ + ngày sinh", "Cao", c.source)
        if len(cands) > 1:
            return MatchResult(
                "", "", "Tên mẹ + ngày sinh", "Thấp - nhiều kết quả",
                "; ".join(f"{c.full_name}|{c.so_ddcn}|{c.source}" for c in cands),
                "Nhiều trẻ cùng mẹ cùng ngày sinh trong dữ liệu tham chiếu — cần kiểm tra thủ công (có thể song sinh).",
            )

    # 2) khop theo (ten doi tuong, ngay sinh) -- danh cho ban ghi da co ten that
    if not is_placeholder and name_n and dob:
        cands = dedup_candidates(by_name_dob.get((name_n, dob), []))
        if len(cands) == 1:
            c = cands[0]
            return MatchResult(c.so_ddcn, c.full_name, "Tên đối tượng + ngày sinh", "Cao", c.source)
        if len(cands) > 1:
            return MatchResult(
                "", "", "Tên đối tượng + ngày sinh", "Thấp - nhiều kết quả",
                "; ".join(f"{c.full_name}|{c.so_ddcn}|{c.source}" for c in cands),
                "Nhiều người trùng tên + ngày sinh — cần kiểm tra thủ công.",
            )

    # 3) noi long: chi khop theo ten me (khong doi chieu ngay sinh) -- do tin cay thap
    if mother_n:
        cands = dedup_candidates(by_mother_only.get(mother_n, []))
        if len(cands) == 1:
            c = cands[0]
            return MatchResult(
                c.so_ddcn, c.full_name, "Chỉ khớp tên mẹ (chưa đối chiếu ngày sinh)",
                "Thấp", c.source,
                "Ngày sinh trong dữ liệu tham chiếu không khớp hoặc thiếu — kiểm tra kỹ trước khi dùng.",
            )
        if len(cands) > 1:
            return MatchResult(
                "", "", "Chỉ khớp tên mẹ", "Thấp - nhiều kết quả",
                "; ".join(f"{c.full_name}|{c.so_ddcn}|{c.source}" for c in cands[:5]),
                "Mẹ có nhiều con trong dữ liệu tham chiếu — cần chọn đúng bằng ngày sinh thủ công.",
            )

    # 4) chi khop khi ten trung VA ngay sinh giong het kieu "nhap nham ngay/thang":
    #    cung nam, cung bo (ngay,thang) nhung bi hoan doi vi tri (vd 04/08 <-> 08/04).
    #    KHONG dung khop "chi ten" cho cac nam khac nhau -- qua nhieu nguoi VN trung ten,
    #    lech nam sinh vai chuc nam gan chac chan la HAI NGUOI KHAC NHAU, de xuat se rat nguy hiem
    #    (co the gan nham so dinh danh cua nguoi khac).
    if not is_placeholder and name_n and dob:
        cands_all = dedup_candidates(by_name_only.get(name_n, []))
        swap_cands = []
        for c in cands_all:
            ref_dob = norm_date(c.dob)
            if (ref_dob and ref_dob.year == dob.year and ref_dob != dob
                    and ref_dob.day == dob.month and ref_dob.month == dob.day
                    and dob.day != dob.month):
                swap_cands.append(c)
        if len(swap_cands) == 1:
            c = swap_cands[0]
            ref_dob = norm_date(c.dob)
            note = (
                f"Tên và năm sinh khớp, nhưng ngày/tháng bị đảo ngược giữa 2 nguồn: "
                f"đối tượng ghi {dob.strftime('%d/%m/%Y')}, tham chiếu ghi {ref_dob.strftime('%d/%m/%Y')} — "
                f"nhiều khả năng một trong hai nguồn nhập nhầm ngày/tháng. Vẫn cần xác nhận thủ công trước khi dùng."
            )
            return MatchResult(c.so_ddcn, c.full_name, "Tên + năm sinh (ngày/tháng bị đảo)", "Thấp", c.source, note)
        if len(swap_cands) > 1:
            return MatchResult(
                "", "", "Tên + năm sinh (ngày/tháng bị đảo)", "Thấp - nhiều kết quả",
                "; ".join(f"{c.full_name}|{c.so_ddcn}|{c.source}" for c in swap_cands[:5]),
                "Nhiều người cùng tên, cùng năm sinh, nghi ngày/tháng bị đảo — cần kiểm tra thủ công.",
            )
        # trung ten nhung nam sinh khac han -> gan nhu chac chan la nguoi khac, KHONG de xuat
        if cands_all:
            other_years = sorted({norm_date(c.dob).year for c in cands_all if norm_date(c.dob)})
            return MatchResult(
                note=(
                    f"Có {len(cands_all)} người trùng tên trong dữ liệu tham chiếu nhưng năm sinh khác hẳn "
                    f"({other_years}) — nhiều khả năng là người khác trùng tên, không đề xuất mã định danh."
                )
            )

    return MatchResult(note="Không tìm thấy trong 2 file tham chiếu — có thể trẻ quá mới, chưa được cấp/cập nhật số định danh, hoặc thuộc nhóm tuổi không nằm trong phạm vi 2 file (16-18 tuổi).")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    print("Đang nạp dữ liệu tham chiếu (CCCD)...")
    indexes = build_reference_indexes()
    all_rows = indexes[0]
    print(f"  -> {len(all_rows)} dòng tham chiếu có số định danh, từ 2 file.")

    print("Đang nạp danh sách đối tượng...")
    df = pd.read_excel(TARGET_FILE, sheet_name="DanhSachDoiTuong", header=2)
    print(f"  -> {len(df)} đối tượng, {df['Mã định danh'].notna().sum()} đã có mã định danh sẵn.")

    todo_mask = df["Mã định danh"].isna()
    print(f"  -> {todo_mask.sum()} đối tượng cần đối chiếu.")

    proposed_id, matched_name, method, confidence, sources, note = [], [], [], [], [], []

    for idx, row in df.iterrows():
        if not todo_mask[idx]:
            proposed_id.append("")
            matched_name.append("")
            method.append("")
            confidence.append("Đã có sẵn")
            sources.append("")
            note.append("")
            continue

        result = match_row(row["Tên đối tượng"], row["Họ tên mẹ"], row["Ngày sinh"], indexes)
        proposed_id.append(result.proposed_id)
        matched_name.append(result.matched_name)
        method.append(result.method)
        confidence.append(result.confidence)
        sources.append(result.sources)
        note.append(result.note)

    df["Mã định danh (đề xuất)"] = proposed_id
    df["Họ tên khớp trong CSDL"] = matched_name
    df["Phương thức khớp"] = method
    df["Độ tin cậy"] = confidence
    df["Nguồn đối chiếu"] = sources
    df["Ghi chú"] = note

    # thong ke nhanh
    todo = df[todo_mask]
    print("\n=== Kết quả đối chiếu (chỉ tính các dòng còn thiếu) ===")
    print(todo["Độ tin cậy"].value_counts())

    OUT_DIR.mkdir(exist_ok=True)
    with pd.ExcelWriter(OUT_FILE, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Đối chiếu", index=False)
        summary = todo["Độ tin cậy"].value_counts().rename_axis("Độ tin cậy").reset_index(name="Số lượng")
        summary.to_excel(writer, sheet_name="Tóm tắt", index=False)

    print(f"\nĐã ghi kết quả gộp vào: {OUT_FILE}")

    # tach rieng 4 file theo do tin cay (chi lay cac dong can doi chieu, bo qua "Da co san")
    splits = {
        "Cao": ("DoTinCay_CAO.xlsx", todo[todo["Độ tin cậy"] == "Cao"]),
        "Thap": ("DoTinCay_THAP.xlsx", todo[todo["Độ tin cậy"] == "Thấp"]),
        "ThapNhieuKetQua": ("DoTinCay_THAP_NHIEU_KETQUA.xlsx", todo[todo["Độ tin cậy"] == "Thấp - nhiều kết quả"]),
        "KhongTimThay": (
            "DoTinCay_KHONG_TIM_THAY.xlsx",
            todo[todo["Độ tin cậy"].isna() | (todo["Độ tin cậy"] == "")],
        ),
    }

    print("\n=== Xuất 4 file riêng theo độ tin cậy ===")
    for label, (filename, sub_df) in splits.items():
        out_path = OUT_DIR / filename
        sub_df.to_excel(out_path, sheet_name="Đối chiếu", index=False)
        print(f"  {label}: {len(sub_df)} dòng -> {out_path}")


if __name__ == "__main__":
    main()
