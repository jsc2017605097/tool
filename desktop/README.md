# Làm sạch & chuyển đổi danh sách CCCD → CSV

**Phát triển bởi Nguyễn Đỗ Cường.**

App desktop (Windows) độc lập với extension Chrome — dùng để làm sạch file
danh sách đối tượng (Excel hoặc CSV, tên cột tuỳ ý) và xuất ra file `.csv`
đúng định dạng mà extension "Cập nhật CCCD hàng loạt" cần.

## Lấy file .exe (không cần cài Python)
1. Vào tab **Actions** của repo trên GitHub → chọn workflow **"Build Windows
   app (làm sạch CCCD)"** → chọn lần chạy mới nhất (ứng với lần push gần nhất
   vào `desktop/`) → tải artifact **LamSachCCCD-windows** → giải nén ra
   `LamSachCCCD.exe`.
2. Chạy trực tiếp `LamSachCCCD.exe` trên Windows, không cần cài gì thêm.
3. Nếu muốn có bản mới sau khi sửa code trong `desktop/`: push lên `main`
   (hoặc bấm "Run workflow" thủ công trong tab Actions), đợi vài phút rồi tải
   lại artifact.

## Cách dùng app
1. Bấm **"Chọn file (.xlsx / .xls / .csv)..."**, chọn file danh sách gốc.
2. App tự nhận diện cột và làm sạch — không cần đổi tên cột trong file gốc.
   Nhận diện các biến thể tên cột như:
   - Mã đối tượng: `Mã đối tượng`, `Mã/ID`, `Mã DT`
   - Mã định danh/CCCD: `Mã định danh`, `Số ĐDCN/CCCD`, `CCCD`, `Số ĐDCN`
   - Tên (không bắt buộc): `Tên đối tượng`, `Họ và tên`, `Họ tên`
3. Số CCCD bị Excel làm mất số 0 đầu (11 hoặc 10 số thay vì 12) được tự động
   phục hồi.
4. Tab **"Hợp lệ"**: các dòng sẵn sàng dùng — bấm **"Lưu CSV hợp lệ..."** để
   xuất file `.csv` nạp thẳng vào extension.
5. Tab **"Cần kiểm tra tay"**: các dòng bị loại (mã định danh không đủ 12 số
   sau chuẩn hoá, hoặc trùng Mã đối tượng với dòng khác) — bấm **"Lưu danh
   sách cần kiểm tra..."** để xuất riêng, tự tra cứu/sửa tay, KHÔNG được đưa
   thẳng vào extension.

## Chạy từ source (không cần build .exe)
```
cd desktop
pip install -r requirements.txt
python clean_app.py
```

## Tự build .exe trên máy Windows (không cần GitHub Actions)
```
cd desktop
pip install -r requirements.txt
pyinstaller --onefile --windowed --name LamSachCCCD --version-file version_info.txt clean_app.py
```
File `.exe` sẽ nằm ở `desktop/dist/LamSachCCCD.exe`.
