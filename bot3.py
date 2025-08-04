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

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# توکن رباتتون رو اینجا بنویسید
BOT_TOKEN = "توکن_ربات_خود_را_اینجا_قرار_دهید"  # توکن دریافتی از @BotFather

# جدول قیمت‌ها
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
    'wire_length_per_cm': 2000,  # قیمت هر سانتی‌متر سیم
    'base_price': 50_000  # قیمت پایه
}

def calculate_price(context):
    """
    محاسبه قیمت نهایی سفارش:
    ((نوع سنسور × کارمزد نوع سنسور) +
     (ابعاد غلاف × کارمزد ابعاد) +
     (طول سیم × دستمزد)) × تعداد = قیمت نهایی
    """
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

# منوهای اصلی
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

# دستور /start
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

# هندل کلیک روی دکمه
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
        photo_url = "https://via.placeholder.com/300x200?text=Close+Up " if data == 'image_closeup' else "https://via.placeholder.com/300x200?text=Installed+View "
        await query.message.reply_photo(photo=photo_url)
        await query.answer()

    elif data == 'order':
        order_text = "📝 لطفاً مشخصات سفارش خود را انتخاب کنید:"
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌡️ نوع سنسور", callback_data='select_sensor_type')],
            [InlineKeyboardButton("📏 ابعاد غلاف", callback_data='select_dimensions')],
            [InlineKeyboardButton("📍 طول سیم", callback_data='select_wire_length')],
            [InlineKeyboardButton("🔢 تعداد", callback_data='select_quantity')],
            [InlineKeyboardButton("✅ ثبت نهایی سفارش", callback_data='final_order')],
            [InlineKeyboardButton("🔙 بازگشت به منوی قبل", callback_data='back_products')]
        ])
        await query.edit_message_text(text=order_text, reply_markup=reply_markup)

    # --- انتخاب نوع سنسور ---
    elif data == 'select_sensor_type':
        context.user_data['sensor_type'] = context.user_data.get('sensor_type', '')
        text = "🌡️ لطفاً نوع سنسور را انتخاب کنید:"
        buttons = [
            [InlineKeyboardButton(f"✓ NTC10K" if context.user_data['sensor_type'] == 'NTC10K' else "NTC10K",
                                 callback_data='sensor_ntc10k')],
            [InlineKeyboardButton(f"✓ PT100" if context.user_data['sensor_type'] == 'PT100' else "PT100",
                                 callback_data='sensor_pt100')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='order')]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(text=text, reply_markup=reply_markup)

    # --- انتخاب ابعاد غلاف ---
    elif data == 'select_dimensions':
        context.user_data['dimensions'] = context.user_data.get('dimensions', '')
        text = "📏 لطفاً ابعاد غلاف را انتخاب کنید:"
        buttons = [
            [InlineKeyboardButton(f"✓ 6×50" if context.user_data['dimensions'] == '6×50' else "6×50",
                                 callback_data='dim_6x50')],
            [InlineKeyboardButton(f"✓ 4×25" if context.user_data['dimensions'] == '4×25' else "4×25",
                                 callback_data='dim_4x25')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='order')]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(text=text, reply_markup=reply_markup)

    # --- پردازش نوع سنسور ---
    elif data.startswith('sensor_'):
        sensor_type = 'NTC10K' if data == 'sensor_ntc10k' else 'PT100'
        context.user_data['sensor_type'] = sensor_type
        await query.answer(f"نوع سنسور {sensor_type} انتخاب شد")
        order_text = """📋 مشخصات سفارش شما:
🎯 نوع سنسور: {}
📐 ابعاد غلاف: {}
📏 طول سیم: {}
🔢 تعداد: {}""".format(
            "❌ انتخاب نشده" if not context.user_data.get('sensor_type') else f"✨ {context.user_data.get('sensor_type')}",
            "❌ انتخاب نشده" if not context.user_data.get('dimensions') else f"✨ {context.user_data.get('dimensions')}",
            "❌ انتخاب نشده" if not context.user_data.get('wire_length') else f"✨ {context.user_data.get('wire_length')} سانتی‌متر",
            "❌ انتخاب نشده" if not context.user_data.get('quantity') else f"✨ {context.user_data.get('quantity')} عدد"
        )
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎯 انتخاب نوع سنسور", callback_data='select_sensor_type')],
            [InlineKeyboardButton("📐 انتخاب ابعاد غلاف", callback_data='select_dimensions')],
            [InlineKeyboardButton("📏 انتخاب طول سیم", callback_data='select_wire_length')],
            [InlineKeyboardButton("🔢 انتخاب تعداد", callback_data='select_quantity')],
            [InlineKeyboardButton("✅ ثبت نهایی سفارش", callback_data='final_order')],
            [InlineKeyboardButton("🔙 بازگشت به منوی قبل", callback_data='back_products')]
        ])
        await query.edit_message_text(text=order_text, reply_markup=reply_markup)

    # --- پردازش ابعاد ---
    elif data.startswith('dim_'):
        dimensions = '6×50' if data == 'dim_6x50' else '4×25'
        context.user_data['dimensions'] = dimensions
        await query.answer(f"ابعاد {dimensions} انتخاب شد")

        order_text = """📋 مشخصات سفارش شما:
🎯 نوع سنسور: {}
📐 ابعاد غلاف: {}
📏 طول سیم: {}
🔢 تعداد: {}""".format(
            "❌ انتخاب نشده" if not context.user_data.get('sensor_type') else f"✨ {context.user_data.get('sensor_type')}",
            "❌ انتخاب نشده" if not context.user_data.get('dimensions') else f"✨ {context.user_data.get('dimensions')}",
            "❌ انتخاب نشده" if not context.user_data.get('wire_length') else f"✨ {context.user_data.get('wire_length')} سانتی‌متر",
            "❌ انتخاب نشده" if not context.user_data.get('quantity') else f"✨ {context.user_data.get('quantity')} عدد"
        )
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎯 انتخاب نوع سنسور", callback_data='select_sensor_type')],
            [InlineKeyboardButton("📐 انتخاب ابعاد غلاف", callback_data='select_dimensions')],
            [InlineKeyboardButton("📏 انتخاب طول سیم", callback_data='select_wire_length')],
            [InlineKeyboardButton("🔢 انتخاب تعداد", callback_data='select_quantity')],
            [InlineKeyboardButton("✅ ثبت نهایی سفارش", callback_data='final_order')],
            [InlineKeyboardButton("🔙 بازگشت به منوی قبل", callback_data='back_products')]
        ])
        await query.edit_message_text(text=order_text, reply_markup=reply_markup)

    # --- انتخاب طول سیم ---
    elif data == 'select_wire_length':
        text = """📏 لطفاً طول سیم را به سانتی‌متر وارد کنید:
⚡️ محدوده مجاز: 40 تا 500 سانتی‌متر"""
        context.user_data['awaiting_wire_length'] = True
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data='order')]
        ])
        await query.edit_message_text(text=text, reply_markup=reply_markup)

    # --- تعیین تعداد ---
    elif data == 'select_quantity':
        text = "🔢 لطفاً تعداد مورد نیاز را وارد کنید (عدد):"
        context.user_data['awaiting_quantity'] = True
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت به منوی سفارش", callback_data='order')]
        ])
        await query.edit_message_text(text=text, reply_markup=reply_markup)

    # --- ثبت نهایی سفارش ---
    elif data == 'final_order':
        if not all(key in context.user_data for key in ['sensor_type', 'dimensions', 'wire_length', 'quantity']):
            await query.answer("❌ لطفاً تمام موارد سفارش را تکمیل کنید.")
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
                payment_keyboard = [
                    [InlineKeyboardButton("💳 نهایی‌سازی سفارش و پرداخت", callback_data='payment_info')]
                ]
                await query.edit_message_text(
                    text=f"{order_details}\n\n✨ یک نسخه از سفارش به چت خصوصی شما ارسال شد.",
                    reply_markup=InlineKeyboardMarkup(payment_keyboard)
                )
                await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text=order_details,
                    reply_markup=InlineKeyboardMarkup(payment_keyboard)
                )

                # ارسال به کانال
                REPORT_CHANNEL_ID = -1002591533364  # ID کانال شما
                try:
                    await context.bot.send_message(chat_id=REPORT_CHANNEL_ID, text=order_details)
                except Exception as e:
                    logging.error(f"❌ خطای ارسال به کانال: {e}")

            except Exception as e:
                error_text = "⚠️ امکان ارسال پیام خصوصی وجود ندارد.\nلطفاً ابتدا با ربات چت کنید: @YourBotUsername"
                await query.answer(error_text, show_alert=True)

    # --- بازگشت به منو ---
    elif data == 'back_main':
        reply_markup = InlineKeyboardMarkup(main_menu)
        await query.edit_message_text(text="🛒 به فروشگاه ولتا استور خوش آمدید!", reply_markup=reply_markup)

    elif data == 'back_products':
        reply_markup = InlineKeyboardMarkup(product_menu)
        await query.edit_message_text(text="📌 منوی محصولات:", reply_markup=reply_markup)

    elif data == 'payment_info':
        payment_text = """💳 اطلاعات پرداخت:
لطفاً از یکی از روش‌های زیر برای پرداخت استفاده کنید:"""
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
            [InlineKeyboardButton("🔙 بازگشت به منوی پرداخت", callback_data='payment_info')]
        ]
        await query.edit_message_text(
            text=f"{payment_info[data]}\n\n✨ پس از پرداخت، لطفاً رسید را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup(send_receipt_button)
        )

    elif data == 'send_receipt':
        context.user_data['awaiting_receipt'] = True
        await query.edit_message_text(
            text="📸 لطفاً تصویر رسید پرداخت را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='payment_info')]])
        )

# هندلر پیام‌های متنی
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'awaiting_wire_length' in context.user_data and context.user_data['awaiting_wire_length']:
        try:
            length = int(update.message.text.strip())
            if 40 <= length <= 500:
                context.user_data['wire_length'] = length
                context.user_data['awaiting_wire_length'] = False
                order_text = """📋 مشخصات سفارش شما:
🎯 نوع سنسور: {}
📐 ابعاد غلاف: {}
📏 طول سیم: {}
🔢 تعداد: {}""".format(
                    "❌ انتخاب نشده" if not context.user_data.get('sensor_type') else f"✨ {context.user_data.get('sensor_type')}",
                    "❌ انتخاب نشده" if not context.user_data.get('dimensions') else f"✨ {context.user_data.get('dimensions')}",
                    f"✨ {length} سانتی‌متر",
                    "❌ انتخاب نشده" if not context.user_data.get('quantity') else f"✨ {context.user_data.get('quantity')} عدد"
                )
                reply_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎯 انتخاب نوع سنسور", callback_data='select_sensor_type')],
                    [InlineKeyboardButton("📐 انتخاب ابعاد غلاف", callback_data='select_dimensions')],
                    [InlineKeyboardButton("📏 انتخاب طول سیم", callback_data='select_wire_length')],
                    [InlineKeyboardButton("🔢 انتخاب تعداد", callback_data='select_quantity')],
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
                order_text = """📋 مشخصات سفارش شما:
🎯 نوع سنسور: {}
📐 ابعاد غلاف: {}
📏 طول سیم: {}
🔢 تعداد: {}""".format(
                    "❌ انتخاب نشده" if not context.user_data.get('sensor_type') else f"✨ {context.user_data.get('sensor_type')}",
                    "❌ انتخاب نشده" if not context.user_data.get('dimensions') else f"✨ {context.user_data.get('dimensions')}",
                    "❌ انتخاب نشده" if not context.user_data.get('wire_length') else f"✨ {context.user_data.get('wire_length')} سانتی‌متر",
                    f"✨ {quantity} عدد"
                )
                reply_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎯 انتخاب نوع سنسور", callback_data='select_sensor_type')],
                    [InlineKeyboardButton("📐 انتخاب ابعاد غلاف", callback_data='select_dimensions')],
                    [InlineKeyboardButton("📏 انتخاب طول سیم", callback_data='select_wire_length')],
                    [InlineKeyboardButton("🔢 انتخاب تعداد", callback_data='select_quantity')],
                    [InlineKeyboardButton("✅ ثبت نهایی سفارش", callback_data='final_order')],
                    [InlineKeyboardButton("🔙 بازگشت به منوی قبل", callback_data='back_products')]
                ])
                await update.message.reply_text(text=order_text, reply_markup=reply_markup)
            else:
                await update.message.reply_text("❌ لطفاً یک عدد مثبت وارد کنید.")
        except ValueError:
            await update.message.reply_text("❌ فقط عدد وارد کنید.")

# اجرای ربات
# هندلر عکس
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'awaiting_receipt' in context.user_data and context.user_data['awaiting_receipt']:
        # دریافت عکس با بالاترین کیفیت
        photo = update.message.photo[-1]
        
        # ارسال به کانال
        RECEIPT_CHANNEL_ID = -1002591533364  # ID کانال
        receipt_text = f"""📸 رسید پرداخت جدید
🆔 شناسه کاربر: {update.effective_user.id}
👤 نام کاربر: {update.effective_user.first_name}"""

        try:
            await context.bot.send_photo(
                chat_id=RECEIPT_CHANNEL_ID,
                photo=photo.file_id,
                caption=receipt_text
            )
            
            # پاسخ به کاربر
            await update.message.reply_text(
                "✅ رسید پرداخت شما با موفقیت ثبت شد.\nکارشناسان ما به زودی آن را بررسی خواهند کرد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data='back_main')]])
            )
            
            # پاک کردن وضعیت انتظار
            context.user_data['awaiting_receipt'] = False
            
        except Exception as e:
            logging.error(f"خطا در ارسال رسید: {e}")
            await update.message.reply_text("❌ متأسفانه در ثبت رسید خطایی رخ داد. لطفاً دوباره تلاش کنید.")

if __name__ == '__main__':
    app = ApplicationBuilder().token("7700497209:AAFiajp94LjmpF4FXa9aBr9558TvQUn6LKo").build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    print("🚀 ربات در حال اجرا است...")
    app.run_polling()