import os
from datetime import timedelta

# starterbot's ID as an environment variable
BOT_ID = os.environ.get("BOT_ID")
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')

# constants
AT_BOT = "<@" + BOT_ID + ">"
BOT_NAME = 'antibot'
DEFAULT_DELETE_DELAY = 20.0 # Default is 180 seconds
DB_NAME = "counter.db"

# Skirmish Constants
CHECKIN_FREQ_DAYS = 7 # Number of days between check-ins
RELAPSE_POINTS = -5
PER_DAY_POINTS = 1
BUFFER_DAYS_TEAM = timedelta(days=7)
SKIRMISH_NOADMIN_FUNCTIONS = ["players", "details"]