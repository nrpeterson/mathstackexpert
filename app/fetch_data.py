import logging
import json
import gzip
from time import sleep
from datetime import datetime as dt
from urllib.parse import urlencode
from urllib.request import urlopen
from io import BytesIO
from app import app, db
from app.database import Question, Answer, get_or_create

def process_api_question(data):
    """Given data (a python object parked from the StackExchange API JSON), 
    return a matching app.database.Question object.
    """
    q = get_or_create(Question, data['question_id'])
    if 'accepted_answer_id' in data:
        q.accepted_answer_id = data['accepted_answer_id']
    if 'author' in data and 'user_id' in data['author']:
        q.author_id = data['owner']['user_id']
    q.body_html = data['body']
    q.body_markdown = data['body_markdown']
    if 'closed_date' in data:
        q.closed_date = dt.fromtimestamp(data['closed_date'])
    if 'closed_details' in data:
        q.closed_desc = data['closed_details']['description']
        q.closed_reason = data['closed_details']['reason']
    q.creation_date = dt.fromtimestamp(data['creation_date'])
    q.last_activity_date = dt.fromtimestamp(data['last_activity_date'])
    q.link = data['link']
    q.score = data['score']
    q.title = data['title']
    for tag in data['tags']:
        q.tags.append(tag)
    db.session.add(q)
    if 'answers' in data:
        for answer in data['answers']:
            a = get_or_create(Answer, answer['answer_id'])
            if 'owner' in answer and 'user_id' in answer['owner']:
                a.author_id = answer['owner']['user_id']
            a.body_html = answer['body']
            a.body_markdown = answer['body_markdown']
            a.creation_date = dt.fromtimestamp(answer['creation_date'])
            a.is_accepted = answer['is_accepted']
            a.last_activity_date = dt.fromtimestamp(
                    answer['last_activity_date'])
            a.link = answer['link']
            a.question_id = answer['question_id']
            a.score = answer['score']
            db.session.add(a)

def fetch_data(first_page = 1):
    logging.basicConfig(
            filename='fetch_data.log', 
            level=logging.INFO,
            format='%(asctime)s %(message)s'
    )

    logging.info('Fetching data from StackExchange API')
    
    base = "http://api.stackexchange.com/2.2/questions"
    params = {
        'site': 'math',
        'page': first_page,
        'pagesize': 100,
        'order': 'asc',
        'sort': 'creation',
        'filter': '!*IXk1kM1CRsCvNX-HctMr3GtJ1.gEYTy9JkKKBvy88x)lhGxe1N.aanvfrdZ)D',
        'key': '062O6ANtxbZRHzqy56VlFw(('
    }

    while True:
        url = base + '?' + urlencode(params)
        response = urlopen(url)
        buf = BytesIO(response.read())
        gz = gzip.GzipFile(fileobj=buf)
        text = gz.read().decode()
        data = json.loads(text)
        if 'items' in data:
            for item in data['items']:
                process_api_question(item)
            db.session.commit()
        logging.info("Processed page {}. Quota remaining: {}".format(
            params['page'],
            data['quota_remaining']))
        if data['quota_remaining'] == 0:
            logging.info("Reached maximum quota. Shutting down.")
            break
        if 'backoff' in data:
            logging.info("Received backoff request for {} seconds.".format(
                data['backoff']))
            sleep(data['backoff'])
        params['page'] += 1
        if not data['has_more']:
            logging.info("Reached end of query!")
            break



