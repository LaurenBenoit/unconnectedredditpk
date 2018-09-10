import random, itertools
from verified import FEMALES
from operator import itemgetter
from datetime import datetime, timedelta
from user_sessions.models import Session
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from models import Link, Photo, PhotoComment, UserProfile, Publicreply, Reply,UserFan, ChatPic
from redis1 import get_inactives, set_inactives, get_inactive_count, create_inactives_copy, delete_inactives_copy, bulk_sanitize_group_invite_and_membership
from redis3 import insert_nick_list, get_nick_likeness, skip_outage, retrieve_all_mobile_numbers, retrieve_numbers_with_country_codes
from redis4 import save_deprecated_photo_ids_and_filenames#, report_rate_limited_conversation
from redis2 import bulk_sanitize_notifications

######################################## Notifications ########################################

@csrf_protect
def skip_outage_notif(request, *args, **kwargs):
	if request.method == "POST":
		which_user = request.POST.get("skip",None)
		origin = request.POST.get("orig",'1')
		if which_user is not None:
			skip_outage(which_user)
		if origin == '1':
				return redirect("home")
		elif origin == '2':
			return redirect("best_photo")
		elif origin == '0':
			return redirect("photo")
		else:
			return redirect("home")
	else:
		return redirect("home")


def damadam_cleanup(request, *args, **kwargs):
	context = {'referrer':request.META.get('HTTP_REFERER',None)}
	return render(request,"damadam_cleanup.html",context)

######################################## Username Sanitzation ########################################

@csrf_protect
# IN THE FUTURE, ENSURE CHANGED NICKS' PHONE NUMBERS ARE RELEASED TOO (in case those users want to verify new IDs)
def change_nicks(request,*args,**kwargs):
	"""This frees up the name space of nicks, 100K at a time.

	Nicks, once taken, are locked out of the namespace.
	This changes nicknames that aren't in use anymore to a random string.
	"""
	if request.user.username == 'mhb11':
		if request.method=='POST':
			decision = request.POST.get("dec",None)
			count = int(request.POST.get("count",None))
			if decision == 'No':
				return redirect("home")
			elif decision == 'Yes':
				inactives, last_batch = get_inactives(get_10K=True)
				id_list = map(itemgetter(1), inactives) #list of ids to deprecate
				id_len = len(id_list)
				start = count*100000
				end = start+100000-1
				rand_nums = random.sample(xrange(start,end), id_len+10)
				counter = 0
				for pk in id_list:
					# change 'i_i__' next time this is run; otherwise there will be collisions
					try:
						nick = "i_i__"+str(rand_nums[counter])
						# print "changing user id %s to %s" % (User.objects.get(id=int(pk)).username, nick)
						User.objects.filter(id=int(pk)).update(username=nick)
					except:
						pass
					counter += 1
				if last_batch:
					return render(request,'deprecate_nicks.html',{})
				else:
					return render(request,'change_nicks.html',{'count':count+1,'nicks_remaining':get_inactive_count()})
		else:
			return render(request,'change_nicks.html',{'count':1,'nicks_remaining':get_inactive_count()})



def export_nicks(request,*args,**kwargs):
	"""Exports deprecated nicks in a CSV.

	This writes all nicks, scores and ids into a CSV.
	The CSV is then exported.
	"""
	if request.user.username == 'mhb11':
		inactives = get_inactives()
		import csv
		with open('inactives.csv','wb') as f:
			wtr = csv.writer(f, delimiter=',')
			columns = "username score id".split()
			wtr.writerow(columns)
			for inactive in inactives:
				tup = inactive[0].split(":")
				username = tup[0]
				try:
					score = tup[1]
				except:
					score = None
				id_ = inactive[1]
				to_write = [username, score, id_]
				wtr.writerows([to_write])
		return render(request,'deprecate_nicks.html',{})
	else:
		return render(request,'404.html',{})



# def deprecate_nicks(request,*args,**kwargs):
# 	"""This singles out user_ids and nicks that haven't been in use over the past 3 months.

# 	It looks at criteria such as last messaging time and a ton of other things.
# 	It ensures pink stars are not included in the list.
# 	Only 'mhb11' can run this function.
# 	"""
# 	if request.user.username == 'mhb11':
# 		three_months_ago = datetime.utcnow()-timedelta(days=240	)#240
		
# 		# all user ids who last logged in more than 3 months ago
# 		all_old_ids = set(User.objects.filter(last_login__lte=three_months_ago).values_list('id',flat=True))
# 		print "step 1 complete"
# 		# user ids not found in Sessions
# 		current_users = Session.objects.filter(user__isnull=False,last_activity__gte=three_months_ago).values_list('user_id',flat=True)
# 		print "step 2a complete"
# 		logged_out_users = set(User.objects.exclude(id__in=current_users).values_list('id',flat=True))
# 		print "step 2b complete"
# 		# messaged on home more than 3 months ago
# 		current_home_messegers = Link.objects.filter(submitted_on__gte=three_months_ago).values_list('submitter_id',flat=True)
# 		print "step 3a complete"
# 		never_home_message = set(User.objects.exclude(id__in=current_home_messegers).values_list('id',flat=True))
# 		print "step 3b complete"
# 		# never submitted a publicreply
# 		current_public_repliers = Publicreply.objects.filter(submitted_on__gte=three_months_ago).values_list('submitted_by_id',flat=True)
# 		print "step 4a complete"
# 		never_publicreply = set(User.objects.exclude(id__in=current_public_repliers).values_list('id',flat=True))
# 		print "step 4b complete"
# 		# never sent a photocomment
# 		current_photo_commenters = PhotoComment.objects.filter(submitted_on__gte=three_months_ago).values_list('submitted_by_id',flat=True)
# 		print "step 5a complete"
# 		never_photocomment = set(User.objects.exclude(id__in=current_photo_commenters).values_list('id',flat=True))
# 		print "step 5b complete"
# 		# never wrote in a group
# 		current_group_writers = Reply.objects.filter(submitted_on__gte=three_months_ago).values_list('writer_id',flat=True)
# 		print "step 6a complete"
# 		never_groupreply = set(User.objects.exclude(id__in=current_group_writers).values_list('id',flat=True))
# 		print "step 6b complete"
# 		# never uploaded a photo
# 		current_photo_uploaders = Photo.objects.filter(upload_time__gte=three_months_ago).values_list('owner_id',flat=True)
# 		print "step 7a complete"
# 		never_uploaded_photo = set(User.objects.exclude(id__in=current_photo_uploaders).values_list('id',flat=True))
# 		print "step 7b complete"
# 		# never sent a chatpic
# 		current_chat_pic_users = ChatPic.objects.filter(upload_time__gte=three_months_ago).values_list('owner_id',flat=True)
# 		print "step 8a complete"
# 		never_sent_chat_pic = set(User.objects.exclude(id__in=current_chat_pic_users).values_list('id',flat=True))
# 		print "step 8b complete"
# 		# never fanned anyone
# 		# change this to never fanned ever (not in the last 3 months, because that could include people like 'mhb11' too)
# 		current_fanners = UserFan.objects.filter(fanning_time__gte=three_months_ago).values_list('fan_id',flat=True)
# 		print "step 9a complete"
# 		never_fanned = set(User.objects.exclude(id__in=current_fanners).values_list('id',flat=True))
# 		print "step 9b complete"
# 		# score is below 15000 (score requirement too high, should be lessened)
# 		less_than_15000 = set(UserProfile.objects.filter(score__lte=15000).values_list('user_id',flat=True))
# 		print "step 10 complete"
# 		# do not have active 1-on-1 private chats
# 		# TODO: never_1_on_1_chatted = 

# 		# intersection of all such ids (and not union)
# 		sets = [all_old_ids, logged_out_users, never_home_message, never_publicreply, never_photocomment, never_uploaded_photo, never_fanned, less_than_15000, \
# 		never_groupreply, never_sent_chat_pic]#, never_1_on_1_chatted]
# 		inactive = set.intersection(*sets)# passing list of sets to set.intersection()
# 		print "step 11 complete"
# 		#sanitize pink stars:
# 		pink_stars = set(User.objects.filter(username__in=FEMALES).values_list('id',flat=True))
# 		inactive = inactive - pink_stars
# 		print "step 12 complete"
# 		# populate required sorted_set in redis 1 (called 'inactive_users')
# 		inactives = []
# 		inactives_data = User.objects.select_related('userprofile').filter(id__in=inactive).values_list('username','id','userprofile__score')
# 		for inact in inactives_data:
# 			inactives.append((inact[0]+":"+str(inact[2]),inact[1]))
# 		print "step 13 complete"
# 		size = len(inactives)
# 		child1 = inactives[:size/8]
# 		child2 = inactives[size/8:size/4]
# 		child3 = inactives[size/4:(size*3)/8]
# 		child4 = inactives[(size*3)/8:size/2]
# 		child5 = inactives[size/2:(size*5)/8]
# 		child6 = inactives[(size*5)/8:(size*6)/8]
# 		child7 = inactives[(size*6)/8:(size*7)/8]
# 		child8 = inactives[(size*7)/8:]
# 		print "step 14 complete"
# 		from itertools import chain
# 		# breaking it into 8 lists avoids socket time out
# 		set_inactives([x for x in chain.from_iterable(child1)])
# 		set_inactives([x for x in chain.from_iterable(child2)])
# 		set_inactives([x for x in chain.from_iterable(child3)])
# 		set_inactives([x for x in chain.from_iterable(child4)])
# 		set_inactives([x for x in chain.from_iterable(child5)])
# 		set_inactives([x for x in chain.from_iterable(child6)])
# 		set_inactives([x for x in chain.from_iterable(child7)])
# 		set_inactives([x for x in chain.from_iterable(child8)])
# 		print "step 15 complete"
# 		return render(request,'deprecate_nicks.html',{})
# 	else:
# 		return render(request,'404.html',{})


def deprecate_nicks(request,*args,**kwargs):
	"""This singles out user_ids and nicks that haven't been in use over the past 3 months.

	It looks at criteria such as last messaging time and a ton of other things.
	It ensures pink stars are not included in the list.
	Only 'mhb11' can run this function.
	"""
	if request.user.username == 'mhb11':

		import redis
		from location import REDLOC4
		ONE_DAY = 60*60*24
		POOL = redis.ConnectionPool(connection_class=redis.UnixDomainSocketConnection, path=REDLOC4, db=0)
		my_server = redis.Redis(connection_pool=POOL)

		four_months_ago = datetime.utcnow()-timedelta(days=120)#240
		
		if my_server.exists("active_users"):
			print "step 14 from cache"
			active_users = my_server.lrange("active_users",0,-1)
			print "by passing steps 1-13\n"

		else:

			# wrote in a group recently
			if my_server.exists("group_writers"):
				current_group_writers = my_server.lrange("group_writers",0,-1)
				print "step 6 from cache"
			else:
				random_four_months_old_reply = 179000000#175550000#165000000
				current_group_writers = Reply.objects.filter(id__gte=random_four_months_old_reply).values_list('writer_id',flat=True)
				print "step 6a calculated"
				current_group_writers = list(set(current_group_writers))
				print "step 6b calculated"
				my_server.lpush("group_writers",*current_group_writers)
				my_server.expire("group_writers",ONE_DAY)
				print "... saved in redis\n"

			# uploaded a photo recently
			if my_server.exists("photo_uploaders"):
				current_photo_uploaders = my_server.lrange("photo_uploaders",0,-1)
				print "step 7 from cache"
			else:
				current_photo_uploaders = set(Photo.objects.filter(upload_time__gte=four_months_ago).values_list('owner_id',flat=True))
				print "step 7 calculated"
				my_server.lpush("photo_uploaders",*current_photo_uploaders)
				my_server.expire("photo_uploaders",ONE_DAY)
				print "... saved in redis\n"


			# sent a chatpic recently
			if my_server.exists("chatpic_uploaders"):
				current_chat_pic_users = my_server.lrange("chatpic_uploaders",0,-1)
				print "step 8 from cache"
			else:
				current_chat_pic_users = set(ChatPic.objects.filter(upload_time__gte=four_months_ago).values_list('owner_id',flat=True))
				print "step 8 calculated"
				my_server.lpush("chatpic_uploaders",*current_chat_pic_users)
				my_server.expire("chatpic_uploaders",ONE_DAY)
				print "... saved in redis\n"

			
			# fanned someone recently
			if my_server.exists("fanners"):
				current_fanners = my_server.lrange("fanners",0,-1)
				print "step 9 from cache"
			else:
				current_fanners = set(UserFan.objects.filter(fanning_time__gte=four_months_ago).values_list('fan_id',flat=True))
				print "step 9 calculated"
				my_server.lpush("fanners",*current_fanners)
				my_server.expire("fanners",ONE_DAY)
				print "... saved in redis\n"
			
			
			# score is above 500
			if my_server.exists("high_score_users"):
				more_than_500 = my_server.lrange("high_score_users",0,-1)
				print "step 10 from cache"
			else:
				more_than_500 = set(UserProfile.objects.filter(score__gte=500).values_list('user_id',flat=True))
				print "step 10 calculated"
				my_server.lpush("high_score_users",*more_than_500)
				my_server.expire("high_score_users",ONE_DAY)
				print "... saved in redis\n"


			# is a pink stars
			if my_server.exists("pink_stars"):
				pink_stars = my_server.lrange("pink_stars",0,-1)
				print "step 11 from cache"
			else:
				pink_stars = set(User.objects.filter(username__in=FEMALES).values_list('id',flat=True))
				print "step 11 calculated"
				my_server.lpush("pink_stars",*pink_stars)
				my_server.expire("pink_stars",ONE_DAY)
				print "... saved in redis\n"



			# submitted a publicreply recently
			random_four_months_old_publicreply = 115706681
			if my_server.exists("public_repliers"):
				current_public_repliers = my_server.lrange("public_repliers",0,-1)
				print "step 4 from cache"
			else:
				current_public_repliers = Publicreply.objects.filter(id__gte=random_four_months_old_publicreply).values_list('submitted_by_id',flat=True)
				print "step 4a calculated"
				current_public_repliers = list(set(current_public_repliers))
				print "step 4b calculated"
				my_server.lpush("public_repliers",*current_public_repliers)
				my_server.expire("public_repliers",ONE_DAY)
				print "... saved in redis\n"

			
			# sent a photocomment recently
			if my_server.exists("photo_commenters"):
				current_photo_commenters = my_server.lrange("photo_commenters",0,-1)
				print "step 5 from cache"
			else:
				random_four_months_old_photocomment = 53000000
				current_photo_commenters = PhotoComment.objects.filter(id__gte=random_four_months_old_photocomment).values_list('submitted_by_id',flat=True)
				print "step 5a calculated"
				current_photo_commenters = list(set(current_photo_commenters))
				print "step 5b calculated"
				my_server.lpush("photo_commenters",*current_photo_commenters)
				my_server.expire("photo_commenters",ONE_DAY)
				print "... saved in redis\n"


			# all user ids who last logged in more than 4 months ago
			if my_server.exists("latest_logins"):
				latest_logins = my_server.lrange("latest_logins",0,-1)
				print "step 1 from cache"
			else:
				latest_logins = list(set(User.objects.filter(last_login__gte=four_months_ago).values_list('id',flat=True)))
				print "step 1 calculated"
				my_server.lpush("latest_logins",*latest_logins)
				my_server.expire("latest_logins",ONE_DAY)
				print "... saved in redis\n"

			
			# latest user ids found in Sessions
			if my_server.exists("current_sessions"):
				current_sessions = my_server.lrange("current_sessions",0,-1)
				print "step 2 from cache"
			else:
				current_sessions = set(Session.objects.filter(user__isnull=False,last_activity__gte=four_months_ago).values_list('user_id',flat=True))
				print "step 2 calculated"
				my_server.lpush("current_sessions",*current_sessions)
				my_server.expire("current_sessions",ONE_DAY)
				print "... saved in redis\n"


			# messaged on home recently
			if my_server.exists("home_messegers"):
				current_home_messegers = my_server.lrange("home_messegers",0,-1)
				print "step 3 from cache"
			else:
				current_home_messegers = set(Link.objects.filter(submitted_on__gte=four_months_ago).values_list('submitter_id',flat=True))
				print "step 3 calculated"
				my_server.lpush("home_messegers",*current_home_messegers)
				my_server.expire("home_messegers",ONE_DAY)
				print "... saved in redis\n"

			

				# has active 1-on-1 private chats
				# TODO: 1_on_1_chatted = 

			# create a list of the data
			sets = [set(current_public_repliers),set(current_photo_commenters),set(latest_logins),set(current_sessions),set(current_home_messegers),\
			set(current_group_writers),set(current_photo_uploaders),set(current_chat_pic_users),set(current_fanners),set(more_than_500),set(pink_stars)]#, 1_on_1_chatted]
			print "step 12 calculated"

			# the union of all of the above gives us users that have been at least remotely active in the last 4 months
			active_users = set.union(*sets)
			print "step 13 calculated"
			my_server.lpush("active_users",*active_users)
			my_server.expire("active_users",ONE_DAY)
			print "... saved in redis\n"
		
		# all user ids
		all_users = list(User.objects.all().values_list('id',flat=True))
		all_users = (map(str, all_users))
		print "step 15 calculated\n"

		# all inactives are simply all users minus all active users
		all_inactives = set(all_users) - set(active_users)
		print "step 16 calculated"
		all_inactives = list(all_inactives)
		llen = len(all_inactives)
		list1 = all_inactives[:llen/2]
		list2 = all_inactives[llen/2:]
		my_server.lpush("all_inactives",*list1)
		my_server.lpush("all_inactives",*list2)
		my_server.expire("all_inactives",ONE_DAY)
		print "... saved in redis\n"

		

		# populate required sorted_set in redis 1 (called 'inactive_users')
		inactives = []
		inactives_data = User.objects.select_related('userprofile').filter(id__in=all_inactives).values_list('username','id','userprofile__score')
		for inact in inactives_data:
			inactives.append((inact[0]+":"+str(inact[2]),inact[1]))
		print "step 17 calculated"
		
		# inactives = list(all_inactives)
		size = len(inactives)
		child1 = inactives[:size/8]
		child2 = inactives[size/8:size/4]
		child3 = inactives[size/4:(size*3)/8]
		child4 = inactives[(size*3)/8:size/2]
		child5 = inactives[size/2:(size*5)/8]
		child6 = inactives[(size*5)/8:(size*6)/8]
		child7 = inactives[(size*6)/8:(size*7)/8]
		child8 = inactives[(size*7)/8:]
		print "step 18 calculated"
		
		from itertools import chain	
		# breaking it into 8 lists avoids socket time out
		set_inactives([x for x in chain.from_iterable(child1)])
		set_inactives([x for x in chain.from_iterable(child2)])
		set_inactives([x for x in chain.from_iterable(child3)])
		set_inactives([x for x in chain.from_iterable(child4)])
		set_inactives([x for x in chain.from_iterable(child5)])
		set_inactives([x for x in chain.from_iterable(child6)])
		set_inactives([x for x in chain.from_iterable(child7)])
		set_inactives([x for x in chain.from_iterable(child8)])
		print "step 19 calculated\n"
		print "we are done!"
		return render(request,'deprecate_nicks.html',{})
	else:
		return render(request,'404.html',{})


def insert_nicks(request,*args,**kwargs):
	"""Inserts nicks in a redis sorted set (for quick validation at the time of sign up)

	All nicknames are first retrieved from the database.
	They are then inserted, chunk-wise, into the redis sorted set.
	It's a standalone function. One only needs to block new signups before running this.
	"""
	if request.user.username == 'mhb11':
		nicknames = User.objects.values_list('username',flat=True)
		list_len = len(nicknames)
		each_slice = int(list_len/10)
		counter = 0
		slices = []
		while counter < list_len:
			slices.append((counter,counter+each_slice))
			counter += each_slice
		for sublist in slices:
			insert_nick_list(nicknames[sublist[0]:sublist[1]])
		return render(request,'nicks_populated.html',{})
	else:
		return render(request,'404.html',{})



######################################## Redis Sanitzation ########################################

@csrf_protect
def remove_inactives_notification_activity(request,*args,**kwargs):
	"""Sanitize all notification activity of inactive users from redis2.

	We will be removing the following for each inactive user:
	1) sn:<user_id> --- a sorted set containing home screen 'single notifications',
	2) ua:<user_id> --- a sorted set containing notifications for 'matka',
	3) uar:<user_id> --- a sorted set containing resorted notifications,
	4) np:<user_id>:*:* --- all notification objects associated to the user,
	5) o:*:* --- any objects that remain with 0 subscribers,
	We will do everything in chunks of 10K, so that no server timeouts are encountered.
	"""
	if request.user.username == 'mhb11':
		if request.method == "POST":
			decision = request.POST.get("dec",None)
			if decision == 'No':
				delete_inactives_copy()
				return redirect("home")
			elif decision == 'Yes':
				inactives, last_batch = get_inactives(get_5K=True, key="copy_of_inactive_users")
				id_list = map(itemgetter(1), inactives) #list of user ids
				notification_hash_deleted, sorted_sets_deleted, object_hash_deleted = bulk_sanitize_notifications(id_list)
				if last_batch:
					delete_inactives_copy(delete_orig=True)
				return render(request,'sanitize_inactives_activity.html',{'inactives_remaining':get_inactive_count(key_name="copy_of_inactive_users"),\
					'last_batch':last_batch,'notif_deleted':notification_hash_deleted,'sorted_sets_deleted':sorted_sets_deleted,\
					'objs_deleted':object_hash_deleted})
		else:
			return render(request,'sanitize_inactives_activity.html',{'inactives_remaining':create_inactives_copy()})
	else:
		return redirect("missing_page")

@csrf_protect
def remove_inactives_groups(request,*args,**kwargs):
	"""Sanitize all group invites and memberships.
	
	This is from redis 1
	"""
	if request.user.username == 'mhb11':
		if request.method == "POST":
			decision = request.POST.get("dec",None)
			if decision == 'No':
				delete_inactives_copy()
				return redirect("home")
			elif decision == 'Yes':
				inactives, last_batch = get_inactives(get_50K=True, key="copy_of_inactive_users")
				id_list = map(itemgetter(1), inactives) #list of user ids
				bulk_sanitize_group_invite_and_membership(id_list)
				if last_batch:
					delete_inactives_copy(delete_orig=True)
				return render(request,"sanitize_groups.html",{'last_batch':last_batch, \
					'inactives_remaining':get_inactive_count(key_name="copy_of_inactive_users")})
		else:
			return render(request,"sanitize_groups.html",{'inactives_remaining':create_inactives_copy()})
	else:
		return redirect("missing_page")


######################################## PSQL Sanitzation ########################################

@csrf_protect
def remove_inactive_user_sessions(request,*args,**kwargs):
	"""Sanitize all sessions of deprecated ids.

	"""
	if request.user.username == 'mhb11':
		if request.method == "POST":
			decision = request.POST.get("dec",None)
			if decision == 'No':
				delete_inactives_copy()
				return redirect("home")
			elif decision == 'Yes':
				inactives, last_batch = get_inactives(get_10K=True, key="copy_of_inactive_users")
				id_list = map(itemgetter(1), inactives) #list of user ids
				# print "Deleting %s sessions created by %s users" % (Session.objects.filter(user_id__in=id_list).count(), len(id_list))
				Session.objects.filter(user_id__in=id_list).delete()
				if last_batch:
					delete_inactives_copy(delete_orig=True)
				return render(request,'sanitize_inactive_sessions.html',{'last_batch':last_batch, \
					'inactives_remaining':get_inactive_count(key_name="copy_of_inactive_users")})
		else:
			return render(request,'sanitize_inactive_sessions.html',{'inactives_remaining':create_inactives_copy()})
	else:
		return redirect("missing_page")




# def process_filenames(list_of_filenames):
# 	"""Parse filenames and save them in redis for exporting

# 	"""
# 	for filename,photo_id in list_of_filenames:
# 		filename = filename.split('photos/')[1]


def confirm_uninteresting(photo_ids):
	"""Returns photo_ids of photos that are uninteresting

	1) Photos that have no related comments, and comment_count is 0
	2) Where the vote score was 0 (although, this could be net 0 couting positives and negatives both. Acknowledging and ignoring that)
	3) Where latest_comment and second_latest_comment were null
	"""
	############
	photo_ids_with_associated_comments = PhotoComment.objects.filter(which_photo_id__in=photo_ids).values_list('which_photo_id',flat=True)
	return list(set(photo_ids) - set(photo_ids_with_associated_comments))
	############

@csrf_protect
def remove_inactives_photos(request,*args,**kwargs):
	"""Sanitize all inactives' photos that garnered 0 comments.

	1) We get the list of inactive ids (divided into batches for performance)
	2) For each batch, find all photo ids
	3) For each photo id, mark photos that do not have a corresponding photocomment
	4) Retrieve the file name of all such photos and store them in a redis list
	"""
	if request.user.username == 'mhb11':
		if request.method == "POST":
			decision = request.POST.get("dec",None)
			if decision == 'No':
				delete_inactives_copy()
				return redirect("home")
			elif decision == 'Yes':
				inactives, last_batch = get_inactives(get_10K=True, key="copy_of_inactive_users")
				id_list = map(itemgetter(1), inactives) #list of user ids
				uninteresting_photo_ids = Photo.objects.filter(owner_id__in=id_list, comment_count=0,vote_score=0,latest_comment__isnull=True).\
				values_list('id',flat=True)
				uninteresting_photo_ids = confirm_uninteresting(uninteresting_photo_ids)
				filenames_and_ids = Photo.objects.filter(id__in=uninteresting_photo_ids).values_list('image_file','id')
				save_deprecated_photo_ids_and_filenames(filenames_and_ids)
				if last_batch:
					delete_inactives_copy(delete_orig=True)
				return render(request,"sanitize_photos.html",{'last_batch':last_batch, \
					'inactives_remaining':get_inactive_count(key_name="copy_of_inactive_users")})
		else:
			return render(request,"sanitize_photos.html",{'inactives_remaining':create_inactives_copy()})
	else:
		return redirect("missing_page")



# def remove_inactives_groups(request,*args,**kwargs):
# 	"""Sanitize all home links and publicreplies.

# 	1) We pick a date constant from over 5 months ago.
# 	2) Set all latest_reply fields to 0 among links created before 5 months ago.
# 	3) Delete all links created before 5 months ago.
# 	4) Delete all publicreplies created before 5 months ago.

#     """
#     if request.user.username == 'mhb11':
#     	if request.method == "POST":
#     		decision = request.POST.get("dec",None)
# 			if decision == 'No':
# 				delete_inactives_copy()
# 				return redirect("home")
# 			elif decision == 'Yes':
# 				inactives, last_batch = get_inactives(get_50K=True, key="copy_of_inactive_users")
# 				id_list = map(itemgetter(1), inactives) #list of user ids
# 				if last_batch:
# 					delete_inactives_copy(delete_orig=True)
# 				return render(request,"santize_groups.html",{'last_batch':last_batch, \
# 					'inactives_remaining':get_inactive_count(key_name="copy_of_inactive_users")})
#     	else:
#     		return render(request,"sanitize_groups.html",{'inactives_remaining':create_inactives_copy()})
#     else:
#     	return redirect("missing_page")

######################################## Mobile Number Sanitzation ########################################

def isolate_non_national_phone_numbers(request):
	all_numbers_and_user_ids = retrieve_all_mobile_numbers() # this produces a list of tuples
	dictionary_of_nums_and_ids = dict(all_numbers_and_user_ids)
	bogus_numbers, users = [], []
	for number, user_id in all_numbers_and_user_ids:
		users.append(int(float(user_id)))
	all_numbers = retrieve_numbers_with_country_codes(set(users))
	import ast
	for entry in all_numbers:
		for number in entry:
			number = ast.literal_eval(number)
			if number["country_prefix"] != '92':
				bogus_numbers.append(((int(float(dictionary_of_nums_and_ids[number["national_number"]]))),number["number"]))
	processed_bogus_pairs = []
	for user_id, number in bogus_numbers:
		user = User.objects.filter(id=user_id).values_list('username',flat=True)[0]
		processed_bogus_pairs.append((user,number))
	return render(request,"show_bogus_mobile_user_ids.html",{'bogus_pairs':processed_bogus_pairs,'total':len(processed_bogus_pairs)})

# ############################################### Logger ###############################################

# def rate_limit_logging_report(request):
# 	report_rate_limited_conversation()
# 	return redirect("missing_page")