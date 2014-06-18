import logging
from calendar import timegm as timestamp
from time import sleep
from datetime import datetime as dt
from app import app, connect_db
from app.api import mse_api_call, from_timestamp
import pickle
import pymysql

logging.basicConfig(
        filename='fetch_data.log', 
        level=logging.INFO,
        format='%(asctime)s %(message)s'
)

def process_api_questions(items, check_quality=True):
    """Given items (a group of questions from the StackExchange API JSON), 
    add/update corresponding records in databases.
    """
    con = connect_db()
    cur = con.cursor()
    qids = [item['question_id'] for item in items]
    qids.sort()
    query = "SELECT id FROM questions WHERE id IN ("
    query += ','.join([str(i) for i in qids])
    query += ');'
    cur.execute(query)
    existing = [q['id'] for q in cur]
    for item in items:
        question = {
                'id': item['question_id'],
                'body_html': item['body'],
                'body_markdown': item['body_markdown'],
                'creation_date': from_timestamp(item['creation_date']),
                'last_activity_date':from_timestamp(item['last_activity_date']),
                'link': item['link'],
                'score': item['score'],
                'title': item['title'],
                'historic': True
        }
        
        if 'owner' in item:
            question['author_id'] = item['owner']['user_id']
        else:
            question['author_id'] = None

        if 'accepted_answer_id' in item:
            question['accepted_answer_id'] = item['accepted_answer_id']
        else:
            question['accepted_answer_id'] = None

        if 'closed_date' in item:
            question['closed_date'] = from_timestamp(item['closed_date'])
            question['closed_desc'] = item['closed_details']['description']
            question['closed_reason'] = item['closed_reason']
        else:
            question['closed_date'] = None
            question['closed_desc'] = None
            question['closed_reason'] = None
    
        if question['id'] not in existing:
            query = 'INSERT INTO questions ('
            query += ','.join(sorted(question.keys()))
            query += ') VALUES ('
            query += ','.join('%s' for i in range(len(question.keys())))
            query += ');'
        else:
            query = "UPDATE questions SET "
            query += ','.join(k + '=%s' for k in sorted(question.keys()))
            query += ' WHERE id=' + str(question['id']) + ';'
        cur.execute(query, [question[k] for k in sorted(question.keys())])

        query = "DELETE FROM question_tags WHERE question_id=%s"
        cur.execute(query, [question['id']])

        query = "SELECT id FROM tags WHERE tag.name IN ("
        query += ','.join(item['tags'])
        query += ");"
        cur.execute(query)
        tagids = [t['id'] for t in cur]
        query = "INSERT INTO question_tags (question_id, tag_id) VALUES (%s,%s)"
        for tagid in tagids:
            cur.execute(query, [question['id'], tagid)

        if 'answers' in item:
            answers = []
            for answer in item['answers']:
                a = {
                        'id': answer['answer_id'],
                        'body_html': answer['body'],
                        'body_markdown': answer['body_markdown'],
                        'creation_date':from_timestamp(answer['creation_date']),
                        'is_accepted': answer['is_accepted'],
                        'last_activity_date': from_timestamp(answer['last_activity_date']),
                        'link': answer['link'],
                        'question_id': answer['question_id'],
                        'score': answer['score']
                }

                if 'owner' in answer and len(answer['owner']) > 0:
                    a['author_id'] = answer['owner']['user_id']
                else:
                    a['author_id'] = None
                
                answers.append(a)
            query = "SELECT id FROM answers WHERE id IN ("
            query += ','.join(str(a['id']) for a in answers)
            query += ') ORDER BY id ASC;'
            cur.execute(query)
            existinga = [a['id'] for a in cur]
            for a in answers:
                if a['id'] not in existinga:
                    query = 'INSERT INTO answers ('
                    query += ','.join(sorted(a.keys()))
                    query += ') VALUES ('
                    query += ','.join('%s' for i in range(len(a.keys())))
                    query += ');'
                else:
                    query = 'UPDATE answers SET '
                    query += ','.join(k + '=%s' for k in sorted(a.keys()))
                    query += ' WHERE id=' + str(a['id']) + ';'
                cur.execute(query, [a[k] for k in sorted(a.keys())])

    con.commit()
    
    if check_quality:
        query = "SELECT id, body_html FROM questions WHERE id IN ("
        query += ','.join([str(i) for i in qids])
        query += ') ORDER BY id ASC;'
        cur.execute(query)
        quals = []
        bodies = [item['body_html'] for item in cur]
        
        with open('homework.pickle', 'rb') as f:
            clf = pickle.load(f)
        probs = clf.predict_proba(bodies)[:, 0]
        for i in range(len(qids)):
            query = "UPDATE questions SET quality_score=%s WHERE id=%s".format(
                    int(100*probs[i]), qids[i])
            cur.execute(query, [int(100*probs[i]), qids[i]])
        con.commit()

    con.close()

def fetch_tags():
    logging.info('Fetching tags from StackExchange API')

    con = connect_db()
    cur = con.cursor()

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
                query = "SELECT * FROM tags WHERE name=%s"
                if cur.execute(query, [item['name']]) == 0:
                    query = "INSERT INTO tags (name) VALUES (%s);"
                    cur.execute(query, [item['name']])
            con.commit()
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
            date = dt.now().strftime('%Y-%m-%d %H:%M:%S')
            logging.info("Reached end of query!")
            query = "SELECT * FROM last_updated WHERE description='questions';"
            if cur.execute(query) == 0:
                query = "INSERT INTO last_updated (description, date) VALUES(%s, %s);"
                desc = 'questions'
                cur.execute(query, [desc, date])
            else:
                query = "UPDATE last_updated SET date=%s WHERE description='questions';"
                cur.execute(query, [date])
            con.commit()
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
            date = dt.now().strftime('%Y-%m-%d %H:%M:%S')
            logging.info("Reached end of query!")
            query = "SELECT * FROM last_updated WHERE description='questions';"
            if cur.execute(query) == 0:
                query = "INSERT INTO last_updated (description, date) VALUES(%s, %s);"
                desc = 'questions'
                cur.execute(query, [desc, date])
            else:
                query = "UPDATE last_updated SET date=%s WHERE description='questions';"
                cur.execute(query, [date])
            con.commit()
            break
