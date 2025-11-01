import datetime

# Working Hours
WORK_START_HOUR = 9
WORK_END_HOUR = 16  # 4 PM

# Appointment Settings
SLOT_DURATION_MINUTES = 30

# Calendar Settings
CALENDAR_ID = "primary"

# Schedule Settings
SKIP_WEEKENDS = True
DAYS_TO_SHOW = 5 # Show 5 days from now

# Lunch Break (optional)
LUNCH_BREAK_START = datetime.time(12, 0)  # 12:00 PM
LUNCH_BREAK_END = datetime.time(13, 0)    # 1:00 PM
ENABLE_LUNCH_BREAK = False

# Timezone
CLINIC_TIMEZONE = "Africa/Cairo"

# Buffer time between appointments (minutes)
BUFFER_TIME_MINUTES = 10

# Maximum appointments per day (0 = unlimited)
MAX_APPOINTMENTS_PER_DAY = 0