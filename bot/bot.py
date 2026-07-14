"""
telegram_bot.py
----------------
MUHIM: bu bot hech qanday biznes-mantiqni o'zida saqlamaydi.
U faqat foydalanuvchi xabarini oladi va bitta joyga - bizning FastAPI
backendimizga (odatda http://127.0.0.1:8000) so'rov yuboradi.

Natijada: Web dashboard'da qilingan savdo - Telegram botda ham,
Telegram botda qilingan savdo - Web dashboard'da ham darhol ko'rinadi.
Bitta baza, ikkita "eshik" (client) - bu "single source of truth" tamoyili.

ISHGA TUSHIRISH:
1) Avval backendni ishga tushiring (alohida terminalda):
       uvicorn main:app --reload
2) Keyin shu faylni ishga tushiring (yana bir terminalda):
       export TELEGRAM_BOT_TOKEN="sizning_tokeningiz"     (Windows: set TELEGRAM_BOT_TOKEN=...)
       python telegram_bot.py

Bot tokenini @BotFather orqali Telegram'da bepul olasiz.
"""

import os
from pathlib import Path
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# .env faylni terminal QAYERDA ochilganidan qat'iy nazar, aynan shu skript
# joylashgan papkadan qidiradi va o'qiydi (bu eng ko'p uchraydigan xatoni oldini oladi).
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Backend qayerda ishlab turganini shu yerdan sozlaysiz.
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Hozircha auth yo'q bo'lgani uchun COMPANY_ID .env orqali beriladi.
# Bosqich 1 (login) qo'shilgach, bot foydalanuvchini /start bosqichida
# aniqlab, uning company_id'sini shu yerda emas, sessiyada saqlaydi.
COMPANY_ID = os.getenv("COMPANY_ID", "1")


def api_headers():
    """Har bir backend so'roviga qo'shiladigan tenant header'i — bitta joyda."""
    return {"X-Company-Id": COMPANY_ID}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Salom! Men MikroERP botiman.\n\n"
        "Buyruqlar:\n"
        "/mahsulotlar — ombordagi barcha mahsulotlar va qoldiqlar\n"
        "/hisobot — moliyaviy xulosa (kirim/chiqim/foyda)\n"
        "/sotish <mahsulot_id> <miqdor> — tezkor sotish\n\n"
        "Masalan: /sotish 1 3"
    )
    await update.message.reply_text(text)


async def mahsulotlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(f"{API_URL}/inventory/products", headers=api_headers(), timeout=5)
        response.raise_for_status()
        products = response.json()
    except requests.RequestException:
        await update.message.reply_text("⚠️ Backendga ulanib bo'lmadi. Server ishlab turganiga ishonch hosil qiling.")
        return

    if not products:
        await update.message.reply_text("Hozircha mahsulotlar yo'q. Web dashboarddan qo'shing.")
        return

    lines = ["📦 *Ombordagi mahsulotlar:*\n"]
    for p in products:
        lines.append(f"#{p['id']} — {p['name']}: {p['quantity']} {p['unit']} (narxi: {p['sale_price']})")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def hisobot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(f"{API_URL}/finance/summary", headers=api_headers(), timeout=5)
        response.raise_for_status()
        summary = response.json()
    except requests.RequestException:
        await update.message.reply_text("⚠️ Backendga ulanib bo'lmadi.")
        return

    text = (
        "💰 *Moliyaviy xulosa*\n\n"
        f"Umumiy tushum: {summary['total_income']}\n"
        f"Umumiy chiqim: {summary['total_expense']}\n"
        f"Sof foyda: {summary['net_profit']}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def sotish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Foydalanish: /sotish <mahsulot_id> <miqdor>\nMasalan: /sotish 1 3")
        return

    try:
        product_id = int(context.args[0])
        quantity = float(context.args[1])
    except ValueError:
        await update.message.reply_text("mahsulot_id butun son, miqdor esa son bo'lishi kerak.")
        return

    payload = {"items": [{"product_id": product_id, "quantity": quantity}]}
    try:
        response = requests.post(f"{API_URL}/sales/", json=payload, headers=api_headers(), timeout=5)
    except requests.RequestException:
        await update.message.reply_text("⚠️ Backendga ulanib bo'lmadi.")
        return

    if response.status_code == 200:
        sale = response.json()
        await update.message.reply_text(f"✅ Sotildi! Chek summasi: {sale['total_amount']} so'm")
    else:
        detail = response.json().get("detail", "Noma'lum xatolik")
        await update.message.reply_text(f"❌ Xatolik: {detail}")


def main():
    if not BOT_TOKEN:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN topilmadi.\n"
            f"Men .env faylni shu joydan qidirdim: {ENV_PATH}\n"
            f".env fayl mavjudmi: {ENV_PATH.exists()}\n\n"
            "Tekshiring:\n"
            "1) Aynan shu yo'lda '.env' fayl bormi (nomi '.env.txt' bo'lib qolmaganmi)?\n"
            "2) Fayl ichida 'TELEGRAM_BOT_TOKEN=...' qatori to'g'ri yozilganmi (bo'sh joy, tirnoqsiz)?\n"
            "3) pip install -r requirements.txt qayta ishga tushirilganmi (python-dotenv o'rnatilishi kerak)?"
        )

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mahsulotlar", mahsulotlar))
    app.add_handler(CommandHandler("hisobot", hisobot))
    app.add_handler(CommandHandler("sotish", sotish))

    print("Bot ishga tushdi. To'xtatish uchun Ctrl+C bosing.")
    app.run_polling()


if __name__ == "__main__":
    main()
