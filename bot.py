import os
import json
import time
import random
import logging
import glob
import pyotp
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from instagrapi import Client

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# توكن البوت
TELEGRAM_TOKEN = "9020659460:AAHDDSsmPO7fp_S0mxRTDZB0p1fJYCncruk"

# الآي دي الخاص بك (مشرف البوت)
ADMIN_ID = 8075259769

ACCOUNTS_FILE = "accounts.json"

def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_accounts(accounts):
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, ensure_ascii=False, indent=4)

def login_instagram(acc):
    cl = Client()
    if acc.get("proxy"):
        cl.set_proxy(acc["proxy"])

    # التحقق مما إذا كان هناك رمز مصادقة ثنائية محفوظ للحساب
    two_factor_code = None
    if acc.get("two_factor_secret"):
        totp = pyotp.TOTP(acc["two_factor_secret"].replace(" ", ""))
        two_factor_code = totp.now()

    # تسجيل الدخول بدعم المصادقة الثنائية
    cl.login(acc["username"], acc["password"], verification_code=two_factor_code if two_factor_code else "")
    return cl

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("عذراً، هذا البوت خاص بكوخا ولا يمكنك استخدامه ❌")
        return

    msg = (
        "أهلاً بك يا كوخا في لوحة تحكم إنستغرام الشاملة 🚀\n\n"
        "🛠 **أوامر الإدارة:**\n"
        "➕ `/add_acc user pass [2fa_key]` : إضافة حساب (مع دعم 2FA اختياري)\n"
        "📋 `/list_acc` : عرض الحسابات\n"
        "❌ `/del_acc user` : حذف حساب\n\n"
        "🎯 **أوامر التفاعل:**\n"
        "👤 `/follow username [العدد]` : متابعة\n"
        "🚶‍♂️ `/unfollow username [العدد]` : إلغاء متابعة\n"
        "❤️ `/like media_url [العدد]` : لايك\n"
        "🤍 `/unlike media_url [العدد]` : إلغاء لايك\n"
        "💬 `/comment media_url [العدد] النص` : تعليق\n"
        "🚨 `/report username [العدد]` : بلاغ\n"
        "✨ `/update_profile [العدد]` : تغيير الصورة والبايو عشوائياً\n\n"
        "📥 **الإضافة المباشرة:**\n"
        "• أرسل أي **صورة** للبوت ليحفظها تلقائياً في مجلد الصور.\n"
        "• `/add_bio النص` : لإضافة سيرة ذاتية جديدة للقائمة."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def add_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text("الاستخدام الصحيح:\n`/add_acc اسم_المستخدم كلمة_المرور [مفتاح_المصادقة_الثنائية]`", parse_mode="Markdown")
        return

    username = context.args[0]
    password = context.args[1]
    two_factor_secret = context.args[2] if len(context.args) > 2 else ""

    accounts = load_accounts()
    for acc in accounts:
        if acc["username"] == username:
            await update.message.reply_text(f"الحساب `{username}` موجود مسبقاً ⚠️", parse_mode="Markdown")
            return

    accounts.append({
        "username": username,
        "password": password,
        "two_factor_secret": two_factor_secret,
        "proxy": ""
    })
    save_accounts(accounts)

    extra_info = " (مع دعم المصادقة الثنائية 🔐)" if two_factor_secret else ""
    await update.message.reply_text(f"تمت إضافة الحساب `{username}` بنجاح ✅{extra_info}", parse_mode="Markdown")

async def list_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    accounts = load_accounts()
    if not accounts:
        await update.message.reply_text("لا توجد حسابات مضافة حالياً 📭")
        return

    msg = "📋 **الحسابات المضافة:**\n\n"
    for idx, acc in enumerate(accounts, 1):
        has_2fa = " 🔐" if acc.get("two_factor_secret") else ""
        msg += f"{idx}. `{acc['username']}`{has_2fa}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def del_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("الاستخدام الصحيح:\n`/del_acc اسم_المستخدم`", parse_mode="Markdown")
        return

    username = context.args[0]
    accounts = load_accounts()
    new_accounts = [acc for acc in accounts if acc["username"] != username]

    if len(accounts) == len(new_accounts):
        await update.message.reply_text(f"لم يتم العثور على الحساب `{username}` ❌", parse_mode="Markdown")
    else:
        save_accounts(new_accounts)
        await update.message.reply_text(f"تم حذف الحساب `{username}` بنجاح 🗑️", parse_mode="Markdown")

async def follow_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("الاستخدام:\n`/follow username [العدد]`", parse_mode="Markdown")
        return

    accounts = load_accounts()
    if not accounts:
        await update.message.reply_text("أضف حسابات أولاً باستخدام `/add_acc` ⚠️", parse_mode="Markdown")
        return

    target_username = context.args[0]
    limit = len(accounts)
    if len(context.args) > 1 and context.args[1].isdigit():
        limit = int(context.args[1])

    active_accounts = accounts[:limit]
    await update.message.reply_text(f"جاري المتابعة للحساب `{target_username}` باستخدام {len(active_accounts)} حساب...", parse_mode="Markdown")

    success, fail = 0, 0
    for acc in active_accounts:
        try:
            cl = login_instagram(acc)
            target_id = cl.user_id_from_username(target_username)
            cl.user_follow(target_id)
            success += 1
            await update.message.reply_text(f"✅ [{acc['username']}] تمت المتابعة.")
        except Exception as e:
            fail += 1
            await update.message.reply_text(f"❌ [{acc['username']}] فشلت: {e}")
        time.sleep(random.randint(5, 10))

    await update.message.reply_text(f"📊 النتائج - نجاح: {success} | فشل: {fail}")

async def unfollow_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("الاستخدام:\n`/unfollow username [العدد]`", parse_mode="Markdown")
        return

    accounts = load_accounts()
    if not accounts:
        await update.message.reply_text("لا توجد حسابات مضافة ⚠️", parse_mode="Markdown")
        return

    target_username = context.args[0]
    limit = len(accounts)
    if len(context.args) > 1 and context.args[1].isdigit():
        limit = int(context.args[1])

    active_accounts = accounts[:limit]
    await update.message.reply_text(f"جاري إلغاء المتابعة للحساب `{target_username}` باستخدام {len(active_accounts)} حساب...", parse_mode="Markdown")

    success, fail = 0, 0
    for acc in active_accounts:
        try:
            cl = login_instagram(acc)
            target_id = cl.user_id_from_username(target_username)
            cl.user_unfollow(target_id)
            success += 1
            await update.message.reply_text(f"🚶‍♂️ [{acc['username']}] تم إلغاء المتابعة.")
        except Exception as e:
            fail += 1
            await update.message.reply_text(f"❌ [{acc['username']}] فشلت: {e}")
        time.sleep(random.randint(5, 10))

    await update.message.reply_text(f"📊 النتائج - نجاح: {success} | فشل: {fail}")

async def like_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("الاستخدام:\n`/like post_url [العدد]`", parse_mode="Markdown")
        return

    accounts = load_accounts()
    if not accounts:
        await update.message.reply_text("لا توجد حسابات مضافة ⚠️", parse_mode="Markdown")
        return

    post_url = context.args[0]
    limit = len(accounts)
    if len(context.args) > 1 and context.args[1].isdigit():
        limit = int(context.args[1])

    active_accounts = accounts[:limit]
    await update.message.reply_text(f"جاري إرسال الإعجابات باستخدام {len(active_accounts)} حساب...", parse_mode="Markdown")

    success, fail = 0, 0
    for acc in active_accounts:
        try:
            cl = login_instagram(acc)
            media_id = cl.media_pk_from_url(post_url)
            cl.media_like(media_id)
            success += 1
            await update.message.reply_text(f"❤️ [{acc['username']}] أعجب بالمنشور.")
        except Exception as e:
            fail += 1
            await update.message.reply_text(f"❌ [{acc['username']}] فشلت: {e}")
        time.sleep(random.randint(4, 8))

    await update.message.reply_text(f"📊 النتائج - نجاح: {success} | فشل: {fail}")

async def unlike_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("الاستخدام:\n`/unlike post_url [العدد]`", parse_mode="Markdown")
        return

    accounts = load_accounts()
    if not accounts:
        await update.message.reply_text("لا توجد حسابات مضافة ⚠️", parse_mode="Markdown")
        return

    post_url = context.args[0]
    limit = len(accounts)
    if len(context.args) > 1 and context.args[1].isdigit():
        limit = int(context.args[1])

    active_accounts = accounts[:limit]
    await update.message.reply_text(f"جاري إزالة الإعجابات باستخدام {len(active_accounts)} حساب...", parse_mode="Markdown")

    success, fail = 0, 0
    for acc in active_accounts:
        try:
            cl = login_instagram(acc)
            media_id = cl.media_pk_from_url(post_url)
            cl.media_unlike(media_id)
            success += 1
            await update.message.reply_text(f"🤍 [{acc['username']}] تم إلغاء الإعجاب.")
        except Exception as e:
            fail += 1
            await update.message.reply_text(f"❌ [{acc['username']}] فشلت: {e}")
        time.sleep(random.randint(4, 8))

    await update.message.reply_text(f"📊 النتائج - نجاح: {success} | فشل: {fail}")

async def comment_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text("الاستخدام:\n`/comment post_url [العدد] النص`", parse_mode="Markdown")
        return

    accounts = load_accounts()
    if not accounts:
        await update.message.reply_text("لا توجد حسابات مضافة ⚠️", parse_mode="Markdown")
        return

    post_url = context.args[0]
    if len(context.args) > 2 and context.args[1].isdigit():
        limit = int(context.args[1])
        comment_text = " ".join(context.args[2:])
    else:
        limit = len(accounts)
        comment_text = " ".join(context.args[1:])

    active_accounts = accounts[:limit]
    await update.message.reply_text(f"جاري التعليق بـ ({comment_text}) باستخدام {len(active_accounts)} حساب...", parse_mode="Markdown")

    success, fail = 0, 0
    for acc in active_accounts:
        try:
            cl = login_instagram(acc)
            media_id = cl.media_pk_from_url(post_url)
            cl.media_comment(media_id, comment_text)
            success += 1
            await update.message.reply_text(f"💬 [{acc['username']}] علق بنجاح.")
        except Exception as e:
            fail += 1
            await update.message.reply_text(f"❌ [{acc['username']}] فشلت: {e}")
        time.sleep(random.randint(6, 12))

    await update.message.reply_text(f"📊 النتائج - نجاح: {success} | فشل: {fail}")

async def report_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("الاستخدام:\n`/report username [العدد]`", parse_mode="Markdown")
        return

    accounts = load_accounts()
    if not accounts:
        await update.message.reply_text("لا توجد حسابات مضافة ⚠️", parse_mode="Markdown")
        return

    target_username = context.args[0]
    limit = len(accounts)
    if len(context.args) > 1 and context.args[1].isdigit():
        limit = int(context.args[1])

    active_accounts = accounts[:limit]
    await update.message.reply_text(f"جاري إرسال البلاغات للحساب `{target_username}` باستخدام {len(active_accounts)} حساب...", parse_mode="Markdown")

    success, fail = 0, 0
    for acc in active_accounts:
        try:
            cl = login_instagram(acc)
            target_id = cl.user_id_from_username(target_username)
            cl.user_report(target_id)
            success += 1
            await update.message.reply_text(f"🚨 [{acc['username']}] تم إرسال البلاغ.")
        except Exception as e:
            fail += 1
            await update.message.reply_text(f"❌ [{acc['username']}] فشلت: {e}")
        time.sleep(random.randint(5, 10))

    await update.message.reply_text(f"📊 النتائج - نجاح: {success} | فشل: {fail}")

async def update_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    accounts = load_accounts()
    if not accounts:
        await update.message.reply_text("لا توجد حسابات مضافة ⚠️", parse_mode="Markdown")
        return

    limit = len(accounts)
    if len(context.args) > 0 and context.args[0].isdigit():
        limit = int(context.args[0])

    active_accounts = accounts[:limit]

    image_paths = glob.glob("avatars/*.jpg") + glob.glob("avatars/*.png") + glob.glob("avatars/*.jpeg")

    bios = []
    if os.path.exists("bios.txt"):
        with open("bios.txt", "r", encoding="utf-8") as f:
            bios = [line.strip() for line in f if line.strip()]

    if not image_paths and not bios:
        await update.message.reply_text("تأكد من توفر صور أو سير ذاتية أولاً ⚠️", parse_mode="Markdown")
        return

    await update.message.reply_text(f"جاري تحديث الملفات الشخصية لـ {len(active_accounts)} حساب...", parse_mode="Markdown")

    success, fail = 0, 0
    for acc in active_accounts:
        try:
            cl = login_instagram(acc)

            if image_paths:
                random_img = random.choice(image_paths)
                cl.account_change_picture(random_img)

            if bios:
                random_bio = random.choice(bios)
                cl.account_set_biography(random_bio)

            success += 1
            await update.message.reply_text(f"✨ [{acc['username']}] تم تحديث الملف الشخصي بنجاح.")
        except Exception as e:
            fail += 1
            await update.message.reply_text(f"❌ [{acc['username']}] فشلت: {e}")
        time.sleep(random.randint(6, 12))

    await update.message.reply_text(f"📊 النتائج - نجاح: {success} | فشل: {fail}")

async def add_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("الاستخدام:\n`/add_bio السيرة الذاتية الجديدة`", parse_mode="Markdown")
        return

    new_bio = " ".join(context.args)
    os.makedirs(".", exist_ok=True)
    with open("bios.txt", "a", encoding="utf-8") as f:
        f.write(new_bio + "\n")

    await update.message.reply_text(f"✅ تمت إضافة البايو بنجاح إلى القائمة:\n`{new_bio}`", parse_mode="Markdown")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    os.makedirs("avatars", exist_ok=True)
    photo_file = await update.message.photo[-1].get_file()

    file_name = f"avatars/img_{int(time.time())}_{random.randint(100,999)}.jpg"
    await photo_file.download_to_drive(file_name)

    await update.message.reply_text("📥 تم استلام وحفظ الصورة في مجلد `avatars` بنجاح وتصبح جاهزة للاستخدام ✅", parse_mode="Markdown")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add_acc", add_account))
    application.add_handler(CommandHandler("list_acc", list_accounts))
    application.add_handler(CommandHandler("del_acc", del_account))
    application.add_handler(CommandHandler("follow", follow_target))
    application.add_handler(CommandHandler("unfollow", unfollow_target))
    application.add_handler(CommandHandler("like", like_post))
    application.add_handler(CommandHandler("unlike", unlike_post))
    application.add_handler(CommandHandler("comment", comment_post))
    application.add_handler(CommandHandler("report", report_target))
    application.add_handler(CommandHandler("update_profile", update_profile))
    application.add_handler(CommandHandler("add_bio", add_bio))

    application.add_handler(MessageHandler(filters.PHOTO & filters.User(user_id=ADMIN_ID), handle_photo))

    print("البوت يعمل الآن بدعم كامل للمصادقة الثنائية 2FA...")
    application.run_polling()
