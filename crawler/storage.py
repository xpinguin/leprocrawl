import sqlite3
from datetime import datetime
from time import time
from copy import copy
import json

from defs import *
from config import *

#------------------------------------------------------------------------------ 
#------------------------------------------------------------------------------ 

#===============================================================================
# NON-STRICT PASSIVE STORAGE
#===============================================================================
class PassiveStorage:
	"""
		- store specified object into database "as is"
		- perform no or little transform before storing
		
		WARN: database could and probably will be inconsistent due to "raw"
				parsed data being stored
	
		NOTE: sqlite3 backend implied!
	"""
	
	def __init__(self, db_name):
		self.db_conn = sqlite3.connect(db_name, detect_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
		self.db_cur = self.db_conn.cursor()
		
		with open(RAW_DB_SCHEMA, "rb") as _schema_f:
			self.db_cur.executescript(_schema_f.read())
			self.db_conn.commit()
	
	def close(self):
		self.db_conn.close()
	
	def __get_observed_date(self, kwa):
		if (not kwa.has_key("observed_date")):
			return int(time())
		
		if (isinstance(kwa["observed_date"], (int, float))):
			return int(kwa["observed_date"])
		elif (isinstance(kwa["observed_date"], datetime)):
			return datetime_to_timestamp(kwa["observed_date"])
		
		raise Exception("observed_date could not be deduced!", kwa)
	
	def __transform_rating(self, rating_dict):
		"""
			transform rating dictionary into _ordered_ (by uid) sequence of tuples: (uid, attitude) 
		"""
		
		return [
				(__uid_key, __val[0])
				for __uid_key, __val
					in sorted(rating_dict.iteritems(), key = lambda _i: _i[0])
		]
	
	def __transform_or_nothing(self, data_dict, attr_name, transform_f):
		if (not data_dict.has_key(attr_name)) or (data_dict[attr_name] is None):
			return None
		
		return transform_f(data_dict[attr_name])
	
	def __are_fields_different(self, ctx, *args):
		dict_data = ctx[0]
		query_res = ctx[1]
		query_row = ctx[2]
		
		
		for _field in args:
			# -----
			if (isinstance(_field, (tuple, list))):
				_row_field_name = _field[0]
				
				if (len(_field) > 2) and (_field[1] is None):
					_dict_field_name = None
					
					if (len(_field) > 3) and (_field[3]) and (_field[2] is None):
						continue
				else:
					_dict_field_name = _field[1]
				
			else:
				_row_field_name = _field
				_dict_field_name = _field
			# -----
			
			# -----
			if (_row_field_name is None):
				continue
			
			if (not _dict_field_name is None) and (not dict_data.has_key(_dict_field_name)):
				continue
			# -----
			
			# -----
			row_field = dbapi_row_col_by_key(query_row, _row_field_name, query_res.description)
			
			if (
				((not _dict_field_name is None) and (row_field != dict_data[_dict_field_name]))
					or
				((_dict_field_name is None) and (row_field != _field[2])) 
			   ):
				
				return True
			# -----
		
		return False
	
	def store_user(self, user_data, **kwargs):
		"""
			store user into database
			
			@arg user_data - proper user's ObjDict()
			
			@return [bool] result
		"""
		
		update_user_data = [False]*5
		observed_date = self.__get_observed_date(kwargs)
		# ----------------------------------------------------------------------------
		
		# deal with "orphan" nickname
		if (user_data.__class__ in (str, unicode)):
			_nickname = user_data
			assert(_nickname != "")
			
			ud_query_res = self.db_cur.execute(
						"""
						SELECT user_id
						FROM user_data
						WHERE user_data.nickname = ?
						ORDER BY observed_date DESC
						LIMIT 1
						""",
						(_nickname,)
			)
			ud_row = ud_query_res.fetchone()
			
			if (ud_row is None):
				# real orphan without any previous information about nickname
				self.db_cur.execute(
							"""
							INSERT INTO user_data (user_id, observed_date, nickname)
							VALUES (NULL, ?, ?)
							""",
							(observed_date, _nickname)
				)
				self.db_conn.commit()
						
			elif (not ud_row[0] is None):
				# not orphan - user were deleted
				_deleted_uid = int(ud_row[0])
				
				# update user info in a dramatic way :)
				self.db_cur.execute(
							"""
							INSERT INTO user_data (user_id, observed_date, nickname)
							VALUES (?, ?, NULL)
							""",
							(_deleted_uid, observed_date)
				)
				self.db_conn.commit()
			
			return True
		# ----------------------------------------------------------------------------
		
		# ----------------------------------------------------------------------------
		_user_favs = self.__transform_or_nothing(user_data, "favs", lambda x: json.dumps(sorted(x)))
		_user_karma = self.__transform_or_nothing(
											user_data,
											"karma",
											lambda x: json.dumps(self.__transform_rating(x))
		)
		_user_children_nicknames = self.__transform_or_nothing(
											user_data,
											"children_nicknames",
											lambda x: json.dumps(sorted(x))
		)
		_user_create_date = self.__transform_or_nothing(
											user_data,
											"create_date",
											lambda x: datetime_to_timestamp(x)
		)
		# ----------------------------------------------------------------------------
		
		user_query_res = self.db_cur.execute(
				"""
				SELECT 
					user_data.real_name, user_data.nickname, user_data.city,
						user_data.country, user_data.max_votes_per_day, user_data.vote_weight,
						user_data.gender,
					user_story.content,
					user_rating.rating_json,
					user_genealogy.parent_nickname, user_genealogy.children_nicknames_json,
					user_fav_posts.fav_posts_json
					
				FROM user
				INNER JOIN user_data ON (user_data.user_id = user.lepro_uid)
				INNER JOIN user_story ON (user_story.user_id = user.lepro_uid)
				INNER JOIN user_rating ON (user_rating.user_id = user.lepro_uid)
				INNER JOIN user_genealogy ON (user_genealogy.user_id = user.lepro_uid)
				INNER JOIN user_fav_posts ON (user_fav_posts.user_id = user.lepro_uid)
				
				WHERE (user.lepro_uid = ?)
				ORDER BY 
						user_data.observed_date DESC,
						user_story.observed_date DESC,
						user_rating.observed_date DESC,
						user_genealogy.observed_date DESC,
						user_fav_posts.observed_date DESC
						
				LIMIT 1
				""",
				(user_data.uid,)
		)
		user_row = user_query_res.fetchone()
		
		if (user_row is None):
			# -----
			if (not user_data.has_key("nickname")) or (user_data.nickname is None):
				# new user without nickname?! Nonsense!
				return False
			# -----
			
			update_user_data = [True]*5
			#user_data.set_default_value(None)
			
			self.db_cur.execute(
						"""
						INSERT INTO user (lepro_uid, create_date)
						VALUES (?, ?)
						""",
						(user_data.uid, _user_create_date)
			)
			self.db_conn.commit()
			
		else:
			# -------
			_afd_ctx = (user_data, user_query_res, user_row)
			# -------
			
			# -- user_data
			update_user_data[0] = self.__are_fields_different(_afd_ctx,
								"real_name", "nickname", "city", "country",
								"max_votes_per_day", "vote_weight", "gender"
			)
			
			# -- user_story
			update_user_data[1] = self.__are_fields_different(_afd_ctx, ("content", "profile_content_raw"))
			
			# -- user_rating
			update_user_data[2] = self.__are_fields_different(_afd_ctx, ("rating_json", None, _user_karma, True))
				
			# -- user_genealogy
			update_user_data[3] = self.__are_fields_different(_afd_ctx,
								"parent_nickname",
								("children_nicknames_json", None, _user_children_nicknames, True)
			) 
			
			# -- user_fav_posts
			update_user_data[4] = self.__are_fields_different(_afd_ctx, ("fav_posts_json", None, _user_favs, True))
			
		# --------------------------
		if (update_user_data[0]):
			self.db_cur.execute(
						"""
						INSERT INTO user_data
							(user_id, observed_date, real_name, nickname, city, country, 
								max_votes_per_day, vote_weight, gender)
						VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
						""",
						(user_data.uid, observed_date, user_data.real_name, user_data.nickname,
							user_data.city, user_data.country, user_data.max_votes_per_day,
							user_data.vote_weight, user_data.gender)
			)
			self.db_conn.commit()
			
		if (update_user_data[1]):
			self.db_cur.execute(
						"""
						INSERT INTO user_story
							(user_id, observed_date, content)
						VALUES (?, ?, ?)
						""",
						(user_data.uid, observed_date, user_data.profile_content_raw)
			)
			self.db_conn.commit()
			
		if (update_user_data[2]):
			self.db_cur.execute(
						"""
						INSERT INTO user_rating
							(user_id, observed_date, rating_json)
						VALUES (?, ?, ?)
						""",
						(user_data.uid, observed_date, _user_karma)
			)
			self.db_conn.commit()
			
		if (update_user_data[3]):
			self.db_cur.execute(
						"""
						INSERT INTO user_genealogy
							(user_id, observed_date, parent_nickname, children_nicknames_json)
						VALUES (?, ?, ?, ?)
						""",
						(user_data.uid, observed_date, user_data.parent_nickname, 
							_user_children_nicknames)
			)
			self.db_conn.commit()
			
		if (update_user_data[4]):
			
			if ((not _user_favs is None) and (not user_row is None) and 
				(dbapi_row_col_by_key(user_row, "fav_posts_json", user_query_res.description)) is None):
				
				self.db_cur.execute(
							"""
							UPDATE user_fav_posts
							SET observed_date = ?, fav_posts_json = ?
							WHERE user_id = ? AND fav_posts_json IS NULL
							ORDER BY observed_date DESC
							LIMIT 1
							""",
							(observed_date, _user_favs, user_data.uid)
				)
			else:
				self.db_cur.execute(
							"""
							INSERT INTO user_fav_posts
								(user_id, observed_date, fav_posts_json)
							VALUES (?, ?, ?)
							""",
							(user_data.uid, observed_date, _user_favs)
				)
			
			self.db_conn.commit()
		
		# ---
		#user_data.remove_default_value()
		# ---
			
		return True
	
	def store_sublepra(self, sublepra_data):
		pass
	
	def store_post(self, post_data, **kwargs):
		"""
			store post into database
			
			@arg post_data - proper post's ObjDict() (incl. "sublepra_name")
			
			@return [bool] result
		"""
		
		deleted_comments = set()
		update_post_data = [False]*4
		observed_date = self.__get_observed_date(kwargs)
		# ----------------------------------------------------------------------------
		
		# deal with deleted posts (we only know index)
		if (isinstance(post_data, int)):
			_post_id = post_data
			assert(_post_id >= 0)
			
			pd_query_res = self.db_cur.execute(
						"""
						SELECT content
						FROM post_content
						WHERE post_content.post_id = ?
						ORDER BY observed_date DESC
						LIMIT 1
						""",
						(_post_id,)
			)
			pd_row = pd_query_res.fetchone()
			
			if ((pd_row is None) or (not pd_row[0] is None)):
				self.db_cur.execute(
							"""
							INSERT INTO post_content (post_id, observed_date, content)
							VALUES (?, ?, NULL)
							""",
							(_post_id, observed_date)
				)
				self.db_conn.commit()
			
			return True
		# ----------------------------------------------------------------------------
		
		# ----------------------------------------------------------------------------
		_post_rating = self.__transform_or_nothing(
											post_data,
											"rating",
											lambda x: json.dumps(self.__transform_rating(x))
		)
		_post_comm_seq = self.__transform_or_nothing(
											post_data,
											"comments",
											lambda x: json.dumps(sorted([_c["id"] for _c in x]))
		)
		_post_create_date = self.__transform_or_nothing(
											post_data,
											"create_date",
											lambda x: datetime_to_timestamp(x)
		)
		# ----------------------------------------------------------------------------
		
		query_res = self.db_cur.execute(
				"""
				SELECT post_props.author_nickname, post_props.sublepra_name, post_props.is_gold,
						post_content.content,
						post_rating.rating_json,
						post_comm_sequence.comm_sequence_json
					
				FROM post
				INNER JOIN post_props ON (post_props.post_id = post.lepro_pid)
				INNER JOIN post_content ON (post_content.post_id = post.lepro_pid)
				INNER JOIN post_rating ON (post_rating.post_id = post.lepro_pid)
				INNER JOIN post_comm_sequence ON (post_comm_sequence.post_id = post.lepro_pid)
				
				WHERE (post.lepro_pid = ?)
				ORDER BY 
						post_props.observed_date DESC,
						post_content.observed_date DESC,
						post_rating.observed_date DESC,
						post_comm_sequence.observed_date DESC
						
				LIMIT 1
				""",
				(post_data.id,)
		)
		query_row = query_res.fetchone()
		
		if (query_row is None):
			update_post_data = [True]*4
			
			self.db_cur.execute(
						"""
						INSERT INTO post (lepro_pid, create_date, author_id)
						VALUES (?, ?, ?)
						""",
						(post_data.id, _post_create_date, post_data.author_uid)
			)
			self.db_conn.commit()
			
		else:
			if (not _post_comm_seq is None):
				deleted_comments = set(json.loads(dbapi_row_col_by_key(
													query_row,
													"comm_sequence_json",
													query_res.description
									))) - \
									set(_c["id"] for _c in post_data.comments)
			
			# -------
			_afd_ctx = (post_data, query_res, query_row)
			# -------
			
			# -- post_props
			update_post_data[0] = self.__are_fields_different(_afd_ctx,
								"author_nickname", "sublepra_name", "is_gold"
			)
			
			# -- post_content
			update_post_data[1] = self.__are_fields_different(_afd_ctx, "content")
			
			# -- post_rating
			update_post_data[2] = self.__are_fields_different(_afd_ctx, 
								("rating_json", None, _post_rating, True)
			)
				
			# -- post_comm_sequence
			update_post_data[3] = (
									(len(deleted_comments) > 0)
									or
									(self.__are_fields_different(
												_afd_ctx,
												("comm_sequence_json", None, _post_comm_seq, True)
									))
			)
									
			
		# --------------------------
		if (update_post_data[0]):
			self.db_cur.execute(
						"""
						INSERT INTO post_props
							(post_id, observed_date, author_nickname, sublepra_name, is_gold) 
						VALUES (?, ?, ?, ?, ?)
						""",
						(post_data.id, observed_date, post_data.author_nickname,
							post_data.sublepra_name, post_data.is_gold)
			)
			self.db_conn.commit()
			
		if (update_post_data[1]):
			self.db_cur.execute(
						"""
						INSERT INTO post_content
							(post_id, observed_date, content) 
						VALUES (?, ?, ?)
						""",
						(post_data.id, observed_date, post_data.content)
			)
			self.db_conn.commit()
			
		if (update_post_data[2]):
			self.db_cur.execute(
						"""
						INSERT INTO post_rating
							(post_id, observed_date, rating_json) 
						VALUES (?, ?, ?)
						""",
						(post_data.id, observed_date, _post_rating)
			)
			self.db_conn.commit()
			
		if (update_post_data[3]):
			self.db_cur.execute(
						"""
						INSERT INTO post_comm_sequence
							(post_id, observed_date, comm_sequence_json) 
						VALUES (?, ?, ?)
						""",
						(post_data.id, observed_date, _post_comm_seq)
			)
			self.db_conn.commit()
			
		# -----------------------------------------
		# handle deleted comments
		for _d_comm_id in deleted_comments:
			self.store_comment(_d_comm_id, observed_date = observed_date, delayed_commit = True) 
		
		# handle comments
		for _comm in post_data.comments:
			_comm["post_id"] = post_data.id
			if (not _comm.has_key("rating")):
				_comm["rating"] = None
				
			self.store_comment(_comm, observed_date = observed_date, delayed_commit = True)
		
		self.db_conn.commit()
		# ----
		return True
	
	def store_comment(self, comment_data, **kwargs):
		"""
			store comment into database
			
			@arg comment_data - proper comment's ObjDict() (incl. "post_id")
			
			@return [bool] result
		"""
		
		# ---
		if (kwargs.has_key("delayed_commit")) and (kwargs["delayed_commit"]):
			_db_do_commit = lambda: None
		else:
			_db_do_commit = lambda: self.db_conn.commit()
		# ---
		
		update_comment_data = [False]*3
		observed_date = self.__get_observed_date(kwargs)
		# ----------------------------------------------------------------------------
		
		# deal with deleted comments (we only know index)
		if (isinstance(comment_data, int)):
			_comm_id = comment_data
			assert(_comm_id >= 0)
			
			cd_query_res = self.db_cur.execute(
						"""
						SELECT content
						FROM comment_content
						WHERE comment_content.comment_id = ?
						ORDER BY observed_date DESC
						LIMIT 1
						""",
						(_comm_id,)
			)
			cd_row = cd_query_res.fetchone()
			
			if ((cd_row is None) or (not cd_row[0] is None)):
				self.db_cur.execute(
							"""
							INSERT INTO comment_content (comment_id, observed_date, content)
							VALUES (?, ?, NULL)
							""",
							(_comm_id, observed_date)
				)
				_db_do_commit()
			
			return True
		# ----------------------------------------------------------------------------
		
		# ----------------------------------------------------------------------------
		_comm_rating = self.__transform_or_nothing(
											comment_data,
											"rating",
											lambda x: json.dumps(self.__transform_rating(x))
		)
		_comm_create_date = self.__transform_or_nothing(
											comment_data,
											"create_date",
											lambda x: datetime_to_timestamp(x)
		)
		# ----------------------------------------------------------------------------
		
		query_res = self.db_cur.execute(
				"""
				SELECT comment_props.author_nickname, comment_props.indent, comment_props.total_rating,
						comment_content.content,
						comment_rating.rating_json
					
				FROM comment
				INNER JOIN comment_props ON (comment_props.comment_id = comment.lepro_cid)
				INNER JOIN comment_content ON (comment_content.comment_id = comment.lepro_cid)
				INNER JOIN comment_rating ON (comment_rating.comment_id = comment.lepro_cid)
				
				WHERE (comment.lepro_cid = ?)
				ORDER BY 
						comment_props.observed_date DESC,
						comment_content.observed_date DESC,
						comment_rating.observed_date DESC
						
				LIMIT 1
				""",
				(comment_data.id,)
		)
		query_row = query_res.fetchone()
		
		if (query_row is None):
			# -----
			if (not comment_data.has_key("post_id")) or (comment_data.post_id is None):
				# new comment without post_id?! Nonsense!
				return False
			# -----
			
			update_comment_data = [True]*3
			
			self.db_cur.execute(
						"""
						INSERT INTO comment (lepro_cid, create_date, author_id, post_id)
						VALUES (?, ?, ?, ?)
						""",
						(comment_data.id, _comm_create_date, comment_data.author_uid,
							comment_data.post_id)
			)
			_db_do_commit()
			
		else:
			# -------
			_afd_ctx = (comment_data, query_res, query_row)
			# -------
			
			# -- comment_props
			update_comment_data[0] = self.__are_fields_different(_afd_ctx,
								"author_nickname", "indent", "total_rating"
			)
			
			# -- comment_content
			update_comment_data[1] = self.__are_fields_different(_afd_ctx, "content")
			
			# -- comment_rating
			update_comment_data[2] = self.__are_fields_different(_afd_ctx, 
								("rating_json", None, _comm_rating, True)
			)
									
			
		# --------------------------
		if (update_comment_data[0]):
			self.db_cur.execute(
						"""
						INSERT INTO comment_props
							(comment_id, observed_date, author_nickname, indent, total_rating) 
						VALUES (?, ?, ?, ?, ?)
						""",
						(comment_data.id, observed_date, comment_data.author_nickname,
							comment_data.indent, comment_data.total_rating)
			)
			_db_do_commit()
			
		if (update_comment_data[1]):
			self.db_cur.execute(
						"""
						INSERT INTO comment_content
							(comment_id, observed_date, content) 
						VALUES (?, ?, ?)
						""",
						(comment_data.id, observed_date, comment_data.content)
			)
			_db_do_commit()
			
		if (update_comment_data[2]):	
			if ((not _comm_rating is None) and (not query_row is None) and 
				(dbapi_row_col_by_key(query_row, "rating_json", query_res.description)) is None):
				
				self.db_cur.execute(
							"""
							UPDATE comment_rating
							SET observed_date = ?, rating_json = ?
							WHERE comment_id = ? AND rating_json IS NULL
							ORDER BY observed_date DESC
							LIMIT 1
							""",
							(observed_date, _comm_rating, comment_data.id)
				)
			else:
				self.db_cur.execute(
						"""
						INSERT INTO comment_rating
							(comment_id, observed_date, rating_json) 
						VALUES (?, ?, ?)
						""",
						(comment_data.id, observed_date, _comm_rating)
				)
			
			_db_do_commit()
		
		# ----
		return True
	
	
	def get_known_users(self):
		"""
			@return set() of all nicknames
		"""
		
		nicknames = dict()
		res_nicknames_set = set()
		
		query_res = self.db_cur.execute(
					"""
					SELECT nickname, observed_date, user_id
					FROM user_data
					WHERE nickname IS NOT NULL
					"""
		)
		
		for _row in query_res:
			if (_row[2] is None):
				res_nicknames_set.add(_row[0])
				continue
			
			obs_date = int(_row[1])
			
			try:
				if (obs_date > nicknames[_row[0]]):
					nicknames[_row[0]] = obs_date
			except KeyError:
				nicknames[_row[0]] = obs_date
		
		res_nicknames_set.update(set(nicknames.iterkeys()))
			
		return res_nicknames_set
	
	def get_known_posts(self):
		"""
			@return set() of all (post_id, sublepra_name) tuples
		"""
		
		posts = dict()
		
		query_res = self.db_cur.execute(
					"""
					SELECT post_id, sublepra_name, observed_date
					FROM post_props
					WHERE post_id IS NOT NULL
					"""
		)
		
		for _row in query_res:
			if (_row[1] is None):
				_row[1] = ""
			obs_date = int(_row[2])
			
			try:
				if (obs_date > posts[_row[0]][1]):
					posts[_row[0]] = (_row[1], obs_date)
			except KeyError:
				posts[_row[0]] = (_row[1], obs_date)
		
		return set((_p_id, _sl[0]) for _p_id, _sl in posts.iteritems())
	
	def get_known_comments(self):
		"""
			@return set() of all (comment_id, post_id) tuples
		"""
		
		comments = set()
		
		query_res = self.db_cur.execute(
					"""
					SELECT lepro_cid, post_id
					FROM comment
					WHERE (post_id IS NOT NULL) AND (lepro_cid IS NOT NULL)
					"""
		)
		
		for _row in query_res:
			comments.add((_row[0], _row[1]))
		
		return comments
			

#===============================================================================
# STRICT REACTIVE STORAGE
#===============================================================================
class ReactiveStorage:
	"""
		- store specified object into database
		- acquire related information through provided callbacks
			* absent attributes
			* related objects (ex. post author user, user favorite post, etc.)
				[strategy: BFS]
				
		NOTE: sqlite3 backend implied!
	"""

	def __init__(self, db_name, db_model_desc, user_query_f, sublepra_query_f, post_query_f):
		"""
			TODO: db_model language!
			
			@arg db_name - database connect string
			@arg db_model_desc - SQL script describing data model
		"""
		
		raise NotImplementedError("Use PassiveStorage for now")
		
		# ------------------------------------------------------------------
		self.user_attrs = {
					"uid" : None,
					"create_date" : None,
					"parent_nickname" : None,
					"children_nicknames" : [],
					"real_name" : None,
					"nickname" : None,
					"city" : None,
					"country" : None,
					"max_votes_per_day" : None,
					"vote_weight" : None,
					"gender" : None,
					"profile_content_raw" : None
		}
		
		self.sublepra_attrs = {
					"id" : None,
					"create_date" : None,
					"name" : None,
					"title" : None,
					"owner_nickname" : None,
					"default_access_mode" : None
		}
		
		self.post_attrs = {
					"id" : None,
					"create_date" : None,
					"sublepra_name" : None,
					"author_uid" : None,
					"content" : None,
					"is_gold" : None
		}
		
		self.comment_attrs = {
					"id" : None,
					"create_date" : None,
					"post_id" : None,
					"author_uid" : None,
					"content" : None
		}
		
		# ------------------------------------------------------------------
		self.__user_query_func = lambda *a, **kwa: user_query_f(*a, **kwa)
		self.__sublepra_query_func = lambda s, *a, **kwa: sublepra_query_f(*a, **kwa)
		self.__post_query_func = lambda s, *a, **kwa: post_query_f(*a, **kwa)
		
		
		# ------------------------------------------------------------------
		self.db_conn = sqlite3.connect(db_name, detect_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
		self.db_cur = self.db_conn.cursor()
		
		self.db_cur.executescript(db_model_desc)
	
	def normalize_dict_data(self, data, default_attrs):
		normed_data = copy(data)
		
		for _k, _v in default_attrs.items():
			if (not normed_data.has_key(_k)):
				normed_data[_k] = _v
				
		return normed_data
	
	def store_user(self, nickname, lepro_uid = None, avoid_info_query = False):
		"""
			add or update user
			
			@return inserted/updated user_id
		"""
		
		assert((not nickname is None) or (not lepro_uid is None))
		# ------------------------------------------------
		
		_id = None
		update_user_data = [False, False]
		# ------------------------------------------------
		
		if ((avoid_info_query) or (nickname is None)):
			user_info = self.normalize_dict_data({"nickname" : nickname, "uid" : lepro_uid}, self.user_attrs)
			user_info["observed_date"] = None
		else:
			user_info = self.__user_query_func(nickname)
			user_info["observed_date"] = time()
			lepro_uid = user_info.uid
		# ------------------------------------------------
		
		user_query_res = self.db_cur.execute(
				"""
				SELECT user.id, user.parent_user_id, user.create_date, user.lepro_uid,
					user_data.real_name, user_data.nickname, user_data.city,
					user_data.country, user_data.max_votes_per_day, user_data.vote_weight,
					user_data.gender,
					user_story.content
				FROM user
				LEFT OUTER JOIN user_data ON user_data.user_id = user.id
				LEFT OUTER JOIN user_story ON user_story.user_id = user.id
				WHERE (user.lepro_uid = ?) OR (user_data.nickname = ?)
				ORDER BY user_data.observed_date DESC, user_story.observed_date DESC
				LIMIT 1
				""",
				(lepro_uid, nickname)
		)
		user_row = user_query_res.fetchone()
		
		if (user_row is None):
			res = self.db_cur.execute(
						"""
						INSERT INTO user (lepro_uid, create_date)
						VALUES (?, ?)
						""",
						(lepro_uid, datetime_to_timestamp(user_info.create_date))
			)
			self.db_conn.commit()
			
			_id = self.db_cur.lastrowid
			assert(not _id is None)
			
			update_user_data = [True, (not user_info.observed_date is None)]
		
		else:
			_id = int(user_row[0])
			user_row = list(user_row)
			user_row[2] = datetime.fromtimestamp(int(user_row[2]))
			
			if (((not lepro_uid is None) and (user_row[3] != lepro_uid)) or
				((not user_info.create_date is None) and (user_row[2] != user_info.create_date))):
				#if (not user_row[3] is None):
				#	raise Exception("{ERR} lepro_uid mismatch", user_row, lepro_uid)
				
				if (not user_row[2] is None):
					raise Exception("{ERR} create_date altered!", user_row, lepro_uid, user_info)
				
				self.db_cur.execute(
						"""
						UPDATE user
						SET lepro_uid = ?, create_date = ?
						WHERE id = ?
						""",
						(lepro_uid, datetime_to_timestamp(user_info.create_date), _id)
				)
				self.db_conn.commit()
				
				if (self.db_cur.rowcount < 1):
					raise Exception("{ERR} failed to update user", user_row, locals(), self.db_cur)
				
				user_row[3] = lepro_uid
				user_row[2] = user_info.create_date
			
			if (not user_info.observed_date is None):
				for i in xrange(len(user_query_res.description)):
					if (user_info.has_key(user_query_res.description[i][0])):
						if (user_row[i] != user_info[user_query_res.description[i][0]]):
							update_user_data[0] = True
							break
					
				if (user_row[-1] != user_info.profile_content_raw):
					update_user_data[1] = True
					
			else:
				update_user_data = [(user_row[5] != nickname), False]
				
			
		if (update_user_data[0]):
			self.db_cur.execute(
						"""
						INSERT OR REPLACE
						INTO user_data (user_id, observed_date, real_name, nickname,
									city, country, max_votes_per_day, vote_weight, gender)
						VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
						""",
						(_id, user_info.observed_date, user_info.real_name, user_info.nickname,
							user_info.city, user_info.country, user_info.max_votes_per_day, 
							user_info.vote_weight, user_info.gender)
			)
			self.db_conn.commit()
			
		if (update_user_data[1]):
			self.db_cur.execute(
						"""
						INSERT OR REPLACE
						INTO user_story (user_id, observed_date, content)
						VALUES (?, ?, ?)
						""",
						(_id, user_info.observed_date, user_info.profile_content_raw)
			)
			self.db_conn.commit()
		
		# -- handle karma
		if (not user_info.karma is None):
			karma_query_res = self.db_cur.execute(
					"""
					SELECT user.lepro_uid, user_rating_data.attitude
					FROM user_rating
					INNER JOIN user_rating_data ON (user_rating.id = user_rating_data.ur_id)
					INNER JOIN user ON (user.id = user_rating.judge_id)
					WHERE user_rating.user_id = ?
					GROUP BY user.lepro_uid
					ORDER BY user_rating_data.observed_date DESC
					""",
					(_id,)
			)
			
			_omit_judge_uid = None
			for _row in karma_query_res:
				print _row
				
				if (_row[0] != _omit_judge_uid):
					_omit_judge_uid = _row[0]
					
					if (user_info.karma.has_key(_row[0])) and (user_info.karma[_row[0]] == _row[1]):
						user_info.karma.pop(_row[0])
						
				
				
		
		return _id
