from sqlalchemy.ext.associationproxy import association_proxy
from app import app, db


def get_or_create(model, id):
    instance = model.query.filter(model.id == id).first()
    if not instance:
        instance = model()
        instance.id = id
    return instance

def get_or_create_tag(tagname):
    tag = Tag.query.filter(Tag.name==tagname).first()
    if not tag:
        tag = Tag(name=tagname)
    return tag

question_tags = db.Table('question_tags',
        db.Column('tag_id', db.Integer, db.ForeignKey('tag.id')),
        db.Column('question_id', db.Integer, db.ForeignKey('question.id'))
)

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    accepted_answer_id = db.Column(db.Integer)
    author_id = db.Column(db.Integer)
    body_html = db.Column(db.Text)
    body_markdown = db.Column(db.Text)
    closed_date = db.Column(db.DateTime)
    closed_desc = db.Column(db.Text)
    closed_reason = db.Column(db.String(300))
    creation_date = db.Column(db.DateTime)
    last_activity_date = db.Column(db.DateTime)
    link = db.Column(db.String(255))
    score = db.Column(db.Integer)
    title = db.Column(db.String(150))
    tag_ids = db.relationship('Tag', 
            secondary=question_tags, 
            cascade="all,delete", 
            backref=db.backref('questions', lazy='dynamic'))
    tags = association_proxy('tag_ids', 'name', creator = get_or_create_tag)

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer)
    body_html = db.Column(db.Text)
    body_markdown = db.Column(db.Text)
    creation_date = db.Column(db.DateTime)
    is_accepted = db.Column(db.Boolean)
    last_activity_date = db.Column(db.DateTime)
    link = db.Column(db.String(255))
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    question = db.relationship('Question', 
            backref=db.backref('answers', lazy='dynamic'))
    score = db.Column(db.Integer)


