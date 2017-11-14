from slackclient import SlackClient
from constants import SLACK_BOT_TOKEN, DB_NAME
import os
import sqlite3

# instantiate Slack client
slack_client = SlackClient(SLACK_BOT_TOKEN)

# Database Variables
db = None
cursor = None

def init():
    global slack_client
    global db
    global cursor
    try:
        if not os.path.exists(DB_NAME):
            db = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
            cursor = db.cursor()
            cursor.execute('''CREATE TABLE counter (userid TEXT PRIMARY KEY, start_date date, username TEXT UNIQUE,
                           admin INTEGER DEFAULT 0)''')
            cursor.execute('''CREATE TABLE sk_details (id INTEGER PRIMARY KEY AUTOINCREMENT, start_date date, 
                           end_date date)''')
            cursor.execute('''CREATE TABLE teams(name TEXT PRIMARY KEY, sk_id INTEGER, FOREIGN KEY (sk_id) 
                           REFERENCES sk_details(id) ON DELETE SET NULL)''')
            cursor.execute('''CREATE TABLE sk_pinfo (username TEXT PRIMARY KEY, team TEXT, relapses INTEGER DEFAULT 0,
                           checkin_date date, FOREIGN KEY (username) REFERENCES counter(username), FOREIGN KEY
                           (team) REFERENCES teams(name) ON DELETE SET NULL )''')
            cursor.execute("PRAGMA foreign_keys=ON")
            db.commit()
        else:
            db = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
            cursor = db.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
    except:
        print("Error opening database")
        exit(1)

def onexit():
    cursor.close()
    db.close()