import numpy as np
from sklearn.cluster import AffinityPropagation, SpectralClustering
from app import connect_db


def create_tag_categories():
    con = connect_db()
    cur = con.cursor()

    query = """
    SELECT T.id, T.name, COUNT(Q.question_id) AS count FROM
    (
        SELECT tags.id, tags.name, COUNT(qt.question_id) AS count FROM tags
        JOIN question_tags AS qt ON qt.tag_id=tags.id
        WHERE tags.name NOT IN ('advice', 'applications', 'big-list', 
        'education', 'intuition', 'learning', 'math-history', 'math-software',
        'reference-request', 'self-learning', 'soft-question', 'teaching',
        'alternative-proof-strategy', 'proof-writing', 'visualization',
        'alternative-proof', 'proof-strategy', 'proof-verification',
        'solution-verification', 'definition', 'examples-counterexamples',
        'mathematica', 'wolfram-alpha', 'maple', 'matlab', 'sage', 'octave',
        'floor-function', 'ceiling-function', 'article-writing', 'publishing',
        'combinatorial-species', 'gromov-hyperbolic-spaces')
        GROUP BY tags.name
    ) AS T
    JOIN question_tags AS Q ON T.id=Q.tag_id
    GROUP BY T.id"""
    cur.execute(query)
    tag_ids = []
    tag_names = []
    tag_indices = dict()
    tag_name_indices = dict()
    counts = []
    for q in cur:
        tag_ids.append(q['id'])
        tag_names.append(q['name'])
        tag_indices[q['id']] = len(tag_ids) - 1
        tag_name_indices[q['name']] = len(tag_ids) - 1
        counts.append(q['count'])

    tag_ids = np.array(tag_ids)
    tag_names = np.array(tag_names)

    query = """
    SELECT t1.id AS tag1, t2.id AS tag2, COUNT(qt1.question_id) as count
    FROM question_tags AS qt1
    JOIN question_tags AS qt2 ON qt1.question_id=qt2.question_id
    JOIN tags AS t1 ON t1.id=qt1.tag_id
    JOIN tags AS t2 ON t2.id=qt2.tag_id
    WHERE t1.id IN ({taglist}) AND t2.id IN ({taglist})
    GROUP BY t1.name, t2.name""".format(taglist=','.join(str(i) for i in tag_ids))
    cur.execute(query)

    paircounts = [[0 for i in range(len(tag_ids))] for j in range(len(tag_ids))]
    for q in cur:
        t1 = q['tag1']
        i1 = tag_indices[t1]
        t2 = q['tag2']
        i2 = tag_indices[t2]
        c = q['count']
        if i1 == i2:
            paircounts[i1][i1] = int(c/2)
        else:
            paircounts[i1][i2] = c

    sim = np.array(paircounts, dtype=np.float_)

    cluster = AffinityPropagation(affinity='precomputed', damping=0.5)

    labels = cluster.fit_predict(sim)

    classes = sorted(list(set(labels)))

    catnames = {i:tag_names[cluster.cluster_centers_indices_[i]] for i in \
            range(len(cluster.cluster_centers_indices_))}
    cur.execute("DELETE FROM categories WHERE 1;")
    cur.execute("DELETE FROM tag_categories WHERE 1;")

    query = "INSERT INTO categories (id,name) VALUES "
    catnames = [tag_names[cluster.cluster_centers_indices_[c]] for c in classes]
    query += ','.join("({},'{}')".format(c,catnames[c]) for c in classes)
    cur.execute(query)

    query = "INSERT INTO tag_categories (tag_id, category_id) VALUES "
    query += ','.join("({},{})".format(tag_ids[i], labels[i]) for i \
            in range(len(labels)))
    cur.execute(query)
    con.commit()
