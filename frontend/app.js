// =========================================================
// Ustun frontend — auth (JWT + refresh) + har bir modul bilan ishlash
// =========================================================

const API = window.APP_CONFIG.API_BASE;

// ---------- Token va sessiya boshqaruvi ----------
function saveSession(data) {
  localStorage.setItem("ustun_token", data.access_token);
  localStorage.setItem("ustun_refresh_token", data.refresh_token);
  if (data.company_name) localStorage.setItem("ustun_company_name", data.company_name);
  if (data.role) localStorage.setItem("ustun_role", data.role);
}

function getToken() { return localStorage.getItem("ustun_token"); }
function getRefreshToken() { return localStorage.getItem("ustun_refresh_token"); }
function getRole() { return localStorage.getItem("ustun_role"); }
function getCompanyName() { return localStorage.getItem("ustun_company_name"); }

function clearSession() {
  localStorage.removeItem("ustun_token");
  localStorage.removeItem("ustun_refresh_token");
  localStorage.removeItem("ustun_company_name");
  localStorage.removeItem("ustun_role");
}

function isLoggedIn() { return !!getToken(); }

// ---------- Access token muddati tugaganda avtomatik yangilash ----------
async function tryRefreshToken() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;
  try {
    const res = await fetch(`${API}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    localStorage.setItem("ustun_token", data.access_token);
    localStorage.setItem("ustun_refresh_token", data.refresh_token);
    return true;
  } catch (_) {
    return false;
  }
}

// ---------- Umumiy so'rov yuboruvchi (fetch wrapper) ----------
async function api(path, options = {}, _isRetry = false) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API}${path}`, { ...options, headers });

  if (res.status === 401) {
    if (!_isRetry) {
      const refreshed = await tryRefreshToken();
      if (refreshed) return api(path, options, true);
    }
    clearSession();
    showAuthScreen();
    throw new Error("Sessiya tugagan, qayta kiring");
  }

  let body = null;
  try { body = await res.json(); } catch (_) { /* body bo'sh bo'lishi mumkin */ }

  if (!res.ok) {
    const message = body?.error?.message || "Noma'lum xatolik yuz berdi";
    const err = new Error(message);
    err.detail = body?.error;
    throw err;
  }
  return body;
}

// ---------- Toast bildirishnomalar ----------
function toast(message, type = "success") {
  const container = document.getElementById("toastContainer");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transition = "opacity 0.3s ease";
    setTimeout(() => el.remove(), 300);
  }, 3200);
}

// ---------- Modal oynalar (umumiy) ----------
function openModal(titleText, bodyHtml, onSubmit, submitLabel = "Saqlash") {
  const box = document.getElementById("modalBox");
  box.innerHTML = `
    <h3>${titleText}</h3>
    <form class="modal-form" id="dynamicModalForm">
      ${bodyHtml}
      <div class="modal-actions">
        <button type="button" class="btn-ghost" id="modalCancelBtn">Bekor qilish</button>
        <button type="submit" class="btn-primary">${submitLabel}</button>
      </div>
    </form>
  `;
  document.getElementById("modalOverlay").classList.remove("hidden");
  document.getElementById("modalCancelBtn").addEventListener("click", closeModal);
  document.getElementById("dynamicModalForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const submitBtn = e.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    try {
      await onSubmit(e.target);
    } finally {
      submitBtn.disabled = false;
    }
  });
}

function closeModal() {
  document.getElementById("modalOverlay").classList.add("hidden");
}

document.getElementById("modalOverlay").addEventListener("click", (e) => {
  if (e.target.id === "modalOverlay") closeModal();
});

// ---------- Ekranlar orasida almashish ----------
function showAuthScreen() {
  document.getElementById("authScreen").classList.remove("hidden");
  document.getElementById("appShell").classList.add("hidden");
}

function showAppShell() {
  document.getElementById("authScreen").classList.add("hidden");
  document.getElementById("appShell").classList.remove("hidden");
  const companyName = getCompanyName() || "";
  document.getElementById("companyNameLabel").textContent = companyName;
  document.getElementById("roleLabel").textContent = roleLabelText(getRole());
  document.getElementById("userAvatar").textContent = companyName.charAt(0).toUpperCase() || "U";
  applyRoleGates();
  loadCurrentView();
  refreshNotifications();
}

function roleLabelText(role) {
  const map = { owner: "Egasi", cashier: "Sotuvchi", storekeeper: "Omborchi", receptionist: "Resepshin" };
  return map[role] || role || "";
}

// ---------- Rolga qarab qaysi tab/bo'lim ko'rinishini belgilash ----------
const ROLE_VISIBILITY = {
  owner: ["inventory", "finance", "pms", "employees", "settings"],
  cashier: [],
  storekeeper: ["inventory"],
  receptionist: ["pms"],
};

function applyRoleGates() {
  const allowed = ROLE_VISIBILITY[getRole()] || [];
  document.querySelectorAll("[data-role-gate]").forEach((el) => {
    const gate = el.getAttribute("data-role-gate");
    el.classList.toggle("hidden", !allowed.includes(gate));
  });
}

// ---------- Auth ekrani: tablar ----------
document.querySelectorAll(".auth-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".auth-tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    const target = tab.dataset.tab;
    document.getElementById("loginForm").classList.toggle("hidden", target !== "login");
    document.getElementById("registerForm").classList.toggle("hidden", target !== "register");
  });
});

document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errEl = document.getElementById("loginError");
  errEl.textContent = "";
  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        phone: document.getElementById("loginPhone").value.trim(),
        password: document.getElementById("loginPassword").value,
      }),
    });
    saveSession(data);
    showAppShell();
    toast(`Xush kelibsiz, ${data.company_name}!`);
  } catch (err) {
    errEl.textContent = err.message;
  }
});

document.getElementById("registerForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errEl = document.getElementById("registerError");
  errEl.textContent = "";
  try {
    const data = await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        company_name: document.getElementById("regCompanyName").value.trim(),
        business_type: document.getElementById("regBusinessType").value,
        owner_full_name: document.getElementById("regOwnerName").value.trim(),
        phone: document.getElementById("regPhone").value.trim(),
        password: document.getElementById("regPassword").value,
      }),
    });
    saveSession(data);
    showAppShell();
    toast("Xush kelibsiz! Tizim tayyor");
  } catch (err) {
    errEl.textContent = err.message;
  }
});

document.getElementById("logoutBtn").addEventListener("click", async () => {
  const refreshToken = getRefreshToken();
  if (refreshToken) {
    try {
      await fetch(`${API}/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch (_) { /* jim o'tkazamiz */ }
  }
  clearSession();
  showAuthScreen();
});

// ---------- Modul (ledger-tab) almashish ----------
document.querySelectorAll(".nav-item").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`view-${tab.dataset.view}`).classList.add("active");
    loadCurrentView();
  });
});

function currentViewName() {
  return document.querySelector(".nav-item.active")?.dataset.view || "home";
}

function loadCurrentView() {
  const view = currentViewName();
  if (view === "home") loadHomeView();
  if (view === "sales") loadSalesView();
  if (view === "inventory") loadInventoryView();
  if (view === "finance") loadFinanceView();
  if (view === "hrms") loadHrmsView();
  if (view === "pms") loadPmsView();
  if (view === "settings") loadSettingsView();
}

function money(n) {
  return Number(n || 0).toLocaleString("uz-UZ");
}

function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

function renderPagination(containerId, page, totalPages, onPageChange) {
  const el = document.getElementById(containerId);
  if (totalPages <= 1) { el.innerHTML = ""; return; }
  el.innerHTML = `
    <button id="${containerId}-prev" ${page <= 1 ? "disabled" : ""}>← Oldingi</button>
    <span>${page} / ${totalPages}</span>
    <button id="${containerId}-next" ${page >= totalPages ? "disabled" : ""}>Keyingi →</button>
  `;
  document.getElementById(`${containerId}-prev`)?.addEventListener("click", () => onPageChange(page - 1));
  document.getElementById(`${containerId}-next`)?.addEventListener("click", () => onPageChange(page + 1));
}

function showEmptyState(tableId, emptyId, isEmpty) {
  document.getElementById(tableId).classList.toggle("hidden", isEmpty);
  document.getElementById(emptyId)?.classList.toggle("hidden", !isEmpty);
}

// =========================================================
// GLOBAL QIDIRUV (topbar)
// =========================================================
function switchToView(viewName) {
  document.querySelectorAll(".nav-item").forEach((t) => t.classList.remove("active"));
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  document.querySelector(`.nav-item[data-view="${viewName}"]`)?.classList.add("active");
  document.getElementById(`view-${viewName}`)?.classList.add("active");
  loadCurrentView();
}

async function runGlobalSearch(query) {
  const panel = document.getElementById("globalSearchPanel");
  if (query.length < 2) {
    panel.classList.add("hidden");
    return;
  }

  const sections = [];

  try {
    const products = await api(`/inventory/products?search=${encodeURIComponent(query)}&page_size=5`);
    if (products.items.length > 0) {
      sections.push({
        title: "Mahsulotlar",
        items: products.items.map((p) => ({
          label: p.name,
          detail: `qoldiq: ${p.quantity}`,
          view: "inventory",
        })),
      });
    }
  } catch (_) { /* jim */ }

  try {
    const transactions = await api(`/finance/transactions?search=${encodeURIComponent(query)}&page_size=5`);
    if (transactions.items.length > 0) {
      sections.push({
        title: "Tranzaksiyalar",
        items: transactions.items.map((t) => ({
          label: t.source || (t.type === "income" ? "Kirim" : "Chiqim"),
          detail: money(t.amount) + " so'm",
          view: "finance",
        })),
      });
    }
  } catch (_) { /* finance.view ruxsati yo'q */ }

  try {
    const employees = await api("/auth/users");
    const matches = employees.filter((e) =>
      e.full_name.toLowerCase().includes(query.toLowerCase()) || e.phone.includes(query)
    ).slice(0, 5);
    if (matches.length > 0) {
      sections.push({
        title: "Xodimlar",
        items: matches.map((e) => ({
          label: e.full_name,
          detail: roleLabelText(e.role),
          view: "hrms",
        })),
      });
    }
  } catch (_) { /* employees.manage ruxsati yo'q */ }

  if (sections.length === 0) {
    panel.innerHTML = `<div class="notif-panel-header">Natija topilmadi</div>`;
  } else {
    panel.innerHTML = sections
      .map((s) => `
        <div class="notif-panel-header">${s.title}</div>
        <ul class="notif-list">
          ${s.items.map((item) => `
            <li onclick="switchToView('${item.view}'); document.getElementById('globalSearchPanel').classList.add('hidden'); document.getElementById('globalSearchInput').value='';">
              <span>${item.label}</span>
              <span style="color:var(--ink-soft);">${item.detail}</span>
            </li>`).join("")}
        </ul>`)
      .join("");
  }
  panel.classList.remove("hidden");
}

document.getElementById("globalSearchInput").addEventListener("input", debounce((e) => {
  runGlobalSearch(e.target.value.trim());
}, 350));

document.addEventListener("click", (e) => {
  const panel = document.getElementById("globalSearchPanel");
  const input = document.getElementById("globalSearchInput");
  if (!panel.classList.contains("hidden") && !panel.contains(e.target) && e.target !== input) {
    panel.classList.add("hidden");
  }
});

// =========================================================
// BILDIRISHNOMALAR (past qoldiq ogohlantirishi)
// =========================================================
let notificationsCache = [];

async function refreshNotifications() {
  try {
    const response = await api("/inventory/products?page_size=100");
    const lowStock = response.items.filter((p) => p.quantity < LOW_STOCK_THRESHOLD);
    notificationsCache = lowStock.map((p) => ({
      text: `"${p.name}" kam qoldi`,
      detail: `${p.quantity} ${p.unit}`,
    }));

    const badge = document.getElementById("notifBadge");
    if (notificationsCache.length > 0) {
      badge.textContent = notificationsCache.length;
      badge.classList.remove("hidden");
    } else {
      badge.classList.add("hidden");
    }
  } catch (_) { /* ruxsat yo'q bo'lsa jim o'tkaziladi */ }
}

function renderNotificationPanel() {
  const list = document.getElementById("notifList");
  list.innerHTML = notificationsCache.length === 0
    ? `<li class="notif-empty">Hozircha bildirishnoma yo'q</li>`
    : notificationsCache
        .map((n) => `<li><span>${n.text}</span><span class="mono" style="color:var(--ink-soft);">${n.detail}</span></li>`)
        .join("");
}

document.getElementById("notifBellBtn").addEventListener("click", (e) => {
  e.stopPropagation();
  const panel = document.getElementById("notifPanel");
  const willOpen = panel.classList.contains("hidden");
  if (willOpen) renderNotificationPanel();
  panel.classList.toggle("hidden");
});

document.addEventListener("click", (e) => {
  const panel = document.getElementById("notifPanel");
  const bell = document.getElementById("notifBellBtn");
  if (!panel.classList.contains("hidden") && !panel.contains(e.target) && !bell.contains(e.target)) {
    panel.classList.add("hidden");
  }
});

// =========================================================
// BOSH SAHIFA (Dashboard Home)
// =========================================================
const LOW_STOCK_THRESHOLD = 5;

function auditActionText(action) {
  const map = {
    "employee.create": "Yangi xodim qo'shildi",
    "employee.update": "Xodim ma'lumoti yangilandi",
    "employee.deactivate": "Xodim faolsizlantirildi",
    "employee.reactivate": "Xodim qayta faollashtirildi",
    "sale.create": "Sotuv amalga oshirildi",
    "booking.checkout": "Mehmon chiqarildi",
  };
  return map[action] || action;
}

async function loadHomeView() {
  const companyName = getCompanyName() || "";
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Xayrli tong" : hour < 18 ? "Xayrli kun" : "Xayrli kech";
  document.getElementById("homeGreeting").textContent = `${greeting}, ${companyName}`;

  // --- Ombor: mahsulotlar va kam qolganlar ---
  const productsResponse = await api("/inventory/products?page_size=100");
  const products = productsResponse.items;
  const lowStock = products.filter((p) => p.quantity < LOW_STOCK_THRESHOLD);

  const lowStockTbody = document.querySelector("#lowStockTable tbody");
  lowStockTbody.innerHTML = lowStock
    .map((p) => `<tr><td>${p.name}</td><td class="mono">${p.quantity}</td></tr>`)
    .join("");
  showEmptyState("lowStockTable", "lowStockEmpty", lowStock.length === 0);

  // --- Stat kartalar (faqat ruxsati bor va mavjud bo'lganlari) ---
  const stats = [{ label: "Mahsulotlar soni", value: products.length }];

  let financeSummary = null;
  try {
    financeSummary = await api("/finance/summary");
    stats.push({ label: "Umumiy tushum", value: money(financeSummary.total_income) + " so'm" });
    stats.push({ label: "Sof foyda", value: money(financeSummary.net_profit) + " so'm", accent: true });
  } catch (_) { /* finance.view ruxsati yo'q — jim o'tkaziladi */ }

  try {
    const occ = await api("/pms/analytics/occupancy");
    if (occ.total_rooms > 0) {
      stats.push({ label: "Mehmonxona to'lilik", value: `${occ.occupancy_rate}%` });
    }
  } catch (_) { /* pms.manage ruxsati yo'q yoki modul ishlatilmaydi */ }

  document.getElementById("homeStatsRow").innerHTML = stats
    .map((s) => `
      <div class="stat-card ${s.accent ? "accent" : ""}">
        <span class="stat-label">${s.label}</span>
        <span class="stat-value mono">${s.value}</span>
      </div>`)
    .join("");

  // --- Onboarding checklist (faqat egasi uchun ma'noli) ---
  if (getRole() === "owner") {
    let employeesCount = 1;
    try {
      const employees = await api("/auth/users");
      employeesCount = employees.length;
    } catch (_) { /* jim o'tkaziladi */ }

    const steps = [
      { done: products.length > 0, text: "Birinchi mahsulotingizni qo'shing" },
      { done: employeesCount > 1, text: "Birinchi xodimingizni qo'shing" },
      { done: !!(financeSummary && financeSummary.total_income > 0), text: "Birinchi sotuvingizni amalga oshiring" },
    ];
    const remaining = steps.filter((s) => !s.done);

    const onboardingCard = document.getElementById("onboardingCard");
    if (remaining.length > 0) {
      onboardingCard.classList.remove("hidden");
      document.getElementById("onboardingList").innerHTML = steps
        .map((s) => `
          <li style="display:flex; align-items:center; gap:10px; ${s.done ? "opacity:0.5;" : ""}">
            <span style="width:18px;height:18px;border-radius:50%;border:2px solid var(--primary);
                         display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;
                         font-size:0.7rem; color:var(--primary);">${s.done ? "✓" : ""}</span>
            <span style="${s.done ? "text-decoration:line-through; color:var(--ink-soft);" : ""}">${s.text}</span>
          </li>`)
        .join("");
    } else {
      onboardingCard.classList.add("hidden");
    }

    // --- So'nggi voqealar (audit-log) ---
    try {
      const auditResponse = await api("/audit-log?page_size=5");
      document.getElementById("homeActivityCard").classList.remove("hidden");
      const list = document.getElementById("recentActivityList");
      list.innerHTML = auditResponse.items.length === 0
        ? `<li style="color:var(--ink-soft);">Hali hech qanday voqea yo'q</li>`
        : auditResponse.items
            .map((e) => `
              <li>
                <span>${auditActionText(e.action)}${e.details ? " — " + e.details : ""}</span>
                <span style="color:var(--ink-soft); font-size:0.78rem;">${new Date(e.created_at).toLocaleString("uz-UZ")}</span>
              </li>`)
            .join("");
    } catch (_) { /* audit.view ruxsati yo'q */ }
  }
}

// =========================================================
// CSV EKSPORT (umumiy yordamchi)
// =========================================================
function downloadCSV(filename, rows) {
  const csvContent = rows
    .map((row) => row.map((cell) => `"${String(cell ?? "").replace(/"/g, '""')}"`).join(","))
    .join("\n");
  // \uFEFF — Excel'da o'zbekcha harflar (masalan o', g') to'g'ri ko'rinishi uchun (UTF-8 BOM)
  const blob = new Blob(["\uFEFF" + csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

document.getElementById("exportProductsCsvBtn").addEventListener("click", async () => {
  try {
    const response = await api(`/inventory/products?page_size=1000&search=${encodeURIComponent(inventoryState.search || "")}`);
    const rows = [["Nomi", "Birligi", "Tannarx", "Sotish narxi", "Qoldiq"]];
    response.items.forEach((p) => rows.push([p.name, p.unit, p.purchase_price, p.sale_price, p.quantity]));
    downloadCSV(`mahsulotlar_${new Date().toISOString().slice(0, 10)}.csv`, rows);
    toast("CSV fayl yuklab olindi");
  } catch (err) {
    toast(err.message, "error");
  }
});

document.getElementById("exportTransactionsCsvBtn").addEventListener("click", async () => {
  try {
    const response = await api(`/finance/transactions?page_size=1000&search=${encodeURIComponent(financeState.search || "")}`);
    const rows = [["Turi", "Summasi", "Manbasi", "Vaqti"]];
    response.items.forEach((t) => rows.push([
      t.type === "income" ? "Kirim" : "Chiqim",
      t.amount,
      t.source || "",
      new Date(t.created_at).toLocaleString("uz-UZ"),
    ]));
    downloadCSV(`tranzaksiyalar_${new Date().toISOString().slice(0, 10)}.csv`, rows);
    toast("CSV fayl yuklab olindi");
  } catch (err) {
    toast(err.message, "error");
  }
});

// =========================================================
// SAVDO
// =========================================================
let saleCart = [];
let productsCache = [];

async function loadSalesView() {
  const response = await api("/inventory/products?page_size=100");
  productsCache = response.items;
  const select = document.getElementById("saleProductSelect");
  select.innerHTML = productsCache
    .map((p) => `<option value="${p.id}">${p.name} (qoldiq: ${p.quantity})</option>`)
    .join("");
  renderCart();
}

document.getElementById("saleAddItemBtn").addEventListener("click", () => {
  const productId = Number(document.getElementById("saleProductSelect").value);
  const qty = Number(document.getElementById("saleQty").value);
  const product = productsCache.find((p) => p.id === productId);
  if (!product || !qty || qty <= 0) return;

  const existing = saleCart.find((i) => i.product_id === productId);
  if (existing) existing.qty += qty;
  else saleCart.push({ product_id: productId, name: product.name, price: product.sale_price, qty });

  renderCart();
});

function renderCart() {
  const tbody = document.querySelector("#saleCartTable tbody");
  tbody.innerHTML = saleCart
    .map((item, idx) => `
      <tr>
        <td>${item.name}</td>
        <td>${item.qty}</td>
        <td class="mono">${money(item.price * item.qty)}</td>
        <td><button class="link-btn danger" onclick="removeCartItem(${idx})">olib tashlash</button></td>
      </tr>`)
    .join("");
  const total = saleCart.reduce((sum, i) => sum + i.price * i.qty, 0);
  document.getElementById("saleCartTotal").textContent = money(total);
}

function removeCartItem(idx) {
  saleCart.splice(idx, 1);
  renderCart();
}

document.getElementById("saleCheckoutBtn").addEventListener("click", async () => {
  if (saleCart.length === 0) {
    toast("Chekka mahsulot qo'shing", "error");
    return;
  }
  try {
    await api("/sales/", {
      method: "POST",
      body: JSON.stringify({
        items: saleCart.map((i) => ({ product_id: i.product_id, quantity: i.qty })),
      }),
    });
    toast("Chek muvaffaqiyatli yopildi");
    saleCart = [];
    await loadSalesView();
    refreshNotifications();
  } catch (err) {
    toast(err.message, "error");
  }
});

// =========================================================
// OMBOR
// =========================================================
let inventoryState = { page: 1, search: "" };

async function loadInventoryView(page = inventoryState.page, search = inventoryState.search) {
  inventoryState = { page, search };
  const response = await api(`/inventory/products?page=${page}&page_size=10&search=${encodeURIComponent(search)}`);
  const products = response.items;

  const tbody = document.querySelector("#productsTable tbody");
  tbody.innerHTML = products
    .map((p) => `
      <tr>
        <td>${p.name}</td>
        <td>${p.unit}</td>
        <td class="mono">${money(p.purchase_price)}</td>
        <td class="mono">${money(p.sale_price)}</td>
        <td class="mono">${p.quantity}</td>
      </tr>`)
    .join("");

  showEmptyState("productsTable", "productsEmptyState", products.length === 0);
  renderPagination("productsPagination", response.page, response.total_pages, (p) => loadInventoryView(p, search));
}

document.getElementById("productSearchInput").addEventListener("input", debounce((e) => {
  loadInventoryView(1, e.target.value.trim());
}, 350));

document.getElementById("openProductModalBtn").addEventListener("click", () => {
  openModal("Yangi mahsulot", `
    <label>Nomi <input type="text" name="name" required /></label>
    <label>Birligi <input type="text" name="unit" value="dona" /></label>
    <label>Tannarx <input type="number" name="purchase_price" min="0" value="0" /></label>
    <label>Sotish narxi <input type="number" name="sale_price" min="0" required /></label>
    <label>Boshlang'ich qoldiq <input type="number" name="quantity" min="0" value="0" /></label>
  `, async (form) => {
    const fd = new FormData(form);
    try {
      await api("/inventory/products", {
        method: "POST",
        body: JSON.stringify({
          name: fd.get("name").trim(),
          unit: fd.get("unit").trim() || "dona",
          purchase_price: Number(fd.get("purchase_price")) || 0,
          sale_price: Number(fd.get("sale_price")),
          quantity: Number(fd.get("quantity")) || 0,
        }),
      });
      toast("Mahsulot qo'shildi");
      closeModal();
      await loadInventoryView(1, inventoryState.search);
      refreshNotifications();
    } catch (err) {
      toast(err.message, "error");
    }
  });
});

document.getElementById("openStockInModalBtn").addEventListener("click", async () => {
  const response = await api("/inventory/products?page_size=100");
  const options = response.items.map((p) => `<option value="${p.id}">${p.name}</option>`).join("");
  openModal("Omborga kirim", `
    <label>Mahsulot <select name="product_id">${options}</select></label>
    <label>Miqdor <input type="number" name="quantity" min="0.01" step="0.01" required /></label>
    <label>Izoh (ixtiyoriy) <input type="text" name="reason" /></label>
  `, async (form) => {
    const fd = new FormData(form);
    try {
      await api("/inventory/stock-in", {
        method: "POST",
        body: JSON.stringify({
          product_id: Number(fd.get("product_id")),
          quantity: Number(fd.get("quantity")),
          reason: fd.get("reason")?.trim() || null,
        }),
      });
      toast("Kirim qilindi");
      closeModal();
      await loadInventoryView(inventoryState.page, inventoryState.search);
      refreshNotifications();
    } catch (err) {
      toast(err.message, "error");
    }
  }, "Kirim qilish");
});

// =========================================================
// MOLIYA
// =========================================================
let financeState = { page: 1, search: "" };

async function loadFinanceView() {
  const summary = await api("/finance/summary");
  document.getElementById("statIncome").textContent = money(summary.total_income);
  document.getElementById("statExpense").textContent = money(summary.total_expense);
  document.getElementById("statProfit").textContent = money(summary.net_profit);

  await loadTransactions(1, "");
  await loadDailySalesChart();
  await loadTopProducts();
  await loadRecurringExpenses();
}

async function loadRecurringExpenses() {
  try {
    const templates = await api("/finance/recurring-expenses");
    const tbody = document.querySelector("#recurringExpensesTable tbody");
    tbody.innerHTML = templates.length === 0
      ? ""
      : templates
          .map((t) => `
            <tr>
              <td>${t.source}</td>
              <td class="mono">${money(t.amount)}</td>
              <td>${t.day_of_month}-kun</td>
              <td><span class="status-pill ${t.is_active ? "status-available" : "status-checked_out"}">${t.is_active ? "Faol" : "To'xtatilgan"}</span></td>
              <td>${t.is_active ? `<button class="link-btn danger" onclick="deactivateRecurringExpense(${t.id})">to'xtatish</button>` : ""}</td>
            </tr>`)
          .join("");
  } catch (_) { /* finance.manage ruxsati yo'q */ }
}

async function deactivateRecurringExpense(id) {
  try {
    await api(`/finance/recurring-expenses/${id}/deactivate`, { method: "POST" });
    toast("To'xtatildi");
    await loadRecurringExpenses();
  } catch (err) {
    toast(err.message, "error");
  }
}

document.getElementById("openRecurringExpenseModalBtn").addEventListener("click", () => {
  openModal("Yangi takrorlanuvchi xarajat", `
    <label>Sababi <input type="text" name="source" placeholder="Masalan: Ijaraga" required /></label>
    <label>Summa <input type="number" name="amount" min="1" required /></label>
    <label>Har oyning nechinchi kunida <input type="number" name="day_of_month" min="1" max="28" value="1" required /></label>
  `, async (form) => {
    const fd = new FormData(form);
    try {
      await api("/finance/recurring-expenses", {
        method: "POST",
        body: JSON.stringify({
          source: fd.get("source").trim(),
          amount: Number(fd.get("amount")),
          day_of_month: Number(fd.get("day_of_month")),
        }),
      });
      toast("Shablon yaratildi");
      closeModal();
      await loadRecurringExpenses();
    } catch (err) {
      toast(err.message, "error");
    }
  }, "Yaratish");
});

async function loadTransactions(page = financeState.page, search = financeState.search) {
  financeState = { page, search };
  const response = await api(`/finance/transactions?page=${page}&page_size=10&search=${encodeURIComponent(search)}`);
  const tbody = document.querySelector("#transactionsTable tbody");
  tbody.innerHTML = response.items
    .map((t) => `
      <tr>
        <td>${t.type === "income" ? "Kirim" : "Chiqim"}</td>
        <td class="mono">${money(t.amount)}</td>
        <td>${t.source || "-"}</td>
        <td>${new Date(t.created_at).toLocaleString("uz-UZ")}</td>
      </tr>`)
    .join("");
  renderPagination("transactionsPagination", response.page, response.total_pages, (p) => loadTransactions(p, search));
}

document.getElementById("openExpenseModalBtn").addEventListener("click", () => {
  openModal("Yangi xarajat (chiqim)", `
    <label>Summa <input type="number" name="amount" min="1" required /></label>
    <label>Sababi <input type="text" name="source" placeholder="Masalan: Ijaraga - iyul oyi" required /></label>
  `, async (form) => {
    const fd = new FormData(form);
    try {
      await api("/finance/expenses", {
        method: "POST",
        body: JSON.stringify({
          amount: Number(fd.get("amount")),
          source: fd.get("source").trim(),
        }),
      });
      toast("Xarajat qo'shildi");
      closeModal();
      await loadFinanceView();
    } catch (err) {
      toast(err.message, "error");
    }
  }, "Qo'shish");
});

document.getElementById("transactionSearchInput").addEventListener("input", debounce((e) => {
  loadTransactions(1, e.target.value.trim());
}, 350));

async function loadDailySalesChart() {
  try {
    const data = await api("/finance/analytics/daily-sales?days=14");
    const chartEl = document.getElementById("dailySalesChart");
    if (data.length === 0) {
      chartEl.innerHTML = `<div class="empty-state" style="padding:20px 0;">
        <div class="empty-hint">Hali savdo tarixi yo'q</div></div>`;
      return;
    }
    const max = Math.max(...data.map((d) => d.total_income), 1);
    chartEl.innerHTML = data.map((d) => {
      const heightPct = Math.max(4, (d.total_income / max) * 100);
      return `<div class="mini-bar" style="height:${heightPct}%" title="${d.date}: ${money(d.total_income)} so'm"></div>`;
    }).join("");
  } catch (_) { /* ruxsat yo'q bo'lsa jim o'tkaziladi */ }
}

async function loadTopProducts() {
  try {
    const data = await api("/sales/analytics/top-products?days=30&limit=5");
    const list = document.getElementById("topProductsList");
    if (data.length === 0) {
      list.innerHTML = `<li style="color:var(--ink-soft);">Hali sotuv tarixi yo'q</li>`;
      return;
    }
    list.innerHTML = data
      .map((p) => `<li><span>${p.product_name}</span><span class="mono">${money(p.total_revenue)} so'm</span></li>`)
      .join("");
  } catch (_) { /* jim o'tkaziladi */ }
}

// =========================================================
// XODIMLAR (HRMS)
// =========================================================
async function loadHrmsView() {
  const shifts = await api("/hrms/shifts/me");
  const tbody = document.querySelector("#myShiftsTable tbody");
  tbody.innerHTML = shifts
    .map((s) => `
      <tr>
        <td>${new Date(s.clock_in).toLocaleString("uz-UZ")}</td>
        <td>${s.clock_out ? new Date(s.clock_out).toLocaleString("uz-UZ") : "— (davom etmoqda)"}</td>
        <td class="mono">${s.duration_hours ?? "-"}</td>
      </tr>`)
    .join("");

  if (getRole() === "owner") {
    try {
      const employees = await api("/auth/users");
      const empTbody = document.querySelector("#employeesTable tbody");
      empTbody.innerHTML = employees
        .map((u) => `
          <tr>
            <td>${u.full_name}</td>
            <td>${u.phone}</td>
            <td>${roleLabelText(u.role)}</td>
            <td class="mono">${u.role === "owner" ? "-" : money(u.hourly_rate) + " so'm/soat"}</td>
            <td><span class="status-pill ${u.is_active ? "status-available" : "status-checked_out"}">${u.is_active ? "Faol" : "Faolsiz"}</span></td>
            <td style="display:flex; gap:10px;">
              ${u.role === "owner" ? "" : (
                u.is_active
                  ? `<button class="link-btn" onclick="payEmployee(${u.id})">ish haqini to'lash</button>
                     <button class="link-btn danger" onclick="deactivateEmployee(${u.id})">faolsizlantirish</button>`
                  : `<button class="link-btn" onclick="reactivateEmployee(${u.id})">qayta faollashtirish</button>`
              )}
            </td>
          </tr>`)
        .join("");
    } catch (_) { /* ruxsat yo'q bo'lsa jim o'tkazib yuboriladi */ }
  }
}

async function deactivateEmployee(userId) {
  if (!confirm("Bu xodimni faolsizlantirmoqchimisiz? U tizimga kira olmay qoladi.")) return;
  try {
    await api(`/auth/users/${userId}/deactivate`, { method: "POST" });
    toast("Xodim faolsizlantirildi");
    await loadHrmsView();
  } catch (err) {
    toast(err.message, "error");
  }
}

async function reactivateEmployee(userId) {
  try {
    await api(`/auth/users/${userId}/reactivate`, { method: "POST" });
    toast("Xodim qayta faollashtirildi");
    await loadHrmsView();
  } catch (err) {
    toast(err.message, "error");
  }
}

async function payEmployee(userId) {
  if (!confirm("Bu xodimning barcha to'lanmagan smenalari uchun ish haqi hisoblanadi va moliyaga chiqim sifatida yoziladi. Davom etamizmi?")) return;
  try {
    const result = await api(`/hrms/payroll/pay/${userId}`, { method: "POST" });
    toast(`To'landi: ${money(result.total_amount)} so'm (${result.total_hours} soat)`);
    await loadHrmsView();
  } catch (err) {
    toast(err.message, "error");
  }
}

document.getElementById("clockInBtn").addEventListener("click", async () => {
  try {
    await api("/hrms/shifts/clock-in", { method: "POST" });
    toast("Ish boshlandi");
    await loadHrmsView();
  } catch (err) {
    toast(err.message, "error");
  }
});

document.getElementById("clockOutBtn").addEventListener("click", async () => {
  try {
    await api("/hrms/shifts/clock-out", { method: "POST" });
    toast("Ish tugatildi");
    await loadHrmsView();
  } catch (err) {
    toast(err.message, "error");
  }
});

document.getElementById("openEmployeeModalBtn").addEventListener("click", () => {
  openModal("Yangi xodim qo'shish", `
    <label>F.I.Sh. <input type="text" name="full_name" required /></label>
    <label>Telefon raqami <input type="text" name="phone" required /></label>
    <label>Parol <input type="password" name="password" minlength="6" required /></label>
    <label>Lavozim
      <select name="role">
        <option value="cashier">Sotuvchi</option>
        <option value="storekeeper">Omborchi</option>
        <option value="receptionist">Resepshin (mehmonxona)</option>
      </select>
    </label>
    <label>Soatlik stavka (ish haqi hisoblash uchun, ixtiyoriy)
      <input type="number" name="hourly_rate" min="0" value="0" />
    </label>
  `, async (form) => {
    const fd = new FormData(form);
    try {
      await api("/auth/users", {
        method: "POST",
        body: JSON.stringify({
          full_name: fd.get("full_name").trim(),
          phone: fd.get("phone").trim(),
          password: fd.get("password"),
          role: fd.get("role"),
          hourly_rate: Number(fd.get("hourly_rate")) || 0,
        }),
      });
      toast("Xodim qo'shildi");
      closeModal();
      await loadHrmsView();
    } catch (err) {
      toast(err.message, "error");
    }
  });
});

// =========================================================
// MEHMONXONA (PMS)
// =========================================================
async function loadPmsView() {
  const roomsResponse = await api("/pms/rooms");
  const rooms = roomsResponse.items || roomsResponse; // hozircha /pms/rooms sahifalanmagan (oddiy ro'yxat)
  const tbody = document.querySelector("#roomsTable tbody");
  tbody.innerHTML = rooms
    .map((r) => `
      <tr>
        <td>${r.room_number}</td>
        <td>${r.room_type}</td>
        <td class="mono">${money(r.price_per_night)}</td>
        <td><span class="status-pill status-${r.status}">${roomStatusText(r.status)}</span></td>
      </tr>`)
    .join("");

  try {
    const occ = await api("/pms/analytics/occupancy");
    document.getElementById("occupancyRate").textContent = `${occ.occupancy_rate}%`;
    document.getElementById("occupancyDetail").textContent = `${occ.occupied_rooms} / ${occ.total_rooms} xona band`;
  } catch (_) { /* jim o'tkaziladi */ }

  try {
    const bookings = await api("/pms/bookings");
    const bTbody = document.querySelector("#bookingsTable tbody");
    bTbody.innerHTML = bookings
      .map((b) => `
        <tr>
          <td>${b.guest_name}</td>
          <td>${b.nights}</td>
          <td class="mono">${money(b.total_price)}</td>
          <td><span class="status-pill status-${b.status}">${b.status === "active" ? "Yashamoqda" : "Chiqib ketgan"}</span></td>
          <td>${b.status === "active" ? `<button class="link-btn" onclick="checkoutBooking(${b.id})">checkout</button>` : ""}</td>
        </tr>`)
      .join("");
  } catch (_) { /* ruxsat bo'lmasa jadval bo'sh qoladi */ }
}

function roomStatusText(status) {
  return { available: "Bo'sh", occupied: "Band", maintenance: "Texnik xizmatda" }[status] || status;
}

document.getElementById("openRoomModalBtn").addEventListener("click", () => {
  openModal("Yangi xona", `
    <label>Xona raqami <input type="text" name="room_number" required /></label>
    <label>Turi <input type="text" name="room_type" value="standard" /></label>
    <label>Kechasi narxi <input type="number" name="price_per_night" min="0" required /></label>
  `, async (form) => {
    const fd = new FormData(form);
    try {
      await api("/pms/rooms", {
        method: "POST",
        body: JSON.stringify({
          room_number: fd.get("room_number").trim(),
          room_type: fd.get("room_type").trim() || "standard",
          price_per_night: Number(fd.get("price_per_night")),
        }),
      });
      toast("Xona qo'shildi");
      closeModal();
      await loadPmsView();
    } catch (err) {
      toast(err.message, "error");
    }
  });
});

document.getElementById("openBookingModalBtn").addEventListener("click", async () => {
  const roomsResponse = await api("/pms/rooms");
  const rooms = (roomsResponse.items || roomsResponse).filter((r) => r.status === "available");
  const options = rooms.length
    ? rooms.map((r) => `<option value="${r.id}">${r.room_number} (${money(r.price_per_night)} so'm/kecha)</option>`).join("")
    : `<option disabled>Bo'sh xona yo'q</option>`;

  openModal("Mehmonni joylashtirish", `
    <label>Xona <select name="room_id">${options}</select></label>
    <label>Mehmon F.I.Sh. <input type="text" name="guest_name" required /></label>
    <label>Telefon (ixtiyoriy) <input type="text" name="guest_phone" /></label>
    <label>Necha kecha <input type="number" name="nights" min="1" value="1" required /></label>
  `, async (form) => {
    const fd = new FormData(form);
    try {
      await api("/pms/bookings", {
        method: "POST",
        body: JSON.stringify({
          room_id: Number(fd.get("room_id")),
          guest_name: fd.get("guest_name").trim(),
          guest_phone: fd.get("guest_phone")?.trim() || null,
          nights: Number(fd.get("nights")),
        }),
      });
      toast("Mehmon joylashtirildi");
      closeModal();
      await loadPmsView();
    } catch (err) {
      toast(err.message, "error");
    }
  }, "Joylashtirish");
});

async function checkoutBooking(bookingId) {
  try {
    await api(`/pms/bookings/${bookingId}/checkout`, { method: "POST" });
    toast("Mehmon chiqarildi, to'lov moliyaga yozildi");
    await loadPmsView();
  } catch (err) {
    toast(err.message, "error");
  }
}

// =========================================================
// SOZLAMALAR
// =========================================================
async function loadSettingsView() {
  const company = await api("/auth/company");
  document.getElementById("settingsCompanyName").value = company.name;
  document.getElementById("settingsBusinessType").value = company.business_type;
  document.getElementById("settingsTaxId").value = company.tax_id || "";
}

document.getElementById("companyForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const data = await api("/auth/company", {
      method: "PATCH",
      body: JSON.stringify({
        name: document.getElementById("settingsCompanyName").value.trim(),
        business_type: document.getElementById("settingsBusinessType").value,
        tax_id: document.getElementById("settingsTaxId").value.trim() || null,
      }),
    });
    localStorage.setItem("ustun_company_name", data.name);
    document.getElementById("companyNameLabel").textContent = data.name;
    document.getElementById("userAvatar").textContent = data.name.charAt(0).toUpperCase();
    toast("Sozlamalar saqlandi");
  } catch (err) {
    toast(err.message, "error");
  }
});

// ---------- Ilova ishga tushishi ----------
if (isLoggedIn()) {
  showAppShell();
} else {
  showAuthScreen();
}
