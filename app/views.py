import json
from time import sleep
from datetime import datetime as dt
import pickle
import os
from flask import render_template, request, g, session, Response
from app import app, get_db
from app.models.questions import build_interest_classifier
from app.api import mse_api_call

@app.route('/')
def index():
    session.clear()
    return render_template('start.html')

@app.route('/questions/')
def questions():
    return render_template('questions.html')

@app.route('/list/', methods=["POST"])
def list():

    con = get_db()
    cur = con.cursor()
    query = "SELECT * FROM categories ORDER BY id ASC;"
    cur.execute(query)
   
    cat_names = [q['name'] for q in cur]
    session['quality'] = request.form['quality'] 
    if 'weights' not in session:
        session['weights'] = dict()

    for cname in cat_names:
        if cname in request.form:
            session['weights'][cname] = float(request.form[cname])
        else:
            session['weights'][cname] = 0
    
    query = """
SELECT Q.body_html, Q.creation_date, Q.last_activity_date, Q.link, Q.title, 
Q.quality_score,
SUM(CASE WHEN """
    query += " WHEN ".join('C.name="{}" THEN {}'.format(k,session['weights'][k]) for k in \
            sorted(session['weights'].keys()))
    query += """ END) AS score
FROM (
    SELECT * FROM questions """

    if 'only_unanswered' in session:
        query += """WHERE accepted_answer_id IS NULL """
    query += """
    ORDER BY last_activity_date DESC LIMIT 100
) AS Q
JOIN question_tags AS QT ON Q.id=QT.question_id
JOIN tag_categories AS TC ON QT.tag_id=TC.tag_id
JOIN categories AS C ON TC.category_id=C.id
WHERE quality_score >= %s
GROUP BY Q.id
ORDER BY score DESC, last_activity_date DESC
LIMIT 30;
"""
    cur.execute(query, [session['quality']])
    
    questions = cur.fetchall()
    return render_template('list.html', questions=questions)

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

@app.route('/api/categories/')
def api_categories():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM categories ORDER BY id ASC;")
    cats = [q['name'] for q in cur]
    return Response(json.dumps(cats, indent=4), mimetype='application/json')

@app.route('/api/questions/')
def api_questions():
    con = get_db()
    cur = con.cursor()
    if 'cats' not in session:
        session['cats'] = dict()
    for k,v in request.args.items():
        if k == 'quality':
            session['quality'] = int(v)
        else:
            session['cats'][k] = int(v)
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT name FROM categories ORDER BY id ASC;")
    cats = [q['name'] for q in cur]
    if 'quality' not in session:
        session['quality'] = 50
        
    if not any(session['cats'][cat]==1 for cat in session['cats']):
        query = """
SELECT Q.id, Q.body_html, Q.creation_date, Q.last_activity_date, Q.link, Q.title,
Q.quality_score, GROUP_CONCAT(DISTINCT C.name) AS categories
FROM questions AS Q
JOIN question_tags AS QT ON QT.question_id = Q.id
JOIN tag_categories AS TC ON TC.tag_id = QT.tag_id
JOIN categories AS C ON C.id = TC.category_id
WHERE Q.accepted_answer_id IS NULL
AND Q.quality_score >= %s
GROUP BY Q.id
ORDER BY Q.last_activity_date DESC
LIMIT 30;"""

    else:
        catlist = ','.join("'{}'".format(cat) for cat in session['cats'] if \
                session['cats'][cat] == 1)
        query = """
SELECT Q.id, Q.body_html, Q.creation_date, Q.last_activity_date, Q.link, 
Q.title, Q.quality_score, Q.author_id, GROUP_CONCAT(DISTINCT C.name) 
AS categories
FROM categories AS C
JOIN tag_categories AS TC ON C.id=TC.category_id
JOIN question_tags AS QT ON QT.tag_id=TC.tag_id
JOIN questions AS Q ON Q.id=QT.question_id
WHERE C.name IN ({})
AND Q.quality_score >= %s
AND Q.accepted_answer_id IS NULL
GROUP BY Q.id
ORDER BY last_activity_date DESC
LIMIT 30
""".format(catlist)
    print(query)
    cur.execute(query, session['quality'])
    result = cur.fetchall()
    for i in range(len(result)):
        result[i]['creation_date'] = result[i]['creation_date'].strftime('%Y-%m-%d %H:%M:%S')
        result[i]['last_activity_date'] = result[i]['last_activity_date'].strftime('%Y-%m-%d %H:%M:%S')
    return Response(json.dumps(result, indent=4), mimetype='application/json')

@app.route('/slides/')
def slides():
    return render_template('slides.html')

