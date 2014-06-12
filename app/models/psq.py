import pickle
from random import sample, shuffle
import numpy as np
from sklearn.svm import LinearSVC
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import precision_score, recall_score
from sklearn.pipeline import Pipeline
from app import db
from app.database import Question
from app.models.questions import build_interest_classifier

def build_psq_classifier():
    """Build a predictor of whether or not a question will be closed as 
    homework / for 'lack of context'.  This is accomplished by building a 
    linear SVC model, trained on old post data. 

    Pickles the classifier, an instance of sklearn.svm.LinearSVC. Also stores
    some basic data metrics.

    Note that we only use posts written after 2013-06-25, the date on which 
    the first such closure reason was instituted.
    """

    trf = TfidfVectorizer(
            ngram_range=(2,6),
            stop_words='english',
            analyzer='char'
        )

    #svc = LinearSVC(C=.1)
    reg = LogisticRegression()

    clf = Pipeline([('vectorizer', trf), ('reg', reg)])

    query = Question.query.filter(Question.creation_date < '2014-05-20').\
            filter(Question.closed_reason=='off-topic').\
            filter(Question.closed_desc.like('%context%'))

    num_closed = query.count()
    X_raw = [q.body_html for q in query]
    Y_raw = [1 for q in query]

    query = Question.query.filter(Question.creation_date < '2014-05-20').\
            filter(Question.closed_reason != 'off-topic').\
            order_by(db.desc(Question.creation_date)).limit(num_closed)

    for q in query:
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

    with open('homework.pickle', 'wb') as f:
        pickle.dump(clf, f)
