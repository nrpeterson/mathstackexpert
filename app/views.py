import json
import gzip
from time import sleep
from datetime import datetime as dt
from urllib.parse import urlencode
from urllib.request import urlopen
from io import BytesIO
import pickle
from flask import render_template, request, g
from app import app, db
from app.models.questions import build_interest_classifier

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/list/', methods=['POST'])
def list():
    userid = request.form['userid']
    clf = build_interest_classifier(userid)
    with open('homework.pickle', 'rb') as f:
        psq = pickle.load(f)
    
    base = "http://api.stackexchange.com/2.2/questions"
    params = {
        'site': 'math',
        'page': 1,
        'pagesize': 100,
        'order': 'desc',
        'sort': 'activity',
        'filter': '!OfYUQYRhcE7qIaRSSxgFjfqkx0JaBqHMlFlM)tvda)H',
        'key': '062O6ANtxbZRHzqy56VlFw(('
    }
    
    url = base + '?' + urlencode(params)
 
    response = urlopen(url)
    buf = BytesIO(response.read())
    gz = gzip.GzipFile(fileobj=buf)
    text = gz.read().decode()
    data = json.loads(text)

    questions = []
    for item in data['items']:
        q = {
            'title':item['title'], 
            'body':item['body'],
            'link':item['link'],
            'username':item['owner']['display_name'],
            'quality':int(100*psq.predict_proba([item['body']])[0,0]),
            'interest':int(100*clf.predict_proba([item['body']])[0,1])
        }
        questions.append(q)

    questions.sort(key=lambda q: clf.predict_proba([q['body']])[0,1], reverse=True)
    return render_template('list.html', questions=questions)

