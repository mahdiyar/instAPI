import argparse
import time
import pandas as pd
import instapi

# parse command line arguments
parser = argparse.ArgumentParser(description='Request n posts from Instagram API with specified hashtag. Saved them to a file called {hashtag}_{n}_{timestamp}.csv.')
parser.add_argument('-n','--number', required=True,
	help='number of posts to request')
parser.add_argument('-t','--tag', required=True,
	help='hashtag to search for')
parser.add_argument('-k','--apikey', required=True,
	help='Instagram API key / client ID')
args = parser.parse_args()

# DOWNLOAD N POSTS WITH SPECIFIC TAG
api = instapi.InstAPI(args.apikey)

tag = args.tag
n = args.number
filename = '%s_%s_posts.csv' % (tag, n)

posts = api.endpoint_tag(tag, n, outfile=filename)