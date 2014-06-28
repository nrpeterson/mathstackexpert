import json
import gzip
from datetime import datetime as dt
from urllib.parse import urlencode
from urllib.request import urlopen
from io import BytesIO

def from_timestamp(ts):
    return dt.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

def mse_api_call(func, params):
    """Fetches (and decodes/parses) API data from Math.StackExchange."""
    base = 'http://api.stackexchange.com/2.2'
    if func[0] != '/':
        func = '/' + func

    if 'key' not in params:
        params['key'] = '062O6ANtxbZRHzqy56VlFw((' 

    if 'site' not in params:
        params['site'] = 'math'

    url = ''.join([base,func,'?',urlencode(params)])
    response = urlopen(url)
    buf = BytesIO(response.read())
    gz = gzip.GzipFile(fileobj=buf)
    text = gz.read().decode()
    data = json.loads(text)
    return data

def process_each_page(func, params, proc):
    params['page'] = 1
    while True:
        data = mse_api_call(func, params)
        if 'items' in data:
            proc(data['items'])
        
        if data['quota_remaining'] == 0:
            logging.info("Reached maximum quota. Shutting down.")
            break
        
        if 'backoff' in data:
            logging.info("Received backoff request for {} seconds.".format(
                data['backoff']
            ))
            sleep(data['backoff'])
        params['page'] += 1
        if not data['has_more']:
            break
