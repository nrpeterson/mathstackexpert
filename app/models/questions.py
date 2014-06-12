import pickle
from random import sample, shuffle
import numpy as np
from sklearn.svm import LinearSVC, SVC
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import precision_score, recall_score
from sklearn.pipeline import Pipeline
from app import db
from app.models.helpers import preprocess_post, is_psq
from app.database import Question, Answer
from sklearn.naive_bayes import GaussianNB, MultinomialNB, BernoulliNB
import logging
import json
import gzip
from time import sleep
from datetime import datetime as dt
from urllib.parse import urlencode
from urllib.request import urlopen
from io import BytesIO

def build_interest_classifier(userid):

    trf = TfidfVectorizer(
            ngram_range=(2,8),
            stop_words='english',
            analyzer='char'
        )

    #nb = MultinomialNB()
    #svc = LinearSVC(C=.1, class_weight='auto')
    reg = LogisticRegression()
    clf = Pipeline([('vectorizer', trf), ('logreg', reg)])
    url = "http://api.stackexchange.com/2.2/users/" + str(userid) +\
            "?order=desc&sort=reputation&site=math&" + \
            "filter=!)RwcIFg0(Qj*_TCkjEiCRnH0&key=062O6ANtxbZRHzqy56VlFw(("

    response = urlopen(url)
    buf = BytesIO(response.read())
    gz = gzip.GzipFile(fileobj=buf)
    text = gz.read().decode()
    data = json.loads(text)
    user = data['items'][0]
    join_date = dt.fromtimestamp(user['creation_date'])

    last_ans_date = Answer.query.filter(Answer.author_id==userid).\
            order_by(db.desc(Answer.creation_date)).first().creation_date

    first_ans_date = Answer.query.filter(Answer.author_id==userid).\
            order_by(Answer.creation_date).first().creation_date

    answers = Answer.query.filter(Answer.author_id==userid).\
            order_by(db.desc(Answer.creation_date))
    num_answers = answers.count()

    X_raw = []
    Y_raw = []
    qids = []
    for a in answers:
        q = a.question
        X_raw.append(q.body_html)
        Y_raw.append(1)
        qids.append(q.id)

    unans = Question.query.filter(~Question.id.in_(qids)).\
            order_by(db.desc(Question.creation_date)).limit(num_answers).all()

    for q in unans:
        X_raw.append(q.body_html)
        Y_raw.append(0)

    shuff = list(range(len(X_raw)))
    shuffle(shuff)
    X_raw = [X_raw[i] for i in shuff]
    Y_raw = [Y_raw[i] for i in shuff]
    
    test_size = round(.2*len(X_raw))
    train_size = len(X_raw) - test_size

    X_train = X_raw[:train_size]
    Y_train = np.array(Y_raw[:train_size])

    X_test = X_raw[train_size:]
    Y_test = np.array(Y_raw[train_size:])

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

    with open('questions.pickle', 'wb') as f:
        pickle.dump(clf, f)

    return clf
    

