# AUTHOR:   Rene Ludwig
# DATE:     15.08.2015
# GITHUB:   https://github.com/rldw
# MAIL:     rene.ludwig@hhu.de

import urllib
import requests
import json
import datetime
import time
import os
import pandas as pd
from sys import maxint

class BadClientID(Exception):
    """Raised when provided Instagram API key is bad/not provided."""
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class InstAPI:
    def __init__(self, clientids):
        # evaluate if provided clientid is valid
        if not clientids:
            raise BadClientID('No API key(s) provided.')
        if type(clientids) is not list:
            clientids = [clientids]
        for clientid in clientids:
            if len(clientid) != 32:
                raise BadClientID('Invalid length for key: %s' % clientid)

        self.clientids = clientids

    @classmethod
    def load_clientids(cls, filename):
        """Initialize class with clientids that are stored in csv file.
        """
        with open(filename, 'r') as f:
            content = f.read()
        ids = [x.strip() for x in content.split(',')]
        return cls(ids)

    def endpoint_tag(self, tag, n, func=None, params={}, outfile=None):
        """API wrapper for /tags/{hashtag}/media/recent endpoint. If outfile is
        specified the output will be saved as CSV; otherwise a list will be
        returned.

        tag (str): hashtag to look up
        n (int): number of posts to retrieve
        func (function): function name to which the list of posts will be passed
            before it is returned or saved to outfile. Use this function to
            filter out the data from the request. See
            `extract_url_timestamp_likes` for an example function.
        params (dict): extra parameters to pass to the URL
        outfile (str): name of file the output should be saved to
        """
        posts = []
        post_count, number_of_requests, per_request = (0, 0, 40)
        start_time, elapsed_time = (time.time(), 0)
        endpoint = '/tags/%s/media/recent' % tag
        n = int(n)

        if not outfile:
            outfile = "{}_{}_{}.csv".format(start_time, tag, n)

        # create files named same as outfile with (_url).log extension
        url_log = ".".join(outfile.split('.')[:-1]) + '_url.log'
        logfile = ".".join(outfile.split('.')[:-1]) + '.log'

        # check if file already exists and get values for post_count,
        # number_of_requests and the elapsed time for this continued run
        if os.path.isfile(logfile):
            post_count, number_of_requests, elapsed_time = self._parse_logfile(logfile)
            #print "CONTINUING RUN FROM {} POSTS\n".format(post_count)

        if post_count >= n:
            print "Already downloaded and saved {} posts to {}".format(
                post_count, outfile)
            return

        # either construct a URL or get it from the log
        if os.path.isfile(url_log):
            # get last url from log file
            next_url = _tail(url_log)
        else:
            # set up an url with parameters passed
            extra_params = {'client_id':self.clientids[0], 'count':per_request}
            params = dict(params, **extra_params)
            next_url = 'https://api.instagram.com/v1' + endpoint + '?' + \
                urllib.urlencode(params)

        # while not enough posts have been gathered
        while (post_count < n):
            # print some information every x requests
            if number_of_requests % 10 == 0 or number_of_requests == 0:
                print '#{}: got {}/{} posts, now using URL: .../{}'.format(
                    number_of_requests, post_count, n, next_url.split('/')[-1])

            # request next posts, if it fails use next clientid or break loop
            current_request = self._do_request(next_url)
            if (not current_request and len(self.clientids) > 1):
                nextid = self.clientids.pop(0)
                self.clientids.append(nextid)
                print "\n\nAPI LIMIT REACHED. USING NEXT CLIENTID: %s\n\n" % \
                    nextid
                # replace client_id in next_url and skip current iteration
                pos = next_url.find('client_id=')
                pos += len('client_id=')
                oldid = next_url[pos:pos+32]
                next_url = next_url.replace(oldid, nextid)
                continue
            elif not current_request:
                print "\nAPI LIMIT REACHED. ONLY ONE CLIENTID PROVIDED.\n"
                break

            # if a data processing function is passed, pass the requested data
            # to it otherwise use all of the requested data retured by the API
            if func:
                data = func(current_request['data'])
            else:
                data = current_request['data']

            next_url = current_request['pagination']['next_url']
            number_of_requests += 1
            # append next_url to url logfile
            with open(url_log, 'a') as f:
                f.write(next_url+'\n')

            # append posts to outfile
            posts_in_call = len(current_request['data'])
            posts_needed = n - post_count
            if (posts_needed - posts_in_call) < 0:
                # there are more posts in this call then there are needed
                df = pd.DataFrame(data[:posts_needed])
                post_count += posts_needed
            else:
                # far more to go
                df = pd.DataFrame(data)
                post_count += posts_in_call

            with open(outfile, 'a') as f:
                df.to_csv(f, index=False, header=False)

            # update numbers in logfile
            with open(logfile, 'w') as f:
                total_time = elapsed_time + (time.time() - start_time)
                f.write("post count: {}\nnumber of requests: {}\ntime (s): {}\n" \
                    .format(post_count, number_of_requests, total_time))

        # print some final info
        posts_per_request = float(post_count) / number_of_requests
        time_needed = time.time() - start_time
        oldest_timestamp = current_request['data'][-1]['created_time']
        oldest_post = timestamp2date(oldest_timestamp)

        print "\nDONE REQUESTING %s POSTS FROM API IN %s REQUESTS\n" % \
            (post_count, number_of_requests)
        print "That means about %.2f posts per request" % posts_per_request
        print "API calls took %.2fs" % time_needed
        print "Total time for all runs %.2fs" % total_time
        print "Oldest post is from %s" % oldest_post

        # log final information
        with open(logfile, 'a') as f:
            f.write("Oldest post: %s\n" % oldest_post)

    def get_coordinates(self, location):
        """Looks up lat and lng values from Google Maps API for the given
        location and returns the values as (lat, lng) tuple.
        """
        location = urllib.pathname2url(location)
        base_url = 'https://maps.googleapis.com/maps/api/geocode/json?address='
        maps_url = base_url + location
        r = requests.get(maps_url)
        temp = json.dumps(r.json())
        js = json.loads(temp)

        lat = js['results'][0]['geometry']['location']['lat']
        lng = js['results'][0]['geometry']['location']['lng']
        return lat, lng

    def _parse_logfile(self, logfile):
        """Parses post count and number of requests stored in logfile and
        returns them as (post_count, number_of_requests) tuple.
        """
        f = open(logfile, 'r')
        post_count = int(f.readline().split(':')[-1])
        number_of_requests = int(f.readline().split(':')[-1])
        elapsed_time = float(f.readline().split(':')[-1])
        f.close()
        return (post_count, number_of_requests, elapsed_time)

    def _do_request(self, url):
        """Sends HTTP request to URL and returns dict if the request was
        successful. Otherwise returns False.
        """
        r = requests.get(url)
        # status code 429 is returned by Instagram API if limit is reached
        if r.status_code == 429:
            return False
        return json.loads(json.dumps(r.json()))

    def _next_url_from_timestamp(self, base_url, maxage):
        """Generates the next URL for /media/search endpoint"""
        return base_url + '&max_timestamp=' + str(maxage)


def extract_url_timestamp_likes(posts):
    """Extracts imgage urls, timestamps and number of likes from list
    returned by endpoint_* function as list
    """
    output = []
    for post in posts:
        image = post['images']['standard_resolution']['url']
        timestamp = post['created_time']
        likes = post['likes']['count']
        output.append([image, timestamp, likes])
    return output

def timestamp2datetime(timestamp):
    """Returns datetime.datetime object of the machine's local time"""
    return datetime.datetime.fromtimestamp(int(timestamp))

def timestamp2date(timestamp, format="%d.%m.%Y %H:%M"):
    """Returns date in given format, standard is '%d.%m.%Y %H:%M'"""
    dt = datetime.datetime.fromtimestamp(int(timestamp))
    rtn = dt.strftime(format)
    return rtn

def date2timestamp(date_):
    """Returns timestamp as int. Takes date in dd.mm.yyyy format"""
    return int(time.mktime(time.strptime(date_, '%d.%m.%Y')))

def _tail(f):
    """Returns last line of file f as str"""
    stdin,stdout = os.popen2("tail -n 1 {}".format(f))
    stdin.close()
    lines = stdout.readlines(); stdout.close()
    return str(lines[-1]).strip()