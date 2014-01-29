# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import json
from datetime import datetime
import re

from defs import *

#===============================================================================
# GLOBALS
#===============================================================================
__json_invalid_re = re.compile("[\x01-\x1f]+")

class WonderfulSoup(BeautifulSoup):
	def __init__(self, raw_html):
		BeautifulSoup.__init__(self, markup = raw_html, features = "lxml")

#===============================================================================
# FUNCTIONS
#===============================================================================
"""
def __safe_json(json_raw):
	json_raw = __json_invalid_re.sub("", json_raw)
		
	try:
		return json.loads(json_raw)
	except:
		return None
"""

def __parse_json_reply(json_raw):
	json_raw = __json_invalid_re.sub("", json_raw)
	
	try:
		reply_data = json.loads(json_raw)
		
		if (reply_data["status"] != "OK"):
			raise Exception("json reply status bad", json_raw)
	
	except:
		with open("debug/failed_reply_at_%s.json" % datetime.now(), "wb") as _json_f:
			_json_f.write(json_raw)
			
		raise
	
	return reply_data

#------------------------------------------------------------------------------ 
def __parse_user_date(day_spec, mon_spec, year_spec):
	mons_prefix = (u"янв", u"фев", u"мар", u"апр", u"ма", u"июн",
					u"июл", u"авг", u"сен", u"окт", u"ноя", u"дек")
	
	mon_spec = mon_spec.lower()
	mon = None
	
	for i in xrange(len(mons_prefix)):
		if (mons_prefix[i] in mon_spec):
			mon = i
			break
	assert(not mon is None)
	
	return datetime(year = int(year_spec), month = mon+1, day = int(day_spec), hour = 0, minute = 0, second = 0, microsecond = 0)

def __parse_comment_date(date_str):
	date_str = unicode(date_str) # just in case
	datetime_sep_pos = 0
	
	while (datetime_sep_pos > -1):
		datetime_sep_pos = date_str.find(u" в ")
		
		date_spec = date_str[datetime_sep_pos-10:datetime_sep_pos].strip()
		time_spec = date_str[datetime_sep_pos+2:datetime_sep_pos+8].strip()
		
		try:
			if (u"вчера" in date_spec):
				date_spec = datetime.fromordinal(datetime.today().toordinal()-1).strftime("%d.%m.%Y")
			elif (u"сегодня" in date_spec):
				date_spec = datetime.today().strftime("%d.%m.%Y")
			
			return datetime.strptime(date_spec + u" " + time_spec, "%d.%m.%Y %H.%M")
		
		except:
			date_str = date_str[datetime_sep_pos+3:]
			
	return None

def __reduce_contents(tag):
	return reduce(
				lambda _res, _el: _res + "\n" + unicode(_el), 
				tag.contents,
				u""
	).strip()


def __purify_nickname(nickname):
	return nickname.strip("#")

#===============================================================================
# COMMON PARSING
#===============================================================================
def parse_rating(rating_json):
	if (not isinstance(rating_json, (str, unicode))):
		return None
	
	rating_data = __parse_json_reply(rating_json)
	
	res_rating = {}
	
	for _vote in rating_data["votes"]:
		if (_vote.has_key("login")):
			_tgt = (int(_vote["attitude"]), _vote["login"])
		else:
			_tgt = (int(_vote["attitude"]),)
			
		res_rating[int(_vote["uid"])] = _tgt 
		
	return res_rating

def parse_live_messages_list(livectl_json, return_token):
	live_data = __parse_json_reply(livectl_json)
	
	res_msgs = []
	
	for _live_el in live_data["live"].values():
		msg = ObjDict()
		
		msg["sublepra"] = _live_el["domain_url"].split(".")[0]
		
		_time_splt = _live_el["time"].split(":") 
		msg["create_date"] = datetime.now().replace(
								hour = int(_time_splt[0]),
								minute = int(_time_splt[1]),
								second = 0
		)
		
		msg["author_uid"] = int(_live_el["userid"])
		msg["author_nickname"] = __purify_nickname(_live_el["login"].encode("utf-8"))
		msg["author_gender"] = int(_live_el["gender"])
		
		msg["id"] = int(_live_el["id"])
		
		if (_live_el["type"] == ""):
			msg["post_id"] = int(_live_el["postid"])
		else:
			msg["post_id"] = None
		
		# ---
		msg["body"] = _live_el["body"].encode("utf-8")
		# ---
		
		res_msgs.append(msg)
	
	if (return_token):
		res_msgs = (res_msgs, int(live_data["token"]))
		
	return res_msgs
		
	
#===============================================================================
# USER PARSING
#===============================================================================
def parse_user_profile(raw_html):
	ws = WonderfulSoup(raw_html)
	user_data = ObjDict()
	
	# -- proper nickname
	user_data["nickname"] = __purify_nickname(ws.find(class_="username").a.stripped_strings.next())
	
	# -- uid and register date
	_reg_date_m = re.match(
						ur"#([\d.]+).+?с\s+(\d+)\s+(.+?)\s+(\d+)\s+год",
						ws.find(class_="userregisterdate").stripped_strings.next(),
						re.U
	)
	user_data["uid"] = int(_reg_date_m.group(1).replace(".", ""))
	user_data["create_date"] = __parse_user_date(_reg_date_m.group(2), 
												_reg_date_m.group(3), 
												_reg_date_m.group(4))
	
	# -- parent user nickname
	user_data["parent_nickname"] = __purify_nickname(
						ws.find(class_="userparent").a.stripped_strings.next()
	)
	
	# -- children users nicknames
	user_data["children_nicknames"] = []
	try:
		for child_tag in ws.find(class_="userchildren").find_all("a", href = re.compile("/users/.+")):
			user_data["children_nicknames"].append(
						__purify_nickname(child_tag.stripped_strings.next())
			)
	except AttributeError:
		user_data["children_nicknames"] = None # info is absent rather than childfree user :)
		
	# -- real name, city-country
	_user_basic_info = ws.find(class_="userbasicinfo")
	
	try:
		user_data["real_name"] = _user_basic_info.h3.stripped_strings.next()
	except (StopIteration, AttributeError):
		user_data["real_name"] = None
	
	try:
		user_data["country"] = map(
			lambda _s: _s.strip(),
			_user_basic_info.find(class_="userego").stripped_strings.next().split(",")
		)
		if (len(user_data["country"]) > 1):
			user_data["country"], user_data["city"] = user_data["country"][-2:]
		else:
			user_data["city"] = None
			user_data["country"] = user_data["country"][0]		
	except (StopIteration, AttributeError):
		user_data["city"] = None
		user_data["country"] = None
	
	# -- gender
	if (u"написала" in (u" ".join(ws.find(class_="userrating").stripped_strings)).lower()):
		user_data["gender"] = 0
	else:
		user_data["gender"] = 1
	
	# -- vote stuff
	_vote_data_m = re.match(
						ur"Вес\s+голоса.+?(\d+).*?Голосов\s+в\s+день.+?(\d+)",
						"".join(ws.find(class_="uservoterate").stripped_strings),
						re.U
	)
	user_data["vote_weight"] = int(_vote_data_m.group(1))
	user_data["max_votes_per_day"] = int(_vote_data_m.group(2))
	
	# -- profile content
	_user_story_tag = ws.find(class_="userstory")
	if (not _user_story_tag is None):
		user_data["profile_content_raw"] = __reduce_contents(_user_story_tag)
	else:
		user_data["profile_content_raw"] = None
	
	return user_data

def parse_user_favorites(page_raw_html):
	ws = WonderfulSoup(page_raw_html)
	favs_list = []
	
	for _post_tag in ws.find_all(lambda _tag: (_tag.name == "div") \
								and (_tag.attrs.has_key("class")) \
								and ("post" in _tag.attrs["class"])):
		
		try:
			favs_list.append(int(_post_tag.attrs["id"][1:]))
		except:
			pass
		
	if (len(favs_list) > 0):	
		total_pages_num = int(ws.find(id="total_pages").strong.stripped_strings.next())
	else:
		total_pages_num = 0
	
	return (favs_list, total_pages_num)
				

#===============================================================================
# POST AND COMMENTS PARSING
#===============================================================================
def parse_post_and_comments(raw_html):
	_post_id_re = re.compile(ur"p(\d+)", re.U)
	_user_id_re = re.compile(ur".*?'u(\d+)'", re.U)
	# ---
	
	ws = WonderfulSoup(raw_html)
	post_data = ObjDict()
	
	_post_tag = ws.find("div", id=_post_id_re, class_=("post", "ord"))
	post_data["id"] = int(_post_id_re.match(_post_tag.attrs["id"]).group(1))
	post_data["content"] = __reduce_contents(_post_tag.find("div", class_="dt"))
	post_data["is_gold"] = int("golden" in _post_tag.attrs["class"])
	
	_post_metadata_tag = _post_tag.find("div", class_="dd").find("div", class_="p")
	if (_post_metadata_tag is None): 
		_post_metadata_tag = _post_tag #.find("div", class_="dt")
		
	post_data["author_nickname"] = __purify_nickname(
		_post_metadata_tag.find("a", href=re.compile(ur"/users/.+", re.U)).stripped_strings.next()
	)
				
	post_data["author_uid"] = int(_user_id_re.match(
						_post_metadata_tag.find("a", class_="u", onclick=_user_id_re).attrs["onclick"]
					).group(1))
	
	post_data["create_date"] = __parse_comment_date("".join(_post_metadata_tag.stripped_strings))
	
	# --- do comments
	post_data["comments"] = []
	
	for _comment_tag in ws.find_all(lambda _tag: (_tag.name == "div") \
												and (_tag.attrs.has_key("class")) \
												and (_tag.attrs.has_key("id")) \
												and ("post" in _tag.attrs["class"]) \
												and ("tree" in _tag.attrs["class"])
										):
		_comm = ObjDict()
		_comm["id"] = int(_comment_tag.attrs["id"])
		
		for _class_name in _comment_tag.attrs["class"]:
			if (_class_name[0] == u"u"):
				_comm["author_uid"] = int(_class_name[1:])
			else:
				_indent = _class_name.split(u"indent_")
				if (len(_indent) > 1):
					_comm["indent"] = int(_indent[1])
		
		_comm["content"] = __reduce_contents(_comment_tag.find("div", class_="dt"))
		
		_comment_metadata_tag = _comment_tag.find("div", class_="dd")
		if (_comment_metadata_tag is None): 
			_comment_metadata_tag = _comment_tag #.find("div", class_="dt")
		
		_comm["author_nickname"] = __purify_nickname(
					_comment_metadata_tag.find("a", href=re.compile(ur"/users/.+", re.U)).stripped_strings.next()
		)
		_comm["create_date"] = __parse_comment_date("".join(_comment_metadata_tag.find("div", class_="p").stripped_strings))
		
		try:
			_comm["total_rating"] = int(_comment_metadata_tag.find("span", class_="rating").stripped_strings.next())
		except AttributeError:
			_comm["total_rating"] = None
		# ---
		
		post_data["comments"].append(_comm)
	
	return post_data



#===============================================================================
# SUBLEPRA(S) PARSING
#===============================================================================
def parse_sublepras_list(page_raw_html):
	ws = WonderfulSoup(page_raw_html)
	sublepras_list = []
	
	_sublepras_tags = ws.find_all("div", class_="jj_general_text")
	if (_sublepras_tags is None):
		raise Exception("no <div> tags with class == 'jj_general_text'")
	
	for _sublepra_tag in _sublepras_tags:
		sublepra_data = ObjDict()
		
		try:
			sublepra_data["title"] = _sublepra_tag.h5.stripped_strings.next()
		except StopIteration:
			sublepra_data["title"] = ""
			
		sublepra_data["name"] = \
			_sublepra_tag.find("a", class_="jj_link").stripped_strings.next().split(".")[0]
			
		_block_semi = _sublepra_tag.find("div", class_="block_semi")
		if (_block_semi is None):
			sublepra_data["id"] = None
		else:
			sublepra_data["id"] = int(_block_semi.label.attrs["for"].split("_")[-1])
		
		sublepras_list.append(sublepra_data)
	
	# ---
	total_pages_num = int(ws.find("div", id="total_pages").strong.stripped_strings.next())
		
	return (sublepras_list, total_pages_num)


def parse_sublepra_info(raw_html):
	if (len(raw_html.strip()) == 0): return None
	
	ws = WonderfulSoup(raw_html)
	sublepra_data = ObjDict()
	
	if (not ws.find("body", id="sublepro_aceess_denied") is None):
		return None
	
	try:
		sublepra_data["owner_nickname"] = __purify_nickname(
			ws.find("div", class_="creator").find("a", href=re.compile(ur"/users/.+")).stripped_strings.next()
		)
		
		_create_date_m = re.match(
							ur".*?(\d+)\s+(.+?)\s+(\d+).*",
							ws.find(class_="sublepro_info").find(class_="block_semi").stripped_strings.next(),
							re.U
		)
	
	except StopIteration:
		return None
	
	sublepra_data["create_date"] = __parse_user_date(_create_date_m.group(1), 
												_create_date_m.group(2), 
												_create_date_m.group(3))
	
	# --------------------------------------------------------------------------
	def _list_nicknames(div_id):
		_cont_tag = ws.find("div", id=div_id)
		if (_cont_tag is None):
			return []
		
		if ((_cont_tag.attrs.has_key("class")) and ("hidden" in _cont_tag.attrs["class"])):
			return []
		
		_list_tags = _cont_tag.find_all("li")
		if (_list_tags is None):
			return []
		
		return [__purify_nickname(_li.a.stripped_strings.next()) for _li in _list_tags]
	# --------------------------------------------------------------------------	
		
			
	sublepra_data["moderators_nicknames"] = _list_nicknames("js-ministers_list")
	sublepra_data["readers_nicknames"] = _list_nicknames("js-read_list")
	sublepra_data["writers_nicknames"] = _list_nicknames("js-write_list")
	sublepra_data["banned_nicknames"] = _list_nicknames("js-banned_list")
	
	return sublepra_data

def parse_sublepra_json(json_raw):
	sl_data = __parse_json_reply(json_raw)
	
	if (int(sl_data["count"]) == 0): return []
	
	# ---
	res_posts = []
	
	for _sl_post in sl_data["posts"].values():
		if (_sl_post.__class__ != dict): continue
		
		_post = ObjDict()
		
		_post["id"] = int(_sl_post["id"])
		_post["author_uid"] = int(_sl_post["user_id"])
		_post["was_gold"] = int(_sl_post["was_gold"])
		
		res_posts.append(_post)
	
	return res_posts

#===============================================================================
# DEMOCRACY-ON-GLAGNE PARSING
#===============================================================================
def parse_glagne_democracy(raw_html):
	ws = WonderfulSoup(raw_html)
	dem_data = ObjDict()
	
	# -- president
	_pres_tag = ws.find("div", id="president")
	dem_data["president"] = None
	dem_data["president_start_date"] = None
	dem_data["president_end_date"] = None
	
	if (not _pres_tag is None):
		_pres_tag = _pres_tag.find("a", href=re.compile(ur"/users/.+", re.U))
		if (not _pres_tag is None):
			try:
				dem_data["president"] = _pres_tag.stripped_strings.next()
			except StopIteration:
				pass
			
			# consider anarchy: dates are presented, but no president in da house
			_rule_date_tag = _pres_tag.find_next_sibling("p")
			if (not _rule_date_tag is None):
				_rule_date_m = re.match(
							ur".*?с\s+(\d{1,2})\.(\d\d)\s+по\s+(\d{1,2})\.(\d\d)",
							" ".join(_rule_date_tag.stripped_strings),
							re.U
				)
				if (not _rule_date_m is None):
					dem_data["president_start_date"] = datetime(
												year = datetime.now().year,
												month = int(_rule_date_m.group(2)),
												day = int(_rule_date_m.group(1))
					)
					dem_data["president_end_date"] = datetime(
												year = datetime.now().year,
												month = int(_rule_date_m.group(4)),
												day = int(_rule_date_m.group(3))
					)
	
	# ------------------------------------------------------------------------------
	def _handle_whitehouse_list(list_name, cont_tag_sibling = False):
		list_name = list_name.lower()
		
		_cont_tag = ws.find_all(lambda _tag: (list_name in "".join(_tag.stripped_strings).lower()))[-1]
		if (_cont_tag is None): return None
		
		if (cont_tag_sibling):
			_cont_table = _cont_tag.find_next_sibling("table")
		else:
			_cont_table = _cont_tag.find("table")
		
		if (_cont_table is None): return None 
		
		res = []
		for _cont_tr in _cont_table.find_all("tr"):
			res.append(__purify_nickname(_cont_tr.a.stripped_strings.next()))
				
		return res
	# ------------------------------------------------------------------------------
	
	# -- ministers, former ministers and banned
	dem_data["ministers_nicknames"] = _handle_whitehouse_list(u"являются министрами")
	dem_data["former_ministers_nicknames"] = _handle_whitehouse_list(u"бывшие министры", True)
	dem_data["banned_nicknames"] = _handle_whitehouse_list(u"трудовой лагерь")
	
	return dem_data

def parse_glagne_presidents(raw_html):
	_rule_date_re = re.compile(ur".*?(\d\d)\.(\d\d)\.(\d\d\d\d)", re.U | re.S)
	# ---
	
	ws = WonderfulSoup(raw_html)
	presidents = []
	
	_ex_img_tag = ws.find("img", src=re.compile(ur"ex-presidents.gif", re.U))
	if (_ex_img_tag is None):
		raise Exception("no <img> tag in presidents list")
	
	_pres_table_tag = _ex_img_tag.find_parent("table")
	if (_pres_table_tag is None):
		raise Exception("no <table> tag in presidents list")
	
	try:
		_pres_trs = _pres_table_tag.find_all("tr")[1:]
	except IndexError:
		return []
	
	for _pres_tr in _pres_trs:
		row = _pres_tr.find_all("td")
		president = ObjDict()
		
		_date_nav_str = row[0].stripped_strings
		_start_date_m = _rule_date_re.match(_date_nav_str.next())
		_end_date_m = _rule_date_re.match(_date_nav_str.next())
		
		if (_start_date_m is None):
			president["start_date"] = None
		else:
			president["start_date"] = datetime(
											year = int(_start_date_m.group(3)),
											month = int(_start_date_m.group(2)),
											day = int(_start_date_m.group(1))
									)
			
		if (_end_date_m is None):
			president["end_date"] = None
		else:
			president["end_date"] = datetime(
											year = int(_end_date_m.group(3)),
											month = int(_end_date_m.group(2)),
											day = int(_end_date_m.group(1))
									)
			
		president["user_nickname"] = __purify_nickname(row[1].a.stripped_strings.next())
		
		presidents.append(president)
		
	return presidents

def parse_glagne_elections(elec_json_raw):
	elec_data = __parse_json_reply(elec_json_raw)
	
	cand_votes = dict()
	
	for _vote in elec_data["votes"]:
		if (_vote.has_key("vote_date")):
			_vote["voter"] = (_vote["voter"], datetime.fromtimestamp(int(_vote["vote_date"])))
		
		if (cand_votes.has_key(_vote["candidate"])):
			cand_votes[_vote["candidate"]].append(_vote["voter"])
		else:
			cand_votes[_vote["candidate"]] = [_vote["voter"]]
		
	return cand_votes
