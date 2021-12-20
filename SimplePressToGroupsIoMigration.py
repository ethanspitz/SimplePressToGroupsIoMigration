import mariadb
import sys
import smtplib
from time import sleep
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from email.utils import format_datetime
from bs4 import BeautifulSoup
from mimetypes import guess_type
import mailbox

debug = True

# This is the preferred way of using this script.
generateMbox = True

# Use to send an email to specified address for each topic. I cannot recommend
# using this option as any topic that has over 25MB of attachments will cause
# the whole script to fail and I didn't add any handling for this. It also
# will take many days running 24/7 for even smaller forums as it can only
# effectively migrate 1 topic per minute.
sendEmails = False

# Addresses to use on emails
sender_address = "source_email@example.com"
receiver_address = "subgroupname@yourgroupname.groups.io"

# Email information. Use this section if you actually want to
# send the emails (sendEmails set to true)
email_password = ""
smtp_server = "smtp.gmail.com"

# Domain name simple press is hosted on. It's important this look like the
# domain name used in the beginning of image sources, otherwise your images
# won't be embedded properly.
domain="http://example.com/"

# Replace this with the list of Forum names you are using and
# how you'd like them to be hashtagged
migration_list = [
  {
    'forum_name': "Using the Manta Forum",
    'save_name': "Using_the_Manta_Forum",
    'hash_tag': "#UsingTheMantaForum #LEGACYOwnersSite"
  },
  {
    'forum_name':"Hull Construction",
    'save_name': "Hull_Construction",
    'hash_tag': "#HullConstruction #LEGACYOwnersSite"
  },
  {
    'forum_name':"Boat Systems",
    'save_name': "Boat_Systems",
    'hash_tag': "#BoatSystems #LEGACYOwnersSite"
  },
  {
    'forum_name':"Electronics",
    'save_name': "Electronics",
    'hash_tag': "#Electronics #LEGACYOwnersSite"
  },
  {
    'forum_name':"Energy",
    'save_name': "Energy",
    'hash_tag': "#Energy #LEGACYOwnersSite"
  },
  {
    'forum_name':"Standing &amp; Running Rigging",
    'save_name': "Standing_and_Running_Rigging",
    'hash_tag': "#StandingAndRunningRigging #LEGACYOwnersSite"
  },
  {
    'forum_name':"Underway",
    'save_name': "Underway",
    'hash_tag': "#Underway #LEGACYOwnersSite"
  },
  {
    'forum_name':"Life Aboard",
    'save_name': "Life_Aboard",
    'hash_tag': "#LifeAboard #LEGACYOwnersSite"
  },
  {
    'forum_name':"Manta Flea Market",
    'save_name': "Manta_Flea_Market",
    'hash_tag': "#MantaFleaMarket #LEGACYOwnersSite"
  },
  {
    'forum_name':"Old Mantatech Forum",
    'save_name': "Old_Mantatech Forum",
    'hash_tag': "#OldOldMantatechForum #LEGACYOwnersSite"
  }
]

# Loop through the migration list
for forum in migration_list:
  # Set variables from the migration list
  forum_name = forum['forum_name']
  forum_name_file_safe = forum['save_name']
  hash_tag = forum['hash_tag']

  # Create mailbox file
  if generateMbox is True:
    mbox_file = f"{forum_name_file_safe}_archive.mbox"
    mbox_object = mailbox.mbox(mbox_file)
    mbox_object.lock()

  try:
    conn = mariadb.connect(
      user="user", # Put your sql server username here
      password="pass", # Put your sql server password here
      host="127.0.0.1",
      port=3306,
      database="database" # Put your sql server database name here
    )
  except mariadb.Error as e:
    print(f"Error connecting to database: {e}")
    sys.exit(1)

  cur = conn.cursor(named_tuple=True)

  # Get forum ID
  cur.execute(f"SELECT forum_id from wp_sfforums where forum_name = '{forum_name}'")
  forum_name_sql_resp = cur.fetchall()

  if cur.rowcount != 1:
    print(f"Too many matches on forum name, matched {cur.rowcount} rows")
    sys.exit(1)

  # Extract forum id into variable
  forum_id = forum_name_sql_resp[0].forum_id

  # Generate list of topics in the forum
  cur.execute(f"SELECT topic_id,topic_name,post_id from wp_sftopics WHERE forum_id = {forum_id} ORDER BY topic_id")
  forum_topic_list_sql_resp = cur.fetchall()

  if cur.rowcount <= 0:
    print(f"Failed to pull list of topics in forum")
    sys.exit(1)

  # Loop through all topics
  for topic in forum_topic_list_sql_resp:
    if debug:
      print(f"Topic ID: {topic.topic_id}, Topic Name: {topic.topic_name}, Post ID: {topic.post_id}")
    
    # Subject line with topic name and new hashtags
    subject = f"{topic.topic_name} {hash_tag}"

    # Grab list of posts in topic
    cur.execute(f"SELECT user_id,post_date,post_content,post_index,post_id,guest_name FROM wp_sfposts where topic_id = {topic.topic_id} ORDER BY post_index")
    post_list_sql_resp = cur.fetchall()

    if cur.rowcount <= 0:
      print(f"Failed to pull list of posts in topic: {topic.topic_id}")
      sys.exit(1)

    # Let's start by creating the email object
    email = MIMEMultipart()
    email['From'] = sender_address
    email['To'] = receiver_address
    # Seems like subject line doesn't support HTML. There are likely
    # other things that should be replaced, but this is the only thing
    # I noticed that should really be replaced in the subject line.
    email['Subject'] = subject.replace("&amp;","&")

    # Generate Message that contains all the posts for that topic
    # Start with oldest at top with newest posts at the bottom.
    # Seperate each post with an HTML horizontal seperator.
    seperator = f"<hr>"
    message = f"{seperator}"
    for post in post_list_sql_resp:
      # For first post in topic, use that as the email date.
      if post.post_index == 1:
        email['Date'] = format_datetime(post.post_date)

      # Grab user display name
      display_name = ""

      # Guest users on Simple Press seem to either have undefied User IDs or
      # have a User ID of 0. In those cases, grab their username from the
      # post directly. Normally we'll look up the user name from the wp_users
      # table using the user ID.
      if post.user_id != 0 and post.user_id is not None:
        cur.execute(f"SELECT display_name from wp_users where ID = {post.user_id}")
        display_name_sql_resp = cur.fetchall()

        if cur.rowcount != 1:
          print(f"Failed to pull display name from post {post.post_id}")
          sys.exit(1)

        display_name = display_name_sql_resp[0].display_name
      else:
        display_name = post.guest_name

      # Append post content to message
      message = message + f"{post.post_content}<br />" \

      # Attach attachments, start by getting them
      cur.execute(f"SELECT path,filename,type from wp_sfpostattachments where post_id = {post.post_id}")
      attachment_list_sql_resp = cur.fetchall()

      # Add attachments section to post.
      if cur.rowcount > 0:
        message = message + f"<b>Attachments:</b><br />"

      # This could probably be indented in under the above if, but it doesn't matter
      # since this won't run if cur.rowcount isn't greater than 0.
      # this takes the attachment path, and grabs the actual file and adds it as a
      # file attachment to the email. It also lists the filename in the attachment
      # list in the post so you can find what post an attachment is associated with.
      for attachment in attachment_list_sql_resp:
        file_path = f"wp-content/sp-resources/forum-{attachment.type}-uploads/{attachment.path}/{attachment.filename}"
        mime_attachment = MIMEApplication(open(file_path, 'rb').read())
        mime_attachment.add_header('Content-Disposition', 'attachment', filename=f"{attachment.filename}")
        email.attach(mime_attachment)
        message = message + f"{attachment.filename}<br />"

      # Add footer to post so you can see Who and When the post was made, as well as
      # an indication of which post in the topic you're looking at.
      message = message + f"<br /><b>Member:</b> {display_name}<br />" \
                        + f"<b>Post Date:</b> {post.post_date}<br />" \
                        + f"<b>Post Index:</b> {post.post_index}<br /></td>" \
                        + seperator

    # At his point a raw message is made, we can either send it or try to do some post processing.
    # We'll want to do some post processing to embed images and attachments.
    
    # First let's convert newlines into <br /n>
    message = message.replace('\n','<br />')

    # Replace image links with embedded email images
    message_soup = BeautifulSoup(message,'html.parser')

    # Loop through all the images in the message and replace the links that
    # reference the domains you're migrating from, and embed an inline email
    # in place with the image that references the web server.
    counter = 1
    for img in message_soup.find_all('img'):
      if img['src'].startswith(domain) or img['src'].startswith('/'):
        # For images that come from the domain, we want to "download" the image,
        # and embed in the email
        local_path = ""
        if img['src'].startswith(domain):
          local_path = img['src'].replace(domain, "")
        else:
          # Found a relative path, need to chop off the leading / though to use
          # it in python
          local_path = img['src'][1:]

        # Use file extension and guess_type to get subtype
        (mimetype, encoding) = guess_type(local_path)
        (maintype, subtype) = mimetype.split('/')
        
        # Attach immage to email
        file_image = open(local_path, 'rb')
        mime_image = MIMEImage(file_image.read(), _subtype=subtype)
        file_image.close()
        mime_image.add_header('Content-ID', f'<image{counter}>')
        email.attach(mime_image)

        # Replace img source with the "cid:image{counter}" we just added to the email
        img['src'] = f"cid:image{counter}"

        # increment counter for next image so that all cids are unique
        counter +=1

    # Now lets attach the properly formatted email
    email.attach(MIMEText(str(message_soup),'html'))

    # Send the message
    if sendEmails is True:
      # Establish connection to SMTP
      session = smtplib.SMTP(smtp_server, 587)
      session.starttls()
      session.login(sender_address, email_password)
      text = email.as_string()
      session.sendmail(sender_address, receiver_address, text)
      session.quit()
      # Groups.io has some pretty heavy rate limiting, so we have to be slow
      # when we go about sending the emails to groups.io
      sleep(60)

    # Add to mbox archive
    if generateMbox is True:
      mbox_object.add(mailbox.mboxMessage(email))

  # Write out messages to file and unlock
  if generateMbox is True:
    mbox_object.flush()
    mbox_object.unlock()

# Done!
sys.exit(0)
