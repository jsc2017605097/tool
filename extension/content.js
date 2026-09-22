/*
 * Cap nhat CCCD hang loat - Tiem chung vncdc
 * Content script chay trong MAIN world (co the dung truc tiep window.jQuery cua trang).
 * Chi hoat dong tren trang /TiemChung/DoiTuong/Index. Khong tu dong chay gi ca cho den
 * khi nguoi dung tai file CSV len va bam "Bat dau" trong bang dieu khien noi tren trang.
 */

(function () {
  if (window.__cccdBulkPanelInjected) return;
  window.__cccdBulkPanelInjected = true;

  // --------------------------------------------------------------------
  // Tien ich
  // --------------------------------------------------------------------
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  async function waitFor(fn, timeoutMs, intervalMs) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      if (fn()) return true;
      await sleep(intervalMs);
    }
    return false;
  }

  async function waitForElement(fn, timeoutMs, intervalMs) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      const el = fn();
      if (el) return el;
      await sleep(intervalMs);
    }
    return null;
  }

  function setInputValue(id, value) {
    const el = document.getElementById(id);
    if (!el) return false;
    const proto = Object.getPrototypeOf(el);
    const desc = Object.getOwnPropertyDescriptor(proto, "value");
    if (desc && desc.set) desc.set.call(el, value);
    else el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }

  function setSelect2(selectId, value, text) {
    if (!window.jQuery) return false;
    const $el = window.jQuery("#" + selectId);
    if ($el.length === 0) return false;
    if ($el.find('option[value="' + value + '"]').length === 0) {
      $el.append(new Option(text, value, true, true));
    }
    $el.val(value).trigger("change");
    return true;
  }

  async function ensureToggleOn(toggleDivId, hiddenInputId) {
    const hf = document.getElementById(hiddenInputId);
    if (!hf) return false;
    if (hf.value !== "1") {
      const div = document.getElementById(toggleDivId);
      if (!div) return false;
      div.click();
      await sleep(300);
    }
    return true;
  }

  function isAdvancedExpanded() {
    const el = document.getElementById("collapseThongTinSua");
    return !!(el && el.classList.contains("in"));
  }

  async function ensureAdvancedExpanded() {
    if (isAdvancedExpanded()) return true;
    const link = Array.from(document.querySelectorAll("a")).find(
      (a) => a.getAttribute("href") === "#collapseThongTinSua"
    );
    if (link) {
      link.click();
      await sleep(400);
      return true;
    }
    return false;
  }

  // --------------------------------------------------------------------
  // Cac buoc nghiep vu
  // --------------------------------------------------------------------

  function isSessionAlive() {
    return !!document.getElementById("txtKeyword") && !!document.getElementById("btnQuickSearch");
  }

  async function searchAndOpen(maDoiTuong) {
    const input = document.getElementById("txtKeyword");
    const btn = document.getElementById("btnQuickSearch");
    if (!input || !btn) {
      return { ok: false, reason: "SESSION_EXPIRED", sessionExpired: true };
    }

    // AJAX tim kiem thay the toan bo noi dung bang ket qua -> cac dong <tr> cu bi huy va
    // tao moi. Doi cho dong dau tien hien tai KHONG CON la node cu (that su la du lieu moi),
    // vi paging_info text co the giong het lan truoc (vd luon la "Hien thi [1-1]/1 doi tuong").
    const oldFirstRow = document.querySelector("#doiTuongSearchResult tbody tr");

    setInputValue("txtKeyword", maDoiTuong);
    btn.click();

    const refreshed = await waitFor(() => {
      const newFirstRow = document.querySelector("#doiTuongSearchResult tbody tr");
      return !!newFirstRow && newFirstRow !== oldFirstRow;
    }, 5000, 150);
    if (!refreshed) return { ok: false, reason: "Không nhận được phản hồi tìm kiếm" };
    await sleep(150);

    const rows = document.querySelectorAll("#doiTuongSearchResult tbody tr");
    if (rows.length === 0) return { ok: false, reason: "Không có kết quả tìm kiếm" };
    if (rows.length > 1) {
      return { ok: false, reason: "Nhiều kết quả trùng mã (" + rows.length + ") - bỏ qua, cần kiểm tra tay" };
    }

    rows[0].click();
    const detailOk = await waitFor(() => {
      const b = document.getElementById("btnEdit");
      const idEl = document.getElementById("txtMaDoiTuong");
      return !!(
        b &&
        b.offsetParent !== null &&
        idEl &&
        idEl.value &&
        idEl.value.trim() === maDoiTuong.trim()
      );
    }, 6000, 150);
    if (!detailOk) return { ok: false, reason: "Không tải được đúng chi tiết đối tượng (dữ liệu cũ chưa kịp thay đổi)" };

    return { ok: true };
  }

  async function enterEditMode() {
    const btn = document.getElementById("btnEdit");
    if (!btn) return false;
    btn.click();
    return await waitFor(() => !!document.getElementById("txtCMT_Sua"), 5000, 150);
  }

  async function saveAndConfirm() {
    const saveBtn = document.getElementById("btnSave");
    if (!saveBtn) return false;
    saveBtn.click();
    await sleep(500);

    // co the co NHIEU dialog canh bao lien tiep (vd thieu SDT ca me lan bo) --
    // bam "Tiep tuc" lap lai cho den khi khong con dialog nao xuat hien nua,
    // toi da 5 lan de tranh treo neu co loi khac.
    for (let i = 0; i < 5; i++) {
      const modalBtn = await waitForElement(() => {
        return Array.from(document.querySelectorAll("button")).find(
          (b) => b.textContent.trim() === "Tiếp tục" && b.offsetParent !== null
        );
      }, 1800, 150);
      if (!modalBtn) break;
      modalBtn.click();
      await sleep(400);
    }

    return await waitFor(() => {
      const editBtn = document.getElementById("btnEdit");
      return !!(editBtn && editBtn.offsetParent !== null);
    }, 7000, 200);
  }

  async function processRecord(rec, cfg) {
    if (!isSessionAlive()) {
      return { status: "session_expired", reason: "Phiên đăng nhập đã hết" };
    }

    const searchRes = await searchAndOpen(rec.maDoiTuong);
    if (searchRes.sessionExpired) {
      return { status: "session_expired", reason: "Phiên đăng nhập đã hết" };
    }
    if (!searchRes.ok) return { status: "fail", reason: searchRes.reason };

    const displayedId = (document.getElementById("txtMaDoiTuong") || {}).value || "";
    if (displayedId && displayedId.trim() !== rec.maDoiTuong.trim()) {
      return { status: "fail", reason: "Mã đối tượng hiển thị không khớp (" + displayedId + ")" };
    }

    const editOk = await enterEditMode();
    if (!editOk) return { status: "fail", reason: "Không vào được chế độ Sửa" };

    const existingCccd = (document.getElementById("txtCMT_Sua") || {}).value || "";
    setInputValue("txtCMT_Sua", rec.cccd);

    const toggleOk = await ensureToggleOn("tggRsts_Sua", "hfRsts_Sua");
    if (!toggleOk) return { status: "fail", reason: "Không tìm thấy toggle 'Đã rà soát thông tin'" };

    await ensureAdvancedExpanded();
    await sleep(250);

    const s1 = setSelect2("slDVHCNs_Sua", cfg.value, cfg.text);
    const s2 = setSelect2("slDVHCDkks_Sua", cfg.value, cfg.text);
    const s3 = setSelect2("slDVHCQq_Sua", cfg.value, cfg.text);
    if (!s1 || !s2 || !s3) return { status: "fail", reason: "Không tìm thấy dropdown Nơi sinh/Khai sinh/Quê quán" };

    const saveOk = await saveAndConfirm();
    if (!saveOk) return { status: "fail", reason: "Không xác nhận được lưu thành công - cần kiểm tra tay" };

    return {
      status: "ok",
      reason: existingCccd ? "đã ghi đè giá trị CCCD cũ: " + existingCccd : "",
    };
  }

  // --------------------------------------------------------------------
  // CSV parsing
  // --------------------------------------------------------------------

  function parseCSV(text) {
    text = text.replace(/^﻿/, "");
    const rows = [];
    let row = [], field = "", inQuotes = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (inQuotes) {
        if (c === '"') {
          if (text[i + 1] === '"') { field += '"'; i++; }
          else inQuotes = false;
        } else field += c;
      } else {
        if (c === '"') inQuotes = true;
        else if (c === ",") { row.push(field); field = ""; }
        else if (c === "\n") { row.push(field); rows.push(row); row = []; field = ""; }
        else if (c === "\r") { /* skip */ }
        else field += c;
      }
    }
    if (field.length || row.length) { row.push(field); rows.push(row); }
    return rows.filter((r) => r.length && r.some((c) => c.trim() !== ""));
  }

  function buildRecords(text) {
    const rows = parseCSV(text);
    if (rows.length < 2) return [];
    const header = rows[0];
    let idIdx = -1, cccdIdx = -1, tenIdx = -1;
    header.forEach((h, i) => {
      const hn = h.trim().toLowerCase();
      if (hn.includes("mã đối tượng")) idIdx = i;
      else if (hn.includes("định danh")) cccdIdx = i;
      else if (hn.includes("tên đối tượng")) tenIdx = i;
    });
    if (idIdx === -1 || cccdIdx === -1) return null;
    return rows
      .slice(1)
      .map((r) => ({
        maDoiTuong: (r[idIdx] || "").trim(),
        cccd: (r[cccdIdx] || "").trim(),
        ten: tenIdx >= 0 ? (r[tenIdx] || "").trim() : "",
      }))
      .filter((rec) => rec.maDoiTuong && rec.cccd);
  }

  // --------------------------------------------------------------------
  // Giao dien bang dieu khien
  // --------------------------------------------------------------------

  const panel = document.createElement("div");
  panel.id = "cccd-bulk-panel";
  panel.style.cssText =
    "position:fixed;right:16px;bottom:16px;width:360px;max-height:75vh;background:#fff;" +
    "border:1px solid #c9d2dc;border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.25);" +
    "z-index:2147483647;font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#222;" +
    "display:flex;flex-direction:column;overflow:hidden;";

  panel.innerHTML = `
    <div id="cccd-panel-header" style="background:#1565c0;color:#fff;padding:10px 12px;
         display:flex;justify-content:space-between;align-items:center;cursor:pointer;">
      <b>Cập nhật CCCD hàng loạt</b>
      <span id="cccd-panel-toggle">▾</span>
    </div>
    <div id="cccd-panel-body" style="padding:12px;overflow:auto;">
      <div style="margin-bottom:8px;">
        <label>File CSV (Mã đối tượng + Mã định danh):</label><br/>
        <input type="file" id="cccd-file-input" accept=".csv" style="width:100%;margin-top:4px;">
      </div>
      <div id="cccd-file-summary" style="margin-bottom:8px;color:#555;"></div>

      <div style="margin-bottom:6px;">
        <label>Giá trị Nơi sinh / Khai sinh / Quê quán (mã DVHC):</label><br/>
        <input id="cccd-place-value" value="1174107" style="width:100%;margin-top:2px;padding:3px;">
      </div>
      <div style="margin-bottom:8px;">
        <label>Tên hiển thị tương ứng:</label><br/>
        <input id="cccd-place-text" value="Phường Yên Thắng, Ninh Bình" style="width:100%;margin-top:2px;padding:3px;">
      </div>
      <div style="margin-bottom:10px;">
        <label>Độ trễ giữa các bản ghi (ms):</label>
        <input id="cccd-delay" type="number" value="700" style="width:80px;padding:2px;">
      </div>

      <div style="margin-bottom:8px;">
        <button id="cccd-start-btn" style="padding:5px 10px;">▶ Bắt đầu</button>
        <button id="cccd-pause-btn" disabled style="padding:5px 10px;">⏸ Tạm dừng</button>
        <button id="cccd-stop-btn" disabled style="padding:5px 10px;">⏹ Dừng</button>
        <button id="cccd-export-btn" disabled style="padding:5px 10px;">⬇ Tải log</button>
      </div>
      <div style="margin-bottom:8px;">
        <button id="cccd-retry-btn" disabled style="padding:5px 10px;">🔁 Chạy lại các dòng lỗi</button>
      </div>

      <div id="cccd-progress" style="font-weight:bold;margin-bottom:6px;">Chưa có file nào được tải lên.</div>
      <div id="cccd-log" style="height:240px;overflow:auto;border:1px solid #e0e0e0;
           padding:4px;background:#fafafa;line-height:1.4;"></div>
    </div>
  `;
  document.documentElement.appendChild(panel);

  const $ = (id) => document.getElementById(id);
  const body = $("cccd-panel-body");
  const toggleIcon = $("cccd-panel-toggle");
  $("cccd-panel-header").addEventListener("click", () => {
    const collapsed = body.style.display === "none";
    body.style.display = collapsed ? "block" : "none";
    toggleIcon.textContent = collapsed ? "▾" : "▸";
  });

  let records = [];
  let results = [];
  let state = { running: false, paused: false, index: 0 };

  function logLine(text, kind) {
    const color = kind === "ok" ? "#2e7d32" : kind === "fail" ? "#c62828" : "#555";
    const div = document.createElement("div");
    div.style.color = color;
    div.textContent = text;
    $("cccd-log").appendChild(div);
    $("cccd-log").scrollTop = $("cccd-log").scrollHeight;
  }

  function updateProgress() {
    const okCount = results.filter((r) => r.status === "ok").length;
    const failCount = results.filter((r) => r.status === "fail").length;
    // dung state.index (tien do cua LUOT CHAY hien tai) lam tu so, vi sau khi
    // "Chay lai loi" thi records chi con la tap con nho hon results tich luy
    $("cccd-progress").textContent =
      `Đã xử lý ${state.index + 1}/${records.length}  ·  OK: ${okCount}  ·  Lỗi: ${failCount}`;
  }

  $("cccd-file-input").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!/\.csv$/i.test(file.name)) {
      $("cccd-file-summary").textContent =
        `File "${file.name}" không phải .csv (có thể bạn chọn nhầm file .xlsx) — ` +
        `hãy chọn đúng file .csv (ví dụ output/queue_CAO.csv).`;
      records = [];
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const parsed = buildRecords(reader.result);
      if (parsed === null) {
        const firstLine = reader.result.split(/\r?\n/, 1)[0] || "";
        $("cccd-file-summary").textContent =
          `Không nhận diện được cột 'Mã đối tượng' / 'Mã định danh' trong file "${file.name}". ` +
          `Dòng đầu file đọc được: "${firstLine.slice(0, 120)}"`;
        records = [];
        return;
      }
      records = parsed;
      results = [];
      state.index = 0;
      $("cccd-file-summary").textContent = `Đã nạp ${records.length} bản ghi từ file.`;
      $("cccd-progress").textContent = `Sẵn sàng xử lý ${records.length} bản ghi.`;
      $("cccd-start-btn").disabled = records.length === 0;
      $("cccd-export-btn").disabled = true;
      $("cccd-retry-btn").disabled = true;
      $("cccd-log").innerHTML = "";
    };
    reader.readAsText(file, "utf-8");
  });

  async function runLoop() {
    state.running = true;
    state.paused = false;
    $("cccd-start-btn").disabled = true;
    $("cccd-pause-btn").disabled = false;
    $("cccd-stop-btn").disabled = false;

    const cfg = {
      value: $("cccd-place-value").value.trim(),
      text: $("cccd-place-text").value.trim(),
    };
    const delayMs = parseInt($("cccd-delay").value, 10) || 700;

    while (state.index < records.length && state.running) {
      while (state.paused && state.running) {
        await sleep(300);
      }
      if (!state.running) break;

      const rec = records[state.index];
      let result;
      try {
        result = await processRecord(rec, cfg);
      } catch (err) {
        result = { status: "fail", reason: "Lỗi không mong muốn: " + (err && err.message) };
      }

      if (result.status === "session_expired") {
        logLine(
          "⚠ Phiên đăng nhập đã hết (hoặc trang bị chuyển hướng). Đã TẠM DỪNG tại " +
            rec.maDoiTuong +
            ". Đăng nhập lại rồi bấm 'Tiếp tục' để chạy tiếp từ đúng bản ghi này.",
          "fail"
        );
        state.paused = true;
        $("cccd-pause-btn").textContent = "▶ Tiếp tục";
        continue; // khong tang index, khong ghi vao results - se thu lai ban ghi nay
      }

      result.maDoiTuong = rec.maDoiTuong;
      result.ten = rec.ten;
      result.cccd = rec.cccd;
      results.push(result);

      const label = `${rec.maDoiTuong} — ${rec.ten || ""}`;
      if (result.status === "ok") {
        logLine("✓ " + label + (result.reason ? "  (" + result.reason + ")" : ""), "ok");
      } else {
        logLine("✗ " + label + "  →  " + result.reason, "fail");
      }
      updateProgress();

      state.index++;
      await sleep(delayMs);
    }

    state.running = false;
    $("cccd-start-btn").disabled = false;
    $("cccd-pause-btn").disabled = true;
    $("cccd-stop-btn").disabled = true;
    $("cccd-export-btn").disabled = results.length === 0;
    $("cccd-retry-btn").disabled = results.filter((r) => r.status === "fail").length === 0;
    if (state.index >= records.length) {
      logLine("— Hoàn tất toàn bộ hàng đợi —", "");
    } else {
      logLine("— Đã dừng —", "");
    }
  }

  function retryFailed() {
    const failedIds = new Set(
      results.filter((r) => r.status === "fail").map((r) => r.maDoiTuong)
    );
    if (failedIds.size === 0) return;

    records = results
      .filter((r) => failedIds.has(r.maDoiTuong))
      .map((r) => ({ maDoiTuong: r.maDoiTuong, cccd: r.cccd, ten: r.ten }));
    // bo cac ket qua loi cu ra khoi results, se duoc ghi lai sau khi chay lai
    results = results.filter((r) => !failedIds.has(r.maDoiTuong));
    state.index = 0;

    logLine(`— Chạy lại ${records.length} dòng lỗi —`, "");
    $("cccd-retry-btn").disabled = true;
    runLoop();
  }

  $("cccd-start-btn").addEventListener("click", () => {
    if (records.length === 0) return;
    runLoop();
  });
  $("cccd-retry-btn").addEventListener("click", retryFailed);
  $("cccd-pause-btn").addEventListener("click", () => {
    state.paused = !state.paused;
    $("cccd-pause-btn").textContent = state.paused ? "▶ Tiếp tục" : "⏸ Tạm dừng";
  });
  $("cccd-stop-btn").addEventListener("click", () => {
    state.running = false;
    state.paused = false;
  });
  $("cccd-export-btn").addEventListener("click", () => {
    const header = "Ma doi tuong,Ten,Trang thai,Ghi chu\n";
    const rows = results
      .map((r) => [r.maDoiTuong, r.ten, r.status, (r.reason || "").replace(/,/g, ";")].join(","))
      .join("\n");
    const blob = new Blob([header + rows], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "ket_qua_cap_nhat_cccd.csv";
    a.click();
    URL.revokeObjectURL(url);
  });
})();
