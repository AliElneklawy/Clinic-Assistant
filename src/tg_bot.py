from telegram import Update 
from telegram.ext import (
    filters,
    CommandHandler,
    Application,
    MessageHandler,
    ContextTypes,
)


class TelegramBot:
    def __init__(self):
        pass

    def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        update.message.reply_text(
            "Welcome to our clinic. Here is what I can do: \n\n"
            "1. Search the clinic's knowledge base\n"
            "2. Search the web\n"
            "3. List available appointments\n"
            "4. Book an appointment\n"
            "5. Cancel an appointment\n"
            "6. Reschedule an appointment\n"
            "7. Classify a patient's diabetes"
        )


