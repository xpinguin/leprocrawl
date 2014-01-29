#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function
import sys
import httplib
from urllib import urlencode
from httplib import HTTPConnection
import zlib
from time import sleep, time
from datetime import datetime
from multiprocessing import Process, Queue, Pipe, Lock
from threading import Thread, Lock as ThLock
from Queue import Empty as QueueEmptyException
from Queue import Full as QueueFullException
import random
from itertools import chain
import codecs

from config import *
from defs import *
from storage import *
from parsers import *


#------------------------------------------------------------------------------ 
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------ 
print_safe = print

"""
@lazy_init_deco
def print_safe(*args, **kwargs):
	global __safe_print_lock
	
	__safe_print_lock.acquire()
	print(*args, **kwargs)
	__safe_print_lock.release()
	
def print_safe_init():
	global __safe_print_lock
	__safe_print_lock = Lock()
"""	

#------------------------------------------------------------------------------
class LocationRedirect(Exception):
	http_status = None
	http_location = None

class MyHTTPConnection(HTTPConnection):
	def __init__(self, *args, **kwargs):
		HTTPConnection.__init__(self, *args, **kwargs)
		
		self.__http_req_headers = {
			"Accept" : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
			"Accept-Encoding" : "gzip",
			"Accept-Language" :	"en-US,en;q=0.5",
			"Cache-Control" : "max-age=0",
			"Connection" :	"keep-alive",
			"User-Agent" : "Mozilla/5.0 (X11; Linux x86_64; rv:26.0) Gecko/20100101 Firefox/26.0",
			"Content-Type" : "application/x-www-form-urlencoded"
		}
		
		with open("cookie.txt", "rb") as _cookie_f:
			self.__http_req_headers["Cookie"] = _cookie_f.read().strip("\r\n")
			
		self.__lock = Lock()
		self.__last_request_time = datetime.fromordinal(1)
	
	def request(self, method, uri, data, **kwargs):
		# ----------------------------------------------
		def _normalized_sleep(s):
			if (s <= 0): return 0
			sleep(s)
			return s  
		# ----------------------------------------------
		
		self.__lock.acquire()
		
		if ((kwargs.has_key("vhost")) and (kwargs["vhost"] != "")):
			self.__http_req_headers["Host"] = kwargs["vhost"]
		else:
			self.__http_req_headers["Host"] = self.host
			
		uri = uri.encode("utf-8")
		
		while (True):
			_time_slept = _normalized_sleep(
						HTTP_REQUEST_DELAY -
						(datetime.now() - self.__last_request_time).total_seconds()
			)
			print_safe(">>> [%.3f] %s %s %s %s" % (_time_slept, method, 
													self.__http_req_headers["Host"], 
													uri, data)
			)
			
			print(method, uri, data, self.__http_req_headers["Host"])
			HTTPConnection.request(self, method, uri, data, self.__http_req_headers)
			self.__last_request_time = datetime.now()
			
			try:
				resp = self.getresponse()
			except Exception as e:
				print_safe("\n{ERR} exception from the depth of httplib:\n\t%s\n" % repr(e))
				
				self.close()
				self.connect()
				continue
			
			try:
				res = zlib.decompress(resp.read(), 16 + zlib.MAX_WBITS)
			except Exception as e:
				print_safe("\n{ERR} exception from the depth of zlib:\n\t%s\n" % repr(e))
				continue
				
			if (resp.status >= 400):
				res = None
				
			elif (resp.status >= 300):
				_loc_exc = LocationRedirect()
				_loc_exc.http_status = resp.status
				_loc_exc.http_location = resp.getheader("Location", None)
				
				if (_loc_exc.http_location is None):
					res = None
				else:
					self.__lock.release()
					raise _loc_exc
				
			elif (resp.status >= 200) and (not isinstance(res, (str, unicode, buffer))):
				print_safe("\n{ERR} invalid response (code = %u, data_type = %s):\n\t'%s'\n" % 
						(resp.status, str(res.__class__), repr(res))
				)
				continue
			
			break
		
		# ------------------------------------------------------
		self.__lock.release()
		
		return res
		
#------------------------------------------------------------------------------ 

#------------------------------------------------------------------------------ 
#------------------------------------------------------------------------------ 


#===============================================================================
# DATA RETRIEVERS
#===============================================================================

def retrieve_user_info(http_conn, nickname):
	"""
		@return dictionary of user's attributes (except for favorites)
	"""
	if (isinstance(nickname, str)):
		nickname = nickname.decode("utf-8")
	
	user_data_raw = http_conn.request("GET", "/users/%s" % nickname, "")
	
	if (user_data_raw is None):
		return None
	
	user_profile_data = parse_user_profile(user_data_raw)
	user_profile_data["favs"] = None
	
	try:
		user_profile_data["karma"] = parse_rating(
						http_conn.request(
										"POST",
										"/karmactl/",
										"view=%u" % user_profile_data.uid
						)
		)
	#
	#except TypeError
	#	pass
	#	TODO: see retrieve_user_favorites
	#
	except Exception as _e:
		print("\n{ERR} karma of '%s' could not be retrieved due to:\n\t%s\n" % 
				(nickname, repr(_e)))

		user_profile_data["karma"] = None
		
	return user_profile_data

def retrieve_user_favorites(http_conn, nickname):
	"""
		@return list of post_id
	"""
	
	if (isinstance(nickname, str)):
		nickname = nickname.decode("utf-8")
	
	_favs_pages = 1
	_cur_fav_page = 1
	total_favs = []
	
	# ---
	_attempts = 0
	_max_attempts = 5
	# ---
	
	while (_cur_fav_page <= _favs_pages):
		try:
			_cur_favs, _favs_pages = parse_user_favorites(
							http_conn.request(
											"GET",
											"/users/%s/favs/%u/" % (nickname, _cur_fav_page),
											""
							)
			)
		
		except TypeError as _e:
			if (_attempts < _max_attempts):
				_attempts += 1
				continue
			else:
				print("\n{ERR} attempts exceeded in retrieve_user_favorites(%s):\n\t%s\n",
						(nickname, repr(_e))
				)
				break
			
		except LocationRedirect:
			# this means that user do not publish his/her favorites
			return None
		
		_cur_fav_page += 1
		total_favs += _cur_favs
		
	return total_favs


def retrieve_post(http_conn, post_id, sublepra_name):
	"""
		@arg http_conn - valid HTTPConnection()
		@arg post_id - post index
		
		@return dict() with post data and comments (incl. post rating, but without comments' rating)
	"""
	
	if (len(sublepra_name) > 0):
		_sl_hostname = "%s.leprosorium.ru" % sublepra_name
	else:
		_sl_hostname = ""
	# -------------------------------------------------
	
	post_data_raw = http_conn.request("GET", "/comments/%u" % post_id, "", vhost = _sl_hostname)
	if (post_data_raw is None):
		return None
	
	post_data = parse_post_and_comments(post_data_raw)
	
	post_data["sublepra_name"] = sublepra_name
	
	try:
		post_data["rating"] = parse_rating(
								http_conn.request(
												"POST",
												"/votesctl/",
												"id=%u&type=1" % post_id,
												vhost = _sl_hostname
								)
		)
	#
	#except TypeError
	#	pass
	#	TODO: see retrieve_user_favorites
	#
	except Exception as _e:
		print("\n{ERR} rating of post (%u, '%s') could not be retrieved due to:\n\t%s\n" % 
				(post_id, sublepra_name, repr(_e)))

		post_data["rating"] = None
		
	return post_data

def retrieve_comment_rating(http_conn, comment_id, post_id, sublepra_name = ""):
	
	if (len(sublepra_name) > 0):
		_sl_hostname = "%s.leprosorium.ru" % sublepra_name
	else:
		_sl_hostname = ""
	# -------------------------------------------------
	
	try:
		return parse_rating(
					http_conn.request(
							"POST",
							"/votesctl/",
							"id=%u&post_id=%u&type=0" % (comment_id, post_id),
							vhost = _sl_hostname
					)
		)
	#
	#except TypeError
	#	pass
	#	TODO: see retrieve_user_favorites
	#
	except Exception as _e:
		print("\n{ERR} rating of comment (%u, %u) could not be retrieved due to:\n\t%s\n" % 
				(comment_id, post_id, repr(_e)))

		return None
	

def retrieve_sublepras_list(http_conn):
	_sl_pages = 1
	_cur_sl_page = 1
	sublepras = []
	
	while (_cur_sl_page <= _sl_pages):
		_cur_sublepras, _sl_pages = parse_sublepras_list(
										http_conn.request(
														"GET",
														"/underground/created/%u/" % _cur_sl_page,
														""
										)
		)
		_cur_sl_page += 1
		sublepras += _cur_sublepras
	
	"""
	# ---
	for i in xrange(len(sublepras)):
		_sl_info = crawl_sublepra_info(sublepras[i].name)
		if (_sl_info is None): continue
		
		sublepras[i] = ObjDict(sublepras[i].items() + _sl_info.items())
	"""
	
	return sublepras


def retrieve_sublepra_info(http_conn, sublepra_name):
	http_conn = MyHTTPConnection("%s.leprosorium.ru" % sublepra_name)
	
	info_raw_html = http_conn.request("GET", "/controls/", "")
	if (info_raw_html is None):
		return None
	
	return parse_sublepra_info(info_raw_html)



#===============================================================================
# CRAWLERS (ROOT DATA SOURCES)
#===============================================================================

def crawl_sublepra(http_conn, sublepra_name, post_queue, start_page = 0, max_posts_num = None):
	sublepra_name = sublepra_name.lower()
	
	# -------------------------------------------------
	if (len(sublepra_name) > 0):
		_sl_hostname = "%s.leprosorium.ru" % sublepra_name
	else:
		_sl_hostname = ""
	# -------------------------------------------------
	
	last_post_pos = start_page * 42
	
	while (True):
		_page_posts = parse_sublepra_json(
					http_conn.request("POST", "/idxctl/", "from=%u" % last_post_pos, vhost = _sl_hostname)
		)
		
		if (len(_page_posts) == 0): break
		
		# ---
		for _page_post in _page_posts:
			post_queue.put((_page_post.id, False, sublepra_name), block = True, timeout = None)
			
		# ---
		last_post_pos += len(_page_posts)
		if (not max_posts_num is None) and (last_post_pos >= max_posts_num): break
	# ---
	
	return last_post_pos


def crawl_lepra_live(http_conn, post_queue):
	token = 0
	
	while (True):
		new_messages, token = parse_live_messages_list(
										http_conn.request(
															"POST",
															"/livectl/",
															"token=%u" % token
										),
										True
		)
		
		for _msg in sorted(new_messages, key = lambda _m: _m.create_date, reverse = True):
			_post_id = _msg.post_id
			if (_post_id is None): _post_id = _msg.id
			
			post_queue.put((_post_id, True, _msg.sublepra.lower()), block = True, timeout = None)
			
	return token

#------------------------------------------------------------------------------ 
# 	TEST CODE
#------------------------------------------------------------------------------ 

"""
presidents = parse_glagne_presidents(__make_http_request_to_glagne(
				"GET",
				"/elections/president/",
				""
))

#print(pres)
#print
for pres in presidents:
	print("'%s'" % pres.start_date)
	print("'%s'" % pres.end_date)
	print(pres.user_nickname)
	print
"""

"""
democracy = parse_glagne_democracy(__make_http_request_to_glagne(
				"GET",
				"/democracy/",
				""
))
print(democracy)
"""

"""
cand_votes = parse_glagne_elections(__make_http_request_to_glagne(
				"POST",
				"/floridactl/",
				"token=1"# + "&rows[]=10"*5
))

print(len(reduce(lambda res, _v: res + _v, cand_votes.values(), [])))
print
print cand_votes["CCCP"]
#for vd in sorted(cand_votes["Nurmamed"], key = lambda _v: _v[1]):
#	print "'%s' at '%s'" % (vd[0], vd[1])
"""

#===============================================================================
# PARALLEL WORKERS
#===============================================================================

def storage_worker(storage_queue):
	p_stor = PassiveStorage(RAW_DB_PATH)
	
	while (True):
		method_name, args, kwargs = storage_queue.get(block = True, timeout = None)
		
		try:
			_method_res = getattr(p_stor, method_name)(*args, **kwargs)
		except Exception as e:
			print_safe("\n{ERR} Exception caught in %s(%s, %s):\n\t%s\n\n" %
						(method_name, repr(args), repr(kwargs), repr(e))
			)
			continue
		
		# -----
		if (not _method_res):
			# try to reinject method back (may be, it awaits some other method to complete?)
			try:
				storage_queue.put((method_name, args), block = False)
			except QueueFullException:
				continue
		# -----
		
		# ---- DEBUG ----------------------------------------------------
		if (method_name == "store_user"):
			if (args[0].__class__ in (str, unicode)):
				_user_name = args[0]
			elif (args[0].has_key("nickname")):
				_user_name = args[0].nickname
			
			print_safe("<storage> %s('%s')" % (method_name, _user_name))
		
		elif (isinstance(args[0], dict)) and (args[0].has_key("id")):
			print_safe("<storage> %s('%u')" % (method_name, args[0]["id"]))
			
		else:
			print_safe("<storage> %s(...)" % method_name)
			
		
	
def user_handle_worker(storage_queue, user_queue, userfav_queue):
	"""
		random walk
		
		NOTE: non-uniform (like with comments)
				probability of transition from any user to any user (except for self-transition, which is 0)
			
			P(user, user_occur_freq) = user_occur_freq / sum({user_occur_freq(user) | any user})
	"""
	
	http_conn = MyHTTPConnection("leprosorium.ru")
	users_observed = dict()
	users_new = set()
	_total_users_freq = [0]
	_lock = ThLock()
	
	# -----------------------------------------------------
	def _receive_users():
		while (True):
			user_nickname = user_queue.get(block = True, timeout = None)
			
			_lock.acquire()
			
			try:
				users_observed[user_nickname] += 1
			except KeyError:
				users_observed[user_nickname] = 1
				users_new.add(user_nickname)
			
			_total_users_freq[0] += 1
			
			_lock.release()
				
	recv_thread = Thread(target = _receive_users)
	recv_thread.start()
	# -----------------------------------------------------
	
	_prev_rand_user = None
	
	while (True):
		# --------------------
		_lock.acquire()
		
		if (len(users_new) > 0):
			_rand_user = users_new.pop()
			_prev_rand_user = _rand_user
		else:
			_rand_user = None
			
			while (_total_users_freq[0] > 1):
				rand_val = random.randint(0, _total_users_freq[0])
				
				_freq_accu = 0
				for _u_nickname, _freq in chain(((None, 0),), users_observed.iteritems()):
					_freq_accu += _freq
					if (rand_val < _freq_accu):
						_rand_user = _u_nickname
						break

				if (_rand_user != _prev_rand_user):
					_prev_rand_user = _rand_user
					break
				
				sleep(0.1)
		
		_lock.release()
			
		if (_rand_user is None):
			sleep(1)
			continue
		# --------------------
			
		try:
			user_data = retrieve_user_info(http_conn, _rand_user)
		except Exception as e:
			print_safe("\n{ERR} Exception caught in retrieve_user_info('%s'):\n\t%s\n\n" % (_rand_user, repr(e)))
			continue
		
		if (user_data is None):
			storage_queue.put(
								("store_user", (_rand_user,), {"observed_date" : time()}),
								block = True,
								timeout = None
			)
			continue
		
		storage_queue.put(
							("store_user", (user_data,), {"observed_date" : time()}),
							block = True,
							timeout = None
		)
		
		userfav_queue.put((_rand_user, user_data.uid), block = True, timeout = None)
		
		try:
			if (isinstance(user_data.parent_nickname, (str, unicode))):
				user_queue.put(user_data.parent_nickname, block = False)
				
			if (isinstance(user_data.children_nicknames, (tuple, list, set))):
				for _child_u in user_data.children_nicknames:
					user_queue.put(_child_u, block = False)
		except QueueFullException:
			pass
		
	# ---
	recv_thread.join()			
		
			
def user_favs_handle_worker(storage_queue, userfav_queue):
	http_conn = MyHTTPConnection("leprosorium.ru")
	
	while (True):
		current_users = set()
		
		# ------------------------------
		while (True):
			try:
				user_nickname, user_id = userfav_queue.get(block = False)
			except QueueEmptyException:
				break
			
			current_users.add((user_nickname, user_id))
		
		if (len(current_users) > 0):
			print("USERSFAVS_QUEUE_SLICE: '%s'" % str(current_users))
		else:
			sleep(1)
		# ------------------------------
		
		for _u_nickname, _u_id in current_users:
			
			try:
				user_favs = retrieve_user_favorites(http_conn, _u_nickname)
			except Exception as e:
				print_safe("\n{ERR} Exception caught in retrieve_user_favorites('%s'):\n\t%s\n\n" % (_u_nickname, repr(e)))
				continue
			
			if (user_favs is None):
				continue
			
			storage_queue.put(
							(
								"store_user",
								(ObjDict({"uid" : _u_id, "favs" : user_favs}),),
								{"observed_date" : time()}
							),
							block = True,
							timeout = None
			)

			
def post_handle_worker(storage_queue, post_queue, comm_rating_queue, user_queue):
	"""
		random walk
		
		NOTE: non-uniform (like with comments)
				probability of transition from any post to any post (except for self-transition, which is 0)
			
			P(post_id, post_occur_freq) = post_occur_freq / sum({post_occur_freq(post_id) | any post_id})
	"""
	
	http_conn = MyHTTPConnection("leprosorium.ru")
	
	posts_observed = dict()
	posts_new = set()
	posts_sublepras_override = dict()
	
	_total_posts_freq = [0]
	_lock = ThLock()
	
	# -----------------------------------------------------
	def _receive_posts():
		while (True):
			post_id, urgent, sublepra_name = post_queue.get(block = True, timeout = None)
			
			_lock.acquire()
			
			if (posts_sublepras_override.has_key(post_id)):
				sublepra_name = posts_sublepras_override[post_id]
			
			post_desc = (post_id, sublepra_name)
			try:
				posts_observed[post_desc] += 1
				if (urgent): posts_new.add(post_desc)
			except KeyError:
				posts_observed[post_desc] = 1
				posts_new.add(post_desc)
			
			_total_posts_freq[0] += 1
			
			
			_lock.release()
				
	recv_thread = Thread(target = _receive_posts)
	recv_thread.start()
	# -----------------------------------------------------
	
	_prev_rand_post = None
	
	while (True):
		# --------------------
		_lock.acquire()
		
		if (len(posts_new) > 0):
			_rand_post = posts_new.pop()
			_prev_rand_post = _rand_post
		else:
			_rand_post = None
			
			while (_total_posts_freq[0] > 1):
				rand_val = random.randint(0, _total_posts_freq[0])
				
				_freq_accu = 0
				for _post_spec, _freq in chain(((None, 0),), posts_observed.iteritems()):
					_freq_accu += _freq
					if (rand_val < _freq_accu):
						_rand_post = _post_spec
						break

				if (_rand_post != _prev_rand_post):
					_prev_rand_post = _rand_post
					break
				
				sleep(0.1)
		
		_lock.release()
			
		if (_rand_post is None):
			sleep(1)
			continue
		# --------------------
		
		# --------
		_out_cont = False
		while (True):
			try:
				post_data = retrieve_post(http_conn, _rand_post[0], _rand_post[1])
				
			except LocationRedirect as loc_exc:
				real_sublepra_name = \
					re.match(".*?(\w+)\.leprosorium\.ru", loc_exc.http_location, re.U).group(1)
				
				_lock.acquire()
				
				posts_sublepras_override[_rand_post[0]] = real_sublepra_name
				post_freq = posts_observed.pop(_rand_post)

				try:
					posts_new.remove(_rand_post)
				except KeyError:
					pass
				
				_rand_post = (_rand_post[0], real_sublepra_name)
				posts_observed[_rand_post] = post_freq
				
				_lock.release()
				
				continue
				
			except Exception as e:
				print_safe("\n{ERR} Exception caught in retrieve_post(%u, '%s'):\n\t%s\n\n" % \
												(_rand_post[0], _rand_post[1], repr(e)))
				_out_cont = True
			
			break
		if (_out_cont): continue
		# --------
		
		if (post_data is None):
			storage_queue.put(
								("store_post", (_rand_post[0],), {"observed_date" : time()}),
								block = True,
								timeout = None
			)
			continue
		
		storage_queue.put(
							("store_post", (post_data,), {"observed_date" : time()}),
							block = True,
							timeout = None
		)
		# ---
		
		user_queue.put(post_data.author_nickname, block = True, timeout = None)
		
		if (isinstance(post_data.rating, dict)):
			for _rate in post_data.rating.itervalues():
				user_queue.put(_rate[1], block = True, timeout = None)
	
		for _comment in post_data.comments:
			user_queue.put(_comment.author_nickname, block = True, timeout = None)
			comm_rating_queue.put([_comment.id, post_data.id], block = True, timeout = None)
		# ---
	
	# ---
	recv_thread.join()
	
			
def comm_rating_handle_worker(storage_queue, comm_rating_queue, user_queue):
	"""
		random walk over known comment_ids is employed
		
		== pros ==
			1. uniform cover density (broader coverage)
			2. no queue stalls (compare to classic sequential walk)
		== cons ===
			??? 
	"""
	
	
	http_conn = MyHTTPConnection("leprosorium.ru")
	comments_observed = set()
	co_lock = ThLock()
	
	# -----------------------------------------------------
	def _receive_comments():
		while (True):
			comment_id, post_id = comm_rating_queue.get(block = True, timeout = None)
			
			co_lock.acquire()
			comments_observed.add((comment_id, post_id))
			co_lock.release()
				
	recv_thread = Thread(target = _receive_comments)
	recv_thread.start()
	# -----------------------------------------------------
	
	_prev_rand_comm = None
	
	while (True):
			# --------------------
			_rand_comm = None
				
			co_lock.acquire()
			while (len(comments_observed) > 1):
				_rand_comm = random.sample(comments_observed, 1)[0]
				if (_rand_comm != _prev_rand_comm):
					_prev_rand_comm = _rand_comm
					break
				
				sleep(0.1)
			co_lock.release()
			
			if (_rand_comm is None):
				sleep(1)
				continue
			# --------------------
		
			try:
				comm_rating = retrieve_comment_rating(http_conn, _rand_comm[0], _rand_comm[1])
			except Exception as e:
				print_safe(
						"\n{ERR} Exception caught in retrieve_comment_rating('%u, %u'):\n\t%s\n\n" \
								% (_rand_comm[0], _rand_comm[1], repr(e))
				)
				continue
			
			if (comm_rating is None):
				continue
			
			storage_queue.put(
							(
								"store_comment",
								(ObjDict({"id" : _rand_comm[0], "rating" : comm_rating}),),
								{"observed_date" : time()}
							),
							block = True,
							timeout = None
			)
			
			if (isinstance(comm_rating, dict)):
				for _rate in comm_rating.itervalues():
					user_queue.put(_rate[1], block = True, timeout = None)
	
	recv_thread.join()
# --------------------------------------------------------------------------------------		

#===============================================================================
# MAIN LOOP
#===============================================================================
storage_queue = Queue()
user_queue = Queue()
userfav_queue = Queue()
post_queue = Queue()
comm_rating_queue = Queue()

_processes = [
		Process(target = storage_worker, args = (storage_queue,)),
		
		Process(target = user_handle_worker, args = (storage_queue, user_queue, userfav_queue)),
		Process(target = user_favs_handle_worker, args = (storage_queue, userfav_queue)),
		
		Process(target = post_handle_worker, args = (storage_queue, post_queue, comm_rating_queue, user_queue)),
		Process(target = comm_rating_handle_worker, args = (storage_queue, comm_rating_queue, user_queue))
]

for _proc in _processes:
	_proc.daemon = True
	_proc.start()
# ---------------------

glagne_http_conn = MyHTTPConnection("leprosorium.ru")

_crawl_threads = [
		Thread(target = crawl_lepra_live, args = (glagne_http_conn, post_queue)),
		Thread(target = crawl_sublepra, args = (glagne_http_conn, "", post_queue))
]

for _th in _crawl_threads:
	_th.start()
	
for _th in _crawl_threads:
	_th.join()
