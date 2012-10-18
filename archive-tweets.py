#!/usr/bin/python

import os
import pytz
import re
import subprocess
import sys
import tweepy

# Personalization
me = len(sys.argv) > 1 and sys.argv[1] or 'HerraBRE'
tweetdir = os.environ['HOME'] + '/bre.pagekite.me/twitter/'
homeTZ = pytz.timezone('GMT+0')

# Parameters.
maxtweets = 1000
urlprefix = 'https://twitter.com/%s/status/'
tweetfile = tweetdir + me + '.txt'
idfile = tweetdir + me + '-lid.txt'
datefmt = '%a, %d %b %Y %H:%M:%S %z'
mboxts = '%a %b %d %T %Y'

def setup_api():
  """Authorize the use of the Twitter API."""
  a = {}
  with open(os.environ['HOME'] + '/.twitter-credentials') as credentials:
    for line in credentials:
      k, v = line.split(': ')
      a[k] = v.strip()
  auth = tweepy.OAuthHandler(a['consumerKey'], a['consumerSecret'])
  auth.set_access_token(a['token'], a['tokenSecret'])
  return tweepy.API(auth)

TCO_RE = re.compile(r'(https?://t.co/\S+)')
def expand_urls(text):
  def replace_url(m):
    url = m.group(1)
    try:
      lines = ('\n'.join(subprocess.Popen(['curl', '-sLI', url],
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE
                                         ).communicate())).split('\n')
      loc = [l for l in lines if l.startswith('Location: ')][-1]
      return loc.split(': ', 1)[1].strip()
    except (subprocess.CalledProcessError, IndexError):
      return url
  return TCO_RE.sub(replace_url, text)


# Authorize.
api = setup_api()

# Get the ID of the last downloaded tweet.
lastID = int('204960244940537858')
try:
  with open(idfile, 'r') as f:
    lastID = int(f.read().strip())
except IOError:
  pass

# Collect all the tweets since the last one.
tweets = []
tweets.extend(api.user_timeline(me, since_id=lastID,
                                    count=maxtweets,
                                    include_rts=True))
tweets.extend(api.favorites(me))

# Collect all recent mentions of this user, via. the search API.
if '--search' in sys.argv:
  tweets.extend(api.search('%s' % me, count=maxtweets))
else:
  tweets.extend(api.search('@%s' % me, count=maxtweets))

# Sort them by ID...
tweets.sort(key=lambda t: t.created_at)

# Write them out to the twitter.txt file.
maxID = lastID
utc = pytz.utc
with open(tweetfile, 'a') as f:
  for t in tweets:
    if int(t.id_str) > lastID and int(t.id_str) != maxID:
      ts = utc.localize(t.created_at).astimezone(homeTZ)
      try:
        frm = t.from_user
      except AttributeError:
        frm = me
      lines = ['From %s@twitter  %s' % (frm, ts.strftime(mboxts).decode('utf8')),
               'Content-Type: text/plain; charset=utf-8',
               'MIME-Version: 1.0',
               'Link: %s%s' % (urlprefix % frm, t.id_str),
               'Date: %s' % ts.strftime(datefmt).decode('utf8'),
               'From: @%s' % frm,
               'Subject: %s' % t.text,
               '', expand_urls(t.text),
               '', '']
      f.write('\n'.join(lines).encode('utf8'))
      if int(t.id_str) > maxID:
        maxID = int(t.id_str)
lastID = maxID

# Update the ID of the last downloaded tweet.
with open(idfile, 'w') as f:
  lastID = f.write('%s' % lastID)
