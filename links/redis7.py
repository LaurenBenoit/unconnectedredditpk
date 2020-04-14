import redis, time
import ujson as json
from random import random
import json as json_backup
from operator import itemgetter
from multiprocessing import Pool
from django.db.models import F
from templatetags.s3 import get_s3_object
from score import PUBLIC_SUBMISSION_TTL, VOTE_SPREE_ALWD, FBS_PUBLIC_PHOTO_UPLOAD_RL, NUM_TRENDING_PHOTOS, CONTEST_LENGTH, TRENDER_RANKS_TO_COUNT,\
UPPER_RELATIONSHIP_UVOTE_CUTOFF, UPPER_RELATIONSHIP_DVOTE_CUTOFF, MEANINGFUL_VOTING_SAMPLE_SIZE, NUM_VOTES_TO_TGT, BAYESIAN_PROB_THRESHOLD_FOR_VOTE_NERFING,\
TOPIC_UNSUB_LOCKING_TIME, TOPIC_SUBMISSION_TTL, TOPIC_LIFELINE, VOTING_CLOSED_ARCHIVE_OVERFLOW_TIME, PUBLIC_TEXT_QUALITY_THRESHOLD_LENGTH, \
MAX_PUBLIC_IMG_WIDTH, REMOVAL_RATE_LIMIT_TIME
from page_controls import ITEMS_PER_PAGE_IN_ADMINS_LEDGER, DEFENDER_LEDGERS_SIZE, GLOBAL_ADMIN_LEDGERS_SIZE
from redis3 import retrieve_user_world_age, exact_date
from abuse import FLAGGED_PUBLIC_TEXT_POSTING_WORDS
from redis4 import retrieve_bulk_credentials
from models import Link, Photo, Cooldown
from collections import defaultdict
from colors import COLOR_GRADIENTS
from location import REDLOC7

POOL = redis.ConnectionPool(connection_class=redis.UnixDomainSocketConnection, path=REDLOC7, db=0)

THREE_MONTHS = 3*4*7*24*60*60
TWO_MONTHS = 2*4*7*24*60*60  
ONE_MONTH = 4*7*24*60*60 
TWO_WEEKS = 2*7*24*60*60 
ONE_WEEK = 7*24*60*60
FOUR_DAYS = 4*24*60*60
THREE_DAYS = 3*24*60*60
TWO_DAYS = 2*24*60*60
ONE_DAY = 24*60*60
TWELVE_HOURS = 12*60*60
SIX_HOURS = 6*60*60
THREE_HOURS = 3*60*60
ONE_HOUR = 60*60
THIRTY_MINS = 60*30
TWENTY_MINS = 20*60
TEN_MINS = 10*60
FOUR_MINS = 4*60
ONE_MIN = 60
FORTY_FIVE_SECS = 45
THREE_SECS = 3
NINE_SECS = 9


DEFENDER_ADDITION_RATE_LIMITED = "darl:" #prefix for key that rate limits super admins from adding new defenders (FOUR_MINS each try)
DEFENDERS = "defs" # sorted set containing data of current defenders
DEFENDER_DATA = "dd:" # hash containing privileges available to defenders (in order to create M1, M2, etc)
DEFENDERS_FOREVER = 'defs_forever' # sorted set containing data of all defenders ever appointed


DEFENDERS_LEDGER = "dlg:" #prefix for a list which records the defenders last 40 blocks
GLOBAL_ADMINS_LEDGER = "ledger" # a global list for super admins, contains latest 3000 blocks
GLOBAL_ADMINS_REJECTIONS_LEDGER = "rejection_ledger" # a global list for super admins, contains latest 3000 rejected reports
DEFENDER_CASE_COUNT = "dcn:" #hash prefix for a running counter of how many cases a said defender handled


COMPLAINT_LIST = "cl" #sorted set containing all reported content hashes (useful for 'cull list' view)
COMPLAINTS_SUBMITTED = "cs:" #sorted set logging complaint objs submitted by regular users (contains most recent 20 reports of a user)
COMPLAINT_HIST_OBJ = "co:" # a simple key containing a json object with complaint details logged by a regular user, used in 'historical' view of who reported what
COMPLAINT = "c:" #prefix for content, mehfil or profile report hash - contains all appended complaints for the same object, used in 'cull-list' etc
PAYABLES = "p:" #prefix for content payables sorted set - contains all point amounts owed to all reporter ids


COMPLAINING_RATE_LIMITED = "crl:" #prefix for sorted set used to rate limit regular users from reporting content too fast
COMPLAINER_TIME_LIST = "ctl" # sorted set containing time-sorted instances of latest time a user made any report
COMPLAINER_CORRECT_TIME_LIST = "cctl" # sorted set containing time-sorted instances of latest time a user made a 'correct' report
COMPLAINER_ATTEMPT_SORTED_SET = "cass" # sorted set containing sorted (by volume) instances of all reports made by a user
COMPLAINER_CORRECT_SORTED_SET = "ccss" # sorted set containing sorted (by volume) instances of correct reports made by a user
TOP_50_CACHED_DATA = "top_50_reporters" # key containing cached data of top 50 reporters

TROLLS = 'trolls'# a sorted set containing users who have been marked as trolls by defenders

CONTENT_SUBMISSION_AND_VOTING_BAN = "csv:"#prefix for hash containing details about a ban levied by a defender on a user
CONTENT_BAN_TEMP_KEY = "cbtk:"#prefix for key containing temporary data regarding a potentially bannable user
#HOME_FEED = "homefeed:1000" # list containing latest 1000 home feed hashes (e.g. tx:234134 or img:341243)
HOME_SORTED_FEED = "homesortedfeed:1000" # sorted set containing latest 1000 home feed hashes (e.g. tx:234134 or img:341243)
TRENDING_HOME_FEED = 'trendinghomefeed:1000'
PHOTO_FEED = "photofeed:1000" # list containing latest 1000 photo feed hashes (e.g. img:234132)
PHOTO_SORTED_FEED = "photosortedfeed:1000" # sorted set containing latest 1000 photo hashes (e.g. img:234134 or img:341243)
ALT_BEST_PHOTO_FEED = 'altbestphotofeed'
TRENDING_PHOTO_FEED = 'trendingphotofeed:1000'
ALT_TRENDING_PHOTO_FEED = 'alttrendingphotofeed:1000'
TRENDING_PHOTO_DETAILS = 'trendingphotodetails:1000'
# TRENDING_PICS_AND_TIMES = 'trendingphotosandtimes'# list containing trending pics (as values) and times (as scores)
# TRENDING_PICS_AND_USERS = 'trendingphotosandusers'# list containing trending pics (as values) and user_ids (as scores)
TRENDING_FOTOS_AND_TIMES = 'tft'# list containing trending pics (as values) and times (as scores)
TRENDING_FOTOS_AND_USERS = 'tfu'# list containing trending pics (as values) and user_ids (as scores)
HAND_PICKED_TRENDING_PHOTOS = 'handpickedphotos'#sorted set containing hand-picked photos meant to show up in trending
BEST_PHOTO_FEED = "bestphotofeed:1000"# list containing best 1000 photo feed hashes (e.g. img:123123)
BEST_HOME_FEED = "besthomefeed:1000"# list containing best 1000 home feed hashes (e.g. tx:122123 or img:123123)
VOTE_ON_IMG = "vi:" #prefix for a sorted set that contains users who voted on a particular image. Each user's vote value is used as a score
VOTE_ON_TXT = "vt:" #prefix for a sorted set that contains users who voted on a particular text post. Each user's vote value is used as a score


FBS_PUBLIC_PHOTO_UPLOAD_RATE_LIMIT = 'fbsuprl:'#rate limit key to throttle FBS users from uploading way too many public photos


CACHED_TOP_STARS = 'cts:'
CACHED_PUBLIC_REPLY = 'crep:'

USER_SUBMISSIONS_AND_EXPIRES = 'use'# list containing all submissions from all users (sorted by expiry time) circulating in various feeds (in <feed_id>*<obj_hash> format)
USER_SUBMISSIONS_AND_SUBMITTERS = 'uss'# list containing all submissions from all users (sorted by submitter ids) circulating in various feeds (in <feed_id>*<obj_hash> format)
TOP_TRENDING_SUBMITTERS = "tts"# sorted set that contains top trenders alongwith their scores (i.e. num pics in trending)

GLOBAL_VOTES_AND_TIMES = 'gvt'# global sorted set hold voting data of the entire user-base, sorted by time (trimmed to last 1 month)
VOTER_UVOTES_AND_TIMES = "vuvt:"# voter specific sorted set hold upvoting data of the voter, sorted by time (trimmed to last 1 month)
VOTER_DVOTES_AND_TIMES = "vdvt:"# voter specific sorted set hold downvoting data of the voter, sorted by time (trimmed to last 1 month)
ALL_UVOTES_TO_TGT_USER = "ut:"# voter and target user specific sorted set containing all upvotes given by the voter to a target (trimmed to last 1 month)
ALL_DVOTES_TO_TGT_USER = "dt:"# voter and target user specific sorted set containing all downvotes given by the voter to a target (trimmed to last 1 month)

UVOTER_AFFINITY = 'uvaf'# global sorted set containing up votes dropped by users to various targets - useful for catching sybil behavior
DVOTER_AFFINITY = 'dvaf'# global sorted set containing down votes dropped by users to various targets - useful for catching hater behavior
DVOTER_AFFINITY_TRUNCATOR = 'dvat'# global sorted set containing the first time a voter gave a downvote vote to a target_user. Useful for truncating DVOTER_AFFINITY sorted set
UVOTER_AFFINITY_TRUNCATOR = 'uvat'# global sorted set containing the first time a voter gave an upvote vote to a target_user. Useful for truncating UVOTER_AFFINITY sorted set
VOTER_AFFINITY_HASH = 'vah:'# this contains the affinity (Bayesian prob) existing in the voting relationship

SYBIL_RELATIONSHIP_LOG = 'srl'# a global sorted set logging all sybil/enemy relationships for given voter_ids
VOTING_RELATIONSHIP_LOG = 'vrl'# global sorted set logging all sybil/enemy relationships for given target_user_ids
VOTING_RELATIONSHIP_LOG_TRUNCATOR = 'vrlt'# global sorted set useful for truncating VOTING_RELATIONSHIP_LOG over time
CACHED_VOTING_RELATIONSHIP = 'cvr:'# key that caches the sybil/data associated to a given target_user_id (for super defender's viewing pleasure)
CACHED_REV_SYB_RELATIONSHIP = 'crsr:'# key that caches the reverse-sybil/data associated to a given voter_id (for super defender's viewing pleasure)
LATEST_REVERSION_TIMES = "lrt"# global sorted set holding latest times that a vote reversion occured between a voter_id:poster_id pairs

TOP_TRENDERS = 'tt'	# A cached json object of trenders
TOP_TRENDER_IDS = 'tti'# a sorted set containing top trender IDs. Can be used to show a 'verified' symbol next to their names
TOP_TRENDERS_REP = 'ttr'# a sorted set containing how many times a top trender has entered trending and stayed there
TOP_TRENDERS_REP_TRUNCATOR = 'ttrt'# sorted set used to truncate TOP_TRENDERS_REP for those who become inactive (i.e. don't show up for 3 months)

CACHED_UPVOTING_DATA = 'cud:'# a key holding a json object containing the detailed voting history of a voter
CACHED_OLD_UPVOTING_DATA = 'coud:'# a key holding a json object containing the detailed voting history of a voter (only 'old objs')

VOTER_HANDPICKED_PROBS = 'vhp'# sorted set containing voter_ids and the prob their editorially picked content will be handpicked
VOTER_AUD_LIKE_PROBS = 'valp'# sorted set containing various voter_ids and the prob their editorially picked content will see audience likes (called 'like_prob')
NUM_EDITORIAL_LIKES = 'nel'# sorted set containing number of editorial likes given by various voters (can be cross-referenced with 'valp' above)
GLOBAL_EDITORIAL_LIKES_ON_IMGS = 'gelon'# global sorted set containing all editorial 'likes' cast on images
GLOBAL_CLOSED_IMG_LIKES = 'gcil'# global sorted set that contains voting data on images where voting has closed
GLOBAL_CLOSED_IMG_OBJ_HASH_NAMES = 'gciohn'# global sorted set that contains obj hash names of images, where voting has closed
GLOBAL_IMG_LIKES = 'gil'# global sorted set that temporarily stores all votes given to img objs
AUDIENCE_LIKED_IMG_HASH_NAMES = 'alihn'# set of img obj_hashes that have at least a single audience 'like'
HANDPICKED_IMG_HASH_NAMES = 'hihn'# set of img obj_hashes that have been handpicked

LOCKED_IMG = 'li:'# set that contains sybil 'likes' given to an img obj - these lock the img from entering trending
HANDPICKED_TRENDING_IMG = 'hti:'# a key that signifies that a certain obj has entered trending by way of being handpicked
NONHANDPICKED_TRENDING_IMG = 'nti:'# a key that signifies that a certain obj has entered trending by way of being voted on by regular voters

MOST_RECENT_IMG_UPLOAD_TIME = 'mriut:'#key that saves the most recent time a user uploaded an img - useful for truncating reps of churned users
GLOBAL_HANDPICKED_IMG_DATA = 'ghid'#global sorted set containing image_hashes+":"+uploader_ID of imgs which were handpicked for trending
GLOBAL_AUD_LIKED_IMG_OBJS = 'galio'# sorted set containing number of images that received audience likes for each uploader

GLOBAL_UPLOADED_IMG_VOLUME = 'guiv'# global sorted set containing num images that were uploaded by a certain user
GLOBAL_IMG_UPLOADER_AUD_LIKE_BASED_REP = 'giualbr'# global sorted set containing the content 'rep' of img uploaders, based on audience 'likes'
GLOBAL_IMG_UPLOADER_HANDPICKING_BASED_REP = 'giuhbr'# global sorted set containing the content 'rep' of img uploaders, based on handpicked imgs

MOST_RECENT_TEXT_SUBMISSION_TIME = 'mrtst:'#key that saves the most recent time a user submitted text - useful for truncating reps of churned users
GLOBAL_SUBMITTED_TXT_VOLUME = 'gstv'# global sorted set containing num text posts that were submitted by a certain user
GLOBAL_HIGH_REP_HANDPICKED_TXT_OBJS = 'ghrhto'# sorted set containing number of text posts that received likes from high-rep voters (per submitter)
GLOBAL_TXT_SUBMITTER_HIGH_REP_HANDPICKER_BASED_REP = 'gtshrhbr' # global sorted set containing the content 'rep' of txt submitters, based on handpicking by 'high-rep' voters (whose rep is sourced by handpick img rep)

LOCKED_TXT = 'lt:'# set that contains sybil 'likes' given to a text obj - these lock the text from entering trending
GLOBAL_RECENT_PUBLIC_TEXTS = 'grpt'# sorted set containing previous ~800 posts - useful for catching dups

TEMP_POST_DATA = 'tpd:' # temporary data store for share functionality

REMOVAL_RATE_LIMIT = 'rrl:'# rate limit key to limit rate of 'remove' commands a user can issue on their posted objs

GLOBAL_UPLOADED_IMGS = 'gui'

STAR_SCORE = 'star_score'

##################################################################################################################
################################# Detecting duplicate images post in public photos ###############################
##################################################################################################################


def already_exists(photo_hash,categ=None):
	my_server = redis.Redis(connection_pool=POOL)
	if categ == 'ecomm':
		exists = my_server.zscore("perceptual_hash_used_item_set", photo_hash)
	else:
		exists = my_server.zscore("img_perceptual_hash", photo_hash)
	return exists


def insert_hash(photo_id, photo_hash,categ=None):
	"""
	Saves a 'thumb-print' of uploaded images in order to detect duplicate uploads
	"""
	set_name = "perceptual_hash_used_item_set" if categ == 'ecomm' else "img_perceptual_hash"# old name: remove it - "perceptual_hash_set"
	##########################
	my_server = redis.Redis(connection_pool=POOL)
	try:
		limit = 500 if categ == 'ecomm' else 50000
		size = my_server.zcard(set_name)
		my_server.zadd(set_name, photo_hash, photo_id)
		if size >= (limit+1):
			my_server.zremrangebyrank(set_name, 0, 10)# removing the oldest 10 hashes
	except:
		my_server.zadd(set_name, photo_hash, photo_id)


# def delete_avg_hash(hash_list, categ=None):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	if hash_list:
# 		if categ == 'ecomm':
# 			my_server.zrem("perceptual_hash_used_item_set", *hash_list)
# 		else:
# 			my_server.zrem("perceptual_hash_set", *hash_list)
# 			my_server.zrem("img_perceptual_hash", *hash_list)


##################################################################################################################
########################################## Content posted on the platform ########################################  
##################################################################################################################


def retrieve_text_quality(text,lower_text,text_lang,is_being_reposted):
	"""
	Flags posts as 'low quality' if some obvious quality compromises are present

	Helper func for add_text_post() and add_topic_post()
	"""
	if is_being_reposted:
		# is an obvious repost
		return '1'

	##########

	text_len = len(text)

	if text_len < PUBLIC_TEXT_QUALITY_THRESHOLD_LENGTH:
		# 'short post': short-posts are considered low-quality
		return '1'


	##########

	flag_text = False
	for word in FLAGGED_PUBLIC_TEXT_POSTING_WORDS:
		if word in lower_text:
			flag_text = True
			break

	if flag_text:
		# 'illegal words': this post is blocked from trending forever
		return '1'

	##########
	
	other_chars = 0
	for c in text:
		if u'\u0600' <= c <= u'\u06FF' or u'\uFB50' <= c <= u'\uFEFF':
			# urdu is readable
			pass
		elif c.isalpha():
			# eng is readable
			pass
		else:
			# these chars may not be deemed readable content
			other_chars += 1
	other_char_ratio = (other_chars*1.0)/text_len
	if text_lang == '1':
		# text is english
		if other_char_ratio > 0.3:# this threshold was determined after some analysis
			return '1'
	else:
		# text is urdu
		if other_char_ratio > 0.32:# this threshold was determined after some analysis
			return '1'

	##########

	# post doesn't suffer from any obvious quality defects
	return '0'


def add_text_post(obj_id, categ, submitter_id, submitter_av_url, submitter_username, is_star, text, submission_time, \
	from_fbs, type_of_object, comments, add_to_feed=False, poster_defined_expiry_time=None):
	"""
	Creating text object (used in home feed, etc)
	"""
	obj_id = str(obj_id)
	submitter_av_url = get_s3_object(submitter_av_url,category='thumb')#pre-convert avatar url for the feed so that we don't have to do it again and again
	hash_name, audience_type = "tx:"+obj_id, type_of_object[1]
	immutable_data = {'i':obj_id,'c':categ,'sa':submitter_av_url,'si':submitter_id,'su':submitter_username, 't':submission_time,\
	'd':text,'h':hash_name,'com':comments, 'ot':type_of_object[0], 'aud':audience_type}

	expiry = type_of_object[2]
	if expiry:
		immutable_data['exp'] = expiry
	if from_fbs:
		immutable_data["fbs"] = '1'
	if is_star:
		immutable_data['s'] = '1'
	if poster_defined_expiry_time:
		immutable_data['et'] = poster_defined_expiry_time
	
	mapping = {'nv':'0','uv':'0','dv':'0','blob':json.dumps(immutable_data)}
	
	my_server = redis.Redis(connection_pool=POOL)

	######################################################
	# flagging low quality posts based on certain text criteria
	if audience_type == 'p':
		lower_text = text.lower()
		mapping['lq'] = retrieve_text_quality(text=text,lower_text=lower_text,text_lang=categ,\
			is_being_reposted=my_server.zscore(GLOBAL_RECENT_PUBLIC_TEXTS,lower_text))

	######################################################
	
	time_now = time.time()
	expire_at = int(time_now+PUBLIC_SUBMISSION_TTL)
	pipeline1 = my_server.pipeline()
	pipeline1.hmset(hash_name,mapping)
	pipeline1.expireat(hash_name,expire_at)#setting ttl to one day
	
	#### initialize voting sorted set ####
	obj_vote_store_key = VOTE_ON_TXT+obj_id
	pipeline1.zadd(obj_vote_store_key,-1,-1)
	pipeline1.expireat(obj_vote_store_key,expire_at)
	pipeline1.execute()
	if add_to_feed:
		add_obj_to_home_feed(submitter_id, time_now, hash_name, my_server)


def add_obj_to_home_feed(submitter_id, time_now, hash_name, my_server=None):
	"""
	Adding various objects to home feed
	"""
	my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
	my_server.zadd(HOME_SORTED_FEED, hash_name, time_now)
	if random() < 0.2:
		# every now and then, trim the sorted set for size
		my_server.zremrangebyrank(HOME_SORTED_FEED, 0, -1001)# to keep top 1000 in the sorted set
	log_user_submission(submitter_id=submitter_id, submitted_obj=hash_name, expire_at=int(time_now+PUBLIC_SUBMISSION_TTL), \
		feeds_to_add=[HOME_SORTED_FEED], my_server=my_server)


def retrieve_photo_feed_index(obj_hash, feed_type='best_photos'):
	"""
	Returns exact index an object is stored at in PHOTO_SORTED_FEED or TRENDING_PHOTO_FEED

	Useful when needing to redirect to precise object after interacting with a post
	"""
	if feed_type == 'best_photos':
		return redis.Redis(connection_pool=POOL).zrevrank(TRENDING_PHOTO_FEED, obj_hash)
	elif feed_type == 'fresh_photos':
		return redis.Redis(connection_pool=POOL).zrevrank(PHOTO_SORTED_FEED, obj_hash)


def retrieve_photo_feed_latest_mod_time(feed_type='best_photos', both=False):
	"""
	Returns time of latest item's input in the page

	Useful for SEO purposes
	"""
	if both:
		latest_trending_mod_time, latest_regular_mod_time = None, None
		my_server = redis.Redis(connection_pool=POOL)
		latest_trending_data = my_server.zrange(TRENDING_PHOTO_FEED,-1,-1,withscores=True)
		latest_regular_data = my_server.zrange(PHOTO_SORTED_FEED,-1,-1,withscores=True)
		if latest_trending_data:
			latest_trending_mod_time = latest_trending_data[0][1]
		if latest_regular_data:
			latest_regular_mod_time = latest_regular_data[0][1]
		return latest_trending_mod_time, latest_regular_mod_time
	else:
		if feed_type == 'best_photos':
			latest_data = redis.Redis(connection_pool=POOL).zrange(TRENDING_PHOTO_FEED,-1,-1,withscores=True)
		else:
			latest_data = redis.Redis(connection_pool=POOL).zrange(PHOTO_SORTED_FEED,-1,-1,withscores=True)
		if latest_data:
			return latest_data[0][1]
		else:
			return None


def retrieve_home_feed_index(obj_hash):
	"""
	Returns exact index an object is stored at in HOME_SORTED_FEED

	Useful when needing to redirect to precise object after interacting with a post
	"""
	return redis.Redis(connection_pool=POOL).zrevrank(HOME_SORTED_FEED,obj_hash)


def retrieve_best_home_feed_index(obj_hash):
	"""
	Returns exact index an object is stored at in TRENDING_HOME_FEED

	Useful when needing to redirect to precise object after interacting with a post
	"""
	return redis.Redis(connection_pool=POOL).zrevrank(TRENDING_HOME_FEED,obj_hash)


def unpack_json_blob(hash_list, with_colors=False):
	"""
	Iterates through provided list of dictionaries and unpacks a json value called 'blob'

	Used by retrieve_obj_feed() and retrieve_topic_feed_data()
	"""
	for hash_data in hash_list:
		if hash_data:
			try:
				unpacked_values = json.loads(hash_data['blob'])
			except:
				unpacked_values = json_backup.loads(hash_data['blob'])
			hash_data.update(unpacked_values)
			del hash_data['blob']
	if with_colors:
		for hash_data in hash_list:
			theme = hash_data.get('th',None)
			if theme:
				colors = COLOR_GRADIENTS[theme]
				hash_data['c1'], hash_data['c2'] = colors[0], colors[1] 
	return hash_list


def retrieve_obj_feed(obj_list, with_colors=False):
	"""
	Retrieves details to show in home, top and fresh photos (full-fledged list of dictionaries)

	Works for both text and image objects
	"""
	pipeline1 = redis.Redis(connection_pool=POOL).pipeline()
	for hash_name in obj_list:
		pipeline1.hgetall(hash_name)
	return unpack_json_blob(filter(None, pipeline1.execute()),with_colors=with_colors)


def change_delete_status_of_obj_hash(obj_hash_name):
	"""
	Changes 'delete_status' flag in obj_hash to '1'

	Useful when a user removes an obj from their history
	Returns a boolean flag used later
	"""
	my_server = redis.Redis(connection_pool=POOL)
	json_data = my_server.hget(obj_hash_name,'blob')
	if json_data:
		data = json.loads(json_data)
		current_delete_status = data.get('ds','')
		if current_delete_status != '1':
			data['ds'] = '1'
			my_server.hset(obj_hash_name,'blob',json.dumps(data))
			return True
	return False


def retrieve_text_obj_scores(obj_list):
	"""
	Retrieves text obj vote scores - useful for calculating trending text posts

	LIMITATION: Does NOT account for voter reputations yet - only based on number of upvotes
	"""
	pipeline1 = redis.Redis(connection_pool=POOL).pipeline()
	for obj_hash_name in obj_list:

		# Criteria 1) retrieve 'upvotes', 'low quality'
		pipeline1.hmget(obj_hash_name,'uv','lq')

		# Criteria 2) is obj locked from trending because of sybils?
		pipeline1.exists(LOCKED_TXT+obj_hash_name)

	result1, counter, final_result = pipeline1.execute(), 0, []

	################################################################
	for obj_hash_name in obj_list:
		
		obj_data = result1[counter]#the obj's voting is still open (it exists in the feeds)
		is_locked_out_from_trending = result1[counter+1]# e.g. because of sybil voting (criteria 2 was met)
		
		# skip content that has been voted on by sybils, or isn't open for voting any more
		if is_locked_out_from_trending or not obj_data:
			pass

		# else: non-sybil voting, and voting is open!
		else:
			num_upvotes, low_quality = obj_data[0], obj_data[1]
			
			# loq quality posts will never trend anyway
			if low_quality == '1':
				pass
			
			# this post can trend, if it has the requisite number of likes
			else:
				likes = int(num_upvotes) if num_upvotes else 0

				if likes > 1:
					# achieved 2 or more likes
					prob_this_item_would_get_handpicked = 0.01# TODO: make this based on voter/content reputation

				else:
					# achieved less than 2 likes - we assume such a post has a 0% chance of getting handpicked (obviously not right at all)
					prob_this_item_would_get_handpicked = 0# TODO: make this based on voter/content reputation
				
				final_result.append((obj_hash_name, likes, prob_this_item_would_get_handpicked))					

		counter += 2

	################################################################

	return final_result


def retrieve_img_obj_scores(obj_list):
	"""
	Retrieves img obj vote scores - useful for calculating trending images

	Only those imgs are considered for trending that have at least 2 votes from users with reputation > 0
	"""
	pipeline1 = redis.Redis(connection_pool=POOL).pipeline()
	for obj_hash in obj_list:
		data = obj_hash.partition(":")
		obj_type, obj_id = data[0], data[-1]
		vote_store = VOTE_ON_TXT if obj_type == 'tx' else VOTE_ON_IMG

		# Criteria 1) retrieve number of upvotes received by the object
		pipeline1.hget(obj_hash,'uv')
		
		# Criteria 2) retrieve the voting reputation of the top two voters
		pipeline1.zrange(vote_store+obj_id,-2,-1,withscores=True)
		
		# Criteria 3) is this obj locked from trending because of sybil voting?
		pipeline1.exists(LOCKED_IMG+obj_hash)
	result1, counter, final_result = pipeline1.execute(), 0, []

	#############################################################
	for obj_hash in obj_list:
		is_locked_out_from_trending = result1[counter+2]# e.g. because of sybil voting (criteria 3 was met)
		vote_store_exists = result1[counter+1]#the obj's voting is still open
		
		# skip content that has been voted on by sybils, or isn't open for voting any more
		if is_locked_out_from_trending or not vote_store_exists:
			pass

		# else: non-sybil voting, and voting is open!
		else:

			likes = result1[counter]
			likes = int(likes) if likes else 0
			
			################################
			num_votes = len(vote_store_exists)
			
			# enough votes have been cast
			if num_votes == 2:
				vote_1, vote_2 = vote_store_exists[0], vote_store_exists[1]
				score_vote_1, score_vote_2 = vote_1[1], vote_2[1]
				if score_vote_1 > 0 and score_vote_2 > 0:
					# 2 reputable users voted on this - count this obj
					score = max(score_vote_2,score_vote_1)
				else:
					# don't count this obj
					score = 0

			# not enough votes cast
			elif num_votes < 2:
				score = 0
			
			# this should never happen
			else:
				score = 0
			
			################################
			final_result.append((obj_hash, likes, score if score > 0 else 0))

		counter += 3

	return final_result


def retrieve_all_home_text_obj_names():
	"""
	Retreives all 'tx' type objs from home
	"""
	final_objs = []
	all_objs = redis.Redis(connection_pool=POOL).zrange(HOME_SORTED_FEED,0,-1)
	if all_objs:
		for obj_hash_name in all_objs:
			if obj_hash_name.partition(":")[0] == 'tx':
				# this is a text object - it's what we need
				final_objs.append(obj_hash_name)
	return final_objs


def get_home_feed(start_idx=0,end_idx=-1, with_feed_size=False):
	"""
	Retrieve list of all home feed objects
	"""
	if with_feed_size:
		my_server = redis.Redis(connection_pool=POOL)
		return my_server.zrevrange(HOME_SORTED_FEED, start_idx, end_idx), my_server.zcard(HOME_SORTED_FEED)
	else:
		return redis.Redis(connection_pool=POOL).zrevrange(HOME_SORTED_FEED, start_idx, end_idx)


def get_best_home_feed(start_idx=0,end_idx=-1, trending_home=True, with_feed_size=False):
	"""
	Retrieve list of best home feed objects
	"""
	if trending_home:
		if with_feed_size:
			my_server = redis.Redis(connection_pool=POOL)
			return my_server.zrevrange(TRENDING_HOME_FEED, start_idx, end_idx), my_server.zcard(TRENDING_HOME_FEED)
		else:
			return redis.Redis(connection_pool=POOL).zrevrange(TRENDING_HOME_FEED, start_idx, end_idx)
	else:
		return redis.Redis(connection_pool=POOL).zrevrange(BEST_HOME_FEED, start_idx, end_idx)


def voted_for_link(link_id, voter_id):
	"""
	Retrieves whether user voted on given textual content

	Used by 'cast_vote' to ensure voter isn't double voting
	"""
	already_exists = redis.Redis(connection_pool=POOL).zscore(VOTE_ON_TXT+str(link_id), voter_id)
	if already_exists is None:
		# i.e. does not already exist
		return False
	else:
		# voted 1.0 (up) or 0.0 (down) - return value is a float
		return True


def can_vote_on_obj(voter_id, is_pht):
	"""
	Vote rate-limiting algorithm that cools down with time

	Used in 'cast_vote' to check whether potential voter is eligible to vote
	Works for both textual and image objects
	return values are: waiting_ttl, did_vote_go_through
	"""
	my_server, voter_id = redis.Redis(connection_pool=POOL), str(voter_id)
	votes_allowed = "pva:"+voter_id if is_pht == '1' else "va:"+voter_id #votes allowed to voter_id
	current_spree = my_server.get(votes_allowed)
	if current_spree is None:
		# i.e. user hasn't voted at all in the past [45 secs - 4.5 mins] (timeout depends on how aggressively the were voting earlier)
		my_server.incr(votes_allowed)
		my_server.expire(votes_allowed,FORTY_FIVE_SECS)
		return None, True
	elif int(current_spree) > (VOTE_SPREE_ALWD-1):#value set at '25' in the system (score.py)
		ttl = my_server.ttl(votes_allowed)
		return ttl, False
	else:
		# current spree exists
		short_term_rate_limit_key = 'rlpv:'+voter_id if is_pht == '1' else 'rlv:'+voter_id
		short_term_rate_limit = my_server.ttl(short_term_rate_limit_key)
		if short_term_rate_limit < 0:
			my_server.incr(votes_allowed)
			my_server.expire(votes_allowed,THREE_SECS*(int(current_spree)+1))
			return None, True
		else:
			# user has to wait a few seconds (upto 9) - they were voting super fast
			return short_term_rate_limit, False


def get_voting_details(obj_id, is_pht, only_exists=False):
	"""
	Returns for each content: net_votes, num of upvotes, num of downvotes, and num of votes by pinkstars

	Works for home, fresh and top photos
	"""
	hash_name = "img:"+obj_id if is_pht == '1' else "tx:"+obj_id #lk is 'link'
	my_server = redis.Redis(connection_pool=POOL)
	if only_exists:
		return my_server.exists(hash_name)
	else:
		if my_server.exists(hash_name):
			net_votes, upvotes, downvotes, pink_votes = my_server.hmget(hash_name,'nv','uv','dv','pv')
			return True, net_votes, upvotes, downvotes, pink_votes
		else:
			return False, None, None, None, None


def cleanse_voting_records():
	"""
	Delete various voting data according to pre-set criteria

	Deletion criteria is:
	(i) delete all records of 'voting data' older than 1 month
	(ii) delete 'voting affinity' trackers older than 2 months
	(iii) delete 'voting relationship' logs useful for super-defenders after 3 months
	"""
	time_now = time.time()
	one_month_ago = time_now - ONE_MONTH
	my_server = redis.Redis(connection_pool=POOL)
	voting_data_older_than_one_month = my_server.zrangebyscore(GLOBAL_VOTES_AND_TIMES,'-inf',one_month_ago)
	if voting_data_older_than_one_month:
		voter_uvote_set, voter_dvote_set, voter_tgt_uvote_set, voter_tgt_dvote_set = set(), set(), set(), set()
		for vote_data in voting_data_older_than_one_month:
			# vote_data contains: voter_id+":"+str(target_user_id)+":"+vote_value+":"+target_obj_id
			data_list = vote_data.split(":")
			voter_id, target_user_id, vote_value, target_obj_id = data_list[0], data_list[1], data_list[2], data_list[3]
			voter_target_id = voter_id+":"+target_user_id
			if vote_value == '1':
				voter_uvote_set.add(voter_id)
				voter_tgt_uvote_set.add(voter_target_id)
			else:
				voter_dvote_set.add(voter_id)
				voter_tgt_dvote_set.add(voter_target_id)
		
		pipeline1 = my_server.pipeline()
		for voter_id in list(voter_uvote_set):
			pipeline1.zremrangebyscore(VOTER_UVOTES_AND_TIMES+voter_id,'-inf',one_month_ago)
		for voter_id in list(voter_dvote_set):
			pipeline1.zremrangebyscore(VOTER_DVOTES_AND_TIMES+voter_id,'-inf',one_month_ago)
		for voter_target_id in list(voter_tgt_uvote_set):
			pipeline1.zremrangebyscore(ALL_UVOTES_TO_TGT_USER+voter_target_id,'-inf',one_month_ago)
		for voter_target_id in list(voter_tgt_dvote_set):
			pipeline1.zremrangebyscore(ALL_DVOTES_TO_TGT_USER+voter_target_id,'-inf',one_month_ago)
		pipeline1.zremrangebyscore(GLOBAL_VOTES_AND_TIMES,'-inf',one_month_ago)
		pipeline1.execute()
	###################################################################################
	two_months_ago = time_now - TWO_MONTHS
	# these sets are used to 'mark' voting relationships that are suspect and must have their Bayesian probs calculated
	uvoting_relationships_started_two_months_ago = my_server.zrangebyscore(UVOTER_AFFINITY_TRUNCATOR, '-inf',two_months_ago)
	if uvoting_relationships_started_two_months_ago:
		my_server.zrem(UVOTER_AFFINITY,*uvoting_relationships_started_two_months_ago)
		my_server.zremrangebyscore(UVOTER_AFFINITY_TRUNCATOR,'-inf',two_months_ago)

	dvoting_relationships_started_two_months_ago = my_server.zrangebyscore(DVOTER_AFFINITY_TRUNCATOR, '-inf',two_months_ago)
	if dvoting_relationships_started_two_months_ago:
		my_server.zrem(DVOTER_AFFINITY,*dvoting_relationships_started_two_months_ago)
		my_server.zremrangebyscore(DVOTER_AFFINITY_TRUNCATOR,'-inf',two_months_ago)
	###################################################################################
	three_months_ago = time_now - THREE_MONTHS
	# this set is used to report a list of sybils/haters to super defenders - it truncated relationships that are inactive for 3 months
	old_logged_voting_relationships = my_server.zrangebyscore(VOTING_RELATIONSHIP_LOG_TRUNCATOR,'-inf',three_months_ago)
	if old_logged_voting_relationships:
		my_server.zrem(VOTING_RELATIONSHIP_LOG, *old_logged_voting_relationships)
		my_server.zremrangebyscore(VOTING_RELATIONSHIP_LOG_TRUNCATOR,'-inf',three_months_ago)


def retrieve_global_voting_records(start_idx=0, end_idx=-1):
	"""
	Retrieves global voting records, useful for exporting data into a CSV
	"""
	return redis.Redis(connection_pool=POOL).zrange(GLOBAL_VOTES_AND_TIMES,start_idx,end_idx, withscores=True)


def cache_detailed_voting_data(json_data, page_num, user_id):
	"""
	Micro-caches a particular page of upvoting history
	"""
	redis.Redis(connection_pool=POOL).setex(CACHED_UPVOTING_DATA+str(user_id)+":"+str(page_num),json_data,ONE_MIN)


def retrieve_detailed_voting_data(page_num, user_id):
	"""
	Retrieves micro-cached detailed upvoting data
	"""
	return redis.Redis(connection_pool=POOL).get(CACHED_UPVOTING_DATA+str(user_id)+":"+str(page_num))


def cache_old_detailed_voting_data(json_data, page_num, user_id):
	"""
	Micro-caches a particular page of upvoting history
	"""
	redis.Redis(connection_pool=POOL).setex(CACHED_OLD_UPVOTING_DATA+str(user_id)+":"+str(page_num),json_data,ONE_MIN)


def retrieve_old_detailed_voting_data(page_num, user_id):
	"""
	Retrieves micro-cached detailed upvoting data
	"""
	return redis.Redis(connection_pool=POOL).get(CACHED_OLD_UPVOTING_DATA+str(user_id)+":"+str(page_num))


####################################################
############# Measuring Voting Metrics #############
####################################################

SUPER_DEFENDER_IDS = (1,26277,484241,868557,1362004,1410395)

def log_section_wise_voting_liquidity(from_, vote_value, voter_id):
	"""
	Logs how many votes were received by photos from which section, to give an idea of voting liquidity

	We ignore super defenders
	Possible values of 'from_' include:
	- 'fresh'
	- 'trending'
	- 'home'
	- 'topic'
	"""
	if not voter_id in SUPER_DEFENDER_IDS:
		origin_key = from_+":"+vote_value
		my_server = redis.Redis(connection_pool=POOL)
		my_server.zincrby(origin_key,voter_id,amount=1)
		my_server.zincrby('voting_liquidity',origin_key,amount=1)


###################################################
###################################################
###################################################


def create_sybil_relationship_log():
	"""
	This creates a sorted set similar to VOTING_RELATIONSHIP_LOG, but with voter_IDs as the score
	"""
	my_server = redis.Redis(connection_pool=POOL)
	voter_votee_pairs = my_server.zrange(VOTING_RELATIONSHIP_LOG,0,-1)
	pipeline1 = my_server.pipeline()
	for voter_votee in voter_votee_pairs:
		pipeline1.hget(VOTER_AFFINITY_HASH+voter_votee,'p1')
	result1, counter, final_voter_data = pipeline1.execute(), 0, []
	for voter_votee in voter_votee_pairs:
		bayes_prob = result1[counter]
		if bayes_prob and float(bayes_prob) >= BAYESIAN_PROB_THRESHOLD_FOR_VOTE_NERFING:
			final_voter_data.append(voter_votee)
			final_voter_data.append(voter_votee.split(":")[0])
		counter += 1
	my_server.delete(SYBIL_RELATIONSHIP_LOG)
	########## Useful for retrieve_users_voting_relationships() ##########
	if final_voter_data:# without 'if' statement, the statement below will fail when final_voter_data = []
		my_server.zadd(SYBIL_RELATIONSHIP_LOG,*final_voter_data)


def retrieve_voting_records(voter_id, start_idx=0, end_idx=-1, upvotes=True, with_total_votes=False):
	"""
	Retrieves voting records for display in the user's profile

	Retrieval of either 'upvotes' or 'downvotes' (and not both together)
	VOTER_UVOTES_AND_TIMES (or its counterpart) contains votes of only the past 1 month, so those are the only votes we can show
	"""
	voter_key = VOTER_UVOTES_AND_TIMES+str(voter_id) if upvotes else VOTER_DVOTES_AND_TIMES+str(voter_id)
	my_server = redis.Redis(connection_pool=POOL)
	voting_data = my_server.zrevrange(voter_key,start_idx,end_idx, withscores=True)
	if with_total_votes:
		return voting_data, my_server.zcard(voter_key)
	else:
		return voting_data


#################################################### Updating image content objects ############################################


# def get_recent_photos(user_id):
# 	"""
# 	Contains last 5 photos

# 	This list self-deletes if user doesn't upload a photo for more than 4 days
# 	"""
# 	return redis.Redis(connection_pool=POOL).lrange("imgs:"+str(user_id), 0, -1)


def save_recent_photo(user_id, photo_id, time_now):
	"""
	Add the image to some required data structures
	"""
	# time_now = time.time()
	# key_name = "imgs:"+str(user_id)
	my_server = redis.Redis(connection_pool=POOL)
	# my_server.lpush(key_name, photo_id)
	# my_server.ltrim(key_name, 0, 4) # save the most recent 5 photos'
	# my_server.expire(key_name,FOUR_DAYS) #ensuring people who don't post anything for 4 days have to restart
	############################################
	my_server.setex(MOST_RECENT_IMG_UPLOAD_TIME+str(user_id),time_now,ONE_MONTH)# used in 'rep' calculation
	############################################
	# useful for display a 'counter' in our 'fresh' page page
	my_server.zincrby(GLOBAL_UPLOADED_IMG_VOLUME,user_id,amount=1)
	my_server.zadd(GLOBAL_UPLOADED_IMGS,photo_id,time_now)
	if random() < 0.01:
		# run clean up after 100 attempts (on avg)
		my_server.zremrangebyscore(GLOBAL_UPLOADED_IMGS,'-inf',time_now-ONE_DAY)


def retrieve_fresh_image_count():
	"""
	Returns num 'fresh' public imgs uploaded in the last 24 hours
	"""
	return redis.Redis(connection_pool=POOL).zcount(GLOBAL_UPLOADED_IMGS,time.time()-ONE_DAY,'+inf')



def log_recent_text(user_id, description):
	"""
	Does various text logging (for multiple purposes)

	1) Log volume of text uploaded by each user - useful for 'content rep' calculation
	2) Log the posting time of the user - useful for calculating user activeness
	3) Log prev 800 texts to mark repetition - useful for marking repetitions
	"""
	time_now = time.time()
	my_server = redis.Redis(connection_pool=POOL)

	# setting last posting time for each poster
	my_server.setex(MOST_RECENT_TEXT_SUBMISSION_TIME+str(user_id),time_now,ONE_MONTH)
	
	# setting volume of text submitted by each poster
	my_server.zincrby(GLOBAL_SUBMITTED_TXT_VOLUME,user_id,amount=1)
	
	# logging the latest 800 public text posts
	my_server.zadd(GLOBAL_RECENT_PUBLIC_TEXTS,description.lower(),time_now)

	if random() < 0.005:
		# cull the set once in 200 trials
		my_server.zremrangebyrank(GLOBAL_RECENT_PUBLIC_TEXTS, 0, -801)# to keep top 800 in the sorted set


def get_recent_trending_photos(user_id):
	"""
	Returns last 5 trending photo ids
	"""
	return redis.Redis(connection_pool=POOL).zrange("timgs:"+str(user_id), 0, -1)


def save_recent_trending_photo(user_id, photo_id, time_of_selection, my_server=None):
	"""
	Saves latest 5 trending photos of a given user
	"""
	estimated_trending_expiry_time = time_of_selection+561600# roughly 1 week (precisely 6 days, 12 hours - a little below full 7 days to ensure we don't run into any errors)
	key_name = "timgs:"+str(user_id)
	my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
	my_server.zadd(key_name, photo_id, estimated_trending_expiry_time)
	my_server.zremrangebyrank(key_name, 0, -6)# to keep top 5 items in the sorted set
	my_server.expireat(key_name,int(estimated_trending_expiry_time))


def cache_recent_trending_images(user_id, payload):
	"""
	"""
	redis.Redis(connection_pool=POOL).setex("cti:"+str(user_id),payload,TWENTY_MINS)


def get_cached_recent_trending_images(user_id):
	"""
	"""
	return redis.Redis(connection_pool=POOL).get("cti:"+str(user_id))


def add_obj_to_photo_feed(submitter_id, time_now, hash_name, my_server=None):
	"""
	Adding various objects to photo feed
	"""
	my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
	my_server.zadd(PHOTO_SORTED_FEED, hash_name, time_now)
	if random() < 0.2:
		# every now and then, trim the sorted set for size
		my_server.zremrangebyrank(PHOTO_SORTED_FEED, 0, -1001)# to keep top 1000 in the sorted set
	log_user_submission(submitter_id=submitter_id, submitted_obj=hash_name, expire_at=int(time_now+PUBLIC_SUBMISSION_TTL), \
		feeds_to_add=[PHOTO_SORTED_FEED], my_server=my_server)


def add_image_post(obj_id, categ, submitter_id, submitter_av_url, submitter_username, is_star, img_url, img_caption, \
	submission_time, from_fbs, type_of_object, comments, img_height, img_width, alt_text, add_to_home_feed=False, \
	add_to_photo_feed=True, poster_defined_expiry_time=None):
	"""
	Creating image object (used in home and photo feed, etc)
	"""
	obj_id = str(obj_id)
	submitter_av_url = get_s3_object(submitter_av_url,category='thumb')#pre-convert avatar url for the feed so that we don't have to do it again and again
	img_thumb = get_s3_object(img_url,category="thumb")
	hash_name = "img:"+obj_id
	img_hw_ratio = (1.0*img_width/img_height)
	immutable_data = {'i':obj_id,'c':categ,'sa':submitter_av_url,'su':submitter_username,'si':submitter_id,'t':submission_time,\
	'd':img_caption,'iu':img_url,'it':img_thumb,'h':hash_name,'ht':img_height,'wd':img_width,'com':comments, 'ot':type_of_object[0], \
	'aud':type_of_object[1],'rt':round((100.0/img_hw_ratio),2),'nht':round(MAX_PUBLIC_IMG_WIDTH/img_hw_ratio),'alt':alt_text}

	expiry = type_of_object[2]
	if expiry:
		immutable_data['exp'] = expiry
	if from_fbs:
		immutable_data['fbs']='1'
	if is_star:
		immutable_data['s']='1'
	if poster_defined_expiry_time:
		immutable_data['et'] = poster_defined_expiry_time

	mapping = {'nv':'0','uv':'0','dv':'0','blob':json.dumps(immutable_data)}
	
	time_now = time.time()
	expire_at = int(time_now+PUBLIC_SUBMISSION_TTL)
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	pipeline1.hmset(hash_name,mapping)
	pipeline1.expireat(hash_name,expire_at)#setting TTL to one day
	#### initialize voting sorted set ####
	obj_vote_store_key = VOTE_ON_IMG+obj_id
	pipeline1.zadd(obj_vote_store_key,-1,-1)
	pipeline1.expireat(obj_vote_store_key,expire_at)
	pipeline1.execute()
	if add_to_photo_feed:
		add_obj_to_photo_feed(submitter_id, time_now, hash_name, my_server)
	if add_to_home_feed:
		add_obj_to_home_feed(submitter_id, time_now, hash_name, my_server)
	return hash_name


def store_inline_reply(parent_obj_type, parent_obj_id, reply_text, reply_writer_id, reply_id, reply_writer_uname, time_now, \
	reference_id='', reply_target=None, target_text_prefix=None,target_text_postfix=None):
	"""
	Adds a comment to text or photo object (if it exists in redis)
	"""
	num_comments = 0
	obj_hash_name = 'tx:'+str(parent_obj_id) if parent_obj_type == '3' else 'img:'+str(parent_obj_id)
	my_server = redis.Redis(connection_pool=POOL)
	if my_server.exists(obj_hash_name):
		reply_blob = my_server.hget(obj_hash_name,'rb')
		reply_blob = truncate_payload(json.loads(reply_blob)) if reply_blob else []
		dict_data = {'poid':parent_obj_id,'tx':reply_text,'epoch_time':time_now,'wun':reply_writer_uname,'wid':reply_writer_id}
		if is_image_star(reply_writer_id, my_server=my_server):
			dict_data['s'] = '1'
		if reply_target:
			dict_data['ct'] = reply_target#'ct' means comment_target (mislabled - should have been 'rt')
		if target_text_prefix:
			dict_data['ttxpre'] = target_text_prefix
			if target_text_postfix:
				dict_data['ttxpos'] = target_text_postfix
		payload = (reply_id,reference_id,dict_data)# this format is optimized for displaying the data and also doing a sequential search in it (when requiring to hide a reply)
		reply_blob.append(payload)
		my_server.hset(obj_hash_name,'rb',json.dumps(reply_blob))
		num_comments = my_server.hincrby(obj_hash_name, "cc", amount=1) #updating comment count in the parent obj
	return num_comments

	
def truncate_payload(reply_blob):
	"""
	Helper function for store_inline_reply()
	
	On average, truncate this after 14 comments have aggregated
	A 'reply_blob' is a list of tuples
	"""
	return reply_blob[-4:] if (random() < 0.07 and reply_blob) else reply_blob


def hide_inline_direct_response(obj_type, parent_obj_id, reply_id):
	"""
	Hides text in 'inline comments' (under text or photos)
	"""
	reply_id = str(reply_id)
	obj_hash_name = 'tx:'+str(parent_obj_id) if obj_type == '3' else 'img:'+str(parent_obj_id)
	my_server = redis.Redis(connection_pool=POOL)
	json_reply_data = my_server.hget(obj_hash_name,'rb')
	if json_reply_data:
		changed = False
		reply_data = json.loads(json_reply_data)
		
		for rid, refid, data in reply_data:
			if reply_id == str(rid):
				# this reply ought to be completely hidden
				data['mrh'] = '1'# main reply hidden
				data.pop('ttxpre', None)# emptying out the reference too
				data.pop('ttxpos', None)# emptying out the reference too
				changed = True
			elif reply_id == str(refid):
				# this reply's reference ought to be hidden
				data['rh'] = '1'# reference hidden
				data.pop('ttxpre', None)# emptying out the reference
				data.pop('ttxpos', None)# emptying out the reference
				changed = True

		if changed:
			# saving altered data
			my_server.hset(obj_hash_name,'rb',json.dumps(reply_data))


def get_obj_owner(obj_id, obj_type):
	"""
	Return owner id of content object (only if redis object of said content exists)

	Replace the usage of get_photo_owner() and get_link_writer() in voting_views.py by this one
	"""
	obj_hash_name = 'img:'+str(obj_id) if obj_type == 'img' else 'tx:'+str(obj_id)
	blob = redis.Redis(connection_pool=POOL).hget(obj_hash_name,'blob')
	if blob:
		return json.loads(blob)['si']
	else:
		return ''


def voted_for_single_photo(photo_id, voter_id):
	"""
	Retrieves whether user voted on given image content

	Used in 'cast_vote' to ensure user isn't double voting
	"""
	already_exists = redis.Redis(connection_pool=POOL).zscore(VOTE_ON_IMG+str(photo_id), voter_id)
	if already_exists is None:
		# i.e. does not already exist
		return False
	else:
		# voted 1.0 (up) or 0.0 (down) - return value is a float
		return True


def get_photo_feed(start_idx=0, end_idx=-1, feed_type='best_photos', with_feed_size=False):
	"""
	Retrieve list of all image feed objects
	"""
	if feed_type == 'best_photos':
		feed_name = TRENDING_PHOTO_FEED
	elif feed_type == 'fresh_photos':
		feed_name = PHOTO_SORTED_FEED
	else:
		return []
	if with_feed_size:
		my_server = redis.Redis(connection_pool=POOL)
		return my_server.zrevrange(feed_name, start_idx, end_idx), my_server.zcard(feed_name)
	else:
		return redis.Redis(connection_pool=POOL).zrevrange(feed_name, start_idx, end_idx)


def add_photos_to_best_photo_feed(photo_scores, consider_world_age=False):
	"""
	Constructing bestphotofeed

	 Provides an alternative route where world age of the voter is taken into consideration (as a proxy for user 'karma')
	"""
	#executing the following commands as a single transaction
	if consider_world_age:
		ALT_BEST_PHOTO_FEED = 'altbestphotofeed'
		try:
			my_server = redis.Redis(connection_pool=POOL)
			pipeline1 = my_server.pipeline()
			pipeline1.delete(ALT_BEST_PHOTO_FEED)
			pipeline1.zadd(ALT_BEST_PHOTO_FEED,*photo_scores)
			pipeline1.execute()
		except:
			pass
	else:
		try:
			my_server = redis.Redis(connection_pool=POOL)
			pipeline1 = my_server.pipeline()
			pipeline1.delete(BEST_PHOTO_FEED)
			pipeline1.zadd(BEST_PHOTO_FEED,*photo_scores)
			pipeline1.execute()
		except:
			pass


def add_posts_to_best_posts_feed(post_scores):
	"""
	Constructing best posts feed
	"""
	#executing the following commands as a single transaction
	try:
		my_server = redis.Redis(connection_pool=POOL)
		pipeline1 = my_server.pipeline()
		pipeline1.delete(BEST_HOME_FEED)
		pipeline1.zadd(BEST_HOME_FEED,*post_scores)
		pipeline1.execute()
	except:
		pass

def get_best_photo_feed():
	"""
	Returns IDs of ranked images, alongwith scores
	"""
	return redis.Redis(connection_pool=POOL).zrevrange(BEST_PHOTO_FEED, 0, -1, withscores=True)


def is_fbs_user_rate_limited_from_photo_upload(user_id):
	"""
	Checks whether FBS user is rate limited from uploading a public image for the photo feed

	We implement rate limits on FBS users since their uploads are low quality in terms of resolution
	"""
	ttl = redis.Redis(connection_pool=POOL).ttl(FBS_PUBLIC_PHOTO_UPLOAD_RATE_LIMIT+str(user_id))
	if ttl > 0:
		return True, ttl
	else:
		return False, None


def rate_limit_fbs_public_photo_uploaders(user_id):
	"""
	Rate limiting fbs public photo uploaders
	"""
	redis.Redis(connection_pool=POOL).setex(FBS_PUBLIC_PHOTO_UPLOAD_RATE_LIMIT+str(user_id),'1',FBS_PUBLIC_PHOTO_UPLOAD_RL)


#########################################################################################################
########################################## Topic Functionality ##########################################
######################################################################################################### 

TOPIC_ID = 'topic_id'# key that produces the unique ID for a given topic
TOPIC_ID_MAPPING = 'tm:'# key that maps a topic to its ID
ALL_CURRENT_TOPICS = 'all_current_topics'# list containing all topics, sorted by time of visit (or last touch). Deleted topics are removed from this list
ALL_TOPICS_CREATED = 'all_topics_created'# list containing all topics, sorted by time of creation. Deleted topics are removed from this list
TOPIC_TOUCH_LOCKED = 'ttl:'# a key that locks 'touching' the topic's ttl again (e.g. because of serial refreshing)

SUB_TOPICS = 'st:'# sorted set containing all topics a user is subscribed to (topic_urls and times of sub)
TOPIC_SUBS = 'ts:'# sorted set containing all topic subscribers (IDs and times of sub)
TOPIC_UNSUB_LOCKED = 'tul:'# key that locks <user_id>:<topic_url> composite data from unsubscribing too fast
TOPIC_FEED = 'tf:'# a sorted set containing all the posts 'within' a certain topic
USER_FEED = 'uf:'# a sorted set containing all posts a certain user has subcribed to
TOPIC_JSON_OBJ = 'tj:'# a key containing details of a topic (description, time of creation, who owns it, etc) in JSON form
ONLY_TOPICS_FEED = 'only_topics_feed'


def get_topic_feed_id(my_server=None):
	"""
	Generate a topic ID for every topic

	Currently it's just a passive number, but might be actively useful later
	"""
	my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
	return my_server.incr(TOPIC_ID)


def create_topic_feed(topic_owner_id, payload, time_now):
	"""
	Create a new topic

	Ensure that it doesn't already exist
	"""
	topic_url = payload['url']# i.e. topic in 'this-is-a-topic' form, which is suitable for urls
	my_server = redis.Redis(connection_pool=POOL)
	if retrieve_topic_credentials(topic_url, my_server=my_server, existence_only=True):
		# topic already exists, cannot re-create it
		return False
	else:
		# create the topic here
		topic_json_obj = TOPIC_JSON_OBJ+topic_url
		topic_id_mapping_key = TOPIC_ID_MAPPING+topic_url
		new_topic_feed_id = get_topic_feed_id(my_server)
		payload['tpid'] = new_topic_feed_id
		#################################################
		pipeline1 = my_server.pipeline()
		pipeline1.set(topic_json_obj,json.dumps(payload))# a key that contains the details of the topic (in json obj form)
		pipeline1.set(topic_id_mapping_key,new_topic_feed_id)# a key that contains a mapping of topic name and its ID
		pipeline1.zadd(ALL_CURRENT_TOPICS,topic_url,time_now)#sorted by time of last visit to the topic
		pipeline1.zadd(ALL_TOPICS_CREATED,topic_url,time_now)#sorted by time of creation
		pipeline1.execute()
		return True


def subscribe_topic(subscriber_id, topic_url, sub_time):
	"""
	Subscribe a particular user to a topic

	Lock them from unsubscribing for 2 hours (i.e. TOPIC_UNSUB_LOCKING_TIME)
	"""
	subscriber_id = str(subscriber_id)
	my_server = redis.Redis(connection_pool=POOL)
	#####################################################
	my_server.zadd(SUB_TOPICS+subscriber_id,topic_url, sub_time)
	my_server.zadd(TOPIC_SUBS+topic_url, subscriber_id, sub_time)# could be useful in generating a 'topic feed' for subscribers
	#####################################################
	my_server.setex(TOPIC_UNSUB_LOCKED+subscriber_id+":"+topic_url, sub_time, TOPIC_UNSUB_LOCKING_TIME)


def retrieve_subscribed_topics(user_id):
	"""
	"""
	final_data = []
	if user_id:
		my_server = redis.Redis(connection_pool=POOL)
		topic_urls = my_server.zrevrange(SUB_TOPICS+user_id,0,-1)
		if topic_urls:
			topic_json_data, topic_data = [], []
			for topic_url in topic_urls:
				topic_json_data.append(my_server.get(TOPIC_JSON_OBJ+topic_url))
			for json_data in topic_json_data:
				topic_data.append(json.loads(json_data))
			final_data = []
			for data in topic_data:
				colors = COLOR_GRADIENTS[data['th']]
				final_data.append({'url':data['url'],'c1':colors[0],'c2':colors[1],'name':data['tn']})
	return final_data


def get_num_topics(user_id):
	"""
	Returns number of topics a user has subscribed to
	"""
	return redis.Redis(connection_pool=POOL).zcard(SUB_TOPICS+str(user_id))


def fan_out_to_subscribers(topic_url, obj_hash_id):
	"""
	TODO: Unused at the moment. This can go live as a second step of introducing 'topics'

	Implementation details: 
	whenever add_topic_post() is run, this function can be run as an async task to populate subscriber feeds
	How will USER_FEEDs be trimmed or kept to a humane size? This is critical to answer
	What to do with users who haven't touched their topic feed in a long time (e.g. dropped out or don't care about the feature)
	"""
	my_server = redis.Redis(connection_pool=POOL)
	all_subscribers = my_server.zrange(TOPIC_SUBS+topic_url,0,-1)
	if len(all_subscribers) < 10:# TODO: should this number be 10 or 20 or what? Find out via testing in test_script.py (both own machine and Fahad's machine for comparison of speeds)
		for subscriber_id in all_subscribers:
			my_server.zadd(USER_FEED+subscriber_id,obj_hash_id)
	else:
		pipeline1 = my_server.pipeline()
		for subscriber_id in all_subscribers:
			pipeline1.zadd(USER_FEED+subscriber_id,obj_hash_id)
		pipeline1.execute()


def unsubscribe_topic(subscriber_id, topic_url, my_server=None):
	"""
	Unsubscribe a user from a topic
	"""
	subscriber_id = str(subscriber_id)
	my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
	ttl = my_server.ttl(TOPIC_UNSUB_LOCKED+subscriber_id+":"+topic_url)
	if ttl:
		return False, ttl
	else:
		my_server.zrem(SUB_TOPICS+subscriber_id,topic_url)
		my_server.zrem(TOPIC_SUBS+topic_url,subscriber_id)
		# not removing already pushed data in USER_FEED, it's cumbersome to do that
		return True, None


def bulk_unsubscribe_topic(subscriber_id, topic_urls, my_server=None):
	"""
	Unsubscribe a user from topics
	"""
	if topic_urls:
		subscriber_id = str(subscriber_id)
		my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
		rate_limited_topics, other_topics = [], []
		for topic_url in topic_urls:
			ttl = my_server.ttl(TOPIC_UNSUB_LOCKED+subscriber_id+":"+topic_url)
			if ttl:
				rate_limited_topics.append(topic_url)
			else:
				other_topics.append(topic_url)
		if other_topics:
			for topic_url in other_topics:
				my_server.zrem(SUB_TOPICS+subscriber_id,topic_url)
				my_server.zrem(TOPIC_SUBS+topic_url,subscriber_id)
		return rate_limited_topics
	else:
		return []


def add_topic_post(obj_id, obj_hash, categ, submitter_id, submitter_av_url, submitter_username, is_star,text, submission_time, \
	from_fbs, topic_url, topic_name, bg_theme, type_of_object, comments, add_to_public_feed=False, poster_defined_expiry_time=None):
	"""
	Creating and submitting text object (used in topic feed and public feed)
	"""
	submitter_av_url = get_s3_object(submitter_av_url,category='thumb')#pre-convert avatar url for the feed so that we don't have to do it again and again
	audience_type = type_of_object[1]
	immutable_data = {'i':obj_id,'c':categ,'si':submitter_id,'sa':submitter_av_url,'su':submitter_username,'t':submission_time,\
	'd':text,'h':obj_hash,'url':topic_url, 'th':bg_theme, 'tn':topic_name,'com':comments, 'ot':type_of_object[0], 'aud':audience_type}
	
	expiry = type_of_object[2]
	if expiry:
		immutable_data['exp'] = expiry
	if from_fbs:
		immutable_data['fbs']='1'
	if is_star:
		immutable_data['s']='1'
	if poster_defined_expiry_time:
		immutable_data['et'] = poster_defined_expiry_time
	
	mapping = {'nv':'0','uv':'0','dv':'0','blob':json.dumps(immutable_data)}

	my_server = redis.Redis(connection_pool=POOL)	
	######################################################
	# flagging low quality posts based on certain text criteria
	if audience_type == 'p':
		lower_text = text.lower()
		mapping['lq'] = retrieve_text_quality(text=text,lower_text=lower_text,text_lang=categ,\
			is_being_reposted=my_server.zscore(GLOBAL_RECENT_PUBLIC_TEXTS,lower_text))
	######################################################
	time_now = time.time()
	expire_at, obj_id = int(time_now+TOPIC_SUBMISSION_TTL), str(obj_id)

	pipeline1 = my_server.pipeline()
	pipeline1.hmset(obj_hash,mapping)# creating the obj hash
	pipeline1.expireat(obj_hash,expire_at)# setting a TTL of one week on this obj hash
	######## initialize voting sorted set ########
	pipeline1.zadd(VOTE_ON_TXT+obj_id,-1,-1)
	pipeline1.expireat(VOTE_ON_TXT+obj_id,expire_at)#setting a TTL of one week on this obj
	##############################################
	pipeline1.execute()
	######## incrementing counts in topic obj ########
	topic_hash_obj = TOPIC_JSON_OBJ+topic_url
	topic_obj = json.loads(my_server.get(topic_hash_obj))
	topic_obj['num'] = topic_obj['num']+1# num posts submitted
	topic_obj['lpt'] = time_now# latest post time
	my_server.set(topic_hash_obj,json.dumps(topic_obj))
	##################################################
	if audience_type == 'p':
		# only add to any feed if the post is "public"
		add_obj_to_feeds(submitter_id, topic_url, obj_hash, time_now, my_server, add_to_public_feed)


def add_obj_to_feeds(submitter_id, topic_url, obj_hash_name, time_now, my_server=None, add_to_public_feed=False):
	"""
	Adding the submitted object to the various feeds (including the topic feed)
	"""
	topic_key = TOPIC_FEED+topic_url
	my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	pipeline1.zadd(topic_key, obj_hash_name, time_now)# adding the submission to the topic's feed
	pipeline1.zadd(ONLY_TOPICS_FEED, obj_hash_name, time_now)# add the submission to the ONLY_TOPICS_FEED sorted set
	if add_to_public_feed:
		pipeline1.zadd(HOME_SORTED_FEED, obj_hash_name, time_now)# add the submittion to the HOME_SORTED_FEED sorted set
		rand = random()
		if rand < 0.1:
			# every now and then, trim the HOME sorted set for size
			pipeline1.zremrangebyrank(HOME_SORTED_FEED, 0, -1001)# to keep latest 1000 in the sorted set
		elif rand > 0.9:
			# every now and then, trim the ONLY_TOPICS sorted set for size (but never together with HOME_SORTED_SET)
			pipeline1.zremrangebyrank(ONLY_TOPICS_FEED, 0, -1001)# to keep latest 1000 in the sorted set
	pipeline1.execute()
	log_user_submission(submitter_id=submitter_id, submitted_obj=obj_hash_name, expire_at=int(time_now+TOPIC_SUBMISSION_TTL), \
		feeds_to_add=[topic_key,ONLY_TOPICS_FEED,HOME_SORTED_FEED], my_server=my_server)# topic_key is TOPIC_FEED+topic


def retrieve_topic_feed_index(topic, obj_hash):
	"""
	Returns exact index an object is stored at in TOPIC_FEED

	Useful when needing to redirect to precise object after interacting with a post
	"""
	return redis.Redis(connection_pool=POOL).zrevrank(TOPIC_FEED+topic,obj_hash)


def retrieve_topic_feed_data(obj_list, topic_url):
	"""
	Retrieves details to show in topic
	"""
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	for hash_name in obj_list:
		pipeline1.hgetall(hash_name)
	result1 = pipeline1.execute()
	return unpack_json_blob(filter(None, result1))


def get_topic_feed(topic_url, start_idx, end_idx, with_feed_size=True, touch_topic=False):
	"""
	Retrieves topic feed obj hashes
	"""
	topic_key = TOPIC_FEED+topic_url
	if with_feed_size:
		my_server = redis.Redis(connection_pool=POOL)
		if touch_topic:
			topic_touch_ttl_key = TOPIC_TOUCH_LOCKED+topic_url
			if not my_server.exists(topic_touch_ttl_key):
				my_server.zadd(ALL_CURRENT_TOPICS,topic_url,time.time())#only the topic url is stored here, not the prefix. Never store prefixes, they can change!
				my_server.setex(topic_touch_ttl_key,'1',THREE_HOURS)
		return my_server.zrevrange(topic_key, start_idx, end_idx), my_server.zcard(topic_key)
	else:
		if touch_topic:
			topic_touch_ttl_key = TOPIC_TOUCH_LOCKED+topic_url
			if not my_server.exists(topic_touch_ttl_key):
				my_server.zadd(ALL_CURRENT_TOPICS,topic_url,time.time())#only the topic url is stored here, not the prefix. Never store prefixes, they can change!
				my_server.setex(topic_touch_ttl_key,'1',THREE_HOURS)
		return redis.Redis(connection_pool=POOL).zrevrange(topic_key, start_idx, end_idx)


def retrieve_recently_used_color_themes():
	"""
	Retrieves list of topics most recently appearing in ONLY_TOPICS_FEED, and then extracts the color themes they used (alongwith frequency of use)

	Useful for deciding what's the next color theme to allot
	"""
	my_server = redis.Redis(connection_pool=POOL)
	recent_topic_enteries = redis.Redis(connection_pool=POOL).zrange(ONLY_TOPICS_FEED,0,200)
	if recent_topic_enteries:
		pipeline1 = my_server.pipeline()
		for obj_hash in recent_topic_enteries:
			pipeline1.hget(obj_hash,'blob')
		result1 = pipeline1.execute()
		final_result_dict = defaultdict(int)
		for obj in result1:
			if obj: 
				try:
					data = json.loads(obj)
				except:
					data = json_backup.loads(obj)
				theme = data.get('th',None)
				if theme:
					final_result_dict[theme] += 1
		final_result_list = final_result_dict.items()
		return final_result_list# list of tuples [(topic_theme, frequency of occurence),...]
	else:
		return []


def retrieve_topic_credentials(topic_url, my_server=None, existence_only=False, with_desc=False, with_name=False, \
	with_theme=False, with_is_subscribed=False, retriever_id=None):
	"""
	Used to retrieve selective credentials about a given topic
	"""
	if existence_only:
		return redis.Redis(connection_pool=POOL).exists(TOPIC_JSON_OBJ+topic_url)
	else:
		my_server = redis.Redis(connection_pool=POOL)
		json_blob = my_server.get(TOPIC_JSON_OBJ+topic_url)
		try:
			blob = json.loads(json_blob) if json_blob else None
		except:
			blob = json_backup.loads(json_blob) if json_blob else None
		if with_desc and with_name and with_theme and with_is_subscribed:
			if blob:
				desc, topic_name, theme = blob['d'], blob['tn'], blob['th']
				is_subscribed = my_server.zscore(TOPIC_SUBS+topic_url, retriever_id)
				return desc, topic_name, theme, is_subscribed
			else:
				return '', '', '', False
		elif with_name and with_theme and with_is_subscribed:
			if blob:
				topic_name, theme = blob['tn'], blob['th']
				is_subscribed = my_server.zscore(TOPIC_SUBS+topic_url, retriever_id)
				return topic_name, theme, is_subscribed
			else:
				return '', '', False
		elif with_desc and with_name and with_theme:
			if blob:
				topic_name, description, theme = blob['tn'], blob['d'], blob['th']
				return topic_name, description, theme
			else:
				return '', '', ''

def retire_abandoned_topics(topic_urls=None):
	"""
	Retired topics that have not been visited since a given amount of time (currently set to 20 days ago)
	"""
	my_server = redis.Redis(connection_pool=POOL)
	if topic_urls:
		inactive_topics = topic_urls
	else:
		cutoff_time = time.time() - TOPIC_LIFELINE
		inactive_topics = my_server.zrangebyscore(ALL_CURRENT_TOPICS,'-inf','('+str(cutoff_time))
	if inactive_topics:
		for topic_url in inactive_topics:

			trim_expired_topic_submissions(topic_url,my_server)# delete all topic submissions
			my_server.zrem(ALL_CURRENT_TOPICS,topic_url)# remove topic from this sorted set
			my_server.zrem(ALL_TOPICS_CREATED,topic_url)# remove topic from this sorted set
			# removing topic's JSON object
			my_server.execute_command('UNLINK', TOPIC_JSON_OBJ+topic_url)# using 'UNLINK' (non-blocking) instead of 'DELETE' (blocking)
			all_subs = my_server.zrange(TOPIC_SUBS+topic_url,0,-1)
			pipeline1 = my_server.pipeline()
			for sub_id in all_subs:
				pipeline1.zrem(SUB_TOPICS+sub_id,topic_url)
			pipeline1.execute()
			# removing all topic subscribers' list
			my_server.execute_command('UNLINK', TOPIC_SUBS+topic_url)
			# remove topic ID and topic_url mapping key
			my_server.execute_command('UNLINK', TOPIC_ID_MAPPING+topic_url)


def trim_expired_topic_submissions(topic_url, my_server=None):
	"""
	Deletes all topic submissions and their references in various feeds (i.e. topic feed, home feed, all_topics feed, etc.)

	Helper function of retire_abandoned_topics()
	"""
	topic_feed_key = TOPIC_FEED+topic_url
	my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
	all_topic_submissions = my_server.zrange(topic_feed_key,0,-1)
	###### checking which submissions exist ######
	pipeline1 = my_server.pipeline()
	for sub in all_topic_submissions:
		pipeline1.exists(sub)
	result1, counter = pipeline1.execute(), 0
	######## commencing deletion of topic ########
	pipeline2 = my_server.pipeline()
	composite_keys_to_delete = []
	for sub in all_topic_submissions:
		composite_obj_1, composite_obj_2, composite_obj_3 = topic_feed_key+"*"+sub, ONLY_TOPICS_FEED+"*"+sub,\
		HOME_SORTED_FEED+"*"+sub
		composite_keys_to_delete.append(composite_obj_1)
		composite_keys_to_delete.append(composite_obj_2)
		composite_keys_to_delete.append(composite_obj_3)
		pipeline2.zrem(HOME_SORTED_FEED,sub)## removing the obj from HOME_SORTED_FEED
		pipeline2.zrem(ONLY_TOPICS_FEED,sub)## removing the obj from ONLY_TOPICS_FEED
		if result1[counter]:
			pipeline2.execute_command('UNLINK', sub)# using 'UNLINK' (non-blocking) instead of 'DELETE' (blocking)
		counter += 1
	pipeline2.execute_command('UNLINK', topic_feed_key)## deleting the topic feed
	if composite_keys_to_delete:
		# clearing out global user submission sets
		pipeline2.zrem(USER_SUBMISSIONS_AND_EXPIRES,*composite_keys_to_delete)
		pipeline2.zrem(USER_SUBMISSIONS_AND_SUBMITTERS,*composite_keys_to_delete)
	pipeline2.execute()


######################################### Logging User Submissions ####################################

def log_user_submission(submitter_id, submitted_obj, expire_at=None, feeds_to_add=[], feeds_to_subtract=[], my_server=None):
	"""
	Logs the submitted object in a global sorted set

	This is useful for periodic truncation of expired items and/or handling banned users whose feeds are to be eliminated
	"""
	my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
	if feeds_to_add:
		expire_at = expire_at if expire_at else int(time.time()+my_server.ttl(submitted_obj))
		for feed in feeds_to_add:
			obj = feed+"*"+submitted_obj
			my_server.zadd(USER_SUBMISSIONS_AND_EXPIRES,obj,expire_at)
			my_server.zadd(USER_SUBMISSIONS_AND_SUBMITTERS,obj,int(submitter_id))
	for feed in feeds_to_subtract:
		obj = feed+"*"+submitted_obj
		my_server.zrem(USER_SUBMISSIONS_AND_EXPIRES,obj)
		my_server.zrem(USER_SUBMISSIONS_AND_SUBMITTERS,obj)


def trim_expired_user_submissions(submitter_id=None, cleanse_feeds='1', already_deleted_objs=None,\
	target_obj_hash_name=None, time_now=None):
	"""
	Trims user submissions' set for expired entries

	Called via a scheduled task, or when banning a certain user and his/her submissions need to be taken out of circulation
	Also used to remove singular post when a user 'removes' it
	"""
	if cleanse_feeds == '1':
		my_server = redis.Redis(connection_pool=POOL)

		# Remove singular post when a user 'removes' it
		if submitter_id and target_obj_hash_name:
			rate_limit_key = REMOVAL_RATE_LIMIT+submitter_id 
			ttl = my_server.ttl(rate_limit_key)
			if ttl:
				# the user is rate-limited from removing the object for 'ttl' seconds
				return False, ttl
			else:
				submitter_id = float(submitter_id)
				user_submissions = my_server.zrangebyscore(USER_SUBMISSIONS_AND_SUBMITTERS,submitter_id,submitter_id)
				if user_submissions:
					rows_to_remove = []
					for submission in user_submissions:
						obj_hash_name = submission.rpartition("*")[-1]
						if obj_hash_name == target_obj_hash_name:
							rows_to_remove.append(submission)

					if rows_to_remove:
						# only remove obj from global feeds, don't delete the object or its vote_stores, since our policy is to continue displaying the obj in user feeds
						pipeline1 = my_server.pipeline()
						for submission in rows_to_remove:
							data = submission.split('*')
							which_feed, obj_hash_name = data[0], data[1]
							pipeline1.zrem(which_feed, obj_hash_name)
							############## In case the obj was a trending image, remove it from sets that calculate total trending images separately ##############
							# this functionality is carried out by trim_trenders_data() in the 'elif' below
							obj_data = obj_hash_name.partition(":")
							if obj_data[0] == 'img':
								obj_id = obj_data[-1]
								pipeline1.zrem(TRENDING_FOTOS_AND_USERS,obj_id)
								pipeline1.zrem(TRENDING_FOTOS_AND_TIMES,obj_id)
							
						pipeline1.zrem(USER_SUBMISSIONS_AND_SUBMITTERS,*rows_to_remove)
						pipeline1.zrem(USER_SUBMISSIONS_AND_EXPIRES,*rows_to_remove)
						pipeline1.setex(rate_limit_key,'1',REMOVAL_RATE_LIMIT_TIME)
						pipeline1.execute()

				# the targeted obj has been removed
				return True, None

				################################################

		####################################################################
		# removes a specific user's footprint from all feeds
		elif submitter_id:
			objs_to_delete = set()
			submitter_id = float(submitter_id)
			user_submissions = my_server.zrangebyscore(USER_SUBMISSIONS_AND_SUBMITTERS,submitter_id,submitter_id)
			if user_submissions:
				# delete them all - along with vote stores
				for submission in user_submissions:
					data = submission.split('*')
					which_feed, obj_hash_name = data[0], data[1]
					if which_feed == TRENDING_PHOTO_DETAILS:
						# TODO: remove this 'if' since TRENDING_PHOTO_DETAILS is defunct
						obj_id = int(obj_hash_name.split(":")[1])
						my_server.zremrangebyscore(which_feed,obj_id,obj_id)
					else:
						my_server.zrem(which_feed, obj_hash_name)# no need
						if obj_hash_name[:2] == 'tx':# removing vote stores (but after a lag of 10 mins)
							my_server.expire(VOTE_ON_TXT+obj_hash_name[3:],TEN_MINS)
						else:
							my_server.expire(VOTE_ON_IMG+obj_hash_name[4:],TEN_MINS)
						my_server.execute_command('UNLINK', obj_hash_name)# removing the object itself
						objs_to_delete.add(obj_hash_name)
				my_server.zrem(USER_SUBMISSIONS_AND_EXPIRES,*user_submissions)
				my_server.zrem(USER_SUBMISSIONS_AND_SUBMITTERS,*user_submissions)
				trim_trenders_data(target_user_id=submitter_id, my_server=my_server)
			if already_deleted_objs:
				private_objs = already_deleted_objs - objs_to_delete
				# these are objs which were part of 'private' feeds, and thus still have their vote stores intact
				# these are also objs that were 'removed' by the OP, and so didn't exist in USER_SUBMISSIONS_AND_SUBMITTERS
				if private_objs:
					for obj_hash_name in private_objs:
						my_server.execute_command('UNLINK', obj_hash_name)
						if obj_hash_name[:2] == 'tx':# removing vote stores (but after a lag of 10 mins)
							my_server.expire(VOTE_ON_TXT+obj_hash_name[3:],TEN_MINS)
						else:
							my_server.expire(VOTE_ON_IMG+obj_hash_name[4:],TEN_MINS)

		#########################################################################
		# takes care of expired user submissions
		else:
			expired_submissions = my_server.zrangebyscore(USER_SUBMISSIONS_AND_EXPIRES,'-inf',time_now)
			if expired_submissions:
				# delete them all - without needing to delete vote stores (they've self deleted)
				for submission in expired_submissions:
					data = submission.split('*')
					which_feed, obj_hash_name = data[0], data[1]
					if which_feed == TRENDING_PHOTO_DETAILS:
						# TODO: remove this 'if' since TRENDING_PHOTO_DETAILS is defunct
						obj_id = int(obj_hash_name.split(":")[1])
						my_server.zremrangebyscore(which_feed,obj_id,obj_id)
					else:
						my_server.zrem(which_feed, obj_hash_name)# no need to expire vote stores of these objects, since they've already self-deleted
				my_server.zrem(USER_SUBMISSIONS_AND_EXPIRES, *expired_submissions)
				my_server.zrem(USER_SUBMISSIONS_AND_SUBMITTERS, *expired_submissions)
				trim_trenders_data(my_server=my_server, time_now=time_now)


def trim_trenders_data(target_user_id=None, my_server=None, time_now=None):
	"""
	Removes trending items

	Called by a scheduled task every few hours, or via trim_expired_user_submissions() when a user is banned
	"""
	my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
	if target_user_id:
		target_obj_ids = my_server.zrangebyscore(TRENDING_FOTOS_AND_USERS,target_user_id, target_user_id)
		if target_obj_ids:
			my_server.zrem(TRENDING_FOTOS_AND_TIMES,*target_obj_ids)
			my_server.zrem(TRENDING_FOTOS_AND_USERS,*target_obj_ids)
	else:
		one_week_ago = (time_now - CONTEST_LENGTH) if time_now else (time.time() - CONTEST_LENGTH)
		obj_ids_to_delete = my_server.zrangebyscore(TRENDING_FOTOS_AND_TIMES,'-inf',one_week_ago)
		if obj_ids_to_delete:
			my_server.zrem(TRENDING_FOTOS_AND_TIMES,*obj_ids_to_delete)
			my_server.zrem(TRENDING_FOTOS_AND_USERS,*obj_ids_to_delete)

####################################################################################################
################################ Trending list related functonality ################################
####################################################################################################


def is_image_star(user_id,my_server=None):
	"""
	Used to determine whether a star is to be shown next to some nicks
	"""
	my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
	return my_server.zscore(TOP_TRENDER_IDS,user_id)


def is_pair_image_stars(user_1_id, user_2_id):
	"""
	Checks if the provided pair of users are top stars

	Special function useful in 1on1s
	"""
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.zscore(TOP_TRENDER_IDS, user_1_id), my_server.zscore(TOP_TRENDER_IDS, user_2_id)


def get_all_image_star_ids():
	"""
	Useful for embedding stars in big lists (e.g. online)
	"""
	return redis.Redis(connection_pool=POOL).zrange(TOP_TRENDER_IDS,0,-1)


def retreive_trending_rep(user_id):
	"""
	Useful for showing 'trending points' on user profiles and such
	"""
	return redis.Redis(connection_pool=POOL).zscore(TOP_TRENDERS_REP,user_id)



def retrieve_num_trending_photos(user_id):
	"""
	Retrieves the total number of trending images found in TRENDING_PHOTOS_AND_USERS for a given user_id

	This normally only contains as many images as dictated by CONTEST_LENGTH
	"""
	return redis.Redis(connection_pool=POOL).zcount(TRENDING_FOTOS_AND_USERS,user_id,user_id)


def retrieve_trending_photo_ids(user_id):
	"""
	Retrieves all trending photos uploaded by user_id currently available in TRENDING_PHOTOS_AND_USERS

	Normally we retain 1 week's worth of data, not longer
	"""
	return redis.Redis(connection_pool=POOL).zrangebyscore(TRENDING_FOTOS_AND_USERS,user_id,user_id)


def retrieve_handpicked_photos_count():
	"""
	Returns count of handpicked photos that are currently enqueued

	Useful for super_defenders in coordinating their voting efforts
	"""
	count = redis.Redis(connection_pool=POOL).zcard(HAND_PICKED_TRENDING_PHOTOS)
	if count:
		return count
	else:
		return 0


def retrieve_trenders_by_score():
	"""
	Retrieves top stars sorted by score calculated in calculate_trender_score()
	"""
	return redis.Redis(connection_pool=POOL).zrevrange(STAR_SCORE,0,-1)


def calculate_trender_score():
	"""
	Provides a 'score' for trenders - in order to rank them in the 'star list'

	'trending hit rate': num_trending_in_1_week / total_submitted_in_1_week
	'recency bonus': give a small 'boost' if most of the trending images were recent (i.e. within the past 3 days)
	"""
	user_ids = get_all_image_star_ids()# retrieve all star_ids
	if user_ids:
		from datetime import datetime, timedelta

		hit_rates = {}
		time_now = datetime.utcnow()
		one_week_ago = time_now-timedelta(days=7)
		image_data = Link.objects.filter(submitter_id__in=user_ids,submitted_on__gte=one_week_ago).\
		values_list('submitter_id','submitted_on','trending_status')
		
		if image_data:
			# defaultdict(int) is a python dictionary that doesn't give KeyError if 'key' doesn't exist (when dict is accessed)
			total_submissions_dict = defaultdict(int)# contains total images uploaded by a trender_id in last 7 days(trending and non-trending)
			trending_submissions_dict = defaultdict(int)# contains trending images uploaded by a trender_id in last 7 days
			num_trending_in_interval_one = defaultdict(int)# last 24 hours time window
			num_trending_in_interval_two = defaultdict(int)# last 24-48 hours time window
			num_trending_in_interval_three = defaultdict(int)# last 48-72 hours time window
			one_day_ago = time_now-timedelta(days=1)
			two_days_ago = time_now-timedelta(days=2)
			three_days_ago = time_now-timedelta(days=3)
			for image_tup in image_data:
				submitter_id, submitted_on, trending_status = image_tup[0], image_tup[1], image_tup[2]
				###########################################
				# gathering data for 'trending hit rate'
				total_submissions_dict[submitter_id] += 1
				if trending_status == '1':
					trending_submissions_dict[submitter_id] += 1
					###########################################
					# gathering data for 'recency bonus'
					if submitted_on >= one_day_ago:
						num_trending_in_interval_one[submitter_id] += 1
					elif submitted_on >= two_days_ago:
						num_trending_in_interval_two[submitter_id] += 1
					elif submitted_on >= three_days_ago:
						num_trending_in_interval_three[submitter_id] += 1
					else:
						# not eligible for bonus
						pass

			################################
			trender_ids = map(int, user_ids)
			for trender_id in trender_ids:

				total_submissions = total_submissions_dict.get(trender_id,0)
				total_trending = trending_submissions_dict.get(trender_id,0)

				# calculate the 'hit rate' of the trender
				hit_rate = (total_trending*1.0)/total_submissions if total_submissions else 0
				
				# eligible for a boost? calculate it
				trending_count_in_interval_one = num_trending_in_interval_one.get(trender_id,0)
				trending_count_in_interval_two = num_trending_in_interval_two.get(trender_id,0)
				trending_count_in_interval_three = num_trending_in_interval_three.get(trender_id,0)

				# has a trending image in: each of the previous 3 time intervals
				if trending_count_in_interval_one and trending_count_in_interval_two and trending_count_in_interval_three:
					weight_of_recent_trending = ((trending_count_in_interval_one+trending_count_in_interval_two+trending_count_in_interval_three)*1.0)/total_trending
					
					# most trending contributions came recently - the user is an active contributor
					if weight_of_recent_trending > 0.50:
						# give max boost available for this tier
						boost = 0.2 * hit_rate
					else:
						# give boost
						boost = 0.2 * hit_rate * (weight_of_recent_trending*2)

				# has a trending image in: the most recent two time intervals
				elif trending_count_in_interval_one and trending_count_in_interval_two:
					weight_of_recent_trending = ((trending_count_in_interval_one+trending_count_in_interval_two)*1.0)/total_trending

					# most trending contributions came recently - the user is an active contributor
					if weight_of_recent_trending > 0.30:
						# give max boost available for this tier
						boost = 0.15 * hit_rate
					else:
						# give boost
						boost = 0.15 * hit_rate * (weight_of_recent_trending*1.5)

				# has a trending image in: time interval one (0-24hrs) and time interval three (48-72 hrs)
				elif trending_count_in_interval_one and trending_count_in_interval_three:
					weight_of_recent_trending = ((trending_count_in_interval_one+trending_count_in_interval_three)*1.0)/total_trending

					# most trending contributions came recently - the user is an active contributor
					if weight_of_recent_trending > 0.30:
						# give max boost available for this tier
						boost = 0.10 * hit_rate
					else:
						# give boost
						boost = 0.10 * hit_rate * (weight_of_recent_trending*1.5)

				# has a trending image in: time interval one (0-24hrs) only
				elif trending_count_in_interval_one:
					weight_of_recent_trending = (trending_count_in_interval_one*1.0)/total_trending

					# most trending contributions came recently - the user is an active contributor
					if weight_of_recent_trending > 0.15:
						# give max boost available for this tier
						boost = 0.07 * hit_rate
					else:
						# give boost
						boost = 0.07 * hit_rate * (weight_of_recent_trending*3)

				# has a trending image in: time interval two (24-48hrs) and time interval three (48-72 hrs)
				elif trending_count_in_interval_two and trending_count_in_interval_three:
					weight_of_recent_trending = ((trending_count_in_interval_two+trending_count_in_interval_three)*1.0)/total_trending
					
					# most trending contributions came recently - the user is an active contributor
					if weight_of_recent_trending > 0.30:
						# give max boost available for this tier
						boost = 0.06 * hit_rate
					else:
						# give boost
						boost = 0.06 * hit_rate * (weight_of_recent_trending*1.5)

				# has a trending image in: time interval two (24-48hrs) one
				elif trending_count_in_interval_two:
					weight_of_recent_trending = (trending_count_in_interval_two*1.0)/total_trending

					# most trending contributions came recently - the user is an active contributor
					if weight_of_recent_trending > 0.15:
						# give max boost available for this tier
						boost = 0.045 * hit_rate
					else:
						# give boost
						boost = 0.045 * hit_rate * (weight_of_recent_trending*3)

				# has a trending image in: time interval three (48-72hrs) one
				elif trending_count_in_interval_three:
					weight_of_recent_trending = (trending_count_in_interval_three*1.0)/total_trending

					# most trending contributions came recently - the user is an active contributor
					if weight_of_recent_trending > 0.15:
						# give max boost available for this tier
						boost = 0.03 * hit_rate
					else:
						# give boost
						boost = 0.03 * hit_rate * (weight_of_recent_trending*3)

				# has no trending images in the most recent 3 time intervals
				else:
					boost = 0

				########################################

				hit_rates[trender_id] = hit_rate+boost

	# return hit_rates

	############ saving result in redis
	final_scores = []
	for key, value in hit_rates.iteritems():
		final_scores.append(key)
		final_scores.append(value)

	if final_scores:
		my_server = redis.Redis(connection_pool=POOL)
		my_server.delete(STAR_SCORE)
		my_server.zadd(STAR_SCORE,*final_scores)



def calculate_top_trenders():
	"""
	Calculating top X trending users within the prev Y hours (rolling-basis)

	Called by a scheduled task
	To calculate 'score', just counting the number of pics an uploader got into trending 
	TODO: consider moving this to a ratio of num_trending/num_total (e.g. how many posts of this user got into trending in the last X uploads)
	"""
	
	one_week_ago = time.time() - CONTEST_LENGTH
	my_server = redis.Redis(connection_pool=POOL)
	last_week_trending_photos = my_server.zrangebyscore(TRENDING_FOTOS_AND_TIMES, one_week_ago,'+inf')
	all_trending_photo_owners = my_server.zrange(TRENDING_FOTOS_AND_USERS, 0,-1,withscores=True)
	all_trending_photo_owners = dict(all_trending_photo_owners)# gives result in {'photo_id':'user_id'} form
	trending_user_ids = defaultdict(int)# a python dictionary that doesn't give KeyError if key doesn't exist when dict is accessed
	for photo_id in last_week_trending_photos:
		photo_owner_id = int(all_trending_photo_owners[photo_id])
		trending_user_ids[photo_owner_id] += 1
	list_of_tups = trending_user_ids.items()
	trending_list = [item for sublist in list_of_tups for item in sublist]#flattening the list of tuples into a simple list which redis accepts (technique explained here: https://stackoverflow.com/a/51291027/4936905)
	my_server.delete(TOP_TRENDING_SUBMITTERS)
	if trending_list:
		my_server.zadd(TOP_TRENDING_SUBMITTERS,*trending_list)


def process_top_trenders_rep(top_trending_ids_and_scores):
	"""
	Creates 'rep' for top trenders that can be used to give them "points" for incentivization

	GOAL: Incentivize posters to remain as long as they humanly can, in the trending pile
	
	Core algo:
	1) +1 every time a re-calc reveals the user: has jumped (or maintained) their rank AND increased their trending pics' count from previous level
	2) Otherwise, all users get a 0
	3) Churned users get a -1
	4) New entrants get a 1

	Advantages:
	- Measured against the crowd: If your rank fell (even if your number of trending pics increased) you get 0, because it seems the crowd around you moved up faster
	- Measured aganst yourself: If your rank improved, but number of trending pics didn't, you get 0 (because you haven't done anything to deserve a +1, someone else probably dropped out)
	"""
	my_server = redis.Redis(connection_pool=POOL)

	# Step 1) Retrieve previous trending IDs (ones that are about to be over-written)
	prev_trending_ids_and_scores = my_server.zrevrange(TOP_TRENDER_IDS,0,-1,withscores=True)# best to worst sorting, format: [('11',5), ('2',3), ...]

	if prev_trending_ids_and_scores:
		
		prev_trending_ids = [int(trending_id) for trending_id, score in prev_trending_ids_and_scores]
		prev_trending_ids_and_scores_dict = dict(prev_trending_ids_and_scores)
		new_trending_ids_and_scores_dict = dict(top_trending_ids_and_scores)

		# Step 2) Sort top_trending_ids_and_scores (descending order, sorted by score)
		sorted_top_trenders = sorted(top_trending_ids_and_scores,key=lambda x: x[1], reverse=True)

		# Step 3) Retrieve all current trending ids (ones that will over-write the previous ones)
		top_trending_ids = [trending_id for trending_id, score in sorted_top_trenders]# best to worst sorting
		###################################

		# Step 4) Isolate all IDs that have newly entered trending (i.e. were not part of the previous set)
		new_trenders = set([trending_id for trending_id in top_trending_ids if trending_id not in prev_trending_ids])

		# Step 5) Isolate all IDs that have churned from trending (i.e. were part of the previous set, but not the new one)
		churned_trenders = set([trending_id for trending_id in prev_trending_ids if trending_id not in top_trending_ids])

		# Step 6) Isolate all IDs common between prev and current trending users
		common_trending_ids = set.intersection(set(prev_trending_ids),set(top_trending_ids))

		# Step 7) Create a list containing new sorted trendng IDs and their respective ranks
		common_trending_ids_and_ranks = []
		rank = 1
		for trending_id, score in sorted_top_trenders:
			if trending_id in common_trending_ids:
				common_trending_ids_and_ranks.append((trending_id,rank))
			rank += 1

		# Step 8) Create a list containing old sorted trending IDs and their respective ranks
		prev_trending_ids_and_ranks = []
		rank = 1
		for trending_id in prev_trending_ids:
			prev_trending_ids_and_ranks.append((trending_id,rank))
			rank += 1

		###################################

		# Step 9) Calculate what rep increment each trender deserves
		scores_to_give = {}

		for churned_trending_id in list(churned_trenders):
			scores_to_give[churned_trending_id] = -1

		for new_entrant_trending_id in list(new_trenders):
			scores_to_give[new_entrant_trending_id] = 1

		for trending_id, rank in common_trending_ids_and_ranks:
			for prev_trending_id, prev_rank in prev_trending_ids_and_ranks:
				if trending_id == prev_trending_id:
					if rank <= prev_rank:
						# rank has improved, or maintained
						num_trending_previously = prev_trending_ids_and_scores_dict[str(trending_id)]
						num_trending_now = new_trending_ids_and_scores_dict[trending_id]
						if num_trending_now > num_trending_previously and random() < 0.75:
							# moreover, num trending pics are greater than before (and adding a bit of stochasticity to the proceedings)
							scores_to_give[trending_id] = 1 
						else:
							scores_to_give[trending_id] = 0 
					else:
						scores_to_give[trending_id] = 0

		##################################

		# Step 10) Allot the points
		pipeline1 = my_server.pipeline()
		for trending_id, score in scores_to_give.iteritems():
			if score != 0:
				pipeline1.zincrby(TOP_TRENDERS_REP,trending_id,amount=score)
		pipeline1.execute()

		###################################

		# Step 11) Update the top trenders list
		my_server.delete(TOP_TRENDER_IDS)
		my_server.zadd(TOP_TRENDER_IDS,*list(sum(top_trending_ids_and_scores, ())))# flattening top_trending_ids_and_scores and passing to zadd

		###################################

		# Step 12) Update the truncator set
		time_now = time.time()
		trending_ids_and_times = []
		for trending_id in top_trending_ids:
			trending_ids_and_times.append(trending_id)
			trending_ids_and_times.append(time_now)
		my_server.zadd(TOP_TRENDERS_REP_TRUNCATOR,*trending_ids_and_times)
		###################################
		
		# Step 13) Truncate trending_ids' reps that have not showed up for the past 3 months
		if random() < 0.05:
			# sometimes trim the trending sorted set for size
			three_months_ago = time_now - THREE_MONTHS
			trending_ids_to_expire = my_server.zrangebyscore(TOP_TRENDERS_REP_TRUNCATOR,'-inf',three_months_ago)
			if trending_ids_to_expire:
				my_server.zrem(TOP_TRENDERS_REP,*trending_ids_to_expire)
				my_server.zrem(TOP_TRENDERS_REP_TRUNCATOR,*trending_ids_to_expire)

	# no previous trending ids found
	else:

		# Step 2) Sort top_trending_ids_and_scores (descending order, sorted by score)
		sorted_top_trenders = sorted(top_trending_ids_and_scores,key=lambda x: x[1], reverse=True)

		# Step 3) Retrieve all top trending ids
		top_trending_ids = [trending_id for trending_id, score in sorted_top_trenders]# best to worst sorting

		# Step 4) Update the top trenders list
		my_server.delete(TOP_TRENDER_IDS)
		my_server.zadd(TOP_TRENDER_IDS,*list(sum(top_trending_ids_and_scores, ())))# flattening top_trending_ids_and_scores and passing to zadd
	
		# Step 5) Update the truncator set
		time_now = time.time()
		trending_ids_and_times = []
		for trending_id in top_trending_ids:
			trending_ids_and_times.append(trending_id)
			trending_ids_and_times.append(time_now)
		my_server.zadd(TOP_TRENDERS_REP_TRUNCATOR,*trending_ids_and_times)


def trim_trending_list(feed_type='best_photos'):
	"""
	Trims trending list down to NUM_TRENDING_PHOTOS elements (in case of the trending photos feed)
	"""
	if feed_type == 'best_photos':
		my_server = redis.Redis(connection_pool=POOL)
		photo_hashes_to_be_removed = my_server.zrevrange(TRENDING_PHOTO_FEED,NUM_TRENDING_PHOTOS,-1)
		if photo_hashes_to_be_removed:
			photo_ids_to_be_removed = [hash_obj.split(":")[1] for hash_obj in photo_hashes_to_be_removed]
			photo_ids_to_be_removed = map(float,photo_ids_to_be_removed)
			pipeline1 = my_server.pipeline()
			pipeline1.zrem(TRENDING_PHOTO_FEED, *photo_hashes_to_be_removed)
			# for photo_id in photo_ids_to_be_removed:
			# 	pipeline1.zremrangebyscore(TRENDING_PHOTO_DETAILS,photo_id,photo_id)
			pipeline1.execute()
	else:
		pass


def retrieve_top_trenders():
	"""
	Populates top stars listing (i.e. list of top trenders of the photo section)
	"""
	my_server = redis.Redis(connection_pool=POOL)
	trenders_data = my_server.get(TOP_TRENDERS)
	if trenders_data:
		return json.loads(trenders_data)
	else:
		rank = 0
		all_trenders = my_server.zrevrange(TOP_TRENDING_SUBMITTERS,0,-1,withscores=True)
		all_trender_ids = [user_id for user_id, num_pics in all_trenders]
		user_cred_dict = retrieve_bulk_credentials(all_trender_ids,decode_unames=False)
		
		if all_trenders:
			starting_score = all_trenders[0][1]#num trending pics of top user
			final_list=[]
			rank_to_display = 0
			top_trending_ids_and_scores = []

			for row in all_trenders:
				if starting_score == row[1]:
					trender_id = int(row[0])
					if (rank_to_display != rank+1):
						rank_to_display = rank+1
						final_list.append((trender_id  ,int(row[1]), rank+1, user_cred_dict[trender_id]['uname'], user_cred_dict[trender_id]['avurl'],rank_to_display  ) )
					else:
						final_list.append(( trender_id  ,int(row[1]), rank+1, user_cred_dict[trender_id]['uname'], user_cred_dict[trender_id]['avurl'] ) )
					top_trending_ids_and_scores.append((trender_id,int(row[1])))
				else:
					starting_score = row[1]
					rank +=1
					if rank == TRENDER_RANKS_TO_COUNT:
						break
					else:
						trender_id = int(row[0])
						if (rank_to_display != rank+1):
							rank_to_display = rank+1
							final_list.append(( trender_id  ,int(row[1]), rank+1, user_cred_dict[trender_id]['uname'], user_cred_dict[trender_id]['avurl'], rank_to_display  ) )
						else:
							final_list.append(( trender_id  ,int(row[1]), rank+1, user_cred_dict[trender_id]['uname'], user_cred_dict[trender_id]['avurl'] ) )
						top_trending_ids_and_scores.append((trender_id,int(row[1])))

			if final_list:
				my_server.setex(TOP_TRENDERS, json.dumps(final_list),THIRTY_MINS)
				process_top_trenders_rep(top_trending_ids_and_scores)
			return 	final_list
		else: 
			return []


def add_single_trending_object_in_feed(obj_hash, time_now, feed_type='home'):
	"""
	Just a quick way to add trending objs in a feed

	TODO: Use the sophisticated add_single_trending_object() later, sunset this
	"""
	if feed_type == 'home':
		feed_name = TRENDING_HOME_FEED
	elif feed_type == 'photos':
		feed_name = ALT_TRENDING_HOME_FEED
	my_server = redis.Redis(connection_pool=POOL)
	my_server.zadd(feed_name,obj_hash, time_now)
	Link.objects.filter(id=obj_hash.partition(":")[-1]).update(trending_status='1')
	if random() < 0.1:
		my_server.zremrangebyrank(feed_name, 0, -201)# to keep top 200 in the sorted set
	#############################
	# ensuring the 'feed cleaning' functionality can track this object (for effective cleansing of related redis sets/objs etc.)
	json_obj = my_server.hget(obj_hash,'blob')
	if json_obj:
		obj = json.loads(json_obj)
		feeds_to_subtract = []#Change this to [HOME_SORTED_FEED] when best text posts are shown to users
		log_user_submission(submitter_id=obj['si'], submitted_obj=obj_hash, feeds_to_add=[feed_name], \
			feeds_to_subtract=feeds_to_subtract, my_server=my_server)
	#############################
	#  Logging trending posts for analysis (can remove)
	# json_data_blob, editorial_upvotes = my_server.hmget(obj_hash,'blob','uv')
	# try:
	# 	data = json.loads(json_data_blob)
	# except:
	# 	data = json_backup.loads(json_data_blob)
	# from redis4 import log_home_post
	# log_home_post(user_id=data['si'], username=data['su'], text=data['d'], on_fbs=data.get('fbs',''),is_urdu=data['c'], \
	# 	editorial_upvotes=editorial_upvotes, trending_time=time_now, posting_time=data['t'])


def add_single_trending_object(prefix, obj_id, obj_hash, my_server=None, from_hand_picked=False):
	"""
	Adds a single trending object to a trending list of objects

	Also adds the objects details to a separate sorted set for later viewing, helpful if obj metrics are to be compared at the time of its selection
	"""
	if prefix == 'img:':
		composite_id = prefix+obj_id
		submitter_id = obj_hash['si']
		time_of_selection = obj_hash['tos']
		float_time_of_selection = float(time_of_selection)
		my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
		pipeline1 = my_server.pipeline()
		# pipeline1.zadd(TRENDING_PHOTO_DETAILS, obj_hash, int(obj_id))# TODO: Remove, this looks expendible
		pipeline1.zadd(TRENDING_PHOTO_FEED, composite_id, float_time_of_selection)# used to populate the trending section
		pipeline1.zrem(PHOTO_SORTED_FEED,composite_id)# since photo has already moved to trending, remove entry from 'latest'
		pipeline1.zadd(TRENDING_FOTOS_AND_TIMES,obj_id,float_time_of_selection)
		pipeline1.zadd(TRENDING_FOTOS_AND_USERS,obj_id,float(submitter_id))
		pipeline1.execute()
		############################
		# setting the 'is_trending flag'
		json_obj_data = my_server.hget(composite_id,'blob')
		if json_obj_data:
			obj_data = json.loads(json_obj_data)
			obj_data['tr'] = '1'
			my_server.hset(composite_id,'blob',json.dumps(obj_data))
		############################
		# Photo.objects.filter(id=obj_id).update(device='6')
		Link.objects.filter(id=obj_id).update(trending_status='1')
		save_recent_trending_photo(user_id=submitter_id, photo_id=obj_id, time_of_selection=float_time_of_selection, my_server=my_server)
		if random() < 0.05:
			# sometimes trim the trending sorted set for size
			trim_trending_list()
		feeds_to_add = [TRENDING_PHOTO_FEED]#,TRENDING_PHOTO_DETAILS]
		feeds_to_subtract = [PHOTO_SORTED_FEED,HAND_PICKED_TRENDING_PHOTOS] if from_hand_picked else [PHOTO_SORTED_FEED]
		log_user_submission(submitter_id=submitter_id, submitted_obj=composite_id, feeds_to_add=feeds_to_add, \
			feeds_to_subtract=feeds_to_subtract, my_server=my_server)
		if not my_server.exists(HANDPICKED_TRENDING_IMG+composite_id):
			my_server.setex(NONHANDPICKED_TRENDING_IMG+composite_id,'1',ONE_MONTH)
	else:
		pass


def select_hand_picked_obj_for_trending(feed_type='best_photos'):
	"""
	Pick the submitter within HAND_PICKED_TRENDING_PHOTOS with the best voting score (aud-likes based vote score used here)
	"""
	pushed, obj_id, audience = False, None, None
	my_server = redis.Redis(connection_pool=POOL)
	all_enqueued_members = my_server.zrange(HAND_PICKED_TRENDING_PHOTOS,0,-1)	
	vote_keys = []
	for obj in all_enqueued_members:
		data = obj.partition(":")
		obj_type, obj_id = data[0], data[-1]
		if obj_type == 'tx':
			vote_key = VOTE_ON_TXT+obj_id
		else:
			vote_key = VOTE_ON_IMG+obj_id
		vote_keys.append((vote_key, obj))

	pipeline1 = my_server.pipeline()
	for vote_key, obj_hash_name in vote_keys:
		pipeline1.zrange(vote_key,0,-1)
		pipeline1.hgetall(obj_hash_name)
	result1, counter = pipeline1.execute(),0

	objs_and_vote_vals = []
	for obj in all_enqueued_members:

		highest_vote_score = 0
		obj_votes = result1[counter]
		if obj_votes:
			for voter_id in obj_votes:
				vote_score = my_server.zscore(VOTER_AUD_LIKE_PROBS,voter_id)
				if vote_score > highest_vote_score:
					highest_vote_score = vote_score
		###############################################################	
		obj_data = result1[counter+1]
		if obj_data:
			obj_data = unpack_json_blob([obj_data])[0]
			time_of_submission = obj_data['t']
		###############################################################
			objs_and_vote_vals.append((obj, highest_vote_score, time_of_submission, obj_data))
		else:
			my_server.zrem(HAND_PICKED_TRENDING_PHOTOS,obj)# remove from hand_picked list
		counter += 2

	# first sort according to vote score (descending), and then time of submission (ascending)
	objs_and_vote_vals = sorted(objs_and_vote_vals, key=lambda x: (-x[1], x[2]))

	# selecting the best 5 - now try pushing them one by one
	best_trending_items = objs_and_vote_vals[:5]

	if best_trending_items:
		for obj_hash_name, item_highest_vote, time_of_submission, obj_hash_data in best_trending_items:
			# this img obj is locked from entering trending because of sybil votes
			if my_server.exists(LOCKED_IMG+obj_hash_name):
				my_server.zrem(HAND_PICKED_TRENDING_PHOTOS,obj_hash_name)# remove from hand_picked list
			
			# push this into trending
			else:
				obj_id = obj_hash_data['i']
				audience = obj_hash_data['aud']
				obj_hash_data['tos'] = time.time()# time_of_selection
				########################
				# related to 'rep'
				my_server.setex(HANDPICKED_TRENDING_IMG+obj_hash_name,'1',ONE_MONTH)# this key is only set if the obj was NOT locked
				my_server.zadd(GLOBAL_HANDPICKED_IMG_DATA,obj_hash_name+":"+str(obj_hash_data['si']),obj_hash_data['si'])
				# ########################
				# # do the deed - push the object for members to see!
				add_single_trending_object(prefix='img:', obj_id=obj_id, obj_hash=obj_hash_data, my_server=my_server,\
					from_hand_picked=True)
				my_server.zrem(HAND_PICKED_TRENDING_PHOTOS,obj_hash_name)# remove from hand_picked list as well
				pushed = True
				break# break out of the for loop
	
	return pushed, obj_id, audience


# def select_hand_picked_obj_for_trending(feed_type='best_photos'):
# 	"""
# 	Pick the submitter within HAND_PICKED_TRENDING_PHOTOS with the best voting score (aud-likes based vote score used here)
# 	"""
# 	pushed, obj_id = False, None
# 	my_server = redis.Redis(connection_pool=POOL)
# 	all_enqueued_members = my_server.zrange(HAND_PICKED_TRENDING_PHOTOS,0,-1)	
# 	vote_keys = []
# 	for obj in all_enqueued_members:
# 		data = obj.partition(":")
# 		obj_type, obj_id = data[0], data[-1]
# 		if obj_type == 'tx':
# 			vote_key = VOTE_ON_TXT+obj_id
# 		else:
# 			vote_key = VOTE_ON_IMG+obj_id
# 		vote_keys.append(vote_key)

# 	pipeline1 = my_server.pipeline()
# 	for vote_key in vote_keys:
# 		pipeline1.zrange(vote_key,0,-1)
# 	result1, counter = pipeline1.execute(),0

# 	objs_and_vote_vals = []
# 	for obj in all_enqueued_members:

# 		highest_vote_score = 0
# 		obj_votes = result1[counter]
# 		if obj_votes:
# 			for voter_id in obj_votes:
# 				vote_score = my_server.zscore(VOTER_AUD_LIKE_PROBS,voter_id)
# 				if vote_score > highest_vote_score:
# 					highest_vote_score = vote_score
		





# 		objs_and_vote_vals.append((obj, highest_vote_score))
# 		counter += 1

	
# 	objs_and_vote_vals.sort(key=itemgetter(1),reverse=True)

	
# 	best_trending_items = objs_and_vote_vals[:5]# selecting the best 5 - now try pushing them one by one
# 	if best_trending_items:
# 		for obj_hash_name, item_highest_vote in best_trending_items:
# 			obj_hash = my_server.hgetall(obj_hash_name)
# 			if obj_hash:
# 				# this img obj is locked from entering trending because of sybil votes
# 				if my_server.exists(LOCKED_IMG+obj_hash_name):
# 					my_server.zrem(HAND_PICKED_TRENDING_PHOTOS,obj_hash_name)# remove from hand_picked list
# 				else:
# 					# do the deed - push the object for members to see!
# 					time_of_selection = time.time()
# 					obj_hash['tos'] = time_of_selection
# 					obj_hash = unpack_json_blob([obj_hash])[0]
# 					obj_id = obj_hash['i']
# 					########################
# 					# related to 'rep'
# 					my_server.setex(HANDPICKED_TRENDING_IMG+obj_hash_name,'1',ONE_MONTH)# this key is only set if the obj was NOT locked
# 					my_server.zadd(GLOBAL_HANDPICKED_IMG_DATA,obj_hash_name+":"+str(obj_hash['si']),obj_hash['si'])
# 					########################
# 					add_single_trending_object(prefix='img:', obj_id=obj_id, obj_hash=obj_hash, my_server=my_server,\
# 						from_hand_picked=True)
# 					my_server.zrem(HAND_PICKED_TRENDING_PHOTOS,obj_hash_name)# remove from hand_picked list as well
# 					pushed = True
# 					break# break out of the for loop
# 			else:
# 				my_server.zrem(HAND_PICKED_TRENDING_PHOTOS,obj_hash_name)# remove from hand_picked list
	
# 	return pushed, obj_id


def push_hand_picked_obj_into_trending(feed_type='best_photos'):
	"""
	HAND_PICKED_TRENDING_PHOTOS contains photos earmarked for movement into trending - this executes the whole procedure

	Note: Doesn't push a handpicked item into trending that has been tainted by sybil votes
	"""
	pushed, obj_id = False, None
	if feed_type == 'best_photos':
		# retrieve oldest object from HAND_PICKED_TRENDING_PHOTOS and push it into trending
		my_server = redis.Redis(connection_pool=POOL)
		if my_server.exists(HAND_PICKED_TRENDING_PHOTOS):
			# sorted set exists
			oldest_enqueued_member = my_server.zrange(HAND_PICKED_TRENDING_PHOTOS,0,0)
			if oldest_enqueued_member:
				# push it if the obj's hash exists and its still in fresh, otherwise just ignore
				oldest_enqueued_member = oldest_enqueued_member[0]
				obj_hash = my_server.hgetall(oldest_enqueued_member)
				if obj_hash:
					if my_server.exists(LOCKED_IMG+oldest_enqueued_member):
						# this img obj is locked from entering trending because of sybil votes
						my_server.zrem(HAND_PICKED_TRENDING_PHOTOS,oldest_enqueued_member)# remove from hand_picked list as well
						pushed = False
					else:
						# do the deed - push the object for members to see!
						time_of_selection = time.time()
						obj_hash['tos'] = time_of_selection
						obj_hash = unpack_json_blob([obj_hash])[0]
						obj_id = obj_hash['i']
						########################
						my_server.setex(HANDPICKED_TRENDING_IMG+oldest_enqueued_member,'1',ONE_MONTH)# this key is only set if the obj was NOT locked
						my_server.zadd(GLOBAL_HANDPICKED_IMG_DATA,oldest_enqueued_member+":"+str(obj_hash['si']),obj_hash['si'])
						########################
						add_single_trending_object(prefix='img:', obj_id=obj_id, obj_hash=obj_hash, my_server=my_server,\
							from_hand_picked=True)
						my_server.zrem(HAND_PICKED_TRENDING_PHOTOS,oldest_enqueued_member)# remove from hand_picked list as well
						pushed = True
				else:
					my_server.zrem(HAND_PICKED_TRENDING_PHOTOS,oldest_enqueued_member)# remove from hand_picked list
					pushed = False
			else:
				# if the handpicked item's data was corrupt
				pushed = False
		else:
			# when nothing remains in the handpicked queue
			pushed = None
	else:
		pushed = False
	return pushed, obj_id


def get_obj_data(obj_hash_name):
	"""
	used for loggers
	"""
	return redis.Redis(connection_pool=POOL).hgetall(obj_hash_name)


def queue_obj_into_trending(prefix, obj_owner_id, obj_id, picked_by_id):
	"""
	Used by super defenders to just move an object straight into trending

	The object does not get added immediately, is instead entered into a queue
	Next time when the celery task runs, this queue is popped and the next trending object is shown
	If two super defenders enqueue the same item for movement into trending, the object simply moves in by the 'initially' set priority
	"""
	if prefix == 'img:':
		time_now = time.time()
		composite_id = prefix+obj_id
		my_server = redis.Redis(connection_pool=POOL)
		already_enqueued = my_server.zscore(HAND_PICKED_TRENDING_PHOTOS,composite_id)
		if already_enqueued:
			# do nothing
			pass
		else:
			# Enqueue the object, but first: i) check if it's already moved into trending (just to be sure), ii) it still exists in fresh (and wasn't censored for instance)
			already_trending = my_server.zscore(TRENDING_PHOTO_FEED, composite_id)
			if already_trending:
				# do nothing
				pass
			else:
				still_in_fresh = my_server.zscore(PHOTO_SORTED_FEED,composite_id)
				if still_in_fresh:
					# Enqueue for trending
					expire_at = int(time_now+PUBLIC_SUBMISSION_TTL)
					pipeline1 = my_server.pipeline()
					pipeline1.zadd(HAND_PICKED_TRENDING_PHOTOS,composite_id,time_now)
					pipeline1.hset(composite_id,'pbid',picked_by_id)# records the ID of the super-defender who ordered this movement
					pipeline1.expireat(composite_id,expire_at)#re-setting TTL to 7 days
					pipeline1.expireat(VOTE_ON_IMG+obj_id,expire_at)#re-setting TTL to 7 days
					pipeline1.execute()
					log_user_submission(submitter_id=obj_owner_id, submitted_obj=composite_id, expire_at=expire_at, \
						feeds_to_add=[HAND_PICKED_TRENDING_PHOTOS], my_server=my_server)
				else:
					# not in fresh any more (e.g. because 1000 pics have overflown) - so do nothing!
					pass
	else:
		pass


def remove_obj_from_trending(prefix,obj_id):
	"""
	Used by super defenders to remove an object from the trending list

	This item is not added back into fresh-list, it is just removed from trending entirely
	"""
	if prefix == 'img:':
		composite_id = prefix+obj_id
		my_server = redis.Redis(connection_pool=POOL)
		# ensure it's not in handpicked photos (e.g. if super-defender changed their mind about enqueing it)
		my_server.zrem(HAND_PICKED_TRENDING_PHOTOS,composite_id)
		obj_owner_id = unpack_json_blob([my_server.hgetall(composite_id)])[0]['si']
		obj_is_trending = my_server.zscore(TRENDING_PHOTO_FEED,composite_id)
		if obj_is_trending:
			# remove it from trending
			pipeline1 = my_server.pipeline()
			pipeline1.zrem(TRENDING_PHOTO_FEED,composite_id)
			# pipeline1.zremrangebyscore(TRENDING_PHOTO_DETAILS,obj_id,obj_id)
			pipeline1.zrem(TRENDING_FOTOS_AND_TIMES,obj_id)
			pipeline1.zrem(TRENDING_FOTOS_AND_USERS,obj_id)
			pipeline1.execute()
			# in case the object trended and was part of the sitemap, remove it from the sitemap model
			if Cooldown.objects.filter(content_id=obj_id).exists():
				Cooldown.objects.filter(content_id=obj_id).delete()
			Link.objects.filter(id=obj_id).update(trending_status='0')
			feeds_to_subtract = [TRENDING_PHOTO_FEED]#,TRENDING_PHOTO_DETAILS]#,TRENDING_PICS_AND_TIMES,TRENDING_PICS_AND_USERS]
			log_user_submission(submitter_id=obj_owner_id, submitted_obj=composite_id, feeds_to_subtract=feeds_to_subtract, \
				my_server=my_server)
			#####################################
			my_server.execute_command('UNLINK', HANDPICKED_TRENDING_IMG+composite_id)# in case key was set
			my_server.execute_command('UNLINK', NONHANDPICKED_TRENDING_IMG+composite_id)# in case key was set
			my_server.zrem(GLOBAL_HANDPICKED_IMG_DATA,composite_id+":"+str(obj_owner_id))
			#####################################
		else:
			# not in trending yet (for whatever reason)
			log_user_submission(submitter_id=obj_owner_id, submitted_obj=composite_id, feeds_to_subtract=[HAND_PICKED_TRENDING_PHOTOS], \
				my_server=my_server)
	else:
		pass


def is_obj_trending(prefix, obj_id, with_trending_time=False):
	"""
	Retrieves the trending status of an object
	"""
	if prefix == 'img:': 
		composite_id = prefix+str(obj_id)
		my_server = redis.Redis(connection_pool=POOL)
		if with_trending_time:
			time_of_selection = my_server.zscore(TRENDING_PHOTO_FEED,composite_id)
			if time_of_selection:
				return True, time_of_selection
			else:
				return False, None
		else:
			return my_server.zscore(TRENDING_PHOTO_FEED,composite_id)
	else:
		pass

####################################################################################################
###################### Helper functions for guaging objects user has voted on ######################
####################################################################################################


def retrieve_last_vote_time(voter_id):
	"""
	Retrieves the last voting time of a given voter (if it exists)
	"""
	tup = redis.Redis(connection_pool=POOL).zrange(VOTER_UVOTES_AND_TIMES+str(voter_id),-1,-1,withscores=True)
	return tup[0][1] if tup else 0


def retrieve_recent_votes(voter_id, oldest_post_time):
	"""
	Retrieves which object hashes has the voter given a 'like' to recently
	
	Useful for various feeds, such as home, topics and photos, assisting us in showing various states of the 'LIKE' button
	"""
	return redis.Redis(connection_pool=POOL).zrangebyscore(VOTER_UVOTES_AND_TIMES+str(voter_id),oldest_post_time,'+inf')


def check_votes_on_objs(obj_list, voter_id):
	"""
	Retrieves whether voter_id voted on any img obj in obj_list via doing a bulk 'zscore'

	Useful to show state of 'like' button in lists that are not sorted by time (e.g. best-photos)
	UNUSED at the moment
	"""
	pipeline1 = redis.Redis(connection_pool=POOL).pipeline()
	for vote_store_key in [VOTE_ON_IMG+img_obj.partition(":")[-1] for img_obj in obj_list]:
		pipeline1.zscore(vote_store_key,voter_id)
	result1, counter = pipeline1.execute(), 0
	objs_voted_on = set()
	for img_obj in obj_list:
		if result1[counter] >= 0:
			objs_voted_on.add(img_obj)
		counter += 1
	return objs_voted_on


####################################################################################################
################################# Bayesian voting calculations #####################################
####################################################################################################


def retrieve_users_voting_relationships(target_user_id, rel_type):
	"""
	Used to populate list of potential sybils/haters for super-defenders

	Can also display reverse-sybil data, i.e. which 'clients' is a voter servicing
	Uses the set called VOTING_RELATIONSHIP_LOG and VOTER_AFFINITY_HASH to generate said reports
	"""
	target_user_id = str(target_user_id)
	my_server = redis.Redis(connection_pool=POOL)
	if rel_type == 'reverse-sybils':
		cached_data = my_server.get(CACHED_REV_SYB_RELATIONSHIP+target_user_id)
		if cached_data:
			return json.loads(cached_data)
		else:
			if my_server.exists(SYBIL_RELATIONSHIP_LOG):
				reverse_sybil_relationships = my_server.zrangebyscore(SYBIL_RELATIONSHIP_LOG,target_user_id,target_user_id)
			else:
				create_sybil_relationship_log()# creating SYBIL_RELATIONSHIP_LOG
				reverse_sybil_relationships = my_server.zrangebyscore(SYBIL_RELATIONSHIP_LOG,target_user_id,target_user_id)
			if reverse_sybil_relationships:
				vote_targets = []
				pipeline1 = my_server.pipeline()
				for voter_target_pair in reverse_sybil_relationships:
					vote_targets.append(voter_target_pair.split(":")[1])
					pipeline1.hgetall(VOTER_AFFINITY_HASH+voter_target_pair)
				result1, counter = pipeline1.execute(), 0
				if result1:
					vote_tgt_cred_dict, final_data = retrieve_bulk_credentials(vote_targets,decode_unames=True), []
					for voter_target_pair in reverse_sybil_relationships:
						vote_tgt_id, data = vote_targets[counter], result1[counter]
						if data:
							# only collate data if VOTER_AFFINITY_HASH existed
							last_vote_time = data['vt']
							raw_bayes_data = json.loads(data['blob'])
							prob_p0 = float(data.get('p0',0))
							prob_p1 = float(data.get('p1',0))
							if prob_p0 >= BAYESIAN_PROB_THRESHOLD_FOR_VOTE_NERFING:# currently set to 0.3
								# relates to downvotes
								tup = (vote_tgt_id, vote_tgt_cred_dict[int(vote_tgt_id)]['uname'], vote_tgt_cred_dict[int(vote_tgt_id)]['avurl'], 0, \
									prob_p0, last_vote_time, raw_bayes_data['uv'],raw_bayes_data['dv'],raw_bayes_data['tuv'],raw_bayes_data['tdv'])
								final_data.append(tup)
							elif prob_p1 >= BAYESIAN_PROB_THRESHOLD_FOR_VOTE_NERFING:# currently set to 0.3
								# relates to upvotes
								tup = (vote_tgt_id, vote_tgt_cred_dict[int(vote_tgt_id)]['uname'], vote_tgt_cred_dict[int(vote_tgt_id)]['avurl'], 1, \
									prob_p1, last_vote_time, raw_bayes_data['uv'],raw_bayes_data['dv'],raw_bayes_data['tuv'],raw_bayes_data['tdv'])
								final_data.append(tup)
						counter += 1
					if final_data:
						final_data.sort(key=itemgetter(3,4,5),reverse=True)
						my_server.setex(CACHED_REV_SYB_RELATIONSHIP+target_user_id,json.dumps(final_data),TWENTY_MINS)
					return final_data
				else:
					return []
			else:
				return []


	elif rel_type == 'sybils':
		cached_data = my_server.get(CACHED_VOTING_RELATIONSHIP+target_user_id)
		if cached_data:
			return json.loads(cached_data)
		else:
			voting_relationships = my_server.zrangebyscore(VOTING_RELATIONSHIP_LOG,target_user_id,target_user_id)
			if voting_relationships:
				# return list of dictionaries
				final_data, voters = [], []
				pipeline1 = my_server.pipeline()
				for voter_target_pair in voting_relationships:
					voters.append(voter_target_pair.split(":")[0])
					pipeline1.hgetall(VOTER_AFFINITY_HASH+voter_target_pair)
				result1, counter = pipeline1.execute(), 0
				if result1:
					voter_cred_dict = retrieve_bulk_credentials(voters,decode_unames=True)
					for voter_target_pair in voting_relationships:
						voter_id, data = voters[counter], result1[counter]
						if data:
							# only collate data if VOTER_AFFINITY_HASH existed
							last_vote_time = data['vt']
							raw_bayes_data = json.loads(data['blob'])
							prob_p0 = float(data.get('p0',0))
							prob_p1 = float(data.get('p1',0))
							if prob_p0 >= BAYESIAN_PROB_THRESHOLD_FOR_VOTE_NERFING:# set to 0.3
								# relates to downvotes
								tup = (voter_id, voter_cred_dict[int(voter_id)]['uname'], voter_cred_dict[int(voter_id)]['avurl'], 0, prob_p0, \
									last_vote_time, raw_bayes_data['uv'],raw_bayes_data['dv'],raw_bayes_data['tuv'],raw_bayes_data['tdv'])
								final_data.append(tup)
							elif prob_p1 >= BAYESIAN_PROB_THRESHOLD_FOR_VOTE_NERFING:# set to 0.3
								# relates to upvotes
								tup = (voter_id, voter_cred_dict[int(voter_id)]['uname'], voter_cred_dict[int(voter_id)]['avurl'], 1, prob_p1, \
									last_vote_time, raw_bayes_data['uv'],raw_bayes_data['dv'],raw_bayes_data['tuv'],raw_bayes_data['tdv'])
								final_data.append(tup)
						counter += 1
					if final_data:
						final_data.sort(key=itemgetter(3,4,5),reverse=True)
						my_server.setex(CACHED_VOTING_RELATIONSHIP+target_user_id,json.dumps(final_data),TWENTY_MINS)
					return final_data
				else:
					return []
			else:
				return []
	else:
		return []


def calculate_bayesian_affinity(suspected_affinity, voter_and_target_data):
	"""
	'suspected_affinity' can be 'upvote' or 'downvote'

	The formula is as follows:
	P(sybil|upvote) = (P(upvote|sybil)*P(sybil))/P(upvote)
	where:
	- P(upvote|sybil) is 100% (by definition)
	- P(sybil) is calculated via (num_net_upvotes_given_to_target_user_id/total_votes_cast)
	- num_net_upvotes_given_to_target_user_id = upvotes - downvotes
	- P(upvote) is (P(sybil,upvoted)+P(non-sybil,upvoted)) - ',' means AND
	"""
	if suspected_affinity == 'upvote':
		suspected_vote_type_keyname, other_vote_type_keyname, suspected_vote_to_tgt_keyname, other_vote_to_tgt_keyname = 'tuv', 'tdv',\
		'uv', 'dv'
	elif suspected_affinity == 'downvote':
		suspected_vote_type_keyname, other_vote_type_keyname, suspected_vote_to_tgt_keyname, other_vote_to_tgt_keyname = 'tdv', 'tuv',\
		'dv', 'uv'
	final_result = []
	rels_of_interest_list = voter_and_target_data.keys()
	for voter_and_target in rels_of_interest_list:
		# voter_and_target_data is a dictionary of dictionaries
		vote_data_of_interest = voter_and_target_data[voter_and_target]
		suspected_votes_of_interest, other_votes_of_interest = vote_data_of_interest[suspected_vote_type_keyname], vote_data_of_interest[other_vote_type_keyname]
		suspected_votes_to_tgt, other_votes_to_tgt = vote_data_of_interest[suspected_vote_to_tgt_keyname], vote_data_of_interest[other_vote_to_tgt_keyname]
		if suspected_votes_to_tgt <= other_votes_to_tgt:
			# what we're suspecting is definitely not true
			final_result.append((voter_and_target, 0.0, json.dumps(vote_data_of_interest)))
		else:
			# what we're suspecting might be true
			all_votes = suspected_votes_of_interest+other_votes_of_interest
			numerator = ((suspected_votes_to_tgt - other_votes_to_tgt)*1.0)/all_votes
			denominator = numerator + ((1-numerator)*((suspected_votes_of_interest*1.0)/all_votes))
			bayesian_prob = numerator/denominator
			final_result.append((voter_and_target, bayesian_prob, json.dumps(vote_data_of_interest)))# list of tuples [(pair, bayes_prob, suspected_affinity, json_data),...]
	return final_result



def retrieve_voter_target_action_count(voter_target_list, vote_type, my_server=None):
	"""
	For each voter:target pair, we need 'upvotes to target', 'downvotes to target', 'all upvotes' and 'all downvotes'

	Once retrieved, this information is used to calculate Bayesian voting affinities
	"""
	if voter_target_list:
		my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
		###########################################
		pipeline0 = my_server.pipeline()
		for voter_and_target in voter_target_list:
			voter_id = voter_and_target.split(":")[0]
			voter_uvote_key, voter_dvote_key = VOTER_UVOTES_AND_TIMES+voter_id, VOTER_DVOTES_AND_TIMES+voter_id
			pipeline0.zrange(voter_uvote_key,-1,-1,withscores=True)
			pipeline0.zrange(voter_dvote_key,-1,-1,withscores=True)
			pipeline0.hget(VOTER_AFFINITY_HASH+voter_and_target,'vt')
		result0, counter, voting_and_calc_times = pipeline0.execute(), 0, []
		# result0 is a list containig [latest_upvote_time1, latest_downvote_time2, voting_affinity_hash3, ...]
		# reorganizing result0 for ease of access
		for voter_and_target in voter_target_list:
			latest_uvote_tup = result0[counter]
			if latest_uvote_tup:
				latest_uvote_time = latest_uvote_tup[0][1] if latest_uvote_tup[0] else 0.0
			else:
				# the tup doesn't exist - this person never upvoted (or their set is truncated)
				latest_uvote_time = 0
			latest_dvote_tup = result0[counter+1]
			if latest_dvote_tup:
				latest_dvote_time = latest_dvote_tup[0][1] if latest_dvote_tup[0] else 0.0
			else:
				# the tup doesn't exist - this person never downvoted (or their set has been truncated)
				latest_dvote_time = 0
			latest_vote_time = max(latest_uvote_time,latest_dvote_time)
			prev_last_vote_time = float(result0[counter+2]) if result0[counter+2] else 0.0
			voting_and_calc_times.append((latest_vote_time, prev_last_vote_time))# this list of tuples is used in the following code (instead of the rather raw result0)
			counter += 3
		
		# for voter_and_target where 'last vote time' is the same as it was in the previous instance (i.e. prev last vote time), do nothing!
		counter, active_voter_target_list, inactive_voter_target_list, last_vote_times = 0, [], [], {}
		for voter_and_target in voter_target_list:
			last_vote_time = voting_and_calc_times[counter][0]
			prev_last_vote_time = voting_and_calc_times[counter][1]
			if last_vote_time != prev_last_vote_time:
				# something has changed since last time this person's VOTER_AFFINITY_HASH was calculated
				active_voter_target_list.append(voter_and_target)
				last_vote_times[voter_and_target] = last_vote_time
			else:
				inactive_voter_target_list.append((voter_and_target,last_vote_time))
			counter += 1
		
		# all those who reverted at least 1 vote (upvote or downvote) in the last 6 hours
		latest_reverted_rels_and_times = my_server.zrange(LATEST_REVERSION_TIMES,0,-1,withscores=True)
		latest_reverted_rels = [reverted_rel for reverted_rel,times in latest_reverted_rels_and_times]

		# scan inactive voters for reverted votes - because it's possible they were active (but in reverting votes, not casting votes!)
		if inactive_voter_target_list:
			
			# all those who reverted a vote, AND also were flagged by uvaf/dvaf
			inactive_voter_targets_with_reversion = [(voter_and_target, last_vote_time) for voter_and_target, last_vote_time \
			in inactive_voter_target_list if voter_and_target in latest_reverted_rels]

			if inactive_voter_targets_with_reversion:
				
				latest_reverted_rels_and_times_dict = dict(latest_reverted_rels_and_times)

				for voter_and_target, last_vote_time in inactive_voter_targets_with_reversion:
					time_of_reversion = latest_reverted_rels_and_times_dict[voter_and_target]
					if time_of_reversion > last_vote_time:
						active_voter_target_list.append(voter_and_target)
						last_vote_times[voter_and_target] = time_of_reversion
			
		# cleansing all reverted-vote-times so that they aren't called up again in the next calculation
		my_server.delete(LATEST_REVERSION_TIMES)

		# deleting all VOTER_AFFINITY_HASHes of vote reverters. If any voting relationships are sturdy enough - they are about to be recaclulated anyway
		if latest_reverted_rels:
			hashes_to_delete, pairs_to_remove = [], []
			for voter_and_target in latest_reverted_rels:
				pairs_to_remove.append(voter_and_target)
				hashes_to_delete.append(VOTER_AFFINITY_HASH+voter_and_target)
			my_server.execute_command('UNLINK', *hashes_to_delete)# using 'UNLINK' (non-blocking) instead of 'DELETE' (blocking)
			my_server.zrem(VOTING_RELATIONSHIP_LOG,*pairs_to_remove)
			my_server.zrem(VOTING_RELATIONSHIP_LOG_TRUNCATOR,*pairs_to_remove)

		###########################################

		if active_voter_target_list:
			pipeline1 = my_server.pipeline()
			for voter_and_target in active_voter_target_list:
				voter_id = voter_and_target.split(":")[0]
				pipeline1.zcard(VOTER_UVOTES_AND_TIMES+voter_id)
				pipeline1.zcard(VOTER_DVOTES_AND_TIMES+voter_id)
			result1, counter, rels_of_interest = pipeline1.execute(), 0, {}
			for voter_and_target in active_voter_target_list:
				if result1[counter]+result1[counter+1] >= MEANINGFUL_VOTING_SAMPLE_SIZE:
					rels_of_interest[voter_and_target] = {'tuv':result1[counter],'tdv':result1[counter+1]}
				counter += 2
			pipeline2, rels_to_process = my_server.pipeline(), {}
			if rels_of_interest:
				rels_of_interest_list = rels_of_interest.keys()
				for voter_and_target in rels_of_interest_list:
					pipeline2.zcard(ALL_UVOTES_TO_TGT_USER+voter_and_target)
					pipeline2.zcard(ALL_DVOTES_TO_TGT_USER+voter_and_target)
				result2, counter = pipeline2.execute(), 0
				for voter_and_target in rels_of_interest_list:
					if result2[counter]+result2[counter+1] >= NUM_VOTES_TO_TGT:
						rels_to_process[voter_and_target] = {'uv':result2[counter], 'dv':result2[counter+1], 'tuv':rels_of_interest[voter_and_target]['tuv'],\
						'tdv':rels_of_interest[voter_and_target]['tdv']}
					counter += 2
			
			return rels_to_process, last_vote_times
		else:
			return {}, {}
	else:
		return {}, {}


def study_voting_preferences():
	"""
	Calculates the Bayesian probability of a voter being a sybil of a target user (or a 'hater')

	Uses the UVOTER_AFFINITY/DVOTER_AFFINITY ("uvaf/dvaf") sorted sets to target which users the following needs to be calculated for:

	Benchmarks:
	- Exempt all those who have cast less than 5 votes to tgt (and don't have 'prior' affinity towards the target)
	- Exempt all those who have cast less than 10 votes overall (and don't have 'prior' affinity towards the target)
	- If 'prior' affinity exists, update it upon recalculation. But only recalculate if the data has changed from last time, otherwise not
	- If affinity >= 50%, tag it as a 'probable' sybil
	- If affinity >= 30%, tag it as a 'suspected' sybil
	"""
	my_server = redis.Redis(connection_pool=POOL)
	# step 1: isolate voting 'relationships' (i.e. voter_id:target_id pairs) to assess, according to how much score has accrued to the target user (by a specific voter)
	uvote_rels_to_study = my_server.zrangebyscore(UVOTER_AFFINITY,UPPER_RELATIONSHIP_UVOTE_CUTOFF,'+inf')# 5 to '+inf'
	dvote_rels_to_study = my_server.zrangebyscore(DVOTER_AFFINITY,UPPER_RELATIONSHIP_DVOTE_CUTOFF,'+inf')# 5 to '+inf'
	
	# step 2: retrieve all metrics required to compute Bayesian affinities for each voter:target_user pair isolated in step 1
	uvote_pair_data, last_uvote_pair_update_times = retrieve_voter_target_action_count(voter_target_list=uvote_rels_to_study, vote_type='uvote', \
	my_server=my_server)# returns a dict of dict where voter:target_user is the 'key'
	dvote_pair_data, last_dvote_pair_update_times = retrieve_voter_target_action_count(voter_target_list=dvote_rels_to_study, vote_type='dvote', \
	my_server=my_server)# returns a dict of dict where voter:target_user is the 'key'
	
	# step 3: calculate_bayesian_affinity for each qualifying voter:target_user relationship
	uvote_rels_affinities = calculate_bayesian_affinity(suspected_affinity='upvote', voter_and_target_data=uvote_pair_data) if uvote_pair_data else []
	dvote_rels_affinities = calculate_bayesian_affinity(suspected_affinity='downvote', voter_and_target_data=dvote_pair_data) if dvote_pair_data else []

	# step 4: save the affinities in redis, and set expiry to THREE_MONTHS
	pipeline1, voting_relationship_logger = my_server.pipeline(), []
	if uvote_rels_affinities:
		for voter_target_pair, bayes_prob, json_vote_metrics in uvote_rels_affinities:
			key_name, last_vote_time = VOTER_AFFINITY_HASH+voter_target_pair, last_uvote_pair_update_times[voter_target_pair]
			if bayes_prob >= BAYESIAN_PROB_THRESHOLD_FOR_VOTE_NERFING:
				voting_relationship_logger.append((voter_target_pair, bayes_prob))
			pipeline1.hmset(key_name,{'p1':bayes_prob,'vt':last_vote_time,'blob':json_vote_metrics})#'vt' and 'blob' are common, but p1 and p0 are saved separately
			pipeline1.expire(key_name,THREE_MONTHS)
	if dvote_rels_affinities:
		for voter_target_pair, bayes_prob, json_vote_metrics in dvote_rels_affinities:
			key_name, last_vote_time = VOTER_AFFINITY_HASH+voter_target_pair, last_dvote_pair_update_times[voter_target_pair]
			if bayes_prob >= BAYESIAN_PROB_THRESHOLD_FOR_VOTE_NERFING:
				voting_relationship_logger.append((voter_target_pair, bayes_prob))
			pipeline1.hmset(key_name,{'p0':bayes_prob,'vt':last_vote_time,'blob':json_vote_metrics})
			pipeline1.expire(key_name,THREE_MONTHS)

	# step 5: log sybils against target users (for ease of look up)
	if voting_relationship_logger:
		for voter_target_pair, bayes_prob in voting_relationship_logger:
			target_user_id = voter_target_pair.split(":")[1]
			pipeline1.zadd(VOTING_RELATIONSHIP_LOG,voter_target_pair,target_user_id)
			pipeline1.zadd(VOTING_RELATIONSHIP_LOG_TRUNCATOR,voter_target_pair,time.time())

	pipeline1.execute()


################################## Processing user vote ##################################


def add_user_vote(voter_id, target_user_id, target_obj_id, obj_type, voting_time, is_reversion,	my_server=None):
	"""
	Saves user's voting history

	The history is used for:
	i) Displaying voting deeds to the users
	ii) Calculating a Bayesian affinity to discount voting (in case of 'sybil', or 'hater' behavior)
	"""
	voter_id, target_obj_id, target_user_id = str(voter_id), str(target_obj_id), str(target_user_id)
	voter_target_id = voter_id+":"+target_user_id
	voter_target_key = ALL_UVOTES_TO_TGT_USER+voter_target_id
	voter_vote_key = VOTER_UVOTES_AND_TIMES+voter_id
	obj_hash_name = obj_type+":"+target_obj_id
	payload = voter_target_id+":1:"+obj_hash_name
	my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
	if is_reversion:
		# handling 'like' reversion
		amnt = -1
		my_server.zrem(voter_target_key, obj_hash_name)
		my_server.zrem(voter_vote_key, payload)
		my_server.zrem(GLOBAL_VOTES_AND_TIMES, payload)
		###########################################################
		# log the reversion separately too
		my_server.zadd(LATEST_REVERSION_TIMES,voter_target_id,voting_time)
		###########################################################
	else:
		# handling 'likes'
		amnt = 1
		my_server.zadd(GLOBAL_VOTES_AND_TIMES, payload, voting_time)# for trimming
		my_server.zadd(voter_vote_key, payload, voting_time)# for display to voter
		my_server.zadd(voter_target_key, obj_hash_name, voting_time)# for Bayesian calculation
		###########################################################
	new_score = my_server.zincrby(UVOTER_AFFINITY, voter_target_id, amount=amnt)# 'UVOTER_AFFINITY' separates out relationships where lots of likes have been given
	if int(new_score) == 1:
		# only update the time when the voting relationship is first created 
		my_server.zadd(UVOTER_AFFINITY_TRUNCATOR, voter_target_id, voting_time)
	elif int(new_score) == 0:
		# the voting relationship has ended, so just remove it from the truncator and affinity sorted sets
		my_server.zrem(UVOTER_AFFINITY_TRUNCATOR, voter_target_id)
		my_server.zrem(UVOTER_AFFINITY, voter_target_id)
	


def determine_vote_score(voter_id, target_user_id, world_age_discount, is_editorial_vote, is_pht, my_server):
	"""
	Determines if a vote is by a sybil, an inexperienced voter, or a non-partisan voter, alloting a value to the vote accordingly
	"""
	my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
	is_sybil = False
	if is_editorial_vote:
		# is an editorial voter
		bayes_prob = my_server.hget(VOTER_AFFINITY_HASH+voter_id+":"+target_user_id,'p1')# the current probability of upvoting that exists between this pair

		if bayes_prob and float(bayes_prob) >= BAYESIAN_PROB_THRESHOLD_FOR_VOTE_NERFING:#0.3
			# voter is a direct sybil of target
			handpicked_prob = None# a sybil locks the content, and can never get it into trending, hence this prob is 0 (we use 'None' for programmatic reasons)
			is_sybil = True
		else:
			num_general_sybils = my_server.zcount(SYBIL_RELATIONSHIP_LOG,voter_id, voter_id)

			if num_general_sybils > 0:
				# voter is generally a sybil-tainted user
				handpicked_prob = None# a sybil locks the content, and can never get it into trending, hence this prob is 0 (we use 'None' for programmatic reasons)
				is_sybil = True#a generic sybil in this case
			else:
				if world_age_discount < 1.0:#'world_age_discount' floats between 0 and 1.0
					# voter is not experienced enough
					handpicked_prob = 0# an inexperienced voter can't contribute to getting an obj into trending
				else:

					# it's a vote on a photo obj
					if is_pht == '1':
						if my_server.zcount(GLOBAL_EDITORIAL_LIKES_ON_IMGS, voter_id, voter_id) < (MEANINGFUL_VOTING_SAMPLE_SIZE+1):
							# voter has not editorially voted in the required volume
							handpicked_prob = 0# an inexperienced voter can't contribute to getting an obj into trending
						else:
							# voter is an experienced, non_partisan voter, get their 'handpicked_prob' (or 'like_prob' alternatively)
							handpicked_prob = my_server.zscore(VOTER_HANDPICKED_PROBS,voter_id)
							if handpicked_prob is None:
								handpicked_prob = 0
							elif handpicked_prob > 0:
								num_editorial_votes = my_server.zscore(NUM_EDITORIAL_LIKES,voter_id)
								if num_editorial_votes and num_editorial_votes < 10:
									# nerf said 'handpicked_prob' since it's based on too small a sample size
									if num_editorial_votes == 1:
										# nerfed the most
										handpicked_prob = 0.1 * handpicked_prob
									elif num_editorial_votes == 2:
										handpicked_prob = 0.15 * handpicked_prob
									elif num_editorial_votes == 3:
										handpicked_prob = 0.25 * handpicked_prob
									elif num_editorial_votes == 4:
										handpicked_prob = 0.35 * handpicked_prob
									elif num_editorial_votes == 5:
										handpicked_prob = 0.45 * handpicked_prob
									elif num_editorial_votes == 6:
										handpicked_prob = 0.55 * handpicked_prob
									elif num_editorial_votes == 7:
										handpicked_prob = 0.65 * handpicked_prob
									elif num_editorial_votes == 8:
										handpicked_prob = 0.75 * handpicked_prob
									elif num_editorial_votes == 9:
										# nerfed the least
										handpicked_prob = 0.85 * handpicked_prob
									else:
										# should never happen
										handpicked_prob = 0.95 * handpicked_prob
						return handpicked_prob, is_sybil
					
					#########################################################################
					# EXPERIMENTAL
					# it's a text vote - use the voter's handpicking rep for imgs to impart content reply to text posters (this is experimental)
					else:
						num_editorial_votes = my_server.zscore(NUM_EDITORIAL_LIKES,voter_id)
						
						if num_editorial_votes >= 6:# why 6? Chosen arbitrarily after some CSV analysis
							handpicked_prob = my_server.zscore(VOTER_HANDPICKED_PROBS,voter_id)
							
							if handpicked_prob < 0.28:# why 28%?Chosen arbitrarily after some CSV analysis
								# this is not a 'high rep' voter, so handpicked_prob is 0
								handpicked_prob = 0
						
						# this is not a 'high rep' voter, so handpicked_prob is 0
						else:
							handpicked_prob = 0

		return handpicked_prob, is_sybil
	######################################################################################################
	else:
		# is an audience voter
		bayes_prob = my_server.hget(VOTER_AFFINITY_HASH+voter_id+":"+target_user_id,'p1')# the current probability of upvoting that exists between this pair
		if bayes_prob and float(bayes_prob) >= BAYESIAN_PROB_THRESHOLD_FOR_VOTE_NERFING:
			# voter is a direct sybil of target
			is_vote_counted = False
			is_sybil = True
		else:
			num_general_sybils = my_server.zcount(SYBIL_RELATIONSHIP_LOG,voter_id, voter_id)
			if num_general_sybils > 0:
				# voter is generally a sybil-tainted user
				is_vote_counted = False
				is_sybil = True
			else:
				if world_age_discount < 1.0:#'world_age_discount' floats between 0 and 1.0
					# voter is not experienced enough
					is_vote_counted = False
				elif my_server.zcard(VOTER_UVOTES_AND_TIMES+voter_id) < MEANINGFUL_VOTING_SAMPLE_SIZE:
					# voter has not voted in the required volumes
					is_vote_counted = False
				else:
					# voter is an experienced, non_partisan voter
					is_vote_counted = True
		return is_vote_counted, is_sybil


def log_like(obj_id, own_id, revert_prev, is_pht, target_user_id, time_of_vote, is_editorial_vote, world_age_discount=None):
	"""
	Logs the 'like' given a voter on an obj

	The 'like' is logged in a variety of ways:
	(i) as a 'visual' +1 to show the object owner
	(ii) as a marker that disallows users to 'like' the same obj again (in 'vote_store')
	(iii) as a +1 in 'net_votes' saved in postgresql
	(iv) as a metric used in Bayesian calc to catch Sybil voters
	(v) as a metric used to calculate 'handpicked_prob' (i.e. prob that voted-on content will be handpicked by super defenders)
	(vi) as a metric used to calculate 'like_prob' (i.e. prob that content that enters trending will receive 'likes' from the audience)
	"""
	obj_id, own_id = str(obj_id), str(own_id)
	if is_pht == '1':
		hash_name  = "img:"+obj_id
		rate_limit_key = 'rlpv:'+own_id
		vote_store = VOTE_ON_IMG+obj_id
		obj_type = 'img'
	else:
		hash_name = "tx:"+obj_id
		rate_limit_key = 'rlv:'+own_id
		vote_store = VOTE_ON_TXT+obj_id
		obj_type = 'tx'
	my_server = redis.Redis(connection_pool=POOL)

	if my_server.exists(rate_limit_key):
		# rate limited from completing action
		return -1
	else:
		#retrieve json obj data; voting is still open/ongoing if this data exists (otherwise consider it closed)
		json_obj_data = my_server.hget(hash_name,'blob')
		if json_obj_data: 
			if is_editorial_vote:
				
				# is an editorial vote (from an uncurated list, e.g. fresh)
				if revert_prev:
					# Reverting a previously cast like

					###############################################
					
					# Step 1) Revert from the content's object hash
					pipeline1 = my_server.pipeline()
					pipeline1.hincrby(hash_name,'nv',amount=-1)#atomic
					pipeline1.hincrby(hash_name,'uv',amount=-1)#atomic
					pipeline1.zrem(vote_store,own_id)#atomic
					if is_pht == '1':
						pipeline1.srem(LOCKED_IMG+hash_name,own_id)
					else:
						pipeline1.srem(LOCKED_TXT+hash_name,own_id)
					new_net_votes = pipeline1.execute()[0]

					###############################################	

					# Step 2) Revert relevent postgresql fields 
					# if is_pht == '1':
					# 	Link.objects.filter(id=obj_id).update(net_score=F('net_votes')-1)#atomic
					# else:
					Link.objects.filter(id=obj_id).update(net_votes=F('net_votes')-1)#atomic

					###############################################

					# Step 3) Revert Bayesian logging of the 'like' for unearthing sybils
					add_user_vote(voter_id=own_id, target_user_id=target_user_id, target_obj_id=obj_id, obj_type=obj_type, \
						voting_time=time_of_vote, is_reversion=True, my_server=my_server)

					###############################################	

					# Only do this for 'public' objs:
					if json.loads(json_obj_data).get('aud','') == 'p':
						
						# Step 4) Revert logging for 'handpicked_prob' and 'like_prob'
						if is_pht == '1':
							# if img vote
							my_server.zrem(GLOBAL_IMG_LIKES, hash_name+"-"+own_id+"-1")

						# else:
						# 	# if text vote
						# 	key_name = hash_name+":"+str(target_user_id)
						# 	score = my_server.zscore(GLOBAL_HIGH_REP_HANDPICKED_TXT_OBJS, key_name)
						# 	if score > 0:
						# 		my_server.zincrby(GLOBAL_HIGH_REP_HANDPICKED_TXT_OBJS,hash_name+":"+str(target_user_id), amount=-1)

					return new_net_votes

				else:
					# processing an editorial 'like'

					###############################################

					# Step 1) Determine 'handpicked_prob', i.e. the prob this item could be picked by a super defender, given it was 'liked' by own_id!
					handpicked_prob, is_sybil = determine_vote_score(is_editorial_vote=True, voter_id=own_id, target_user_id=target_user_id, \
						my_server=my_server, world_age_discount=world_age_discount, is_pht=is_pht)

					###############################################

					# Step 2) Record the 'handpicked_prob' in vote_store, and the act of liking in 'nv' and 'uv'
					pipeline1 = my_server.pipeline()
					pipeline1.hincrby(hash_name,'nv',amount=1)#atomic
					pipeline1.hincrby(hash_name,'uv',amount=1)#atomic
					pipeline1.zadd(vote_store,own_id, 0 if handpicked_prob is None else handpicked_prob)#atomic
					if is_sybil:
						if is_pht == '1':
							pipeline1.sadd(LOCKED_IMG+hash_name,own_id)
							pipeline1.expire(LOCKED_IMG+hash_name,ONE_MONTH)
						else:
							pipeline1.sadd(LOCKED_TXT+hash_name,own_id)
							pipeline1.expire(LOCKED_TXT+hash_name,ONE_MONTH)
					new_net_votes = pipeline1.execute()[0]

					###############################################	

					# Step 3) Update postgresql fields 
					if is_pht == '1':
						# Photo.objects.filter(id=obj_id).update(vote_score=F('vote_score')+1)#atomic
						vote_count_key = 'fpv:'+own_id
					else:
						# Link.objects.filter(id=obj_id).update(net_votes=F('net_votes')+1)#atomic
						vote_count_key = 'fv:'+own_id
					Link.objects.filter(id=obj_id).update(net_votes=F('net_votes')+1)#atomic

					###############################################

					# Step 4) setting rate limits for those liking "too fast" (i.e. 3 times within 10 secs)
					is_set = my_server.setnx(vote_count_key,1)
					if is_set:
						# key didn't hitherto exist, now set its ttl
						my_server.expire(vote_count_key,10)
					else:
						# key already exists'
						new_value = my_server.incr(vote_count_key)
						if new_value > 2:
							# this person has liked 3 times in 10 seconds, rate limit them for 9 seconds
							my_server.setex(rate_limit_key,'1',NINE_SECS)
							my_server.execute_command('UNLINK', vote_count_key)

					###############################################

					# Step 5) log like for Bayesian filter that unearths 'sybils'
					add_user_vote(voter_id=own_id, target_user_id=target_user_id, target_obj_id=obj_id, obj_type=obj_type, \
						voting_time=time_of_vote, is_reversion=False, my_server=my_server)

					###############################################

					# Only do this for 'public' objs:
					if json.loads(json_obj_data).get('aud','') == 'p':

						# Step 6) log like in a global set, for 'like_prob' and 'handpicked_prob' calculation later
						# if handpicked_prob is not None (i.e. the voter is not a specific or a general sybil)
						if handpicked_prob is not None and is_pht == '1':
							# only if img vote (for now)
							my_server.zadd(GLOBAL_IMG_LIKES, hash_name+"-"+own_id+"-1", time_of_vote)# '1' at the end signifies editorial vote

						# EXPERIMENTAL - using img 'handpicked' voting rep to impart content rep to text posters!
						# elif handpicked_prob >= 0.28 and is_pht != '1':
						# 	# text vote
						# 	my_server.zincrby(GLOBAL_HIGH_REP_HANDPICKED_TXT_OBJS,hash_name+":"+str(target_user_id), amount=1)#, time_of_vote)

					return new_net_votes
			#############################################################################################################################
			# is an audience vote (from a curated list, e.g. best, or my-home, etc)
			else:
				
				if revert_prev:
					# reverting a previously cast audience 'like'

					###############################################
					
					# Step 1) Revert from the content's object hash
					pipeline1 = my_server.pipeline()
					pipeline1.hincrby(hash_name,'nv',amount=-1)#atomic
					pipeline1.hincrby(hash_name,'uv',amount=-1)#atomic
					pipeline1.zrem(vote_store,own_id)#atomic
					new_net_votes = pipeline1.execute()[0]

					###############################################	

					# Step 2) Revert relevent postgresql fields 
					# if is_pht == '1':
					# 	Photo.objects.filter(id=obj_id).update(vote_score=F('vote_score')-1)#atomic
					# else:
					Link.objects.filter(id=obj_id).update(net_votes=F('net_votes')-1)#atomic

					###############################################

					# Step 3) Revert Bayesian logging of the 'like' for unearthing sybils
					add_user_vote(voter_id=own_id, target_user_id=target_user_id, target_obj_id=obj_id, obj_type=obj_type, \
						voting_time=time_of_vote, is_reversion=True, my_server=my_server)

					###############################################		
					
					# Only do this for 'public' objs:
					# if json.loads(json_obj_data)['aud'] == 'p':
					if json.loads(json_obj_data).get('aud','') == 'p':

						# Step 4) Revert logging for 'handpicked_prob','like_prob'
						if is_pht == '1':
							# only if img vote (for now)
							removed = my_server.zrem(GLOBAL_IMG_LIKES, hash_name+"-"+own_id+"-0")
							#################################################################
							if removed:
								my_server.zincrby(GLOBAL_AUD_LIKED_IMG_OBJS,hash_name+":"+str(target_user_id), amount=-1)

					return new_net_votes
				else:
					# processing an audience 'like'

					###############################################

					# Step 1) check if this vote is to be counted or ignored
					is_vote_counted, is_sybil = determine_vote_score(is_editorial_vote=False, voter_id=own_id, target_user_id=target_user_id, \
						my_server=my_server, world_age_discount=world_age_discount, is_pht=is_pht)

					###############################################

					# Step 2) Record the audience vote
					pipeline1 = my_server.pipeline()
					pipeline1.hincrby(hash_name,'nv',amount=1)#atomic
					pipeline1.hincrby(hash_name,'uv',amount=1)#atomic
					pipeline1.zadd(vote_store,own_id,0)#atomic
					new_net_votes = pipeline1.execute()[0]
					
					###############################################	

					# Step 3) Update postgresql fields 
					vote_count_key = 'fpv:'+own_id if is_pht == '1' else 'fv:'+own_id
					Link.objects.filter(id=obj_id).update(net_votes=F('net_votes')+1)#atomic

					###############################################

					# Step 4) setting rate limits for those liking "too fast" (i.e. 3 times within 10 secs)
					is_set = my_server.setnx(vote_count_key,1)
					if is_set:
						# key didn't hitherto exist, now set its ttl
						my_server.expire(vote_count_key,10)
					else:
						# key already exists'
						new_value = my_server.incr(vote_count_key)
						if new_value > 2:
							# this person has liked 3 times in 10 seconds, rate limit them for 9 seconds
							my_server.setex(rate_limit_key,'1',NINE_SECS)
							my_server.execute_command('UNLINK', vote_count_key)

					###############################################

					# Step 5) log like for Bayesian filter that unearths 'sybils'
					add_user_vote(voter_id=own_id, target_user_id=target_user_id, target_obj_id=obj_id, obj_type=obj_type, \
						voting_time=time_of_vote, is_reversion=False, my_server=my_server)

					###############################################

					# Only do this for 'public' objs:
					# if json.loads(json_obj_data)['aud'] == 'p':
					if json.loads(json_obj_data).get('aud','') == 'p':

						# Step 6) log like in a global set for 'like_prob', 'handpicked_prob' calculation later
						if is_vote_counted and is_pht == '1':
							# only if img vote (for now)
							my_server.zadd(GLOBAL_IMG_LIKES, hash_name+"-"+own_id+"-0", time_of_vote)# '0' at the end signifies audience vote
							#####################################
							# helpful in calculating 'content upload rep' for the image uploader
							my_server.zincrby(GLOBAL_AUD_LIKED_IMG_OBJS,hash_name+":"+str(target_user_id), amount=1)#, time_of_vote)

					return new_net_votes
		else:
			# voting is closed
			return -1


def archive_closed_objs_and_votes():
	"""
	Scheduled task that organizes and processes voting data of objs (where voting was closed) to rep for voters

	Executed every 7 hours
	"""
	my_server = redis.Redis(connection_pool=POOL)

	############### Processing for images only ###############

	# Step 1) Isolate all votes recently cast
	all_votes_cast_and_times = my_server.zrange(GLOBAL_IMG_LIKES,0,-1, withscores=True)

	# Step 2) Extract hash_names from all_votes, and populate a dictionary with all these hash_names
	all_hash_names = {}
	for vote, vote_time in all_votes_cast_and_times:
		all_hash_names[vote.partition("-")[0]] = ''# populating the dictionary with all hash_names that got voted on

	# Step 3) Distinguish between objs where voting was closed ('0') and those where voting is still open ('1')
	pipeline1 = my_server.pipeline()
	list_of_hashes = all_hash_names.keys()
	for hash_name in list_of_hashes:
		pipeline1.exists(hash_name)
	result1, counter, closed_objs = pipeline1.execute(), 0, []
	for hash_name in list_of_hashes:
		if result1[counter]:
			all_hash_names[hash_name] = '1'#voting open
		else:
			closed_objs.append(hash_name)
			all_hash_names[hash_name] = '0'#voting closed
		counter += 1

	# Step 4) enrich data with 'handpicked','trended' and 'locked' flags (where voting is closed)
	if closed_objs:
		keys_to_delete = []
		pipeline2 = my_server.pipeline()
		for hash_name in closed_objs:
			pipeline2.exists(HANDPICKED_TRENDING_IMG+hash_name)
			pipeline2.exists(NONHANDPICKED_TRENDING_IMG+hash_name)
			pipeline2.exists(LOCKED_IMG+hash_name)
		result2, counter = pipeline2.execute(), 0

		for hash_name in closed_objs:
			trended_via_handpicking_and_not_locked, trended_via_regular_votes, locked = result2[counter], result2[counter+1], result2[counter+2]
			if trended_via_handpicking_and_not_locked:
				# it entered trending via handpicking, concatenate '2' to it as a marker
				all_hash_names[hash_name] += '2'
				keys_to_delete.append(HANDPICKED_TRENDING_IMG+hash_name)
			elif trended_via_regular_votes:
				# it entered trending via regular votes (not handpicking), concatenate '1' to it as a marker
				all_hash_names[hash_name] += '1'
				keys_to_delete.append(NONHANDPICKED_TRENDING_IMG+hash_name)
			elif locked:
				# it was locked, concatenate '0' to it as a marker
				all_hash_names[hash_name] += '0'
				keys_to_delete.append(LOCKED_IMG+hash_name)
			counter += 3
		if keys_to_delete:
			my_server.execute_command('UNLINK', *keys_to_delete)

	# Step 5) move closed obj/vote data to GLOBAL_CLOSED_IMG_LIKES and GLOBAL_CLOSED_IMG_OBJ_HASH_NAMES, removing this data from GLOBAL_IMG_LIKES
	votes_to_add, objs_to_add, rows_to_remove = [], [], []
	time_now = time.time()
	for vote, vote_time in all_votes_cast_and_times:
		obj_hash = vote.partition("-")[0]# i.e. the hash_name, like img:12312
		obj_state = all_hash_names[obj_hash]
		"""
		obj_state:
		'1' implies voting is ongoing - ignore this obj
		'0' implies closed and obj never trended
		'01' implies it's closed and has trended via regular votes (not handpicking)
		'02' implies it's closed and has trended via handpicking
		'00' implies it's closed and was locked from trending
		"""
		if obj_state in ('0','01','02','00'):
			rows_to_remove.append(vote)
			if obj_state != '00':
				# ignore '00' state - it implies objs that are locked from trending (so could never have achieved handpicked success/audience likes - skewing our calcs)
				vote_with_final_state = vote+"-"+obj_state
				votes_to_add.append(vote_with_final_state)
				votes_to_add.append(vote_time)
				objs_to_add.append(obj_hash)
				objs_to_add.append(time_now)
	
	if rows_to_remove:
		my_server.zrem(GLOBAL_IMG_LIKES,*rows_to_remove)# removing closed votes from GLOBAL_IMG_LIKES - they've been processed
	if objs_to_add:
		my_server.zadd(GLOBAL_CLOSED_IMG_LIKES,*votes_to_add)# adding votes to GLOBAL_CLOSED_IMG_LIKES
		my_server.zadd(GLOBAL_CLOSED_IMG_OBJ_HASH_NAMES,*objs_to_add)# adding objs to GLOBAL_CLOSED_IMG_OBJ_HASH_NAMES - useful for cleanup 28 days later
		############################################################
		process_global_closed_objs_and_votes(my_server=my_server)# calcs voters' rep
		expire_outdated_closed_objs_and_votes(my_server=my_server)
		############################################################
		uploader_data = process_closed_imgs_uploaders_rep(my_server=my_server)# calcs uploaders' reps: (i) via audience likes, (ii) via handpicking
		expire_outdated_img_uploaders_rep(uploader_data, my_server=my_server)
		############################################################
		submitter_data = process_txt_submitters_rep(my_server=my_server)
		expire_outdated_txt_submitters_rep(submitter_data, my_server=my_server)


def process_txt_submitters_rep(my_server=None):
	"""
	Calculating txt submitter rep
	"""
	my_server = my_server if  my_server else redis.Redis(connection_pool=POOL)
	submitter_ids_and_txt_counts = my_server.zrange(GLOBAL_SUBMITTED_TXT_VOLUME,0,-1,withscores=True)
	txt_submitter_pairs_and_likes = my_server.zrange(GLOBAL_HIGH_REP_HANDPICKED_TXT_OBJS,0,-1,withscores=True)

	submitter_ids_and_likes = defaultdict(int)
	scanned_pairs = defaultdict(list)# useful for deletion later

	for txt_submitter_pair, num_likes in txt_submitter_pairs_and_likes:
		data = txt_submitter_pair.rpartition(":")
		txt_hash_name, submitter_id = data[0], data[-1]
		scanned_pairs[submitter_id].append(txt_submitter_pair)
		if num_likes > 0:
			submitter_ids_and_likes[submitter_id] += 1# +1 given if a post has been liked, regardless of how many likes were received

	txt_submitter_high_rep_handpicked_based_content_rep = []
	for submitter_id, txt_count in submitter_ids_and_txt_counts:

		num_likes = submitter_ids_and_likes[submitter_id]
		aud_likes_based_content_rep = (num_likes*1.0)/txt_count

		txt_submitter_high_rep_handpicked_based_content_rep.append(submitter_id)
		txt_submitter_high_rep_handpicked_based_content_rep.append(aud_likes_based_content_rep)

	if txt_submitter_high_rep_handpicked_based_content_rep:
		my_server.delete(GLOBAL_TXT_SUBMITTER_HIGH_REP_HANDPICKER_BASED_REP)
		my_server.zadd(GLOBAL_TXT_SUBMITTER_HIGH_REP_HANDPICKER_BASED_REP,*txt_submitter_high_rep_handpicked_based_content_rep)

	return scanned_pairs


def process_closed_imgs_uploaders_rep(my_server=None):
	"""
	Calculating img uploader rep

	The calc is quite simply this: content_rep_of_user = num_aud_liked_imgs/num_uploaded_imgs
	Reputations are reset to 0 if someone hasn't uploaded an img in over a month
	"""
	my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
	uploader_ids_and_img_counts = my_server.zrange(GLOBAL_UPLOADED_IMG_VOLUME,0,-1,withscores=True)
	
	obj_uploader_pairs_and_likes = my_server.zrange(GLOBAL_AUD_LIKED_IMG_OBJS,0,-1,withscores=True)
	
	uploader_ids_and_likes = defaultdict(int)
	scanned_pairs = defaultdict(list)# useful for deletion later
	for obj_uploader_pair, num_likes in obj_uploader_pairs_and_likes:
		data = obj_uploader_pair.rpartition(":")
		obj_hash_name, uploader_id = data[0], data[-1]
		scanned_pairs[uploader_id].append(obj_uploader_pair)
		if num_likes > 0:
			uploader_ids_and_likes[uploader_id] += 1# +1 given if a post has been liked, regardless of how many likes were received

	img_uploader_aud_likes_based_content_rep, img_uploader_handpicked_based_content_rep = [], []
	for uploader_id, img_count in uploader_ids_and_img_counts:

		num_likes = uploader_ids_and_likes[uploader_id]
		aud_likes_based_content_rep = (num_likes*1.0)/img_count

		num_handpicked = my_server.zcount(GLOBAL_HANDPICKED_IMG_DATA,uploader_id,uploader_id)#TODO: include in a pipeline
		handpicked_based_content_rep = (num_handpicked*1.0)/img_count

		img_uploader_aud_likes_based_content_rep.append(uploader_id)
		img_uploader_aud_likes_based_content_rep.append(aud_likes_based_content_rep)

		img_uploader_handpicked_based_content_rep.append(uploader_id)
		img_uploader_handpicked_based_content_rep.append(handpicked_based_content_rep)

	if img_uploader_aud_likes_based_content_rep:
		my_server.delete(GLOBAL_IMG_UPLOADER_AUD_LIKE_BASED_REP)
		my_server.zadd(GLOBAL_IMG_UPLOADER_AUD_LIKE_BASED_REP,*img_uploader_aud_likes_based_content_rep)

	if img_uploader_handpicked_based_content_rep:
		my_server.delete(GLOBAL_IMG_UPLOADER_HANDPICKING_BASED_REP)
		my_server.zadd(GLOBAL_IMG_UPLOADER_HANDPICKING_BASED_REP,*img_uploader_handpicked_based_content_rep)

	return scanned_pairs


def expire_outdated_txt_submitters_rep(submitter_data, my_server=None):
	"""
	If a user has not submitted a text post for over a month, reset their txt content reps to 0
	"""
	if submitter_data:
		my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
		txt_submitter_ids = my_server.zrange(GLOBAL_SUBMITTED_TXT_VOLUME,0,-1)

		pipeline1 = my_server.pipeline()
		for submitter_id in txt_submitter_ids:
			pipeline1.exists(MOST_RECENT_TEXT_SUBMISSION_TIME+submitter_id)
		result1, counter = pipeline1.execute(), 0

		reset_reputation = []
		for submitter_id in txt_submitter_ids:
			if not result1[counter]:
				# has not submitted a text post in the last 1 month - reset content reputation to 0
				reset_reputation.append(submitter_id)
			counter += 1

		if reset_reputation:
			pipeline2 = my_server.pipeline()
			pipeline2.zrem(GLOBAL_SUBMITTED_TXT_VOLUME,*reset_reputation)# removing churned uploaders
			pipeline2.zrem(GLOBAL_TXT_SUBMITTER_HIGH_REP_HANDPICKER_BASED_REP,*reset_reputation)
			pipeline2.execute()

		to_delete, set_of_expendibles = [], set(reset_reputation)
		for submitter_id, txt_submitter_pair_list in submitter_data.iteritems():
			if submitter_id in set_of_expendibles:
				to_delete += txt_submitter_pair_list

		if to_delete:
			my_server.zrem(GLOBAL_HIGH_REP_HANDPICKED_TXT_OBJS,*to_delete)


def expire_outdated_img_uploaders_rep(uploader_data, my_server=None):
	"""
	If a user has not uploaded an img for over a month, reset their img content reps to 0
	"""
	if uploader_data:
		my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
		img_uploader_ids = my_server.zrange(GLOBAL_UPLOADED_IMG_VOLUME,0,-1)

		pipeline1 = my_server.pipeline()
		for uploader_id in img_uploader_ids:
			pipeline1.exists(MOST_RECENT_IMG_UPLOAD_TIME+uploader_id)
		result1, counter = pipeline1.execute(), 0

		reset_reputation = []
		for uploader_id in img_uploader_ids:
			if not result1[counter]:
				# has not uploaded an image in the last 1 month - reset content reputation to 0
				reset_reputation.append(uploader_id)
			counter += 1

		if reset_reputation:
			pipeline2 = my_server.pipeline()
			pipeline2.zrem(GLOBAL_UPLOADED_IMG_VOLUME,*reset_reputation)# removing churned uploaders
			pipeline2.zrem(GLOBAL_IMG_UPLOADER_AUD_LIKE_BASED_REP,*reset_reputation)
			pipeline2.zrem(GLOBAL_IMG_UPLOADER_HANDPICKING_BASED_REP,*reset_reputation)
			pipeline2.execute()

		to_delete, set_of_expendibles = [], set(reset_reputation)
		for uploader_id, obj_uploader_pair_list in uploader_data.iteritems():
			if uploader_id in set_of_expendibles:
				to_delete += obj_uploader_pair_list

		if to_delete:
			my_server.zrem(GLOBAL_AUD_LIKED_IMG_OBJS,*to_delete)


def expire_outdated_closed_objs_and_votes(my_server=None):
	"""
	Deletes extra voting data (i.e. archived data that is now outdated)

	Must be scheduled to run right after archive_closed_objs_and_votes()
	"""
	my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
	twenty_eight_days_ago = time.time() - VOTING_CLOSED_ARCHIVE_OVERFLOW_TIME
	excess_objs = my_server.zrangebyscore(GLOBAL_CLOSED_IMG_OBJ_HASH_NAMES,'-inf',twenty_eight_days_ago)
	if excess_objs:
		# trim the excess
		
		# Step 1) remove from AUDIENCE_LIKED_IMG_HASH_NAMES and HANDPICKED_IMG_HASH_NAMES
		my_server.srem(AUDIENCE_LIKED_IMG_HASH_NAMES,*excess_objs)
		my_server.srem(HANDPICKED_IMG_HASH_NAMES,*excess_objs)

		# Step 2) cleanse defunct rows of GLOBAL_EDITORIAL_LIKES_ON_IMGS
		set_of_excess_objs = set(excess_objs)
		editorial_votes_to_delete = []
		all_editorial_votes = my_server.zrange(GLOBAL_EDITORIAL_LIKES_ON_IMGS,0,-1)
		for vote in all_editorial_votes:
			obj_hash_name = vote.partition("-")[0]
			if obj_hash_name in set_of_excess_objs:
				editorial_votes_to_delete.append(vote)
		if editorial_votes_to_delete:
			my_server.zrem(GLOBAL_EDITORIAL_LIKES_ON_IMGS,*editorial_votes_to_delete)# removed excess votes from GLOBAL_EDITORIAL_LIKES_ON_IMGS

		# Step 3) remove the excess from GLOBAL_CLOSED_IMG_OBJ_HASH_NAMES
		my_server.zremrangebyscore(GLOBAL_CLOSED_IMG_OBJ_HASH_NAMES,'-inf',twenty_eight_days_ago)


def process_global_closed_objs_and_votes(my_server=None):
	"""
	Organizes data in a form that can be used to calculate 'like_prob' for various editorial voters
	
	# The question we need to answer is: What % of items received audience likes out of all the items editorially liked by a voter?
	"""
	my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
	all_closed_vote_objs = my_server.zrange(GLOBAL_CLOSED_IMG_LIKES,0,-1)

	all_editorial_votes, handpicked_imgs, audience_liked_imgs, trending_imgs = [], set(), set(), set()
	for vote in all_closed_vote_objs:
		# example vote is 'img:123123-543534-1-02 etc'
		data = vote.split("-")
		target_obj_hash_name, voter_id, is_editorial_vote, vote_status = data[0], data[1], data[2], data[3]
		##################################################################
		if vote_status == '02':
			# this vote was cast on an obj that made it into trending via getting handpicked
			handpicked_imgs.add(target_obj_hash_name)
		##################################################################
		if is_editorial_vote == '1':
			all_editorial_votes.append(target_obj_hash_name+"-"+voter_id)
			all_editorial_votes.append(voter_id)
		else:
			audience_liked_imgs.add(target_obj_hash_name)

	###########################
	if all_editorial_votes:
		my_server.zadd(GLOBAL_EDITORIAL_LIKES_ON_IMGS,*all_editorial_votes)
	###########################
	if audience_liked_imgs:
		my_server.sadd(AUDIENCE_LIKED_IMG_HASH_NAMES,*audience_liked_imgs)
	###########################
	if handpicked_imgs:
		my_server.sadd(HANDPICKED_IMG_HASH_NAMES,*handpicked_imgs)
	###########################
	my_server.execute_command('UNLINK', GLOBAL_CLOSED_IMG_LIKES)# no need to keep this around, it's been processed!
	###########################
	calculate_voter_probs(my_server)


def calculate_voter_probs(my_server=None):
	"""
	Calculates the 'like_prob' and the 'handpicked_prob' for each editorial voter in the system 
	I.e.: 
	'like_prob': What % of items received audience likes out of all the items editorially liked by a voter?
	'handpicked_prob': What % of items got handpicked by defenders out of all the items editorially liked by a voter?

	'like_prob' formula is as follows:
	Numerator = Num editorially picked objs (picked by voter_id) that received audience likes
	Denominator = All editorial likes recently cast by voter_id
	like_prob = Numerator/Denominator

	'handpicked_prob' formula is as follows:
	Numerator = Num editorially picked objs (picked by voter_id) that ended up getting handpicked (locked items are exlcuded)
	Denominator = All editorial likes recently cast by voter_id
	handpicked_prob = Numerator/Denominator
	"""
	my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
	votes_and_voters = my_server.zrange(GLOBAL_EDITORIAL_LIKES_ON_IMGS,0,-1,withscores=True)# [(obj_hash_name+"-"+voter_id),...]
	voter_ids = set([int(voter_id) for vote_obj, voter_id in votes_and_voters])# isolating set of editorial voter_ids
	all_audience_liked_obj_hashes = my_server.smembers(AUDIENCE_LIKED_IMG_HASH_NAMES)
	all_handpicked_obj_hashes = my_server.smembers(HANDPICKED_IMG_HASH_NAMES)

	voter_like_probs, voter_handpicked_probs, voter_num_editorial_likes = [], [], []
	# iterate through all voter IDs, calculating 'like_prob' and 'handpicked_prob' for each
	for voter_id in list(voter_ids):
		all_editorial_votes_by_voter_id = my_server.zrangebyscore(GLOBAL_EDITORIAL_LIKES_ON_IMGS, voter_id, voter_id)
		objs_voted_on_by_audience, objs_handpicked_by_defenders = 0, 0
		for vote_obj in all_editorial_votes_by_voter_id:
			obj_hash_name = vote_obj.partition("-")[0]
			if obj_hash_name in all_audience_liked_obj_hashes:
				objs_voted_on_by_audience += 1#i.e. the numerator for 'like_prob'
			if obj_hash_name in all_handpicked_obj_hashes:
				objs_handpicked_by_defenders += 1#i.e the numerator for 'handpicked_prob'

		num_editorial_votes = len(all_editorial_votes_by_voter_id)# i.e the denominator for 'like_prob' and 'handpicked_prob'
		like_prob = (objs_voted_on_by_audience*1.0)/num_editorial_votes
		handpicked_prob = (objs_handpicked_by_defenders*1.0)/num_editorial_votes
		##################
		voter_like_probs.append(voter_id)
		voter_like_probs.append(like_prob)
		##################
		voter_handpicked_probs.append(voter_id)
		voter_handpicked_probs.append(handpicked_prob)
		##################
		voter_num_editorial_likes.append(voter_id)
		voter_num_editorial_likes.append(num_editorial_votes)
	
	if voter_like_probs:
		my_server.delete(VOTER_AUD_LIKE_PROBS)
		my_server.zadd(VOTER_AUD_LIKE_PROBS,*voter_like_probs)

	if voter_num_editorial_likes:
		my_server.delete(NUM_EDITORIAL_LIKES)
		my_server.zadd(NUM_EDITORIAL_LIKES,*voter_num_editorial_likes)

	if voter_handpicked_probs:
		my_server.delete(VOTER_HANDPICKED_PROBS)
		my_server.zadd(VOTER_HANDPICKED_PROBS,*voter_handpicked_probs)


#################################################### Vote banning functionality (defenders) ############################################


def get_votes(obj_id,obj_type, with_net_score=False):
	"""
	Returns all vote values and voter_ids

	Used to show who voted which way on a piece of content (used by defenders)
	Once voting closes, this information is deleted from the system
	"""
	prefix = VOTE_ON_TXT if obj_type == 'tx' else VOTE_ON_IMG
	raw_data = redis.Redis(connection_pool=POOL).zrange(prefix+str(obj_id), 0, -1, withscores=True)
	final_data = []
	for tup in raw_data:
		if int(tup[0]) == -1 and int(tup[1]) == -1:
			#removing default (-1,-1) tuple since it's not a real ID,vote pair
			pass
		else:
			final_data.append((tup[0],1.0 if tup[1] >= 0 else 0.0))# produces a list of tuples, of the sort [('16', 1.0), ('2', 1.0)]
	if with_net_score:
		net_score = 0
		for voter_id, vote_type in final_data:
			if vote_type > 0:
				net_score += 1
			else:
				net_score += 0
		return final_data, net_score
	else:
		return final_data


def is_content_voting_closed(obj_id,obj_type):
	"""
	Returns whether voting on object is open or closed
	"""
	prefix = VOTE_ON_TXT if obj_type == 'tx' else VOTE_ON_IMG
	if redis.Redis(connection_pool=POOL).exists(prefix+str(obj_id)):
		return False
	else:
		return True


#################### Content submission and voting ban ####################


def ban_time_remaining(ban_time, ban_type,hash_name=None):
	"""
	Calculates ban time remaining of a user banned by a defender

	'ban_type' is:
		'1' is 3 hours
		'2' is 1 day
		'3' is 3 days
		'4' is 1 week
		'5' is 1 month
		'6' is forever
	"""
	current_time = time.time()
	time_difference = current_time - float(ban_time)
	if ban_type == '1':
		BENCHMARK_TIME_DIFF = THREE_HOURS
	elif ban_type == '2':
		BENCHMARK_TIME_DIFF = ONE_DAY
	elif ban_type == '3':
		BENCHMARK_TIME_DIFF = THREE_DAYS
	elif ban_type == '4':
		BENCHMARK_TIME_DIFF = ONE_WEEK
	elif ban_type == '5':
		BENCHMARK_TIME_DIFF = ONE_MONTH
	elif ban_type == '6':
		# banned forever
		return True, '-1'
	if time_difference < BENCHMARK_TIME_DIFF:
		return True, (float(ban_time)+BENCHMARK_TIME_DIFF)-current_time
	else:
		if hash_name:
			redis.Redis(connection_pool=POOL).delete(hash_name)    
		return False, None


def retrieve_user_content_and_vote_ban_dictionary(user_id_list):
	"""
	Returns whether a list of users are vote banned (or not)

	Used to show ban-status of already vote-banned users so that defenders don't ban them yet again!
	"""
	pipeline1 = redis.Redis(connection_pool=POOL).pipeline()
	for user_id in user_id_list:
		pipeline1.exists(CONTENT_SUBMISSION_AND_VOTING_BAN+user_id)
	results1, counter, users_with_bans = pipeline1.execute(), 0, {}
	for user_id in user_id_list:
		users_with_bans[user_id] = '1' if results1[counter] else '0'
		counter += 1
	return users_with_bans


def are_ids_unbannable(defender_id, target_id_list):
	"""
	Returns IDs that the defender_id is able to pass judgement on (and are not locked due to another defender handling the case)
	"""
	if target_id_list and defender_id:
		ban_keys, defender_id = [], str(defender_id)
		for target_id in target_id_list:
			ban_keys.append(CONTENT_SUBMISSION_AND_VOTING_BAN+str(target_id))
		my_server = redis.Redis(connection_pool=POOL)
		pipeline1 = my_server.pipeline()
		for ban_key in ban_keys:
			pipeline1.hget(ban_key,'did')
		result1 = pipeline1.execute()
		counter, unbannable_ids = 0, []
		for target_id in target_id_list:
			banner_id = result1[counter]
			if banner_id:
				if banner_id == defender_id:
					# banned by self, hence can ban
					pass
				else:
					# banned by someone else, cannot ban
					unbannable_ids.append(target_id)
			else:
				# not already banned, hence can ban
				pass
			counter += 1
		return unbannable_ids
	else:
		return None


def filter_ids_with_content_and_voting_ban(target_user_ids):
	"""
	Separates fed IDs into banned and unbanned IDs

	Useful in avoiding 'double banning'
	"""
	target_user_ids, ban_keys = map(str,target_user_ids), []
	for target_user_id in target_user_ids:
		ban_keys.append(CONTENT_SUBMISSION_AND_VOTING_BAN+target_user_id)
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	for ban_key in ban_keys:
		pipeline1.exists(ban_key)
	result1 = pipeline1.execute()
	unbanned_ids, banned_ids, counter = [], [], 0
	for target_user_id in target_user_ids:
		if result1[counter]:
			banned_ids.append(target_user_id)
		else:
			unbanned_ids.append(target_user_id)
		counter += 1
	return unbanned_ids, banned_ids


def check_content_and_voting_ban(target_user_id, with_details=False):
	"""
	Used to check if a user is banned, and if required, can also fetch the ban details for showing to the user
	
	"""
	hash_name = CONTENT_SUBMISSION_AND_VOTING_BAN+str(target_user_id)
	my_server = redis.Redis(connection_pool=POOL)
	hash_contents = my_server.hgetall(hash_name)
	if hash_contents:
		ban_type = hash_contents["b"]
		if ban_type == '6':
			if with_details:
				hash_contents['r'] = hash_contents['r'].decode('utf-8') if 'r' in hash_contents else ''
				hash_contents['oun'] = hash_contents['oun'].decode('utf-8') if 'oun' in hash_contents else ''
				hash_contents['dunm'] = hash_contents['dunm'].decode('utf-8') if 'dunm' in hash_contents else ''
				hash_contents['tunm'] = json.loads(hash_contents['tunm'])
				return True, '-1', hash_contents
			else:
				return True, '-1'#'-1' is forever in templates
		elif ban_type in ('1','2','3','4','5'):
			ban_start_time = hash_contents["t"]
			is_banned, time_remaining = ban_time_remaining(ban_start_time, ban_type, hash_name=hash_name)
			if with_details:
				hash_contents['r'] = hash_contents['r'].decode('utf-8') if 'r' in hash_contents else ''
				hash_contents['oun'] = hash_contents['oun'].decode('utf-8') if 'oun' in hash_contents else ''
				hash_contents['dunm'] = hash_contents['dunm'].decode('utf-8') if 'dunm' in hash_contents else ''
				hash_contents['tunm'] = json.loads(hash_contents['tunm'])
				return is_banned, time_remaining, hash_contents
			else:
				return is_banned, time_remaining
		else:
			if with_details:
				return False, None, None
			else:
				return False, None
	else:
		if with_details:
			return False, None, None
		else:
			return False, None


def remove_content_and_voting_ban(target_user_id, target_username, removal_reason, time_now, editor_id, editor_uname):
	"""
	Remove user's content submission ban (both photos or text)
	
	PARAMETERS:
	target_user_id: ID of the user who's ban is to be edited
	removal_reason: string containing reason why ban is removed
	time_now: time of editing/removal
	editor_id: ID of defender editing/removing the ban (i.e. self)
	editor_uname: username of defender editing/removing the ban (i.e. self)
	"""
	ban_key = CONTENT_SUBMISSION_AND_VOTING_BAN+str(target_user_id)
	my_server = redis.Redis(connection_pool=POOL)
	if my_server.exists(ban_key):
		ban_detail = my_server.hgetall(ban_key)
		old_editor_id, old_editor_uname, ban_levied_by = ban_detail.get('eid',''), ban_detail.get('eun',''), ban_detail['did']
		previously_banned_by_some_else = True if ban_levied_by != str(editor_id) else False
		if previously_banned_by_some_else and in_defenders(ban_levied_by,my_server):
			# if this person is still a defender, inform them about the removal
			# form payload for 'prev' defender (it will go in their ledger via 'lpush')
			payload_for_prev_defender_ledger = ban_detail
			payload_for_prev_defender_ledger['utid'] = target_user_id# the target user being unbanned
			payload_for_prev_defender_ledger['utunm'] = target_username# the target user being unbanned (same as 'oun' if bad_submission)
			payload_for_prev_defender_ledger['edit_time'] = time_now
			payload_for_prev_defender_ledger['edit_remark'] = removal_reason
			payload_for_prev_defender_ledger['eid'] = editor_id
			payload_for_prev_defender_ledger['eunm'] = editor_uname
			payload_for_prev_defender_ledger['oeid'] = old_editor_id
			payload_for_prev_defender_ledger['oeunm'] = old_editor_uname.decode('utf-8') if old_editor_uname else ''
			payload_for_prev_defender_ledger['act'] = 'ban_removed_by_other'# over writing 'act'
			pushed = push_to_defender_ledger(defender_id=ban_levied_by, json_payload=json.dumps(payload_for_prev_defender_ledger), also_super_admin=False, \
				my_server=my_server)# no need to save this in super admin's ledger, that will happen when 'payload_for_your_ledger' gets filled anyway
		payload_for_your_ledger = ban_detail
		payload_for_your_ledger['utid'] = target_user_id# the target user being unbanned
		payload_for_your_ledger['utunm'] = target_username# the target user being unbanned
		payload_for_your_ledger['edit_time'] = time_now
		payload_for_your_ledger['edit_remark'] = removal_reason
		payload_for_your_ledger['eid'] = editor_id
		payload_for_your_ledger['eunm'] = editor_uname
		payload_for_your_ledger['oeid'] = old_editor_id
		payload_for_your_ledger['oeunm'] = old_editor_uname.decode('utf-8') if old_editor_uname else ''
		payload_for_your_ledger['act'] = 'others_ban_removed_by_self' if previously_banned_by_some_else else 'own_ban_removed_by_self'
		pushed = push_to_defender_ledger(defender_id=editor_id, json_payload=json.dumps(payload_for_your_ledger), also_super_admin=True, my_server=my_server)
		# get the current ban ttl
		ban_exists = my_server.exists(ban_key)
		if ban_exists:
			ban_ttl = my_server.ttl(ban_key)
			# delete the ban before returning the value, to honor 'ban_removed' command
			my_server.delete(ban_key)
			if ban_ttl:
				return ban_ttl
			else:
				return 'forever'
		else:
			return 'key_does_not_exist'
	else:
		return 'key_does_not_exist'


def edit_content_and_voting_ban(target_user_id, target_username, edit_reason, new_dur, time_now, editor_id, editor_uname):
	"""
	PARAMETERS:
	target_user_id: ID of the user who's ban is to be edited
	new_dur: the new ban duration (encoded into '1','2','3','4','5','6')
	banner_uname: username of defender
	banner_id: ID of defender
	inform_prev_banner: Boolean depicting whether the previous banner has to be informed of this edition or not
	"""
	ban_key = CONTENT_SUBMISSION_AND_VOTING_BAN+str(target_user_id)
	my_server = redis.Redis(connection_pool=POOL)
	# get the current ban ttl
	ban_exists = my_server.exists(ban_key)
	if not ban_exists:
		return None, 'key_does_not_exist'
	else:
		original_ttl = my_server.ttl(ban_key)
		ban_detail = my_server.hgetall(ban_key)
		old_editor_id, old_editor_uname, ban_levied_by = ban_detail.get('eid',None), ban_detail.get('eun',None), ban_detail['did']
		previously_banned_by_some_else = True if ban_levied_by != str(editor_id) else False
		if previously_banned_by_some_else and in_defenders(ban_levied_by,my_server):
			# if this person is still a defender, inform them about the edit
			# form payload for 'prev' defender (it will go in their ledger via 'lpush')
			payload_for_prev_defender_ledger = ban_detail
			payload_for_prev_defender_ledger['utid'] = target_user_id# the target user being unbanned
			payload_for_prev_defender_ledger['utunm'] = target_username# the target user being unbanned (same as 'oun' if bad_submission)
			payload_for_prev_defender_ledger['edit_time'] = time_now
			payload_for_prev_defender_ledger['edit_remark'] = edit_reason
			payload_for_prev_defender_ledger['edit_dur'] = new_dur
			payload_for_prev_defender_ledger['eid'] = editor_id
			payload_for_prev_defender_ledger['eunm'] = editor_uname
			if old_editor_id:
				payload_for_prev_defender_ledger['oeid'] = old_editor_id
				payload_for_prev_defender_ledger['oeunm'] = old_editor_uname.decode('utf-8')
			payload_for_prev_defender_ledger['act'] = 'ban_edited_by_other'# over writing 'act'
			pushed = push_to_defender_ledger(defender_id=ban_levied_by, json_payload=json.dumps(payload_for_prev_defender_ledger), also_super_admin=False, \
				my_server=my_server)# no need to save this in super admin's ledger, that will happen when 'payload_for_your_ledger' gets filled anyway
		payload_for_your_ledger = ban_detail
		payload_for_your_ledger['utid'] = target_user_id# the target user being unbanned
		payload_for_your_ledger['utunm'] = target_username# the target user being unbanned
		payload_for_your_ledger['edit_time'] = time_now
		payload_for_your_ledger['edit_remark'] = edit_reason
		payload_for_your_ledger['edit_dur'] = new_dur
		payload_for_your_ledger['eid'] = editor_id
		payload_for_your_ledger['eunm'] = editor_uname
		if old_editor_id:
			payload_for_your_ledger['oeid'] = old_editor_id
			payload_for_your_ledger['oeunm'] = old_editor_uname.decode('utf-8')
		payload_for_your_ledger['act'] = 'others_ban_edited_by_self' if previously_banned_by_some_else else 'own_ban_edited_by_self'
		pushed = push_to_defender_ledger(defender_id=editor_id, json_payload=json.dumps(payload_for_your_ledger), also_super_admin=True, my_server=my_server)
		#############################################
		# retrieve some required details from existing ban
		old_dur, old_time = ban_detail['b'], ban_detail['t']
		# add some required details into existing ban to edit it
		context = {'b':new_dur,'t':time_now,'ob':old_dur,'ot':old_time,'eid':editor_id,'eun':editor_uname}
		if has_super_privilege(editor_id,my_server):
			context["sd_lock"] = '1'# super_defender_lock is in place
		my_server.hmset(ban_key,context)
		# edit the ban's ttl
		if new_dur == '1':
			# ban for 3 hrs
			my_server.expire(ban_key,THREE_HOURS)
			expire_time = THREE_HOURS
		elif new_dur == '2':
			# ban for 24 hrs
			my_server.expire(ban_key,ONE_DAY)
			expire_time = ONE_DAY
		elif new_dur == '3':
			# ban for 3 days
			my_server.expire(ban_key,THREE_DAYS)
			expire_time = THREE_DAYS
		elif new_dur == '4':
			# ban for 1 week
			my_server.expire(ban_key,ONE_WEEK)
			expire_time = ONE_WEEK
		elif new_dur == '5':
			# ban for 1 month
			my_server.expire(ban_key,ONE_MONTH)
			expire_time = ONE_MONTH
		else:
			# ban 'forever'
			my_server.persist(ban_key)# remove any 'ttl' that might exist
			expire_time = 'forever'
		if old_dur == '6':
			return expire_time,'forever'
		else:
			# return original_ttl
			return expire_time,original_ttl


def is_ban_editing_locked(banned_id):
	"""
	Checks if a ban has been locked after a super defender changed it
	"""
	if redis.Redis(connection_pool=POOL).hget(CONTENT_SUBMISSION_AND_VOTING_BAN+str(banned_id),'sd_lock') == '1':
		return True
	else:
		return False


def is_abusive_troll(user_id):
	"""
	If user is an abusive troll, they ought to be rate-limited from submitting public posts
	"""
	return redis.Redis(connection_pool=POOL).zscore(TROLLS,user_id)


def mark_abusive_troll(defender_id, target_user_id):
	"""
	When user write something excessively trollish and are banned, their public posts still remain curtailed
	"""
	redis.Redis(connection_pool=POOL).zadd(TROLLS,target_user_id,time.time())


def impose_content_and_voting_ban(target_user_ids, target_usernames, ban_duration, current_time, banner_uname, obj_type, obj_id, obj_owner_uname, \
	obj_owner_id, ban_reason, reference, banner_id, sin):
	"""
	This is triggered when content submitter or malicious voter are slapped with a ban

	PARAMETERS:
	'target_user_ids': list of ids that are to be banned
	'target_usernames': list of usernames that are being banned
	'ban_duration': ranges between '1','2','3','4','5' and '6', and denotes the duration of the ban
	'current_time': time at the point of banning
	'banner_uname': username of the banning defender
	'obj_type': 'tx' or 'img' object
	'obj_id': object ID
	'obj_owner_uname': username of the object owner. Same as target_usernames list if banning a content submitter, or could be different if banning bad voters
	'obj_owner_id': ID of the object owner. Same as target_user_ids if banning a content submitter, or coule be different if banning bad voters
	'ban_reason': ban reason provided by the defender (in defender's own words)
	'reference': data containing a reference a banned user can be shown regarding the text/image object that was acted upon
	'banner_id': defender ID
	'sin': string identifying why user is being banned. 'bad_submission' if it's a malicious content submission, otherwise 'bad_voting'
	"""
	if ban_duration not in ('1','2','3','4','5','6') or not sin:
		return None
	else:
		# creating keys allowing banned users to see their ban payloads
		target_user_ids, ban_keys = map(str,target_user_ids), []
		for target_user_id in target_user_ids:
			ban_keys.append(CONTENT_SUBMISSION_AND_VOTING_BAN+target_user_id)

		# forming payload to be shown to the banned user
		payload = {'t':current_time,'b':ban_duration,'tp':obj_type, 'remark':ban_reason, 'oun':obj_owner_uname, 'obid':obj_id, 'sin':sin,\
		'did':banner_id,'dunm':banner_uname,'tunm':json.dumps(target_usernames),'act':'banned'}
		if obj_type == 'tx':
			payload['txt'] = reference
		else:
			payload['pu'] = reference

		# determining ban durations
		if ban_duration == '1':
			# ban for 3 hrs
			ban_time = THREE_HOURS
		elif ban_duration == '2':
			# ban for 24 hrs
			ban_time = ONE_DAY
		elif ban_duration == '3':
			# ban for 3 days
			ban_time = THREE_DAYS
		elif ban_duration == '4':
			# ban for 1 week
			ban_time = ONE_WEEK
		elif ban_duration == '5':
			# ban for 1 month
			ban_time = ONE_MONTH
		else:
			# do nothing, ban 'forever'
			ban_time = '-1'

		# setting user ban(s)
		my_server = redis.Redis(connection_pool=POOL)
		pipeline1 = my_server.pipeline()
		for ban_key in ban_keys:
			pipeline1.hmset(ban_key,payload)
			if ban_time != '-1':
				pipeline1.expire(ban_key,ban_time)
		pipeline1.execute()

		# logging the fact that defender 'handled' a case (incrementing their case file's counter)
		if sin == "bad_submission":
			increment_defender_case_file(banner_id,'bad_submission',my_server)
		elif sin == "bad_voting":
			# even if multiple voters banned, it's counted as 1 case
			increment_defender_case_file(banner_id,'bad_voting',my_server)

		# adding to defender's and super_admin's ledgers
		json_payload = json.dumps(payload)
		pushed = push_to_defender_ledger(defender_id=banner_id, json_payload=json_payload, also_super_admin=True, my_server=my_server)

		# resetting TOP_TRENDING_SUBMITTERS and TOP_TRENDERS
		my_server.delete(TOP_TRENDING_SUBMITTERS)
		calculate_top_trenders()
		my_server.delete(TOP_TRENDERS)

		return ban_time


def increment_defender_case_file(defender_id,sin,my_server=None):
	"""
	Tracks number of various cases handled by a defender during their tenure
	"""
	defender_id = str(defender_id)
	my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
	if sin == 'bad_submission':
		my_server.hincrby(DEFENDER_CASE_COUNT+defender_id,'bad_submission',amount=1)
	elif sin == 'bad_voting':
		my_server.hincrby(DEFENDER_CASE_COUNT+defender_id,'bad_voting',amount=1)
	elif sin == 'bad_profile':
		my_server.hincrby(DEFENDER_CASE_COUNT+defender_id,'bad_profile',amount=1)# i.e. bad profile pic or bad nickname
	elif sin == 'bad_mehfil':
		my_server.hincrby(DEFENDER_CASE_COUNT+defender_id,'bad_mehfil',amount=1)# i.e bad topic or rules
	else:
		pass


def push_to_defender_ledger(defender_id, json_payload, also_super_admin=False, my_server=None):
	"""
	Pushes banning data into defender's and super_admin's respective ledgers
	"""
	my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
	if in_defenders(defender_id, my_server):
		defenders_ledger = DEFENDERS_LEDGER+str(defender_id)
		my_server.lpush(defenders_ledger, json_payload)#defenders' ledger
		my_server.ltrim(defenders_ledger, 0, (DEFENDER_LEDGERS_SIZE-1))# keeping latest 40 blocks/unblocks for each defender
		if also_super_admin:
			my_server.lpush(GLOBAL_ADMINS_LEDGER,json_payload)#global admin's ledger
			my_server.ltrim(GLOBAL_ADMINS_LEDGER, 0, (GLOBAL_ADMIN_LEDGERS_SIZE-1))# keeps most recent 3000 blocks/unblocks
		return True
	else:
		return False

		
##################### Defenders case logging #####################


def get_defenders_ledger(defender_id, with_ttl=False):
	"""
	Retrieves previous banning activity of given defender
	"""
	info, my_server, ledger_key = [], redis.Redis(connection_pool=POOL), DEFENDERS_LEDGER+str(defender_id)
	data = my_server.lrange(ledger_key,0,-1)
	if data:
		for block_info in data:
			credentials = json.loads(block_info)
			credentials['tunm'] = json.loads(credentials['tunm'])
			info.append(credentials)
	if with_ttl:
		ttl = my_server.ttl(ledger_key)
		if ttl > 4:
			return info, ttl# a 'ttl' is enforced on the ledger if defender has been removed (i.e. this is a legacy ledger)
		else:
			return info, None
	else:
		return info


def get_global_admins_ledger(page_number, rejection_history=False):
	"""
	Retrieves previous banning activity of all defenders
	"""
	info, my_server = [], redis.Redis(connection_pool=POOL)
	if rejection_history:
		data = my_server.lrange(GLOBAL_ADMINS_REJECTIONS_LEDGER,ITEMS_PER_PAGE_IN_ADMINS_LEDGER*(page_number-1),(ITEMS_PER_PAGE_IN_ADMINS_LEDGER*page_number)-1)#ITEMS_PER_PAGE_IN_ADMINS_LEDGER = 50
		if data:
			for block_info in data:
				# credentials = json.loads(block_info)
				# credentials['oun'] = json.loads(credentials['oun'])
				# credentials['dun'] = credentials['dun'].encode('utf-8')# if 'dun' in credentials else ''
				info.append(json.loads(block_info))
		if info:
			return info, my_server.llen(GLOBAL_ADMINS_REJECTIONS_LEDGER)
		else:
			return [], 0
	else:
		data = my_server.lrange(GLOBAL_ADMINS_LEDGER,ITEMS_PER_PAGE_IN_ADMINS_LEDGER*(page_number-1),(ITEMS_PER_PAGE_IN_ADMINS_LEDGER*page_number)-1)#ITEMS_PER_PAGE_IN_ADMINS_LEDGER = 50
		if data:
			for block_info in data:
				credentials = json.loads(block_info)
				credentials['tunm'] = json.loads(credentials['tunm'])
				credentials['dunm'] = credentials['dunm'].encode('utf-8')# if 'dunm' in credentials else ''
				info.append(credentials)
		if info:
			return info, my_server.llen(GLOBAL_ADMINS_LEDGER)
		else:
			return [], 0


def log_banning(target_uname,reason_of_ban,action, dur_of_ban,time_of_ban,banned_by_id,banned_by_uname, obj_id, owner_id, oun, \
	photo_thumb=None, cap=None, ban_type=None, obj_type=None):
	"""
	Logging banning event for defender and super admins (for later reference)

	Also keeps account of banning for global admin
	'action' is 'banned_content_submitter' 'undo_content_ban' 'banned_voter' ('tp' is type of obj)
	"""
	banning_data = {'rsn':reason_of_ban,'dur':dur_of_ban,'t':time_of_ban,'obj_id':obj_id,'owner_id':owner_id,'act':action, \
	'tunm':target_uname,'oun':oun, 'bt':ban_type, 'tp':obj_type}# target_uname can be a list of unames if multi_ban is being documented (over erroneous voting)
	if obj_type == 'tx':
		banning_data['c'] = cap
	else:
		banning_data['p'] = photo_thumb
	my_server, defenders_ledger = redis.Redis(connection_pool=POOL), DEFENDERS_LEDGER+str(banned_by_id)
	my_server.lpush(defenders_ledger,json.dumps(banning_data))#defenders' ledger
	my_server.ltrim(defenders_ledger, 0, 39)# keeping latest 40 blocks/unblocks for each defender
	# save for global admin as well
	banning_data["did"] = banned_by_id
	banning_data['dunm'] = banned_by_uname
	my_server.lpush(GLOBAL_ADMINS_LEDGER,json.dumps(banning_data))#global admin's ledger
	my_server.ltrim(GLOBAL_ADMINS_LEDGER, 0, (GLOBAL_ADMIN_LEDGERS_SIZE-1))# keeps most recent 3000 blocks/unblocks



# def cleanse_all_feeds_of_user_content(target_user_id, post_type, cleanse_feeds='1'):
# 	"""
# 	Ensures no content of target_user_id is part of current feeds

# 	Called when a defender bans a user's content
# 	Removes textual and image content both
# 	Suggested edit: IF CONTENT TYPE IS 'TX', ONLY CLEANSE FROM HOMEFEED
# 	"""
# 	if post_type not in ('img','tx'):
# 		pass
# 	elif cleanse_feeds != '1':
# 		pass
# 	else:
# 		target_user_id = str(target_user_id)
# 		my_server = redis.Redis(connection_pool=POOL)
# 		# retrieve all feeds
# 		pipeline1 = my_server.pipeline()
# 		pipeline1.zrange(PHOTO_SORTED_FEED,0,-1)
# 		pipeline1.zrange(TRENDING_PHOTO_FEED,0,-1)
# 		pipeline1.zrange(HOME_SORTED_FEED,0,-1)
# 		result1 = pipeline1.execute()
# 		fresh_image_objs, best_image_objs, home_objs = result1[0], result1[1], result1[2]
		
		
# 		# isolating target user's fresh photos
# 		pipeline2 = my_server.pipeline()
# 		for hash_name in fresh_image_objs:#contains img:4312341 type objs
# 			pipeline2.hget(hash_name,'si')
# 		result2, counter = pipeline2.execute(), 0
# 		target_fresh_photo_hashes = []
# 		for hash_name in fresh_image_objs:
# 			if result2[counter] == target_user_id:
# 				target_fresh_photo_hashes.append(hash_name)# i.e. all objs target user uploaded in photofeed:1000
# 			counter += 1

# 		#isolating target user's best photos
# 		pipeline3 = my_server.pipeline()
# 		for hash_name in best_image_objs:#contains img:4312341 type objs
# 			pipeline3.hget(hash_name,'si')
# 		result3, counter = pipeline3.execute(), 0
# 		target_best_photo_hashes = []
# 		for hash_name in best_image_objs:
# 			if result3[counter] == target_user_id:
# 				target_best_photo_hashes.append(hash_name)# i.e. all objs target user uploaded in bestphotofeed:1000
# 			counter += 1
		
# 		#isolating target user's home posts (text and photos both)
# 		pipeline4 = my_server.pipeline()
# 		for hash_name in home_objs:#contains tx:1231 or img:4312341 type objs
# 			pipeline4.hget(hash_name,'si')
# 		result4, counter = pipeline4.execute(), 0
# 		target_home_hashes = []
# 		for hash_name in home_objs:
# 			if result4[counter] == target_user_id:
# 				target_home_hashes.append(hash_name)# i.e. all objs target user uploaded in homefeed:1000
# 			counter += 1

# 		# 1) delete isolated hash, 2) expire voting objects so voting is 'closed' after ten more mins, 3) cleanse the feeds

# 		# removing target users' photofeed hashes, and expiring voting objs
# 		pipeline5 = my_server.pipeline()
# 		for hash_name in target_fresh_photo_hashes:
# 			pipeline5.delete(hash_name)
# 			pipeline5.expire(VOTE_ON_IMG+hash_name[4:],TEN_MINS)#expire - don't delete - so that a defender can ban voters if need be in the next 10 min window!
# 			pipeline5.zrem(PHOTO_SORTED_FEED,hash_name)
# 		pipeline5.execute()

# 		# removing target users' bestphotofeed hashes, and expiring voting objs
# 		pipeline6 = my_server.pipeline()
# 		for hash_name in target_best_photo_hashes:
# 			pipeline6.delete(hash_name)#might have been deleted in the previous loop, but we need to catch cases where a hash may not have been in the previous list
# 			pipeline6.expire(VOTE_ON_IMG+hash_name[4:],TEN_MINS)
# 			pipeline6.zrem(TRENDING_PHOTO_FEED,hash_name)
# 		pipeline6.execute()

# 		# removing target users' hashes from TRENDING_PHOTO_DETAILS
# 		# photo_ids_to_be_removed = [hash_obj.split(":")[1] for hash_obj in target_best_photo_hashes]
# 		# photo_ids_to_be_removed = map(float,photo_ids_to_be_removed)
# 		# pipeline7 = my_server.pipeline()
# 		# for photo_id in photo_ids_to_be_removed:
# 		# 	pipeline7.zremrangebyscore(TRENDING_PHOTO_DETAILS,photo_id,photo_id)
# 		# pipeline7.execute()

# 		# removing target users' homefeed hashes, and expiring voting objs
# 		pipeline8 = my_server.pipeline()
# 		for hash_name in target_home_hashes:
# 			pipeline8.delete(hash_name)
# 			if hash_name[:2] == 'tx':
# 				pipeline8.expire(VOTE_ON_TXT+hash_name[3:],TEN_MINS)
# 			else:
# 				pipeline8.expire(VOTE_ON_IMG+hash_name[4:],TEN_MINS)
# 			pipeline8.zrem(HOME_SORTED_FEED,hash_name)
# 		pipeline8.execute()
# 		# this approach has a lot of duplication of effort, but is comprehensive

##################### Adding or removing defenders ######################


def in_defs_forever(user_id):
	"""
	Checks if given user ID is a defender (currently or in the past)

	DEFENDERS is a current list
	DEFENDERS_FOREVER is a lasting list of all defenders ever
	"""
	if redis.Redis(connection_pool=POOL).zscore(DEFENDERS_FOREVER, user_id):
		return True
	else:
		return False


def in_defenders(user_id, my_server=None, return_super_status=False):
	"""
	Checks if given user ID is indeed a defender currently

	DEFENDERS is a current list
	DEFENDERS_FOREVER is a lasting list of all defenders ever
	"""
	my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
	if my_server.zscore(DEFENDERS, user_id):
		if return_super_status:
			priv_level = my_server.hget(DEFENDER_DATA+str(user_id),'priv')
			if priv_level == '1':
				return True, True
			else:
				return True, False
		else:
			return True
	else:
		if return_super_status:
			return False, False
		else:
			return False


def has_super_privilege(user_id, my_server=None):
	"""
	Checks whether a given user_id has super defender priveleges (outlined in add_defender()'s docstring)
	"""
	is_defender, is_super = in_defenders(user_id, my_server=my_server, return_super_status=True)
	return is_super


def retrieve_all_defenders(mark_super=False):
	"""
	Returns all current and olden defenders

	if 'mark_super' is set, return the privilege level of current defenders too
	"""
	my_server = redis.Redis(connection_pool=POOL)
	curr_defenders = my_server.zrevrange(DEFENDERS,0,-1, withscores=True)
	all_defenders = my_server.zrevrange(DEFENDERS_FOREVER,0,-1, withscores=True)
	if mark_super:
		curr_defenders_with_privs = []
		for curr_def_id,adding_time in curr_defenders:
			priv_level = '1' if my_server.hget(DEFENDER_DATA+curr_def_id,'priv') == '1' else '0'
			curr_defenders_with_privs.append((curr_def_id,adding_time,priv_level))
		return curr_defenders, all_defenders, curr_defenders_with_privs
	else:
		return curr_defenders, all_defenders


def remove_defender(user_id):
	"""
	Remove from defender list

	Keep user_id intact in DEFENDERS_FOREVER (so we can always tell who was once a defender)
	"""
	user_id = str(user_id)
	my_server = redis.Redis(connection_pool=POOL)
	my_server.zrem(DEFENDERS, user_id)
	my_server.delete(DEFENDER_DATA+user_id)# removing the hash map with defender data
	my_server.expire(DEFENDERS_LEDGER+user_id,2)#TWO_MONTHS)# their ledger expires after a while


def add_defender(own_id, target_id, time_of_adding, is_super):
	"""
	Adds a new defender

	Privileges:
	'0': Regular defender
	'1': Has the privilege to:
		i) edit/remove other defenders' banning actions 
		ii) access the global ledger
		iii) add/remove basic defenders
		iv) view top reporters
	"""
	if target_id:
		target_id = str(target_id)
		my_server = redis.Redis(connection_pool=POOL)
		my_server.zadd(DEFENDERS, target_id, time_of_adding)# this just records current defenders
		my_server.zadd(DEFENDERS_FOREVER,target_id,time_of_adding)#simply keeps a record of all defenders
		my_server.hmset(DEFENDER_DATA+target_id,{'dfid':target_id,'priv':'1' if is_super else '0','appointed_at':time_of_adding,'appointed_by':own_id})
		# remove any 'ttl' that might have existed on the defender's ledger (in case they were 're-added')
		ledger_key = DEFENDERS_LEDGER+target_id
		if my_server.exists(ledger_key):
			my_server.persist(ledger_key)
		# Even admins can't add defenders in quick fire. Rate limit them as a precaution!
		my_server.setex(DEFENDER_ADDITION_RATE_LIMITED+str(own_id),'1',TWENTY_MINS)


def is_rate_limited_from_adding_defender(own_id):
	"""
	Check if admin is able to add a defender
	"""
	if redis.Redis(connection_pool=POOL).ttl(DEFENDER_ADDITION_RATE_LIMITED+str(own_id)) > 2:
		return True
	else:
		return False


##################### Content banning temp data (while defender is filling the banning forms) ######################


def temporarily_save_content_details(obj_id, owner_id, photo_url, caption, obj_type, origin, owner_uname, link_id, banner_id, sin, target_id=None, \
	target_ids=None, voting_ban_dur=None):
	"""
	Temporarily saves target item and item poster credentials for processing a content_submission_and_voting ban
	"""
	data = {'obid':obj_id,'ooid':owner_id,'purl':photo_url,'cap':caption,'tp':obj_type,'orig':origin,'oun':owner_uname,'lid':link_id,\
		'bid':banner_id,'sin':sin}
	if target_id:
		data['tid'] = target_id
	elif target_ids:
		data['tids'] = target_ids
		data['vdur'] = voting_ban_dur
	else:
		return False
	redis.Redis(connection_pool=POOL).setex(CONTENT_BAN_TEMP_KEY+str(banner_id),json.dumps(data),ONE_HOUR)
	return True


def enrich_temporarily_saved_content_details_with_duration(banner_id, duration, return_credentials=False):
	"""
	Enriches a temporarily saved ban data key with 'duration'

	Applicable for 'bad_submission' type banning only. 'bad_voting' type banning is pre-enriched with 'dur' data
	"""
	saved_key = CONTENT_BAN_TEMP_KEY+str(banner_id)
	my_server = redis.Redis(connection_pool=POOL)
	data = my_server.get(saved_key)
	if data:
		data = json.loads(data)
		data['dur'] = duration
		my_server.setex(saved_key,json.dumps(data),TWENTY_MINS)
		if return_credentials:
			return True, data
		else:
			return True
	else:
		# data was never set, or has expired
		if return_credentials:
			return False, None
		else:
			return False

def retrieve_temporary_saved_content_details(banner_id):
	"""
	Retrieves and returns temporarily saved data useful when imposing a content ban
	"""
	data = redis.Redis(connection_pool=POOL).get(CONTENT_BAN_TEMP_KEY+str(banner_id))
	if data:
		return json.loads(data)
	else:
		return None

def delete_temporarily_saved_content_details(banner_id):
	"""
	Deletes temporarily saved content
	"""
	redis.Redis(connection_pool=POOL).delete(CONTENT_BAN_TEMP_KEY+str(banner_id))



##################### Content, mehfil and profile complaints by users ######################

def set_complaint(report_desc, rep_type, obj_id, obj_owner_id, obj_type, price_paid, reporter_id, time_now, feedback_text=None, img_caption=None, \
	obj_url=None, obj_txt=None, orig_obid=None,orig_url=None, orig_txt=None, mehfil_topic=None, mehfil_rules=None, mehfil_report_tp=None, \
	reported_item_ct=None, orig_item_ct=None, new_obj_type=None):
	"""
	Enter a complaint in the list displayed to our defenders

	Handles both obj_types 'tx' and type 'img' (and new_obj_types 'g' and 't')
	If 'mf', save obj_id, obj_type, mehfil topic and rules
	If 'pf', save obj_id, obj_type, image_url and nickname
	If 'tx', save obj_id and obj_txt
	If 'img', save obj_id, img_caption and obj_url
	If special case of rep_type in ('9','10'), use orig_obid and orig_txt (for 'tx'), or orig_obid and orig_url (for 'img')
	Note: also creates a historical object of the complaint for viewing in a list
	"""
	reporter_id, obj_id = str(reporter_id), str(obj_id)
	my_server = redis.Redis(connection_pool=POOL)
	complaining_rate_limited = my_server.ttl(COMPLAINING_RATE_LIMITED+reporter_id)
	if complaining_rate_limited > 1:
		# reporter is rate limited from reporting
		return complaining_rate_limited
	else:
		# if user reported this object recently, disallow (we're pinging a sorted set that contains most recent 20 reports of a user)
		complaint_id = obj_type+":"+obj_id#turn this into payload for COMPLAINTS_SUBMITTED, and its current contents into a hash
		# reported_recently = my_server.zcount(COMPLAINTS_SUBMITTED+reporter_id,complaint_id,complaint_id)
		reported_recently = my_server.zscore(COMPLAINTS_SUBMITTED+reporter_id,complaint_id)
		if reported_recently:
			return '-1'
		else:
			# didn't report recently, proceed
			report = {'h':report_desc,'i':reporter_id,'rt':rep_type}
			if obj_type == 'mf':
				# public mehfil topic/rules complaint
				report["d"] = feedback_text
				report["categ"] = mehfil_report_tp
				mehfil_report, num_reports = COMPLAINT+complaint_id, 1
				if my_server.exists(mehfil_report):
					# appending to a pre-existing report
					existing_reports = json.loads(my_server.hget(mehfil_report,'pl'))
					existing_reports.append(report)
					my_server.hset(mehfil_report,'pl',json.dumps(existing_reports))
					num_reports = my_server.hincrby(mehfil_report,'n',amount=1)
				else:
					# new report
					new_payload = []
					new_payload.append(report)
					mapping = {'pl':json.dumps(new_payload),'obid':obj_id, 'ooid':obj_owner_id, 'n':num_reports,'tp':obj_type,'c':mehfil_topic,\
					'r':mehfil_rules,'ct':reported_item_ct}
					if new_obj_type:
						mapping['ot'] = new_obj_type
					my_server.hmset(mehfil_report,mapping)
				
				# payables sorted set - contains all amounts owed to all reporter ids - recalled when complaint's fate is decided
				payables = PAYABLES+complaint_id
				prev_payable = my_server.zscore(payables,reporter_id)
				new_amnt_owed = (price_paid if prev_payable is None else prev_payable+int(price_paid))# in case a user has double reported a photo
				my_server.zadd(payables,reporter_id,new_amnt_owed)
				
				# sorted set containing all complaints (useful in defender view - 'cull list')
				pipeline1 = my_server.pipeline()
				pipeline1.zadd(COMPLAINT_LIST,mehfil_report,num_reports)
				pipeline1.setex(COMPLAINING_RATE_LIMITED+reporter_id,1,FOUR_MINS)# stop user from going on a reporting spree in quick succession

				# logging attempt and case description
				pipeline1.zadd(COMPLAINER_TIME_LIST,reporter_id,time_now)
				pipeline1.zincrby(COMPLAINER_ATTEMPT_SORTED_SET,reporter_id,amount=1)
				payload = {'ftx':feedback_text,'h':report_desc,'tp':obj_type,'obid':obj_id,'categ':mehfil_report_tp,'c':mehfil_topic,\
				'r':mehfil_rules,'t':time_now}
				# pipeline1.zadd(COMPLAINTS_SUBMITTED+reporter_id,json.dumps(payload),complaint_id) #logging reporter submissions (change: obj_id+":"+obj_type)
				pipeline1.set(COMPLAINT_HIST_OBJ+reporter_id+":"+complaint_id,json.dumps(payload))
				pipeline1.zadd(COMPLAINTS_SUBMITTED+reporter_id,complaint_id,time_now)
				pipeline1.execute()

				#trimming the sorted set every now and then, down to the latest 20 reports, nothing more!
				if random() < 0.3:
					trim_reporter_complaints(reporter_id, my_server)

				return None
			elif obj_type == 'pf':
				# profile complaint
				report["d"] = feedback_text
				report["categ"] = mehfil_report_tp
				profile_report, num_reports = COMPLAINT+complaint_id, 1
				if my_server.exists(profile_report):
					existing_reports = json.loads(my_server.hget(profile_report,'pl'))
					existing_reports.append(report)
					my_server.hset(profile_report,'pl',json.dumps(existing_reports))
					num_reports = my_server.hincrby(profile_report,'n',amount=1)
				else:
					new_payload = []
					new_payload.append(report)
					mapping = {'pl':json.dumps(new_payload),'obid':obj_id,'ooid':obj_owner_id,'nick':img_caption,'av_img':obj_url,'n':num_reports,\
					'tp':obj_type,'ct':reported_item_ct}
					if new_obj_type:
						mapping['ot'] = new_obj_type
					my_server.hmset(profile_report,mapping)
				# payables sorted set - contains all amounts owed to all reporter ids - recalled when content's fate is decided
				payables = PAYABLES+complaint_id
				prev_payable = my_server.zscore(payables,reporter_id)
				new_amnt_owed = (price_paid if prev_payable is None else prev_payable+int(price_paid))# in case a user has double reported a photo
				my_server.zadd(payables,reporter_id,new_amnt_owed)

				#sorted set containing all reported content (useful in defender view)
				pipeline1 = my_server.pipeline()
				pipeline1.zadd(COMPLAINT_LIST,profile_report,num_reports)
				pipeline1.setex(COMPLAINING_RATE_LIMITED+reporter_id,1,FOUR_MINS)# stop user from going on a reporting spree in quick succession

				# logging attempt and case description
				pipeline1.zadd(COMPLAINER_TIME_LIST,reporter_id,time_now)
				pipeline1.zincrby(COMPLAINER_ATTEMPT_SORTED_SET,reporter_id,amount=1)
				payload = {'ftx':feedback_text,'h':report_desc,'tp':obj_type,'obid':obj_id,'categ':mehfil_report_tp,'purl':obj_url,\
				'nick':img_caption,'t':time_now}
				# pipeline1.zadd(COMPLAINTS_SUBMITTED+reporter_id,json.dumps(payload),complaint_id) #logging reporter submissions (change: obj_id+":"+obj_type)
				pipeline1.set(COMPLAINT_HIST_OBJ+reporter_id+":"+complaint_id,json.dumps(payload))
				pipeline1.zadd(COMPLAINTS_SUBMITTED+reporter_id,complaint_id,time_now)
				pipeline1.execute()

				#trimming the sorted set every now and then, down to the latest 20 reports, nothing more!
				if random() < 0.3:
					trim_reporter_complaints(reporter_id, my_server)

				return None
			elif obj_type == 'img':
				# public image complaint
				if rep_type in ('9','10'):# (change: differentiate between rep_type AND obj_type)
					# this is a report regarding duplicate content
					report["oobid"] = orig_obid
					report["ourl"] = orig_url
				else:
					# essentially not adding feedback_text when duplicate items are being reported (i.e. rep_type in ('9','10')) because we don't need explanatory text then
					report["d"] = feedback_text
				public_image_report, num_reports = COMPLAINT+complaint_id, 1
				if my_server.exists(public_image_report):
					existing_reports = json.loads(my_server.hget(public_image_report,'pl'))
					existing_reports.append(report)
					my_server.hset(public_image_report,'pl',json.dumps(existing_reports))
					num_reports = my_server.hincrby(public_image_report,'n',amount=1)
				else:
					new_payload = []
					new_payload.append(report)
					mapping = {'pl':json.dumps(new_payload),'obid':obj_id,'ooid':obj_owner_id,'c':img_caption,'url':obj_url,'n':num_reports,\
					'tp':obj_type,'ct':reported_item_ct}
					if rep_type in ('9','10'):
						mapping['oict'] = orig_item_ct
					if new_obj_type:
						mapping['ot'] = new_obj_type
					my_server.hmset(public_image_report,mapping)
				# payables sorted set - contains all amounts owed to all reporter ids - recalled when content's fate is decided
				payables = PAYABLES+complaint_id
				prev_payable = my_server.zscore(payables,reporter_id)
				new_amnt_owed = (price_paid if prev_payable is None else prev_payable+int(price_paid))# in case a user has double reported a photo
				my_server.zadd(payables,reporter_id,new_amnt_owed)
				
				#sorted set containing all reported content (useful in defender view)
				pipeline1 = my_server.pipeline()
				pipeline1.zadd(COMPLAINT_LIST,public_image_report,num_reports)
				pipeline1.setex(COMPLAINING_RATE_LIMITED+reporter_id,1,FOUR_MINS)# stop user from going on a reporting spree in quick succession

				# logging attempt and case description
				pipeline1.zadd(COMPLAINER_TIME_LIST,reporter_id,time_now)
				pipeline1.zincrby(COMPLAINER_ATTEMPT_SORTED_SET,reporter_id,amount=1)
				payload = {'ftx':feedback_text,'h':report_desc,'tp':obj_type,'obid':obj_id,'purl':obj_url,'t':time_now}
				# pipeline1.zadd(COMPLAINTS_SUBMITTED+reporter_id,json.dumps(payload),complaint_id) #logging reporter submissions (change: obj_id+":"+obj_type)
				pipeline1.set(COMPLAINT_HIST_OBJ+reporter_id+":"+complaint_id,json.dumps(payload))
				pipeline1.zadd(COMPLAINTS_SUBMITTED+reporter_id,complaint_id,time_now)
				pipeline1.execute()

				#trimming the sorted set every now and then, down to the latest 20 reports, nothing more!
				if random() < 0.3:
					trim_reporter_complaints(reporter_id, my_server)

				return None
			elif obj_type == 'tx':
				# public text complaint
				if rep_type in ('9','10'):
					# this is a report regarding duplicate content
					report["oobid"] = orig_obid
					report["otxt"] = orig_txt
				else:
					# essentially not adding feedback_text when duplicate items are being reported (i.e. rep_type in ('9','10')) because we don't need explanatory text then
					report["d"] = feedback_text
				public_text_report, num_reports = COMPLAINT+complaint_id, 1
				if my_server.exists(public_text_report):
					existing_reports = json.loads(my_server.hget(public_text_report,'pl'))
					existing_reports.append(report)
					my_server.hset(public_text_report,'pl',json.dumps(existing_reports))
					num_reports = my_server.hincrby(public_text_report,'n',amount=1)
				else:
					new_payload = []
					new_payload.append(report)
					mapping = {'pl':json.dumps(new_payload),'obid':obj_id,'ooid':obj_owner_id,'c':obj_txt,'n':num_reports,'tp':obj_type,'ct':reported_item_ct}
					if rep_type in ('9','10'):
						mapping['oict'] = orig_item_ct
					if new_obj_type:
						mapping['ot'] = new_obj_type
					my_server.hmset(public_text_report,mapping)
				# payables sorted set - contains all amounts owed to all reporter ids - recalled when content's fate is decided
				payables = PAYABLES+complaint_id
				prev_payable = my_server.zscore(payables,reporter_id)
				new_amnt_owed = (price_paid if prev_payable is None else prev_payable+int(price_paid))# in case a user has double reported a photo
				my_server.zadd(payables,reporter_id,new_amnt_owed)
				
				#sorted set containing all reported content (useful in defender view)
				pipeline1 = my_server.pipeline()
				pipeline1.zadd(COMPLAINT_LIST,public_text_report,num_reports)
				pipeline1.setex(COMPLAINING_RATE_LIMITED+reporter_id,1,FOUR_MINS)# stop user from going on a reporting spree in quick succession

				# logging attempt and case description
				pipeline1.zadd(COMPLAINER_TIME_LIST,reporter_id,time_now)
				pipeline1.zincrby(COMPLAINER_ATTEMPT_SORTED_SET,reporter_id,amount=1)
				payload = {'ftx':feedback_text,'h':report_desc,'tp':obj_type,'obid':obj_id,'c':obj_txt,'t':time_now}
				# pipeline1.zadd(COMPLAINTS_SUBMITTED+reporter_id,json.dumps(payload),complaint_id) #logging reporter submissions (change: obj_id+":"+obj_type)
				pipeline1.set(COMPLAINT_HIST_OBJ+reporter_id+":"+complaint_id,json.dumps(payload))
				pipeline1.zadd(COMPLAINTS_SUBMITTED+reporter_id,complaint_id,time_now)
				pipeline1.execute()

				#trimming the sorted set every now and then, down to the latest 20 reports, nothing more!
				if random() < 0.3:
					trim_reporter_complaints(reporter_id, my_server)
					
				return None
			else:
				# not entertaining any other reports currently
				return None


def trim_reporter_complaints(reporter_id, my_server=None):
	"""
	A record of each reporter's recent reports is kept - this must be periodically trimmed for memory-management purposes
	"""
	my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
	overflowing = my_server.zrevrange(COMPLAINTS_SUBMITTED+reporter_id,20,-1)
	if overflowing:
		# isolate which overflowing complaints are still unresolved (so we don't accidentally try to delete their HIST objects)
		pipeline1 = my_server.pipeline()
		for complaint_id in overflowing:
			pipeline1.zscore(COMPLAINT_LIST,COMPLAINT+complaint_id)
		still_outstanding = pipeline1.execute()# these complaints haven't been resolved yet, so do not cull their historical objects
		################################################
		counter, deletable_overflowing = 0, []
		for complaint_id in overflowing:
			if not still_outstanding[counter]:
				deletable_overflowing.append(complaint_id)
			counter += 1
		if deletable_overflowing:
			pipeline2 = my_server.pipeline()
			for complaint_id in deletable_overflowing:
				pipeline2.delete(COMPLAINT_HIST_OBJ+reporter_id+":"+complaint_id)
			pipeline2.zrem(COMPLAINTS_SUBMITTED+reporter_id,*overflowing)
			pipeline2.execute()


def get_complainer_ids(obj_id, obj_type, my_server=None):
	"""
	Returns IDs of all complainers of a certain object or content

	obj_type is either 'tx', 'img', 'pf' or 'mf'
	"""
	if not obj_id:
		return []
	else:
		my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
		indiv_complaints = json.loads(my_server.hget(COMPLAINT+obj_type+":"+str(obj_id),'pl'))#list of dictionaries
		complainer_ids = []
		for complaint in indiv_complaints:
			complainer_ids.append(str(complaint["i"]))
		return complainer_ids


def get_payables(reporter_ids,obj_id,obj_type):
	"""
	Return (id,payable) tuple list for ids.

	These are payable points for complainers of content or objects
	"""
	all_payables, selected_payables = redis.Redis(connection_pool=POOL).zrange(PAYABLES+obj_type+":"+obj_id,0,-1,withscores=True), []
	if all_payables:
		for reporter_id, payable_score in all_payables:
			if reporter_id in reporter_ids:
				selected_payables.append((reporter_id,payable_score))
	return selected_payables


def complaint_exists(obj_id, obj_type):
	"""
	Checking to see if an item was already reported

	We allow users to report already reported items
	But we let defenders know in case they themselves try to report an item
	We also let them know if they try to handle an already-handled case
	"""
	return redis.Redis(connection_pool=POOL).exists(COMPLAINT+obj_type+":"+obj_id)


def retrieve_top_complainer_reputation():
	"""
	Shows global list of top complaint reporting IDs (by reputation)
	"""
	my_server = redis.Redis(connection_pool=POOL)
	cached_data = my_server.get(TOP_50_CACHED_DATA)
	if cached_data:
		return json.loads(cached_data)
	else:
		top_50_with_scores = my_server.zrevrange(COMPLAINER_CORRECT_SORTED_SET,0,49,withscores=True)#top 50, with number of correct reports
		top_50_dict = {}
		for reporter_id, num_correct in top_50_with_scores:
			top_50_dict[reporter_id] = num_correct
		only_ids = [i[0] for i in top_50_with_scores]
		pipeline1 = my_server.pipeline()
		for reporter_id in only_ids:
			pipeline1.zscore(COMPLAINER_ATTEMPT_SORTED_SET,reporter_id)
		result1, counter = pipeline1.execute(), 0
		top_50 = []
		for reporter_id in only_ids:
			top_50.append((reporter_id,top_50_dict[reporter_id],result1[counter]))
			counter += 1
		num_correct = my_server.zcard(COMPLAINER_CORRECT_SORTED_SET)# total correct
		my_server.setex(TOP_50_CACHED_DATA,json.dumps([top_50, num_correct]),TWENTY_MINS)
		return (top_50, num_correct)


def cleanse_inactive_complainers():
	"""
	Scrub complainers who haven't complained (i.e. reported content) for over two months (reasoning: they probably don't show up any more)

	The reasoning is that they've probably dropped out, and no longer should be in the "top reporters" lists, nor do we need their case histories, etc.
	This is a scheduled task and runs every 3 days
	"""
	epoch_time_two_months_ago = time.time() - TWO_MONTHS
	my_server = redis.Redis(connection_pool=POOL)
	inactive_complainer_ids = my_server.zrangebyscore(COMPLAINER_TIME_LIST,'-inf','('+str(epoch_time_two_months_ago))

	if inactive_complainer_ids:
		inactive_complainer_ids = set(inactive_complainer_ids)
		# only consider those inactive_complainer_ids whose complaints do NOT exist CURRENTLY in cull-list
		all_current_complaint_objs = my_server.zrange(COMPLAINT_LIST,0,-1)
		for complaint_obj in all_current_complaint_objs:
			data = complaint_obj.split(":")
			obj_type, obj_id = data[1], data[2]
			current_complainer_ids = get_complainer_ids(obj_id, obj_type, my_server)
			if current_complainer_ids:
				for complainer_id in current_complainer_ids:
					inactive_complainer_ids.discard(complainer_id)

		if inactive_complainer_ids:
			# only proceed if inactive_complainers are not present in the current cull-list
			inactive_complainer_ids = list(inactive_complainer_ids)
			pipeline1 = my_server.pipeline()
			#removing from 'attempts' list and set
			pipeline1.zrem(COMPLAINER_TIME_LIST,*inactive_complainer_ids)
			pipeline1.zrem(COMPLAINER_ATTEMPT_SORTED_SET,*inactive_complainer_ids)
			#removing from 'correct' list and set
			pipeline1.zrem(COMPLAINER_CORRECT_TIME_LIST,*inactive_complainer_ids)
			pipeline1.zrem(COMPLAINER_CORRECT_SORTED_SET,*inactive_complainer_ids)
			pipeline1.execute()

			for complainer_id in inactive_complainer_ids:
				# removing 'case files' that are shown to defenders in top 50 reporters view, etc. (retrieve_top_complainer_reputation() for example)
				all_hist_objs = my_server.zrange(COMPLAINTS_SUBMITTED+complainer_id,0,-1)
				pipeline2 = my_server.pipeline()
				for complaint_id in all_hist_objs:
					pipeline2.delete(COMPLAINT_HIST_OBJ+complainer_id+":"+complaint_id)
				pipeline2.delete(COMPLAINTS_SUBMITTED+complainer_id)
				pipeline2.execute()
	my_server.delete(TOP_50_CACHED_DATA)


def log_case_closure(defender_id, defender_uname, obj_id, obj_type, owner_uname, reporter_data, obj_data, time_now):
	"""
	Logging rejected reports so that super defenders can uncover any biases in the defenders
	"""
	rejection_data = {'did':defender_id,'dun':defender_uname, 'obj_id':obj_id, 'tp':obj_type, 't':time_now, 'oun':owner_uname,\
	'reporter_data':reporter_data}# reporter_data_dict is a dictionary of the format {reporter_uname:report_reason}
	if obj_type == 'tx':
		rejection_data['txt'] = obj_data
	else:
		rejection_data['purl'] = obj_data# add more obj types as required
	my_server = redis.Redis(connection_pool=POOL)
	my_server.lpush(GLOBAL_ADMINS_REJECTIONS_LEDGER,json.dumps(rejection_data))
	my_server.ltrim(GLOBAL_ADMINS_REJECTIONS_LEDGER, 0, (GLOBAL_ADMIN_LEDGERS_SIZE-1))# keeps most recent 3000 rejected reports


def log_case_and_incr_reputation(correct_reporter_ids,incorrect_reporter_ids, malicious_reporter_ids, time_now, obj_id, defender_id, defender_uname,\
	obj_type):
	"""
	Logging report 'attempts' and successful outcomes, so that a % success rate (per reporter) can be computed later

	This is called whenever a defender 'decides' a case (from the cull-list)
	It also logs cases raised by each reporter separately
	
	Reporter reputation is calculated thusly:
		Correct reports get +1 (incorrect or malicious reports both don't merit a positive score)
		Incorrect reports get 0 (incorrect and malicious are highly subjective, hence don't give malicious -1)
		Malicious reports get 0
	"""
	complaint_id = obj_type+":"+obj_id
	my_server = redis.Redis(connection_pool=POOL)
	# Retrieving report object and enriching objects according to decision
	report_data = my_server.hget(COMPLAINT+complaint_id,'pl')# 'pl' is the payload - a JSON string (list of dictionaries) containing all reports
	if report_data:
		for report in json.loads(report_data):
			reporter_id = str(report['i'])#int format originally, converted to string
			
			complaint_obj_key = COMPLAINT_HIST_OBJ+reporter_id+":"+complaint_id
			complaint_obj = my_server.get(complaint_obj_key)#we disallow users from reporting something that already exists in this list, so only 1 such item would be present - hence [0] is what we needed
			if complaint_obj:
				complaint_obj = json.loads(complaint_obj)
				
				if reporter_id in correct_reporter_ids:
					# marking the reporter's complaint object
					complaint_obj['o'] = '1'
				elif reporter_id in incorrect_reporter_ids:
					# marking the reporter's complaint object
					complaint_obj['o'] = '0'
				elif reporter_id in malicious_reporter_ids:
					# marking the reporter's complaint object
					complaint_obj['o'] = '-1'

				# set 'decided by' credentials
				complaint_obj['dun'] = defender_uname
				complaint_obj['did'] = defender_id
				my_server.set(complaint_obj_key,json.dumps(complaint_obj))# and then re-save the enriched complaint_obj

		pipeline1 = my_server.pipeline()
		for reporter_id in correct_reporter_ids:
			# logging good outcome - that's the only one which merits a +1 score (all others are zero)
			pipeline1.zadd(COMPLAINER_CORRECT_TIME_LIST,reporter_id,time_now)# sorted by latest complaint logged
			pipeline1.zincrby(COMPLAINER_CORRECT_SORTED_SET,reporter_id,amount=1)# sorted by score
		pipeline1.execute()


def get_complainer_case_history(reporter_id):
	"""
	Retrieves reports logged by reporters (along with whether they were correct, incorrect or malicious)

	Sorted by time - most recent first
	"""
	reporter_id = str(reporter_id)
	my_server = redis.Redis(connection_pool=POOL)
	complaint_obj_postfixes = my_server.zrevrange(COMPLAINTS_SUBMITTED+reporter_id,0,-1)
	complaint_obj_keys = []
	for complaint_obj_postfix in complaint_obj_postfixes:
		complaint_obj_keys.append(COMPLAINT_HIST_OBJ+reporter_id+":"+complaint_obj_postfix)
	complaint_objs = my_server.mget(*complaint_obj_keys)
	# retrieved complaint_objs are sorted by time (which is what we need)
	all_cases = []
	for case in complaint_objs:
		all_cases.append(json.loads(case))
	return all_cases
	# # return list sorted by time
	# sorted_cases = sorted(all_cases, key=lambda k: int(k['t']), reverse=True) 
	# return sorted_cases


def delete_complaint(obj_id, defender_id, obj_type):
	"""
	Wrapping up a complaint on an object (removing it from the cull-list)

	Logs defender_id against a report
	Content type is 'img', 'tx', 'pf' or 'mf'
	"""
	obj_id = str(obj_id)
	complaint = COMPLAINT+obj_type+":"+obj_id
	my_server = redis.Redis(connection_pool=POOL)
	# delete the complaint and update relevant defender's stats
	pipeline1 = my_server.pipeline()
	pipeline1.delete(PAYABLES+obj_type+":"+obj_id) #deleting the payables sorted set
	pipeline1.delete(complaint) #deleting the complaint hash
	pipeline1.zrem(COMPLAINT_LIST,complaint) #removing the complaint from the sorted set of 'all complaint'
	pipeline1.execute()
	sin = None
	if obj_type in ('img','tx'):
		sin = 'bad_submission'
	elif obj_type == 'pf':
		sin = 'bad_profile'# i.e. bad profile pic or bad nickname
	elif obj_type == 'mf':
		sin = 'bad_mehfil'# i.e bad topic or rules
	increment_defender_case_file(defender_id,sin,my_server)


def rate_limit_complainer(reporter_ids, my_server=None):
	"""
	If a reporter's report was done in jest (or maliciously), rate limit their reporting for many days
	"""
	if reporter_ids:
		my_server = my_server if my_server else redis.Redis(connection_pool=POOL)
		if len(reporter_ids) > 5:
			pipeline1 = my_server.pipeline()
			for reporter_id in reporter_ids:
				pipeline1.setex(COMPLAINING_RATE_LIMITED+reporter_id,'1',TWO_WEEKS)
			pipeline1.execute()
		else:
			for reporter_id in reporter_ids:
				my_server.setex(COMPLAINING_RATE_LIMITED+reporter_id,'1',TWO_WEEKS)


def get_content_complaints():
	"""
	Returns all current photo reports' hash names
	"""
	# Sorted by number of complaints
	return redis.Redis(connection_pool=POOL).zrevrange(COMPLAINT_LIST,0,-1)


def get_complaint_details(complaint_list):
	"""
	Given a hash_name for a content complaint, this can retrieve all the data related to that.

	Complaint hashes must be fed in list format
	"""
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	complaints_with_details = []
	for complaint in complaint_list:
		pipeline1.hgetall(complaint)
	result1 = pipeline1.execute()
	for complaint in result1:
		complaint["pl"] = json.loads(complaint["pl"])
		complaints_with_details.append(complaint)
	return complaints_with_details


def get_num_complaints():
	"""
	Retrieves num of outstanding reports for the attention of mods
	"""
	return redis.Redis(connection_pool=POOL).zcard(COMPLAINT_LIST)


##################### Maintaining public replies cache #####################


def cache_public_replies(json_payload, obj_id):
	"""
	Caching public replies under a home text
	"""
	redis.Redis(connection_pool=POOL).setex(CACHED_PUBLIC_REPLY+str(obj_id),json_payload,ONE_HOUR)


def retrieve_cached_public_replies(obj_id):
	"""
	Retrieve cached public replies
	"""
	return redis.Redis(connection_pool=POOL).get(CACHED_PUBLIC_REPLY+str(obj_id))


def invalidate_cached_public_replies(obj_id):
	"""
	Deleting cached public replies
	"""
	redis.Redis(connection_pool=POOL).delete(CACHED_PUBLIC_REPLY+str(obj_id))


#####################Authorization#####################

def account_creation_disallowed(ip):
	"""
	Do not allow the same user to create an account right away!

	Outdated: later on, replace it via 'localstorage' html5 functionality. That at least is more reliable
	"""
	my_server = redis.Redis(connection_pool=POOL)
	if my_server.exists("ip:"+str(ip)):
		return True
	else:
		return False


def account_created(ip,username):
	"""
	Save the IP of the user who just created the account
	"""
	my_server = redis.Redis(connection_pool=POOL)

	my_server.setex("ip:"+str(ip),username,FOUR_MINS)


###################### legacy redis1 functions ##############################
###################### ecomm.py  ############################################

def add_exchange_visitor(user_id):
	redis.Redis(connection_pool=POOL).sadd("ftux:"+str(user_id), '14')


def first_time_exchange_visitor(user_id):
	if redis.Redis(connection_pool=POOL).sismember("ftux:"+str(user_id),'14'):
		return False
	else:
		return True 


def add_photo_ad_visitor(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	my_server.sadd(set_name, '17')


def first_time_photo_ads_visitor(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	if my_server.sismember(set_name,'17'):
		return False
	else:
		return True     


##################### Maintaining top stars listing #####################


def set_top_stars(payload):
	"""
	Sets top stars data
	"""
	redis.Redis(connection_pool=POOL).setex(CACHED_TOP_STARS,json.dumps(payload),ONE_HOUR)


def retrieve_top_stars():
	"""
	Retrieves top stars' data
	"""
	return redis.Redis(connection_pool=POOL).get(CACHED_TOP_STARS)


################################## maint_views.py ##############################################


def get_inactives(get_100K=False, get_50K=False, get_10K=False, get_5K=False, key=None):
	my_server = redis.Redis(connection_pool=POOL)
	if not key:
		key = "inactive_users"
	if get_100K:
		remaining = get_inactive_count(server=my_server,key_name = None if key == 'inactive_users' else key)
		if remaining < 100000:
			data = my_server.zrange(key,0,-1,withscores=True)
			my_server.delete(key)
			return data, True
		else:
			data = my_server.zrange(key,0,99999,withscores=True)
			my_server.zremrangebyrank(key,0,99999)
			return data, False
	elif get_50K:
		remaining = get_inactive_count(server=my_server,key_name = None if key == 'inactive_users' else key)
		if remaining < 50000:
			data = my_server.zrange(key,0,-1,withscores=True)
			my_server.delete(key)
			return data, True
		else:
			data = my_server.zrange(key,0,49999,withscores=True)
			my_server.zremrangebyrank(key,0,49999)
			return data, False
	elif get_10K:
		remaining = get_inactive_count(server=my_server,key_name = None if key == 'inactive_users' else key)
		if remaining < 10000:
			data = my_server.zrange(key,0,-1,withscores=True)
			my_server.delete(key)
			return data, True
		else:
			data = my_server.zrange(key,0,9999,withscores=True)
			my_server.zremrangebyrank(key,0,9999)
			return data, False
	elif get_5K:
		remaining = get_inactive_count(server=my_server,key_name = None if key == 'inactive_users' else key)
		if remaining < 5000:
			data = my_server.zrange(key,0,-1,withscores=True)
			my_server.delete(key)
			return data, True
		else:
			data = my_server.zrange(key,0,4999,withscores=True)
			my_server.zremrangebyrank(key,0,4999)
			return data, False
	else:
		return my_server.zrange(key,0,-1,withscores=True)

def set_inactives(inactive_list):
	if inactive_list:
		redis.Redis(connection_pool=POOL).zadd("inactive_users", *inactive_list)


def get_inactive_count(server=None, key_name=None):
	if not server:
		server = redis.Redis(connection_pool=POOL)
	if not key_name:
		return server.zcard("inactive_users")
	else:
		return server.zcard(key_name)

def create_inactives_copy():
	"""Creates a copy of the sorted set using redis' zunionstore.

	"""
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.zunionstore("copy_of_inactive_users",["inactive_users"])

def delete_inactives_copy(delete_orig=False):
	"""Deletes the copy of the sorted set using redis' zunionstore.

	Can optionally delete the original version as well.
	"""
	my_server = redis.Redis(connection_pool=POOL)
	if delete_orig:
		pipeline1 = my_server.pipeline()
		pipeline1.delete("copy_of_inactive_users")
		pipeline1.delete("inactive_users")
		pipeline1.execute()
	else:
		my_server.delete("copy_of_inactive_users")

def bulk_sanitize_group_invite_and_membership(user_ids_list):
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	for user_id in user_ids_list:
		user_id = str(int(user_id))
		pipeline1.delete("ug:"+user_id)
		pipeline1.delete('ipg:'+user_id)
		pipeline1.delete("pir:"+user_id)
	pipeline1.execute()


################################## Direct response data retrieval ##############################################


def retrieve_shared_obj_meta_data(obj_type,obj_id, with_owner_id=False):
	"""
	Retrieves some meta data required by direct_response functionality(e.g. parent obj text, submitter, etc)

	Optimization function: this looks into redis, before falling back into Postgresql data
	"""
	final_data, via_db, is_legacy_obj = {}, False, False
	
	# it's a post of type 'tx'
	if obj_type == '3':
		my_server = redis.Redis(connection_pool=POOL)
		redis_json_blob = my_server.hget('tx:'+str(obj_id),'blob')
		if redis_json_blob:
			# the obj is cached in redis
			data = json.loads(redis_json_blob)
			final_data = {'turl':data.get('url',''),'tn':data.get('tn',''),'th':data.get('th',None),'ooid':data['si'] if with_owner_id else '',\
			'd':data['d'],'ds':data.get('ds','0'),'et':data.get('et',None)}
		else:
			# the object is not available in redis - fall back to postgresql
			via_db = True
			if with_owner_id:
				final_data = Link.objects.values('url','description','submitter','delete_status','expire_at').filter(id=obj_id)[0]
			else:
				final_data = Link.objects.values('url','description','delete_status','expire_at').filter(id=obj_id)[0]

	# it's a post of type 'img'
	elif obj_type == '4':
		my_server = redis.Redis(connection_pool=POOL)
		redis_json_blob = my_server.hget('img:'+str(obj_id),'blob')
		
		if redis_json_blob:
			# the obj is cached in redis
			data = json.loads(redis_json_blob)
			final_data = {'iu':data['iu'],'d':data['d'],'ooid':data['si'] if with_owner_id else '','ds':data.get('ds','0'),\
			'et':data.get('et',None)}
			is_legacy_obj = False if data.get('ot','') == 'g' else True# 'legacy' type objs don't have the 'ot' flag (TODO: remove this line)
		
		else:
			# the object is not available in redis - fall back to postgresql
			via_db = True
			if with_owner_id:
				data_list = Link.objects.values('image_file','description','submitter','delete_status','type_of_content','expire_at').\
				filter(id=obj_id)
				if data_list:
					final_data = data_list[0]
					if not final_data['type_of_content']:
						#legacy object - residing in 'Photo' model (so the prior lookup in 'Link' was erroneous - redo the lookup!)
						final_data = Photo.objects.values('image_file','caption','owner').filter(id=obj_id)[0]
						is_legacy_obj = True
				else:
					#retrieved data is empty - try a lookup in the Photo() table
					final_data = Photo.objects.values('image_file','caption','owner').filter(id=obj_id)[0]
					is_legacy_obj = True

			else:
				data_list = Link.objects.values('image_file','description','delete_status','type_of_content','expire_at').\
				filter(id=obj_id)
				if data_list:
					final_data = data_list[0]
					if not final_data['type_of_content']:
						#legacy object - residing in 'Photo' model (so the prior lookup in 'Link' was erroneous - redo the lookup!)
						final_data = Photo.objects.values('image_file','caption').filter(id=obj_id)[0]
						is_legacy_obj = True
				else:
					#retrieved data is empty - try a lookup in the Photo() table
					final_data = Photo.objects.values('image_file','caption').filter(id=obj_id)[0]
					is_legacy_obj = True


	return final_data, via_db, is_legacy_obj


################################## export_website_feedback.py ##############################################

def get_website_feedback():
	my_server = redis.Redis(connection_pool=POOL)
	feedback_set = "website_feedback"
	feedback_users = my_server.smembers(feedback_set)
	pipeline1 = my_server.pipeline()
	complaints_with_details = []
	for user_id in feedback_users:
		pipeline1.hgetall("wf:"+str(user_id))
	return pipeline1.execute()


##################################### Regulating fb fan page posting #####################################


def can_post_image_on_fb_fan_page():
	"""
	Regulates fan page posting

	Currently, a new trending image is added every 3 hours
	"""
	return True if not redis.Redis(connection_pool=POOL).get("bp") else False

def set_best_photo_for_fb_fan_page(photo_id):
	"""
	Sets a lock on posting new content for our fan page
	"""
	redis.Redis(connection_pool=POOL).setex("bp",photo_id,THREE_HOURS)


################################## Save temporary post data ##################################


def set_temp_post_data(user_id,data,post_type,obj_id):
	"""
	Save data to be posted for a while
	"""
	redis.Redis(connection_pool=POOL).setex(TEMP_POST_DATA+str(user_id),data,TWENTY_MINS)


def get_temp_post_data(user_id):
	"""
	get data from share for a while
	"""
	return redis.Redis(connection_pool=POOL).get(TEMP_POST_DATA+str(user_id))



