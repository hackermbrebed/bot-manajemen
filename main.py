# manager_bot_v2.py
# Powered bot by @hackermbrebed

import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions, ChatMember
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)
from telegram.constants import ParseMode, ChatType
from datetime import timedelta
import asyncio

# Muat variabel lingkungan dari file .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID_STR = os.getenv("ADMIN_USER_ID")

# Konfigurasi logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("ManagerBotV2")


# ----------------------------------------------------------------------
## KONFIGURASI GLOBAL & PERMANEN
# ----------------------------------------------------------------------

# Pesan penyambutan PERMANEN (diambil dari skrip, tidak bisa diubah via bot lagi)
WELCOME_MESSAGE = (
    "<blockquote>👋𝙒𝙀𝙇𝘾𝙊𝙈𝙀, {user_name}! 𝙎𝙚𝙡𝙖𝙢𝙖𝙩 𝙗𝙚𝙧𝙜𝙖𝙗𝙪𝙣𝙜 𝙙𝙞 𝙜𝙧𝙪𝙥 𝙠𝙖𝙢𝙞🎉</blockquote>\n\n"
    "╭❈━━━━━━❖ ❖━━━━━━❈╮\n"
    "┣𝐉𝐚𝐧𝐠𝐚𝐧 𝐫𝐞𝐬𝐞𝐤 𝐝𝐚𝐧 𝐢𝐤𝐮𝐭𝐢 𝐫𝐮𝐥𝐞𝐬\n"
    "┣𝐲𝐚𝐧𝐠 𝐚𝐝𝐚!\n"
    "╰❈━━━━━━❖ ❖━━━━━━❈╯\n"
    "╭❈━━━━━━❖ ❖━━━━━━❈╮\n"
    "┣|ɪᴅ ➭  <code>{user_id}</code>\n"
    "┣|ᴜsᴇʀɴᴀᴍᴇ ➭  @{user_username}\n"
    "╰❈━━━━━━❖ ❖━━━━━━❈╯\n\n"
    "<blockquote>𝙎𝙚𝙢𝙤𝙜𝙖 𝙗𝙚𝙩𝙖𝙝!</blockquote>\n"
    "<blockquote>𝘗𝘰𝘸𝘦𝘳𝘦𝘥 𝘣𝘰𝘵 𝘣𝘺 𝕂𝕒𝕚𝕤𝕒𝕣 𝕌𝕕𝕚𝕟👑</blockquote>"
)

# Konfigurasi foto dan tombol yang BISA disetel oleh admin global
GLOBAL_PHOTO_FILE_ID = None
GLOBAL_BUTTONS_CONFIG = [
    ['🤖𝙋𝙚𝙢𝙞𝙡𝙞𝙠 𝘽𝙊𝙏', 'https://t.me/udiens123'],
]

# Variabel konfigurasi baru
BUTTON_SETUP_DATA = {}
RULES_MESSAGE = "❌ Aturan grup belum ditetapkan. Gunakan /setrules untuk mengaturnya."

# ----------------------------------------------------------------------
## FUNGSI UTILITAS DAN DECORATOR
# ----------------------------------------------------------------------

def create_inline_keyboard(config):
    """Membuat objek InlineKeyboardMarkup dari list konfigurasi tombol URL."""
    keyboard_buttons = []
    inline_btns = []
    
    for text, action in config:
        if action.startswith(('http', 't.me')):
            inline_btns.append(InlineKeyboardButton(text, url=action))

    i = 0
    while i < len(inline_btns):
        if (len(inline_btns) - i >= 2) and (len(keyboard_buttons) % 2 == 0):
            keyboard_buttons.append(inline_btns[i:i+2])
            i += 2
        elif i < len(inline_btns):
            keyboard_buttons.append([inline_btns[i]])
            i += 1
            
    return InlineKeyboardMarkup(keyboard_buttons) if keyboard_buttons else None

def admin_private_only(func):
    """Membatasi fungsi hanya untuk ADMIN_USER_ID dan hanya di private chat."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        cleaned_admin_id_str = ADMIN_USER_ID_STR.strip()
        try:
            admin_id_int = int(cleaned_admin_id_str)
        except (ValueError, TypeError):
             logger.error(f"ADMIN_USER_ID ('{cleaned_admin_id_str}') di file .env tidak valid.")
             if update.effective_chat.type == ChatType.PRIVATE:
                 await update.message.reply_text("Kesalahan konfigurasi: ID Admin tidak valid di file .env.")
             return
        
        if update.effective_user.id != admin_id_int:
            if update.effective_chat.type == ChatType.PRIVATE:
                await update.message.reply_text("Maaf, Anda bukan administrator global bot ini.")
            return

        if update.effective_chat.type != ChatType.PRIVATE:
            await update.message.reply_text("Perintah konfigurasi ini hanya dapat digunakan dalam **private chat** dengan bot.")
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
    
    if chat_member.status not in [ChatMember.CREATOR, ChatMember.ADMINISTRATOR]:
        await update.message.reply_text("⛔️ Anda harus menjadi Admin grup untuk menggunakan perintah ini.")
        return False
    
    return True

# ----------------------------------------------------------------------
## HANDLER UTAMA GRUP: WELCOME & RULES
# ----------------------------------------------------------------------

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengirim pesan penyambutan saat anggota baru bergabung ke grup."""
    global WELCOME_MESSAGE, GLOBAL_PHOTO_FILE_ID, GLOBAL_BUTTONS_CONFIG
    
    if update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return

    chat = update.effective_chat
    for member in update.message.new_chat_members:
        if member.is_bot: continue
        
        user_id = member.id
        user_name = member.full_name
        user_username = member.username if member.username else 'None'
        
        formatted_message = WELCOME_MESSAGE.format(
            user_name=user_name,
            user_id=user_id,
            user_username=user_username
        )

        reply_markup = create_inline_keyboard(GLOBAL_BUTTONS_CONFIG)
        
        if GLOBAL_PHOTO_FILE_ID:
            try:
                await context.bot.send_photo(
                    chat_id=chat.id, photo=GLOBAL_PHOTO_FILE_ID, caption=formatted_message,
                    reply_markup=reply_markup, parse_mode=ParseMode.HTML
                )
            except Exception:
                await context.bot.send_message(
                    chat_id=chat.id, text=formatted_message,
                    reply_markup=reply_markup, parse_mode=ParseMode.HTML
                )
        else:
            await context.bot.send_message(
                chat_id=chat.id, text=formatted_message,
                reply_markup=reply_markup, parse_mode=ParseMode.HTML
            )

async def set_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengatur pesan aturan grup (/setrules)."""
    if not await is_group_admin(update, context): return
    global RULES_MESSAGE
    
    if not context.args:
        await update.message.reply_text(
            "Format: `/setrules Teks Aturan Anda`. Gunakan Markdown/HTML untuk format.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    new_rules = " ".join(context.args)
    RULES_MESSAGE = new_rules
    await update.message.reply_text("✅ Aturan grup berhasil diperbarui!")

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan aturan grup (/rules)."""
    global RULES_MESSAGE
    if update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("Perintah ini hanya berlaku di grup.")
        return

    try:
        await update.message.reply_text(RULES_MESSAGE, parse_mode=ParseMode.HTML)
    except:
        await update.message.reply_text(RULES_MESSAGE, parse_mode=ParseMode.MARKDOWN) # Fallback

# ----------------------------------------------------------------------
## HANDLER UTILITAS & MODERASI
# ----------------------------------------------------------------------

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengukur latency bot (/ping)."""
    if update.effective_chat.type == ChatType.PRIVATE:
        await update.message.reply_text("Bot aktif. Latensi hanya dapat diukur di grup.")
        return
        
    start_time = update.message.date.timestamp()
    sent_message = await update.message.reply_text("Pinging...")
    end_time = sent_message.date.timestamp()
    latency = round((end_time - start_time) * 1000)
    
    await sent_message.edit_text(f"Pong! 🏓 Latensi: **{latency}ms**", parse_mode=ParseMode.MARKDOWN)

async def vctitle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengubah judul obrolan suara/video grup (/vctitle)."""
    if not await is_group_admin(update, context): return
    
    if not context.args:
        await update.message.reply_text("Format: `/vctitle Judul Obrolan Suara Baru`")
        return
        
    new_title = " ".join(context.args)
    if len(new_title) > 255:
        await update.message.reply_text("Judul terlalu panjang. Maksimal 255 karakter.")
        return

    try:
        await context.bot.set_chat_title(
            chat_id=update.effective_chat.id,
            title=new_title
        )
        await update.message.reply_text(f"✅ Judul grup berhasil diubah menjadi **{new_title}**.", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Gagal ubah judul VC: {e}")
        await update.message.reply_text("❌ Gagal mengubah judul. Pastikan bot memiliki izin **'Change Group Info'**.")

async def adminlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan daftar admin grup (/adminlist)."""
    if update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("Perintah ini hanya berlaku di grup.")
        return

    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        admin_list = []
        for admin in admins:
            user = admin.user
            status = admin.status
            name = user.full_name
            
            if user.is_bot:
                continue
                
            line = f"• {name} (`{user.id}`)"
            if status == ChatMember.CREATOR:
                line = f"👑 {name} (`Creator`)"
            elif admin.custom_title:
                 line = f"🔸 {name} (`{admin.custom_title}`)"
            
            admin_list.append(line)
            
        
        response = f"**Daftar Admin Grup {update.effective_chat.title} ({len(admin_list)}):**\n\n" + "\n".join(admin_list)
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    
    except Exception as e:
        logger.error(f"Gagal menampilkan adminlist: {e}")
        await update.message.reply_text("❌ Gagal mengambil daftar admin.")

async def reload_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Perintah untuk reload konfigurasi (simulasi) oleh admin global."""
    if not await is_group_admin(update, context): return
    
    # Karena konfigurasi (photo/button/rules) disimpan di memori,
    # 'reload' di sini hanya berfungsi sebagai penanda log & konfirmasi admin.
    await update.message.reply_text("⚙️ Konfigurasi bot (Rules, Foto, Tombol) telah dimuat ulang dari memori.")
    
async def anonadmin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengatur anonimitas admin bot saat membalas pesan (/anonadmin)."""
    if not await is_group_admin(update, context): return
    
    if update.effective_chat.type not in [ChatType.SUPERGROUP]:
        await update.message.reply_text("Perintah ini hanya berlaku di Supergrup.")
        return

    current_member = await context.bot.get_chat_member(update.effective_chat.id, context.bot.id)
    
    if current_member.status != ChatMember.ADMINISTRATOR:
        await update.message.reply_text("Bot ini bukan admin grup, tidak bisa mengubah pengaturan anonimitas.")
        return
        
    # Toggle Anonimitas
    new_anonimity_status = not current_member.is_anonymous
    
    try:
        await context.bot.set_chat_administrator_custom_title(
            chat_id=update.effective_chat.id,
            user_id=context.bot.id,
            custom_title=current_member.custom_title if current_member.custom_title else "Bot",
            is_anonymous=new_anonimity_status
        )
        status_text = "DI-AKTIFKAN" if new_anonimity_status else "DI-NONAKTIFKAN"
        await update.message.reply_text(f"✅ Mode anonimitas bot saat membalas pesan **{status_text}**.", parse_mode=ParseMode.MARKDOWN)
    
    except Exception as e:
        logger.error(f"Gagal set anonimitas: {e}")
        await update.message.reply_text("❌ Gagal mengubah status anonimitas. Pastikan bot adalah Admin dengan izin 'Change Group Info'.")


# ----------------------------------------------------------------------
## HANDLER PROMOSI & DEMOSI
# ----------------------------------------------------------------------

# Izin Admin Penuh
FULL_PERMISSIONS = ChatPermissions(
    can_manage_chat=True,
    can_delete_messages=True,
    can_manage_video_chats=True,
    can_restrict_members=True,
    can_promote_members=True,
    can_change_info=True,
    can_invite_users=True,
    can_pin_messages=True
)
# Izin Admin Standar (Admin baru, tanpa promote/anonimitas)
STANDARD_PERMISSIONS = ChatPermissions(
    can_manage_chat=False,
    can_delete_messages=True,
    can_manage_video_chats=False,
    can_restrict_members=True,
    can_promote_members=False, # Tidak bisa promote/demote
    can_change_info=False,
    can_invite_users=True,
    can_pin_messages=True
)

async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mempromosikan pengguna yang dibalas dengan izin standar (/promote)."""
    if not await is_group_admin(update, context): return
    
    target_msg = update.message.reply_to_message
    if not target_msg:
        await update.message.reply_text("Mohon balas pesan pengguna yang ingin dipromosikan.")
        return
    
    target_user = target_msg.from_user
    
    try:
        await context.bot.promote_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target_user.id,
            # Promosikan dengan izin standar
            is_anonymous=False,
            **STANDARD_PERMISSIONS.to_dict()
        )
        await update.message.reply_text(f"✅ Pengguna **{target_user.full_name}** telah dipromosikan sebagai Admin standar.", parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Gagal promote user: {e}")
        await update.message.reply_text("❌ Gagal mempromosikan. Bot harus Admin dengan izin **'Add new admins'** dan wewenang yang lebih tinggi dari target.")

async def full_promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mempromosikan pengguna yang dibalas dengan izin admin penuh (/fullpromote)."""
    if not await is_group_admin(update, context): return
    
    target_msg = update.message.reply_to_message
    if not target_msg:
        await update.message.reply_text("Mohon balas pesan pengguna yang ingin dipromosikan penuh.")
        return
    
    target_user = target_msg.from_user
    
    try:
        await context.bot.promote_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target_user.id,
            # Promosikan dengan izin penuh (termasuk promote/demote)
            is_anonymous=False,
            **FULL_PERMISSIONS.to_dict()
        )
        await update.message.reply_text(f"✅ Pengguna **{target_user.full_name}** telah dipromosikan sebagai **Admin Penuh**.", parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Gagal full promote user: {e}")
        await update.message.reply_text("❌ Gagal mempromosikan penuh. Bot harus Admin dengan izin **'Add new admins'** dan wewenang yang lebih tinggi dari target.")

async def demote_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mendemosi pengguna yang dibalas, mencabut status admin (/demote)."""
    if not await is_group_admin(update, context): return
    
    target_msg = update.message.reply_to_message
    if not target_msg:
        await update.message.reply_text("Mohon balas pesan pengguna yang ingin didemosi.")
        return
    
    target_user = target_msg.from_user
    
    # Cegah demote diri sendiri atau Creator
    if target_user.id == update.effective_user.id:
        await update.message.reply_text("Anda tidak bisa mendemosi diri Anda sendiri.")
        return
    
    try:
        # Mendemosi berarti mempromosikan kembali tanpa izin admin (is_admin=False)
        await context.bot.promote_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target_user.id,
            can_manage_chat=False,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )
        await update.message.reply_text(f"✅ Admin **{target_user.full_name}** telah didemosi menjadi anggota biasa.", parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Gagal demote user: {e}")
        await update.message.reply_text("❌ Gagal mendemosi. Bot harus Admin dan tidak bisa mendemosi Creator grup atau admin yang wewenangnya lebih tinggi.")

# ----------------------------------------------------------------------
## HANDLER MODERASI DASAR
# ----------------------------------------------------------------------

# (Mute, Unmute, Pin, Ban - menggunakan fungsi dari skrip sebelumnya)
async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menyematkan (pin) pesan yang dibalas."""
    if not await is_group_admin(update, context): return
    if not update.message.reply_to_message:
        await update.message.reply_text("Mohon balas pesan yang ingin di-pin.")
        return
    try:
        await context.bot.pin_chat_message(
            chat_id=update.effective_chat.id, message_id=update.message.reply_to_message.message_id,
            disable_notification=True
        )
        await update.message.reply_text("✅ Pesan berhasil di-pin.")
    except Exception as e:
        logger.error(f"Gagal pin pesan: {e}")
        await update.message.reply_text("❌ Gagal pin. Pastikan bot adalah Admin dan memiliki izin **'Pin Messages'**.")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Membatasi (mute) pengguna yang dibalas (default: 1 jam)."""
    if not await is_group_admin(update, context): return
    target_msg = update.message.reply_to_message
    if not target_msg:
        await update.message.reply_text("Mohon balas pesan pengguna yang ingin di-mute.")
        return
    target_user = target_msg.from_user
    until_date = update.message.date + timedelta(hours=1)
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id, user_id=target_user.id, until_date=until_date,
            permissions=ChatPermissions(can_send_messages=False),
        )
        await update.message.reply_text(f"✅ Pengguna **{target_user.full_name}** telah di-mute selama 1 jam.", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Gagal mute user: {e}")
        await update.message.reply_text("❌ Gagal mute. Pastikan bot memiliki izin **'Restrict Members'**.")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Membuka pembatasan (unmute) pengguna yang dibalas."""
    if not await is_group_admin(update, context): return
    target_msg = update.message.reply_to_message
    if not target_msg:
        await update.message.reply_text("Mohon balas pesan pengguna yang ingin di-unmute.")
        return
    target_user = target_msg.from_user
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id, user_id=target_user.id,
            permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_polls=True, can_send_other_messages=True),
        )
        await update.message.reply_text(f"✅ Pengguna **{target_user.full_name}** telah di-unmute.", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Gagal unmute user: {e}")
        await update.message.reply_text("❌ Gagal unmute. Pastikan bot memiliki izin **'Restrict Members'**.")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memblokir (ban) pengguna yang dibalas."""
    if not await is_group_admin(update, context): return
    target_msg = update.message.reply_to_message
    if not target_msg:
        await update.message.reply_text("Mohon balas pesan pengguna yang ingin di-ban.")
        return
    target_user = target_msg.from_user
    try:
        await context.bot.ban_chat_member(
            chat_id=update.effective_chat.id, user_id=target_user.id
        )
        await update.message.reply_text(f"✅ Pengguna **{target_user.full_name}** telah diban dari grup secara permanen.", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Gagal ban user: {e}")
        await update.message.reply_text("❌ Gagal ban. Pastikan bot memiliki izin **'Ban Users'** dan wewenang yang lebih tinggi dari target.")


# ----------------------------------------------------------------------
## HANDLER KONFIGURASI (Private Chat Only)
# ----------------------------------------------------------------------
# (set_photo, start_set_button, done_set_button, cancel_set_button, handle_button_input, show_current_config)

@admin_private_only
async def set_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengatur foto penyambutan dari foto yang dibalas (reply)."""
    global GLOBAL_PHOTO_FILE_ID
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text("Mohon balas (reply) ke **FOTO** di chat ini lalu ketik `/setphoto`.")
        return
    photo_file_id = update.message.reply_to_message.photo[-1].file_id
    GLOBAL_PHOTO_FILE_ID = photo_file_id
    await update.message.reply_text("✅ Foto penyambutan berhasil diatur!\nFoto ini akan muncul pada sambutan anggota baru.", parse_mode='Markdown')

@admin_private_only
async def start_set_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memulai proses pengaturan tombol inline."""
    user_id = update.effective_user.id
    BUTTON_SETUP_DATA[user_id] = []
    context.user_data['setting_buttons'] = True
    await update.message.reply_text(
        "📝 Pengaturan Tombol Inline Dimulai\n\n"
        "Silakan masukkan Nama Tombol dan URL Link pada baris baru.\n"
        "Formatnya adalah: `Nama Tombol Anda URL_LENGKAP`\n"
        "Contoh: `Gabung Grup https://t.me/grupAnda`\n\n"
        "Ketik `/donebutton` saat selesai, atau `/cancelbutton` untuk membatalkan."
    )

@admin_private_only
async def done_set_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menyelesaikan proses pengaturan tombol inline."""
    global GLOBAL_BUTTONS_CONFIG
    user_id = update.effective_user.id
    if not context.user_data.get('setting_buttons'):
        await update.message.reply_text("Anda tidak sedang dalam mode pengaturan tombol.")
        return
    new_config = BUTTON_SETUP_DATA.pop(user_id, [])
    if new_config:
        GLOBAL_BUTTONS_CONFIG = new_config
        preview_markup = create_inline_keyboard(GLOBAL_BUTTONS_CONFIG)
        await update.message.reply_text(
            "✅ Tombol inline penyambutan berhasil diubah!\n\nPratinjau:",
            reply_markup=preview_markup, parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("Tidak ada tombol yang ditambahkan.")
    context.user_data['setting_buttons'] = False

@admin_private_only
async def cancel_set_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Membatalkan proses pengaturan tombol inline."""
    user_id = update.effective_user.id
    if context.user_data.get('setting_buttons'):
        BUTTON_SETUP_DATA.pop(user_id, None)
        context.user_data['setting_buttons'] = False
        await update.message.reply_text("❌ Pengaturan tombol dibatalkan. Konfigurasi lama dipertahankan.")
    else:
        await update.message.reply_text("Anda tidak sedang dalam mode pengaturan tombol.")

@admin_private_only
async def handle_button_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani input teks setelah /setbutton."""
    user_id = update.effective_user.id
    text = update.message.text
    if not context.user_data.get('setting_buttons'): return
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("Format tidak valid. Mohon masukkan minimal dua kata: `Nama Tombol URL`")
        return
    url = parts[-1]
    button_text = " ".join(parts[:-1])
    if not url.startswith(('http://', 'https://', 't.me/')):
        await update.message.reply_text(
            f"❌ Link '{url}' terlihat tidak valid. Pastikan link dimulai dengan `http://`, `https://`, atau `t.me/`.
        )
        return
    BUTTON_SETUP_DATA[user_id].append([button_text, url])
    await update.message.reply_text(
        f"✅ Tombol ditambahkan:\nTeks: {button_text}\nLink: `{url}`\n\nTotal tombol: {len(BUTTON_SETUP_DATA[user_id])}. Lanjutkan atau ketik `/donebutton`.",
        parse_mode='Markdown'
    )

@admin_private_only
async def show_current_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan konfigurasi saat ini."""
    global WELCOME_MESSAGE, GLOBAL_PHOTO_FILE_ID, GLOBAL_BUTTONS_CONFIG, RULES_MESSAGE
    photo_status = f"ID Foto: `{GLOBAL_PHOTO_FILE_ID}`" if GLOBAL_PHOTO_FILE_ID else "Status: TIDAK ADA FOTO DISIAPKAN"
    button_list = "\n".join([f"- {text} -> `{url}`" for text, url in GLOBAL_BUTTONS_CONFIG])
    
    await update.message.reply_text(
        "⚙️ Konfigurasi Bot Saat Ini\n\n"
        "Pesan Penyambutan (Permanen):\n"
        f"```html\n{WELCOME_MESSAGE}\n```\n\n"
        "Pesan Aturan (`/rules`):\n"
        f"```html\n{RULES_MESSAGE}\n```\n\n"
        "Foto Penyambutan:\n"
        f"{photo_status}\n\n"
        "Tombol Inline:\n"
        f"{button_list}",
        parse_mode='Markdown'
    )


# ----------------------------------------------------------------------
## FUNGSI UTAMA UNTUK MENJALANKAN BOT
# ----------------------------------------------------------------------

def main() -> None:
    """Memulai bot."""
    
    if not BOT_TOKEN:
        logger.error("Token BOT tidak ditemukan. Bot gagal dijalankan.")
        return

    try:
        application = Application.builder().token(BOT_TOKEN).build()
    except Exception as e:
        logger.error(f"Gagal membuat aplikasi bot: {e}")
        return

    # --- HANDLER UTILITAS & MODERASI GRUP (Admin Grup) ---
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("pin", pin_message))
    application.add_handler(CommandHandler("mute", mute_user))
    application.add_handler(CommandHandler("unmute", unmute_user))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("vctitle", vctitle))
    application.add_handler(CommandHandler("promote", promote_user))
    application.add_handler(CommandHandler("fullpromote", full_promote_user))
    application.add_handler(CommandHandler("demote", demote_user))
    application.add_handler(CommandHandler("adminlist", adminlist))
    application.add_handler(CommandHandler("reload", reload_config))
    application.add_handler(CommandHandler("anonadmin", anonadmin))
    application.add_handler(CommandHandler("rules", show_rules))
    application.add_handler(CommandHandler("setrules", set_rules))
    
    # --- HANDLER KONFIGURASI (Pemilik Bot Global - PRIVATE CHAT) ---
    application.add_handler(CommandHandler("setphoto", set_photo))
    application.add_handler(CommandHandler("setbutton", start_set_button))
    application.add_handler(CommandHandler("donebutton", done_set_button))
    application.add_handler(CommandHandler("cancelbutton", cancel_set_button))
    application.add_handler(CommandHandler("showconfig", show_current_config))
    
    # Handler pesan teks (input tombol)
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND, handle_button_input
    ))

    # --- HANDLER UTAMA GRUP (Welcome Message) ---
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, lambda u, c: None))

    logger.info("Bot Manager V2 sedang berjalan...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
