import argparse
from instapi import InstAPI

# parse command line arguments
parser = argparse.ArgumentParser(description='Request n posts from Instagram API with specified hashtag.')
parser.add_argument('-n','--number', required=True,
	help='number of posts to request')
parser.add_argument('-t','--tag', required=True,
	help='hashtag to search for')
parser.add_argument('-k','--keyfile', required=True,
	help='CSV file with Instagram API keys / client IDs')
parser.add_argument('-o','--outfile', required=False,
	help='CSV file to save data to.')
args = parser.parse_args()

def data_processing(posts):
	output = []
	for post in posts:
	    timestamp = post['created_time']
	    likes = post['likes']['count']
	    output.append([timestamp, likes])
	return output

# DOWNLOAD N POSTS WITH SPECIFIC TAG
api = InstAPI.load_clientids(args.keyfile)

tag = args.tag
n = args.number
filename = args.outfile

posts = api.endpoint_tag(tag, n, outfile=filename, func=data_processing)