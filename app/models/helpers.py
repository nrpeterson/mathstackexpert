from sklearn.feature_extraction.text import CountVectorizer
from bs4 import BeautifulSoup
import re

def preprocess_post(text):
    # Strip out HTML
    newtext = BeautifulSoup(text).get_text()
    
    # Find inline math.  Replace $$...$$ with 'MathJaxDisplay' and $...$ with 
    # 'MathJaxInline'
    p = re.compile('\$\$.*?\$\$')
    newtext = p.sub('MathJaxDisplay', newtext)

    p = re.compile('\$.*?\$')
    newtext = p.sub('MathJaxInline', newtext)
    return newtext

def is_psq(quest):
    """Given a question, return whether or not it has been voted as a PSQ."""
    
    result = False
    if quest.closed_date and quest.closed_reason == 'off-topic':
        if 'homework' in quest.closed_desc or 'context' in quest.closed_desc:
            result = True
    return result
    
