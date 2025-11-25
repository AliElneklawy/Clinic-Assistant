import json
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from agents.query_handler_agent import QueryHandlerAgent
from settings.logger import get_logger

load_dotenv()
logger = get_logger(__name__)


class TelegramBot:
    def __init__(self):
        self.admins = json.loads(os.getenv("ADMINS"))

        self.agent = QueryHandlerAgent()

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
            "   1. Search the clinic's knowledge base\n"
            "   2. Search the web\n"
            "   3. List available appointments\n"
            "   4. Book an appointment\n"
            "   5. Cancel an appointment\n"
            "   6. Reschedule an appointment\n"
            "   7. Classify a patient's diabetes"
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = (
            "👋 <b>Welcome! Here's how I can help you:</b>\n\n"
            "🩺 <b>To book an appointment</b>, please provide:\n"
            "• Full Name\n"
            "• Age\n"
            "• Email Address\n"
            "• Reason for the visit\n"
            "• Preferred Date & Time\n\n"
            "❌ <b>To cancel an appointment</b>, please provide:\n"
            "• Your Appointment (Event) ID\n\n"
            "🧪 <b>To classify diabetes risk</b>, please provide:\n"
            "• Age\n"
            "• Gender (Male / Female)\n"
            "• Smoking History (never / no_info / former / current / not_current / ever)\n"
            "• Hypertension History (yes / no)\n"
            "• Heart Disease History (yes / no)\n"
            "• BMI (Body Mass Index)\n"
            "• HbA1c Level\n"
            "• Blood Glucose Level\n\n"
            "💬 Just type the information, and I’ll guide you from there!"
        )

        await update.message.reply_text(message, parse_mode=ParseMode.HTML)

    async def add_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.from_user.id not in self.admins:
            await update.message.reply_text("You are not authorized to add content")
            return

        args: list = context.args
        content: str = " ".join(args)

        msg = await update.message.reply_text(
            "Please wait while I add the new content to my knowledge base..."
        )

        self.agent.rag.update_vectorstore(content)
        await msg.edit_text("Content added successfully")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.message.text
        user_id = update.message.from_user.id

        await update.message.chat.send_action("typing")

        response = self.agent.run(query, user_id)
        await update.message.reply_text(response["output"])

    def run(self):
        logger.info("========= Bot is running =========")
        self.application.run_polling()


if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()


# TODO:
# 🏥 1. Patient & Appointment Management

# View My Appointments – Let patients list their upcoming bookings.
# → e.g., /my_appointments
# Reminders / Notifications – Schedule automatic reminders before appointments using JobQueue.
# Reschedule Flow – Implement a guided conversation to change date/time easily.
# Confirmations – Send confirmation messages (and maybe email) after booking/canceling.

# ⚕️ 3. Medical Assistant Features

# Expand beyond diabetes:
# Symptom Checker – Collect symptoms and suggest possible conditions.
# Medication Reminders – Allow users to set reminders for their meds.
# Vitals Tracker – Log and visualize user vitals (blood sugar, pressure, etc.) over time.
# Health Tips – Send daily/weekly medical tips from a curated dataset or RAG index.

# 🧠 4. AI / Data Features

# Summarization – Summarize long medical documents or discharge summaries.
# Voice Input / Output – Add speech-to-text and text-to-speech support for accessibility.
# Image Analysis – Let users upload reports (e.g., blood tests) and summarize results.

# 👩‍💼 5. Admin Tools

# Admin Dashboard – View bookings, delete or confirm them.
# Usage Logs / Analytics – Track number of interactions, most common queries, etc.
# Backup and Restore – Save and restore the FAISS index and knowledge base.

# 🔒 6. Security & Compliance

# For real-world use, this is critical:
# Patient Verification – OTP/email confirmation before booking.

# ☁️ 7. Integration Ideas

# Email / SMS Notifications – Send confirmations via external channels.

# 🧩 8. Fun or Helpful Extras

# Health Quiz or Tips of the Day – “Did you know?” facts or simple wellness quizzes.
# Feedback System – “How was your visit today?” to collect ratings.
# Emergency Contact Shortcut – Quick access to emergency numbers.
# Location Sharing – Let users send location to find the nearest clinic branch.
