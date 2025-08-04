import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from flask import Flask
import threading
import os

# --- تنظیمات لاگ ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- توکن از محیط بگیر ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ متغیر محیطی BOT_TOKEN تنظیم نشده است!")

# --- جدول قیمت‌ها ---
PRICES = {
    'sensor_type': {
        'NTC10K': 350_000,
        'PT100': 450_000,
        'DS18B20': 400_000
    },
    'dimensions': {
        '6×50': 150_000,
        '4×25': 100_000,
        '8×75': 200_000
    },
    'wire_length_per_cm': 2000,
    'base_price': 50_000
}

def calculate_price(context):
    try:
        if not all(key in context.user_data for key in ['sensor_type', 'dimensions', 'wire_length', 'quantity']):
            return None
        total = PRICES['base_price']
        total += PRICES['sensor_type'].get(context.user_data['sensor_type'], 0)
        total += PRICES['dimensions'].get(context.user_data['dimensions'], 0)
        total += PRICES['wire_length_per_cm'] * int(context.user_data['wire_length'])
        total *= int(context.user_data['quantity'])
        return total
    except Exception as e:
        logging.error(f"❌ خطای محاسبه قیمت: {e}")
        return None

# --- منوها ---
main_menu = [
    [InlineKeyboardButton("📦 محصولات", callback_data='products')],
    [InlineKeyboardButton("📞 تماس با ما", callback_data='contact')]
]
product_menu = [
    [InlineKeyboardButton("🌡️ سنسور دمای NTC10K", callback_data='ntc10k')],
    [InlineKeyboardButton("🛍️ ثبت سفارش آنلاین", callback_data='order')],
    [InlineKeyboardButton("⬅️ بازگشت به منو اصلی", callback_data='back_main')]
]
ntc10k_menu = [
    [InlineKeyboardButton("🔧 مشخصات فنی", callback_data='specs')],
    [InlineKeyboardButton("📐 ابعاد و مشخصات فیزیکی", callback_data='dimensions')],
    [InlineKeyboardButton("🏭 کاربردها", callback_data='uses')],
    [InlineKeyboardButton("⚙️ شرایط کاری", callback_data='conditions')],
    [InlineKeyboardButton("📸 گالری تصاویر محصول", callback_data='images')],
    [InlineKeyboardButton("🔙 بازگشت به منوی محصولات", callback_data='back_products')]
]

# --- دستور /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    try:
        await update.message.delete()
    except:
        pass
    welcome_text = """
✨ به فروشگاه ولتا استور خوش آمدید! ✨
🔸 ارائه دهنده انواع سنسورهای صنعتی
🔸 کیفیت برتر، قیمت مناسب
🔸 ارسال به سراسر کشور
🔸 پشتیبانی ۲۴ ساعته
لطفاً یکی از گزینه‌های زیر را انتخاب کنید:
"""
    reply_markup = InlineKeyboardMarkup(main_menu)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# --- هندل کلیک روی دکمه ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data == 'products':
        reply_markup = InlineKeyboardMarkup(product_menu)
        await query.edit_message_text(text="📌 منوی محصولات:", reply_markup=reply_markup)
    elif data == 'ntc10k':
        reply_markup = InlineKeyboardMarkup(ntc10k_menu)
        await query.edit_message_text(
            text="🌡️ سنسور دمای NTC10K\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=reply_markup
        )
    # ... (باقی کد)

# --- وب سرور ساده برای نگه داشتن ربات زنده ---
app = Flask('')
@app.route('/')
def home():
    return "ربات ولتا استور در حال اجراست! 🚀"

def run():
    app.run(host='0.0.0.0', port=8080)

# --- اجرای ربات ---
if __name__ == '__main__':
    t = threading.Thread(target=run)
    t.start()

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    print("🚀 ربات در حال اجرا است...")
    application.run_polling()
