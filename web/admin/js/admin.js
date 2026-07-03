(() => {
  "use strict";

  const TOKEN_KEY = "sgb_admin_token";
  const configuredBase = (document.body.dataset.apiBase || "").replace(/\/$/, "");
  const API_BASE = configuredBase || window.location.origin;
  const ASSETS_BASE = (document.body.dataset.assetsBase || "").replace(/\/$/, "");

  const FILE_RULES = {
    samplesFile: {
      exts: [".json", ".tsv", ".csv", ".xlsx", ".docx"],
      label: "xlsx, docx, tsv, csv, json",
    },
    studentsFile: {
      exts: [".tsv", ".csv", ".txt"],
      label: "tsv, csv, txt",
    },
    aiStudentFile: {
      exts: [".txt", ".tsv", ".csv", ".docx", ".xlsx", ".pdf", ".hwp"],
      label: "txt, tsv, csv, docx, xlsx 등",
    },
  };

  function fileExtension(name) {
    const dot = name.lastIndexOf(".");
    return dot >= 0 ? name.slice(dot).toLowerCase() : "";
  }

  function validateFiles(files, inputId) {
    const rule = FILE_RULES[inputId];
    if (!rule) return { ok: true, valid: [...files], rejected: [] };

    const valid = [];
    const rejected = [];
    for (const file of files) {
      const ext = fileExtension(file.name);
      if (rule.exts.includes(ext)) valid.push(file);
      else rejected.push(file);
    }
    return { ok: rejected.length === 0, valid, rejected, rule };
  }

  function formatRejectedNames(files) {
    return files.map((f) => f.name).join(", ");
  }

  function assetUrl(path) {
    const clean = path.replace(/^\//, "");
    return ASSETS_BASE ? `${ASSETS_BASE}/${clean}` : clean;
  }

  function setupFilePickers() {
    document.querySelectorAll("[data-file-trigger]").forEach((btn) => {
      const inputId = btn.getAttribute("data-file-trigger");
      const input = document.getElementById(inputId);
      const nameEl = document.getElementById(`${inputId}Name`);
      if (!input) return;

      btn.addEventListener("click", () => input.click());

      input.addEventListener("change", () => {
        const files = input.files ? [...input.files] : [];
        if (!nameEl) return;

        if (!files.length) {
          nameEl.textContent = "선택된 파일 없음";
          nameEl.classList.remove("has-file", "is-invalid");
          return;
        }

        const check = validateFiles(files, inputId);
        if (check.rejected.length) {
          nameEl.textContent = `지원 안 함: ${formatRejectedNames(check.rejected)}`;
          nameEl.classList.add("is-invalid");
          nameEl.classList.remove("has-file");
          showToast(`지원하지 않는 형식입니다. (${check.rule.label})`);
          input.value = "";
          return;
        }

        nameEl.classList.remove("is-invalid");
        nameEl.classList.add("has-file");
        if (files.length === 1) {
          nameEl.textContent = files[0].name;
        } else {
          nameEl.textContent = `${files.length}개 파일 선택됨`;
        }
      });
    });

    document.querySelectorAll(".admin-sample-links a[href^='samples/']").forEach((link) => {
      const href = link.getAttribute("href");
      if (href) link.setAttribute("href", assetUrl(href));
    });
  }

  const gate = document.getElementById("adminGate");
  const app = document.getElementById("adminApp");
  const loginForm = document.getElementById("loginForm");
  const loginError = document.getElementById("loginError");
  const logoutBtn = document.getElementById("logoutBtn");
  const toast = document.getElementById("toast");

  let currentStudentId = null;
  let currentStudentData = null;
  let lastTabBeforeDetail = "review";
  let selectedSampleIds = new Set();
  let selectedStudentIds = new Set();
  let selectedReviewIds = new Set();
  let busyTimer = null;
  let busyStartedAt = 0;
  let systemInfo = { gemini_model: "—" };

  const busyOverlay = document.getElementById("busyOverlay");
  const busyTitle = document.getElementById("busyTitle");
  const busyMessage = document.getElementById("busyMessage");
  const busyModel = document.getElementById("busyModel");
  const busyHint = document.getElementById("busyHint");
  const busyElapsed = document.getElementById("busyElapsed");

  function showToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 3200);
  }

  function setBusy(active, title = "AI 처리 중", message = "잠시만 기다려 주세요", hint = "", options = {}) {
    const { showModel = true } = options;
    if (active) {
      document.body.classList.add("admin-is-busy");
      if (busyOverlay) busyOverlay.hidden = false;
      if (busyTitle) busyTitle.textContent = title;
      if (busyMessage) busyMessage.textContent = message;
      if (busyHint) busyHint.textContent = hint;
      if (busyModel) {
        busyModel.hidden = !showModel;
        busyModel.textContent = `사용 모델 · ${systemInfo.gemini_model}`;
      }
      if (busyElapsed) busyElapsed.textContent = "0초 경과";
      return;
    }
    if (busyTimer) {
      clearInterval(busyTimer);
      busyTimer = null;
    }
    document.body.classList.remove("admin-is-busy");
    if (busyOverlay) busyOverlay.hidden = true;
  }

  function startBusy(title, message, hint = "응답을 기다리는 중입니다. 창을 닫지 마세요.", options = {}) {
    const { showModel = true } = options;
    busyStartedAt = Date.now();
    setBusy(true, title, message, hint, { showModel });
    if (busyTimer) clearInterval(busyTimer);
    busyTimer = setInterval(() => {
      const sec = Math.floor((Date.now() - busyStartedAt) / 1000);
      if (busyElapsed) busyElapsed.textContent = `${sec}초 경과`;
    }, 1000);
    return () => setBusy(false);
  }

  async function withBusy(title, message, hint, fn, options = {}) {
    const stop = startBusy(title, message, hint, options);
    try {
      return await fn();
    } finally {
      stop();
    }
  }

  async function loadSystemInfo() {
    try {
      const data = await api("/api/auth/me");
      if (data.gemini_model) systemInfo.gemini_model = data.gemini_model;
      return data;
    } catch {
      return null;
    }
  }

  function showUploadLog(elementId, lines) {
    const el = document.getElementById(elementId);
    if (!el) return;
    if (!lines.length) {
      el.hidden = true;
      el.textContent = "";
      return;
    }
    el.hidden = false;
    el.textContent = lines.join("\n");
  }

  function getToken() {
    return sessionStorage.getItem(TOKEN_KEY) || "";
  }

  function setToken(token) {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  }

  async function api(path, options = {}) {
    const headers = { ...(options.headers || {}) };
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;

    const isForm = options.body instanceof FormData;
    if (!isForm && options.body && typeof options.body === "object") {
      headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(options.body);
    }

    let response;
    try {
      response = await fetch(`${API_BASE}${path}`, { ...options, headers });
    } catch {
      const hint = configuredBase
        ? `API 서버(${configuredBase})에 연결할 수 없습니다. NAS·터널이 실행 중인지 확인하세요.`
        : "API 서버에 연결할 수 없습니다.";
      throw new Error(hint);
    }
    const text = await response.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { detail: text };
    }

    if (!response.ok) {
      const message = data?.detail || data?.message || `요청 실패 (${response.status})`;
      throw new Error(typeof message === "string" ? message : JSON.stringify(message));
    }
    return data;
  }

  function showGate() {
    gate.hidden = false;
    app.hidden = true;
  }

  function showApp() {
    gate.hidden = true;
    app.hidden = false;
  }

  function switchTab(name) {
    document.querySelectorAll(".admin-tab").forEach((btn) => {
      const tabName = btn.dataset.tab;
      if (tabName === "detail") {
        btn.hidden = name !== "detail";
      }
      btn.classList.toggle("active", tabName === name);
    });
    document.querySelectorAll(".admin-panel").forEach((panel) => {
      const key = panel.id.replace(/^panel/, "").toLowerCase();
      panel.hidden = key !== name;
    });
  }

  function statusPill(status) {
    const labels = {
      pending: "대기",
      done: "완료",
      partial: "일부 완료",
      error: "오류",
      in_progress: "작성 중",
    };
    return `<span class="status-pill status-${status}">${labels[status] || status}</span>`;
  }

  const WRITE_SECTION_LABELS = {
    행발: "행동특성 및 종합의견",
    세특: "세부능력 및 특기사항",
    자율: "자율활동",
    동아리: "동아리활동",
    진로: "진로활동",
    창체: "창의적 체험활동",
  };

  function getSelectedWriteTargets() {
    return [...document.querySelectorAll(".write-target:checked")].map((el) => el.value);
  }

  function updateStudentMemoPanels() {
    const selected = new Set(getSelectedWriteTargets());
    let firstVisible = null;
    document.querySelectorAll(".admin-memo-panel").forEach((panel) => {
      const target = panel.dataset.target;
      const visible = selected.has(target);
      panel.hidden = !visible;
      if (visible && !firstVisible) firstVisible = panel;
    });
    if (firstVisible && !document.querySelector(".admin-memo-panel:not([hidden])[open]")) {
      firstVisible.open = true;
    }
  }

  function initStudentFormControls() {
    const classEl = document.getElementById("simpleClass");
    const numberEl = document.getElementById("simpleNumber");
    if (classEl && !classEl.options.length) {
      for (let i = 1; i <= 20; i += 1) {
        classEl.add(new Option(`${i}반`, String(i), false, i === 1));
      }
    }
    if (numberEl && !numberEl.options.length) {
      for (let i = 1; i <= 50; i += 1) {
        numberEl.add(new Option(`${i}번`, String(i), false, i === 1));
      }
    }
  }

  function setStudentGrade(grade) {
    const value = String(grade);
    const hidden = document.getElementById("simpleGrade");
    if (hidden) hidden.value = value;
    document.querySelectorAll(".admin-grade-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.grade === value);
    });
  }

  function resetStudentFormDefaults() {
    setStudentGrade(2);
    const classEl = document.getElementById("simpleClass");
    const numberEl = document.getElementById("simpleNumber");
    if (classEl) classEl.value = "1";
    if (numberEl) numberEl.value = "1";
    document.querySelectorAll(".write-target").forEach((box) => {
      box.checked = box.value === "행발";
    });
    updateStudentMemoPanels();
  }

  function formatWriteTargets(student) {
    const raw = student.notes?.write_targets;
    if (Array.isArray(raw) && raw.length) {
      return raw.join(", ");
    }
    const inferred = [];
    if (student.notes?.행발 || student.notes?.행발_notes) inferred.push("행발");
    if (student.subjects && Object.keys(student.subjects).length) inferred.push("세특");
    const changche = student.changche || {};
    for (const key of ["자율", "동아리", "진로", "봉사"]) {
      if (changche[key]) inferred.push(key);
    }
    return inferred.length ? inferred.join(", ") : "-";
  }

  function openGuideModal() {
    const modal = document.getElementById("guideModal");
    if (!modal) return;
    modal.hidden = false;
    document.body.classList.add("admin-guide-open");
    document.getElementById("guideCloseBtn")?.focus();
  }

  function closeGuideModal() {
    const modal = document.getElementById("guideModal");
    if (!modal) return;
    modal.hidden = true;
    document.body.classList.remove("admin-guide-open");
    document.getElementById("guideBtn")?.focus();
  }

  function getSelectedWriteSection() {
    const checked = document.querySelector('input[name="writeSection"]:checked');
    if (!checked) {
      throw new Error("작성할 영역을 선택하세요.");
    }
    return checked.value;
  }

  function updateWriteSectionUi() {
    const section = document.querySelector('input[name="writeSection"]:checked')?.value || "행발";
    const btn = document.getElementById("runBatchBtn");
    if (btn) {
      btn.textContent = `${section} 미작성 학생 작성`;
    }
    sessionStorage.setItem("sgb_write_section", section);
  }

  function restoreWriteSectionChoice() {
    const saved = sessionStorage.getItem("sgb_write_section");
    if (!saved) return;
    const input = document.querySelector(`input[name="writeSection"][value="${saved}"]`);
    if (input) input.checked = true;
    updateWriteSectionUi();
  }

  function studentLabel(s) {
    return `${s.grade}-${s.class_num} ${s.number}번 ${s.name}`;
  }

  function formatUsage(usage) {
    if (!usage) return "";
    if (usage.unlimited) {
      return `무제한 · 이번 달 ${usage.generations_used}건 작성`;
    }
    const left = usage.generations_remaining ?? 0;
    const limit = usage.generations_limit ?? 0;
    return `무료 플랜 · 이번 달 ${left}/${limit}건 남음`;
  }

  async function loadUsage() {
    try {
      const usage = await api("/api/usage");
      const badge = document.getElementById("usageBadge");
      const text = document.getElementById("usageText");
      const line = formatUsage(usage);
      if (badge) badge.textContent = line ? `${line} · ① 학습 → ② 설정 → ③ 학생 → ④ 작성·검토` : badge.textContent;
      if (text) text.textContent = line || text.textContent;
      return usage;
    } catch {
      return null;
    }
  }

  async function loadStudents() {
    const tbody = document.getElementById("studentsTableBody");
    const toolbar = document.getElementById("studentsBulkActions");
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="5">불러오는 중…</td></tr>`;
    if (toolbar) toolbar.hidden = true;
    const data = await api("/api/students");
    if (!data.students.length) {
      tbody.innerHTML = `<tr><td colspan="5" class="admin-muted">등록된 학생이 없습니다.</td></tr>`;
      selectedStudentIds.clear();
      updateStudentSelectionUi(0);
      return;
    }
    tbody.innerHTML = data.students
      .map((s) => {
        const targets = formatWriteTargets(s);
        const checked = selectedStudentIds.has(s.id) ? "checked" : "";
        const actions =
          s.status === "done"
            ? `<button class="admin-btn secondary admin-btn-sm" data-action="review" data-id="${s.id}">검토</button>`
            : `<button class="admin-btn secondary admin-btn-sm" data-action="run-one" data-id="${s.id}">${
                s.status === "partial" ? "추가 작성" : "작성"
              }</button>`;
        return `<tr>
          <td class="sample-select-cell">
            <label class="admin-check admin-check-row" title="선택">
              <input class="student-select admin-check-input" type="checkbox" data-id="${s.id}" ${checked}>
              <span class="admin-check-box" aria-hidden="true"></span>
            </label>
          </td>
          <td>${studentLabel(s)}</td>
          <td>${statusPill(s.status)}</td>
          <td>${targets}</td>
          <td class="admin-row-actions">
            ${actions}
            <button class="admin-btn danger admin-btn-sm" type="button" data-action="delete-student" data-id="${s.id}" data-label="${escapeAttr(studentLabel(s))}">삭제</button>
          </td>
        </tr>`;
      })
      .join("");
    updateStudentSelectionUi(data.count);
  }

  function updateStudentSelectionUi(totalCount = null) {
    const toolbar = document.getElementById("studentsBulkActions");
    const countBadge = document.getElementById("studentsCountBadge");
    const countEl = document.getElementById("studentsSelectedCount");
    const deleteSelectedBtn = document.getElementById("deleteSelectedStudentsBtn");
    const selectAll = document.getElementById("studentsSelectAll");
    const boxes = [...document.querySelectorAll(".student-select")];
    const checkedCount = boxes.filter((box) => box.checked).length;
    const total = totalCount ?? boxes.length;

    if (countBadge) countBadge.textContent = `${total}명`;
    if (countEl) countEl.textContent = checkedCount ? `${checkedCount}명 선택됨` : "";
    if (deleteSelectedBtn) deleteSelectedBtn.disabled = checkedCount === 0;
    if (selectAll && boxes.length) {
      selectAll.checked = checkedCount > 0 && checkedCount === boxes.length;
      selectAll.indeterminate = checkedCount > 0 && checkedCount < boxes.length;
    }
    if (toolbar) toolbar.hidden = total === 0;
  }

  function getSelectedStudentIds() {
    return [...document.querySelectorAll(".student-select:checked")].map((box) => box.dataset.id);
  }

  async function deleteStudentsByIds(ids, confirmMessage) {
    if (!ids.length) {
      showToast("삭제할 학생을 선택하세요.");
      return;
    }
    if (!confirm(confirmMessage)) return;

    const stop = startBusy("학생 삭제", "선택한 학생을 정리하고 있습니다.", "잠시만 기다려 주세요.", { showModel: false });
    try {
      if (ids.length === 1) {
        await api(`/api/students/${ids[0]}`, { method: "DELETE" });
      } else {
        await api("/api/students/bulk-delete", { method: "POST", body: { ids } });
      }
      ids.forEach((id) => {
        selectedStudentIds.delete(id);
        selectedReviewIds.delete(id);
      });
      showToast(`${ids.length}명 삭제됨`);
      await Promise.all([loadStudents(), loadReviewList()]);
    } catch (error) {
      showToast(error.message || "삭제 실패");
    } finally {
      stop();
    }
  }

  async function loadReviewList() {
    const tbody = document.getElementById("reviewTableBody");
    const toolbar = document.getElementById("reviewBulkActions");
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="4">불러오는 중…</td></tr>`;
    if (toolbar) toolbar.hidden = true;
    const data = await api("/api/students");
    const reviewable = data.students.filter((s) => s.status === "done" || Object.keys(s.generated || {}).length);
    if (!reviewable.length) {
      tbody.innerHTML = `<tr><td colspan="4" class="admin-muted">아직 작성된 생기부가 없습니다. ④에서 일괄 작성을 실행하세요.</td></tr>`;
      selectedReviewIds.clear();
      updateReviewSelectionUi(0);
      return;
    }
    tbody.innerHTML = reviewable
      .map((s) => {
        const checked = selectedReviewIds.has(s.id) ? "checked" : "";
        return `<tr>
          <td class="sample-select-cell">
            <label class="admin-check admin-check-row" title="선택">
              <input class="review-select admin-check-input" type="checkbox" data-id="${s.id}" ${checked}>
              <span class="admin-check-box" aria-hidden="true"></span>
            </label>
          </td>
          <td>${studentLabel(s)}</td>
          <td>${statusPill(s.status)}</td>
          <td class="admin-row-actions">
            <button class="admin-btn secondary admin-btn-sm" data-action="review" data-id="${s.id}">열기</button>
            <button class="admin-btn danger admin-btn-sm" type="button" data-action="reset-generated" data-id="${s.id}" data-label="${escapeAttr(studentLabel(s))}">작성 삭제</button>
          </td>
        </tr>`;
      })
      .join("");
    updateReviewSelectionUi(reviewable.length);
  }

  function updateReviewSelectionUi(totalCount = null) {
    const toolbar = document.getElementById("reviewBulkActions");
    const countBadge = document.getElementById("reviewCountBadge");
    const countEl = document.getElementById("reviewSelectedCount");
    const resetSelectedBtn = document.getElementById("resetSelectedReviewBtn");
    const selectAll = document.getElementById("reviewSelectAll");
    const boxes = [...document.querySelectorAll(".review-select")];
    const checkedCount = boxes.filter((box) => box.checked).length;
    const total = totalCount ?? boxes.length;

    if (countBadge) countBadge.textContent = `${total}명`;
    if (countEl) countEl.textContent = checkedCount ? `${checkedCount}명 선택됨` : "";
    if (resetSelectedBtn) resetSelectedBtn.disabled = checkedCount === 0;
    if (selectAll && boxes.length) {
      selectAll.checked = checkedCount > 0 && checkedCount === boxes.length;
      selectAll.indeterminate = checkedCount > 0 && checkedCount < boxes.length;
    }
    if (toolbar) toolbar.hidden = total === 0;
  }

  function getSelectedReviewIds() {
    return [...document.querySelectorAll(".review-select:checked")].map((box) => box.dataset.id);
  }

  async function resetGeneratedByIds(ids, confirmMessage) {
    if (!ids.length) {
      showToast("초기화할 학생을 선택하세요.");
      return;
    }
    if (!confirm(confirmMessage)) return;

    const stop = startBusy("작성본 삭제", "선택한 작성 결과를 지우고 있습니다.", "잠시만 기다려 주세요.", { showModel: false });
    try {
      if (ids.length === 1) {
        await api(`/api/students/${ids[0]}/reset`, { method: "POST" });
      } else {
        await api("/api/students/bulk-reset-generated", { method: "POST", body: { ids } });
      }
      ids.forEach((id) => selectedReviewIds.delete(id));
      showToast(`${ids.length}명 작성본 삭제됨`);
      await Promise.all([loadStudents(), loadReviewList()]);
    } catch (error) {
      showToast(error.message || "삭제 실패");
    } finally {
      stop();
    }
  }

  async function downloadStudentsExcel() {
    const token = getToken();
    let response;
    try {
      response = await fetch(`${API_BASE}/api/students/export/xlsx`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
    } catch {
      throw new Error("API 서버에 연결할 수 없습니다.");
    }
    if (!response.ok) {
      const text = await response.text();
      let detail = "다운로드 실패";
      try {
        detail = JSON.parse(text).detail || detail;
      } catch {
        detail = text || detail;
      }
      throw new Error(detail);
    }
    const blob = await response.blob();
    const stamp = new Date().toISOString().slice(0, 10).replace(/-/g, "");
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `saenggibu_${stamp}.xlsx`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function sampleDisplayLabel(s) {
    const label = String(s.label || "").trim();
    if (label && label !== "미명시") return label;
    const src = String(s.source_file || "");
    const file = src.split(/[/\\]/).pop();
    if (file) return `미명시 (${file})`;
    return `미명시 (${s.id})`;
  }

  function updateSampleSelectionUi(totalCount = null) {
    const toolbar = document.getElementById("samplesBulkActions");
    const countBadge = document.getElementById("samplesCountBadge");
    const countEl = document.getElementById("samplesSelectedCount");
    const deleteSelectedBtn = document.getElementById("deleteSelectedSamplesBtn");
    const selectAll = document.getElementById("samplesSelectAll");
    const boxes = [...document.querySelectorAll(".sample-select")];
    const checkedCount = boxes.filter((box) => box.checked).length;
    const total = totalCount ?? boxes.length;

    if (countBadge) countBadge.textContent = `${total}건`;
    if (countEl) {
      countEl.textContent = checkedCount ? `${checkedCount}건 선택됨` : "";
    }
    if (deleteSelectedBtn) {
      deleteSelectedBtn.disabled = checkedCount === 0;
    }
    if (selectAll && boxes.length) {
      selectAll.checked = checkedCount > 0 && checkedCount === boxes.length;
      selectAll.indeterminate = checkedCount > 0 && checkedCount < boxes.length;
    }
    if (toolbar) {
      toolbar.hidden = total === 0;
    }
  }

  function getSelectedSampleIds() {
    return [...document.querySelectorAll(".sample-select:checked")].map((box) => box.dataset.id);
  }

  async function deleteSamplesByIds(ids, confirmMessage) {
    if (!ids.length) {
      showToast("삭제할 샘플을 선택하세요.");
      return;
    }
    if (!confirm(confirmMessage)) return;

    const stop = startBusy("샘플 삭제", "선택한 항목을 정리하고 있습니다.", "잠시만 기다려 주세요.", { showModel: false });
    try {
      if (ids.length === 1) {
        await api(`/api/samples/${ids[0]}`, { method: "DELETE" });
      } else {
        await api("/api/samples/bulk-delete", { method: "POST", body: { ids } });
      }
      ids.forEach((id) => selectedSampleIds.delete(id));
      showToast(`${ids.length}건 삭제됨`);
      await loadSamples();
    } catch (error) {
      showToast(error.message || "삭제 실패");
    } finally {
      stop();
    }
  }

  async function loadSamples() {
    const list = document.getElementById("samplesList");
    const toolbar = document.getElementById("samplesBulkActions");
    if (!list) return;
    list.textContent = "불러오는 중…";
    if (toolbar) toolbar.hidden = true;
    const data = await api("/api/samples");
    if (!data.samples.length) {
      list.innerHTML = `<p class="admin-muted">아직 올린 샘플이 없습니다.</p>`;
      selectedSampleIds.clear();
      updateSampleSelectionUi(0);
      return;
    }
    list.innerHTML = `
      <table class="admin-table admin-sample-table">
        <thead><tr>
          <th class="sample-select-cell" aria-label="선택"></th>
          <th>이름</th>
          <th>ID</th>
          <th></th>
        </tr></thead>
        <tbody>${data.samples
          .map((s) => {
            const label = sampleDisplayLabel(s);
            const checked = selectedSampleIds.has(s.id) ? "checked" : "";
            return `<tr>
              <td class="sample-select-cell">
                <label class="admin-check admin-check-row" title="선택">
                  <input class="sample-select admin-check-input" type="checkbox" data-id="${s.id}" ${checked}>
                  <span class="admin-check-box" aria-hidden="true"></span>
                </label>
              </td>
              <td>${label}</td>
              <td class="admin-muted">${s.id}</td>
              <td><button class="admin-btn danger admin-btn-sm" type="button" data-action="delete-sample" data-id="${s.id}" data-label="${label.replace(/"/g, "&quot;")}">삭제</button></td>
            </tr>`;
          })
          .join("")}</tbody>
      </table>`;
    updateSampleSelectionUi(data.count);
  }

  document.getElementById("samplesList")?.addEventListener("change", (event) => {
    const box = event.target.closest(".sample-select");
    if (!box) return;
    if (box.checked) selectedSampleIds.add(box.dataset.id);
    else selectedSampleIds.delete(box.dataset.id);
    updateSampleSelectionUi();
  });

  document.getElementById("samplesSelectAll")?.addEventListener("change", (event) => {
    const checked = event.target.checked;
    document.querySelectorAll(".sample-select").forEach((box) => {
      box.checked = checked;
      if (checked) selectedSampleIds.add(box.dataset.id);
      else selectedSampleIds.delete(box.dataset.id);
    });
    updateSampleSelectionUi();
  });

  document.getElementById("deleteSelectedSamplesBtn")?.addEventListener("click", async () => {
    const ids = getSelectedSampleIds();
    await deleteSamplesByIds(ids, `선택한 ${ids.length}건의 샘플을 삭제할까요?`);
  });

  document.getElementById("deleteAllSamplesBtn")?.addEventListener("click", async () => {
    const data = await api("/api/samples");
    const count = data.count || 0;
    if (!count) {
      showToast("삭제할 샘플이 없습니다.");
      return;
    }
    if (!confirm(`올린 샘플 ${count}건을 전부 삭제할까요?\n이 작업은 되돌릴 수 없습니다.`)) return;

    const stop = startBusy("샘플 전체 삭제", "모든 샘플을 정리하고 있습니다.", "되돌릴 수 없습니다. 잠시만 기다려 주세요.", {
      showModel: false,
    });
    try {
      const result = await api("/api/samples", { method: "DELETE" });
      selectedSampleIds.clear();
      showToast(`${result.count || count}건 전체 삭제됨`);
      await loadSamples();
    } catch (error) {
      showToast(error.message || "전체 삭제 실패");
    } finally {
      stop();
    }
  });

  document.getElementById("adminApp")?.addEventListener("click", async (event) => {
    const btn = event.target.closest("button[data-action='delete-sample']");
    if (!btn) return;
    const id = btn.dataset.id;
    const label = btn.dataset.label || id;
    await deleteSamplesByIds([id], `「${label}」\n이 샘플을 삭제할까요?`);
  });

  async function loadStyleGuide() {
    const editor = document.getElementById("styleGuideEditor");
    if (!editor) return;
    try {
      const data = await api("/api/patterns");
      editor.value = data.style_guide || "";
    } catch {
      editor.placeholder = "①에서 샘플을 올리고 분석을 실행한 뒤 여기서 확인·수정할 수 있습니다.";
    }
  }

  function buildDetailEditor(generated) {
    const editor = document.getElementById("detailEditor");
    if (!editor) return;
    const parts = [];

    if (generated.행발) {
      parts.push(`
        <div class="admin-field">
          <label>행동특성 및 종합의견</label>
          <textarea class="admin-textarea detail-field" data-key="행발" rows="6">${escapeHtml(generated.행발)}</textarea>
        </div>`);
    }

    const setuk = generated.세특 || {};
    for (const [subject, text] of Object.entries(setuk)) {
      parts.push(`
        <div class="admin-field">
          <label>세특 · ${escapeHtml(subject)}</label>
          <textarea class="admin-textarea detail-field" data-key="세특:${escapeAttr(subject)}" rows="5">${escapeHtml(text)}</textarea>
        </div>`);
    }

    const changche = generated.창체 || {};
    for (const [key, text] of Object.entries(changche)) {
      parts.push(`
        <div class="admin-field">
          <label>창체 · ${escapeHtml(key)}</label>
          <textarea class="admin-textarea detail-field" data-key="창체:${escapeAttr(key)}" rows="4">${escapeHtml(text)}</textarea>
        </div>`);
    }

    if (!parts.length) {
      editor.innerHTML = `<p class="admin-muted">아직 생성된 본문이 없습니다.</p>`;
      return;
    }
    editor.innerHTML = parts.join("");
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(text) {
    return String(text).replace(/"/g, "&quot;");
  }

  function collectGeneratedFromEditor() {
    const generated = JSON.parse(JSON.stringify(currentStudentData?.generated || {}));
    document.querySelectorAll("#detailEditor .detail-field").forEach((el) => {
      const key = el.dataset.key;
      const value = el.value;
      if (key === "행발") {
        generated.행발 = value;
      } else if (key.startsWith("세특:")) {
        generated.세특 = generated.세특 || {};
        generated.세특[key.slice(4)] = value;
      } else if (key.startsWith("창체:")) {
        generated.창체 = generated.창체 || {};
        generated.창체[key.slice(4)] = value;
      }
    });
    return generated;
  }

  function allDetailText() {
    return [...document.querySelectorAll("#detailEditor .detail-field")]
      .map((el) => {
        const label = el.closest(".admin-field")?.querySelector("label")?.textContent || "";
        return `【${label}】\n${el.value}`;
      })
      .join("\n\n");
  }

  async function showStudent(id, fromTab = "review") {
    currentStudentId = id;
    lastTabBeforeDetail = fromTab;
    const student = await api(`/api/students/${id}`);
    currentStudentData = student;
    switchTab("detail");
    document.getElementById("detailTitle").textContent = studentLabel(student);
    document.getElementById("detailMeta").innerHTML = `상태: ${statusPill(student.status)}`;
    buildDetailEditor(student.generated || {});
  }

  loginForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    loginError.textContent = "";
    const password = document.getElementById("adminPassword").value;
    try {
      const data = await api("/api/auth/login", { method: "POST", body: { password } });
      setToken(data.token);
      showApp();
      await refreshAll();
    } catch (error) {
      loginError.textContent = error.message;
    }
  });

  logoutBtn?.addEventListener("click", () => {
    setToken("");
    showGate();
  });

  document.querySelectorAll(".admin-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab;
      if (tab !== "detail") switchTab(tab);
      if (tab === "learn" || tab === "samples") loadSamples();
    });
  });

  document.getElementById("studentsTableBody")?.addEventListener("click", async (event) => {
    const target = event.target.closest("button[data-action]");
    if (!target) return;
    const id = target.dataset.id;
    if (target.dataset.action === "review") {
      await showStudent(id, "students");
      return;
    }
    if (target.dataset.action === "run-one") {
      const studentName = target.closest("tr")?.children[1]?.textContent?.trim() || "학생";
      let section;
      try {
        section = getSelectedWriteSection();
      } catch (error) {
        showToast(error.message);
        switchTab("review");
        return;
      }
      const sectionLabel = WRITE_SECTION_LABELS[section] || section;
      try {
        await withBusy(
          `${section} 작성`,
          `${studentName} · ${sectionLabel}`,
          "완료될 때까지 기다려 주세요.",
          () =>
            api("/api/run", {
              method: "POST",
              body: { student_id: id, sections: [section] },
            })
        );
        showToast("작성 완료");
        await Promise.all([loadStudents(), loadReviewList(), loadUsage()]);
      } catch (error) {
        showToast(error.message);
      }
      return;
    }
    if (target.dataset.action === "delete-student") {
      const label = target.dataset.label || id;
      await deleteStudentsByIds([id], `「${label}」\n이 학생을 삭제할까요?\n메모·작성 결과가 모두 지워집니다.`);
    }
  });

  document.getElementById("studentsTableBody")?.addEventListener("change", (event) => {
    const box = event.target.closest(".student-select");
    if (!box) return;
    if (box.checked) selectedStudentIds.add(box.dataset.id);
    else selectedStudentIds.delete(box.dataset.id);
    updateStudentSelectionUi();
  });

  document.getElementById("studentsSelectAll")?.addEventListener("change", (event) => {
    const checked = event.target.checked;
    document.querySelectorAll(".student-select").forEach((box) => {
      box.checked = checked;
      if (checked) selectedStudentIds.add(box.dataset.id);
      else selectedStudentIds.delete(box.dataset.id);
    });
    updateStudentSelectionUi();
  });

  document.getElementById("deleteSelectedStudentsBtn")?.addEventListener("click", async () => {
    const ids = getSelectedStudentIds();
    await deleteStudentsByIds(ids, `선택한 ${ids.length}명의 학생을 삭제할까요?\n메모·작성 결과가 모두 지워집니다.`);
  });

  document.getElementById("deleteAllStudentsBtn")?.addEventListener("click", async () => {
    const data = await api("/api/students");
    const count = data.count || 0;
    if (!count) {
      showToast("삭제할 학생이 없습니다.");
      return;
    }
    if (!confirm(`등록된 학생 ${count}명을 전부 삭제할까요?\n이 작업은 되돌릴 수 없습니다.`)) return;

    const stop = startBusy("학생 전체 초기화", "모든 학생 데이터를 지우고 있습니다.", "되돌릴 수 없습니다. 잠시만 기다려 주세요.", {
      showModel: false,
    });
    try {
      const result = await api("/api/students", { method: "DELETE" });
      selectedStudentIds.clear();
      selectedReviewIds.clear();
      showToast(`${result.count || count}명 전체 삭제됨`);
      await Promise.all([loadStudents(), loadReviewList()]);
    } catch (error) {
      showToast(error.message || "전체 삭제 실패");
    } finally {
      stop();
    }
  });

  document.getElementById("reviewTableBody")?.addEventListener("click", async (event) => {
    const target = event.target.closest("button[data-action]");
    if (!target) return;
    const id = target.dataset.id;
    if (target.dataset.action === "review") {
      await showStudent(id, "review");
      return;
    }
    if (target.dataset.action === "reset-generated") {
      const label = target.dataset.label || id;
      await resetGeneratedByIds([id], `「${label}」\n작성된 생기부만 삭제할까요?\n학생 메모는 유지됩니다.`);
    }
  });

  document.getElementById("reviewTableBody")?.addEventListener("change", (event) => {
    const box = event.target.closest(".review-select");
    if (!box) return;
    if (box.checked) selectedReviewIds.add(box.dataset.id);
    else selectedReviewIds.delete(box.dataset.id);
    updateReviewSelectionUi();
  });

  document.getElementById("reviewSelectAll")?.addEventListener("change", (event) => {
    const checked = event.target.checked;
    document.querySelectorAll(".review-select").forEach((box) => {
      box.checked = checked;
      if (checked) selectedReviewIds.add(box.dataset.id);
      else selectedReviewIds.delete(box.dataset.id);
    });
    updateReviewSelectionUi();
  });

  document.getElementById("resetSelectedReviewBtn")?.addEventListener("click", async () => {
    const ids = getSelectedReviewIds();
    await resetGeneratedByIds(ids, `선택한 ${ids.length}명의 작성본을 삭제할까요?\n학생 메모는 유지됩니다.`);
  });

  document.getElementById("resetAllReviewBtn")?.addEventListener("click", async () => {
    const data = await api("/api/students");
    const count = data.students.filter((s) => Object.keys(s.generated || {}).length).length;
    if (!count) {
      showToast("삭제할 작성본이 없습니다.");
      return;
    }
    if (!confirm(`작성된 생기부 ${count}건을 전부 삭제할까요?\n학생 메모는 유지됩니다.`)) return;

    const stop = startBusy("작성본 전체 초기화", "모든 작성 결과를 지우고 있습니다.", "잠시만 기다려 주세요.", {
      showModel: false,
    });
    try {
      const result = await api("/api/students/generated/all", { method: "DELETE" });
      selectedReviewIds.clear();
      showToast(`${result.count || count}건 작성본 삭제됨`);
      await Promise.all([loadStudents(), loadReviewList()]);
    } catch (error) {
      showToast(error.message || "전체 초기화 실패");
    } finally {
      stop();
    }
  });

  document.getElementById("exportReviewExcelBtn")?.addEventListener("click", async () => {
    try {
      await downloadStudentsExcel();
      showToast("엑셀 파일을 저장했습니다.");
    } catch (error) {
      showToast(error.message);
    }
  });

  document.getElementById("backToReview")?.addEventListener("click", () => switchTab(lastTabBeforeDetail));

  document.getElementById("saveDetailBtn")?.addEventListener("click", async () => {
    if (!currentStudentId) return;
    try {
      const generated = collectGeneratedFromEditor();
      const updated = await api(`/api/students/${currentStudentId}`, {
        method: "PATCH",
        body: { generated },
      });
      currentStudentData = updated;
      showToast("저장됨");
    } catch (error) {
      showToast(error.message);
    }
  });

  document.getElementById("copyDetailBtn")?.addEventListener("click", async () => {
    const text = allDetailText();
    if (!text) {
      showToast("복사할 내용이 없습니다.");
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      showToast("클립보드에 복사됨");
    } catch {
      showToast("복사에 실패했습니다.");
    }
  });

  document.getElementById("saveStyleBtn")?.addEventListener("click", async () => {
    const style_guide = document.getElementById("styleGuideEditor").value;
    try {
      await api("/api/patterns/style-guide", { method: "PUT", body: { style_guide } });
      showToast("스타일 저장됨");
    } catch (error) {
      showToast(error.message);
    }
  });

  document.getElementById("simpleStudentForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const writeTargets = getSelectedWriteTargets();
    if (!writeTargets.length) {
      showToast("작성할 항목을 하나 이상 선택하세요.");
      return;
    }

    const subjects = {};
    if (writeTargets.includes("세특")) {
      const subject = document.getElementById("simpleSubject").value.trim();
      const activities = document.getElementById("simpleActivities").value.trim();
      if (subject) {
        subjects[subject] = { activities: activities ? [activities] : [], notes: activities };
      }
    }

    const changche = {};
    if (writeTargets.includes("자율")) {
      changche.자율 = document.getElementById("simpleJayul").value.trim();
    }
    if (writeTargets.includes("동아리")) {
      changche.동아리 = document.getElementById("simpleDongari").value.trim();
    }
    if (writeTargets.includes("진로")) {
      changche.진로 = document.getElementById("simpleJillo").value.trim();
    }

    try {
      await api("/api/students", {
        method: "POST",
        body: {
          name: document.getElementById("simpleName").value.trim(),
          grade: Number(document.getElementById("simpleGrade").value),
          class_num: Number(document.getElementById("simpleClass").value),
          number: Number(document.getElementById("simpleNumber").value),
          haengbal_notes: writeTargets.includes("행발")
            ? document.getElementById("simpleHaengbal").value.trim()
            : "",
          subjects,
          changche,
          write_targets: writeTargets,
        },
      });
      showToast("학생 추가됨");
      event.target.reset();
      resetStudentFormDefaults();
      await loadStudents();
    } catch (error) {
      showToast(error.message);
    }
  });

  async function aiParse(save) {
    const fileInput = document.getElementById("aiStudentFile");
    const text = document.getElementById("aiStudentInput").value.trim();
    const previewEl = document.getElementById("aiParsePreview");

    if (fileInput?.files?.length) {
      const file = fileInput.files[0];
      const form = new FormData();
      form.append("file", file);
      const path = save ? "/api/students/parse-file?save=true" : "/api/students/parse-file";
      const data = await api(path, { method: "POST", body: form });
      if (save) return data;
      previewEl.hidden = false;
      previewEl.textContent = JSON.stringify(data.preview, null, 2);
      return data.preview;
    }

    if (!text) throw new Error("메모를 입력하거나 파일을 선택하세요.");
    const path = save ? "/api/students/parse-save" : "/api/students/parse";
    const data = await api(path, { method: "POST", body: { text } });
    if (save) return data;
    previewEl.hidden = false;
    previewEl.textContent = JSON.stringify(data.preview, null, 2);
    return data.preview;
  }

  document.getElementById("aiParsePreviewBtn")?.addEventListener("click", async () => {
    try {
      await withBusy(
        "AI 학생 정보 정리",
        "메모·파일을 읽고 구조화하고 있습니다.",
        "완료될 때까지 창을 닫지 마세요.",
        () => aiParse(false)
      );
      showToast("미리보기 완료");
    } catch (error) {
      showToast(error.message);
    }
  });

  document.getElementById("aiParseSaveBtn")?.addEventListener("click", async () => {
    try {
      await withBusy(
        "AI 학생 등록",
        "학생 정보를 저장하고 있습니다.",
        "완료될 때까지 창을 닫지 마세요.",
        () => aiParse(true)
      );
      showToast("학생 추가됨");
      document.getElementById("aiStudentInput").value = "";
      const fileInput = document.getElementById("aiStudentFile");
      if (fileInput) fileInput.value = "";
      const nameEl = document.getElementById("aiStudentFileName");
      if (nameEl) {
        nameEl.textContent = "선택된 파일 없음";
        nameEl.classList.remove("has-file");
      }
      document.getElementById("aiParsePreview").hidden = true;
      await loadStudents();
    } catch (error) {
      showToast(error.message);
    }
  });

  document.getElementById("importStudentsForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = document.getElementById("studentsFile");
    const files = [...(input.files || [])];
    if (!files.length) {
      showToast("파일을 선택하세요.");
      return;
    }
    const check = validateFiles(files, "studentsFile");
    if (!check.ok) {
      showToast(`지원하지 않는 형식: ${formatRejectedNames(check.rejected)}`);
      return;
    }
    showToast(`${files.length}개 파일 업로드 중…`);
    let imported = 0;
    const errors = [];
    for (const file of files) {
      const form = new FormData();
      form.append("file", file);
      try {
        const data = await api("/api/students/import", { method: "POST", body: form });
        imported += data.imported || 0;
      } catch (error) {
        errors.push(`${file.name}: ${error.message}`);
      }
    }
    if (errors.length) {
      showUploadLog("studentsUploadLog", errors);
      showToast(`등록 ${imported}명 · 실패 ${errors.length}건`);
    } else {
      showUploadLog("studentsUploadLog", []);
      showToast(`${imported}명 등록됨`);
    }
    await loadStudents();
    event.target.reset();
    const nameEl = document.getElementById("studentsFileName");
    if (nameEl) {
      nameEl.textContent = "선택된 파일 없음";
      nameEl.classList.remove("has-file");
    }
  });

  document.getElementById("importSamplesForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = document.getElementById("samplesFile");
    const files = [...(input.files || [])];
    if (!files.length) {
      showToast("파일을 선택하세요.");
      return;
    }
    const check = validateFiles(files, "samplesFile");
    if (!check.ok) {
      showToast(`지원하지 않는 형식: ${formatRejectedNames(check.rejected)}`);
      return;
    }
    showToast(`${files.length}개 파일 업로드 중…`);
    let imported = 0;
    const errors = [];
    for (const file of files) {
      const form = new FormData();
      form.append("file", file);
      try {
        const data = await api("/api/samples/import", { method: "POST", body: form });
        imported += data.imported || 0;
      } catch (error) {
        errors.push(`${file.name}: ${error.message}`);
      }
    }
    if (errors.length) {
      showUploadLog("samplesUploadLog", errors);
      showToast(`샘플 ${imported}건 · 실패 ${errors.length}건`);
    } else {
      showUploadLog("samplesUploadLog", []);
      showToast(`샘플 ${imported}건 등록됨`);
    }
    await loadSamples();
    event.target.reset();
    const nameEl = document.getElementById("samplesFileName");
    if (nameEl) {
      nameEl.textContent = "선택된 파일 없음";
      nameEl.classList.remove("has-file");
    }
  });

  document.getElementById("analyzeBtn")?.addEventListener("click", async () => {
    const useGemini = document.getElementById("analyzeGemini").checked;
    try {
      await withBusy(
        "문체·분량 분석",
        useGemini ? "AI가 스타일 가이드를 정리하고 있습니다." : "샘플 문체·분량을 계산하고 있습니다.",
        useGemini ? "샘플 수에 따라 1~3분 걸릴 수 있습니다." : "곧 완료됩니다.",
        () => api(`/api/analyze?use_gemini=${useGemini}`, { method: "POST" })
      );
      showToast("분석 완료 · ② 스타일 설정에서 확인하세요");
      await loadStyleGuide();
    } catch (error) {
      showToast(error.message);
    }
  });

  document.getElementById("runBatchBtn")?.addEventListener("click", async () => {
    const limit = Number(document.getElementById("runLimit").value || 0) || null;
    let section;
    try {
      section = getSelectedWriteSection();
    } catch (error) {
      showToast(error.message);
      return;
    }
    const sectionLabel = WRITE_SECTION_LABELS[section] || section;
    const limitText = limit ? `${limit}명` : `${section} 미작성 전원`;
    try {
      const data = await withBusy(
        `${section} 일괄 작성`,
        `${limitText} · ${sectionLabel}`,
        "완료될 때까지 기다려 주세요.",
        () =>
          api("/api/run", {
            method: "POST",
            body: { sections: [section], limit },
          })
      );
      const errCount = (data.errors || []).length;
      const msg = data.message || `완료 ${data.processed || 0}명${errCount ? `, 오류 ${errCount}건` : ""}`;
      showToast(msg);
      document.getElementById("runLog").textContent = JSON.stringify(data, null, 2);
      await Promise.all([loadStudents(), loadReviewList(), loadUsage()]);
    } catch (error) {
      showToast(error.message);
    }
  });

  async function refreshAll() {
    await loadSystemInfo();
    await Promise.all([loadStudents(), loadSamples(), loadReviewList(), loadStyleGuide(), loadUsage()]);
    switchTab("learn");
  }

  document.querySelector(".admin-grade-pick")?.addEventListener("click", (event) => {
    const btn = event.target.closest(".admin-grade-btn");
    if (!btn) return;
    setStudentGrade(btn.dataset.grade);
  });

  document.getElementById("guideBtn")?.addEventListener("click", openGuideModal);
  document.getElementById("guideCloseBtn")?.addEventListener("click", closeGuideModal);
  document.getElementById("guideModal")?.addEventListener("click", (event) => {
    if (event.target.id === "guideModal") closeGuideModal();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !document.getElementById("guideModal")?.hidden) {
      closeGuideModal();
    }
  });

  document.getElementById("studentWriteTargets")?.addEventListener("change", (event) => {
    if (event.target.classList.contains("write-target")) {
      const selected = getSelectedWriteTargets();
      if (!selected.length) {
        event.target.checked = true;
        showToast("최소 한 항목은 선택해야 합니다.");
        return;
      }
      updateStudentMemoPanels();
    }
  });

  async function bootstrap() {
    setupFilePickers();
    initStudentFormControls();
    restoreWriteSectionChoice();
    document.getElementById("writeSectionChoices")?.addEventListener("change", updateWriteSectionUi);
    updateWriteSectionUi();
    updateStudentMemoPanels();
    const expectedPanels = ["panelLearn", "panelStyle", "panelStudents", "panelReview"];
    const missing = expectedPanels.filter((id) => !document.getElementById(id));
    if (missing.length) {
      showToast("관리자 UI가 오래됐습니다. NAS-UI-동기화.bat 실행 후 Ctrl+F5");
    }
    const token = getToken();
    if (!token) {
      showGate();
      return;
    }

    try {
      await api("/api/auth/me");
      showApp();
      await refreshAll();
    } catch {
      setToken("");
      showGate();
    }
  }

  bootstrap();
})();
