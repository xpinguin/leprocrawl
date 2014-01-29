--
-- Abstract object
--
CREATE TABLE IF NOT EXISTS 'object' (
	id INTEGER PRIMARY KEY,
	type INTEGER NOT NULL,
	create_date INTEGER
);

-- NOTE: some objects (users, comments, posts) could have raw text content inside them
-- # time-tracked
CREATE TABLE IF NOT EXISTS 'object_data' (
	obj_id INTEGER REFERENCES object (id) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	content TEXT
)

--
-- Abstract binary relation between objects
--
CREATE TABLE IF NOT EXISTS 'binary_relation' (
	id INTEGER PRIMARY KEY,
	type INTEGER NOT NULL,
	
	obj1_id INTEGER REFERENCES object (id) NOT NULL,
	obj2_id INTEGER REFERENCES object (id) NOT NULL
);

--
-- OBJ "user": object<->lepra_user_id
-- # not time-tracked
-- # cacheable
--
CREATE TABLE IF NOT EXISTS 'user' (
	user_id INTEGER REFERENCES object (id),
	lepra_uid INTEGER UNIQUE
);
--CREATE INDEX IF NOT EXISTS _idx_user_lepra_uid ON user (lepra_uid);

-- # time-tracked
CREATE TABLE IF NOT EXISTS 'user_data' (
	user_id INTEGER REFERENCES object (id) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	real_name TEXT,
	nickname TEXT,
	city TEXT,
	country TEXT,
	max_votes_per_day INTEGER,
	vote_weight INTEGER,
	gender INTEGER
);
--CREATE INDEX IF NOT EXISTS _idx_user_data_user_id ON user_data (user_id);
--CREATE INDEX IF NOT EXISTS _idx_user_data_nickname ON user_data (nickname);

--
-- OBJ "post": object<->lepra_post_id
-- # not time-tracked
-- # cacheable
--
CREATE TABLE IF NOT EXISTS 'post' (
	post_id INTEGER REFERENCES object (id),
	lepra_pid INTEGER UNIQUE
);
--CREATE INDEX IF NOT EXISTS _idx_post_author_id ON post (author_id);
--CREATE INDEX IF NOT EXISTS _idx_post_lepra_pid ON post (lepra_pid);

-- # time-tracked
CREATE TABLE IF NOT EXISTS 'post_data' (
	post_id INTEGER REFERENCES object (id) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	is_gold INTEGER
);

--
-- OBJ "comment": object<->lepra_comment_id
-- # not time-tracked
-- # cacheable
--
CREATE TABLE IF NOT EXISTS 'comment' (
	comment_id INTEGER REFERENCES object (id),
	lepra_cid INTEGER UNIQUE
);
--CREATE INDEX IF NOT EXISTS _idx_comment_author_id ON comment (author_id);
--CREATE INDEX IF NOT EXISTS _idx_comment_post_id ON comment (post_id);
--CREATE INDEX IF NOT EXISTS _idx_comment_lepra_cid ON comment (lepra_cid);

-- # time-tracked
CREATE TABLE IF NOT EXISTS 'comment_data' (
	comment_id INTEGER REFERENCES object (id) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	indent INTEGER
);

--
-- OBJ "sublepra": object<->sublepra_name
-- # not time-tracked
--
CREATE TABLE IF NOT EXISTS 'sublepra' (
	sublepra_id INTEGER REFERENCES object (id),
	name TEXT UNIQUE
);
--CREATE INDEX IF NOT EXISTS _idx_sublepra_name ON sublepra (name);

-- # time-tracked
CREATE TABLE IF NOT EXISTS 'sublepra_data' (
	sublepra_id INTEGER REFERENCES object (id) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	lepra_slid INTEGER,
	owner_id INTEGER REFERENCES object (id),
);

--
-- OBJ/REL "administrative": user<->(administrative_role, date_start, date_end)
-- # not time-tracked
--
CREATE TABLE IF NOT EXISTS 'administrative' (
	user_id INTEGER REFERENCES object (id),
	date_start INTEGER NOT NULL,
	date_end INTEGER NOT NULL,
	flags INTEGER NOT NULL DEFAULT 0
);

--
-- REL "favorites": user<->post
-- # time-tracked
--
CREATE TABLE IF NOT EXISTS 'favs' (
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),

	user_id INTEGER REFERENCES object (id) NOT NULL,
	post_id INTEGER REFERENCES object (id)
);

--
-- REL "attitude": object<->(user, attitude)
-- # time-tracked
--
CREATE TABLE IF NOT EXISTS 'attitude' (
	id INTEGER PRIMARY KEY,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),

	obj_id INTEGER REFERENCES object (id),
	user_id INTEGER REFERENCES object (id),
	attitude INTEGER DEFAULT NULL
);
