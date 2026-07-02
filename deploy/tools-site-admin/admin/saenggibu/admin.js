(() => {
  "use strict";

  const TOKEN_KEY = "sgb_admin_token";
  const configuredBase = (document.body.dataset.apiBase || "").replace(/\/$/, "");
  const API_BASE = configuredBase || window.location.origin;
  const ASSETS_BASE = (document.body.dataset.assetsBase || "").replace(/\/$/, "");

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
        const file = input.files && input.files[0];
        if (!nameEl) return;
        if (file) {
          nameEl.textContent = file.name;
          nameEl.classList.add("has-file");
        } else {
          nameEl.textContent = "선택된 파일 없음";
          nameEl.classList.remove("has-file");
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

  const panels = {
    students: document.getElementById("panelStudents"),
    samples: document.getElementById("panelSamples"),
    run: document.getElementById("panelRun"),
    detail: document.getElementById("panelDetail"),
  };

  let currentStudentId = null;

  function showToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 2200);
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

    const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
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
      btn.classList.toggle("active", btn.dataset.tab === name);
    });
    Object.entries(panels).forEach(([key, panel]) => {
      if (!panel) return;
      panel.hidden = key !== name;
    });
  }

  function statusPill(status) {
    return `<span class="status-pill status-${status}">${status}</span>`;
  }

  async function loadStudents() {
    const tbody = document.getElementById("studentsTableBody");
    tbody.innerHTML = `<tr><td colspan="5">불러오는 중…</td></tr>`;
    const data = await api("/api/students");
    if (!data.students.length) {
      tbody.innerHTML = `<tr><td colspan="5" class="admin-muted">등록된 학생이 없습니다.</td></tr>`;
      return;
    }
    tbody.innerHTML = data.students
      .map((s) => {
        const subjects = Object.keys(s.subjects || {}).join(", ") || "-";
        return `<tr>
          <td>${s.grade}-${s.class_num} ${s.number}번 ${s.name}</td>
          <td>${statusPill(s.status)}</td>
          <td>${subjects}</td>
          <td><button class="admin-btn secondary" data-action="show" data-id="${s.id}">보기</button></td>
          <td><button class="admin-btn secondary" data-action="run-one" data-id="${s.id}">작성</button></td>
        </tr>`;
      })
      .join("");
  }

  async function loadSamples() {
    const list = document.getElementById("samplesList");
    list.textContent = "불러오는 중…";
    const data = await api("/api/samples");
    if (!data.samples.length) {
      list.innerHTML = `<p class="admin-muted">샘플이 없습니다. JSON/TSV 파일을 업로드하세요.</p>`;
      return;
    }
    list.innerHTML = `<ul>${data.samples
      .map((s) => `<li><strong>${s.label}</strong> <span class="admin-muted">(${s.id})</span></li>`)
      .join("")}</ul>`;
  }

  async function showStudent(id) {
    currentStudentId = id;
    const student = await api(`/api/students/${id}`);
    switchTab("detail");
    document.getElementById("detailTitle").textContent = `${student.grade}-${student.class_num} ${student.number}번 ${student.name}`;
    document.getElementById("detailMeta").innerHTML = `상태: ${statusPill(student.status)}`;
    document.getElementById("detailOutput").textContent = JSON.stringify(student.generated || {}, null, 2);
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
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  document.getElementById("studentsTableBody")?.addEventListener("click", async (event) => {
    const target = event.target.closest("button[data-action]");
    if (!target) return;
    const id = target.dataset.id;
    if (target.dataset.action === "show") {
      await showStudent(id);
      return;
    }
    if (target.dataset.action === "run-one") {
      showToast("작성 중… 시간이 걸릴 수 있습니다.");
      try {
        await api("/api/run", { method: "POST", body: { student_id: id } });
        showToast("작성 완료");
        await loadStudents();
      } catch (error) {
        showToast(error.message);
      }
    }
  });

  document.getElementById("importStudentsForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = document.getElementById("studentsFile").files[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    try {
      const data = await api("/api/students/import", { method: "POST", body: form });
      showToast(`${data.imported}명 등록됨`);
      await loadStudents();
      event.target.reset();
    } catch (error) {
      showToast(error.message);
    }
  });

  document.getElementById("importSamplesForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = document.getElementById("samplesFile").files[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    try {
      const data = await api("/api/samples/import", { method: "POST", body: form });
      showToast(`샘플 ${data.imported}건 등록됨`);
      await loadSamples();
      event.target.reset();
    } catch (error) {
      showToast(error.message);
    }
  });

  document.getElementById("analyzeBtn")?.addEventListener("click", async () => {
    const useGemini = document.getElementById("analyzeGemini").checked;
    showToast("패턴 분석 중…");
    try {
      await api(`/api/analyze?use_gemini=${useGemini}`, { method: "POST" });
      showToast("패턴 분석 완료");
    } catch (error) {
      showToast(error.message);
    }
  });

  document.getElementById("runBatchBtn")?.addEventListener("click", async () => {
    const limit = Number(document.getElementById("runLimit").value || 0) || null;
    showToast("일괄 작성 시작…");
    try {
      const data = await api("/api/run", {
        method: "POST",
        body: { status: "pending", limit },
      });
      showToast(`완료 ${data.processed || 0}명, 오류 ${(data.errors || []).length}건`);
      document.getElementById("runLog").textContent = JSON.stringify(data, null, 2);
      await loadStudents();
    } catch (error) {
      showToast(error.message);
    }
  });

  document.getElementById("backToStudents")?.addEventListener("click", () => switchTab("students"));

  async function refreshAll() {
    await Promise.all([loadStudents(), loadSamples()]);
    switchTab("students");
  }

  async function bootstrap() {
    setupFilePickers();
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
