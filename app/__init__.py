import pymysql
import sys
from flask import Flask, g, request, url_for

app = Flask(__name__)
app.config.from_pyfile('../settings/development.cfg')

def connect_db():
    try:
        con = pymysql.connect(
                host=app.config['DB_HOST'], 
                port=app.config['DB_PORT'], 
                user=app.config['DB_USER'], 
                passwd=app.config['DB_PASSWORD'], 
                db=app.config['DB_NAME'],
                charset='utf8',
                cursorclass=pymysql.cursors.DictCursor
        )
    except pymysql.Error as e:
        print("Error {}: {}".format(e.args[0], e.args[1]))
        sys.exit(1)

    return con

def get_db():
    if not hasattr(g, 'db_con'):
        g.db_con = connect_db()
    return g.db_con

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db_con'):
        g.db_con.close()

from app import views
