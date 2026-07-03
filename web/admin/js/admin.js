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
  let busyTimer = null;
  let busyStartedAt = 0;

  const busyOverlay = document.getElementById("busyOverlay");
  const busyMessage = document.getElementById("busyMessage");
  const busyHint = document.getElementById("busyHint");

  function showToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 3200);
  }

  function setBusy(active, message = "처리 중…", hint = "AI 응답을 기다리는 중입니다. 1~2분 걸릴 수 있습니다.") {
    if (active) {
      document.body.classList.add("admin-is-busy");
      if (busyOverlay) busyOverlay.hidden = false;
      if (busyMessage) busyMessage.textContent = message;
      if (busyHint) busyHint.textContent = hint;
      return;
    }
    if (busyTimer) {
      clearInterval(busyTimer);
      busyTimer = null;
    }
    document.body.classList.remove("admin-is-busy");
    if (busyOverlay) busyOverlay.hidden = true;
  }

  function startBusy(message, hint = "AI 응답을 기다리는 중입니다. 1~2분 걸릴 수 있습니다.") {
    busyStartedAt = Date.now();
    setBusy(true, message, hint);
    if (busyTimer) clearInterval(busyTimer);
    busyTimer = setInterval(() => {
      const sec = Math.floor((Date.now() - busyStartedAt) / 1000);
      if (busyMessage) busyMessage.textContent = `${message} (${sec}초)`;
    }, 1000);
    return () => setBusy(false);
  }

  async function withBusy(message, hint, fn) {
    const stop = startBusy(message, hint);
    try {
      return await fn();
    } finally {
      stop();
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
    const labels = { pending: "대기", done: "완료", error: "오류", in_progress: "작성 중" };
    return `<span class="status-pill status-${status}">${labels[status] || status}</span>`;
  }

  function studentLabel(s) {
    return `${s.grade}-${s.class_num} ${s.number}번 ${s.name}`;
  }

  function formatUsage(usage) {
    if (!usage) return "";
    if (usage.unlimited) {
      return `Pro 플랜 · 이번 달 ${usage.generations_used}건 작성`;
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
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="4">불러오는 중…</td></tr>`;
    const data = await api("/api/students");
    if (!data.students.length) {
      tbody.innerHTML = `<tr><td colspan="4" class="admin-muted">등록된 학생이 없습니다.</td></tr>`;
      return;
    }
    tbody.innerHTML = data.students
      .map((s) => {
        const subjects = Object.keys(s.subjects || {}).join(", ") || "-";
        const actions =
          s.status === "done"
            ? `<button class="admin-btn secondary" data-action="review" data-id="${s.id}">검토</button>`
            : `<button class="admin-btn secondary" data-action="run-one" data-id="${s.id}">작성</button>`;
        return `<tr>
          <td>${studentLabel(s)}</td>
          <td>${statusPill(s.status)}</td>
          <td>${subjects}</td>
          <td>${actions}</td>
        </tr>`;
      })
      .join("");
  }

  async function loadReviewList() {
    const tbody = document.getElementById("reviewTableBody");
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="3">불러오는 중…</td></tr>`;
    const data = await api("/api/students");
    const reviewable = data.students.filter((s) => s.status === "done" || Object.keys(s.generated || {}).length);
    if (!reviewable.length) {
      tbody.innerHTML = `<tr><td colspan="3" class="admin-muted">아직 작성된 생기부가 없습니다. ④에서 일괄 작성을 실행하세요.</td></tr>`;
      return;
    }
    tbody.innerHTML = reviewable
      .map(
        (s) => `<tr>
          <td>${studentLabel(s)}</td>
          <td>${statusPill(s.status)}</td>
          <td><button class="admin-btn secondary" data-action="review" data-id="${s.id}">열기</button></td>
        </tr>`
      )
      .join("");
  }

  function sampleDisplayLabel(s) {
    const label = String(s.label || "").trim();
    if (label && label !== "미명시") return label;
    const src = String(s.source_file || "");
    const file = src.split(/[/\\]/).pop();
    if (file) return `미명시 (${file})`;
    return `미명시 (${s.id})`;
  }

  function updateSampleSelectionUi() {
    const toolbar = document.getElementById("samplesBulkActions");
    const countEl = document.getElementById("samplesSelectedCount");
    const deleteSelectedBtn = document.getElementById("deleteSelectedSamplesBtn");
    const selectAll = document.getElementById("samplesSelectAll");
    const boxes = [...document.querySelectorAll(".sample-select")];
    const checkedCount = boxes.filter((box) => box.checked).length;

    if (countEl) {
      countEl.textContent = checkedCount ? `${checkedCount}건 선택` : "";
    }
    if (deleteSelectedBtn) {
      deleteSelectedBtn.disabled = checkedCount === 0;
    }
    if (selectAll && boxes.length) {
      selectAll.checked = checkedCount > 0 && checkedCount === boxes.length;
      selectAll.indeterminate = checkedCount > 0 && checkedCount < boxes.length;
    }
    if (toolbar) {
      toolbar.hidden = boxes.length === 0;
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

    const stop = startBusy("샘플 삭제 중…", "선택한 항목을 정리하고 있습니다.");
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
      updateSampleSelectionUi();
      return;
    }
    list.innerHTML = `
      <p class="admin-muted">${data.count}건 · 체크 후 선택 삭제 또는 전체 삭제</p>
      <table class="admin-table admin-sample-table">
        <thead><tr>
          <th class="sample-select-cell"></th>
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
                <input class="sample-select" type="checkbox" data-id="${s.id}" ${checked}>
              </td>
              <td>${label}</td>
              <td class="admin-muted">${s.id}</td>
              <td><button class="admin-btn danger admin-btn-sm" type="button" data-action="delete-sample" data-id="${s.id}" data-label="${label.replace(/"/g, "&quot;")}">삭제</button></td>
            </tr>`;
          })
          .join("")}</tbody>
      </table>`;
    updateSampleSelectionUi();
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

    const stop = startBusy("샘플 전체 삭제 중…", "목록과 파일을 정리하고 있습니다.");
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
      try {
        await withBusy(
          "AI 생기부 작성 중…",
          "학생 한 명 분량이라 30초~2분 정도 걸릴 수 있습니다.",
          () => api("/api/run", { method: "POST", body: { student_id: id } })
        );
        showToast("작성 완료");
        await Promise.all([loadStudents(), loadReviewList(), loadUsage()]);
      } catch (error) {
        showToast(error.message);
      }
    }
  });

  document.getElementById("reviewTableBody")?.addEventListener("click", async (event) => {
    const target = event.target.closest("button[data-action='review']");
    if (!target) return;
    await showStudent(target.dataset.id, "review");
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
    const subject = document.getElementById("simpleSubject").value.trim();
    const activities = document.getElementById("simpleActivities").value.trim();
    const subjects = {};
    if (subject) {
      subjects[subject] = { activities: activities ? [activities] : [], notes: activities };
    }
    try {
      await api("/api/students", {
        method: "POST",
        body: {
          name: document.getElementById("simpleName").value.trim(),
          grade: Number(document.getElementById("simpleGrade").value),
          class_num: Number(document.getElementById("simpleClass").value),
          number: Number(document.getElementById("simpleNumber").value),
          haengbal_notes: document.getElementById("simpleHaengbal").value.trim(),
          subjects,
        },
      });
      showToast("학생 추가됨");
      event.target.reset();
      document.getElementById("simpleGrade").value = "2";
      document.getElementById("simpleClass").value = "1";
      document.getElementById("simpleNumber").value = "1";
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
        "AI가 학생 정보 정리 중…",
        "메모·파일을 읽고 구조화하는 중입니다.",
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
        "AI가 학생 등록 중…",
        "학생 정보를 저장할 때까지 잠시만 기다려 주세요.",
        () => aiParse(true)
      );
      showToast("학생 등록됨");
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
    const hint = useGemini
      ? "AI가 스타일 가이드를 정리합니다. 샘플 수에 따라 1~3분 걸릴 수 있습니다."
      : "샘플 문체·분량을 계산하는 중입니다.";
    try {
      await withBusy("문체·분량 분석 중…", hint, () =>
        api(`/api/analyze?use_gemini=${useGemini}`, { method: "POST" })
      );
      showToast("분석 완료 · ② 스타일 설정에서 확인하세요");
      await loadStyleGuide();
    } catch (error) {
      showToast(error.message);
    }
  });

  document.getElementById("runBatchBtn")?.addEventListener("click", async () => {
    const limit = Number(document.getElementById("runLimit").value || 0) || null;
    const limitText = limit ? `${limit}명` : "전원";
    try {
      const data = await withBusy(
        "일괄 AI 작성 중…",
        `${limitText} 분량입니다. 학생 수에 따라 수 분 이상 걸릴 수 있습니다.`,
        () =>
          api("/api/run", {
            method: "POST",
            body: { status: "pending", limit },
          })
      );
      const errCount = (data.errors || []).length;
      showToast(`완료 ${data.processed || 0}명${errCount ? `, 오류 ${errCount}건` : ""}`);
      document.getElementById("runLog").textContent = JSON.stringify(data, null, 2);
      await Promise.all([loadStudents(), loadReviewList(), loadUsage()]);
    } catch (error) {
      showToast(error.message);
    }
  });

  async function refreshAll() {
    await Promise.all([loadStudents(), loadSamples(), loadReviewList(), loadStyleGuide(), loadUsage()]);
    switchTab("learn");
  }

  async function bootstrap() {
    setupFilePickers();
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
