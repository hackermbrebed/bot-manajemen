# handlers/welcome.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode, ChatType
from handlers.core import GLOBAL_CONFIG, logger, is_global_admin, create_inline_keyboard

# Global state untuk menyimpan proses konfigurasi tombol (perlu karena ini stateful)
BUTTON_SETUP_DATA = {} 

# --- HANDLER PENYAMBUTAN UTAMA ---

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengirim pesan penyambutan saat anggota baru bergabung."""
    if update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return

    for member in update.message.new_chat_members:
        if member.is_bot: continue
        
        user_name = member.full_name
        chat_title = update.effective_chat.title
        
        formatted_message = GLOBAL_CONFIG['welcome_message'].format(
            user_name=user_name,
            chat_title=chat_title,
            # Tambahkan variabel lain seperti {user_id} atau {user_username} jika diperlukan
        )

        reply_markup = create_inline_keyboard(GLOBAL_CONFIG['welcome_buttons'])
        
        try:
            if GLOBAL_CONFIG['welcome_photo_id']:
                await update.effective_chat.send_photo(
                    photo=GLOBAL_CONFIG['welcome_photo_id'],
                    caption=formatted_message,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.effective_chat.send_message(
                    text=formatted_message,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            logger.info(f"Welcome sent to {user_name} in {chat_title}")
        except Exception as e:
            logger.error(f"Gagal mengirim pesan welcome: {e}")

# --- PERINTAH KONFIGURASI (Hanya Global Admin) ---

@is_global_admin
async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengatur pesan sambutan. Gunakan {user_name} dan {chat_title}."""
    if not context.args:
        await update.message.reply_text(
            "Format: `/setwelcome Pesan Sambutan Anda`. Gunakan `{user_name}` dan `{chat_title}` sebagai placeholder. "
            f"\n\nPesan saat ini: \n`{GLOBAL_CONFIG['welcome_message']}`",
            parse_mode='Markdown'
        )
        return

    new_message = " ".join(context.args)
    GLOBAL_CONFIG['welcome_message'] = new_message
    await update.message.reply_text("✅ Pesan sambutan berhasil diperbarui!")

@is_global_admin
async def set_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengatur foto penyambutan dari foto yang dibalas."""
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text("Mohon balas (reply) ke FOTO lalu ketik `/setphoto`.")
        return

    photo_file_id = update.message.reply_to_message.photo[-1].file_id
    GLOBAL_CONFIG['welcome_photo_id'] = photo_file_id
    await update.message.reply_text("✅ Foto penyambutan berhasil diatur!")

@is_global_admin
async def start_set_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memulai proses pengaturan tombol inline."""
    BUTTON_SETUP_DATA[update.effective_user.id] = [] 
    context.user_data['setting_buttons'] = True

    await update.message.reply_text(
        "📝 Pengaturan Tombol Inline Dimulai.\nFormat: `Nama Tombol URL_LENGKAP`\nKetik `/donebuttons` saat selesai."
    )

@is_global_admin
async def done_set_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menyelesaikan proses pengaturan tombol inline."""
    user_id = update.effective_user.id
    if not context.user_data.get('setting_buttons'): return
    
    new_config = BUTTON_SETUP_DATA.pop(user_id, [])
    
    if new_config:
        GLOBAL_CONFIG['welcome_buttons'] = new_config
        preview_markup = create_inline_keyboard(GLOBAL_CONFIG['welcome_buttons'])
        await update.message.reply_text(
            "✅ Tombol inline berhasil diubah!\nPratinjau:",
            reply_markup=preview_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("Tidak ada tombol yang ditambahkan.")
        
    context.user_data['setting_buttons'] = False

@is_global_admin
async def handle_button_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani input teks selama proses /setbutton."""
    user_id = update.effective_user.id
    if not context.user_data.get('setting_buttons') or update.effective_chat.type != ChatType.PRIVATE: return
    
    text = update.message.text
    parts = text.split(maxsplit=1)
    
    if len(parts) == 2 and parts[1].startswith(('http', 't.me')):
        BUTTON_SETUP_DATA[user_id].append([parts[0], parts[1]])
        await update.message.reply_text(
            f"✅ Tombol '{parts[0]}' ditambahkan. Total: {len(BUTTON_SETUP_DATA[user_id])}. Lanjutkan atau ketik `/donebuttons`."
        )
    else:
        await update.message.reply_text("Format tidak valid. Gunakan: `Nama Tombol URL_LENGKAP`")


# --- DAFTAR HANDLER WELCOME ---

welcome_handlers = [
    MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member),
    # Konfigurasi Admin (Private Chat)
    CommandHandler("setwelcome", set_welcome),
    CommandHandler("setphoto", set_photo),
    CommandHandler("setbuttons", start_set_button),
    CommandHandler("donebuttons", done_set_button),
    MessageHandler(filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND, handle_button_input),
]
