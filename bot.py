import os
import time
from slackclient import SlackClient

# starterbot's ID as an environment variable
BOT_ID = os.environ.get("BOT_ID")

# constants
AT_BOT = "<@" + BOT_ID + ">"
BOT_NAME = 'antibot'


# instantiate Slack client
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

def bot_help(channel, slack_user, args):
    """
        Sends a reply, with all the current list of commands.
    """
    response = "<@" + slack_user + "> " + """
    *help*: Gives a list of commands. This is the command.\n
    *inspire*: Sends a motivational quote, to the channel. Doesn't work yet.\n
    *reset counter*: Reset's the user counter, if a _date_ is provided, then to the date, otherwise, to the current date.
    """
    slack_client.api_call("chat.postMessage", channel=channel, text=response, as_user=True)

def do(channel, slack_user, args):
    """

    """
def inspire(channel, slack_user, args):
    """
        Sends an inspirational message to the
    """

def add(channel, slack_user, args):
    sum = 0
    for i in args:
        sum += int(i)
    response = "Sum: " + str(sum)
    slack_client.api_call("chat.postMessage", channel=channel, text=response, as_user=True)

def counter(channel, slack_user, args):
    """

    :param channel:
    :param slack_user:
    :param message:
    :param args:
    :return:
    """

def handle_command(cmd, channel, slack_user, args):
    """
        Receives commands directed at the bot and determines if they
        are valid commands. If so, then acts on the commands. If not,
        returns back what it needs for clarification.
    """
    response = "Unknown command. Use the *help* command, to give a list of commands."
    if cmd in commands:
        commands[cmd](channel, slack_user, args)
    #     response = "Sure...write some more code then I can do that!"
    # slack_client.api_call("chat.postMessage", channel=channel,
    #                       text=response, as_user=True)


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

isInitialized = False

if __name__ == "__main__":
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