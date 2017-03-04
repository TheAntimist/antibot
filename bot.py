import os
import signal
import time
from slackclient import SlackClient
from slackclient._client import SlackNotConnected
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


def getcounterforuser(slack_user):

    val = 0
    try:
        for row in cursor.execute('SELECT start_date FROM counter WHERE userid=? LIMIT 1;',
                                  [slack_user]):
            val = (datetime.utcnow() - row[0]).days
    except Exception as e:
            print("Error resetting counter for: {}, with Exception: {}".format(slack_user, str(e)))
    finally:
        return val


def sendmessage(channel, message):
    """
    Sends a message to the given channel.
    :param channel: Channel to send message to.
    :param message: Message to send.
    """
    return slack_client.api_call("chat.postMessage", channel=channel, text=message, as_user=True)


def bot_help(channel, slack_user, args):
    """
        Sends a reply, with all the current list of commands.
    """
    combined_args = ' '.join(args)
    if len(args) == 0:
        response = helpd["help"]
    elif combined_args not in helpd:
        response = "Command was not found on help."
    else:
        response = helpd[combined_args]
    sendmessage(channel, response)

def do(channel, slack_user, args):
    """

    """
    response = "This does nothing. You aren't supposed to be here."
    sendmessage(channel, response)

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

def up(channel, slack_user, args):
    sendmessage(channel, BOT_NAME + " is up!")

def counter(channel, slack_user, args):
    """
        Handles all the counter related commands.
    """

    if not args:
        return

    if args[0] == 'reset' or args[0] == 'set' or args[0] == 'add':

        def reset_date(channel, slack_user, date=None):
            """
                Resets date for given user, to the date provided or the current date.
            """
            if date is None:
                date = datetime.utcnow()

            try:
                c = cursor.execute('SELECT EXISTS(SELECT 1 FROM counter WHERE userid=? LIMIT 1);',
                                   [slack_user]).fetchone()[0]
                if c:
                    cursor.execute('UPDATE counter SET start_date=? WHERE userid=?', [date, slack_user])
                else:

                    def getuserinfo(slack_user):
                        api_call = slack_client.api_call("users.info", user=slack_user)
                        if api_call.get('ok'):
                            return api_call['user']['name']
                        return ""

                    username = getuserinfo(slack_user)
                    cursor.execute('INSERT INTO counter VALUES (?, ?, ?)', [slack_user, date, username])
                db.commit()
                sendmessage(channel, "Counter has been set to {}".format(date.strftime("%Y-%m-%d")))
            except Exception as e:
                print("Error resetting counter for: {}, with Exception: {}".format(slack_user, str(e)))

        try:
            if args[1:]:
                d = datetime.strptime(args[1], "%Y-%m-%d")
                reset_date(channel, slack_user, d)
            else:
                reset_date(channel, slack_user)
        except Exception as e:
            print("Error while resetting, with exception {}".format(str(e)))
            response = "Couldn't parse Date and time, please, provide it in the format YYYY-mm-dd"
            sendmessage(channel, response)

    elif args[0] == 'show':
        response = "Your counter is at: " + str(getcounterforuser(slack_user))
        sendmessage(channel, response)

    elif args[0] == 'team' or args[0] == 'total':

        def gettotalcounter():
            """
                Retrieves the Counter for the whole team.
            """
            val = 0
            response = ""
            try:
                for username, sdate in cursor.execute('SELECT username, start_date FROM counter;'):
                    days = (datetime.utcnow() - sdate).days
                    response += username + ": " + str(days) + "\n"
                    val += days
            except Exception as e:
                print("Error resetting with Exception: {}".format(str(e)))
            finally:
                return val, response

        value, response = gettotalcounter()
        r = "Total Streak: " + str(value) + "\n"
        if args[0] == 'team':
            r += response
        sendmessage(channel, r)

    elif args[0] == 'remove':

        def remove_user(channel, slack_user, username=None):
            """
                If username given, then specific username is removed from the Counter table,
                else the slack_user is removed.
            """

            try:
                r = "Removed counter for user: "
                if username:
                    c = cursor.execute('DELETE from counter WHERE username=?', [username])
                    r += username

                else:
                    c = cursor.execute('DELETE from counter WHERE userid=?', [slack_user])
                    r += "<@" + slack_user + ">"

                db.commit()
                sendmessage(channel, r)

            except Exception as e:
                print("Error, while deleting with exception: {}".format(str(e)))

        if args[1:]:
            remove_user(channel, slack_user, args[1])
        else:
            remove_user(channel, slack_user)


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
            if output and 'text' in output and output['text'].startswith(AT_BOT):
                # return text after the @ mention, whitespace removed
                cmd = output['text'].replace(":", "").split(AT_BOT)[1].strip().lower()
                cmd = cmd.split()
                return cmd[0], output['channel'], output['user'], cmd[1:]
    return None, None, None, None


def onexit(passed_signal, frame=None, exit_code=None):
    print("In Signal Handler, closing all connections.")
    db.close()
    if passed_signal in [signal.SIGTERM, signal.SIGINT]: # Only exit cleanly is a SIGINT is passed
        exit(0)
    else:
        if exit_code:
            exit(exit_code)
        else:
            exit(exit_code)


helpd = {
    "help": "Gives a list of commands. To find a help on a specific command, use: " +
            "`help command`\nCurrent Command list:" +
            " `help`, `inspire`, `counter`, `add`, `up`",
    "inspire": "Sends a motivational quote, to the channel.\nUsage: `inspire`",
    "counter": "Super class of all counter related commands. Note, uses UTC time. " +
               "Currently we have: `counter reset`, `counter remove`, " +
               "`counter add`, `counter set`, `counter total`, `counter team`, `counter show`",
    "counter total": "Shows the whole teams current counters.\nUsage: `counter total`",
    "counter team": "Shows the whole teams current counters.\nUsage: `counter team`",
    "counter show": "Shows the user's streak.\nUsage: `counter show`",
    "counter reset": "Reset's the user counter, if a _date_ is provided, then to the date, " +
                     "otherwise, to the current date.\nUsage: `counter reset [YYYY-mm-dd]`",
    "counter add": "Similar to `counter reset`, a convenient function for a user." +
                   "\nUsage: `counter add [YYYY-mm-dd]`",
    "counter set": "Similar to `counter reset`, a convenient function for a user." +
                   "\nUsage: `counter set [YYYY-mm-dd]`",
    "counter remove": "Removes the counter for the current user, or for the username " +
                      "specified.\nUsage: `counter remove [username]`",
    "up": "Responds with a message, stating if online, otherwise, there is no response.\nUsage: `up`",
    "add": "Takes any number of args, and gives the sum.\nUsage: `add arg1 arg2 arg3 ...`"
}


commands = {
    "do": do,
    "inspire": inspire,
    "help": bot_help,
    "counter": counter,
    "add": add,
    "up": up
}

signal.signal(signal.SIGTERM, onexit)
signal.signal(signal.SIGINT, onexit)

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
            raise ConnectionError("Connect Failed.")

    except (ConnectionError, TimeoutError, SlackNotConnected) as e:
        print("Caught Exception: {}. Shutting down.".format(str(e)))
        onexit(signal.SIGKILL, exit_code=23)
    except Exception as e:
        print("Caught Exception: {}. Shutting down.".format(str(e)))
        onexit(signal.SIGKILL)
