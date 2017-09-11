from datetime import datetime
from dateutil.tz import *
import grequests
import gzip
import io
import re
import urllib


EVENT_REGEX = re.compile(r'^ObjectCreated:')
PUBLIC_API_LOG_REGEX = re.compile(r'^public_api_logs/')
LOG_LINE_REGEX = re.compile(r''
           '(\d+.\d+.\d+.\d+)\s-\s-\s' # IP address
           '\[(.+)\]\s+'               # datetime
           '"GET\s(.+)\s\w+/.+"\s'     # requested file
           '(\d+)\s'                   # status
           '(\d+)\s'                   # bandwidth
           '"(.+)"\s'                  # referrer
           '"(.+)"'                    # user agent
        )

import boto3
S3 = boto3.client('s3')

def handle_lambda(event, context):
    if event['Records']:
        record = event['Records'][0]
        file_created = EVENT_REGEX.match(record['eventName'])
        filename = get_filename(record)
        is_public_api_log_event = PUBLIC_API_LOG_REGEX.match(filename)
        if file_created and is_public_api_log_event:
            bucket_name = get_bucket_name(record)
            obj = S3.get_object(Bucket=bucket_name, Key=filename)
            send_events_to_GA(obj)

def get_bucket_name(record):
    return record['s3']['bucket']['name']

def get_filename(record):
    return urllib.parse.unquote(record['s3']['object']['key'])

def calculate_time_delta(timestamp):
    real_hit_time = datetime.strptime(timestamp, "%d/%b/%Y:%H:%M:%S %z")
    timedelta = datetime.now(tzutc()) - real_hit_time
    return int(timedelta.total_seconds() * 1000)

def send_events_to_GA(s3object):
    urls = []

    with io.TextIOWrapper(gzip.GzipFile(fileobj=s3object['Body'], mode='r')) as log_file:
        for line in log_file:
            match = re.search(LOG_LINE_REGEX, line)
            if match:
                ip, timestamp, path, status, _, referrer, user_agent = match.groups()
                params = urllib.parse.urlencode({
                    'v': 1,
                    'tid': 'UA-12811748-1',
                    'cid': 'No client ID',
                    't': 'event',
                    'ec': 'Public API request',
                    'ea': path or 'No path present',
                    'el': referrer or 'No referrer present',
                    'ua': user_agent or 'No user agent present',
                    'uip': ip or 'No IP address present',
                    'qt': calculate_time_delta(timestamp)
                })
                print(params)
                url = "http://www.google-analytics.com/collect?{0}".format(params)
                urls.append(url)

    rs = [grequests.post(u) for u in urls]

    return grequests.map(rs)
