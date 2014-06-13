import json
import gzip
from urllib.parse import urlencode
from urllib.request import urlopen
from io import BytesIO


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
