from datetime import timedelta
from enum import Enum
import sys 
from pathlib import Path

from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts import get_api_key
from services.database.database_service import DatabaseOpsService
from settings.logger import get_logger
from settings.paths import EMAIL_TEMPLATES_DIR
from utils.scheduler import Scheduler

logger = get_logger(__name__)


class EmailTemplate(Enum):
    TXT = "appointment_confirmation.txt"
    HTML = "appointment_confirmation.html"


class EmailService(Scheduler):

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 465

    def __init__(self, sender_email: str, app_password: str, db: DatabaseOpsService):
        """
        Initialize the EmailService with sender email and app password.
        Args:
            sender_email (str): The sender's email address.
            app_password (str): The application-specific password for SMTP authentication.
        """
        super().__init__()
        self.sender_email = sender_email
        self.app_password = app_password
        self.db = db
        self._server = None

    def _load_template(self, filename: str) -> str:
        """
        Load an email template from a file.
        Args:
            filename (str): The name of the template file to load.
        Returns:
            str: The content of the template file.
        Raises:
            FileNotFoundError: If the template file does not exist.
            Exception: For other errors during file reading.
        """
        template_path = EMAIL_TEMPLATES_DIR / filename
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                content = f.read()
                return content
        except FileNotFoundError:
            logger.error(f"ERROR: Template file not found: {template_path}")
            raise
        except Exception as e:
            logger.error(f"ERROR loading template: {e}")
            raise

    def _get_connection(self):
        """
        Establish and return an SMTP SSL connection if not already connected.
        Returns:
            smtplib.SMTP_SSL: The SMTP server connection.
        """
        if self._server is None:
            self._server = smtplib.SMTP_SSL(self.SMTP_HOST, self.SMTP_PORT)
            self._server.login(self.sender_email, self.app_password)
        return self._server

    def _close_connection(self):
        """Close the SMTP connection if it exists."""
        if self._server is not None:
            try:
                self._server.quit()
            except Exception as e:
                logger.error(f"Error closing SMTP connection: {e}")
            finally:
                self._server = None

    def _load_preprocess_templates(
        self,
        patient_name: str,
        formatted_date: str,
        formatted_time: str,
        doctor_name: str,
        clinic_name: str,
        clinic_address: str,
        clinic_phone: str,
    ):
        """
        Load and preprocess both text and HTML email templates with appointment details.
        Args:
            patient_name (str): Name of the patient.
            formatted_date (str): Appointment date (formatted).
            formatted_time (str): Appointment time (formatted).
            doctor_name (str): Name of the doctor.
            clinic_name (str): Name of the clinic.
            clinic_address (str): Address of the clinic.
            clinic_phone (str): Phone number of the clinic.
        Returns:
            tuple: (text_body, html_body) with placeholders replaced, or False on error.
        """
        try:
            text_body = self._load_template(EmailTemplate.TXT.value)
            html_body = self._load_template(EmailTemplate.HTML.value)
        except Exception as e:
            logger.error(f"ERROR: Could not load templates: {e}")
            return False

        replacements = {
            "{patient_name}": patient_name,
            "{formatted_date}": formatted_date,
            "{formatted_time}": formatted_time,
            "{doctor_name}": doctor_name,
            "{clinic_name}": clinic_name,
            "{clinic_address}": clinic_address if clinic_address else "",
            "{clinic_phone}": clinic_phone if clinic_phone else "",
        }

        for placeholder, value in replacements.items():
            text_body = text_body.replace(placeholder, value)
            html_body = html_body.replace(placeholder, value)

        logger.info("Templates processed successfully")
        return text_body, html_body

    def _construct_message(
        self, formatted_time: str, receiver_email: str, text_body: str, html_body: str
    ):
        """
        Construct a multipart email message with both plain text and HTML content.
        Args:
            formatted_time (str): Appointment time (formatted).
            receiver_email (str): Recipient's email address.
            text_body (str): Plain text email body.
            html_body (str): HTML email body.
        Returns:
            MIMEMultipart: The constructed email message.
        """
        message: MIMEMultipart = MIMEMultipart("alternative")
        message["Subject"] = f"Reminder: Your Appointment Today at {formatted_time}"
        message["From"] = self.sender_email
        message["To"] = receiver_email

        part1 = MIMEText(text_body, "plain")
        part2 = MIMEText(html_body, "html")

        message.attach(part1)
        message.attach(part2)

        logger.info("Message constructed successfully")
        return message

    def send_appointment_confirmation(
        self,
        receiver_email: str,
        patient_name: str,
        appointment_time: str,
        doctor_name: str = "Dr. Smith",
        clinic_name: str = "Healthcare Clinic",
        clinic_address: str = "",
        clinic_phone: str = "",
    ):
        """
        Send an appointment confirmation email to the specified recipient.
        Args:
            receiver_email (str): Recipient's email address.
            patient_name (str): Name of the patient.
            appointment_time (str): Appointment time in ISO format.
            doctor_name (str, optional): Name of the doctor. Defaults to "Dr. Smith".
            clinic_name (str, optional): Name of the clinic. Defaults to "Healthcare Clinic".
            clinic_address (str, optional): Address of the clinic. Defaults to empty string.
            clinic_phone (str, optional): Phone number of the clinic. Defaults to empty string.
        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        if not receiver_email:
            logger.error("ERROR: No receiver email provided")
            return False

        appointment_time = datetime.fromisoformat(appointment_time)
        formatted_date = appointment_time.strftime("%A, %B %d, %Y")
        formatted_time = appointment_time.strftime("%I:%M %p")

        text_body, html_body = self._load_preprocess_templates(
            patient_name,
            formatted_date,
            formatted_time,
            doctor_name,
            clinic_name,
            clinic_address,
            clinic_phone,
        )
        message: MIMEMultipart = self._construct_message(
            formatted_time, receiver_email, text_body, html_body
        )

        try:
            server = self._get_connection()
            server.sendmail(self.sender_email, receiver_email, message.as_string())
            logger.info(f"Email sent successfully to {receiver_email}")
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"AUTHENTICATION ERROR: {e}")
            logger.error("Check your email and app password!")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP ERROR: {e}")
            return False
        except Exception as e:
            logger.error(f"UNEXPECTED ERROR: {e}")
            return False

    def run(self):
        logger.info("Running email service scheduled task...")
        
        appointments = self.db.get_appointments()
        for (
            _,
            _,
            event_id,
            patient_name,
            _,
            patient_email,
            date_time,
            _,
            status,
            _,
            email_sent,
        ) in appointments:

            if email_sent:
                continue

            if status != "cancelled" and \
                datetime.fromisoformat(date_time) - datetime.now() < timedelta(hours=4):

                self.send_appointment_confirmation(patient_email, patient_name, date_time)

                self.db.update_field(
                    table_name="appointments",
                    field_name="email_sent",
                    value=True,
                    condition=f"event_id = '{event_id}'",
                )

    def stop(self):
        """Stop the scheduler and close SMTP connection."""
        super().stop()
        self._close_connection()

if __name__ == "__main__":
    from datetime import timedelta
    import threading

    db = DatabaseOpsService()
    email_service = EmailService(
        sender_email=get_api_key.get_key("SENDER_EMAIL"),
        app_password=get_api_key.get_key("GMAIL_APP_PASSWORD"),
        db=db,
    )

    logger.info("Starting email service in background mode...")
    email_service.start()

    try:
        logger.info("Email service is running. Press Ctrl+C to stop.")
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        logger.info("\nShutting down email service...")
        email_service.stop()
        logger.info("Email service stopped.")
