from threading import Timer
from datetime import datetime, timedelta
from brainyquote import pybrainyquote
from constants import DEFAULT_DELETE_DELAY, BOT_NAME, BOT_ID, RELAPSE_POINTS,\
    CHECKIN_FREQ_DAYS, BUFFER_DAYS_TEAM, PER_DAY_POINTS, SKIRMISH_NOADMIN_FUNCTIONS
import globals as g
from functools import partial

# Admin handling code

def updateadmins(channel, slack_user, args):
    """
    Updates the admins based on the current admin list of the group.
    :return: 
    """
    call = g.slack_client.api_call("users.list")
    if call['ok']:
        try:
            admins = [user['id'] for user in call['members'] if user['is_admin']]
            str_admin = ', '.join('?' for _ in admins)
            g.cursor.execute('UPDATE counter SET admin = 1 WHERE userid IN ({0})'.format(str_admin),
                           admins)
            g.cursor.execute('UPDATE counter SET admin = 0 WHERE userid NOT IN ({0})'.format(str_admin),
                           admins)
            g.db.commit()
            sendmessage(channel=channel, message="Updated the admin list.")
        except Exception as e:
            print('Error updating admins.')
            sendmessage(channel, 'Error updating admins.')


def checkadmin(slack_user):
    """
    :return: Returns True only if the user is an admin 
    """
    val = False
    try:
        for row in g.cursor.execute('SELECT admin FROM counter WHERE userid=? LIMIT 1;',
                                  [slack_user]):
            val = True if row[0] else False
    except Exception as e:
        print("Error checking admin for: {}, with Exception: {}".format(slack_user, str(e)))
    finally:
        return val


# Skirmish code comes here.


def skirmish_dates():
    """
    Returns the start and end date of the current skirmish, otherwise, a tuple of None, None
    """
    try:
        for start_date, end_date in g.cursor.execute('SELECT start_date, end_date FROM sk_details LIMIT 1;'):
            return start_date, end_date
    except Exception as e:
        print('Error checking for skirmish start.')

    return None, None


def skirmish_started(buffer_days=timedelta(days=0)):
    """
    Check if skirmish started. 
    """
    start_date, end_date = skirmish_dates()
    if start_date and end_date and start_date - buffer_days <= datetime.utcnow().date() <= end_date + buffer_days:
        return True
    return False

def skirmish_exists():
    """
    Check if the skirmish exists
    """
    try:
        c = g.cursor.execute('SELECT EXISTS(SELECT 1 FROM sk_details WHERE id=1 LIMIT 1);').fetchone()[0]
        if c:
            return True
        else:
            return False
    except Exception as e:
        print('Unable to check if the skirmish is planned.')

    return False


def skirmish(channel, slack_user, args):
    """
    Parent of all the skirmish functions. 
    """
    if args and args[0] in SKIRMISH_NOADMIN_FUNCTIONS:
        pass
    elif not checkadmin(slack_user):
        sendmessage(channel=channel, message="You are not an admin, thus you don't have skirmish controls")
        return

    if not args or args[0] == 'details':
        start_date, end_date = skirmish_dates()
        if start_date and end_date:
            r = 'Current skirmish is going on for the period of {} to {}'\
                .format(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            sendmessage(channel, r)
        else:
            r = 'No skirmish is currently going on.'
            sendmessage(channel, r)
    elif args[0] == 'add':
        start_date, end_date = skirmish_dates()
        if not start_date and not end_date:
            sendmessage(channel, "No skirmish is planned.")
            return

        try:
            names = get_list_of_usernames(args[1:])
            if not names:
                sendmessage(channel, 'Unable to add to the skirmish, no user[s] found.')
                return
            per_name = '( ?, NULL, 0, \''+ start_date.isoformat() + '\')'
            sql_str = ', '.join(per_name for _ in names)

            g.cursor.execute('INSERT INTO sk_pinfo VALUES {}'.format(sql_str), names)
            g.db.commit()
            sendmessage(channel, 'Added to the skirmish.')
        except Exception as e:
            print('Error adding to skirmish. Extra vars: names: {}'.format(names))
            sendmessage(channel, 'Error adding to skirmish')

    elif args[0] == 'start':
        def skirmish_start(channel, slack_user, start_date=None, end_date=None):
            """
            Function for starting the skirmish if, one hasn't already started yet. 
            """

            # Check if already running
            if skirmish_exists():
                sendmessage(channel, 'Skirmish has already begun, if you want to start it again, end the current one.')
                return

            if not end_date:
                end_date = start_date
                start_date = datetime.utcnow().date()

            try:
                g.cursor.execute('INSERT INTO sk_details VALUES (1, ?, ?)', (start_date, end_date))
                g.db.commit()
                sendmessage(channel, 'Created Skirmish for the range {} to {}'
                            .format(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))
            except Exception as e:
                print('Error in creating Skirmish')
                sendmessage(channel, 'Error in creating Skirmish')

        try:
            start = datetime.strptime(args[1], "%Y-%m-%d").date()
            end = datetime.strptime(args[2], "%Y-%m-%d").date()
            if start < end:
                skirmish_start(channel, slack_user, start, end)
            else:
                sendmessage(channel, 'Cannot create skirmish, Start Date is on or after End date')
        except Exception as e:
            print("Error in starting skirmish.")
            sendmessage(channel, "Couldn't parse Date and time, please, provide it in the format YYYY-mm-dd")
    elif args[0] == 'end':
        def skirmish_end(channel):
            """
            Ending the skirmish which, is mostly deleting all the respective rows and foreign keys. 
            """
            try:
                g.cursor.execute('DELETE FROM sk_pinfo')
                g.cursor.execute('DELETE FROM teams')
                g.cursor.execute('DELETE FROM sk_details')
                g.db.commit()
                sendmessage(channel, 'Ending skirmish. Removing all related data.')
            except Exception as e:
                print('Error in deleting skirmish related content.')
                sendmessage(channel, 'Error in deleting skirmish related content.')

        skirmish_end(channel)
    elif args[0] == 'remove':
        if not skirmish_exists():
            sendmessage(channel, "No skirmish is currently planned.")
            return

        try:
            names = get_list_of_usernames(args[1:])
            sql_str = ', '.join('?' for _ in names)

            g.cursor.execute('DELETE FROM sk_pinfo WHERE username IN ({0})'.format(sql_str), names)
            g.db.commit()
            sendmessage(channel, 'Removed {} from the skirmish'.format(', '.join(name for name in names)))
        except Exception as e:
            print('Error removing from team')
            sendmessage(channel, 'Error removing from team')
    elif args[0] == 'players':
        if not skirmish_exists():
            sendmessage(channel, "No skirmish is currently planned.")
            return

        try:
            str = 'Players:\n'
            for name, in g.cursor.execute('SELECT username from sk_pinfo'):
                str += '\t' + name + '\n'

            sendmessage(channel, str[:-1])
        except Exception as e:
            print('Error in fetching skirmish player list.')
            sendmessage(channel, 'Error in fetching skirmish player list.')
    elif args[0] == 'team':
        if not skirmish_exists():
            sendmessage(channel, "No skirmish is currently planned.")
            return

        if not args or args[0] == 'list':
            try:
                str = 'Teams:\n'
                team_list = g.cursor.execute('SELECT name from teams;')
                t = False
                for team in team_list:
                    str += "Team " + team[0] + '\n'
                    t = True

                if t:
                    sendmessage(channel, str[:-1])
            except Exception as e:
                print('Error in fetching team list.')
                sendmessage(channel, 'Error in fetching team list.')
        elif args[1] == 'add':
            try:
                g.cursor.execute('INSERT INTO teams VALUES (?, 1)', [args[2]])
                g.db.commit()
                sendmessage(channel, 'Team {}, added to skirmish'.format(args[2]))
            except Exception as e:
                r = 'Error adding team to skirmish.'
                sendmessage(channel, r)
                print(r)
        elif args[1] == 'remove':
            try:
                g.cursor.execute('DELETE FROM teams WHERE name=?', [args[2]])
                g.db.commit()
                sendmessage(channel, 'Team {}, removed to skirmish'.format(args[2]))
            except Exception as e:
                print('Error removing team to skirmish.')
                sendmessage(channel, 'Error removing team to skirmish.')



def teams(channel, slack_user, args):
    """
    Skirmish Teams functions. 
    """
    if not skirmish_exists():
        sendmessage(channel, "No skirmish is currently planned.")
        return

    if not args or args[0] == 'list':
        try:
            str = 'Teams:\n'
            team_list = g.cursor.execute('SELECT name from teams;')
            t = False
            for team in team_list:
                str += "Team " + team[0] + '\n'
                t = True

            if t:
                sendmessage(channel, str[:-1])
        except Exception as e:
            print('Error in fetching team list.')
            sendmessage(channel, 'Error in fetching team list.')
    elif args[0] == 'players':
        try:
            str = 'Teams:\n'
            team_list = g.cursor.execute('SELECT name from teams;').fetchall()
            for team in team_list:
                str += "Team " + team[0] + '\n'
                for name, in g.cursor.execute('SELECT username from sk_pinfo WHERE team=?', team):
                    str += '\t' + name + '\n'

            sendmessage(channel, str[:-1])
        except Exception as e:
            print('Error in fetching team players list.')
            sendmessage(channel, 'Error in fetching team players list.')
    elif args[0] == 'add':
        if not args[2:]: # Nothing after the team name
            return

        try:
            team_name = args[1]
            names = get_list_of_usernames(args[2:])

            g.cursor.execute('UPDATE sk_pinfo SET team=? WHERE username IN ({0})'
                             .format(', '.join('?' for _ in names)), [team_name, *names])
            g.db.commit()
        except Exception as e:
            print('Error adding to team')
            sendmessage(channel, 'Error adding to team')
    elif args[0] == 'remove':
        if not args[2:]:
            return
        try:
            names = get_list_of_usernames(args[2:])
            sql_str = ', '.join('?' for _ in names)

            g.cursor.execute('UPDATE sk_pinfo SET team=NULL WHERE team=? AND username IN ({0})'.format(sql_str),
                           names)
            g.db.commit()
        except Exception as e:
            print('Error adding to team')
            sendmessage(channel, 'Error adding to team')
    elif args[0] == 'score':
        score_str = team_score()
        if score_str:
            sendmessage(channel, score_str)

def team_score():
    try:
        team_str = 'Teams:\n'
        team_list = g.cursor.execute('SELECT name from teams;').fetchall()
        team_lead_names = ''
        team_lead_score = -1
        for team in team_list:
            team_str += "Team " + team[0] + '\n'
            c = g.cursor.execute('SELECT username from sk_pinfo WHERE team=?', team)
            usernames = [name for name, in c]
            scores = []
            start_date, end_date = skirmish_dates()
            for relapses, checkin_date, name in g.cursor.execute('SELECT relapses, checkin_date, username FROM sk_pinfo WHERE '
                                                           'username IN ({0})'.format(
                ', '.join('?' for _ in usernames)),
                    usernames):
                score = score_value(checkin_date, start_date, end_date, relapses)
                team_str += '\t' + name + ": *" + str(score) + '* with Relapses: *' + str(relapses) +'*\n'
                scores.append(score)
            total = sum(scores)
            if team_lead_score < total:
                team_lead_score = total
                team_lead_names = team[0]
            team_str += 'Team Total: ' + str(total) + '\n'

        team_str += 'Team ' + team_lead_names + ' is in lead.'
        return team_str
    except Exception as e:
        print('Error in fetching team score.')
    return None

def score_value(checkin_date, start_date, end_date, relapses):
    """
    Score value based on checkin, start date and relapses 
    """
    date = datetime.utcnow().date()

    if (date - checkin_date).days >= 7:
        date = checkin_date + timedelta(days=7)

    date = end_date if date > end_date else date

    val = (date - start_date).days * PER_DAY_POINTS - relapses + relapses * RELAPSE_POINTS
    return val


def sk_score(channel, slack_user, args):
    """
    Scoring functions for the skirmish
    """
    if not skirmish_started():
        sendmessage(channel, 'Skirmish hasn\'t started yet')
        return

    elif not args or args[0] in ['team', 'teams']:
        score_str = team_score()
        if score_str:
            sendmessage(channel, score_str)
    elif args[0] == 'total':
        try:
            total = 0
            start_date, end_date = skirmish_dates()
            for name, relapses, checkin_date in g.cursor.execute('''SELECT username, relapses, checkin_date  
                                                                   FROM sk_pinfo'''):

                score = score_value(checkin_date, start_date, end_date, relapses)
                total += score
            total_str = 'Skirmish Total: ' + str(total)
            sendmessage(channel, total_str)
        except Exception as e:
            print('Error finding scores for users')
    elif args[0] == 'players':
        try:
            player_str = 'Players:\n'
            total = 0
            start_date, end_date = skirmish_dates()
            for name, relapses, checkin_date in g.cursor.execute('''SELECT username, relapses, checkin_date  
                                                           FROM sk_pinfo'''):

                score = score_value(checkin_date, start_date, end_date, relapses)
                player_str += name + ': *' + str(score) + '* with Relapses: *' + str(relapses) + '*\n'
                total += score
            player_str += 'Skirmish Total: ' + str(total)
            sendmessage(channel, player_str)
        except Exception as e:
            print('Error finding scores for users')
    elif args[0] == 'show':
        try:
            user = getusername(slack_user)
            start_date, end_date = skirmish_dates()
            msg = ''
            for relapses, checkin_date, name in g.cursor.execute(
                    'SELECT relapses, checkin_date FROM sk_pinfo WHERE '
                    'username=?', [user]):

                score = score_value(checkin_date, start_date, end_date, relapses)
                msg = 'Your skirmish score is at *' + str(score) + '* with Relapses: *' + str(relapses) + '*\n'

            sendmessage(channel, msg)
        except Exception as e:
            print('Error in fetching individual score.')


def check_in(channel, slack_user, args):
    """
    Checks in the user. 
    """
    start_date, end_date = skirmish_dates()
    if not start_date and not end_date:
        sendmessage(channel, 'Skirmish hasn\'t started yet')
        return

    def getactualcheckin(start_date):
        """
        Returns the actual check in date. 
        """
        today = datetime.utcnow().date()
        diff = today.weekday() - start_date.weekday()

        if diff <= 0:
            diff = diff

        checkin_date = today - timedelta(days=diff)

        return checkin_date


    try:
        user = getusername(slack_user)
        date = getactualcheckin(start_date)
        g.cursor.execute('UPDATE sk_pinfo SET checkin_date=? WHERE username=?', [date, user])
        g.db.commit()
        sendmessage(channel, 'Checked in.')
    except Exception as e:
        print('Error in checkin date.')


# General Functions for the commands start here.

def get_list_of_usernames(list_of_names):
    """
    :param list_of_names: Could be names or, in the form of '<@SKJDNJS>'
    """
    names = []
    userids = []
    for user in list_of_names:
        userid = getuserid(user)
        if not userid:
            names += [user]
        else:
            userids += [userid]

    if userids:
        def getusernames(userids):
            t = g.cursor.execute('SELECT username FROM counter WHERE userid IN ({0})'
                                 .format(', '.join('?' for _ in userids)), userids)
            return [username for username, in t]
        temp = getusernames(userids)
        names += temp
    return names

def getusername(userid):
    username = ''
    try:
        for name, in g.cursor.execute('SELECT username FROM counter WHERE userid=? LIMIT 1', [userid]):
            username = name
    except Exception as e:
        print('Unable to get username for user')
    finally:
        return username

def getuserid(user_text):
    """
    :return the userid if the text is of the form: '<@USERID>' else return None
    """
    if user_text[0:2] == "<@" and user_text[-1] == ">":
        return user_text[2:-1]
    else:
        return None

def get_counter_for_user(slack_user):
    """
        Returns the counter for the given user
    """
    val = 0
    try:
        for row in g.cursor.execute('SELECT start_date FROM counter WHERE userid=? LIMIT 1;',
                                  [slack_user]):
            val = (datetime.utcnow().date() - row[0]).days
    except Exception as e:
            print("Error resetting counter for: {}, with Exception: {}".format(slack_user, str(e)))
    finally:
        return val

def rank_command(channel, slack_user, args):
    """
        Sends a message to the channel with the rank of the user.
    """
    days = get_counter_for_user(slack_user)
    r, r_str = get_rank_for_user(days)
    response = "You are at Rank " + str(r) + " with the title " + r_str
    sendmessage(channel, response)


def get_rank_for_user(days):
    """
        Returns the rank, for the specific days in a range.
    """

    rank_string = ""
    rank = 0
    if days == 0:
        rank_string = "Private"
        rank = 1
    elif days == 1:
        rank_string = "Private 2"
        rank = 2
    elif 2 <= days <= 4:
        rank_string = "Private First Class"
        rank = 3
    elif 4 < days <= 8:
        rank_string = "Specialist"
        rank = 4
    elif 8 < days <= 12:
        rank_string = "Corporal"
        rank = 5
    elif 12 < days <= 18:
        rank = 6
        rank_string = "Sergeant"
    elif 18 < days <= 24:
        rank = 7
        rank_string = "Staff Sergeant"
    elif 24 < days <= 32:
        rank_string = "Sergeant First Class"
        rank = 8
    elif 32 < days <= 40:
        rank_string = "Master Sergeant"
        rank = 9
    elif 40 < days <= 50:
        rank_string = "First Sergeant"
        rank = 10
    elif 50 < days <= 60:
        rank_string = "Sergeant Major"
        rank = 11
    elif 60 < days <= 72:
        rank_string = "Command Sergeant Major"
        rank = 12
    elif 72 < days <= 84:
        rank_string = "Sergeant Major of the Army"
        rank = 13
    elif 84 < days <= 98:
        rank_string = "Warrant Officer"
        rank = 14
    elif 98 < days <= 112:
        rank_string = "Chief Warrant Officer 2"
        rank = 15
    elif 112 < days <= 128:
        rank_string = "Chief Warrant Officer 3"
        rank = 16
    elif 128 < days <= 144:
        rank_string = "Chief Warrant Officer 4"
        rank = 17
    elif 144 < days <= 162:
        rank_string = "Chief Warrant Officer 5"
        rank = 18
    elif 162 < days <= 180:
        rank_string = "Second Lieutenant"
        rank = 19
    elif 180 < days <= 200:
        rank_string = "First Lieutenant"
        rank = 20
    elif 200 < days <= 220:
        rank_string = "Captain"
        rank = 21
    elif 220 < days <= 242:
        rank_string = "Major"
        rank = 22
    elif 242 < days <= 264:
        rank_string = "Lieutenant Colonel"
        rank = 23
    elif 264 < days <= 288:
        rank_string = "Colonel"
        rank = 24
    elif 288 < days <= 312:
        rank_string = "Brigadier General"
        rank = 25
    elif 312 < days <= 338:
        rank_string = "Major General"
        rank = 26
    elif 338 < days <= 364:
        rank_string = "Lieutenant General"
        rank = 27
    elif 364 < days <= 392:
        rank_string = "General"
        rank = 28
    elif days > 392:
        rank_string = "General of the Army"
        rank = 29

    return rank, rank_string


def sendmessage(channel, message, delete_delay=DEFAULT_DELETE_DELAY):
    """
    Sends a message to the given channel.
    :param channel: Channel to send message to.
    :param message: Message to send.
    :param delete_delay: Delay in seconds for when the message has to be deleted.
            Default delay is 2 minutes.
    """
    status = g.slack_client.api_call("chat.postMessage", channel=channel, text=message, as_user=True)

    if delete_delay != 0 and status["ok"] == True:
        Timer(delete_delay, partial(delete_message, channel, status['message']['ts'])).start()

def delete_message(channel, ts):
    """
        Deletes a message with a specific ts value on the channel.
    """
    return g.slack_client.api_call("chat.delete", channel=channel, ts=ts)

def do(channel, slack_user, args):
    """

    """
    response = 'This doesn\'t exist and you are not supposed to be here.'
    sendmessage(channel, response)

def inspire(channel, slack_user, args):
    """
        Sends an inspirational message to the channel. Note, use pybrainyquote
    """
    quote = pybrainyquote.get_quotes('motivational')[0]
    sendmessage(channel, quote, delete_delay=0)


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

    if not args or args[0] == 'show':
        response = "Your counter is at: " + str(get_counter_for_user(slack_user))
        sendmessage(channel, response)

    elif args[0] == 'reset' or args[0] == 'set' or args[0] == 'add':

        def reset_date(channel, slack_user, date=None, ignore_relapse=False):
            """
                Resets date for given user, to the date provided or the current date.
            """
            if date is None:
                date = datetime.utcnow().date()

            try:
                c = g.cursor.execute('SELECT EXISTS(SELECT 1 FROM counter WHERE userid=? LIMIT 1);',
                                   [slack_user]).fetchone()[0]
                if c:
                    def update_skirmish_relapses(slack_user):
                        username = getusername(slack_user)
                        if in_skirmish(username):
                            g.cursor.execute('UPDATE sk_pinfo SET relapses = relapses + 1 WHERE username=?',
                                                 [username])

                    g.cursor.execute('UPDATE counter SET start_date=? WHERE userid=?', [date, slack_user])
                    if not ignore_relapse:
                        update_skirmish_relapses(slack_user)

                else:

                    def getuserinfo(slack_user):
                        api_call = g.slack_client.api_call("users.info", user=slack_user)
                        if api_call.get('ok'):
                            return api_call['user']['name']
                        return ""

                    username = getuserinfo(slack_user)
                    g.cursor.execute('INSERT INTO counter VALUES (?, ?, ?, 0)', [slack_user, date, username])
                g.db.commit()
                sendmessage(channel, "Counter has been set to {}".format(date.strftime("%Y-%m-%d")))
            except Exception as e:
                print("Error resetting counter for: {}, with Exception: {}".format(slack_user, str(e)))

        def in_skirmish(username):
            """
            Checks if the user is present in the skirmish 
            """
            try:
                c = g.cursor.execute('SELECT EXISTS(SELECT 1 FROM sk_pinfo WHERE username=? LIMIT 1);',
                                     [username]).fetchone()[0]
                if c:
                    return True
                else:
                    return False
            except Exception as e:
                print('Unable to check if the user is in the skirmish.')

            return False

        try:
            ignore_relapse = False

            if len(args) > 2 and (args[2] == 'ignore' or args[2] == 'ign'):
                ignore_relapse = True

            if args[1:]:
                d = datetime.strptime(args[1], "%Y-%m-%d").date()
                reset_date(channel, slack_user, d, ignore_relapse)
            else:
                reset_date(channel, slack_user, ignore_relapse=ignore_relapse)
        except Exception as e:
            print("Error while resetting, with exception {}".format(str(e)))
            response = "Couldn't parse Date and time, please, provide it in the format YYYY-mm-dd"
            sendmessage(channel, response)

    elif args[0] == 'team' or args[0] == 'total':

        def gettotalcounter():
            """
                Retrieves the Counter for the whole team.
            """
            val = 0
            response = ""
            try:
                for username, sdate in g.cursor.execute('SELECT username, start_date FROM counter;'):
                    days = (datetime.utcnow().date() - sdate).days
                    r, r_str = get_rank_for_user(days)
                    response += "[" + r_str + "] " + username + ": " + str(days) + "\n"
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

        def remove_user(channel, slack_user, usernames=None):
            """
                If username given, then specific username is removed from the Counter table,
                else the slack_user is removed.
            """

            try:
                r = "Removed counter for user: "
                if usernames:
                    c = g.cursor.execute('DELETE from counter WHERE username=?', [usernames])
                    r += usernames

                else:
                    c = g.cursor.execute('DELETE from counter WHERE userid=?', [slack_user])
                    r += "<@" + slack_user + ">"

                g.db.commit()

                if g.cursor.rowcount == -1:
                    r = 'No such user exists'
                sendmessage(channel, r)

            except Exception as e:
                print("Error, while deleting with exception: {}".format(str(e)))

        if args[1:]:
            names = get_list_of_usernames(args[1:])
            remove_user(channel, slack_user, names)
        else:
            remove_user(channel, slack_user)
