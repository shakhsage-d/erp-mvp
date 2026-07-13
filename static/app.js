// app.js
// Bu fayl bevosita FastAPI backendiga (o'sha bitta "single source of truth")
// so'rov yuboradi. Telegram bot ham xuddi shu endpointlarga so'rov jo'natadi -
// shuning uchun ikkalasi doim bir xil ma'lumotni ko'rsatadi.

const API = ""; // bo'sh qoldirilgan - chunki dashboard shu backendning o'zidan ochiladi

async function loadProducts() {
  const res = await fetch(`${API}/inventory/products`);
  const products = await res.json();

  // Jadvalni to'ldirish
  const tbody = document.querySelector("#products-table tbody");
  tbody.innerHTML = "";
  const select = document.getElementById("s-product");
  select.innerHTML = "";

  products.forEach((p) => {
    const row = document.createElement("tr");
    row.innerHTML = `<td>${p.id}</td><td>${p.name}</td><td>${p.sale_price}</td><td>${p.quantity} ${p.unit}</td>`;
    tbody.appendChild(row);

    const option = document.createElement("option");
    option.value = p.id;
    option.textContent = `${p.name} (qoldiq: ${p.quantity})`;
    select.appendChild(option);
  });
}

async function loadFinance() {
  const summaryRes = await fetch(`${API}/finance/summary`);
  const summary = await summaryRes.json();
  document.getElementById("stat-income").textContent = summary.total_income;
  document.getElementById("stat-expense").textContent = summary.total_expense;
  document.getElementById("stat-profit").textContent = summary.net_profit;

  const txRes = await fetch(`${API}/finance/transactions`);
  const transactions = await txRes.json();
  const tbody = document.querySelector("#transactions-table tbody");
  tbody.innerHTML = "";
  transactions.slice(0, 10).forEach((t) => {
    const row = document.createElement("tr");
    const typeLabel = t.type === "income" ? "🟢 Kirim" : "🔴 Chiqim";
    row.innerHTML = `<td>${typeLabel}</td><td>${t.amount}</td><td>${t.source ?? "-"}</td><td>${new Date(t.created_at).toLocaleString()}</td>`;
    tbody.appendChild(row);
  });
}

async function refreshAll() {
  await loadProducts();
  await loadFinance();
}

document.getElementById("product-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    name: document.getElementById("p-name").value,
    sale_price: parseFloat(document.getElementById("p-price").value),
    quantity: parseFloat(document.getElementById("p-qty").value || 0),
  };
  await fetch(`${API}/inventory/products`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  e.target.reset();
  await refreshAll();
});

document.getElementById("sale-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const productId = parseInt(document.getElementById("s-product").value);
  const quantity = parseFloat(document.getElementById("s-qty").value);
  const messageEl = document.getElementById("sale-message");

  const res = await fetch(`${API}/sales/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items: [{ product_id: productId, quantity }] }),
  });

  if (res.ok) {
    const sale = await res.json();
    messageEl.textContent = `✅ Chek yopildi: ${sale.total_amount} so'm`;
    messageEl.style.color = "green";
    e.target.reset();
  } else {
    const err = await res.json();
    messageEl.textContent = `❌ Xatolik: ${err.detail}`;
    messageEl.style.color = "#b3261e";
  }

  await refreshAll();
});

// Sahifa ochilganda va har 5 soniyada bir avtomatik yangilanadi
// (Telegram bot orqali sotilgan mahsulot ham shu yerda ko'rinishi uchun)
refreshAll();
setInterval(refreshAll, 5000);
