#!/usr/bin/python

# py 3 version tested on 3.4.2
# requires praw, requests

import praw
# hide praw induced requests warnings
import warnings

# get user input, write inplace
import getpass
import tempfile

# match & fetch url resources
import re
import requests

# name generation
import string
import random

# create dir
import os

# cli update
import sys

user = None
passwd = None
last = None
save_dir = None

seennit = 'seennit.py3.py'
skipped = 0

def write_to_me(pattern, value):
	t = tempfile.NamedTemporaryFile(mode="r+")

	i = open(seennit, 'r+')
	for line in i:
		match = re.search(pattern, line)
		if match:
			line = match.group(0)+'\''+value+'\'\n'
		t.write(line)
	i.close()

	t.seek(0)

	o = open( seennit, 'w')
	for line in t:
		o.write(line)
	o.close()

	t.close()

def download(s):
	global skipped

	if hasattr(s, 'url'):
		# regex for image
		url = s.url

		img = re.compile('(\.png)$|(\.jpg)$|(\.jpeg)$|(\.gif)$')
		imgur = re.compile('^http://(\w+.)?imgur.com')
		imgur_imgs = re.compile('<meta\s+property=\"og:image\"\s+content=\"(http:\/\/i.imgur.com\/(\w+)\.(gif)|(png)|(jpg)|(jpeg))\"\s+\/\>')
		
		path = '/'.join([save_dir, s.subreddit.display_name])
		match = img.search(url)
		if match is not None:
			# grab lone image
			rand_name = [random.choice(string.ascii_lowercase) for x in range(7)]

			name = ''.join([''.join(rand_name), match.group(0)])
			save_to_file(url, path, name )
		elif imgur.match(url) is not None:
			# get ogp img urls
			rq = requests.get(url)
			ogp_urls = [ a[0] for a in imgur_imgs.findall(rq.text) ]
			rand_name = [random.choice(string.ascii_lowercase) for x in range(7)]
			name = ''.join([''.join(rand_name), '_%d%s'])
			for idx, u in enumerate(ogp_urls):
				save_to_file(u, path, name % ( idx, img.search(u).group(0)))
		else:
			# print('unable to match url with a pattern: %s' % s.url)
			save_line_to_file(url, save_dir, 'skipped.txt')
			skipped +=1
	else:
		print('unable to match submission with a pattern')

def save_line_to_file(line, loc, name):
	if not os.path.exists( loc ):
		os.makedirs( loc )
	with open('/'.join([ loc, name]), 'a') as handle:
		handle.write(''.join([ line, '\n']))

def save_to_file(url, loc, name, append=False):
	global skipped
	if not os.path.exists( loc ):
		os.makedirs( loc )
	if append:
		write = 'a'
	else:
		write = 'wb'
	with open('/'.join([loc,name]), write) as handle:
		response = requests.get(url, stream=True)
		if not response.ok:
			print('download %s failed' % url)
			save_line_to_file(url, save_dir, 'skipped.txt')
			skipped +=1
		for block in response.iter_content(1024):
			if not block:
				break
			handle.write(block)

if __name__ =='__main__':

	warnings.simplefilter("ignore")

	if user == None:
		user = input('Reddit username: ')
	if passwd == None:
		passwd = getpass.getpass('password: ')

	r = praw.Reddit('Seennit v2 - downloads saved image links from Reddit user account')

	r.login(user, passwd)

	if save_dir is None:
		save_dir = input('Enter base save dir: ')
		write_to_me(r'(^save_dir =)', save_dir)

	saves_to_do = []

	params = {}
	# ordered asc by user save date not submission date

	more = True
	top = 100
	old_last = last

	while more: # while there is potentially more pages to fetch...
		more = False # no more unless we hit top in inner loop...
		saves = r.user.get_saved(params=params, limit=top) # in ascending chronological order

		count = 0
		first = ''

		for s in saves: # cycle through page...
			if s.fullname == old_last: # if we hit the previous last processed, exit...
				more = False
				print('reached last save point')
				break
			saves_to_do.append(s)
			count+=1
			# download(s)
		if count == top: # potentially more pages to fetch...
			more = True
		# one page finished, persist top last to file
		#global last = first in file above
		params['after'] = s.fullname # for new query take first record in newly processed page...
	# cycle through saves from last, saving & updating one by one...
	total = len(saves_to_do)
	current = 0
	for s in saves_to_do[::-1]:
		current += 1
		download(s)
		write_to_me(r'(^last =)', s.fullname)
		sys.stdout.write("\rprogress: %d/%d" % ( current, total))
		sys.stdout.flush()
	print('\rtotal saves processed: %d' % total)
	print('total attempted downloads missed: %d' % skipped)
