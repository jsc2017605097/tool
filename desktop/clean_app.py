"""
App desktop (Windows) - Lam sach & chuyen doi danh sach doi tuong sang CSV
dung dinh dang cho extension "Cap nhat CCCD hang loat".

Phat trien boi Nguyen Do Cuong.

Chay truc tiep: python clean_app.py
Dong goi .exe: xem .github/workflows/build-windows-app.yml (PyInstaller).
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from cleaning import convert, write_records_csv, write_warnings_csv

APP_TITLE = "Làm sạch & chuyển đổi danh sách CCCD"
APP_AUTHOR = "Nguyễn Đỗ Cường"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} — by {APP_AUTHOR}")
        self.geometry("860x580")
        self.minsize(720, 500)

        self.input_path: Path | None = None
        self.result = None

        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Button(top, text="Chọn file (.xlsx / .xls / .csv)...", command=self.on_pick_file).pack(side="left")
        self.file_label = ttk.Label(top, text="Chưa chọn file nào.")
        self.file_label.pack(side="left", padx=10)

        self.summary_label = ttk.Label(self, text="", padding=(10, 0), foreground="#333")
        self.summary_label.pack(fill="x")

        self.warn_label = ttk.Label(self, text="", padding=(10, 4), foreground="#b26a00")
        self.warn_label.pack(fill="x")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=6)

        self.valid_tree = self._make_tree(notebook, ("Mã đối tượng", "Tên đối tượng", "Mã định danh"))
        notebook.add(self.valid_tree.master, text="Hợp lệ (sẵn sàng đẩy lên)")

        self.warn_tree = self._make_tree(notebook, ("Mã đối tượng", "Tên đối tượng", "Số gốc", "Lý do"))
        notebook.add(self.warn_tree.master, text="Cần kiểm tra tay")

        bottom = ttk.Frame(self, padding=10)
        bottom.pack(fill="x")

        self.save_valid_btn = ttk.Button(
            bottom, text="Lưu CSV hợp lệ...", command=self.on_save_valid, state="disabled"
        )
        self.save_valid_btn.pack(side="left")

        self.save_warn_btn = ttk.Button(
            bottom, text="Lưu danh sách cần kiểm tra...", command=self.on_save_warnings, state="disabled"
        )
        self.save_warn_btn.pack(side="left", padx=8)

        footer = ttk.Frame(self, padding=(10, 0, 10, 6))
        footer.pack(fill="x")
        ttk.Label(
            footer, text=f"Phát triển bởi {APP_AUTHOR}", foreground="#888", font=("", 9)
        ).pack(side="right")

    def _make_tree(self, parent, columns):
        frame = ttk.Frame(parent)
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        for c in columns:
            tree.heading(c, text=c)
            tree.column(c, width=180 if c != "Lý do" else 320, anchor="w")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        return tree

    # ------------------------------------------------------------------
    def on_pick_file(self):
        path = filedialog.askopenfilename(
            title="Chọn file danh sách đối tượng",
            filetypes=[("Excel / CSV", "*.xlsx *.xls *.csv"), ("Tất cả file", "*.*")],
        )
        if not path:
            return
        self.input_path = Path(path)
        self.file_label.config(text=self.input_path.name)
        self._run_convert()

    def _run_convert(self):
        assert self.input_path is not None
        try:
            result = convert(self.input_path)
        except Exception as exc:  # file hỏng, sai định dạng, v.v.
            messagebox.showerror(APP_TITLE, f"Không đọc được file:\n{exc}")
            return

        self.result = result
        self._clear_tree(self.valid_tree)
        self._clear_tree(self.warn_tree)

        if result.header_error:
            self.summary_label.config(text="")
            self.warn_label.config(text="")
            header_hint = ""
            if result.detected_header:
                header_hint = "\n\nCác cột đọc được trong file: " + ", ".join(
                    str(h) for h in result.detected_header
                )
            messagebox.showerror(APP_TITLE, result.header_error + header_hint)
            self.save_valid_btn.config(state="disabled")
            self.save_warn_btn.config(state="disabled")
            return

        for r in result.records:
            self.valid_tree.insert("", "end", values=(r["ma"], r["ten"], r["cccd"]))
        for w in result.warnings:
            self.warn_tree.insert("", "end", values=(w["ma"], w["ten"], w["raw_cccd"], w["reason"]))

        self.summary_label.config(
            text=f"Đọc {len(result.records) + len(result.warnings)} dòng dữ liệu — "
            f"{len(result.records)} dòng hợp lệ."
        )
        if result.warnings:
            self.warn_label.config(
                text=f"⚠ {len(result.warnings)} dòng bị loại khỏi file xuất — "
                "xem tab 'Cần kiểm tra tay' và tự xử lý riêng, KHÔNG đưa vào extension."
            )
        else:
            self.warn_label.config(text="")

        self.save_valid_btn.config(state="normal" if result.records else "disabled")
        self.save_warn_btn.config(state="normal" if result.warnings else "disabled")

    @staticmethod
    def _clear_tree(tree: ttk.Treeview):
        for item in tree.get_children():
            tree.delete(item)

    # ------------------------------------------------------------------
    def on_save_valid(self):
        if not self.result or not self.result.records:
            return
        default_name = (self.input_path.stem if self.input_path else "danh_sach") + "_cleaned.csv"
        path = filedialog.asksaveasfilename(
            title="Lưu file CSV hợp lệ",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        write_records_csv(path, self.result.records)
        messagebox.showinfo(APP_TITLE, f"Đã lưu {len(self.result.records)} dòng vào:\n{path}")

    def on_save_warnings(self):
        if not self.result or not self.result.warnings:
            return
        default_name = (self.input_path.stem if self.input_path else "danh_sach") + "_can_kiem_tra.csv"
        path = filedialog.asksaveasfilename(
            title="Lưu danh sách cần kiểm tra tay",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        write_warnings_csv(path, self.result.warnings)
        messagebox.showinfo(APP_TITLE, f"Đã lưu {len(self.result.warnings)} dòng vào:\n{path}")


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
