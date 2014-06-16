from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.pipline import Pipeline
from sklearn.naive_bayes import MultinomialNB
from sklearn.preprocessing import MultiLabelBinarizer
from app import db
from app.database import Question, Tag
from app.models.helpers import preprocess_post

class TagClassifier:
    def __init__(self, **kwargs):
        tags = [t.name for t in Tag.query.order_by(Tag.id)]
        self.bin = MultiLabelBinarizer(classes=tags)
        self.bin.classes_ = tags
        self.vec = HashingVectorizer()
        self.clf = MultinomialNB(**kwargs)

    def fit(self, X, y, **kwargs):
        y0 = self.bin.transform(y)
        X0 = self.vec.transform(preprocess_post(X))
        return self.clf.fit(X0, y0, **kwargs)

    def get_params(deep=True):
        return self.clf.

def build_labeller():
    tag_names = [tag.name for tag in Tag.query.order_by(Tag.id)]
    binarizer = MultiLabelBinarizer(classes=tag_names)
    vectorizer = HashingVectorizer()
    classifier = MultinomialNB()

