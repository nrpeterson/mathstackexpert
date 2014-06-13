import logging
from calendar import timegm as timestamp
from time import sleep
from datetime import datetime as dt
from app import app, db
from app.database import Question, Answer, get_or_create, Tag
from app.database import TagSynonym, get_or_create_tag, LastUpdated
from app.api import mse_api_call
import pickle

logging.basicConfig(
        filename='fetch_data.log', 
        level=logging.INFO,
        format='%(asctime)s %(message)s'
)

def process_api_questions(items, check_quality=True):
    """Given items (a group of questions from the StackExchange API JSON), 
    add corresponding Question and Answer objects to db.session.
    """
    questions = []
    
    for question in items:
        q = get_or_create(Question, question['question_id'])
        db.session.add(q)
        
        if 'accepted_answer_id' in question:
            q.accepted_answer_id = question['accepted_answer_id']
        
        if 'author' in question and 'user_id' in question['author']:
            q.author_id = question['owner']['user_id']
        
        q.body_html = question['body']
        
        q.body_markdown = question['body_markdown']
        
        q.historic = True
        
        if 'closed_date' in question:
            q.closed_date = dt.fromtimestamp(question['closed_date'])
        if 'closed_details' in question:
            q.closed_desc = question['closed_details']['description']
            q.closed_reason = question['closed_details']['reason']
        q.creation_date = dt.fromtimestamp(question['creation_date'])
        q.last_activity_date = dt.fromtimestamp(question['last_activity_date'])
        q.link = question['link']
        q.score = question['score']
        q.title = question['title']
        for tag in question['tags']:
            q.tags.append(tag)

        questions.append(q)
    
        if 'answers' in question:
            for answer in question['answers']:
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
    
    if check_quality:
        print("Checking quality of {} questions.".format(len(questions)))
        with open('homework.pickle', 'rb') as f:
            psq_clf = pickle.load(f)
    
        probs = psq_clf.predict_proba([q.body_html for q in questions])
        for i in range(len(questions)):
            questions[i].quality_score = int(100*probs[i,0])

    db.session.commit()

def fetch_tags_and_synonyms():
    logging.info('Fetching tags and synonyms from StackExchange API')
    logging.info('First: tags')

    func = "/tags"
    params = {
        'page': 1,
        'pagesize': 100,
        'order': 'asc',
        'sort': 'name'
    }

    while True:
        data = mse_api_call(func, params)
        if 'items' in data:
            for item in data['items']:
                tag = get_or_create_tag(item['name'])
                tag.has_synonyms = item['has_synonyms']
                db.session.add(tag)
            db.session.commit()
        logging.info('Processed page {}. Quota remaining: {}'.format(
            params['page'],
            data['quota_remaining']
        ))
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
            logging.info("Reached end of query!")
            break
    
    logging.info("Next: synonyms.")

    func = '/tags/synonyms'
    params = {
        'page': 1,
        'pagesize': 100,
        'order': 'asc',
        'sort': 'creation'
    }

    while True:
        data = mse_api_call(func, params)
        if 'items' in data:
            for item in data['items']:
                syn = TagSynonym()
                syn.from_tag_name = item['from_tag']
                syn.to_tag_id = get_or_create_tag(item['to_tag']).id
                db.session.add(syn)
            db.session.commit()
        
        logging.info('Processed page {}. Quota remaining: {}'.format(
            params['page'],
            data['quota_remaining']
        ))
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
            logging.info("Reached end of query!")
            break

def fetch_questions_and_answers(first_page = 1):
    logging.info('Fetching data from StackExchange API')
    
    func = "/questions"
    params = {
        'page': first_page,
        'pagesize': 100,
        'order': 'asc',
        'sort': 'creation',
        'filter': '!*IXk1kM1CRsCvNX-HctMr3GtJ1.gEYTy9JkKKBvy88x)lhGxe1N.aanvfrdZ)D'
    }

    while True:
        data = mse_api_call(func, params)
        if 'items' in data:
            process_api_questions(data['items'], check_quality=False)
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
            last_updated = LastUpdated.query.\
                    filter_by(description='questions').first()
            if not last_updated:
                last_updated = LastUpdated()
                last_updated.description = 'questions'
            last_updated.date = dt.now() 
            db.session.add(last_updated)
            db.session.commit()
            break

def fetch_recent_questions():
    logging.info('Fetching recent questions...')
    q = LastUpdated.query.filter_by(description='questions').first()
    if not q:
        q = LastUpdated()
        q.description = 'questions'
        q.date = dt.fromtimestamp(0)

    func = "/questions"
    params = {
            'page': 1,
            'pagesize': 100,
            'order': 'desc',
            'fromdate': timestamp(q.date.utctimetuple()) - 60,
            'sort': 'activity',
            'filter': '!*IXk1kM1CRsCvNX-HctMr3GtJ1.gEYTy9JkKKBvy88x)lhGxe1N.aanvfrdZ)D'
    }
    
    while True:
        data = mse_api_call(func, params)
        if 'items' in data:
            process_api_questions(data['items'])
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
            q.date = dt.now()
            db.session.add(q)
            db.session.commit()
            break
