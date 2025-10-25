# handlers/core.py

import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatType

# --- SETUP LINGKUNGAN ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID_STR = os.getenv("ADMIN_USER_ID") 

# --- SETUP LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("ManagerBot")

# --- VARIABEL GLOBAL DATA (Akan diisi melalui perintah admin) ---
# Menggunakan dictionary untuk menyimpan konfigurasi per-grup jika diperlukan di masa depan.
GLOBAL_CONFIG = {
    'welcome_message': "<blockquote>👋 Selamat datang, {user_name}! Di grup {chat_title}. Jangan lupa baca Rules!</blockquote>",
    'welcome_photo_id': None,
    'welcome_buttons': [['🤖 Pemilik Bot', 'https://t.me/GANTI_USERNAME_ANDA']],
}

# --- DECORATOR DAN UTILITIES ---

def is_global_admin(func):
    """Membatasi perintah hanya untuk Pemilik Bot Global."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            admin_id_int = int(ADMIN_USER_ID_STR.strip())
        except ValueError:
             logger.error("ADMIN_USER_ID di .env tidak valid.")
             return

        if update.effective_user.id != admin_id_int:
            if update.effective_chat.type == ChatType.PRIVATE:
                await update.message.reply_text("⛔️ Perintah ini hanya untuk pemilik bot.")
            return

        return await func(update, context)
    return wrapper

async def is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Mengecek apakah pengguna adalah admin (Creator/Administrator) di grup saat ini."""
    if update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("Perintah ini hanya berlaku di grup.")
        return False
    
    chat_member = await context.bot.get_chat_member(
        update.effective_chat.id, update.effective_user.id
    )
    if chat_member.status not in ['creator', 'administrator']:
        await update.message.reply_text("⛔️ Anda harus menjadi Admin grup untuk menggunakan perintah ini.")
        return False
    
    return True

# Fungsi sederhana untuk membuat keyboard inline
def create_inline_keyboard(config):
    """Membuat InlineKeyboardMarkup (Pola sederhana 1 tombol per baris)."""
    keyboard_buttons = []
    for text, action in config:
        if action.startswith(('http', 't.me')):
            keyboard_buttons.append([InlineKeyboardButton(text, url=action)])
    return InlineKeyboardMarkup(keyboard_buttons) if keyboard_buttons else None
