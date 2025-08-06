import logging
import os
from datetime import datetime
import pytz
from jdatetime import datetime as jdatetime
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
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageEnhance
import threading

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

# --- تابع کمکی: دریافت زمان به وقت تهران و شمسی ---
def get_tehran_time():
    tehran_tz = pytz.timezone('Asia/Tehran')
    now = datetime.now(tehran_tz)
    j_now = jdatetime.fromgregorian(datetime=now)
    return f"{j_now.strftime('%Y/%m/%d')} - {now.strftime('%H:%M')}"

# --- مسیر فونت و لوگو ---
FONT_PATH = 'Vazirmatn-Regular.ttf'
LOGO_PATH = 'volta_store_logo.png'

# --- منوها ---
main_menu = [
    [InlineKeyboardButton("📦 محصولات", callback_data='products')],
    [InlineKeyboardButton("📞 تماس با ما", callback_data='contact')]
]
product_menu = [
    [InlineKeyboardButton("🌡️ سنسور دمای NTC10K", callback_data='ntc10k')],
    [InlineKeyboardButton("🛍️ ثبت سفارش آنلاین", callback_data='order')],
    [InlineKeyboardButton("🧮 ماشین حساب تخمین قیمت", callback_data='calculator')],
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
        [InlineKeyboardButton("📞 اطلاعات تماس", callback_data='enter_contact_info')],
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
        await show_order_summary(query, context)

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
        await show_order_summary(query, context)

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

    # --- درخواست اطلاعات تماس ---
    elif data == 'enter_contact_info':
        context.user_data['awaiting_customer_name'] = True
        await query.edit_message_text(
            text="📝 لطفاً نام و نام خانوادگی خود را وارد کنید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='order')]])
        )

    # --- ثبت نهایی سفارش ---
    elif data == 'final_order':
        required_keys = ['sensor_type', 'dimensions', 'wire_length', 'quantity', 'customer_first_name', 'customer_phone']
        if not all(key in context.user_data for key in required_keys):
            await query.answer("❌ لطفاً اطلاعات تماس را کامل کنید.", show_alert=True)
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
📱 برای نهایی کردن سفارش با @admin در تماس باشید."""

            try:
                # ارسال به کاربر
                payment_keyboard = [[InlineKeyboardButton("💳 نهایی‌سازی سفارش و پرداخت", callback_data='payment_info')]]
                await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text=order_details,
                    reply_markup=InlineKeyboardMarkup(payment_keyboard)
                )

                # --- ساخت و ارسال PDF ---
                user_name = query.from_user.full_name
                user_id = query.from_user.id
                try:
                    pdf_path = create_invoice_pdf(context, user_name, user_id)
                    await context.bot.send_document(
                        chat_id=query.from_user.id,
                        document=open(pdf_path, 'rb'),
                        caption="📄 پیش‌فاکتور سفارش شما"
                    )
                    os.remove(pdf_path)
                except Exception as pdf_error:
                    logging.error(f"❌ خطای ساخت PDF: {pdf_error}")
                    await context.bot.send_message(
                        chat_id=query.from_user.id,
                        text="⚠️ در ایجاد پیش‌فاکتور مشکلی پیش آمد، اما سفارش شما ثبت شد."
                    )

                # ارسال به کانال (فقط یک بار)
                if not context.user_data.get('order_sent_to_channel', False):
                    await context.bot.send_message(chat_id=-1002591533364, text=order_details)
                    context.user_data['order_sent_to_channel'] = True

                # ویرایش پیام فعلی
                await query.edit_message_text(
                    text=f"{order_details}\n✨ سفارش و پیش‌فاکتور برای شما ارسال شد.",
                    reply_markup=InlineKeyboardMarkup(payment_keyboard)
                )
                await query.answer("✅ سفارش و پیش‌فاکتور با موفقیت ارسال شد.")

            except Exception as e:
                logging.error(f"❌ خطای ارسال: {e}")
                await query.answer("⚠️ خطایی در ارسال سفارش رخ داد.")

    # --- ماشین حساب تخمین قیمت ---
    elif data == 'calculator':
        keyboard = [
            [InlineKeyboardButton("NTC 5K", callback_data='calc_sensor_12000')],
            [InlineKeyboardButton("NTC 10K", callback_data='calc_sensor_15000')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='products')]
        ]
        await query.edit_message_text(
            text="🔧 لطفاً نوع سنسور را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith('calc_sensor_'):
        price = int(data.split('_')[2])
        context.user_data['calc_sensor_price'] = price
        await query.answer("نوع سنسور انتخاب شد")
        keyboard = [
            [InlineKeyboardButton("25×4", callback_data='calc_sheath_10000')],
            [InlineKeyboardButton("50×4", callback_data='calc_sheath_10500')],
            [InlineKeyboardButton("100×4", callback_data='calc_sheath_11000')],
            [InlineKeyboardButton("25×5", callback_data='calc_sheath_11500')],
            [InlineKeyboardButton("50×50", callback_data='calc_sheath_12000')],
            [InlineKeyboardButton("30×5", callback_data='calc_sheath_12500')],
            [InlineKeyboardButton("30×6", callback_data='calc_sheath_13000')],
            [InlineKeyboardButton("40×6", callback_data='calc_sheath_13500')],
            [InlineKeyboardButton("50×6 سرتخت", callback_data='calc_sheath_14000')],
            [InlineKeyboardButton("50×6 سرگرد", callback_data='calc_sheath_14500')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='calculator')]
        ]
        await query.edit_message_text(
            text="🔧 لطفاً نوع غلاف را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith('calc_sheath_'):
        price = int(data.split('_')[2])
        context.user_data['calc_sheath_price'] = price
        await query.answer("نوع غلاف انتخاب شد")
        context.user_data['awaiting_calc_length'] = True
        await query.edit_message_text(
            text="📏 لطفاً طول کابل را به متر وارد کنید (مثلاً 2.5):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='calculator')]])
        )

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
    # --- ورود طول سیم ---
    if 'awaiting_wire_length' in context.user_data and context.user_data['awaiting_wire_length']:
        try:
            length = int(update.message.text.strip())
            if 40 <= length <= 500:
                context.user_data['wire_length'] = length
                context.user_data['awaiting_wire_length'] = False

                # ارسال دوباره منوی سفارش
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
                    [InlineKeyboardButton("📞 اطلاعات تماس", callback_data='enter_contact_info')],
                    [InlineKeyboardButton("✅ ثبت نهایی سفارش", callback_data='final_order')],
                    [InlineKeyboardButton("🔙 بازگشت به منوی قبل", callback_data='back_products')]
                ])
                await update.message.reply_text(text=order_text, reply_markup=reply_markup)
            else:
                await update.message.reply_text("❌ لطفاً عددی بین 40 تا 500 وارد کنید.")
        except ValueError:
            await update.message.reply_text("❌ فقط عدد معتبر وارد کنید.")

    # --- ورود تعداد ---
    elif 'awaiting_quantity' in context.user_data and context.user_data['awaiting_quantity']:
        try:
            quantity = int(update.message.text.strip())
            if quantity > 0:
                context.user_data['quantity'] = quantity
                context.user_data['awaiting_quantity'] = False

                # ارسال دوباره منوی سفارش
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
                    [InlineKeyboardButton("📞 اطلاعات تماس", callback_data='enter_contact_info')],
                    [InlineKeyboardButton("✅ ثبت نهایی سفارش", callback_data='final_order')],
                    [InlineKeyboardButton("🔙 بازگشت به منوی قبل", callback_data='back_products')]
                ])
                await update.message.reply_text(text=order_text, reply_markup=reply_markup)
            else:
                await update.message.reply_text("❌ لطفاً یک عدد مثبت وارد کنید.")
        except ValueError:
            await update.message.reply_text("❌ فقط عدد وارد کنید.")

    # --- ورود نام مشتری ---
    elif 'awaiting_customer_name' in context.user_data and context.user_data['awaiting_customer_name']:
        name = update.message.text.strip()
        if len(name) < 2:
            await update.message.reply_text("❌ لطفاً یک نام معتبر وارد کنید.")
        else:
            parts = name.split()
            first_name = parts[0]
            last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
            context.user_data['customer_first_name'] = first_name
            context.user_data['customer_last_name'] = last_name
            context.user_data['awaiting_customer_name'] = False
            context.user_data['awaiting_customer_phone'] = True
            await update.message.reply_text(
                "📞 لطفاً شماره تماس خود را (با 0) وارد کنید:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='order')]])
            )

    # --- ورود شماره تماس ---
    elif 'awaiting_customer_phone' in context.user_data and context.user_data['awaiting_customer_phone']:
        phone = update.message.text.strip()
        if not phone.startswith("0") or not phone.isdigit() or not (10 <= len(phone) <= 11):
            await update.message.reply_text("❌ لطفاً یک شماره معتبر (مثلاً 09123456789) وارد کنید.")
        else:
            context.user_data['customer_phone'] = phone
            context.user_data['awaiting_customer_phone'] = False

            # ارسال دوباره منوی سفارش
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
                [InlineKeyboardButton("📞 اطلاعات تماس", callback_data='enter_contact_info')],
                [InlineKeyboardButton("✅ ثبت نهایی سفارش", callback_data='final_order')],
                [InlineKeyboardButton("🔙 بازگشت به منوی قبل", callback_data='back_products')]
            ])
            await update.message.reply_text(text=order_text, reply_markup=reply_markup)

    # --- ورود طول کابل برای ماشین حساب ---
    elif 'awaiting_calc_length' in context.user_data and context.user_data['awaiting_calc_length']:
        try:
            length = float(update.message.text.strip())
            if length < 0:
                await update.message.reply_text("❌ طول کابل نمی‌تواند منفی باشد.")
                return

            sensor_price = context.user_data.get('calc_sensor_price', 0)
            sheath_price = context.user_data.get('calc_sheath_price', 0)
            cable_price_per_meter = 12000
            cable_total = length * cable_price_per_meter
            assembly = 25000
            extra = 7000
            profit = 15000

            base_price = sensor_price + sheath_price + cable_total + assembly + extra + profit

            # فاکتور سختی کار
            if length <= 2:
                factor = 1.00
            elif length <= 5:
                factor = 1.05
            elif length <= 10:
                factor = 1.10
            elif length <= 15:
                factor = 1.15
            else:
                factor = 1.20

            final_price = int(base_price * factor)

            # ✅ فقط قیمت نهایی نمایش داده میشه
            result_text = f"""✅ قیمت تخمینی سنسور دما:
💰 قیمت نهایی: {final_price:,.0f} تومان"""

            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 محاسبه مجدد", callback_data='calculator')],
                [InlineKeyboardButton("🛍️ ثبت سفارش آنلاین", callback_data='order')],
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data='back_main')]
            ])

            await update.message.reply_text(result_text, reply_markup=reply_markup)
            context.user_data.pop('awaiting_calc_length', None)
            context.user_data.pop('calc_sensor_price', None)
            context.user_data.pop('calc_sheath_price', None)

        except ValueError:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید (مثلاً 2.5).")

# --- هندلر عکس ---
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'awaiting_receipt' in context.user_data and context.user_data['awaiting_receipt']:
        photo = update.message.photo[-1]
        receipt_text = f"""📸 رسید پرداخت جدید
🆔 شناسه کاربر: {update.effective_user.id}
👤 نام کاربر: {update.effective_user.first_name}"""
        try:
            # جلوگیری از ارسال دوباره
            if not context.user_data.get('receipt_sent', False):
                await context.bot.send_photo(
                    chat_id=-1002591533364,
                    photo=photo.file_id,
                    caption=receipt_text
                )
                context.user_data['receipt_sent'] = True

            await update.message.reply_text(
                "✅ رسید پرداخت شما با موفقیت ثبت شد.\nکارشناسان ما به زودی آن را بررسی خواهند کرد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data='back_main')]])
            )
            context.user_data['awaiting_receipt'] = False
        except Exception as e:
            logging.error(f"❌ خطای ارسال رسید: {e}")
            await update.message.reply_text("❌ متأسفانه در ثبت رسید خطایی رخ داد. لطفاً دوباره تلاش کنید.")

# --- ساخت PDF پیش‌فاکتور ---
def create_invoice_pdf(context, user_name, user_id):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # --- بررسی وجود فونت ---
    if not os.path.exists(FONT_PATH):
        raise FileNotFoundError("فایل فونت Vazirmatn-Regular.ttf یافت نشد. لطفاً فونت رو در پوشه اصلی قرار بدید.")

    # --- افزودن فونت فارسی ---
    pdf.add_font('Vazir', '', FONT_PATH)
    pdf.set_font('Vazir', size=16)

    # --- اضافه کردن لوگو به عنوان watermark در پس‌زمینه (فقط بزرگ‌تر) ---
    WATERMARK_PATH = 'volta_store_logo_watermark.png'

    if os.path.exists(WATERMARK_PATH):
        try:
            # اندازه لوگو رو بزرگ‌تر کن (مثلاً 150x150)
            pdf.image(WATERMARK_PATH, x=30, y=60, w=150, h=150)  # بزرگ‌تر و مرکز صفحه
        except Exception as e:
            print(f"⚠️ مشکل در افزودن watermark: {e}")
    else:
        print("❌ فایل لوگوی watermark پیدا نشد: 'volta_store_logo_watermark.png'")

    # --- سربرگ (هدر) ---
    pdf.set_fill_color(0, 120, 215)  # آبی کاربنی
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Vazir', '', 20)
    pdf.cell(0, 20, txt=get_display(arabic_reshaper.reshape("پیش‌فاکتور سفارش")), ln=True, align='C', fill=True)
    pdf.ln(5)

    # --- اطلاعات فروشگاه ---
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Vazir', size=14)
    shop_info = "ولتا استور | فروشگاه تخصصی سنسورهای صنعتی"
    reshaped_shop = get_display(arabic_reshaper.reshape(shop_info))
    pdf.cell(0, 8, txt=reshaped_shop, ln=True, align='C')

    contact_info = "تلفن: 09359636526 | تهران، سه راه مرزداران"
    reshaped_contact = get_display(arabic_reshaper.reshape(contact_info))
    pdf.cell(0, 8, txt=reshaped_contact, ln=True, align='C')
    pdf.ln(10)

    # --- خط جداکننده ---
    pdf.set_draw_color(0, 120, 215)
    pdf.line(10, 45, 200, 45)
    pdf.ln(5)

    # --- اطلاعات فاکتور ---
    pdf.set_font('Vazir', size=16)
    now = get_tehran_time()
    factor_number = f"شماره فاکتور: {user_id}-{now.split('-')[0].replace('/', '')}"
    reshaped_factor = get_display(arabic_reshaper.reshape(factor_number))
    pdf.cell(0, 8, txt=reshaped_factor, ln=True, align='R')

    date_text = f"تاریخ: {now}"
    reshaped_date = get_display(arabic_reshaper.reshape(date_text))
    pdf.cell(0, 8, txt=reshaped_date, ln=True, align='R')
    pdf.ln(5)

    # --- اطلاعات مشتری ---
    customer_first_name = context.user_data.get('customer_first_name', 'نامشخص')
    customer_last_name = context.user_data.get('customer_last_name', '')
    customer_phone = context.user_data.get('customer_phone', 'نامشخص')

    customer_info = f"نام: {customer_first_name} {customer_last_name}\nشماره تماس: {customer_phone}"
    reshaped_customer = get_display(arabic_reshaper.reshape(customer_info))
    pdf.multi_cell(0, 8, txt=reshaped_customer, align='R')
    pdf.ln(5)

    # --- جدول سفارش (کامل عرض، از لبه راست شروع میشه) ---
    col1_width = 100  # مقدار
    col2_width = 60   # مشخصه
    # مجموعاً 160mm (از x=10 تا x=170)

    # داده‌ها
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Vazir', size=16)

    items = [
        ("نوع سنسور", context.user_data.get('sensor_type', 'نامشخص')),
        ("ابعاد غلاف", context.user_data.get('dimensions', 'نامشخص')),
        ("طول سیم", f"{context.user_data.get('wire_length', 'نامشخص')} سانتی‌متر"),
        ("تعداد", context.user_data.get('quantity', 'نامشخص')),
        ("قیمت کل", f"{calculate_price(context):,} تومان" if calculate_price(context) else "نامشخص")
    ]

    for label, value in items:
        reshaped_label = get_display(arabic_reshaper.reshape(label))
        reshaped_value = get_display(arabic_reshaper.reshape(str(value)))
        # اول "مقدار" (سمت چپ)، بعد "مشخصه" (سمت راست)
        pdf.cell(col1_width, 12, reshaped_value, border=1, align="R")
        pdf.cell(col2_width, 12, reshaped_label, border=1, align="R", ln=True)

    # --- فوتر ---
    pdf.ln(10)
    footer1 = "با تشکر از اعتماد شما به ولتا استور"
    footer2 = "سفارش شما در دسترسی است و به زودی پیگیری می‌شود."

    pdf.set_font('Vazir', '', 16)
    pdf.set_text_color(0, 120, 215)
    pdf.cell(0, 10, txt=get_display(arabic_reshaper.reshape(footer1)), ln=True, align='C')

    pdf.set_text_color(100, 100, 100)
    pdf.set_font('Vazir', size=14)
    pdf.cell(0, 8, txt=get_display(arabic_reshaper.reshape(footer2)), ln=True, align='C')

    # --- ذخیره فایل ---
    filename = f"پیش_فاکتور_{user_id}.pdf"
    pdf.output(filename)
    return filename
    
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







