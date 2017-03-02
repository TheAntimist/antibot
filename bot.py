import os
import time
from slackclient import SlackClient
import sqlite3
from datetime import datetime
from brainyquote import pybrainyquote

# starterbot's ID as an environment variable
BOT_ID = os.environ.get("BOT_ID")

# constants
AT_BOT = "<@" + BOT_ID + ">"
BOT_NAME = 'antibot'


# instantiate Slack client
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

# Database Variables
db = None
cursor = None

def getuserinfo(slack_user):
    api_call = slack_client.api_call("users.info", user=slack_user)
    if api_call.get('ok'):
        return api_call['user']['name']
    return ""

def resetDate(channel, slack_user, date=None):
    if date is None:
        date = datetime.now()

    try:
        c = cursor.execute('SELECT EXISTS(SELECT 1 FROM counter WHERE userid=? LIMIT 1);',
                           [slack_user]).fetchone()[0]
        if c:
            cursor.execute('UPDATE counter SET start_date=? WHERE userid=?', [date, slack_user])
        else:
            username = getuserinfo(slack_user)
            cursor.execute('INSERT INTO counter VALUES (?, ?, ?)', [slack_user, date, username])
        db.commit()
        sendmessage(channel, "Counter has been reset to {}".format(date.strftime("%Y-%m-%d")))
    except:
        print("Error resetting counter for: {}".format(slack_user))

def getcounterforuser(slack_user):

    val = 0
    try:
        for row in cursor.execute('SELECT start_date FROM counter WHERE userid=? LIMIT 1;', [slack_user]):
            val = (datetime.now() - row[0]).days
    except:
        print("Error getting counter for: {}".format(slack_user))
    finally:
        return val

def gettotalcounter():
    """
    """
    val = 0
    response = ""
    try:
        for userid, sdate in cursor.execute('SELECT userid, start_date FROM counter;'):
            days = (datetime.now() - sdate).days
            response += getuserinfo(userid) + ": " + str(days) + "\n"
            val += days
    except:
        print("Error getting counter for: {}".format(slack_user))
    finally:
        return val, response

def sendmessage(channel, message):
    return slack_client.api_call("chat.postMessage", channel=channel, text=message, as_user=True)

def bot_help(channel, slack_user, args):
    """
        Sends a reply, with all the current list of commands.
    """
    response = """
    *help*: Gives a list of commands. This is the command you are running.\n
    *inspire*: Sends a motivational quote, to the channel.\n
    *counter reset*: Reset's the user counter, if a _date_ is provided, then to the date, otherwise, to the current date.
    Date Format: YYYY-dd-mm\n
    *counter total* or *counter team*: Shows the whole teams current counters.\n
    *counter show*: Shows the user's streak.\n
    *add*: Takes any number of args, and gives the sum.
    """
    sendmessage(channel, response)

def do(channel, slack_user, args):
    """

    """
def inspire(channel, slack_user, args):
    """
        Sends an inspirational message to the channel. Note, use pybrainyquote
    """
    quote = pybrainyquote.get_quotes('motivational')[0]
    sendmessage(channel, quote)



def add(channel, slack_user, args):
    sum = 0
    for i in args:
        sum += int(i)
    response = "Sum: " + str(sum)
    sendmessage(channel, response)

def counter(channel, slack_user, args):
    """
        Handles all the counter related commands.
    """

    if args[0] == 'reset':
        try:
            if len(args[1:]) != 0:
                d = datetime.strptime(args[1], "%Y-%m-%d")
                resetDate(channel, slack_user, d)
            else:
                resetDate(channel, slack_user)
        except:
            response = "Couldn't parse Date and time, please, provide it in the format YYYY-mm-dd"
            sendmessage(channel, response)
    elif args[0] == 'show':
        response = "Counter at: " + str(getcounterforuser(slack_user))
        sendmessage(channel, response)
    elif args[0] == 'team' or args[0] == 'total':
        value, response = gettotalcounter()
        r = "Total Streak: " + str(value) + "\n"
        r += response
        sendmessage(channel, r)

    elif args[0] == 'set' | args[0] == 'add':
        try:
            d = datetime.strptime(args[1], "%Y-%m-%d")
            resetDate(channel, slack_user, d)
        except:
            response = "Couldn't parse Date and time, please, provide it in the format YYYY-mm-dd"
            sendmessage(channel, response)


def handle_command(cmd, channel, slack_user, args):
    """
        Receives commands directed at the bot and determines if they
        are valid commands. If so, then acts on the commands. If not,
        returns back what it needs for clarification.
    """
    if cmd in commands:
        commands[cmd](channel, slack_user, args)
    else:
        response = "Unknown command. Use the *help* command, to give a list of commands."
        sendmessage(channel, response)

def parse_slack_output(slack_rtm_output):
    """
        The Slack Real Time Messaging API is an events firehose.
        this parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and AT_BOT in output['text']:
                # return text after the @ mention, whitespace removed
                cmd = output['text'].split(AT_BOT)[1].strip().lower()
                cmd = cmd.split()
                return cmd[0], \
                       output['channel'], output['user'], cmd[1:]
    return None, None, None, None

commands = {
    "do": do,
    "inspire": inspire,
    "help": bot_help,
    "counter": counter,
    "add": add
}

try:
    if not os.path.exists("counter.db"):
        db = sqlite3.connect('counter.db', detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = db.cursor()
        cursor.execute('create table counter (userid text primary key, start_date timestamp, username text)')
        db.commit()
    else:
        db = sqlite3.connect('counter.db', detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = db.cursor()
except:
    print("Error opening datebase")
    exit(1)

if __name__ == "__main__":
    try:
        READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
        if slack_client.rtm_connect():
            print("{} connected and running!".format(BOT_NAME))
            while True:
                command, channel, slack_user, slack_args = parse_slack_output(slack_client.rtm_read())
                if command and channel and slack_user:
                    handle_command(command, channel, slack_user, slack_args)
                time.sleep(READ_WEBSOCKET_DELAY)
        else:
            print("Connection failed. Invalid Slack token or bot ID?")
    except (KeyboardInterrupt, SystemExit):
        db.close()