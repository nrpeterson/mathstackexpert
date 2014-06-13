from sklearn.feature_extraction.text import CountVectorizer
from bs4 import BeautifulSoup
import re

def preprocess_post(text):
    # Strip out HTML
    return BeautifulSoup(text).get_text()

def is_psq(quest):
    """Given a question, return whether or not it has been voted as a PSQ."""
    
    result = False
    if quest.closed_date and quest.closed_reason == 'off-topic':
        if 'homework' in quest.closed_desc or 'context' in quest.closed_desc:
            result = True
    return result
    
