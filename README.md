# Bộ công cụ CCCD — Tiêm chủng

**Phát triển bởi Nguyễn Đỗ Cường.**

Tập hợp công cụ hỗ trợ đối chiếu, làm sạch và cập nhật hàng loạt Số định danh
cá nhân (CCCD) cho danh sách đối tượng trong phần mềm tiêm chủng vncdc.

## Thành phần

- **`src/match_cccd.py`** — đối chiếu danh sách đối tượng còn thiếu "Mã định
  danh" với các nguồn dữ liệu dân cư (CCCD), xuất ra file Excel review kèm độ
  tin cậy cho từng kết quả khớp. Không tự động ghi đè dữ liệu gốc.
- **`extension/`** — tiện ích mở rộng Chrome "Cập nhật CCCD hàng loạt": tải
  file CSV (Mã đối tượng + Mã định danh) và tự động điền/lưu vào phần mềm
  tiêm chủng vncdc.
- **`desktop/`** — app desktop Windows độc lập để làm sạch file danh sách gốc
  (Excel/CSV) và xuất ra đúng định dạng CSV mà extension cần. Xem
  [`desktop/README.md`](desktop/README.md) để lấy bản `.exe` dựng sẵn.

## Cài đặt (chạy từ source)

```
uv sync
```

hoặc dùng `pip install -e .` với `pyproject.toml`.

## Tác giả

Nguyễn Đỗ Cường
