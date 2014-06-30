from sklearn.feature_extraction.text import CountVectorizer
from bs4 import BeautifulSoup
import re

def preprocess_post(text):
    """Preprocessor for MSE questions, to be applied before TFIDF.

       Strips out HTML, converts everything to lowercase, and removes digits.
    """
    result = BeautifulSoup(text).get_text()
    result = result.lower()
    result = ''.join(c for c in result if not c.isdigit())
    return BeautifulSoup(text).get_text()
