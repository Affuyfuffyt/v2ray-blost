import telebot
import os
from dotenv import load_dotenv

# تحميل المتغيرات
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

try:
    # جلب الأوامر المثبتة حالياً في البوت
    cmds = bot.get_my_commands()
    
    # حساب عدد أوامر start الموجودة
    start_cmds = [c for c in cmds if c.command.startswith("start")]
    count = len(start_cmds)

    # تحديد الأمر الجديد بناءً على العدد
    if count == 0:
        my_cmd = "start"
    else:
        my_cmd = f"start{count + 1}"

    # إضافة الأمر الجديد لقائمة البوت في تيليجرام
    new_cmd = telebot.types.BotCommand(my_cmd, f"⚙️ لوحة تحكم السيرفر رقم {count + 1}")
    cmds.append(new_cmd)
    bot.set_my_commands(cmds)

    # حفظ الأمر داخل ملف .env الخاص بهذا السيرفر حصراً
    with open(".env", "a") as f:
        f.write(f"\nMY_BOT_COMMAND={my_cmd}\n")

    print(f"[+] تم حجز وتثبيت الأمر الخاص بهذا السيرفر: /{my_cmd}")

except Exception as e:
    print(f"❌ حدث خطأ أثناء حجز الأمر: {e}")
