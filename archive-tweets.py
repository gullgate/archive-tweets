#!/usr/bin/python

import os
import pytz
import sys
import tweepy

# Personalization
me = len(sys.argv) > 1 and sys.argv[1] or 'HerraBRE'
tweetdir = os.environ['HOME'] + '/bre.pagekite.me/twitter/'
homeTZ = pytz.timezone('GMT+0')

# Parameters.
maxtweets = 1000
urlprefix = 'http://twitter.com/%s/status/'
tweetfile = tweetdir + me + '.txt'
idfile = tweetdir + me + '-lid.txt'
datefmt = '%B %-d, %Y at %-I:%M %p (%s)'

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

# Authorize.
api = setup_api()

# Get the ID of the last downloaded tweet.
lastID = '204960244940537858'
try:
  with open(idfile, 'r') as f:
    lastID = f.read().rstrip()
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
    if t.id_str > lastID and t.id_str != maxID:
      ts = utc.localize(t.created_at).astimezone(homeTZ)
      try:
        frm = t.from_user
      except AttributeError:
        frm = me
      # TODO: Clean up t.co URLs by using this trick:
      #       curl -sLI http://t.co/Hy13FmLM |grep Location:
      lines = ['From: @%s' % frm,
               'Text: %s' % t.text,
               'Date: %s' % ts.strftime(datefmt).decode('utf8'),
               'Link: %s%s' % (urlprefix % frm, t.id_str),
               '', '']
      f.write('\n'.join(lines).encode('utf8'))
      if t.id_str > maxID:
        maxID = t.id_str
lastID = maxID

# Update the ID of the last downloaded tweet.
with open(idfile, 'w') as f:
  lastID = f.write(lastID)
