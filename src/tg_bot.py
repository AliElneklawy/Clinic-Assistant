import json
import os

from dotenv import load_dotenv
from telegram import Update 
from telegram.ext import (
    filters,
    CommandHandler,
    Application,
    MessageHandler,
    ContextTypes,
)

from agents.query_handler_agent import QueryHandlerAgent
from settings.paths import INDEXES_DIR, MED_DATA_FILE
from settings.logger import get_logger

load_dotenv()
logger = get_logger(__name__)

class TelegramBot:
    def __init__(self):
        self.admins = json.loads(os.getenv("ADMINS"))

        self.agent = QueryHandlerAgent(
            content_path=MED_DATA_FILE,
            index_path=INDEXES_DIR / "index_7ad274e90429ac4.faiss.temp",
        )

        self.application = (
            Application.builder()
            .token(os.getenv("TELEGRAM_BOT_TOKEN"))
            .concurrent_updates(True)
            .build()
        )

        self.register_handlers()

    def register_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("add_content", self.add_content))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Welcome to our clinic. Here is what I can do: \n\n"
            "1. Search the clinic's knowledge base\n"
            "2. Search the web\n"
            "3. List available appointments\n"
            "4. Book an appointment\n"
            "5. Cancel an appointment\n"
            "6. Reschedule an appointment\n"
            "7. Classify a patient's diabetes"
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass

    async def add_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.from_user.id not in self.admins:
            await update.message.reply_text("You are not authorized to add content")
            return
        ...

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.message.text
        user_id = update.message.from_user.id

        response = self.agent.run(query, user_id)
        await update.message.reply_text(response["output"])


    def run(self):
        logger.info("========= Bot is running =========")
        self.application.run_polling()

if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()
