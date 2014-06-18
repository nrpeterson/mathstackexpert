import pickle
from random import sample, shuffle
from time import time
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import precision_score, recall_score
from sklearn.pipeline import Pipeline
from app import connect_db
from app.models.helpers import preprocess_post
from app.api import from_timestamp

def build_psq_classifier(end_date_str=None):
    """Build a predictor of whether or not a question will be closed as 
    homework / for 'lack of context'.  This is accomplished by building a 
    linear SVC model, trained on old post data. 

    If end_date_str isn't specified, it is initialized to two weeks prior.

    Pickles the classifier, an instance of sklearn.svm.LinearSVC. Also stores
    some basic data metrics.

    Note that we only use posts written after 2013-06-25, the date on which 
    the first such closure reason was instituted.
    """

    if end_date_str == None:
        ts = time() - 60 * 60 * 24 * 14
        end_date_str = from_timestamp(ts)

    con = connect_db()
    cur = con.cursor()

    trf = TfidfVectorizer(
            ngram_range=(2,6),
            stop_words='english',
            analyzer='char',
            preprocessor=preprocess_post
        )

    #svc = LinearSVC(C=.1)
    reg = LogisticRegression()

    clf = Pipeline([('vectorizer', trf), ('reg', reg)])
    
    X_raw = []
    Y_raw = []

    query = """SELECT * FROM questions WHERE creation_date < '{}' AND 
               closed_reason='off-topic' AND (closed_desc LIKE '%context%'
               OR closed_desc LIKE '%homework%');""".format(end_date_str)

    cur.execute(query)

    for q in cur:
        X_raw.append(q['body_html'])
        Y_raw.append(1)

    num_closed = len(X_raw)

    query = """SELECT * FROM questions WHERE creation_date < %s AND 
               closed_reason IS NULL ORDER BY creation_date LIMIT %s"""
    
    cur.execute(query, [end_date_str, num_closed])

    for q in cur:
        X_raw.append(q['body_html'])
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

    with open('psq.pickle', 'wb') as f:
        pickle.dump(clf, f)
