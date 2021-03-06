PRAGMA synchronous=OFF;

--
-- User
--
CREATE TABLE IF NOT EXISTS 'user' (
	lepro_uid INTEGER PRIMARY KEY,
	create_date INTEGER
);
CREATE INDEX IF NOT EXISTS _idx_user_lepro_uid ON user (lepro_uid);

CREATE TABLE IF NOT EXISTS 'user_data' (
	user_id INTEGER REFERENCES user (lepro_uid),
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	real_name TEXT,
	nickname TEXT,
	city TEXT,
	country TEXT,
	max_votes_per_day INTEGER,
	vote_weight INTEGER,
	gender INTEGER
);
CREATE INDEX IF NOT EXISTS _idx_user_data_id ON user_data (user_id);

CREATE TABLE IF NOT EXISTS 'user_story' (
	user_id INTEGER REFERENCES user (lepro_uid) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')), 
	
	content TEXT
);
CREATE INDEX IF NOT EXISTS _idx_user_story_id ON user_story (user_id);

CREATE TABLE IF NOT EXISTS 'user_rating' (
	user_id INTEGER REFERENCES user (lepro_uid) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')), 
	
	rating_json TEXT
);
CREATE INDEX IF NOT EXISTS _idx_user_rating_id ON user_rating (user_id);

CREATE TABLE IF NOT EXISTS 'user_genealogy' (
	user_id INTEGER REFERENCES user (lepro_uid) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')), 
	
	parent_nickname TEXT,
	children_nicknames_json TEXT
);
CREATE INDEX IF NOT EXISTS _idx_user_genealogy_id ON user_genealogy (user_id);

CREATE TABLE IF NOT EXISTS 'user_fav_posts' (
	user_id INTEGER REFERENCES user (lepro_uid) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')), 
	
	fav_posts_json TEXT
);
CREATE INDEX IF NOT EXISTS _idx_user_favposts_id ON user_fav_posts (user_id);

--
-- Sublepra
--
CREATE TABLE IF NOT EXISTS 'sublepra' (
	lepro_slid INTEGER PRIMARY KEY,
	create_date INTEGER
);

CREATE TABLE IF NOT EXISTS 'sublepra_data' (
	sublepra_id INTEGER REFERENCES sublepra (lepro_slid) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	name TEXT,
	title TEXT,
	owner_nickname TEXT,
	default_access_mode INTEGER
);

CREATE TABLE IF NOT EXISTS 'sublepra_stats' (
	sublepra_id INTEGER REFERENCES sublepra (lepro_slid) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	posts_num INTEGER,
	comments_num INTEGER,
	subscribers_num INTEGER
);

-- access_list_json <=> [(user_nickname, int ACCESS_MODE), ...]
-- (see defs.py for SUBLEPRA_ACCESS_* bit flags)
CREATE TABLE IF NOT EXISTS 'sublepra_acl' (
	sublepra_id INTEGER REFERENCES sublepra (lepro_slid) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	access_list_json TEXT
);

--
-- Post
--
CREATE TABLE IF NOT EXISTS 'post' (
	lepro_pid INTEGER PRIMARY KEY,
	create_date INTEGER,
	author_id INTEGER
);
CREATE INDEX IF NOT EXISTS _idx_post_lepro_pid ON post (lepro_pid);

CREATE TABLE IF NOT EXISTS 'post_props' (
	post_id INTEGER REFERENCES post (lepro_pid) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	author_nickname TEXT,
	sublepra_name TEXT,
	is_gold INTEGER
);
CREATE INDEX IF NOT EXISTS _idx_post_props_id ON post_props (post_id);

CREATE TABLE IF NOT EXISTS 'post_content' (
	post_id INTEGER REFERENCES post (lepro_pid) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	content TEXT
);
CREATE INDEX IF NOT EXISTS _idx_post_content_id ON post_content (post_id);

CREATE TABLE IF NOT EXISTS 'post_rating' (
	post_id INTEGER REFERENCES post (lepro_pid) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	rating_json TEXT
);
CREATE INDEX IF NOT EXISTS _idx_post_rating_id ON post_rating (post_id);

-- whether this needs decomposition, or not?
CREATE TABLE IF NOT EXISTS 'post_comm_sequence' (
	post_id INTEGER REFERENCES post (lepro_pid) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	comm_sequence_json TEXT
);
CREATE INDEX IF NOT EXISTS _idx_post_commseq_id ON post_comm_sequence (post_id);

-- TODO: decompose
-- now I am not of much interest in tags
-- tags_json <=> [(tag_id, (nick1, nick2, ...)), ...]
CREATE TABLE IF NOT EXISTS 'post_tags' (
	post_id INTEGER REFERENCES post (lepro_pid) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	tags_json TEXT
);
CREATE INDEX IF NOT EXISTS _idx_post_tags_id ON post_tags (post_id);
--
-- Comment
--
CREATE TABLE IF NOT EXISTS 'comment' (
	lepro_cid INTEGER PRIMARY KEY,
	create_date INTEGER,
	author_id INTEGER,
	
	post_id INTEGER REFERENCES post (lepro_pid) NOT NULL
);
CREATE INDEX IF NOT EXISTS _idx_comment_lepro_cid ON comment (lepro_cid);

CREATE TABLE IF NOT EXISTS 'comment_props' (
	comment_id INTEGER REFERENCES comment (lepro_cid) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	author_nickname TEXT,
	indent INTEGER
);
CREATE INDEX IF NOT EXISTS _idx_comment_props_id ON comment_props (comment_id);

CREATE TABLE IF NOT EXISTS 'comment_content' (
	comment_id INTEGER REFERENCES comment (lepro_cid) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	content TEXT
);
CREATE INDEX IF NOT EXISTS _idx_comment_content_id ON comment_content (comment_id);

CREATE TABLE IF NOT EXISTS 'comment_rating' (
	comment_id INTEGER REFERENCES comment (lepro_cid) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	rating_json TEXT
);
CREATE INDEX IF NOT EXISTS _idx_comment_rating_id ON comment_rating (comment_id);

CREATE TABLE IF NOT EXISTS 'comment_total_rating' (
	comment_id INTEGER REFERENCES comment (lepro_cid) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	total_rating INTEGER
);
CREATE INDEX IF NOT EXISTS _idx_comment_totalrating_id ON comment_total_rating (comment_id);

--
-- Glagne voting
--
CREATE TABLE IF NOT EXISTS 'glagne_vote' (
	id INTEGER PRIMARY KEY,
	
	voting_date INTEGER NOT NULL,
	voter_nickname TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS 'glagne_vote_data' (
	vote_id INTEGER REFERENCES glagne_vote (id) NOT NULL,
	observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	
	candidate_nickname TEXT
);

--
-- Greetings
--
CREATE TABLE IF NOT EXISTS 'greeting' (
	id INTEGER PRIMARY KEY,
	content TEXT UNIQUE
);
CREATE INDEX IF NOT EXISTS _idx_greeting_id ON greeting (id);
CREATE INDEX IF NOT EXISTS _idx_greeting_content ON greeting (content);

CREATE TABLE IF NOT EXISTS 'greeting_sublepra' (
	id INTEGER PRIMARY KEY,
	greeting_id INTEGER REFERENCES greeting (id) NOT NULL,
	sublepra_name TEXT,
	
	first_observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	last_observed_date INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	times_occured INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS _idx_greeting_sublepra_id ON greeting_sublepra (id);
CREATE INDEX IF NOT EXISTS _idx_greeting_sublepra_greetingid ON greeting_sublepra (greeting_id);
CREATE INDEX IF NOT EXISTS _idx_greeting_sublepra_slname ON greeting_sublepra (sublepra_name);

--
-- Posts tagging
--
CREATE TABLE IF NOT EXISTS 'tag' (
	id INTEGER PRIMARY KEY,
	content TEXT UNIQUE NOT NULL
);
CREATE INDEX IF NOT EXISTS _idx_tag_id ON tag (id);
CREATE INDEX IF NOT EXISTS _idx_tag_content ON tag (content);



-------------------------------------------------------------------------------------------
--- CONVINIENT STUFF
-------------------------------------------------------------------------------------------

CREATE VIEW IF NOT EXISTS '_v_greeting_per_sublepra' AS
select	greeting.content,
		greeting_sublepra.sublepra_name, greeting_sublepra.first_observed_date,
		greeting_sublepra.last_observed_date, greeting_sublepra.times_occured
from greeting
inner join greeting_sublepra on greeting.id = greeting_sublepra.greeting_id
order by greeting.content asc;

