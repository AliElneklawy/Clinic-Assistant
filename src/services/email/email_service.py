import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from scripts import get_api_key
from settings.logger import get_logger
from settings.paths import EMAIL_TEMPLATES_DIR

logger = get_logger(__name__)


class EmailService:
    def __init__(self, sender_email: str, app_password: str):
        self.sender_email = sender_email
        self.app_password = app_password
        self._server = None
        # self.templates_dir = Path(__file__).parent / "templates"

    def _load_template(self, filename: str) -> str:
        """Load email template from file"""
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
        if self._server is None:
            self._server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
            self._server.login(self.sender_email, self.app_password)
        return self._server

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
        try:
            text_body = self._load_template("appointment_confirmation.txt")
            html_body = self._load_template("appointment_confirmation.html")
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


if __name__ == "__main__":
    from datetime import timedelta

    email = EmailService(
        sender_email=get_api_key.get_key("SENDER_EMAIL"),
        app_password=get_api_key.get_key("GMAIL_APP_PASSWORD"),
    )

    appointment_time = datetime.now() + timedelta(hours=4)

    result = email.send_appointment_confirmation(
        receiver_email="ali.mostafa.elneklawy@gmail.com",
        patient_name="John Doe",
        appointment_time=appointment_time,
        doctor_name="Dr. Sarah Johnson",
        clinic_name="City Health Clinic",
        clinic_address="123 Main Street, Suite 200, City, State 12345",
        clinic_phone="(555) 123-4567",
    )

    logger.info(f"\nFinal result: {'SUCCESS' if result else 'FAILED'}")
