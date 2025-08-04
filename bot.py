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

# --- توکن از محیط بگیر (حتماً در Render تنظیم شود) ---
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

# --- نمایش خلاصه سفارش ---
async def show_order_summary(query, context):
    order_text = """📋 مشخصات سفارش شما:
🎯 نوع سنسور: {}
📐 ابعاد غلاف: {}
📏 طول سیم: {}
🔢 تعداد: {}""".format(
        f"✨ {context.user_data.get('sensor_type')}" if context.user_data.get('sensor_type') else "❌ انتخاب نشده",
        f"✨ {context.user_data.get('dimensions')}" if context.user_data.get('dimensions') else "❌ انتخاب نشده",
        f"✨ {context.user_data.get('wire_length')} سانتی‌متر" if context.user_data.get('wire_length') else "❌ انتخاب نشده",
        f"✨ {context.user_data.get('quantity')} عدد" if context.user_data.get('quantity') else "❌ انتخاب نشده"
    )
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 انتخاب نوع سنسور", callback_data='select_sensor_type')],
        [InlineKeyboardButton("📐 انتخاب ابعاد غلاف", callback_data='select_dimensions')],
        [InlineKeyboardButton("📍 طول سیم", callback_data='select_wire_length')],
        [InlineKeyboardButton("🔢 تعداد", callback_data='select_quantity')],
        [InlineKeyboardButton("✅ ثبت نهایی سفارش", callback_data='final_order')],
        [InlineKeyboardButton("🔙 بازگشت به منوی قبل", callback_data='back_products')]
    ])
    await query.edit_message_text(text=order_text, reply_markup=reply_markup)

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

    elif data == 'contact':
        contact_text = """✨ ارتباط با ولتا استور ✨
👤 مدیر فروش: محمد حسین داودی
📱 تلفن تماس: 09359636526
📍 آدرس: تهران، سه راه مرزداران، برج نگین رضا
⏰ ساعات پاسخگویی:
شنبه تا چهارشنبه: 9:00 - 18:00
پنجشنبه: 9:00 - 13:00"""
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت به منوی قبل", callback_data='back_main')]
        ])
        await query.edit_message_text(text=contact_text, reply_markup=reply_markup)

    # --- اطلاعات محصول ---
    product_info = {
        'specs': {
            'title': '📘 مشخصات فنی:',
            'content': """- نوع سنسور: 103AT-2-NTC
- محدوده دما: -50 تا +110°C
- دقت اندازه‌گیری: ±0.5°C
- نوع اتصال: 2 سیمه 
- جنس غلاف: استیل ضدزنگ"""
        },
        'dimensions': {
            'title': '📏 ویژگی‌های فیزیکی:',
            'content': """- طول غلاف: 50 میلی‌متر
- قطر غلاف: 6 میلی‌متر
- طول سیم: 2 متر
- وزن: 50 گرم
- نوع نصب: مجاورتی"""
        },
        'uses': {
            'title': '🏭 کاربردها:',
            'content': """- صنایع غذایی
- دیگ بخار
- تجهیزات آزمایشگاهی
- چیلر و تهویه مطبوع
- خطوط تولید صنعتی"""
        },
        'conditions': {
            'title': '🌡️ شرایط کاری:',
            'content': """- دمای کاری: -50 تا +110°C
- فشار قابل تحمل: تا 10 بار
- مقاومت در برابر رطوبت: دارد"""
        }
    }

    if data in product_info:
        info = product_info[data]
        text = f"{info['title']}\n{info['content']}"
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت به منوی قبل", callback_data='ntc10k')]
        ])
        await query.edit_message_text(text=text, reply_markup=reply_markup)

    elif data == 'images':
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🖼️ نمای نزدیک", callback_data='image_closeup')],
            [InlineKeyboardButton("🖼️ نصب شده روی دستگاه", callback_data='image_installed')],
            [InlineKeyboardButton("🔙 بازگشت به منوی قبل", callback_data='ntc10k')]
        ])
        await query.edit_message_text(text="📷 لطفاً یک تصویر را انتخاب کنید:", reply_markup=reply_markup)

    elif data in ['image_closeup', 'image_installed']:
        photo_url = "https://via.placeholder.com/300x200?text=Close+Up" if data == 'image_closeup' else "https://via.placeholder.com/300x200?text=Installed+View"
        await query.message.reply_photo(photo=photo_url)
        await query.answer()

    elif data == 'order':
        await show_order_summary(query, context)

    # --- انتخاب نوع سنسور ---
    elif data == 'select_sensor_type':
        keyboard = [
            [InlineKeyboardButton("🌡️ NTC10K", callback_data='sensor_ntc10k')],
            [InlineKeyboardButton("🌡️ PT100", callback_data='sensor_pt100')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='order')]
        ]
        await query.edit_message_text(
            text="🎯 لطفاً نوع سنسور را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # --- پردازش انتخاب نوع سنسور ---
    elif data.startswith('sensor_'):
        sensor_type = 'NTC10K' if data == 'sensor_ntc10k' else 'PT100'
        context.user_data['sensor_type'] = sensor_type
        await query.answer(f"نوع سنسور {sensor_type} انتخاب شد")
        await show_order_summary(query, context)  # بازگشت اتوماتیک به منوی سفارش

    # --- انتخاب ابعاد غلاف ---
    elif data == 'select_dimensions':
        keyboard = [
            [InlineKeyboardButton("📏 6×50", callback_data='dim_6x50')],
            [InlineKeyboardButton("📏 4×25", callback_data='dim_4x25')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='order')]
        ]
        await query.edit_message_text(
            text="📐 لطفاً ابعاد غلاف را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # --- پردازش انتخاب ابعاد ---
    elif data.startswith('dim_'):
        dimensions = '6×50' if data == 'dim_6x50' else '4×25'
        context.user_data['dimensions'] = dimensions
        await query.answer(f"ابعاد {dimensions} انتخاب شد")
        await show_order_summary(query, context)  # بازگشت اتوماتیک به منوی سفارش

    # --- انتخاب طول سیم ---
    elif data == 'select_wire_length':
        context.user_data['awaiting_wire_length'] = True
        await query.edit_message_text(
            text="📏 لطفاً طول سیم را به سانتی‌متر وارد کنید (40 تا 500):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='order')]])
        )

    # --- انتخاب تعداد ---
    elif data == 'select_quantity':
        context.user_data['awaiting_quantity'] = True
        await query.edit_message_text(
            text="🔢 لطفاً تعداد مورد نیاز را وارد کنید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='order')]])
        )

    # --- ثبت نهایی سفارش ---
    elif data == 'final_order':
        if not all(key in context.user_data for key in ['sensor_type', 'dimensions', 'wire_length', 'quantity']):
            await query.answer("❌ لطفاً تمام موارد سفارش را تکمیل کنید.", show_alert=True)
        else:
            final_price = calculate_price(context)
            if final_price is None:
                await query.answer("⚠️ خطایی در محاسبه قیمت رخ داد.")
                return
            order_details = f"""✅ سفارش جدید با مشخصات زیر ثبت شد:
- نوع سنسور: {context.user_data.get('sensor_type')}
- ابعاد غلاف: {context.user_data.get('dimensions')}
- طول سیم: {context.user_data.get('wire_length')} سانتی‌متر
- تعداد: {context.user_data.get('quantity')} عدد
💰 قیمت کل: {final_price:,} تومان
📱 برای نهایی کردن سفارش با @admin در تماس باشید.
🆔 شناسه کاربر: {query.from_user.id}"""

            try:
                payment_keyboard = [[InlineKeyboardButton("💳 نهایی‌سازی سفارش و پرداخت", callback_data='payment_info')]]
                await query.edit_message_text(
                    text=f"{order_details}\n✨ یک نسخه از سفارش به چت خصوصی شما ارسال شد.",
                    reply_markup=InlineKeyboardMarkup(payment_keyboard)
                )
                await context.bot.send_message(chat_id=query.from_user.id, text=order_details, reply_markup=InlineKeyboardMarkup(payment_keyboard))
                await context.bot.send_message(chat_id=-1002591533364, text=order_details)
            except Exception as e:
                logging.error(f"❌ خطای ارسال: {e}")
                await query.answer("⚠️ امکان ارسال پیام خصوصی وجود ندارد.", show_alert=True)

    elif data == 'back_main':
        await query.edit_message_text(text="🛒 به فروشگاه ولتا استور خوش آمدید!", reply_markup=InlineKeyboardMarkup(main_menu))

    elif data == 'back_products':
        await query.edit_message_text(text="📌 منوی محصولات:", reply_markup=InlineKeyboardMarkup(product_menu))

    elif data == 'payment_info':
        payment_text = "💳 لطفاً از یکی از روش‌های زیر برای پرداخت استفاده کنید:"
        payment_menu = [
            [InlineKeyboardButton("💳 شماره کارت", callback_data='card_number')],
            [InlineKeyboardButton("📱 شماره شبا", callback_data='sheba_number')],
            [InlineKeyboardButton("🏦 شماره حساب", callback_data='account_number')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='back_products')]
        ]
        await query.edit_message_text(text=payment_text, reply_markup=InlineKeyboardMarkup(payment_menu))

    elif data in ['card_number', 'sheba_number', 'account_number']:
        payment_info = {
            'card_number': "💳 شماره کارت:\n6037-9975-9975-9975\nبه نام: محمد حسین داودی\nبانک: ملی",
            'sheba_number': "📱 شماره شبا:\nIR06-0170-0000-0012-3456-7890-01\nبه نام: محمد حسین داودی\nبانک: ملی",
            'account_number': "🏦 شماره حساب:\n0012345678901\nبه نام: محمد حسین داودی\nبانک: ملی"
        }
        send_receipt_button = [
            [InlineKeyboardButton("📸 ارسال رسید پرداخت", callback_data='send_receipt')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='payment_info')]
        ]
        await query.edit_message_text(
            text=f"{payment_info[data]}\n✨ پس از پرداخت، لطفاً رسید را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup(send_receipt_button)
        )

    elif data == 'send_receipt':
        context.user_data['awaiting_receipt'] = True
        await query.edit_message_text(
            text="📸 لطفاً تصویر رسید پرداخت را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='payment_info')]])
        )

# --- هندلر پیام‌های متنی ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'awaiting_wire_length' in context.user_data and context.user_data['awaiting_wire_length']:
        try:
            length = int(update.message.text.strip())
            if 40 <= length <= 500:
                context.user_data['wire_length'] = length
                context.user_data['awaiting_wire_length'] = False
                # ⬅️ ارسال دوباره منوی سفارش با خلاصه به‌روز
                order_text = """📋 مشخصات سفارش شما:
🎯 نوع سنسور: {}
📐 ابعاد غلاف: {}
📏 طول سیم: {}
🔢 تعداد: {}""".format(
                    f"✨ {context.user_data.get('sensor_type')}" if context.user_data.get('sensor_type') else "❌ انتخاب نشده",
                    f"✨ {context.user_data.get('dimensions')}" if context.user_data.get('dimensions') else "❌ انتخاب نشده",
                    f"✨ {length} سانتی‌متر",
                    f"✨ {context.user_data.get('quantity')} عدد" if context.user_data.get('quantity') else "❌ انتخاب نشده"
                )
                reply_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎯 انتخاب نوع سنسور", callback_data='select_sensor_type')],
                    [InlineKeyboardButton("📐 انتخاب ابعاد غلاف", callback_data='select_dimensions')],
                    [InlineKeyboardButton("📍 طول سیم", callback_data='select_wire_length')],
                    [InlineKeyboardButton("🔢 تعداد", callback_data='select_quantity')],
                    [InlineKeyboardButton("✅ ثبت نهایی سفارش", callback_data='final_order')],
                    [InlineKeyboardButton("🔙 بازگشت به منوی قبل", callback_data='back_products')]
                ])
                await update.message.reply_text(text=order_text, reply_markup=reply_markup)
            else:
                await update.message.reply_text("❌ لطفاً عددی بین 40 تا 500 وارد کنید.")
        except ValueError:
            await update.message.reply_text("❌ فقط عدد معتبر وارد کنید.")

    elif 'awaiting_quantity' in context.user_data and context.user_data['awaiting_quantity']:
        try:
            quantity = int(update.message.text.strip())
            if quantity > 0:
                context.user_data['quantity'] = quantity
                context.user_data['awaiting_quantity'] = False
                # ⬅️ ارسال دوباره منوی سفارش با خلاصه به‌روز
                order_text = """📋 مشخصات سفارش شما:
🎯 نوع سنسور: {}
📐 ابعاد غلاف: {}
📏 طول سیم: {}
🔢 تعداد: {}""".format(
                    f"✨ {context.user_data.get('sensor_type')}" if context.user_data.get('sensor_type') else "❌ انتخاب نشده",
                    f"✨ {context.user_data.get('dimensions')}" if context.user_data.get('dimensions') else "❌ انتخاب نشده",
                    f"✨ {context.user_data.get('wire_length')} سانتی‌متر" if context.user_data.get('wire_length') else "❌ انتخاب نشده",
                    f"✨ {quantity} عدد"
                )
                reply_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎯 انتخاب نوع سنسور", callback_data='select_sensor_type')],
                    [InlineKeyboardButton("📐 انتخاب ابعاد غلاف", callback_data='select_dimensions')],
                    [InlineKeyboardButton("📍 طول سیم", callback_data='select_wire_length')],
                    [InlineKeyboardButton("🔢 تعداد", callback_data='select_quantity')],
                    [InlineKeyboardButton("✅ ثبت نهایی سفارش", callback_data='final_order')],
                    [InlineKeyboardButton("🔙 بازگشت به منوی قبل", callback_data='back_products')]
                ])
                await update.message.reply_text(text=order_text, reply_markup=reply_markup)
            else:
                await update.message.reply_text("❌ لطفاً یک عدد مثبت وارد کنید.")
        except ValueError:
            await update.message.reply_text("❌ فقط عدد وارد کنید.")

# --- هندلر عکس ---
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'awaiting_receipt' in context.user_data and context.user_data['awaiting_receipt']:
        photo = update.message.photo[-1]
        receipt_text = f"""📸 رسید پرداخت جدید
🆔 شناسه کاربر: {update.effective_user.id}
👤 نام کاربر: {update.effective_user.first_name}"""
        try:
            await context.bot.send_photo(
                chat_id=-1002591533364,
                photo=photo.file_id,
                caption=receipt_text
            )
            await update.message.reply_text(
                "✅ رسید پرداخت شما با موفقیت ثبت شد.\nکارشناسان ما به زودی آن را بررسی خواهند کرد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data='back_main')]])
            )
            context.user_data['awaiting_receipt'] = False
        except Exception as e:
            logging.error(f"❌ خطای ارسال رسید: {e}")
            await update.message.reply_text("❌ متأسفانه در ثبت رسید خطایی رخ داد. لطفاً دوباره تلاش کنید.")

# --- وب سرور ساده برای نگه داشتن ربات زنده ---
flask_app = Flask('')

@flask_app.route('/')
def home():
    return "ربات ولتا استور در حال اجراست! 🚀"

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)

# --- اجرای ربات ---
if __name__ == '__main__':
    # راه‌اندازی وب سرور در پس‌زمینه
    t = threading.Thread(target=run_flask)
    t.start()

    # ساخت و اجرای ربات
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    print("🚀 ربات در حال اجرا است...")
    application.run_polling()
