import time, uuid
import json as json_backup
import ujson as json
from django.db.models import Q
from django.http import Http404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import cache_control
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.core.urlresolvers import reverse_lazy, reverse
from django.shortcuts import redirect, render
from django.contrib.auth.models import User
from models import UserFan, Link
from redis6 import human_readable_time
from views import get_page_obj, get_indices
from redirection_views import return_to_content
from direct_response_forms import DirectResponseForm
from redis3 import is_already_banned, is_mobile_verified
from page_controls import FOLLOWERS_PER_PAGE, FOLLOWING_PER_PAGE, ITEMS_PER_PAGE
from views import get_indices, retrieve_user_env, format_post_times, get_addendum
from redis4 import retrieve_uname, retrieve_user_id, set_text_input_key, retrieve_avurl
from redis7 import check_content_and_voting_ban, retrieve_obj_feed, retrieve_last_vote_time, retrieve_recent_votes,get_all_image_star_ids,\
is_image_star, in_defenders, retrieve_top_trenders
from redis2 import check_if_follower, add_follower, remove_follower, get_custom_feed, retrieve_custom_feed_index, retrieve_follower_data, \
retrieve_following_ids,is_potential_follower_rate_limited, rate_limit_removed_follower,rate_limit_unfollower, cache_user_feed_history, \
retrieve_cached_user_feed_history, remove_single_post_from_custom_feed, invalidate_cached_user_feed_history, update_user_activity_event_time,\
get_all_follower_count, get_user_activity_event_time, add_last_fanout_to_feed, get_for_me_seen_time, retrieve_and_cache_new_followers_notif, \
set_user_last_seen, filter_following, retrieve_cached_new_follower_notif#get_verified_follower_count, logging_remove_data, logging_follow_data
from score import MAX_HOME_REPLY_SIZE, REMOVAL_RATE_LIMIT_TIME
from redis9 import retrieve_latest_direct_reply
from links.templatetags import future_time
from score import SEGMENT_STARTING_USER_ID
from templatetags.s3 import get_s3_object
from utilities import convert_to_epoch
from tasks import log_user_activity
from colors import COLOR_GRADIENTS
from redis7 import get_obj_data


ONE_MONTH = 2592000# seconds in 1 month


def custom_feed_redirect(request, obj_hash=None):
	"""
	Used to redirect to specific spot in the user's subscriber feed (e.g. after writing something, liking etc)
	"""
	index = retrieve_custom_feed_index(request.user.id, obj_hash)
	addendum = '?page=1#section0' if index is None else get_addendum(index, ITEMS_PER_PAGE, only_addendum=True)
	return redirect(reverse_lazy('for_me')+addendum)


def custom_feed_page(request):
	"""
	Displays posts by 'stars' the user is following
	"""
	own_id = request.user.id
	time_now = time.time()
	is_mob_verified = request.mobile_verified
	#############################################################################
	# guaging whether to show a 'new followers' notification at the top

	# Step 1) Get cached notification of how many 'new followers' followed this user
	cached_notif = retrieve_cached_new_follower_notif(own_id)
	# Step 2) Use the cached notif
	if cached_notif:
		data = cached_notif.partition(":")
		new_count, last_seen = str(data[0]), float(data[2])
	# Step 3) the cached notif doesn't exist, check if there are new followers at this point that can be shown in a notif
	else:
		new_count, last_seen = retrieve_and_cache_new_followers_notif(own_id)
	#############################################################################
	page_num = request.GET.get('page', '1')
	own_name = retrieve_uname(own_id, decode=True)
	start_index, end_index = get_indices(page_num, ITEMS_PER_PAGE)
	obj_tup_list, list_total_size = get_custom_feed(own_id, time_now, start_idx=start_index, end_idx=end_index)
	num_pages = list_total_size/ITEMS_PER_PAGE
	max_pages = num_pages if list_total_size % ITEMS_PER_PAGE == 0 else (num_pages+1)
	page_num = int(page_num)
	obj_list = [obj_hash for (obj_hash,time_of_entry_in_user_feed) in obj_tup_list]
	list_of_dictionaries = retrieve_obj_feed(obj_list, with_colors=True)

	#######################
	if list_of_dictionaries:
		
		list_size = len(list_of_dictionaries)

		# should be done in here, since the 't' information is lost when format_post_times() is run
		try:
			oldest_post_time = list_of_dictionaries[-1]['t']
		except:
			oldest_post_time = 0.0

		#######################
		
		if retrieve_last_vote_time(voter_id=own_id) > oldest_post_time:
			recent_user_votes = retrieve_recent_votes(voter_id=own_id, oldest_post_time=oldest_post_time)
			# payload in recent_user_votes is voter_id+":"+target_user_id+":"+vote_value+":"+obj_type+":"+target_obj_id
			recent_user_voted_obj_hashes = set(obj.split(":",3)[-1] for obj in recent_user_votes)
		else:
			recent_user_voted_obj_hashes = []
		
		#######################

		prev_for_me_seen_time = get_for_me_seen_time(user_id=own_id)

		#######################

		obj_entry_times_dict, unseen_posts = dict(obj_tup_list), False
		for obj in list_of_dictionaries:
			
			# enrich objs with information that 'own_id' liked them or not
			if obj['h'] in recent_user_voted_obj_hashes:
				obj['v'] = True# user 'liked' this particular object, so mark it

			# enrich objs with 'seen' information 
			if obj_entry_times_dict[obj['h']] > float(prev_for_me_seen_time):
				obj['new'] = True# this obj has not been seen by the user previously
				unseen_posts = True# TODO: remove when retention loggers are removed

		list_of_dictionaries = format_post_times(list_of_dictionaries, with_machine_readable_times=True)

		###################### Retention activity logging ######################
		from_redirect = request.session.pop('rd',None)# remove this too when removing retention activity logger
		if not from_redirect and own_id > SEGMENT_STARTING_USER_ID:
			if page_num == 1:
				act = 'FN' if unseen_posts else 'FO'
				act = act if is_mob_verified else act+'.u'
			else:
				act = 'F2'
				act = act if is_mob_verified else act+'.u'
			activity_dict = {'m':'GET','act':act,'t':time_now,'pg':page_num}# defines what activity just took place
			log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
		########################################################################
	
	else:
		list_size = 0
		###################### Retention activity logging ######################
		# there are no posts
		from_redirect = request.session.pop('rd',None)# remove this too when removing retention activity logger
		if not from_redirect and own_id > SEGMENT_STARTING_USER_ID:
			act = 'FE'
			act = act if is_mob_verified else act+'.u'
			activity_dict = {'m':'GET','act':act,'t':time_now,'pg':page_num}# defines what activity just took place
			log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
		########################################################################

	# recommend red stars to this user
	if list_size < 5:
		
		# Step 1) Retreive top trenders
		data = retrieve_top_trenders()

		# Step 2) Retrieve whether own_id is following any top trender
		trending_ids = set()
		for obj in data:
			 trending_ids.add(str(obj[0]))
		
		ids_already_fanned = filter_following(trending_ids,own_id)

		# Step 3) Set 'is_follower' flag for trenders that own_id is following
		enriched_data = []

		for tup_obj in data:
			list_obj = list(tup_obj)
			if str(tup_obj[0]) in ids_already_fanned:
				list_obj.insert(0, True)
			else:
				list_obj.insert(0, False)	
			enriched_data.append(list_obj)

		top_list = enriched_data

	# no need to recommend red stars to this user
	else:
		top_list = None

	#######################
	on_fbs = request.META.get('HTTP_X_IORG_FBS',False)
	on_opera = request.is_opera_mini
	is_js_env = retrieve_user_env(opera_mini=on_opera, fbs = on_fbs)
	# on_opera = True if (not on_fbs and not is_js_env) else False
	
	########################

	show_post_removed_prompt = request.session.pop("post_removed"+str(own_id),None)

	context = {'link_list':list_of_dictionaries,'fanned':None,'is_auth':True,'on_fbs':on_fbs,'stars':get_all_image_star_ids(),\
	'ident':own_id, 'process_notification':False,'newest_user':None,'newbie_lang':request.session.get("newbie_lang",None),\
	'mobile_verified':is_mob_verified, 'show_post_removed_prompt':show_post_removed_prompt,'time_now':time_now,\
	'on_opera':on_opera,'own_name':own_name,'new_count':new_count,'dir_rep_form':DirectResponseForm(with_id=True),\
	'thin_rep_form':DirectResponseForm(thin_strip=True),'latest_dir_rep':retrieve_latest_direct_reply(user_id=own_id),\
	'single_notif_dir_rep_form':DirectResponseForm(),'last_seen':last_seen,'max_home_reply_size':MAX_HOME_REPLY_SIZE,\
	'dir_rep_invalid':request.session.pop("dir_rep_invalid"+str(own_id),None),'origin':'26','single_notif_origin':'38',\
	'top_list':top_list}

	context["page"] = {'number':page_num,'has_previous':True if page_num>1 else False,'has_next':True if page_num<max_pages else False,\
	'previous_page_number':page_num-1,'next_page_number':page_num+1}

	newbie_flag = request.session.get("newbie_flag",None)
	if newbie_flag:
		context["newbie_flag"] = newbie_flag
		if newbie_flag in ('1','2','3','5','6','7'):
			if newbie_flag == '5':
				context["newbie_tutorial_page"] = 'tutorial5b.html'
			elif newbie_flag == '6':
				context["newbie_tutorial_page"] = 'tutorial6b.html'
			elif newbie_flag == '7':
				context["newbie_tutorial_page"] = 'tutorial7c.html'
			else:
				context["newbie_tutorial_page"] = 'tutorial'+newbie_flag+'.html'
		else:
			context["newbie_tutorial_page"] = 'newbie_rules.html'

	#####################
	context["lang"] = 'None'
	#####################

	return render(request, 'follow/for_me.html', context)


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def skip_notif(request):
	"""
	Skips 'new followers' notification on the user's custom home

	Updates their last_seen time as well to maintain integrity of 'new followers count'
	"""
	update_user_activity_event_time(request.user.id)
	return redirect('for_me')

###############################################################################################
###################################### Follow & Unfollow ######################################
###############################################################################################

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def follow(request):
	"""
	Subscribes the user to the provided target_id

	Ensure that the subscriber:
	i) is target_user_id an actual user
	ii) is not already subscribed
	iii) is not pvp blocked by target_user_id
	iv) is not banned in the system

	Ensure that the target_user_id is:
	i) is mobile verified
	ii) is not banned in the system
	iii) is a fannable id (i.e. has the requisite privacy settings)
	"""
	is_ajax = request.is_ajax()
	if request.method == "POST":
		# check subscriber and target_user_id credentials first
		own_id = request.user.id
		payload = request.POST.get('pl',[])
		data = payload.split("*")
		topic, obj_id, obj_hash, origin, target_user_id, garbage, page_num = data[0], data[1], data[2], data[3], data[4],\
		data[5], data[6]
		target_username = retrieve_uname(target_user_id,decode=True)
		if not target_username:
			raise Http404("This user doesn't exist")
		
		# elif not request.mobile_verified:
		# 	# REQUIREMENT REMOVED: a prompt asking the user to verify first
		# 	if is_ajax:
		# 		message = "Sorry! Follow karney ke liye pehlay apna account verify karwain"
		# 		return HttpResponse(json.dumps({'success':False,'message':message,'type':'text'}),\
		# 			content_type='application/json',)
		# 	else:
		# 		return render(request,"verification/unable_to_submit_without_verifying.html",{'fan':True})
		
		elif not is_mobile_verified(target_user_id):
			# show a prompt that the target is not verified so you cannot become their fan
			if is_ajax:
				message = "Sorry! {} ka account verified nahi hai, is liye unko follow nahi kia ja sakta".format(target_username)
				return HttpResponse(json.dumps({'success':False,'message':message,'type':'text'}),\
					content_type='application/json',)
			else:
				return render(request,"follow/notify_and_redirect.html",{'target_not_verified':True,\
					'target_uname':target_username,'orig':origin,'lid':obj_hash,'obid':obj_id})
		
		elif is_potential_follower_rate_limited(follower_id=own_id,star_id=target_user_id):
			# show a prompt that you cannot follow target user ID
			if is_ajax:
				message = "Sorry! Ap kuch time tak {} ko follow nahi kar sakte".format(target_username)
				return HttpResponse(json.dumps({'success':False,'message':message,'type':'text'}),\
					content_type='application/json',)
			else:
				if topic:
					request.session["origin_topic"] = topic
				return render(request,"follow/notify_and_redirect.html",{'user_rate_limited':True,\
					'target_uname':target_username,'orig':origin,'lid':obj_hash,'obid':obj_id})	
		
		elif check_if_follower(own_id, target_user_id, with_db_lookup=True):
			# this person is already subscribed
			if is_ajax:
				return HttpResponse(json.dumps({'success':True,'message':'followed','type':'text'}),\
					content_type='application/json',)
			else:
				if topic:
					request.session["origin_topic"] = topic
				return return_to_content(request=request,origin=origin,obj_id=obj_id,link_id=obj_hash,\
					target_uname=target_username)
		else:
			################## SYSTEM BANS ##################
			# is own_id banned by the system?
			own_user_banned, own_time_remaining, own_ban_details = check_content_and_voting_ban(own_id, with_details=True)
			if own_user_banned:
				if is_ajax:
					message = "Sorry! Ap banned hain. Ap 'follow' kar sakein ge {}".format(future_time.future_time(own_time_remaining))
					return HttpResponse(json.dumps({'success':False,'message':message,'type':'text'}),\
						content_type='application/json',)
				else:
					return render(request, 'judgement/cannot_comment.html', {'time_remaining': own_time_remaining,\
						'ban_details':own_ban_details,'own_profile':True,'defender':None,'is_profile_banned':True,\
						'org':origin, 'tun':retrieve_uname(own_id,decode=True),'lid':obj_hash,'obid':obj_id})

			# is target_user_id banned by the system
			target_user_banned, target_time_remaining, target_ban_details = check_content_and_voting_ban(target_user_id, \
				with_details=True)
			if target_user_banned:
				if is_ajax:
					message = "Sorry! Ap {0} ko follow nahi kar saktey kyun ke {1} banned hain".format(target_username,target_username)
					return HttpResponse(json.dumps({'success':False,'message':message,'type':'text'}),\
						content_type='application/json',)
				else:
					return render(request,"follow/notify_and_redirect.html",{'target_user_banned':True,'target_uname':target_username,\
						'orig':origin,'lid':obj_hash,'obid':obj_id})

 			################## PVP BAN ##################
 			banned_by, ban_time = is_already_banned(own_id=own_id,target_id=target_user_id, return_banner=True)
			if banned_by:
				request.session["banned_by"] = banned_by
				request.session["ban_time"] = ban_time
				request.session["where_from"] = origin
				request.session["obj_id"] = obj_id
				request.session["lid"] = obj_hash
				request.session["target_username"] = target_username
				request.session.modified = True
				if is_ajax:
					return HttpResponse(json.dumps({'success':False,'message':reverse('ban_underway'),'type':'redirect'}),\
						content_type='application/json',)
				else:
					return redirect("ban_underway")	
			else:
				# now we can subcribe!
				if topic:
					request.session["origin_topic"] = topic
				is_mob_verified = request.mobile_verified
				verification_status = '1' if is_mob_verified else '0'
				time_now = time.time()
				set_user_last_seen(target_user_id,time_now)
				add_follower(user_id=own_id, target_user_id=target_user_id, verification_status=verification_status, time_now=time_now+1)

				add_last_fanout_to_feed(own_id,target_user_id,time_now)

				###################### Retention activity logging ######################
				if own_id > SEGMENT_STARTING_USER_ID:
					request.session['rd'] = '1'
					act = 'N' if is_mob_verified else 'N.u'
					activity_dict = {'m':'POST','act':act,'t':time_now,'pg':page_num}# defines what activity just took place
					log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
				########################################################################

				###########################################################################
				############################### Follow Logger #############################
				###########################################################################
				# num_fans = get_all_follower_count(own_id)
				# num_vfans = get_verified_follower_count(own_id)
				# data = {'star_id':target_user_id,'follower':own_id, 'v_stat':verification_status,'orig':origin, 'obj_id':obj_id,'lid':obj_hash,\
				# 'numf':num_fans,'num_vf':num_vfans,'type':'follow'}
				# logging_follow_data(data)
				###########################################################################
				###########################################################################	
				###########################################################################
				
				if is_ajax:
					return HttpResponse(json.dumps({'success':True,'message':'followed','type':'text'}),\
						content_type='application/json',)
				else:
					return return_to_content(request=request,origin=origin,obj_id=obj_id,link_id=obj_hash,\
						target_uname=target_username)
	else:
		raise Http404("Cannot follow via a GET request")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def unfollow(request):
	"""
	There are 3 fan removal cases:
	i) When a fan removes themselves
	ii) When the 'star' removes their fan
	iii) When there's a pvp ban
	"""
	is_ajax = request.is_ajax()
	if request.method == "POST":
		own_id = request.user.id
		#########################################################
		payload = request.POST.get('pl',[])
		data = payload.split("*")
		
		topic, obj_id, obj_hash, origin, target_user_id, garbage, page_num = data[0], data[1], data[2], data[3], data[4],\
		data[5], data[6]
		target_username = retrieve_uname(target_user_id,decode=True)
		if target_username:
			if topic:
				request.session["origin_topic"] = topic
			verification_status = '1' if is_mobile_verified(target_user_id) else '0'
			remove_follower(follower_id=own_id, star_id=target_user_id,follower_verification_status=verification_status)

			###################### Retention activity logging ######################
			if own_id > SEGMENT_STARTING_USER_ID:
				time_now = time.time()
				request.session['rd'] = '1'
				act = 'N1' if request.mobile_verified else 'N1.u'
				activity_dict = {'m':'POST','act':act,'t':time_now,'pg':page_num}# defines what activity just took place
				log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
			########################################################################

			###########################################################################
			############################### Unfollow Logger ###########################
			###########################################################################
			# num_fans = get_all_follower_count(own_id)
			# num_vfans = get_verified_follower_count(own_id)
			# data = {'star_id':target_user_id,'follower':own_id, 'v_stat':verification_status,'orig':origin, 'obj_id':obj_id,'lid':obj_hash,\
			# 'numf':num_fans,'num_vf':num_vfans,'type':'unfollow'}
			# logging_follow_data(data)
			###########################################################################
			###########################################################################	
			###########################################################################
			if not is_potential_follower_rate_limited(follower_id=own_id, star_id=target_user_id):
				rate_limit_unfollower(follower_id=own_id, star_id=target_user_id)
			if origin == '28':
				start_index, end_index = get_indices(page_num, FOLLOWING_PER_PAGE)
				following, num_following = retrieve_following_ids(own_id,start_idx=start_index, end_idx=end_index, with_follower_count=True)
				num_pages = num_following/FOLLOWING_PER_PAGE
				max_pages = num_pages if num_following % FOLLOWING_PER_PAGE == 0 else (num_pages+1)
				page_num = int(page_num)
				if not following and page_num > 1:
					new_num = int(page_num)-1
					request.session['page_num']= str(new_num)
				else:
					request.session['page_num']= page_num
			if is_ajax:
				return HttpResponse(json.dumps({'success':True,'message':'unfollowed','type':'text'}),\
					content_type='application/json',)
			else:
				return return_to_content(request=request,origin=origin,obj_id=obj_id,link_id=obj_hash,\
					target_uname=target_username)
		else:
			raise Http404("This user does not exist")
	else:
		raise Http404("Not a post request")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def remove_my_follower(request, target_username):
	"""
	This function is called when a 'star' forcefully removes a follower
	
	This is different from unfollow() - that is purely used by a 'follower' to unfollow a 'star'
	"""
	if request.method == "POST":
		star_id = request.user.id
		follower_id = retrieve_user_id(target_username)
		#########################################################
		obj_id = request.POST.get("obid",None)
		request.session.modified = True
		if star_id:
			# banned, ttl = set_inter_user_ban(own_id=star_id, target_id=follower_id, target_username=target_username, \
			# 			ttl=60, time_now=time.time(), can_unban=True)
			rate_limit_removed_follower(follower_id=follower_id, star_id=star_id )
			verification_status = '1' if is_mobile_verified(follower_id) else '0'
			remove_follower(follower_id=follower_id, star_id=star_id, follower_verification_status=verification_status)

			page_num = request.POST.get("page_num",None)
			origin = request.POST.get("origin",None)
			start_index, end_index = get_indices(page_num, FOLLOWERS_PER_PAGE)
			followers, num_followers = retrieve_follower_data(star_id,start_idx=start_index, end_idx=end_index, with_follower_count=True)
			if not followers and page_num > 1:
				new_num = int(page_num)-1 if page_num else 1
				request.session['page_num']= str(new_num)
			else:
				request.session['page_num']= page_num

			###################### Retention activity logging ######################
			if star_id > SEGMENT_STARTING_USER_ID:
				time_now = time.time()
				request.session['rd'] = '1'
				act = 'N3' if request.mobile_verified else 'N3.u'
				activity_dict = {'m':'POST','act':act,'t':time_now,'pg':page_num}# defines what activity just took place
				log_user_activity.delay(user_id=star_id, activity_dict=activity_dict, time_now=time_now)
			########################################################################

			return return_to_content(request=request,origin=origin,obj_id=str(obj_id),link_id=None,\
				target_uname=target_username)
		else:
			raise Http404("This user does not exist")
	else:
		raise Http404("Not a post request")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def remove_single_post(request):
	"""
	Enables a post viewer to remove a post from their custom feed
	Enables OP to remove post from their history
	"""
	if request.method == "POST":
		own_id = request.user.id
		origin = request.POST.get("origin",None)
		obj_hash = request.POST.get("obj_hash",None)
		which_link = request.POST.get("which_link",None)

		if which_link:
			# for deletion of post from history
			own_name = retrieve_uname(own_id, decode=True)
			removed, ttl, action_by_op = remove_single_post_from_custom_feed(obj_hash=obj_hash, own_id=own_id)
			if removed:
				if action_by_op:
					if origin == '29':
						invalidate_cached_user_feed_history(own_id,'public')
					elif origin == '30':
						invalidate_cached_user_feed_history(own_id,'limited')
					else:
						invalidate_cached_user_feed_history(own_id,'private')
				request.session["history_post_removed"+str(own_id)] = '1'

				###########################################################################
				############################### Post Removal Logger #######################
				###########################################################################				
				# post_data = Link.objects.values('type_of_content', 'description', 'url', \
				# 	'image_file', 'reply_count', 'net_votes', 'trending_status').filter(id=which_link)
				# data = {'Is_OP':action_by_op,'remover_name':own_name, 'orig':origin,'lid':obj_hash,'which_link':which_link,'type':'from history',\
				# 'type_of_content':post_data[0]['type_of_content'],'trending_status':post_data[0]['trending_status'],'url':post_data[0]['url'],\
				# 'image_file':post_data[0]['image_file'],'reply_count':post_data[0]['reply_count'],'net_votes':post_data[0]['net_votes'],\
				# 'description':post_data[0]['description']}
				# logging_remove_data(data)
				###########################################################################
				###########################################################################	
				###########################################################################
				
				return return_to_content(request=request,origin=origin,link_id=None,target_uname=own_name)
				
			elif ttl:
				# user is rate limited from removing the post
				return render(request,"follow/notify_and_redirect.html",{'removal_rate_limited':True,\
					'orig':origin,'lid':obj_hash,'obid':obj_hash.partition(':')[-1],'ttl':ttl,\
					'human_readable_rate_limit':human_readable_time(REMOVAL_RATE_LIMIT_TIME),\
					'target_uname':own_name})
			
			else:
				raise Http404("Could not remove post - it possibly does not exist")
		else:
			# for removal of post from own feed
			removed, ttl, action_by_op = remove_single_post_from_custom_feed(obj_hash=obj_hash, own_id=own_id)
			own_name = retrieve_uname(own_id, decode=True)

			###########################################################################
			############################### Post Removal Logger #######################
			###########################################################################				
			# post_data = get_obj_data(obj_hash)#Link.objects.values('type_of_content', 'description', 'url', \#'image_file', 'reply_count', 'net_votes', 'trending_status').filter(id=which_link)
			# if post_data:
			# 	data = {'Is_OP':action_by_op,'remover_name':own_name, 'orig':origin,'lid':obj_hash,'which_link':which_link,'type':'from my home',\
			# 	'post_details':post_data}
			# 	logging_remove_data(data)
			###########################################################################
			###########################################################################	
			###########################################################################

			if removed:
				if action_by_op:
					invalidate_cached_user_feed_history(own_id,'public')
					invalidate_cached_user_feed_history(own_id,'limited')
					invalidate_cached_user_feed_history(own_id,'private')
				request.session["post_removed"+str(own_id)] = '1'
				url = reverse_lazy('for_me')+'?page=1#error'
				return redirect(url)

			elif ttl:
				# user is rate limited from removing the post
				
				return render(request,"follow/notify_and_redirect.html",{'removal_rate_limited':True,\
					'orig':origin,'lid':obj_hash,'obid':obj_hash.partition(':')[-1],'ttl':ttl,\
					'human_readable_rate_limit':human_readable_time(REMOVAL_RATE_LIMIT_TIME),\
					'target_uname':own_name})

			else:
				raise Http404("Could not remove post - it possibly does not exist")
	else:
		raise Http404("Not a post request")


def show_follower_list(request):
	"""
	Renders the list of users following the given user
	"""
	# can we use use and uss here?
	page_num = request.GET.get('page', '1')
	start_index, end_index = get_indices(page_num, FOLLOWERS_PER_PAGE)
	own_id = request.user.id
	followers, num_followers = retrieve_follower_data(own_id,start_idx=start_index, end_idx=end_index, with_follower_count=True)
	num_pages = num_followers/FOLLOWERS_PER_PAGE
	max_pages = num_pages if num_followers % FOLLOWERS_PER_PAGE == 0 else (num_pages+1)
	page_num = int(page_num)
	if not followers and page_num > 1:
		page_num = page_num-1
		# no followers have been retrieved, and the page is greater than 1
	own_name = retrieve_uname(own_id, decode=True)
	origin = '27'

	###################### Retention activity logging ######################
	if own_id > SEGMENT_STARTING_USER_ID:
		time_now = time.time()
		act = 'A6' if request.mobile_verified else 'A6.u'
		activity_dict = {'m':'GET','act':act,'t':time_now,'pg':page_num}# defines what activity just took place
		log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
	########################################################################

	#TODO: micro-cache 'followers'
	context={'followers':followers,'own_name':own_name,'count':num_followers,'own_id':own_id,'origin':origin}#,'page_obj':page_obj}
	context["page_obj"] = {'number':page_num,'has_previous':True if page_num>1 else False,'has_next':True if page_num<max_pages else False,\
	'previous_page_number':page_num-1,'next_page_number':page_num+1}
	return render(request,"follow/followers.html",context)



def show_new_followers(request):
	"""
	Renders the list of users following the given user
	"""
	# can we use use and uss here?
	own_id = request.user.id
	last_seen_time = get_user_activity_event_time(own_id)
	if last_seen_time == None:
		last_seen_time = time.time()
	followers, num_followers = retrieve_follower_data(own_id,start_idx=0, end_idx=-1, with_follower_count_since_last_seen=last_seen_time)
		
	###################### Retention activity logging ######################
	if own_id > SEGMENT_STARTING_USER_ID:
		time_now = time.time()
		act = 'N2' if request.mobile_verified else 'N2.u'
		activity_dict = {'m':'GET','act':act,'t':time_now,'pg':''}# defines what activity just took place
		log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
	########################################################################

	own_name = retrieve_uname(own_id, decode=True)
	new_follower_list = True
	origin = '32'
	context={'followers':followers,'own_name':own_name,'count':num_followers,'own_id':own_id,'new_follower_list':new_follower_list,'origin':origin}#,'page_obj':page_obj}
	return render(request,"follow/followers.html",context)	
	

def show_following_list(request):
	"""
	Renders the list of users the given user is following
	"""
	context = {}
	own_id = request.user.id
	ids = UserFan.objects.filter(fan_id=own_id).values_list('star_id',flat=True).order_by('-fanning_time')

	page_num = request.GET.get('page', '1')	
	start_index, end_index = get_indices(page_num, FOLLOWING_PER_PAGE)
	following, num_following = retrieve_following_ids(own_id,start_idx=start_index, end_idx=end_index, with_follower_count=True)
	num_pages = num_following/FOLLOWING_PER_PAGE
	max_pages = num_pages if num_following % FOLLOWING_PER_PAGE == 0 else (num_pages+1)
	page_num = int(page_num)
	own_name = retrieve_uname(own_id, decode=True)

	###################### Retention activity logging ######################
	if own_id > SEGMENT_STARTING_USER_ID:
		time_now = time.time()
		act = 'A7' if request.mobile_verified else 'A7.u'
		activity_dict = {'m':'GET','act':act,'t':time_now,'pg':page_num}# defines what activity just took place
		log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
	########################################################################

	context={'followers':following,'own_name':own_name,'count':num_following,'own_id':own_id,\
	'on_fbs':request.META.get('HTTP_X_IORG_FBS',False)}#,'page_obj':page_obj}
	context["page_obj"] = {'number':page_num,'has_previous':True if page_num>1 else False,'has_next':True if page_num<max_pages else False,\
	'previous_page_number':page_num-1,'next_page_number':page_num+1}
	return render(request,"follow/following.html",context)


###############################################################################################
###################################### User Feed History ######################################
###############################################################################################


def display_user_public_feed_history(request, target_uname):
	"""
	Display all posts shared by the user of the sort 'tp' and 'gp' (where 'tp' is 'public text' and 'gp' is 'public image')
	
	Works even if the user is not authenticated
	"""
	target_user_id = retrieve_user_id(target_uname)
	if target_user_id:

		dict_data = []
		own_id = request.user.id
		own_mobile_verified = request.mobile_verified
		page_num = request.GET.get('page', '1')
		is_own_profile = str(own_id) == target_user_id
		on_fbs = request.META.get('HTTP_X_IORG_FBS',False)
		context = {'target_uname':target_uname,'own_id':own_id,'section':'public','origin':'29','is_own_profile':is_own_profile,\
		'mobile_verified':own_mobile_verified if is_own_profile else is_mobile_verified(target_user_id), 'on_fbs':on_fbs,\
		'target_user_id':target_user_id}

		###########
		# is user banned?
		banned, time_remaining, ban_details = check_content_and_voting_ban(target_user_id, with_details=True)
		context["ban_detail"] = ban_details
		context["is_profile_banned"] = banned
		context["noindex"] = True if (banned or not context["mobile_verified"]) else False
		context["defender"] = in_defenders(own_id)
		context["time_remaining"] = time_remaining
		###########

		context["target_avurl"] = retrieve_avurl(target_user_id)
		context["is_star"] = is_image_star(user_id=target_user_id)

		time_now = int(time.time())
		context['time_now'] = time_now

		start_index, end_index = get_indices(page_num, ITEMS_PER_PAGE)

		cached_json_data = retrieve_cached_user_feed_history(user_id=target_user_id, page_num=page_num, hist_type='public')
		if cached_json_data:
			try:
				cached_data = json.loads(cached_json_data)
			except:
				cached_data = json_backup.loads(cached_json_data)
			dict_data, total_objs = cached_data[0], cached_data[1]
			if total_objs > 0:

				context["object_list"] = dict_data

				########### Enabling pagination ###########

				num_pages = total_objs/ITEMS_PER_PAGE
				max_pages = num_pages if total_objs % ITEMS_PER_PAGE == 0 else (num_pages+1)
				page_num = int(page_num)

				next_page_number = page_num+1 if page_num<max_pages else 1
				previous_page_number = page_num-1 if page_num>1 else max_pages
				
				context["page"] = {'number':page_num,'has_previous':True if page_num>1 else False,'has_next':True if page_num<max_pages else False,\
				'previous_page_number':previous_page_number,'next_page_number':next_page_number,'max_pages':max_pages}

		else:
			total_objs = Link.objects.filter(Q(submitter_id=target_user_id,audience='p',delete_status='0',mortality='i')|\
				Q(submitter_id=target_user_id,audience='p',delete_status='0',expire_at__gte=time_now)).count()
			if total_objs > 0:

				dict_data = Link.objects.values('id','submitter_id','submitted_on','type_of_content','description','url',\
					'image_file','reply_count','net_votes','trending_status','cagtegory','expire_at','comment_status',\
					'mortality','web_link').filter(Q(submitter_id=target_user_id,audience='p',delete_status='0',mortality='i')|\
					Q(submitter_id=target_user_id,audience='p',delete_status='0',expire_at__gte=time_now)).\
					order_by('-id')[start_index:end_index+1]

				for obj in dict_data:
					# converting datetime obj into epoch
					obj['submitted_on'] = convert_to_epoch(obj['submitted_on'])
	
					# enriching object_list with topic data
					topic_payload = obj['url']
					if topic_payload:
						payload = topic_payload.split(":")
						try:
							theme, obj['topic_name'], obj['topic_url'] = payload[0], payload[1], payload[2]
							color_grads = COLOR_GRADIENTS[theme]
							obj["c1"], obj["c2"] = color_grads[0], color_grads[1]
						except IndexError:
							pass

					# enriching object_list with obj_hash names
					obj['obj_hash'] = 'tx:'+str(obj['id']) if obj['type_of_content'] == 't' else 'img:'+str(obj['id'])


				context["object_list"] = dict_data

				########### Enabling pagination ###########

				num_pages = total_objs/ITEMS_PER_PAGE
				max_pages = num_pages if total_objs % ITEMS_PER_PAGE == 0 else (num_pages+1)
				page_num = int(page_num)

				next_page_number = page_num+1 if page_num<max_pages else 1
				previous_page_number = page_num-1 if page_num>1 else max_pages
				
				context["page"] = {'number':page_num,'has_previous':True if page_num>1 else False,'has_next':True if page_num<max_pages else False,\
				'previous_page_number':previous_page_number,'next_page_number':next_page_number,'max_pages':max_pages}

			######## cache the data alongwith page num ########

			cache_user_feed_history(user_id=target_user_id, json_payload=json.dumps([dict_data,total_objs]),page_num=page_num, hist_type='public')

		###################### Retention activity logging ######################
		from_redirect = request.session.pop('rd',None)# remove this too when removing retention activity logger
		if not from_redirect and own_id > SEGMENT_STARTING_USER_ID:
			act = 'A2' if is_own_profile else 'A5'
			act = act if own_mobile_verified else act+'.u'
			activity_dict = {'m':'GET','act':act,'t':time_now,'pg':page_num}# defines what activity just took place
			log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
		########################################################################

		context['num_posts'] = total_objs if total_objs < 1000 else '999+'
		context['is_follower'] = True if is_own_profile else check_if_follower(own_id,target_user_id,with_db_lookup=True)
		context['show_post_removed_prompt'] = request.session.pop("history_post_removed"+str(own_id),None)
		#######################
		on_opera = request.is_opera_mini
		is_js_env = retrieve_user_env(opera_mini=on_opera, fbs = on_fbs)
		context['on_opera'] = on_opera

		return render(request,"follow/user_feed_history.html",context)
	else:
		# user does not exist
		raise Http404("This user does not exist")


def display_user_follower_feed_history(request, target_uname):
	"""
	Display all posts shared by the poster - of the sort 'tai', 'gai', 'tam' and 'gam', where:

	(i) 'tai' is 'text shared to all followers'
	(ii) 'gai' is 'image shared to all followers'
	(iii) 'tam' is 'text shared to all followers ephemerally'
	(iv) 'gam' is 'image shared to all followers ephemerally'
	"""
	target_user_id = retrieve_user_id(target_uname)
	if target_user_id:
		dict_data = []
		own_id = request.user.id
		page_num = request.GET.get('page', '1')
		is_own_profile = str(own_id) == target_user_id
		on_fbs = request.META.get('HTTP_X_IORG_FBS',False)
		context = {'target_uname':target_uname,'own_id':own_id,'section':'limited','origin':'30','is_own_profile':is_own_profile,\
		'mobile_verified':request.mobile_verified if is_own_profile else is_mobile_verified(target_user_id),\
		'on_fbs':on_fbs,'target_user_id':target_user_id}

		###########
		# is user banned?
		banned, time_remaining, ban_details = check_content_and_voting_ban(target_user_id, with_details=True)
		context["ban_detail"] = ban_details
		context["is_profile_banned"] = banned
		context["noindex"] = True if (banned or not context["mobile_verified"]) else False
		context["defender"] = in_defenders(own_id)
		context["time_remaining"] = time_remaining
		###########

		context["target_avurl"] = retrieve_avurl(target_user_id)
		context["is_star"] = is_image_star(user_id=target_user_id)

		time_now = int(time.time())
		context['time_now'] = time_now

		cached_json_data = retrieve_cached_user_feed_history(user_id=target_user_id, page_num=page_num, hist_type='limited')
		if cached_json_data:
			try:
				cached_data = json.loads(cached_json_data)
			except:
				cached_data = json_backup.loads(cached_json_data)
			dict_data, total_objs, context["ephemeral_posts_exist"] = ephemeral_posts_exist = cached_data[0], cached_data[1], cached_data[2]
			if total_objs > 0:
				context["object_list"] = dict_data

				########### Enabling pagination ###########

				num_pages = total_objs/ITEMS_PER_PAGE
				max_pages = num_pages if total_objs % ITEMS_PER_PAGE == 0 else (num_pages+1)
				page_num = int(page_num)

				next_page_number = page_num+1 if page_num<max_pages else 1
				previous_page_number = page_num-1 if page_num>1 else max_pages
				
				context["page"] = {'number':page_num,'has_previous':True if page_num>1 else False,'has_next':True if page_num<max_pages else False,\
				'previous_page_number':previous_page_number,'next_page_number':next_page_number,'max_pages':max_pages}

		else:
			
			# get object count
			total_objs = Link.objects.filter(Q(submitter_id=target_user_id,audience='a',delete_status='0',mortality='i')|\
				Q(submitter_id=target_user_id,audience='a',delete_status='0',mortality='m',expire_at__gte=time_now)).count()

			# maybe this person also posts ephemeral stuff - let the prospective follower know accordingly:
			ephemeral_posts_exist = Link.objects.filter(submitter_id=target_user_id,audience='a',delete_status='0',\
				expire_at__gte=time_now-ONE_MONTH).exists()

			context["ephemeral_posts_exist"] = ephemeral_posts_exist

			if total_objs > 0:

				start_index, end_index = get_indices(page_num, ITEMS_PER_PAGE)

				dict_data = Link.objects.values('id','submitter_id','submitted_on','type_of_content','description','url',\
					'image_file','reply_count','net_votes','trending_status','cagtegory','expire_at','comment_status',\
					'mortality','web_link').filter(Q(submitter_id=target_user_id,audience='a',delete_status='0',mortality='i')|\
					Q(submitter_id=target_user_id,audience='a',delete_status='0',mortality='m',expire_at__gte=time_now)).\
					order_by('-id')[start_index:end_index+1]

				for obj in dict_data:
					# converting datetime obj into epoch
					obj['submitted_on'] = convert_to_epoch(obj['submitted_on'])

					# enriching object_list with topic data
					topic_payload = obj['url']
					if topic_payload:
						payload = topic_payload.split(":")
						try:
							theme, obj['topic_name'], obj['topic_url'] = payload[0], payload[1], payload[2]
							color_grads = COLOR_GRADIENTS[theme]
							obj["c1"], obj["c2"] = color_grads[0], color_grads[1]
						except IndexError:
							pass

					# enriching object_list with obj_hash names
					obj['obj_hash'] = 'tx:'+str(obj['id']) if obj['type_of_content'] == 't' else 'img:'+str(obj['id'])

				context["object_list"] = dict_data

				########### Enabling pagination ###########

				num_pages = total_objs/ITEMS_PER_PAGE
				max_pages = num_pages if total_objs % ITEMS_PER_PAGE == 0 else (num_pages+1)
				page_num = int(page_num)

				next_page_number = page_num+1 if page_num<max_pages else 1
				previous_page_number = page_num-1 if page_num>1 else max_pages
				
				context["page"] = {'number':page_num,'has_previous':True if page_num>1 else False,'has_next':True if page_num<max_pages else False,\
				'previous_page_number':previous_page_number,'next_page_number':next_page_number,'max_pages':max_pages}
			
				
			######## cache the data alongwith page num ########
			cache_user_feed_history(user_id=target_user_id, json_payload=json.dumps([dict_data,total_objs,ephemeral_posts_exist]),page_num=page_num, hist_type='limited')

		context['post_count'] = total_objs
		context['is_follower'] = True if is_own_profile else check_if_follower(own_id,target_user_id,with_db_lookup=True)
		context['show_post_removed_prompt'] = request.session.pop("history_post_removed"+str(own_id),None)
		#######################
		on_opera = request.is_opera_mini
		is_js_env = retrieve_user_env(opera_mini=on_opera, fbs = on_fbs)
		context['on_opera'] = on_opera

		return render(request,"follow/user_feed_history.html",context)
	else:
		# user does not exist
		raise Http404("This poster does not exist")




def display_user_private_feed_history(request, target_uname):
	"""
	Display all 'selective' posts ever shared by the user (which remain unexpired)

	Only for the OP's eyes
	"""
	own_id = request.user.id
	target_user_id = retrieve_user_id(target_uname)
	if str(own_id) == target_user_id:
		dict_data = []
		page_num = request.GET.get('page', '1')
		on_fbs = request.META.get('HTTP_X_IORG_FBS',False)
		context = {'target_uname':target_uname,'own_id':own_id,'section':'private','origin':'31',\
		'is_own_profile':True,'on_fbs':on_fbs,'mobile_verified':request.mobile_verified}

		###########
		# is own_id banned?
		banned, time_remaining, ban_details = check_content_and_voting_ban(target_user_id, with_details=True)
		context["ban_detail"] = ban_details
		context["is_profile_banned"] = banned
		context["noindex"] = True if (banned or not context["mobile_verified"]) else False
		context["defender"] = in_defenders(own_id)
		context["time_remaining"] = time_remaining
		###########

		context["is_star"] = is_image_star(user_id=own_id)
		context["target_avurl"] = retrieve_avurl(own_id)

		start_index, end_index = get_indices(page_num, ITEMS_PER_PAGE)
		time_now = int(time.time())
		context['time_now'] = time_now
		cached_json_data = retrieve_cached_user_feed_history(user_id=target_user_id, page_num=page_num, hist_type='private')
		if cached_json_data:
			try:
				cached_data = json.loads(cached_json_data)
			except:
				cached_data = json_backup.loads(cached_json_data)
			dict_data, total_objs = cached_data[0], cached_data[1]
			if total_objs > 0:
				context["object_list"] = dict_data
				########### Enabling pagination ###########

				num_pages = total_objs/ITEMS_PER_PAGE
				max_pages = num_pages if total_objs % ITEMS_PER_PAGE == 0 else (num_pages+1)
				page_num = int(page_num)

				next_page_number = page_num+1 if page_num<max_pages else 1
				previous_page_number = page_num-1 if page_num>1 else max_pages
				
				context["page"] = {'number':page_num,'has_previous':True if page_num>1 else False,'has_next':True if page_num<max_pages else False,\
				'previous_page_number':previous_page_number,'next_page_number':next_page_number,'max_pages':max_pages}

		else:

			total_objs = Link.objects.filter(Q(submitter_id=target_user_id, audience='s', delete_status='0',mortality='m',expire_at__gte=time_now)|\
				Q(submitter_id=target_user_id, audience='s',delete_status='0',mortality='i')).count()

			if total_objs > 0:

				dict_data = Link.objects.values('id','submitter_id','submitted_on','type_of_content','expire_at','description',\
					'url','image_file','reply_count','net_votes','trending_status','cagtegory','comment_status','mortality','web_link',\
					).filter(Q(submitter_id=target_user_id,audience='s',delete_status='0',mortality='m',expire_at__gte=time_now)|\
					Q(submitter_id=target_user_id,audience='s',delete_status='0',mortality='i')).\
					order_by('-id')[start_index:end_index+1]

				for obj in dict_data:
					# converting datetime obj into epoch
					obj['submitted_on'] = convert_to_epoch(obj['submitted_on'])

					# enriching object_list with topic data
					topic_payload = obj['url']
					if topic_payload:
						payload = topic_payload.split(":")
						try:
							theme, obj['topic_name'], obj['topic_url'] = payload[0], payload[1], payload[2]
							color_grads = COLOR_GRADIENTS[theme]
							obj["c1"], obj["c2"] = color_grads[0], color_grads[1]
						except IndexError:
							pass

					# enriching object_list with obj_hash names
					obj['obj_hash'] = 'tx:'+str(obj['id']) if obj['type_of_content'] == 't' else 'img:'+str(obj['id'])

				context["object_list"] = dict_data
				
				########### Enabling pagination ###########

				num_pages = total_objs/ITEMS_PER_PAGE
				max_pages = num_pages if total_objs % ITEMS_PER_PAGE == 0 else (num_pages+1)
				page_num = int(page_num)

				next_page_number = page_num+1 if page_num<max_pages else 1
				previous_page_number = page_num-1 if page_num>1 else max_pages
				
				context["page"] = {'number':page_num,'has_previous':True if page_num>1 else False,'has_next':True if page_num<max_pages else False,\
				'previous_page_number':previous_page_number,'next_page_number':next_page_number,'max_pages':max_pages}

			######## cache the data alongwith page num ########
			cache_user_feed_history(user_id=target_user_id, json_payload=json.dumps([dict_data,total_objs]),page_num=page_num, hist_type='private')
		context['post_count'] = total_objs
		context['show_post_removed_prompt'] = request.session.pop("history_post_removed"+str(own_id),None)
		return render(request,"follow/user_feed_history.html",context)
	else:
		# user does not exist
		raise Http404("This user's private feed is not available")


def display_trending_history(request, target_uname):
	"""
	Displays trending posts of a user (text and images both)
	"""
	own_id = request.user.id
	target_id = retrieve_user_id(target_uname)
	if str(own_id) == target_id:
		
		time_now = time.time()
		page_num = request.GET.get('page', '1')
		start_index, end_index = get_indices(page_num, ITEMS_PER_PAGE)

		# get object count
		total_objs = Link.objects.filter(trending_status='1',delete_status='0',submitter_id=target_id).count()

		# retrieve  objects
		object_list = Link.objects.values('id','description','image_file','net_votes','submitted_on','reply_count','type_of_content',\
			'cagtegory','url','expire_at','web_link').filter(trending_status='1',delete_status='0',submitter_id=target_id).\
		order_by('-id')[start_index:end_index+1]

		context = {'target_uname':target_uname,'on_fbs':request.META.get('HTTP_X_IORG_FBS',False),'is_star':is_image_star(user_id=target_id),\
		'own_profile':True,'star_id':target_id,'av_url':get_s3_object(retrieve_avurl(target_id),category='thumb'),'total_objs':total_objs,\
		'object_list':object_list,'time_now':time_now}

		for obj in object_list:
			obj['machine_time'] = obj['submitted_on']
			obj['submitted_on'] = naturaltime(obj['submitted_on'])
			if obj['url']:
				payload = obj['url'].split(":")
				try:
					theme, obj['topic_name'], obj['url'] = payload[0], payload[1], payload[2]
					color_grads = COLOR_GRADIENTS[theme]
					obj['c1'], obj['c2'] = color_grads[0], color_grads[1]
				except:
					obj['topic_name'], obj['url'] = '', ''
					obj['c1'], obj['c2'] = '', ''

		###################### Retention activity logging ######################
		if own_id > SEGMENT_STARTING_USER_ID:
			act = 'A3' if request.mobile_verified else 'A3.u'
			activity_dict = {'m':'GET','act':act,'t':time_now,'pg':page_num}# defines what activity just took place
			log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
		########################################################################

		########### Enabling pagination ###########

		num_pages = total_objs/ITEMS_PER_PAGE
		max_pages = num_pages if total_objs % ITEMS_PER_PAGE == 0 else (num_pages+1)
		page_num = int(page_num)

		next_page_number = page_num+1 if page_num<max_pages else 1
		previous_page_number = page_num-1 if page_num>1 else max_pages

		context["page"] = {'number':page_num,'has_previous':True if page_num>1 else False,'has_next':True if page_num<max_pages else False,\
		'previous_page_number':previous_page_number,'next_page_number':next_page_number,'max_pages':max_pages}

		return render(request,"trending_posts.html",context)
	else:
		# user does not exist
		raise Http404("This user's trending data is not available for you (or user is spurious)")


####################################################		


def export_post_data(request,post_type):
	"""
	Exports all 'follow' logging results into a CSV file for analysis

	Useful for analysis such as:
	- Various types of posts shared (i.e. segmented by audience, mortality, comment-status)
	- Content differences (if any) between different segments found above
	- Avg/Median number of followers selected for 'some follower' posting
	- Do users prefer permanent posts or posts with expiry? i.e. should ephemerality be the default?
	- Are users sharing 'authentic' images of selves?
	- Are 'some follower' posts usually targeting 'friends', or are they impersonal as the rest of them?
	- Are '15 minute' posts different (content-wise) from their '1-day' counterparts?
	Etcetra
	"""
	from redis3 import exact_date#, get_world_age
	from redis2 import retrieve_post_data
	
	own_id = request.user.id
	is_defender, is_super_defender = in_defenders(own_id, return_super_status=True)
	if is_super_defender:
		list_data = retrieve_post_data(post_type=post_type)
		if list_data:
			import csv
			
			###################################################################################
			# Exporting posting data
			if post_type == 'dl':
				filename = 'post_data.csv'
				with open(filename,'wb') as f:
					wtr = csv.writer(f)
					columns = ['User ID', 'Audience','Expiry','Comments', 'Alignment','Topic name', \
					'Origin', 'Link ID','Expiry_Time','Total Followers','Verified Followers','Description',\
					'Image_URL']
					wtr.writerow(columns)
					for json_row in list_data:
						data = json.loads(json_row)
						to_write = [data['uid'],data['aud'],data['exp'],data['coms'],data['align'],data['top'],data['orig'], \
						data['Lid'],exact_date(data['expt']),data['numf'],data['num_vf'],data['desc'].encode('utf-8'),\
						data.get('image',None)]
						wtr.writerows([to_write])
			
			###################################################################################
			# Exporting follow data
			elif post_type == 'fl':
				filename = 'follow_data.csv'
				with open(filename,'wb') as f:
					wtr = csv.writer(f)
					columns = ['Star ID', 'Follower ID','Origin','Action','Follower Verif Stat','Link_id', \
					'Object ID', 'Total Followers','Verified Followers']# TODO: create column  names
					wtr.writerow(columns)
					for json_row in list_data:
						data = json.loads(json_row)
						to_write = [data['star_id'],data['follower'],data['orig'],data['type'],data['v_stat'],data['lid'],data['obj_id'],data['numf'],data['num_vf']]# TODO: add relevant column data
						wtr.writerows([to_write])
			###################################################################################
			# Exporting post removal data
			elif post_type == 'rl':
				filename = 'post_removal_data.csv'
				with open(filename,'wb') as f:
					wtr = csv.writer(f)
					columns = ['Link ID','Poster Name','Poster ID','Remover Name','Origin of Removal','Is OP','Post Description', \
					'Image Link','Post data']# TODO: create column  names
					wtr.writerow(columns)

					for json_row in list_data:
						data = json.loads(json_row)
						if data['type'] == 'from my home':
							data2 = json.loads(data['post_details']['blob'])
			
						obj_hash_type =  data['lid'].split(':')
			
						if obj_hash_type[0] == 'tx':
							#writing data taken from redis
							if data['type'] == 'from my home':
								to_write = [data['lid'],data2['su'].encode('utf-8'),data2['si'],data['remover_name'].encode('utf-8'),data['type'],data['Is_OP'],data2['d'].encode('utf-8'),'NA',data2]# TODO: add relevant column data
							#writing data taken from Postgresql
							else:
								to_write = [data['lid'],data['remover_name'].encode('utf-8'),'OP from '+str(data['orig']),'remover is op = '+str(data['Is_OP']),'from history '+str(data['orig']),data['Is_OP'],data['description'].encode('utf-8'),data['image_file'],data]
								# to_write = [data['lid'],data2['su'],data2['si'],data['remover_name'],data['type'],data2['d'],'NA',data2]	
						else:
							#writing data taken from redis
							if data['type'] == 'from my home':
								to_write = [data['lid'],data2['su'].encode('utf-8'),data2['si'],data['remover_name'].encode('utf-8'),data['type'],data['Is_OP'],data2['d'].encode('utf-8'),data2['iu'],data2]# TODO: add relevant column data
							#writing data taken from Postgresql
							else:
								to_write = [data['lid'],data['remover_name'].encode('utf-8'),'OP from '+str(data['orig']),'remover is op = '+str(data['Is_OP']),'from history '+str(data['orig']),data['Is_OP'],data['description'].encode('utf-8'),data['image_file'],data]
						wtr.writerows([to_write])

	raise Http404("Completed ;)")