"""
Blocklist Flow (Telegram UI)
============================

لوحة تحكم داخل البوت لإدارة قائمة المواقع المحظورة (مثل مواقع فحص IP).
يستخدم xray_core.blocklist_manager للحفظ والتطبيق على xray.
"""

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sys
import os

# إجبار الملف على قراءة المسار الرئيسي
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from xray_core import blocklist_manager as bm

# عدد العناصر في الصفحة الواحدة لقوائم العرض/الحذف
PAGE_SIZE = 10


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _main_menu_markup():
    """القائمة الرئيسية لإدارة المواقع."""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ إضافة موقع", callback_data="bl_add"),
        InlineKeyboardButton("➖ حذف موقع", callback_data="bl_remove_page_0"),
    )
    markup.add(
        InlineKeyboardButton("📋 عرض القائمة", callback_data="bl_list_page_0"),
        InlineKeyboardButton("🔍 بحث", callback_data="bl_search"),
    )
    markup.add(
        InlineKeyboardButton("🔄 إعادة تطبيق على السيرفر", callback_data="bl_apply"),
    )
    markup.add(
        InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="admin_main_menu"),
    )
    return markup


def _status_text():
    """نص موجز يوضح حالة القائمة."""
    domains = bm.list_domains()
    keywords = bm.list_keywords()
    return (
        "🚫 *إدارة المواقع المحظورة*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 الدومينات المحظورة: *{len(domains)}*\n"
        f"🔑 الكلمات المفتاحية (catch-all): *{len(keywords)}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        "اختر إجراء من القائمة:"
    )


def _send_or_edit(bot, call, text, markup):
    """تحديث الرسالة الحالية أو إرسال جديدة."""
    try:
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown",
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=markup,
            parse_mode="Markdown",
        )


def _paginated_keyboard(items, page, callback_prefix, back_callback,
                        action_callback_prefix=None):
    """
    Build an inline keyboard with pagination.

    items: list of strings
    page: 0-based page index
    callback_prefix: prefix for page navigation callbacks (e.g. "bl_list_page")
    back_callback: callback_data for the back button
    action_callback_prefix: if set, each item becomes a button with this prefix
                            (e.g. "bl_del:") + the item value. Otherwise items
                            are rendered as text in the message only.
    """
    markup = InlineKeyboardMarkup(row_width=1)
    total = len(items)
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = items[start:end]

    if action_callback_prefix:
        for item in page_items:
            # Telegram callback_data is capped at 64 bytes — truncate if needed
            cb = f"{action_callback_prefix}{item}"[:64]
            markup.add(InlineKeyboardButton(f"❌ {item}", callback_data=cb))

    # Pagination row
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            "⬅️ السابق", callback_data=f"{callback_prefix}_{page - 1}"))
    nav.append(InlineKeyboardButton(
        f"📄 {page + 1}/{pages}", callback_data="bl_noop"))
    if page < pages - 1:
        nav.append(InlineKeyboardButton(
            "التالي ➡️", callback_data=f"{callback_prefix}_{page + 1}"))
    if len(nav) > 1:
        markup.row(*nav)

    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data=back_callback))
    return markup, page_items, page, pages


# ----------------------------------------------------------------------
# Registration
# ----------------------------------------------------------------------


def register_blocklist_handlers(bot):

    # 1) فتح القائمة الرئيسية
    @bot.callback_query_handler(func=lambda c: c.data == "manage_blocklist", is_admin=True)
    def open_blocklist_menu(call):
        _send_or_edit(bot, call, _status_text(), _main_menu_markup())
        bot.answer_callback_query(call.id)

    # 2) إعادة تطبيق على xray
    @bot.callback_query_handler(func=lambda c: c.data == "bl_apply", is_admin=True)
    def apply_now(call):
        bot.answer_callback_query(call.id, "⏳ جارٍ التطبيق...")
        ok, msg = bm.apply_and_restart()
        text = (
            f"{'✅' if ok else '❌'} *تطبيق على السيرفر:*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{msg}"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="manage_blocklist"))
        _send_or_edit(bot, call, text, markup)

    # 3) عرض القائمة (مع pagination)
    @bot.callback_query_handler(func=lambda c: c.data.startswith("bl_list_page_"), is_admin=True)
    def list_blocked(call):
        try:
            page = int(call.data.rsplit("_", 1)[1])
        except ValueError:
            page = 0
        domains = bm.list_domains()
        markup, page_items, page, pages = _paginated_keyboard(
            domains, page,
            callback_prefix="bl_list_page",
            back_callback="manage_blocklist",
        )
        if not domains:
            body = "_(القائمة فارغة)_"
        else:
            lines = "\n".join(f"• `{d}`" for d in page_items)
            body = (
                f"*المواقع المحظورة* ({len(domains)} إجمالي)\n"
                f"الصفحة {page + 1}/{pages}\n"
                f"━━━━━━━━━━━━━━━━━━\n{lines}"
            )
        _send_or_edit(bot, call, body, markup)
        bot.answer_callback_query(call.id)

    # 4) قائمة الحذف (كل موقع زرّ يحذفه عند الضغط)
    @bot.callback_query_handler(func=lambda c: c.data.startswith("bl_remove_page_"), is_admin=True)
    def remove_menu(call):
        try:
            page = int(call.data.rsplit("_", 1)[1])
        except ValueError:
            page = 0
        domains = bm.list_domains()
        markup, page_items, page, pages = _paginated_keyboard(
            domains, page,
            callback_prefix="bl_remove_page",
            back_callback="manage_blocklist",
            action_callback_prefix="bl_del:",
        )
        if not domains:
            body = "_(لا يوجد مواقع لحذفها)_"
        else:
            body = (
                f"*اضغط على الموقع لحذفه*\n"
                f"الصفحة {page + 1}/{pages} — إجمالي: {len(domains)}"
            )
        _send_or_edit(bot, call, body, markup)
        bot.answer_callback_query(call.id)

    # 5) تنفيذ حذف موقع
    @bot.callback_query_handler(func=lambda c: c.data.startswith("bl_del:"), is_admin=True)
    def do_delete(call):
        domain = call.data[len("bl_del:"):]
        ok, msg = bm.remove_domain(domain)
        if ok:
            ok2, apply_msg = bm.apply_and_restart()
            full_msg = f"{msg}\n\n{apply_msg}"
        else:
            full_msg = msg
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(
            "🔙 رجوع لقائمة الحذف", callback_data="bl_remove_page_0"))
        markup.add(InlineKeyboardButton(
            "🏠 القائمة الرئيسية", callback_data="manage_blocklist"))
        _send_or_edit(bot, call, full_msg, markup)
        bot.answer_callback_query(call.id, "تم")

    # 6) إضافة موقع — يطلب الإدخال
    @bot.callback_query_handler(func=lambda c: c.data == "bl_add", is_admin=True)
    def ask_add(call):
        msg = bot.send_message(
            call.message.chat.id,
            "📝 *أرسل الدومين الذي تريد حظره*\n"
            "(مثال: `ipinfo.io` أو `https://example.com`)\n\n"
            "لإضافة عدة دومينات، افصل بفاصلة أو سطر جديد.",
            parse_mode="Markdown",
        )
        bot.register_next_step_handler(msg, _process_add_input)
        bot.answer_callback_query(call.id)

    def _process_add_input(message):
        chat_id = message.chat.id
        raw = message.text or ""
        # دعم فاصلة أو سطر جديد
        candidates = [p.strip() for chunk in raw.splitlines()
                      for p in chunk.split(",")]
        candidates = [c for c in candidates if c]

        added, skipped, errors = [], [], []
        for c in candidates:
            ok, msg = bm.add_domain(c)
            if ok:
                added.append(c)
            elif "موجود" in msg:
                skipped.append(c)
            else:
                errors.append(c)

        lines = []
        if added:
            lines.append(f"✅ تمت الإضافة ({len(added)}):")
            lines.extend(f"   • `{bm._normalize_domain(d)}`" for d in added)
        if skipped:
            lines.append(f"⚠️ موجود مسبقاً ({len(skipped)}):")
            lines.extend(f"   • `{bm._normalize_domain(d)}`" for d in skipped)
        if errors:
            lines.append(f"❌ غير صالح ({len(errors)}):")
            lines.extend(f"   • `{d}`" for d in errors)

        if added:
            ok2, apply_msg = bm.apply_and_restart()
            lines.append("")
            lines.append(apply_msg)

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(
            "➕ إضافة المزيد", callback_data="bl_add"))
        markup.add(InlineKeyboardButton(
            "🏠 القائمة الرئيسية", callback_data="manage_blocklist"))

        bot.send_message(
            chat_id,
            "\n".join(lines) if lines else "_(لم يتم إدخال أي دومين)_",
            reply_markup=markup,
            parse_mode="Markdown",
        )

    # 7) بحث
    @bot.callback_query_handler(func=lambda c: c.data == "bl_search", is_admin=True)
    def ask_search(call):
        msg = bot.send_message(
            call.message.chat.id,
            "🔍 *أرسل كلمة البحث*\n(مثال: `ipinfo` أو `geo`)",
            parse_mode="Markdown",
        )
        bot.register_next_step_handler(msg, _process_search)
        bot.answer_callback_query(call.id)

    def _process_search(message):
        chat_id = message.chat.id
        query = (message.text or "").strip()
        results = bm.search_domains(query)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(
            "🏠 القائمة الرئيسية", callback_data="manage_blocklist"))
        if not results:
            body = f"❌ لا توجد نتائج لـ `{query}`."
        else:
            lines = "\n".join(f"• `{d}`" for d in results[:50])
            extra = ""
            if len(results) > 50:
                extra = f"\n_(عُرضت 50 من أصل {len(results)})_"
            body = (
                f"🔍 *نتائج البحث عن* `{query}`:\n"
                f"━━━━━━━━━━━━━━━━━━\n{lines}{extra}"
            )
        bot.send_message(chat_id, body, reply_markup=markup,
                         parse_mode="Markdown")

    # 8) noop (لزر الصفحة)
    @bot.callback_query_handler(func=lambda c: c.data == "bl_noop", is_admin=True)
    def noop(call):
        bot.answer_callback_query(call.id)
