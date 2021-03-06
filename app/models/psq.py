import pickle
from time import time
import numpy as np
from sklearn.grid_search import GridSearchCV
from sklearn.cross_validation import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import precision_score, recall_score, f1_score
from sklearn.pipeline import Pipeline
from app import connect_db
from app.api import from_timestamp
from app.models.helpers import preprocess_post

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

    reg = LogisticRegression()

    clf = Pipeline([('vectorizer', trf), ('reg', reg)])
    
    X_raw = []
    Y_raw = []

    # Fetch closed questions from database
    query = """SELECT * FROM questions WHERE creation_date < '{}' AND 
               closed_reason='off-topic' AND (closed_desc LIKE '%context%'
               OR closed_desc LIKE '%homework%');""".format(end_date_str)

    cur.execute(query)

    for q in cur:
        X_raw.append(q['body_html'])
        Y_raw.append(1)

    num_closed = len(X_raw)

    # Fetch an equal number of un-closed questions
    query = """SELECT * FROM questions WHERE creation_date < %s AND 
               closed_reason IS NULL ORDER BY creation_date LIMIT %s"""
    
    cur.execute(query, [end_date_str, num_closed])

    for q in cur:
        X_raw.append(q['body_html'])
        Y_raw.append(0)
    
    X_raw = [X_raw[i] for i in shuff]
    Y_raw = [Y_raw[i] for i in shuff]
   

    # Hold back 20% of examples as test set
    X_train, X_test, Y_train, Y_test = train_test_split(
            X_raw, Y_raw, test_size=0.2)

    test_size = len(X_test)
    train_size = len(X_train)

    # Perform grid search to tune parameters for F1-score
    params = [
            {
                'vectorizer__ngram_range': [(2,2), (2,4), (2,6), (2,8)],
                'reg__penalty': ['l1', 'l2'],
                'reg__C': [.01, .03, .1, .3, 1, 3, 10, 30, 100],
                'reg__intercept_scaling': [.1,1,10,100]
            }
        ]


    gridsearch = GridSearchCV(clf, params, scoring='f1', n_jobs=4, \
            pre_dispatch=8)

    gridsearch.fit(X_train, Y_train)
    clf = gridsearch.best_estimator_
    print("Done training classifier!")
    print("Parameters from CV:")
    for k,v in gridsearch.best_params_.items():
        print("{}: {}".format(k,v))
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
