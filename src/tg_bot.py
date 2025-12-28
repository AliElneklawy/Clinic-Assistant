import json
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from agents.query_handler_agent import QueryHandlerAgent
from scripts import get_api_key

# from services.calendar.calendar_service import CalendarService
from services.database.database_service import DatabaseOpsService
from services.email.email_service import EmailService
from settings.logger import get_logger

load_dotenv()
logger = get_logger(__name__)


class TelegramBot:
    def __init__(
        self, agent: QueryHandlerAgent, db: DatabaseOpsService, email: EmailService
    ):
        self.admins = json.loads(os.getenv("ADMINS"))

        self.agent = agent
        self.db = db
        self.email = email

        self.application = (
            Application.builder()
            .token(os.getenv("TELEGRAM_BOT_TOKEN"))
            .concurrent_updates(True)
            .build()
        )

        self.register_handlers()
        self.register_jobs()

    def register_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("add_content", self.add_content))
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

    def register_jobs(self):
        self.application.job_queue.run_repeating(self.send_medical_fact, interval=3600)
        self.application.job_queue.run_repeating(self.confirm_appointment, interval=1800)

    @staticmethod
    def create_keyboard(texts: list[str], callback_data: list[str]):
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(text=text, callback_data=callback_data)
                    for text, callback_data in zip(texts, callback_data)
                ]
            ]
        )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        response, event_id = query.data.split(":")

        if response == "user_confirmed":
            self.db.update_field(
                table_name="appointments",
                field_name="status",
                value="confirmed",
                condition=f"event_id = '{event_id}'",
            )
            await query.edit_message_text("✅ Appointment confirmed. See you there!")
        elif response == "user_cancelled":
            self.agent.agent_tools.cancel_appointment(event_id)
            await query.edit_message_text("❌ Appointment cancelled.")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        chat_id = update.message.chat.id

        if not self.db.get_bot_subscribers(user_id):  # If the user is not subscribed
            self.db.insert_bot_subscriber(user_id=user_id, chat_id=chat_id)

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

    async def send_medical_fact(self, context: ContextTypes.DEFAULT_TYPE):
        """Send a medical fact to bot subscribers"""
        fact = self.db.get_medical_fact()
        users = self.db.get_bot_subscribers(get_all=True)

        for _, _, chat_id, _, last_fact_sent in users:
            if datetime.fromisoformat(last_fact_sent) < datetime.now() - timedelta(
                days=1
            ):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"💡 <b>Daily Health Tip:</b>\n\n{fact}",
                    parse_mode=ParseMode.HTML,
                )

                self.db.update_field(
                    table_name="bot_subscribers",
                    field_name="last_fact",
                    value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    condition=f"chat_id = '{chat_id}'",
                )

    async def confirm_appointment(self, context: ContextTypes.DEFAULT_TYPE):
        appointments = self.db.get_appointments()
        for (
            _,
            user_id,
            event_id,
            patient_name,
            _,
            patient_email,
            date_time,
            _,
            status,
            confirmation_sent,
            email_sent,
        ) in appointments:
            if confirmation_sent and email_sent:
                logger.info(f"Appointment {event_id} already confirmed and emailed")
                continue

            if status == "scheduled" and datetime.fromisoformat(
                date_time
            ) - datetime.now() < timedelta(hours=24):
                logger.info(f"Sending confirmation message for appointment {event_id}")

                keyboard = self.create_keyboard(
                    texts=["✅ I'm coming", "❌ Sorry, I'll cancel"],
                    callback_data=[
                        f"user_confirmed:{event_id}",
                        f"user_cancelled:{event_id}",
                    ],
                )

                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"⏰ <b>Appointment Reminder</b>\n\n"
                        f"You have an upcoming appointment on <b>{date_time}</b>\n"
                        f"Event ID: <code>{event_id}</code>\n\n"
                        f"Please confirm or cancel:"
                    ),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML,
                )

                self.db.update_field(
                    table_name="appointments",
                    field_name="confirmation_sent",
                    value=True,
                    condition=f"event_id = '{event_id}'",
                )

            elif status == "confirmed" and datetime.fromisoformat(
                date_time
            ) - datetime.now() < timedelta(hours=4):
                # Send confirmation email 4 hours before the appointment
                logger.info(f"Sending confirmation email to {patient_email}")
                self.email.send_appointment_confirmation(
                    patient_email, patient_name, date_time
                )

                self.db.update_field(
                    table_name="appointments",
                    field_name="email_sent",
                    value=True,
                    condition=f"event_id = '{event_id}'",
                )

    def run(self):
        logger.info("========= Bot is running =========")
        self.application.run_polling()


if __name__ == "__main__":
    agent = QueryHandlerAgent()
    db = DatabaseOpsService()
    email = EmailService(
        sender_email=get_api_key.get_key("SENDER_EMAIL"),
        app_password=get_api_key.get_key("GMAIL_APP_PASSWORD"),
    )
    bot = TelegramBot(agent, db, email)

    bot.run()


# TODO:
# 🏥 1. Patient & Appointment Management

# View My Appointments – Let patients list their upcoming bookings.
# → e.g., /my_appointments
# [DONE] Reminders / Notifications – Schedule automatic reminders before appointments using JobQueue.
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
