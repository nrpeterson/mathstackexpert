-- MySQL schemas
-- To import your schemas into your database, run:
-- `mysql -u username -p database < schema.sql`
-- where username is your MySQL username

CREATE TABLE IF NOT EXISTS answers (
    id INT NOT NULL,
    author_id INT,
    body_html TEXT NOT NULL,
    body_markdown TEXT NOT NULL,
    creation_date DATETIME NOT NULL,
    is_accepted BOOLEAN NOT NULL,
    last_activity_date DATETIME NOT NULL,
    link VARCHAR(255) NOT NULL,
    question_id INT NOT NULL,
    score INT NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS questions (
    id INT NOT NULL,
    accepted_answer_id INT,
    author_id INT,
    body_html TEXT NOT NULL,
    body_markdown TEXT NOT NULL,
    closed_date DATETIME,
    closed_desc TEXT,
    closed_reason VARCHAR(300),
    creation_date DATETIME NOT NULL,
    last_activity_date DATETIME NOT NULL,
    link VARCHAR(255) NOT NULL,
    score INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    quality_score INT,
    historic BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS tags (
    id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS question_tags (
    tag_id INT NOT NULL,
    question_id INT NOT NULL,
    PRIMARY KEY (tag_id, question_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS last_updated (
    description VARCHAR(100) NOT NULL,
    date DATETIME NOT NULL,
    PRIMARY KEY (description)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS categories (
    id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS tag_categories (
    tag_id INT NOT NULL,
    category_id INT NOT NULL,
    PRIMARY KEY (tag_id, category_id)
) ENGINE=InnoDB;
