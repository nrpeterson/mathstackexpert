from time import sleep
from datetime import datetime as dt
import pickle
from flask import render_template, request, g
from app import app, db
from app.models.questions import build_interest_classifier
from app.database import Question
from app.api import mse_api_call

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/list/', methods=['POST'])
def list():
    userid = request.form['userid']
    quality = 50
    if 'quality' in request.form:
        quality = request.form['quality']


    clf = build_interest_classifier(userid)
    with open('homework.pickle', 'rb') as f:
        psq = pickle.load(f)

    func = '/users/' + str(userid)
    params = {'filter':'!)RwcIFN1K)cI6Nxx4kqWciTW'}
    data = mse_api_call(func, params)
    if 'items' not in data or 'user_id' not in data['items'][0]:
        return redirect(url_for('index', error="user"))
    user = data['items'][0]

    qlist = Question.query.filter(Question.quality_score != None)
    qlist = qlist.filter(Question.quality_score >= quality)
    if 'onlyunanswered' in request.form and request.form['onlyunanswered'] == 'yes':
        qlist = qlist.filter(Question.accepted_answer_id == None)
    qlist = qlist.order_by(db.desc(Question.last_activity_date))
    qlist = qlist.limit(30)

    questions = [
            {
                'title':q.title,
                'body':q.body_html,
                'link':q.link,
                'quality':q.quality_score,
                'creation_date':q.creation_date.strftime('%c'),
                'last_activity_date':q.last_activity_date.strftime('%c')
            } for q in qlist]

    interests = clf.predict_proba([q['body'] for q in questions])[:,1]
    for i in range(len(questions)):
        questions[i]['interest'] = int(100*interests[i])

    questions.sort(key=lambda q: q['interest'], reverse=True)
    
    return render_template('list.html', questions=questions, user=user, psqstats=psq.stats, clfstats=clf.stats)

