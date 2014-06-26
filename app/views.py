import json
import pickle
from flask import render_template, request, session, Response
from app import app, get_db
from app.api import mse_api_call

@app.route('/')
def start():
    session.clear()
    return render_template('start.html')

@app.route('/questions/')
def questions():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM categories ORDER BY name  ASC;")
    categories = cur.fetchall()
    return render_template('questions.html', categories=categories)

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
SELECT Q.id, Q.body_html, Q.creation_date, Q.last_activity_date, Q.link, 
Q.title, Q.author_id, Q.quality_score, '' AS chosen_categories, 
GROUP_CONCAT(DISTINCT C.name ORDER BY C.name) AS categories
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
Q.title, Q.quality_score, Q.author_id, 
GROUP_CONCAT(DISTINCT C.name ORDER BY C.name) AS categories,
GROUP_CONCAT(DISTINCT IF(C.name in ({}), C.name, NULL) ORDER BY C.name) AS chosen_categories
FROM categories AS C
JOIN tag_categories AS TC ON C.id=TC.category_id
JOIN question_tags AS QT ON QT.tag_id=TC.tag_id
JOIN questions AS Q ON Q.id=QT.question_id
WHERE Q.quality_score >= %s
AND Q.accepted_answer_id IS NULL
GROUP BY Q.id
HAVING CHAR_LENGTH(chosen_categories) > 0
ORDER BY last_activity_date DESC
LIMIT 30
""".format(catlist)
    cur.execute(query, session['quality'])
    result = cur.fetchall()
    for i in range(len(result)):
        result[i]['creation_date'] = result[i]['creation_date'].strftime('%Y-%m-%d %H:%M:%S')
        result[i]['last_activity_date'] = result[i]['last_activity_date'].strftime('%Y-%m-%d %H:%M:%S')
    return Response(json.dumps(result, indent=4), mimetype='application/json')

@app.route('/slides/')
def slides():
    return render_template('slides.html')

