from time import sleep
from datetime import datetime as dt
import pickle
import os
from flask import render_template, request, g
from app import app, get_db
from app.models.questions import build_interest_classifier
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
    with open('psq.pickle', 'rb') as f:
        psq = pickle.load(f)

    func = '/users/' + str(userid)
    params = {'filter':'!)RwcIFN1K)cI6Nxx4kqWciTW'}
    data = mse_api_call(func, params)
    if 'items' not in data or 'user_id' not in data['items'][0]:
        return redirect(url_for('index', error="user"))
    user = data['items'][0]

    query = """SELECT * FROM questions WHERE quality_score IS NOT NULL
               AND quality_score >= %s"""
    if 'onlyunanswered' in request.form and request.form['onlyunanswered'] \
            == 'yes':
        query += """ AND accepted_answer_id IS NULL"""
    query += """ ORDER BY last_activity_date DESC LIMIT 30;"""
    con = get_db()
    cur = con.cursor()
    cur.execute(query, [quality])
    
    questions = cur.fetchall()

    interests = clf.predict_proba([q['body_html'] for q in questions])[:,1]
    for i in range(len(questions)):
        questions[i]['interest'] = int(100*interests[i])

    questions.sort(key=lambda q: q['interest'], reverse=True)
    
    return render_template('list.html', questions=questions, user=user, quality=quality)

@app.route('/analytics/')
def analytics():
    with open('psq.pickle', 'rb') as f:
        psq = pickle.load(f)
   
    clfstats = []
    for filename in os.listdir('data'):
        userid = int(filename.split('.')[0])
        with open('data/'+filename, 'rb') as f:
            stats = pickle.load(f).stats
        clfstats.append((userid, stats))

    clfstats.sort(key=lambda s:s[1]['accuracy'], reverse=True)

    return render_template('analytics.html', psqstats=psq.stats, clfstats=clfstats)


@app.route('/slides/')
def slides():
    return render_template('slides.html')

