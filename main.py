# main.py

import logging
from telegram.ext import Application
# Impor konfigurasi dan logger
from handlers.core import BOT_TOKEN, ADMIN_USER_ID_STR, logger
# Impor semua handler/modul
from handlers.welcome import welcome_handlers
from handlers.moderation import moderation_handlers

# Konfigurasi logging (diulang untuk memastikan)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

def main() -> None:
    """Memulai bot dan memuat handlers dari semua modul."""
    
    if not BOT_TOKEN:
        logger.error("Token BOT tidak ditemukan. Bot gagal dijalankan.")
        return
    
    try:
        application = Application.builder().token(BOT_TOKEN).read_timeout(30).write_timeout(30).build()
    except Exception as e:
        logger.error(f"Gagal membuat aplikasi bot: {e}")
        return

    # --- MEMUAT HANDLERS/PLUGINS ---
    
    # Memuat Handler Welcome
    for handler in welcome_handlers:
        application.add_handler(handler)
        
    # Memuat Handler Moderasi
    for handler in moderation_handlers:
        application.add_handler(handler)

    logger.info("Bot Manager sedang berjalan...")
    application.run_polling()


if __name__ == '__main__':
    main()
