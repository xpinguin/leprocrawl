# -------------------------------------
HTTP_REQUEST_DELAY = 1.0

# -------------------------------------
SOCKET_GLOBAL_TIMEOUT = 30
HTTP_RECONNECT_ATTEMPT_DELAY = 15

# -------------------------------------
STRICT_DB_SCHEMA = "../db/schemas/lepra_strict_schema.sql"
STRICT_DB_PATH = "../db/lepra_strict.db"

RAW_DB_SCHEMA = "../db/schemas/lepra_raw_schema.sql"
RAW_DB_PATH = "../db/lepra_raw.db"

# -------------------------------------
cfg_params = {
			"never_halt" : True,
			"collect_greetings" : True,
			
			
			"elections" : False,
			"lepra_live" : True,
			"glagne_metadata" : False,
			
			"all_glagne_posts" : False,
			"all_sublepras_posts" : True
}
