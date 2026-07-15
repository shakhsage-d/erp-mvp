// =========================================================
// MikroERP frontend — auth (JWT) + har bir modul bilan ishlash
// =========================================================

const API = window.APP_CONFIG.API_BASE;

// ---------- Token va sessiya boshqaruvi ----------
function saveSession(data) {
  localStorage.setItem("mikroerp_token", data.access_token);
  localStorage.setItem("mikroerp_company_name", data.company_name);
  localStorage.setItem("mikroerp_role", data.role);
}

function getToken() { return localStorage.getItem("mikroerp_token"); }
function getRole() { return localStorage.getItem("mikroerp_role"); }
function getCompanyName() { return localStorage.getItem("mikroerp_company_name"); }

function clearSession() {
  localStorage.removeItem("mikroerp_token");
  localStorage.removeItem("mikroerp_company_name");
  localStorage.removeItem("mikroerp_role");
}

function isLoggedIn() { return !!getToken(); }

// ---------- Umumiy so'rov yuboruvchi (fetch wrapper) ----------
async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API}${path}`, { ...options, headers });

  if (res.status === 401) {
    // Token yaroqsiz/eskirgan — qayta kirishga yo'naltiramiz
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

// ---------- Ekranlar orasida almashish ----------
function showAuthScreen() {
  document.getElementById("authScreen").classList.remove("hidden");
  document.getElementById("appShell").classList.add("hidden");
}

function showAppShell() {
  document.getElementById("authScreen").classList.add("hidden");
  document.getElementById("appShell").classList.remove("hidden");
  document.getElementById("companyNameLabel").textContent = getCompanyName() || "";
  document.getElementById("roleLabel").textContent = roleLabelText(getRole());
  applyRoleGates();
  loadCurrentView();
}

function roleLabelText(role) {
  const map = { owner: "Egasi", cashier: "Sotuvchi", storekeeper: "Omborchi", receptionist: "Resepshin" };
  return map[role] || role || "";
}

// ---------- Rolga qarab qaysi tab/bo'lim ko'rinishini belgilash ----------
// ESLATMA: bu FAQAT interfeysni soddalashtirish uchun (foydalanuvchi
// ishlata olmaydigan tugmalarni ko'rmasin). Haqiqiy xavfsizlik tekshiruvi
// har doim backend'da (`require_permission`) amalga oshadi — frontend
// bu yerda xato qilsa ham, backend baribir ruxsatsiz amalni rad etadi.
const ROLE_VISIBILITY = {
  owner: ["inventory", "finance", "pms", "employees"],
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

// ---------- Auth ekrani: tablar (Kirish / Ro'yxatdan o'tish) ----------
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
  } catch (err) {
    errEl.textContent = err.message;
  }
});

document.getElementById("logoutBtn").addEventListener("click", () => {
  clearSession();
  showAuthScreen();
});

// ---------- Modul (ledger-tab) almashish ----------
document.querySelectorAll(".ledger-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".ledger-tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`view-${tab.dataset.view}`).classList.add("active");
    loadCurrentView();
  });
});

function currentViewName() {
  return document.querySelector(".ledger-tab.active")?.dataset.view || "sales";
}

function loadCurrentView() {
  const view = currentViewName();
  if (view === "sales") loadSalesView();
  if (view === "inventory") loadInventoryView();
  if (view === "finance") loadFinanceView();
  if (view === "hrms") loadHrmsView();
  if (view === "pms") loadPmsView();
}

function setMessage(elId, text, isError = false) {
  const el = document.getElementById(elId);
  el.textContent = text;
  el.className = "form-message " + (isError ? "error" : "success");
}

function money(n) {
  return Number(n || 0).toLocaleString("uz-UZ");
}

// =========================================================
// SAVDO
// =========================================================
let saleCart = []; // {product_id, name, price, qty}
let productsCache = [];

async function loadSalesView() {
  // ERP 2.0: backend endi sahifalab qaytaradi ({items, total, ...}).
  // Hozircha to'liq sahifalash UI'si keyingi (UI/UX) bosqichda qo'shiladi —
  // shu oraliqda page_size=100 bilan "deyarli barchasi"ni ko'rsatamiz.
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
        <td><button class="link-btn" onclick="removeCartItem(${idx})">olib tashlash</button></td>
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
    setMessage("saleMessage", "Chekka mahsulot qo'shing", true);
    return;
  }
  try {
    await api("/sales/", {
      method: "POST",
      body: JSON.stringify({
        items: saleCart.map((i) => ({ product_id: i.product_id, quantity: i.qty })),
      }),
    });
    setMessage("saleMessage", "Chek muvaffaqiyatli yopildi ✅");
    saleCart = [];
    await loadSalesView();
  } catch (err) {
    setMessage("saleMessage", err.message, true);
  }
});

// =========================================================
// OMBOR
// =========================================================
async function loadInventoryView() {
  const response = await api("/inventory/products?page_size=100");
  const products = response.items;
  productsCache = products;

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

  const stockSelect = document.getElementById("stockInProductSelect");
  stockSelect.innerHTML = products.map((p) => `<option value="${p.id}">${p.name}</option>`).join("");
}

document.getElementById("productForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/inventory/products", {
      method: "POST",
      body: JSON.stringify({
        name: document.getElementById("prodName").value.trim(),
        unit: document.getElementById("prodUnit").value.trim() || "dona",
        purchase_price: Number(document.getElementById("prodPurchasePrice").value) || 0,
        sale_price: Number(document.getElementById("prodSalePrice").value),
        quantity: Number(document.getElementById("prodQty").value) || 0,
      }),
    });
    setMessage("productMessage", "Mahsulot qo'shildi ✅");
    e.target.reset();
    document.getElementById("prodUnit").value = "dona";
    await loadInventoryView();
  } catch (err) {
    setMessage("productMessage", err.message, true);
  }
});

document.getElementById("stockInForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/inventory/stock-in", {
      method: "POST",
      body: JSON.stringify({
        product_id: Number(document.getElementById("stockInProductSelect").value),
        quantity: Number(document.getElementById("stockInQty").value),
        reason: document.getElementById("stockInReason").value.trim() || null,
      }),
    });
    setMessage("stockInMessage", "Kirim qilindi ✅");
    e.target.reset();
    await loadInventoryView();
  } catch (err) {
    setMessage("stockInMessage", err.message, true);
  }
});

// =========================================================
// MOLIYA
// =========================================================
async function loadFinanceView() {
  const summary = await api("/finance/summary");
  document.getElementById("statIncome").textContent = money(summary.total_income);
  document.getElementById("statExpense").textContent = money(summary.total_expense);
  document.getElementById("statProfit").textContent = money(summary.net_profit);

  const transactionsResponse = await api("/finance/transactions?page_size=50");
  const transactions = transactionsResponse.items;
  const tbody = document.querySelector("#transactionsTable tbody");
  tbody.innerHTML = transactions
    .map((t) => `
      <tr>
        <td>${t.type === "income" ? "Kirim" : "Chiqim"}</td>
        <td class="mono">${money(t.amount)}</td>
        <td>${t.source || "-"}</td>
        <td>${new Date(t.created_at).toLocaleString("uz-UZ")}</td>
      </tr>`)
    .join("");
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
        .map((u) => `<tr><td>${u.full_name}</td><td>${u.phone}</td><td>${roleLabelText(u.role)}</td></tr>`)
        .join("");
    } catch (_) { /* ruxsat yo'q bo'lsa jim o'tkazib yuboriladi */ }
  }
}

document.getElementById("clockInBtn").addEventListener("click", async () => {
  try {
    await api("/hrms/shifts/clock-in", { method: "POST" });
    setMessage("shiftMessage", "Ish boshlandi ✅");
    await loadHrmsView();
  } catch (err) {
    setMessage("shiftMessage", err.message, true);
  }
});

document.getElementById("clockOutBtn").addEventListener("click", async () => {
  try {
    await api("/hrms/shifts/clock-out", { method: "POST" });
    setMessage("shiftMessage", "Ish tugatildi ✅");
    await loadHrmsView();
  } catch (err) {
    setMessage("shiftMessage", err.message, true);
  }
});

document.getElementById("employeeForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/auth/users", {
      method: "POST",
      body: JSON.stringify({
        full_name: document.getElementById("empName").value.trim(),
        phone: document.getElementById("empPhone").value.trim(),
        password: document.getElementById("empPassword").value,
        role: document.getElementById("empRole").value,
      }),
    });
    setMessage("employeeMessage", "Xodim qo'shildi ✅");
    e.target.reset();
    await loadHrmsView();
  } catch (err) {
    setMessage("employeeMessage", err.message, true);
  }
});

// =========================================================
// MEHMONXONA (PMS)
// =========================================================
let roomsCache = [];

async function loadPmsView() {
  roomsCache = await api("/pms/rooms");
  const tbody = document.querySelector("#roomsTable tbody");
  tbody.innerHTML = roomsCache
    .map((r) => `
      <tr>
        <td>${r.room_number}</td>
        <td>${r.room_type}</td>
        <td class="mono">${money(r.price_per_night)}</td>
        <td><span class="status-pill status-${r.status}">${roomStatusText(r.status)}</span></td>
      </tr>`)
    .join("");

  const availableRooms = roomsCache.filter((r) => r.status === "available");
  const select = document.getElementById("bookingRoomSelect");
  select.innerHTML = availableRooms
    .map((r) => `<option value="${r.id}">${r.room_number} (${money(r.price_per_night)} so'm/kecha)</option>`)
    .join("") || "<option disabled>Bo'sh xona yo'q</option>";

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

document.getElementById("roomForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/pms/rooms", {
      method: "POST",
      body: JSON.stringify({
        room_number: document.getElementById("roomNumber").value.trim(),
        room_type: document.getElementById("roomType").value.trim() || "standard",
        price_per_night: Number(document.getElementById("roomPrice").value),
      }),
    });
    setMessage("roomMessage", "Xona qo'shildi ✅");
    e.target.reset();
    document.getElementById("roomType").value = "standard";
    await loadPmsView();
  } catch (err) {
    setMessage("roomMessage", err.message, true);
  }
});

document.getElementById("bookingForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/pms/bookings", {
      method: "POST",
      body: JSON.stringify({
        room_id: Number(document.getElementById("bookingRoomSelect").value),
        guest_name: document.getElementById("guestName").value.trim(),
        guest_phone: document.getElementById("guestPhone").value.trim() || null,
        nights: Number(document.getElementById("bookingNights").value),
      }),
    });
    setMessage("bookingMessage", "Mehmon joylashtirildi ✅");
    e.target.reset();
    document.getElementById("bookingNights").value = 1;
    await loadPmsView();
  } catch (err) {
    setMessage("bookingMessage", err.message, true);
  }
});

async function checkoutBooking(bookingId) {
  try {
    await api(`/pms/bookings/${bookingId}/checkout`, { method: "POST" });
    await loadPmsView();
  } catch (err) {
    alert(err.message);
  }
}

// ---------- Ilova ishga tushishi ----------
if (isLoggedIn()) {
  showAppShell();
} else {
  showAuthScreen();
}
