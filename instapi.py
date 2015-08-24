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
# from numpy import NaN
import pandas as pd
from sys import maxint

class BadClientID(Exception):
    """Raised when provided Instagram API key is bad/not provided."""
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class InstAPI:
    def __init__(self, clientid):
        # evaluate if provided clientid is valid
        if not clientid:
            raise BadClientID('No API key provided.')
        if len(clientid) != 32:
            raise BadClientID('The provided API key is too long/short.')

        self.clientid = clientid

    # def endpoint_media(self, params, n=NaN, per_request=40, verbose=None):
    #     # initialize variables
    #     posts = []
    #     post_count, verbose_count, number_of_requests = (0, 1.0, 0)
    #     start_time = time.time()
    #     endpoint = '/media/search'
    #     n = int(n)

    #     if 'min_timestamp' in params:
    #         min_timestamp = int(params['min_timestamp'])
    #         params.pop('min_timestamp')
    #         # reset the number of posts to NaN
    #         n = NaN
    #     else:
    #         min_timestamp = NaN

    #     if 'max_timestamp' in params:
    #         maxage = int(params['max_timestamp'])
    #         params.pop('max_timestamp')
    #     else:
    #         # current date
    #         maxage = int(time.time())

    #     # set up an url with parameters passed
    #     extra_params = {'client_id':self.clientid, 'count':per_request}
    #     params = dict(params, **extra_params)
    #     base_url = 'https://api.instagram.com/v1' + endpoint + '?' + \
    #         urllib.urlencode(params)

    #     # while not enough posts have been gathered
    #     while (post_count < n) or (min_timestamp < maxage):
    #         # the next URL to request
    #         next_url = self._next_url_from_timestamp(base_url, maxage)

    #         # print log info
    #         if verbose is True:
    #             print 'got {0}/{1} posts, now using URL: .../{2}'.format(
    #                 len(posts), n, next_url.split('/')[-1])

    #         # request next set of posts and get maxage of the oldest post
    #         current_request = self._do_request(next_url)
    #         maxage = int(current_request['data'][-1]['created_time'])

    #         # add posts to list that will be returned
    #         posts_in_call = len(current_request['data'])
    #         posts_needed = n - post_count
    #         if (posts_needed - posts_in_call) < 0:
    #             # there are more posts in this call than there are still needed
    #             posts.extend(current_request['data'][:posts_needed])
    #         elif maxage < min_timestamp:
    #             # only add posts till min_timestamp is reached
    #             for post in current_request['data']:
    #                 maxage = int(post['created_time'])
    #                 if min_timestamp < maxage:
    #                     posts.append(post)
    #                 else:
    #                     break
    #         else:
    #             # far more to go, use all posts in this request
    #             posts.extend(current_request['data'])

    #         post_count += posts_in_call
    #         number_of_requests += 1

    #     # print some final info
    #     print "\nDONE REQUESTING %s POSTS FROM API IN %s REQUESTS\n" % \
    #         (len(posts), number_of_requests)
    #     print "That means about %.2f posts per request" % \
    #         (float(len(posts)) / number_of_requests)
    #     print "API calls took %.2fs" % (time.time() - start_time)

    #     return posts

    def endpoint_tag(self, tag, n, func=None, params={}, verbose=True, outfile=None,
            per_request=40):
        """API wrapper for /tags/{hashtag}/media/recent endpoint. If outfile is
        specified the output will be saved as CSV; otherwise a list will be
        returned.

        tag (str): hashtag to look up
        n (int): number of posts to retrieve
        func (function): function name to which the list of posts will be passed
            before it is returned or saved to outfile. Use this function to filter
            out the data from the request. See `extract_url_timestamp_likes` for an
            example function.
        params (dict): extra parameters to pass to the URL
        verbose (bool): prints output to stdout if True
        outfile (str): name of file the output should be saved to
        per_request (int): number of posts to retrieve per request. Usually
            capped at around 33 by the API
        """
        posts = []
        post_count, number_of_requests = (0, 0)
        start_time = time.time()
        endpoint = '/tags/%s/media/recent' % tag
        n = int(n)

        # create file named same as outfile but with .log extension
        if outfile:
            url_log = ".".join(outfile.split('.')[:-1]) + '_url.log'
            logfile = ".".join(outfile.split('.')[:-1]) + '.log'
            # check if file already exists and get values for post_count and
            # number_of_requests for this continued run
            if os.path.isfile(logfile):
                f = open(logfile, 'r')
                log_post_count = f.readline()
                log_number_of_requests = f.readline()
                post_count = int(log_post_count.split(':')[-1])
                number_of_requests = int(log_number_of_requests. \
                    split(':')[-1])
                f.close()

        # either construct a URL or get it from the log
        if os.path.isfile(url_log):
            # get last url from log file
            next_url = _tail(url_log)
        else:
            # set up an url with parameters passed
            extra_params = {'client_id':self.clientid, 'count':per_request}
            params = dict(params, **extra_params)
            next_url = 'https://api.instagram.com/v1' + endpoint + '?' + \
                urllib.urlencode(params)

        # while not enough posts have been gathered
        while (post_count < n):
            # print info to stdout
            if verbose is True:
                print 'got {0}/{1} posts, now using URL: .../{2}'.format(
                    post_count, n, next_url.split('/')[-1])

            # request next posts, if it fails break loop
            current_request = self._do_request(next_url)
            if not current_request:
                print "API LIMIT REACHED."
                break

            if func:
                data = func(current_request['data'])
            else:
                data = current_request['data']

            next_url = current_request['pagination']['next_url']
            if url_log:
                # append next_url to url logfile
                with open(url_log, 'a') as f:
                    f.write(next_url+'\n')

            # add posts to list that will be returned, but only when no outfile
            # is specified. Otherwise append posts to outfile
            posts_in_call = len(current_request['data'])
            posts_needed = n - post_count
            if not outfile:
                if (posts_needed - posts_in_call) < 0:
                    # there are more posts in this call than there are needed
                    posts.extend(data[:posts_needed])
                else:
                    # far more to go, use all posts in this request
                    posts.extend(data)

            if outfile:
                df = pd.DataFrame(data)
                with open(outfile, 'a') as f:
                    df.to_csv(f, index=False, header=False)

            post_count += posts_in_call
            number_of_requests += 1

            # update numbers in logfile
            if logfile:
                with open(logfile, 'w') as f:
                    f.write("post count: {}\nnumber of requests: {}".format(
                        post_count, number_of_requests))

        # print some final info
        print "\nDONE REQUESTING %s POSTS FROM API IN %s REQUESTS\n" % \
            (post_count, number_of_requests)
        print "That means about %.2f posts per request" % \
            (float(post_count) / number_of_requests)
        print "API calls took %.2fs" % (time.time() - start_time)

        if not outfile:
            return posts

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

def timestamp2date(timestamp):
    """Returns datetime.datetime object of the machine's local time"""
    return datetime.datetime.fromtimestamp(int(timestamp))

def date2timestamp(date_):
    """Returns timestamp as int. Takes date in dd.mm.yyyy format"""
    return int(time.mktime(time.strptime(date_, '%d.%m.%Y')))

def _tail(f):
    """Returns last line of file f as str"""
    stdin,stdout = os.popen2("tail -n 1 {}".format(f))
    stdin.close()
    lines = stdout.readlines(); stdout.close()
    return str(lines[-1])

if __name__ == "__main__":
    pass