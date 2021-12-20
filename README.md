# Introduction
This is the script I used to migrate an old forum hosted on a Simple Press Wordpress Forum on to groups.io. The way it works is it takes an input of the forum names that you'd like to migrate, the hashtag you'd like to tag that forum with, and the filename of the mbox file you'd like to generate that contains that list of topics.

# Using this script
This script is intended to be run either in the root web directory of your live forum, or on a computer/server that has a file backup of the webserver's root directy also running a copy of the Wordpress database in MariaDb.

There are two operating modes. 

The first one and recommended method is to output the migration in mbox files. These files can be provided to groups.io support and they will import them for you (at least they did for us). You can also coveniently preview the output using any email client that has support for mbox files.

The second one is to send each topic as an individual email directly to groups.io. This is a very slow and error prone process. groups.io rate limits emails from a single email address to about once per minute before blocking it after 40 emails. Additionally, depending on your email server you may only be able to send messages with attachments summing to 25MB (any larger and your smtp server will complain and this script will crash, I did not spend time adding error handling or any work arounds for this).

# Variables
Set the following variables in the SimplePressToGroupsIoMigration.py
| Variable Name    | Description |
| `debug`          | Shows CLI output while it runs. |
| `generateMbox`   | This boolean says whether or not to generate mbox files for each forum listed in the migration list. |
| `sendEmails`     | This boolean indicates whether it should send each topic as an email to the `receiver_address`
| `sender_address` | This string indicates what source email address will be on the generated emails. When using `sendEmails` set to `True`, this must be the email address you're using to send the emails or you're very likely to run into issues |
| `receiver_address` | This should be the groups.io email address you'd use to send an email to add a new message to a group on groups.io |
| `conn` | This is your database connection object. Set `user`, `password`, and `database` appropriately. |
| `email_password` | This is important if you have `sendEmails` set to `True`. This is the password you'll used connect to your smtp server. |
| `smtp_server` | This is the domain name of your smtp server |
| `domain` | This should be the domain that wordpress was accessed on. It's important that this is the domain that simplepress used to access all the images as this script will do a search replace on this to generate embedded images and find the images on your local filesystem |
| `migration_list` | This is a list of dictionaries that contain a mapping of forum name to the name of the mbox file and the hash tag that will go in the subject of each email |

# Dependencies
See requirements.txt for dependencies. I recommend setting it up in python venv.

# Disclaimer
There is very little (almost no) error handling logic. For my purposes, as long as I could get it to output the files I needed, that was sufficient and I handled Tracebacks/unhandled exceptions as they came.

I'm not affilated with groups.io or Simple Press.

Use this at your own risk!