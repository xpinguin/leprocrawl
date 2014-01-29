--
-- User
--
CREATE TABLE IF NOT EXISTS 'user' (
	id INTEGER PRIMARY KEY,
	lepro_uid INTEGER,
	create_date INTEGER,
	parent_user_id INTEGER REFERENCES user (id)
);

CREATE TABLE IF NOT EXISTS 'user_data' (
	user_id INTEGER REFERENCES user (id) NOT NULL,
	observed_date INTEGER DEFAULT (strftime('%s', 'now')),
	
	real_name TEXT,
	nickname TEXT,
	city TEXT,
	country TEXT,
	max_votes_per_day INTEGER,
	vote_weight INTEGER,
	gender INTEGER
);

CREATE TABLE IF NOT EXISTS 'user_story' (
	user_id INTEGER REFERENCES user (id) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')), 
	
	content TEXT
);

--
-- Sublepra
--
CREATE TABLE IF NOT EXISTS 'sublepra' (
	id INTEGER PRIMARY KEY,
	lepro_slid INTEGER,
	create_date INTEGER
);

CREATE TABLE IF NOT EXISTS 'sublepra_data' (
	sublepra_id INTEGER REFERENCES sublepra (id) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	name TEXT,
	title TEXT,
	owner_id INTEGER REFERENCES user (id),
	default_access_mode INTEGER
);

CREATE TABLE IF NOT EXISTS 'sublepra_acl' (
	sublepra_id INTEGER REFERENCES sublepra (id) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	user_id INTEGER REFERENCES user (id),
	access_mode INTEGER
);

--- the glagne
--INSERT OR IGNORE INTO 'sublepra' (id, lepra_slid, create_date) VALUES (1, 0, NULL);

--
-- Post
--
CREATE TABLE IF NOT EXISTS 'post' (
	id INTEGER PRIMARY KEY,
	lepro_pid INTEGER,
	create_date INTEGER,
	author_id INTEGER REFERENCES user (id) NOT NULL,
	sublepra_id INTEGER REFERENCES sublepra (id) NOT NULL
);

CREATE TABLE IF NOT EXISTS 'post_data' (
	post_id INTEGER REFERENCES post (id) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	content TEXT,
	is_gold INTEGER
);

--
-- Comment
--
CREATE TABLE IF NOT EXISTS 'comment' (
	id INTEGER PRIMARY KEY,
	lepro_cid INTEGER,
	create_date INTEGER,
	author_id INTEGER REFERENCES user (id) NOT NULL,
	post_id INTEGER REFERENCES post (id) NOT NULL,
	parent_comment_id INTEGER REFERENCES comment (id)
);

CREATE TABLE IF NOT EXISTS 'comment_data' (
	comment_id INTEGER REFERENCES comment (id) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	content TEXT
);

--
-- (pure rel) Favourite post
--
CREATE TABLE IF NOT EXISTS 'user_fav_post' (
	id INTEGER PRIMARY KEY,
	
	user_id INTEGER REFERENCES user (id) NOT NULL,
	post_id INTEGER REFERENCES post (id) NOT NULL
);

CREATE TABLE IF NOT EXISTS 'user_fav_post_data' (
	ufp_id INTEGER REFERENCES user_fav_post (id) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	is_active INTEGER NOT NULL CHECK (is_active IN (0, 1))
);

--
-- (pure rel) User rating
--
CREATE TABLE IF NOT EXISTS 'user_rating' (
	id INTEGER PRIMARY KEY,
	
	user_id INTEGER REFERENCES user (id) NOT NULL,
	judge_id INTEGER REFERENCES user (id) NOT NULL
);

CREATE TABLE IF NOT EXISTS 'user_rating_data' (
	ur_id INTEGER REFERENCES user_rating (id) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	attitude INTEGER
);

--
-- (pure rel) Post rating
--
CREATE TABLE IF NOT EXISTS 'post_rating' (
	id INTEGER PRIMARY KEY,
	
	post_id INTEGER REFERENCES post (id) NOT NULL,
	judge_id INTEGER REFERENCES user (id) NOT NULL
);

CREATE TABLE IF NOT EXISTS 'post_rating_data' (
	pr_id INTEGER REFERENCES post_rating (id) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	attitude INTEGER
);

--
-- (pure rel) Comment rating
--
CREATE TABLE IF NOT EXISTS 'comment_rating' (
	id INTEGER PRIMARY KEY,
	
	comment_id INTEGER REFERENCES comment (id) NOT NULL,
	judge_id INTEGER REFERENCES user (id) NOT NULL
);

CREATE TABLE IF NOT EXISTS 'comment_rating_data' (
	cr_id INTEGER REFERENCES comment_rating (id) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	attitude INTEGER
);

--
-- (pure rel) Glagne vote
--
CREATE TABLE IF NOT EXISTS 'glagne_vote' (
	id INTEGER PRIMARY KEY,
	
	voting_date INTEGER NOT NULL,
	voter_id INTEGER REFERENCES user (id) NOT NULL
);

CREATE TABLE IF NOT EXISTS 'glagne_vote_data' (
	vote_id INTEGER REFERENCES glagne_vote (id) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	candidate_id INTEGER REFERENCES user (id)
);

