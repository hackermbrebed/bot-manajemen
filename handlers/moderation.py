# handlers/moderation.py

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from handlers.core import logger, is_group_admin
from datetime import timedelta

# --- PERINTAH ADMINISTRATIF GRUP ---

async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menyematkan (pin) pesan yang dibalas."""
    if not await is_group_admin(update, context): return

    if not update.message.reply_to_message:
        await update.message.reply_text("Mohon balas pesan yang ingin di-pin.")
        return

    try:
        await context.bot.pin_chat_message(
            chat_id=update.effective_chat.id,
            message_id=update.message.reply_to_message.message_id,
            disable_notification=True # Pin tanpa notifikasi berisik
        )
        await update.message.reply_text("✅ Pesan berhasil di-pin.")
        
    except Exception as e:
        logger.error(f"Gagal pin pesan: {e}")
        await update.message.reply_text("❌ Gagal pin pesan. Pastikan bot adalah Admin dan memiliki izin **'Pin Messages'**.")

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
            chat_id=update.effective_chat.id,
            user_id=target_user.id,
            # Memberi izin default (bisa mengirim pesan, media, dll.)
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
        )
        await update.message.reply_text(f"✅ Pengguna **{target_user.full_name}** telah di-unmute.", parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Gagal unmute user: {e}")
        await update.message.reply_text("❌ Gagal unmute. Pastikan bot memiliki izin **'Restrict Members'**.")


async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Membatasi (mute) pengguna yang dibalas (default: 1 jam)."""
    if not await is_group_admin(update, context): return
    
    target_msg = update.message.reply_to_message
    if not target_msg:
        await update.message.reply_text("Mohon balas pesan pengguna yang ingin di-mute.")
        return
        
    target_user = target_msg.from_user
    # Mute selama 1 jam (timedelta default)
    until_date = update.message.date + timedelta(hours=1)
    
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target_user.id,
            until_date=until_date,
            can_send_messages=False, # Hapus izin mengirim pesan
        )
        await update.message.reply_text(f"✅ Pengguna **{target_user.full_name}** telah di-mute selama 1 jam.", parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Gagal mute user: {e}")
        await update.message.reply_text("❌ Gagal mute. Pastikan bot memiliki izin **'Restrict Members'**.")

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
            chat_id=update.effective_chat.id,
            user_id=target_user.id
        )
        await update.message.reply_text(f"✅ Pengguna **{target_user.full_name}** telah diban dari grup secara permanen.", parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Gagal ban user: {e}")
        await update.message.reply_text("❌ Gagal ban. Pastikan bot memiliki izin **'Ban Users'** dan wewenang yang lebih tinggi dari target.")

# --- DAFTAR HANDLER MODERASI ---

moderation_handlers = [
    CommandHandler("pin", pin_message),
    CommandHandler("mute", mute_user),
    CommandHandler("unmute", unmute_user),
    CommandHandler("ban", ban_user),
]
