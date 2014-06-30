import datetime as dt
from app import connect_db

def get_last_updated():
    """Get the MySQL datetime of the last update to the question list.

       Returns the epoch if no time is listed in the database.
    """
    con = connect_db()
    cur = con.cursor()
    query = "SELECT * FROM last_updated WHERE description='questions'"
    if cur.execute(query) > 0:
        ts = cur.fetchone()['date']
    else:
        ts = dt.fromtimestamp(0)
        cur.execute("""INSERT INTO last_updated (description, date) VALUES 
        ('questions', %s);""", [ts])

    con.commit()
    con.close()
    return ts

def set_last_updated():
    """Mark the database as having last been updated now."""
    con = connect_db()
    cur = con.cursor()
    date = dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    query = "select * from last_updated where description='questions';"
    if cur.execute(query) == 0:
        query = "insert into last_updated (description, date) values(%s, %s);"
        desc = 'questions'
        cur.execute(query, [desc, date])
    else:
        query = "update last_updated set date=%s where description='questions';"
        cur.execute(query, [date])
    con.commit()
    con.close()
