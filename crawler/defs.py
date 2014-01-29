import sys
import re

# -------------------------------------
SUBLEPRA_ACCESS_READ = 0x1
SUBLEPRA_ACCESS_WRITE = 0x2
SUBLEPRA_ACCESS_BANNED = 0x4
SUBLEPRA_ACCESS_MODERATOR = 0x8

#------------------------------------------------------------------------------ 
def lazy_init_deco(func):
	"""
		lazy auto init decorator
	"""
	
	func_module = sys.modules[func.__module__] 
	
	def _func_init_wrap(*args, **kwargs):
		getattr(func_module, func.__name__ + "_init")()	
		setattr(func_module, func.__name__, func)
		
		return func(*args, **kwargs)
		
	return _func_init_wrap

#------------------------------------------------------------------------------ 
class ObjDict(dict):
	def __init__(self, *args, **kwargs):
		dict.__init__(self, *args, **kwargs)
	
	def __getattr__(self, attr_name):
		if (attr_name == "_ObjDict__default_value"):
			raise AttributeError
		
		try:
			return dict.__getitem__(self, attr_name)
		except KeyError as _ke:
			try:
				return self.__default_value
			except AttributeError:
				pass
			
			raise _ke

	def __getstate__(self):
		return self.__dict__.copy()
	
	def __setstate__(self, state):
		self.__dict__ = state
	
	def set_default_value(self, val):
		self.__default_value = val
		
	def remove_default_value(self):
		try:
			del self.__default_value
		except AttributeError:
			pass
		
	"""
	def __repr__(self):
		res = "="*60 + "\n"
		for _k, _v in sorted(self.items(), key = lambda _i: _i[0]):
			res += "%s = '%s'\n" % (str(_k), str(_v))
		res += "="*60 + "\n"*2
		
		return res 
	"""
#------------------------------------------------------------------------------ 
def datetime_to_timestamp(dt):
	return int(dt.strftime("%s"))

#------------------------------------------------------------------------------ 
def dbapi_row_col_by_key(row, key, dbapi_descr):
	try:
		key_id = next(i for i in xrange(len(dbapi_descr)) if (dbapi_descr[i][0] == key))
	except StopIteration:
		return None
	
	return row[key_id]
