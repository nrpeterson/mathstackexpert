from datetime import datetime as dt
from datetime import timedelta
from time import mktime
from app import connect_db
from app.fetch_data.lastupdated import get_last_updated, set_last_updated
from app.api import process_each_page, from_timestamp
import pickle


def insert_tags(items):
    """Insert tags into the database, if they don't already exist.

    items -- the 'items' object returned from the StackExchange API when
    querying for tags.
    """
    for item in items:
        query = "SELECT * FROM tags WHERE name='%s'"
        if cur.execute(query, [item['name']]) == 0:
            query = "INSERT INTO tags (name) VALUES ('%s');"
            cur.execute(query, [item['name']])
    con.commit()


def fetch_tags():
    """Grab all tags from Math.StackExchange, and add to our database."""
    con = connect_db()
    cur = con.cursor()

    func = "/tags"
    params = {
        'pagesize': 100,
        'order': 'asc',
        'sort': 'name'
    }
    
    process_each_page(func, params, insert_tags)


def fetch_questions_and_answers():
    """Grab all questions/answers from Math.StackExchange and add to our db."""
    func = "/questions"
    params = {
        'pagesize': 100,
        'order': 'asc',
        'sort': 'creation',
        'filter': '!*IXk1kM1CRsCvNX-HctMr3GtJ1.gEYTy9JkKKBvy88x)lhGxe1N.aanvfrdZ)D'
    }
    process_each_page(func, params, \
            lambda x: process_api_questions(x, check_quality=False))
    set_last_updated() 


def fetch_recent_questions():
    """Grab recent questions/answers from Math.StackExchange and update DB.

    "Recent" is defined as "since the last update".
    """
    ts = get_last_updated()
    if ts == dt.fromtimestamp(0):
        ts = dt.fromtimestamp(60*60*8)
    func = "/questions"
    params = {
            'pagesize': 100,
            'order': 'desc',
            'fromdate': int(mktime((ts - timedelta(hours=8)).timetuple())),
            'sort': 'activity',
            'filter': '!*IXk1kM1CRsCvNX-HctMr3GtJ1.gEYTy9JkKKBvy88x)lhGxe1N.aanvfrdZ)D'
    }
    process_each_page(func, params, process_api_questions)
    
    set_last_updated()


def process_api_questions(items, check_quality=True):
    """Add question/answer list to the database.

    items -- 'items' object returned from Math.SE query against questions with
             specific filters set (as in fetch_recent_questions)
    check_quality -- if True, questions are run through the effort predictor
    """
    if len(items) == 0:
        return
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
        
        if 'owner' in item and len(item['owner']) > 0:
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

        query = "SELECT id FROM tags WHERE tags.name IN ("
        query += ','.join("'{}'".format(t) for t in item['tags'])
        query += ");"
        cur.execute(query)
        tagids = [t['id'] for t in cur]
        query = "INSERT INTO question_tags (question_id, tag_id) VALUES (%s,%s)"
        for tagid in tagids:
            cur.execute(query, [question['id'], tagid])

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
        
        with open('psq.pickle', 'rb') as f:
            clf = pickle.load(f)
        probs = clf.predict_proba(bodies)[:, 0]
        for i in range(len(qids)):
            query = "UPDATE questions SET quality_score=%s WHERE id=%s".format(
                    int(100*probs[i]), qids[i])
            cur.execute(query, [int(100*probs[i]), qids[i]])
        con.commit()

    con.close()
