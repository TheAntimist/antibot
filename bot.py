import signal
import time
from constants import *
from functions import *
import globals as g

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

### Functions for parsing the commands

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
                cmd = output['text'].replace(":", "").split(AT_BOT)[1].strip() #.lower()
                cmd = cmd.split()
                if cmd:
                    return cmd[0].lower(), output['channel'], output['user'], cmd[1:]

    return None, None, None, None


# Main Code begins


def onexit(passed_signal, frame=None, exit_code=1):
    print("In Signal Handler, closing all connections.")
    g.onexit()
    if passed_signal in [signal.SIGTERM, signal.SIGINT]:
        # Only exit cleanly if a SIGINT, SIGTERM is passed
        exit(0)
    else:
        exit(exit_code)


helpd = {
    "help": "Gives a list of commands. To find a help on a specific command, use: " +
            "`help command`\nCurrent Command list:" +
            " `help`, `inspire`, `counter`, `add`, `up`",
    "inspire": "Sends a motivational quote, to the channel.\nUsage: `inspire`",
    "counter": "Super class of all counter related commands. Note, uses UTC time. " +
               "If no command provided, then is `show` by default. Currently we have: " +
               "`counter reset`, `counter remove`, " +
               "`counter add`, `counter set`, `counter total`, `counter team`, `counter show`",
    "counter total": "Shows the whole teams current counters.\nUsage: `counter total`",
    "counter team": "Shows the whole teams current counters.\nUsage: `counter team`",
    "counter show": "Shows the user's streak.\nUsage: `counter show`",
    "counter reset": "Reset's the user counter, if a _date_ is provided, then to the date, "
                     "otherwise, to the current date. If an `ignore` or `ign` is provided, after "
                     "the date, then if a skirmish is currently running, it ignore the reset as an "
                     "indicator for relapse \nUsage: `counter reset [YYYY-mm-dd] [ignore | ign]`",
    "counter add": "Same as `counter reset`, a convenient function for a user." +
                   "\nUsage: `counter add [YYYY-mm-dd]`",
    "counter set": "Same as `counter reset`, a convenient function for a user." +
                   "\nUsage: `counter set [YYYY-mm-dd]`",
    "counter remove": "Removes the counter for the current user, or for the username " +
                      "specified.\nUsage: `counter remove [username]`",
    "up": "Responds with a message, stating if online, otherwise, there is no response.\nUsage: `up`",
    "add": "Takes any number of args, and gives the sum.\nUsage: `add arg1 arg2 arg3 ...`",
    "rank": "Returns the rank and the title of the user.\nUsage: `rank`",
    "update_admins": "Updates the internal list of admins, based on the slack channel admin list\nUsage: `update_admins`",
    "ua": "Updates the internal list of admins, based on the slack channel admin list\nUsage: `ua`",
    "sk": "Same as skirmish, just shorter to type. Use the same skirmish commands from there.",
    "skirmish": "Super class of all skirmish commands, if no args then displays the current skirmish details."
                "\nNote: Requires you to be an admin, to execute any of these commands."
                "\nCurrent command list: `skirmish details`, `skirmish add`, `skirmish start`, "
                "`skirmish end`, `skirmish remove`, `skirmish players`, `skirmish team`",
    "skirmish details": "Default command, displays the current skirmish details, if one is present.",
    "skirmish add": "Used to add players to the skirmish. Can add multiple users in one command."
                    "\nUsage: `skirmish add @Username User... `"
                    "\nExample: `" + AT_BOT + " skirmish add @antimist @antibot @heartignited`",
    "skirmish remove": "Used to remove players from the skirmish.\n"
                       "Usage: `skirmish remove @username username ...`\n"
                       "Example: `" + AT_BOT + " skirmish remove @antimist @antibot @heartignited`",
    "skirmish start": "Used to start the skirmish. If one is already present, that must removed before "
                      "starting a new one.\n"
                      "Usage: `skirmish start [START-DATE] [END-DATE]`, dates are in the `YYYY-mm-dd` format.",
    "skirmish end": "Used to end the skirmish.\nNote: This deletes all skirmish related data, "
                    "beware of what you are do with this command."
                    "\nUsage: `skirmish end`",
    "skirmish players": "Shows the current list of users in the skirmish.\nUsage: `skirmish players`",
    "skirmish team": "Used to list, add and remove teams. If no args are given, then it will show the "
                     "current list of teams. This is different from the `team` command.\nCare should be taken that all team commands are "
                     "case-sensitive. Thus, _'One'_ and _'one'_ is different.\n"
                     "Contains multiple sub commands, specifically: `skirmish team add`, `skirmish team remove`"
                     "`skirmish team list`",
    "skirmish team add": "Used to add teams if they aren't already present to the skirmish.\n"
                         "Usage: `skirmish team add TEAM-NAME`\n"
                         "Note: Team Name, cannot have any spaces in it. For example, 'Viking Warriors' is not"
                         "allowed, but 'Viking-Warriors' is.",
    "skirmish team remove": "Used to remove teams from the skirmish. Note, all members who were a part of the "
                            "team, will not be assigned any team. They'll have to manually assigned any other team"
                            "using the `@antibot team add` command.\nAlso, if the team name was _One_, then you should"
                            "specify only, _One_ and not anything like _one_ or _ONE_"
                            "Usage: `skirmish team remove TEAM-NAME`",
    "team": "Used to manage all aspects of the teams. Can only be used, when there is a skirmish planned. "
            "By default it shows the list of teams. Commands are: `team list`, `team players`, "
            "`team add`, `team remove`, `team score`",
    "teams": "Same the team command, look at the other commands from there.",
    "team players": "Gives a list of teams and the players associated with them.\nUsage: `team players`",
    "team add": "Used to add players to the teams.\nUsage: `team add @username1 username2 ...`",
    "team remove": ""
}


commands = {
    "do": do,
    "inspire": inspire,
    "help": bot_help,
    "counter": counter,
    "add": add,
    "up": up,
    "rank": rank_command,
    "ua": updateadmins,
    "update_admins": updateadmins,
    "skirmish": skirmish,
    'sk': skirmish,
    "team": teams,
    "teams": teams,
    "checkin": check_in,
    "ci": check_in,
    "score": sk_score
}

signal.signal(signal.SIGTERM, onexit)
signal.signal(signal.SIGINT, onexit)

g.init()

if __name__ == "__main__":
    try:
        READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
        if g.slack_client.rtm_connect():
            print("{} connected and running!".format(BOT_NAME))
            while True:
                command, channel, slack_user, slack_args = parse_slack_output(g.slack_client.rtm_read())
                if command and channel and slack_user:
                    handle_command(command, channel, slack_user, slack_args)
                time.sleep(READ_WEBSOCKET_DELAY)
        else:
            print("Connection failed. Invalid Slack token or bot ID?")
            raise ConnectionError("Connect Failed.")

    except (ConnectionError, TimeoutError) as e:
        print("Caught Exception: {}. Shutting down.".format(str(e)))
        onexit(signal.SIGKILL, exit_code=23)
    except Exception as e:
        print("Caught Exception: {}. Shutting down.".format(str(e)))
        onexit(signal.SIGKILL)
