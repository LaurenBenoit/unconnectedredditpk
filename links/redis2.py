import redis, time
from location import REDLOC2
# from lua_scripts import storelogin, getlatestlogins, cleanselogins, retrieveclones

'''
##########Redis Namespace##########

fans = "f:"+str(photo_owner_id) // a sorted set
group_attendance = "ga:"+str(group_id)
latest_user_ip = "lip:"+str(user_id) #latest ip of user with 'user_id'
hash_name = "np:"+str(viewer_id)+":"+str(object_type)+":"+str(object_id) #'np' is notification payload, contains notification data
hash_name = "o:"+str(object_type)+":"+str(object_id) #'o' is object, this contains link, photo, group, salat invite, video, etc.
photos_benchmark = "photos_benchmark"
sorted_set = "public_group_rankings"
recent_fans = "rf:"+photo_owner_id
user_score_hash = "us:"+str(user_id)
sorted_set = "si:"+str(viewer_id) #salat invites sent to viewer_id
sorted_set = "sn:"+str(viewer_id) #'sn' is single notification, for user with viewer_id
single_key = 't:'+str(viewer_id) #'t' stores time of last visit to unseen activity by viewer_id
sorted_set = "ua:"+str(viewer_id) #'ua' is unseen activity, for user with viewer_id
sorted_set = "uar:"+str(viewer_id) #unseen activity resorted (by whether notifs are seen or not)
user_ban = "ub:"+str(user_id)
user_presence = "up:"+str(user_id)+str(group_id)
user_presence = "up:"+str(user_id)+":"+str(group_id)
sorted_set = "whose_online_new"

###################################
'''
# changed connection from TCP port to UNIX socket
POOL = redis.ConnectionPool(connection_class=redis.UnixDomainSocketConnection, path=REDLOC2, db=0)

# 5,000,000,000 is most important priority wise
PRIORITY={'priv_mehfil':5000000000,'home_jawab':4000000000,'photo_tabsra':3000000000,'public_mehfil':2000000000,'photo_fan':2000000000,'namaz_invite':1000000000}

# Weightage of 'seen' status, used to find notification count for each user
SEEN={True:2000000000,False:4000000000}

FUTURE_EPOCH = 1609406042 #Human time (GMT): Thu, 31 Dec 2020 09:14:02 GMT

TEN_MINS = 10*60
ONE_HOUR = 60*60
ONE_DAY = 1*24*60*60
THREE_DAYS = 3*24*60*60
HALF_LIFE = THREE_DAYS #used in ranking public groups

# unseen_activity size limit (per user)
UA_LIMIT = 70
UA_TO_TRIM = 20

#######################Notifications#######################

'''
OBJECT types:
	link publicreply = '2'
	photo comment = '0'
	group chat = '3'
	salat invites = '4'
	photo upload = '1' #for fans only
'''

def delete_salat_notification(notif_name, hash_name, viewer_id):
	my_server = redis.Redis(connection_pool=POOL)
	my_server.zrem("sn:"+str(viewer_id),notif_name)
	my_server.delete(hash_name)
	my_server.delete(notif_name)

def retrieve_object_data(obj_id,obj_type):
	my_server = redis.Redis(connection_pool=POOL)
	obj_name = "o:"+obj_type+":"+str(obj_id)
	return my_server.hgetall(obj_name)

# populates the single notification on the screen
def retrieve_latest_notification(viewer_id):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "sn:"+str(viewer_id) # this contains the 'single notifications' of the user
	notif = my_server.zrange(sorted_set,-1,-1)
	if notif:
		notification = my_server.hgetall(notif[0])
		parent_object = my_server.hgetall(notification['c'])
		combined = dict(notification,**parent_object)
		return notif[0],notification['c'],combined
	else:
		return None, None, None

# populates the 'matka'
def retrieve_unseen_notifications(viewer_id):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "ua:"+str(viewer_id) #the sorted set containing 'unseen activity' notifications
	if my_server.zcard(sorted_set):
		return my_server.zrevrange(sorted_set, 0, -1)
	else:
		return []

# populates the 'matka'
def retrieve_unseen_activity(notifications):
	my_server = redis.Redis(connection_pool=POOL)
	list_of_dictionaries = []
	pipeline1 = my_server.pipeline()
	for notification in notifications:
		notif = pipeline1.hgetall(notification)
		associated_obj = pipeline1.hgetall("o:"+notification.split(":",2)[2])
	result = pipeline1.execute()
	i = 0
	while i < len(result):
		if 'c' in result[i] and 'ot' in result[i+1]:
			combined = dict(result[i],**result[i+1])
			list_of_dictionaries.append(combined)
		i += 2
	return list_of_dictionaries

def bulk_update_salat_notifications(viewer_id=None, starting_time=None, seen=None, updated_at=None):
	my_server = redis.Redis(connection_pool=POOL)
	salat_invites_to_update = my_server.zrangebyscore("si:"+str(viewer_id),starting_time,'+inf')
	my_server.zremrangebyscore("si:"+str(viewer_id),starting_time,'+inf')
	for salat_invite in salat_invites_to_update:
		hash_name = "np:"+str(viewer_id)+":4:"+str(salat_invite)
		my_server.hmset(hash_name,{"s":seen,"u":updated_at})
		my_server.zrem("sn:"+str(viewer_id),hash_name)

def viewer_salat_notifications(viewer_id=None, object_id=None, time=None):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "si:"+str(viewer_id) #salat invites sent to viewer_id
	my_server.zadd(sorted_set,object_id,time)

def bulk_create_photo_notifications_for_fans(viewer_id_list=None,object_id=None,seen=None,updated_at=None,unseen_activity=None):
	my_server = redis.Redis(connection_pool=POOL)
	increment = 0
	parent_object = "o:0:"+str(object_id) #points to the parent object each notification is related to
	pipeline1 = my_server.pipeline()
	for viewer_id in viewer_id_list:
		notification = "np:"+str(viewer_id)+":0:"+str(object_id)
		mapping = { 's':seen,'u':updated_at,'c':parent_object,'f':True,'nc':True }#'f' means for_fans, 'nc' means no_comment
		pipeline1.hmset(notification, mapping)
		#updating single_notif sorted set
		sorted_set = "sn:"+str(viewer_id) #'sn' is single notification, for user with viewer_id
		score = PRIORITY['photo_fan']+int(updated_at)
		pipeline1.zadd(sorted_set, notification, score) #where updated_at is the score
		#updating unseen_acitivity sorted set, if warranted
		if unseen_activity:
			increment += 1
			sorted_set = "ua:"+str(viewer_id) #'ua' is unseen activity, for user with viewer_id
			pipeline1.zadd(sorted_set, notification, updated_at) #where updated_at is the score
			sorted_set2 = "uar:"+str(viewer_id) #'uar' is unseen activity resorted (by whether notifs are seen or not)
			pipeline1.zadd(sorted_set2,notification,updated_at+SEEN[seen])
	pipeline1.hincrby(parent_object, 'n', amount=increment)
	pipeline1.execute()


# this does not update notifications for users whose notification object was deleted
def bulk_update_notifications(viewer_id_list=None, object_id=None, object_type=None, seen=None, updated_at=None, single_notif=None, \
	unseen_activity=None, priority=None):
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	for viewer_id in viewer_id_list:
		hash_name = "np:"+str(viewer_id)+":"+str(object_type)+":"+str(object_id)
		pipeline1.exists(hash_name)	#list of all hashes that exist
	result1 = pipeline1.execute()
	count = 0
	pipeline2 = my_server.pipeline()
	for exist in result1:
		hash_name = "np:"+str(viewer_id_list[count])+":"+str(object_type)+":"+str(object_id)
		if exist:
			pipeline2.hset(hash_name, "s", seen) #updating 'seen'
			if updated_at:
				pipeline2.hset(hash_name, "u", updated_at)
			if single_notif is not None:
				sorted_set = "sn:"+str(viewer_id_list[count]) #'sn' is single notification, for user with viewer_id
				if single_notif:
					score = PRIORITY[priority]+int(time.time())
					pipeline2.zadd(sorted_set, hash_name, score)
				else:
					pipeline2.zrem(sorted_set, hash_name)
			if unseen_activity is not None:
				sorted_set = "ua:"+str(viewer_id_list[count]) #'ua' is unseen activity, for user with viewer_id
				sorted_set2 = "uar:"+str(viewer_id_list[count]) #'uar' is unseen activity resorted (by whether notifs are seen or not)
				if unseen_activity:
					#all updates will be bumped in ua: anyway, so no need for 'bump_ua' flag here
					epochtime = time.time()
					pipeline2.zadd(sorted_set, hash_name, epochtime)
					pipeline2.zadd(sorted_set2,hash_name,epochtime+SEEN[seen])
				else:
					pipeline2.zrem(sorted_set, hash_name)
					pipeline2.zrem(sorted_set2, hash_name)
		count += 1
	pipeline2.execute()


# this does not update a notification whose notification object was deleted
def update_notification(viewer_id=None, object_id=None, object_type=None, seen=None, updated_at=None, unseen_activity=None, \
	single_notif=None, priority=None, bump_ua=None, no_comment=None):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "np:"+str(viewer_id)+":"+str(object_type)+":"+str(object_id)
	if my_server.exists(hash_name):
		my_server.hset(hash_name,"s", seen) #updating 'seen'
		if no_comment is not True:
			my_server.hset(hash_name,"nc",no_comment)
		if updated_at:
			my_server.hset(hash_name, "u", updated_at) #updating 'updated_at' only if value is available
		if single_notif is not None:
			sorted_set = "sn:"+str(viewer_id) #'sn' is single notification, for user with viewer_id
			if single_notif:
				score = PRIORITY[priority]+int(time.time())
				my_server.zadd(sorted_set, hash_name, score)
			else:
				my_server.zrem(sorted_set, hash_name)
		if unseen_activity is not None:
			sorted_set = "ua:"+str(viewer_id) #'ua' is unseen activity, for user with viewer_id
			sorted_set2 = "uar:"+str(viewer_id) #'uar' is unseen activity resorted (by whether notifs are seen or not)
			epochtime = time.time()
			if bump_ua and unseen_activity:
				my_server.zadd(sorted_set, hash_name, epochtime)
				my_server.zadd(sorted_set2, hash_name, epochtime+SEEN[seen])
			elif unseen_activity:
				# only zadd if the member doesn't exist
				if my_server.zscore(sorted_set,hash_name) is None:
					my_server.zadd(sorted_set,hash_name, epochtime)
					my_server.zadd(sorted_set2, hash_name, epochtime+SEEN[seen])
				else:
					#i.e. don't bump up in unseen_activity by just 'viewing', but adjust notification counter
					my_server.zadd(sorted_set2, hash_name, epochtime+SEEN[seen])
					# pass
			else:	
				my_server.zrem(sorted_set, hash_name)
				my_server.zrem(sorted_set2, hash_name)
		return True
	else:
		return False

def create_notification(viewer_id=None, object_id=None, object_type=None, seen=None, updated_at=None, unseen_activity=None, \
	single_notif=None, priority=None, no_comment=None):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "np:"+str(viewer_id)+":"+str(object_type)+":"+str(object_id)
	composite_id = "o:"+str(object_type)+":"+str(object_id) #points to the parent object this notification is related to
	if my_server.exists(hash_name):
		return False
	else:
		mapping = { 's':seen,'u':updated_at,'c':composite_id,'nc':no_comment }
		my_server.hmset(hash_name, mapping)
		#updating unseen_acitivity sorted set
		if unseen_activity:
			sorted_set = "ua:"+str(viewer_id) #'ua' is unseen activity, for user with viewer_id
			sorted_set2 = "uar:"+str(viewer_id) #'uar' is unseen activity resorted (by whether notifs are seen or not)
			my_server.zadd(sorted_set, hash_name, updated_at) #where updated_at is the score
			my_server.zadd(sorted_set2, hash_name, updated_at+SEEN[seen])
			my_server.hincrby(composite_id, 'n', amount=1) #increment number_of_subscribers in parent_object. This is equivalent to number of unseen_activities the reply shows up in!
		#updating single_notif sorted set
		if single_notif:
			sorted_set = "sn:"+str(viewer_id) #'sn' is single notification, for user with viewer_id
			score = PRIORITY[priority]+int(updated_at)
			my_server.zadd(sorted_set, hash_name, score) #where updated_at is the score
		if my_server.zcard("ua:"+str(viewer_id)) > UA_LIMIT:
			from tasks import delete_notifications
			delete_notifications.delay(viewer_id)
		return True

def update_object(object_id=None, object_type=None, lt_res_time=None,lt_res_avurl=None,lt_res_sub_name=None,lt_res_text=None,\
	res_count=None, vote_score=None,reply_photourl=None, object_desc=None, just_vote=None, lt_res_wid=None):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "o:"+str(object_type)+":"+str(object_id) #'o' is object, this contains link, photo, group, salat invite, video, etc.
	if object_type == '2':
		mapping={'lrti':lt_res_time,'lrau':lt_res_avurl,'lrsn':lt_res_sub_name,'lrtx':lt_res_text,'r':res_count, 'lrwi':lt_res_wid}
	elif object_type == '3':
		mapping={'lrti':lt_res_time,'lrau':lt_res_avurl,'lrsn':lt_res_sub_name,'lrtx':lt_res_text,'rp':reply_photourl,\
		'od':object_desc, 'lrwi':lt_res_wid}
	elif object_type == '0':
		if just_vote is True:
			mapping={'v':vote_score}
		else:
			mapping={'lrti':lt_res_time,'lrau':lt_res_avurl,'lrsn':lt_res_sub_name,'lrtx':lt_res_text,'r':res_count,\
			'v':vote_score, 'lrwi':lt_res_wid}
	my_server.hmset(hash_name, mapping)

def create_object(object_id=None, object_type=None, object_owner_avurl=None,object_owner_id=None,object_owner_name=None,\
	object_desc=None,lt_res_time=None,lt_res_avurl=None,lt_res_sub_name=None,lt_res_text=None,is_welc=None,res_count=None,\
	is_thnks=None, photourl=None, reply_photourl=None, group_privacy=None,vote_score=None, slug=None, lt_res_wid=None):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "o:"+str(object_type)+":"+str(object_id) #'o' is object, this contains link, photo, group, salat invite, video, etc
	# print hash_name
	if my_server.exists(hash_name):
		return False
	else:
		if object_type == '2':
			#creating link object, with latest_response
			mapping={'oi':object_id,'ot':object_type,'ooa':object_owner_avurl,'ooi':object_owner_id,'oon':object_owner_name,\
			'od':object_desc,'lrti':lt_res_time,'lrau':lt_res_avurl,'lrsn':lt_res_sub_name,'lrtx':lt_res_text,'w':is_welc,\
			'r':res_count,'lrwi':lt_res_wid}
		elif object_type == '3':
			#creating group chat object, with latest_response
			mapping = {'oi':object_id, 'ot':object_type,'ooi':object_owner_id,'od':object_desc,'lrti':lt_res_time,\
			'lrau':lt_res_avurl,'lrsn':lt_res_sub_name,'lrtx':lt_res_text,'rp':reply_photourl,'g':group_privacy,'l':slug,\
			'lrwi':lt_res_wid}
		elif object_type == '0':
			#creating photo object, with latest_response
			mapping = {'oi':object_id, 'ot':object_type, 'p':photourl, 'od':object_desc, 'ooa':object_owner_avurl,\
			'ooi':object_owner_id,'oon':object_owner_name,'v':vote_score, 'r':res_count,'lrti':lt_res_time, \
			'lrau':lt_res_avurl,'lrsn':lt_res_sub_name,'lrtx':lt_res_text,'lrwi':lt_res_wid}
		elif object_type == '4':
			#creating salat_invite object
			mapping = {'oi':object_id,'ot':object_type,'oon':object_owner_name,'ooa':object_owner_avurl,'od':object_desc,\
			'ooi':object_owner_id}
		elif object_type == '1':
			#photo uploaded for fans. Fed from tasks.bulk_create_notifications()
			mapping = {'oi':object_id,'ot':object_type,'ooi':object_owner_id,'p':photourl,'v':vote_score,'l':slug,'t':is_thnks,\
			'r':res_count,'oon':object_owner_name, 'od':object_desc}
		elif object_type == '5':
			#video object
			mapping = {}
		my_server.hmset(hash_name, mapping)
		return True

# find whether a reply is seen or unseen (used in groups page)
def get_replies_with_seen(group_replies=None,viewer_id=None, object_type=None):
	my_server = redis.Redis(connection_pool=POOL)
	replies_list = []
	pipeline1 = my_server.pipeline()
	for reply in group_replies:
		hash_name = "np:"+str(viewer_id)+":"+str(object_type)+":"+str(reply["which_group"])
		pipeline1.hget(hash_name,'s')
	result1 = pipeline1.execute()
	count = 0
	for is_seen in result1:
		replies_list.append((group_replies[count],is_seen))
		count += 1
	return replies_list

######################################## Sanitization functions ########################################

def remove_erroneous_notif(notif_name, user_id):
	"""
	Removes notification that does have associated object

	This way the notification feed of users is not blocked
	"""
	my_server = redis.Redis(connection_pool=POOL)
	user_id = str(user_id)
	sorted_set = "sn:"+user_id
	unseen_activity = "ua:"+user_id
	unseen_activity_resorted = "uar:"+user_id #'uar' is unseen activity resorted (by whether notifs are seen or not)
	pipeline1 = my_server.pipeline()
	pipeline1.zrem(sorted_set, notif_name)
	pipeline1.zrem(unseen_activity, notif_name)
	pipeline1.zrem(unseen_activity_resorted, notif_name)
	pipeline1.execute()
	my_server.delete(notif_name)


def remove_notification_of_banned_user(target_id, object_id, object_type):
	my_server = redis.Redis(connection_pool=POOL)
	target_id = str(target_id)
	notification = "np:"+target_id+":"+object_type+":"+object_id
	################################################################################
	sorted_set = "sn:"+target_id
	unseen_activity = "ua:"+target_id
	unseen_activity_resorted = "uar:"+target_id #'uar' is unseen activity resorted (by whether notifs are seen or not)
	pipeline1 = my_server.pipeline()
	pipeline1.zrem(sorted_set, notification)
	pipeline1.zrem(unseen_activity, notification)
	pipeline1.zrem(unseen_activity_resorted, notification)
	pipeline1.execute()
	my_server.delete(notification)

def remove_group_object(group_id):
	my_server = redis.Redis(connection_pool=POOL)
	group_object = "o:3:"+str(group_id)
	my_server.delete(group_object)

def remove_group_notification(user_id=None,group_id=None):
	my_server = redis.Redis(connection_pool=POOL)
	unseen_activity = "ua:"+str(user_id)
	unseen_activity_resorted = "uar:"+str(user_id) #'uar' is unseen activity resorted (by whether notifs are seen or not)
	single_notif = "sn:"+str(user_id)
	notification = "np:"+str(user_id)+":3:"+str(group_id)
	parent_object = "o:3:"+str(group_id)
	my_server.zrem(unseen_activity, notification)			#not worked
	my_server.zrem(unseen_activity_resorted, notification)  #not worked
	my_server.zrem(single_notif, notification)				#not worked
	my_server.delete(notification)							#WORKED
	num_subscribers = my_server.hincrby(parent_object, 'n', amount=-1)

def clean_expired_notifications(viewer_id):
	my_server = redis.Redis(connection_pool=POOL)
	unseen_activity = "ua:"+str(viewer_id)
	unseen_activity_resorted = "uar:"+str(viewer_id) #'uar' is unseen activity resorted (by whether notifs are seen or not)
	single_notif = "sn:"+str(viewer_id)
	notif_to_del = my_server.zrevrange(unseen_activity,(UA_LIMIT-UA_TO_TRIM),-1)
	if notif_to_del:
		# sanitize the ua: sorted set, and uar: sorted set
		my_server.zrem(unseen_activity,*notif_to_del)
		my_server.zrem(unseen_activity_resorted,*notif_to_del)
		#sanitize the sn: sorted set
		my_server.zrem(single_notif,*notif_to_del)
		# deleting actual notification objects
		pipeline1 = my_server.pipeline()
		for notif in notif_to_del:
			pipeline1.delete(notif)							
		pipeline1.execute()
		# decrementing subscriber counts
		pipeline2 = my_server.pipeline()
		for notif in notif_to_del:
			object_hash="o:"+notif.split(":",2)[2]
			num_of_subscribers = pipeline2.hincrby(object_hash,"n",amount=-1)
		result2 = pipeline2.execute()
		count = 0
		# deleting objects with no subscriptions
		pipeline3 = my_server.pipeline()
		for result in result2:
			if result < 1:
				#delete the object hash
				object_hash = "o:"+notif_to_del[count].split(":",2)[2]
				pipeline3.delete(object_hash)
			count += 1
		result3 = pipeline3.execute()


def bulk_sanitize_notifications(inactive_user_ids):
	"""Sanitize all notification acitivity of inactive users.

	This is a helper function for remove_inactives_notification_activity()
	We will be removing the following for each inactive user:
	1) sn:<user_id> --- a sorted set containing home screen 'single notifications',
	2) ua:<user_id> --- a sorted set containing notifications for 'matka',
	3) uar:<user_id> --- a sorted set containing resorted notifications,
	4) np:<user_id>:*:* --- all notification objects associated to the user,
	5) o:*:* --- any objects that remain with 0 subscribers,
	We will do everything in chunks of 10K, so that no server timeouts are encountered.
	"""
	if inactive_user_ids:
		from itertools import chain
		my_server = redis.Redis(connection_pool=POOL)
		#####################################################
		ids_to_process = []
		for user_id in inactive_user_ids:
			try:
				ids_to_process.append(str(int(user_id)))
			except:
				pass
		#####################################################
		# get all notification objects to delete
		pipeline1 = my_server.pipeline()
		for user_id in ids_to_process:
			pipeline1.zrange("sn:"+user_id, 0, -1)
			pipeline1.zrange("ua:"+user_id, 0, -1)
		all_notifications_to_delete = list(set(chain.from_iterable(pipeline1.execute())))
		#####################################################
		# get all sorted sets to delete
		all_sorted_sets_to_delete = []
		for user_id in ids_to_process:
			all_sorted_sets_to_delete.append("sn:"+user_id)
			all_sorted_sets_to_delete.append("ua:"+user_id)
			all_sorted_sets_to_delete.append("uar:"+user_id)
		#####################################################
		# delete all notification objects and sorted sets
		pipeline2 = my_server.pipeline()
		for key_name in all_notifications_to_delete+all_sorted_sets_to_delete:
			pipeline2.delete(key_name)
		pipeline2.execute()
		#####################################################
		# decrement all related objects
		if all_notifications_to_delete:
			pipeline3 = my_server.pipeline()
			for notif in all_notifications_to_delete:
				object_hash="o:"+notif.split(":",2)[2]
				pipeline3.hincrby(object_hash,"n",amount=-1)
			pipeline3.execute()
			#####################################################
			# delete all objects with no subscribers
			objects_to_review = []
			for notif in all_notifications_to_delete:
				object_hash="o:"+notif.split(":",2)[2]
				objects_to_review.append(object_hash)
			objects_to_review = list(set(objects_to_review))
			pipeline4 = my_server.pipeline()
			for obj in objects_to_review:
				pipeline4.hget(obj,'n')
			subscribers = pipeline4.execute()
			count, objects_deleted= 0, 0
			pipeline5 = my_server.pipeline()
			for obj in objects_to_review:
				if subscribers[count] and int(subscribers[count]) < 1:
					objects_deleted += 1
					pipeline5.delete(obj)
				count += 1
			pipeline5.execute()
			return len(all_notifications_to_delete), len(all_sorted_sets_to_delete), objects_deleted
		else:
			return 0, len(all_sorted_sets_to_delete), 0
	else:
		return 0, 0, 0


def prev_unseen_activity_visit(viewer_id):
	my_server = redis.Redis(connection_pool=POOL)
	last_visit = 't:'+str(viewer_id)
	now = time.time()+SEEN[False]
	prev_time = my_server.getset(last_visit,now)
	if prev_time:
		return prev_time
	else:
		return now

def get_notif_count(viewer_id):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "uar:"+str(viewer_id) #'uar' is unseen activity resorted (by whether notifs are seen or not)
	last_visit = 't:'+str(viewer_id)
	last_visit_time = my_server.get(last_visit) #O(1)
	count = my_server.zcount(sorted_set,'('+str(last_visit_time),'+inf') #O(log(N))
	return count

#####################Public Group Rankings#####################

#get public group's last 15 mins attendance

def get_attendance(group_id):
	my_server = redis.Redis(connection_pool=POOL)
	group_attendance = "ga:"+str(group_id)
	fifteen_mins_ago = time.time() - (15*60)
	return my_server.zrangebyscore(group_attendance, fifteen_mins_ago, '+inf')

#del public group's attendance register

def del_attendance(group_id):
	my_server = redis.Redis(connection_pool=POOL)
	group_attendance = "ga:"+str(group_id)
	my_server.delete(group_attendance)

#save attendance history for each public group

def public_group_attendance(group_id,user_id):
	my_server = redis.Redis(connection_pool=POOL)
	group_attendance = "ga:"+str(group_id)
	my_server.zadd(group_attendance,user_id,time.time())

# sanitize group from rankings if group owner wants to delete it

# def del_from_rankings(group_id):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	my_server.zrem("public_group_rankings", group_id)

#expire bottom feeders among top public groups

# def expire_top_groups():
# 	my_server = redis.Redis(connection_pool=POOL)
# 	limit = 1000
# 	size = my_server.zcard("public_group_rankings")
# 	if size > limit:
# 		my_server.zremrangebyrank("public_group_rankings", 0, (size-limit-1))

#get public group rankings

# def public_group_ranking():
# 	my_server = redis.Redis(connection_pool=POOL)
# 	sorted_set = "public_group_rankings"
# 	return my_server.zrevrange(sorted_set,0,100,withscores=True) # returning highest 100 groups

#each reply or refresh in a group means the group is voted up!

# def public_group_vote_incr(group_id,priority):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	sorted_set = "public_group_rankings"
# 	increment_amount = 2**((time.time()-FUTURE_EPOCH)/HALF_LIFE) # <---- replace in 4 years from 10th Dec, 2016!
# 	increment_amount = increment_amount * priority #differentiate between refresh and reply, etc.
# 	my_server.zincrby(name=sorted_set, value=group_id,amount=increment_amount)

#####################Private Group Presence#####################

#saves the user's latest presence, to be used to show green, orange or grey blob
def save_user_presence(user_id,group_id,epochtime):
	my_server = redis.Redis(connection_pool=POOL)
	my_server.setex("up:"+str(user_id)+":"+str(group_id),epochtime,100)

#gets the latest presence for all users participating in the most recent 25 replies
def get_latest_presence(group_id, user_id_list):
	my_server = redis.Redis(connection_pool=POOL)
	pres_dict={}
	pipeline1 = my_server.pipeline()
	try:
		for user_id in user_id_list:
			user_presence = "up:"+str(user_id)+":"+str(group_id)
			time_since_last_viewing = pipeline1.get(user_presence) #time since last viewing
		result1 = pipeline1.execute()
		time_now, count = time.time(), 0
		for user_id in user_id_list:
			try:
				pres_dict[user_id] = time_now - float(result1[count])
			except:
				pres_dict[user_id] = 100.0
			count += 1
	except:
		pass
	return pres_dict

#######################Photo Fans#######################

def remove_from_photo_owner_activity(photo_owner_id,fan_id):
	my_server = redis.Redis(connection_pool=POOL)
	photo_owner_id = str(photo_owner_id)
	pipeline1 = my_server.pipeline()
	pipeline1.zrem("f:"+photo_owner_id,fan_id)
	pipeline1.zrem("rf:"+photo_owner_id,fan_id)
	pipeline1.execute()

def add_to_photo_owner_activity(photo_owner_id,fan_id,new=None):
	my_server = redis.Redis(connection_pool=POOL)
	photo_owner_id = str(photo_owner_id)
	fans = "f:"+photo_owner_id # after 30 days, remove .exists() query from tasks.py's photo_tasks function
	time_now = time.time()
	my_server.zadd(fans,fan_id,time_now)
	if new:
		my_server.zadd("rf:"+photo_owner_id,fan_id, time_now)

def get_active_fans(photo_owner_id, num_of_fans_to_notify):
	my_server = redis.Redis(connection_pool=POOL)
	fans = "f:"+str(photo_owner_id)
	if num_of_fans_to_notify:
		return my_server.zrevrange(fans,0,(num_of_fans_to_notify-1))
	else:
		return None

def is_fan(photo_owner_id, fan_id):
	my_server = redis.Redis(connection_pool=POOL)
	fans = "f:"+str(photo_owner_id)
	if my_server.zscore(fans,fan_id):
		return True
	else:
		return False

def get_all_fans(photo_owner_id):
	my_server = redis.Redis(connection_pool=POOL)
	fans = "f:"+str(photo_owner_id)
	return my_server.zrevrange(fans,0,-1), my_server.zcard(fans), get_recent_fans(photo_owner_id,server=my_server)

def get_recent_fans(photo_owner_id, server=None):
	if not server:
		server = redis.Redis(connection_pool=POOL)
	photo_owner_id = str(photo_owner_id)
	recent_fans = "rf:"+photo_owner_id
	server.zremrangebyscore(recent_fans,'-inf',time.time()-ONE_DAY)
	return server.zrange(recent_fans,0,-1), server.zcard(recent_fans)

def get_photo_fan_count(photo_owner_id):
	my_server = redis.Redis(connection_pool=POOL)
	photo_owner_id = str(photo_owner_id)
	fans = "f:"+photo_owner_id
	return my_server.zcard(fans), get_recent_photo_fan_count(photo_owner_id,my_server)

def get_recent_photo_fan_count(photo_owner_id,server=None):
	if not server:
		server = redis.Redis(connection_pool=POOL)
	server.zremrangebyscore("rf:"+photo_owner_id,'-inf',time.time()-ONE_DAY)
	return server.zcard("rf:"+photo_owner_id)

def get_fan_counts_in_bulk(user_ids):
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	for user_id in user_ids:
		pipeline1.zcard("f:"+user_id)
	result = pipeline1.execute()
	fan_counts = {}
	counter = 0
	for user_id in user_ids:
		fan_counts[user_id] = result[counter]
		counter += 1
	return fan_counts 

#######################Photos Benchmarking#######################

def set_benchmark(benchmark):
	my_server = redis.Redis(connection_pool=POOL)
	photos_benchmark = "photos_benchmark"
	my_server.delete(photos_benchmark)
	my_server.zadd(photos_benchmark,*benchmark)

def set_uploader_score(user_id,benchmark_score):
	my_server = redis.Redis(connection_pool=POOL)
	user_score_hash = "us:"+str(user_id)
	mapping = { 'b':benchmark_score }
	my_server.hmset(user_score_hash, mapping)

def get_uploader_percentile(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	user_score_hash = "us:"+str(user_id) 
	user_score = my_server.hget(user_score_hash,'b')# 1.0
	try:
		value = my_server.zrevrangebyscore('photos_benchmark','('+str(user_score), '-inf', start=0, num=1)
		if value:
			rank = my_server.zrank('photos_benchmark',value[0])+1 #added 1 because rank is 0 based
			cardinality = my_server.zcard('photos_benchmark')
			# the uploader beat the following percentage of users:
			percentile = rank/(cardinality*1.0)
		else:
			percentile = 0
	except:
		percentile = 0
	return percentile

def get_top_100():
	my_server = redis.Redis(connection_pool=POOL)
	photos_benchmark = "photos_benchmark"
	return my_server.zrevrange(photos_benchmark,0,99)