antibot
=======

A bot for my Slack team made with <3 in Python. It consists of commands to 
 * Create, edit and manage counters.
 * Have a ranking system based on the counters.
 * Send occasional inspirational messages
 * Have a team based management system, for arbitrary users in the group.
 * Also, a small admin control system, based on the slack group's admins.

All of this is done using Python 3, Slackclient, SQLite (Persistent data.) and BrainyQuote (For quotes).

Installing
============
To run, you require Python 3. The dependencies are in the *requirements.txt*. To install them run:

    pip install -r requirements.txt


Running
=======

To run, export, the following, environment variables:

    export SLACK_BOT_TOKEN='your-slack-token'
    export BOT_ID='bot-id'

then run

    python bot.py

Or you could utilize the ``antibot.service` file, which contains:

	[Unit]
	Description=Slackbot daemon
	After=network.target network-online.target

	[Service]
	Type=simple
	Environment="SLACK_BOT_TOKEN=your-slack-token"
	Environment="BOT_ID=your-bot-id"
	ExecStart=/usr/bin/python3 bot.py
	Restart=on-failure
	RestartSec=600 
	# RestartPreventExitStatus=23
	StandardOutput=syslog+console

	[Install]
	WantedBy=default.target

Replace, `SLACK_BOT_TOKEN` and `BOT_ID` with the relevant variables.
