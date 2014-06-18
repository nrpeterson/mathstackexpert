import pickle
import os.path
from random import sample, shuffle
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import precision_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.cross_validation import train_test_split
from app import connect_db
from app.models.helpers import preprocess_post, is_psq
import logging
from time import sleep
from datetime import datetime as dt
from app.api import mse_api_call, from_timestamp

def build_interest_classifier(userid, recreate=False):
    filename = ''.join(['data/', str(userid), '.pickle'])
    if not recreate and os.path.exists(filename):
        print("Using cached classifier.")
        with open(filename, 'rb') as f:
            clf = pickle.load(f)
        return clf

    print("Building new interest classifier.")
    trf = TfidfVectorizer(
            ngram_range=(2,8),
            stop_words='english',
            analyzer='char',
            preprocessor=preprocess_post
        )

    reg = LogisticRegression()
    clf = Pipeline([('vectorizer', trf), ('logreg', reg)])

    func = '/users/' + str(userid)
    params = {
            'order': 'desc',
            'sort': 'reputation',
            'filter': '!)RwcIFg0(Qj*_TCkjEiCRnH0'
            }
    data = mse_api_call(func, params)
    user = data['items'][0]
    join_date = dt.fromtimestamp(user['creation_date'])
    
    con = connect_db()
    cur = con.cursor()

    query = """SELECT creation_date FROM answers ORDER BY creation_date DESC 
               LIMIT 1;"""
    cur.execute(query)
    last_ans_date = from_timestamp(cur.fetchone()['creation_date'])

    query = """SELECT creation_date FROM answers ORDER BY creation_date ASC 
               LIMIT 1;"""
    cur.execute(query)
    first_ans_date = from_timestamp(cur.fetchone()['creation_date'])

    query = """SELECT * FROM answers WHERE author_id=%s ORDER BY creation_date
               DESC"""
    cur.execute(query, [userid])
     
    answers = Answer.query.filter(Answer.author_id==userid).\
            order_by(db.desc(Answer.creation_date))

    X_raw = []
    Y_raw = []
    qids = []
    
    for a in cur:
        qids.append(a['question_id'])

    query = """SELECT * FROM questions WHERE id IN ("""
    query += ','.join(str(qid) for qid in qids)
    query += """);"""

    cur.execute(query)
    for q in cur:
        X_raw.append(q['body_html'])
        Y_raw.append(1)
   
    num_answers = len(qids)

    query = """SELECT * FROM questions WHERE id NOT IN ("""
    query += ','.join(str(qid) for qid in qids)
    query += ") ORDER BY creation_date DESC LIMIT %s;"
    cur.execute(query, num_answers)

    for q in cur:
        X_raw.append(q.body_html)
        Y_raw.append(0)
    
    X_train, X_test, Y_train, Y_test = train_test_split(
            X_raw, Y_raw, test_size=0.2)
    
    train_size = len(X_train)
    test_size = len(X_test)

    clf.fit(X_train, Y_train)

    print("Done training classifier!")
    preds = clf.predict(X_test)
    print("Done making predictions for test set.")
    print("Results:")

    clf.stats = dict()
    clf.stats['train_size'] = train_size
    clf.stats['train_pos'] = np.sum(Y_train)
    clf.stats['train_neg'] = train_size - np.sum(Y_train)
    clf.stats['test_size'] = test_size
    clf.stats['test_pos'] = np.sum(Y_test)
    clf.stats['test_neg'] = test_size - np.sum(Y_test)
    clf.stats['accuracy'] = clf.score(X_test, Y_test)
    clf.stats['precision'] = precision_score(Y_test, preds)
    clf.stats['recall'] = recall_score(Y_test, preds)
    for k in clf.stats:
        print("  {}: {}".format(k, clf.stats[k]))

    with open(filename, 'wb') as f:
        pickle.dump(clf, f)

    query = """SELECT * FROM last_updated WHERE description=%s"""
    date = dt.now.strftime('%Y-%m-%d %H:%M:%S')
    if cur.execute(query, userid) > 0:
        query = "UPDATE last_updated SET date=%s WHERE description=%s;"
    else:
        query = "INSERT INTO last_updated (date, description) VALUES (%s, %s);"
    cur.execute(query, date, userid)
    con.commit()

    print("Done!")
        
    return clf
    

