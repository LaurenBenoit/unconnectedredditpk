import ujson as json
import os, time, datetime, random, ast#, math
from collections import defaultdict, Counter
from operator import itemgetter
#from location import MEMLOC
from unconnectedreddit import celery_app1
from django.core.cache import get_cache, cache
from django.db.models import Count, Q, F, Sum
from datetime import datetime, timedelta
from django.utils import timezone
from cricket_score import cricket_scr
# from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from send_sms import process_sms, bind_user_to_twilio_notify_service, process_buyer_sms, send_personal_group_sms,\
process_user_pin_sms
from score import PUBLIC_GROUP_MESSAGE, PRIVATE_GROUP_MESSAGE, PUBLICREPLY, SHARE_ORIGIN,NUM_TO_DELETE,\
GIBBERISH_PUNISHMENT_MULTIPLIER
from models import Photo, LatestSalat, Photo, PhotoComment, Link, Publicreply, TotalFanAndPhotos, UserProfile, Cooldown, \
Video, HotUser, PhotoStream, HellBanList, UserFan
from redis3 import retrieve_random_pin, calculate_world_age_discount, log_gibberish_text_writer, get_gibberish_text_writers, \
set_world_age, queue_punishment_amount, save_used_item_photo, save_single_unfinished_ad, save_consumer_number, get_world_age, \
process_ad_final_deletion, process_ad_expiry, log_detail_click, remove_banned_users_in_bulk, log_404_errors, exact_date, \
ratelimit_banner_from_unbanning_target, is_mobile_verified, clean_log_logger
from redis5 import trim_personal_group, set_personal_group_image_storage, mark_personal_group_attendance, cache_personal_group_data,\
invalidate_cached_user_data, get_personal_group_anon_state, personal_group_soft_deletion, \
personal_group_hard_deletion, exited_personal_group_hard_deletion, update_personal_group_last_seen, set_uri_metadata_in_personal_group,\
rate_limit_personal_group_sharing, exit_user_from_targets_priv_chat
from redis4 import expire_online_users, get_recent_online, set_online_users, log_input_rate, log_input_text, retrieve_uname, retrieve_avurl, \
retrieve_credentials, invalidate_avurl, log_personal_group_exit_or_delete,log_share, logging_sharing_metrics, cache_photo_share_data, \
retrieve_bulk_unames, save_most_recent_online_users,sanitize_unused_subscriptions,log_1on1_chat, recreate_hell_banned_list
from redis6 import group_attendance, add_to_universal_group_activity, retrieve_single_group_submission, increment_pic_count,\
log_group_chatter, del_overflowing_group_submissions, empty_idle_groups, delete_ghost_groups, remove_inactive_members,\
retrieve_all_member_ids, group_owner_administrative_interest, hide_direct_response_in_group#, rank_mehfil_active_users
from redis7 import log_like, retrieve_obj_feed, add_obj_to_home_feed, get_photo_feed, add_photos_to_best_photo_feed, retrieve_text_obj_scores,\
insert_hash, retrieve_all_home_text_obj_names, delete_temporarily_saved_content_details, cleanse_inactive_complainers, account_created, set_top_stars, \
add_posts_to_best_posts_feed, add_single_trending_object, trim_expired_user_submissions, select_hand_picked_obj_for_trending,retire_abandoned_topics,\
queue_obj_into_trending, in_defenders, remove_obj_from_trending, calculate_top_trenders, calculate_trender_score, calculate_bayesian_affinity, \
cleanse_voting_records, study_voting_preferences,retrieve_img_obj_scores, add_single_trending_object_in_feed, cache_detailed_voting_data, \
cache_old_detailed_voting_data, get_best_home_feed, create_sybil_relationship_log, set_best_photo_for_fb_fan_page, can_post_image_on_fb_fan_page, \
archive_closed_objs_and_votes, hide_inline_direct_response
from redis9 import delete_all_direct_responses_between_two_users, cleanse_direct_response_list, submit_direct_response, set_comment_history, \
delete_single_direct_response, hide_direct_response_in_inbox, modify_direct_response_objs, log_direct_response_metrics, log_location_for_sender,\
delete_direct_responses_upon_obj_deletion, cleanse_replier_data_from_location, cleanse_replier_history_when_pvp_blocked, remove_1on1_direct_responses,\
log_rate_of_reply
from redis2 import trim_expired_fanouts, fan_out_to_followers,remove_follower, sanitize_posts_after_pvp_ban
from ecomm_tracking import insert_latest_metrics
from django.contrib.auth.models import User
from facebook_api import photo_poster
from redis3 import log_vote_disc
from redis8 import log_activity
from math import log

# from mixpanel import Mixpanel
# from unconnectedreddit.settings import MIXPANEL_TOKEN

# mp = Mixpanel(MIXPANEL_TOKEN)


def get_credentials(user_id, uname=None, avurl=None):
	if not uname and not avurl:
		# both dont exist
		uname, avurl = retrieve_credentials(user_id, decode_uname=True)
	elif avurl:
		# uname doesnt exist
		uname = retrieve_uname(user_id,decode=True)
	elif uname:
		# avurl desn't exist
		avurl = retrieve_avurl(user_id)
	else:
		# both exist, do nothing
		pass
	return uname, avurl


def hide_direct_response_in_db(obj_type, reply_id):
	"""
	When a sentence in comments is hidden, are there any "reply of reply" chats associated to it that need to be hidden too on the same page?
	"""
	# Retreive "replies to reply" that have replied to this particular reply_id, and set their addendums to 'hidden'
	if obj_type in ('3','4'):
		Publicreply.objects.filter(direct_reply=reply_id).update(direct_reply_tgt_text_prefix='', direct_reply_tgt_text_postfix='')
	else:
		pass


def set_rank(netvotes, upload_time):
	"""
	Based on reddit ranking algo at https://medium.com/hacking-and-gonzo/how-reddit-ranking-algorithms-work-ef111e33d0d9
	"""
	# if netvotes is None:
	#     netvotes = 0
	# order = log(max(abs(netvotes), 1), 10)
	# if netvotes > 0:
	#     sign = 1
	# else:
	#     sign = -1
	# secs = upload_time - 1432201843 # Thu, 21 May 2015 09:50:43 GMT coverted to epoch time
	# return round(sign * order + secs / 45000, 8)
	##############################################################################
	"""
	Added a time factor to ensure 'newer' photos are given more preference all else equal
	"""
	secs = upload_time - 1432201843 # Thu, 21 May 2015 09:50:43 GMT coverted to epoch time
	return round(netvotes+secs/45000,8)


@celery_app1.task(name='tasks.cache_photo_shares')
def cache_photo_shares(json_photo_data, user_id):
	cache_photo_share_data(json_photo_data, user_id)

@celery_app1.task(name='tasks.invalidate_avatar_url')
def invalidate_avatar_url(user_id,set_rate_limit=False):
	invalidate_avurl(user_id, set_rate_limit)
	invalidate_cached_user_data(user_id)

@celery_app1.task(name='tasks.photo_sharing_metrics_and_rate_limit')
def photo_sharing_metrics_and_rate_limit(sharer_id, photo_id, photo_owner_id, num_shares, sharing_time, group_ids):
	#rate limiting sharing
	rate_limit_personal_group_sharing(sharer_id)
	#logging metrics
	logging_sharing_metrics(sharer_id, photo_id, photo_owner_id, num_shares, sharing_time, group_ids)


@celery_app1.task(name='tasks.add_image_to_personal_group_storage')
def add_image_to_personal_group_storage(img_url, img_id, img_wid, hw_ratio, img_quality, blob_id, index, own_id, group_id, is_shared=False, op=None):
	if is_shared:
		set_personal_group_image_storage(img_url, img_id, img_wid, hw_ratio, img_quality, blob_id, index, own_id, group_id, True, op)
	else:
		set_personal_group_image_storage(img_url, img_id, img_wid, hw_ratio, img_quality, blob_id, index, own_id, group_id)


@celery_app1.task(name='tasks.personal_group_trimming_task')
def personal_group_trimming_task(group_id, object_count):
	trim_personal_group(group_id,object_count)


@celery_app1.task(name='tasks.cache_personal_group')
def cache_personal_group(pg_data, group_id):
	cache_personal_group_data(pg_data,group_id)


@celery_app1.task(name='tasks.private_chat_tasks')
def private_chat_tasks(own_id, target_id, group_id, posting_time, text, txt_type, own_anon='', target_anon='', blob_id='', idx='', img_url='', \
	own_uname='', own_avurl='',deleted='',hidden='',successful=True, from_dir_rep_list=False, sharing=False):
	if successful:
		mark_personal_group_attendance(own_id, target_id, group_id, posting_time)

		if txt_type == 'exited':
			own_id = str(own_id)
			log_personal_group_exit_or_delete(group_id, exit_by_id=own_id, action_type='exit')
			
			# ensuring both side don't have notifications in their inboxes anymore
			delete_single_direct_response(target_user_id=own_id, obj_type='7', parent_obj_id=group_id, sender_id=target_id)
			delete_single_direct_response(target_user_id=target_id, obj_type='7', parent_obj_id=group_id, sender_id=own_id)

			#ensuring own_id's 'reply activity' doesn't contain any trace of the exited 1on1
			cleanse_replier_data_from_location(obj_type='7', parent_obj_id=group_id, obj_owner_id=target_id, replier_ids=[own_id])
		
		else:
			own_uname, own_avurl = get_credentials(own_id, own_uname, own_avurl)
			target_uname = retrieve_uname(target_id,decode=True)

			# All txt_types are: 'notif','img','img_res','text','text_res','action','reentry','exited','creation','shared_img'
			if txt_type in ('text','img','shared_img','text_res','img_res'):
				set_uri_metadata_in_personal_group(own_id, text, group_id, blob_id, idx, txt_type)#Checks content and turns URLs clickable

			if from_dir_rep_list or sharing:
				update_personal_group_last_seen(own_id, group_id, posting_time)#supposed to update 'seen' of contributer

			########### GENERATE A DIR REP NOTIF ###########
			if own_anon == '1':
				sun = own_uname[:1].upper()
				group_name = '1 on 1 with {}'.format(sun.encode('utf-8'))
			elif own_anon == '0':
				sun = own_uname
				group_name = '1 on 1 with {}'.format(sun.encode('utf-8'))
			else:
				own_anon, target_anon, group_id = get_personal_group_anon_state(own_id,target_id)
				if own_anon:
					sun = own_uname[:1].upper()
					group_name = '1 on 1 with {}'.format(sun.encode('utf-8'))
				else:
					sun = own_uname
					group_name = '1 on 1 with {}'.format(sun.encode('utf-8'))

			# ensure a non-empty blob_id is passed, otherwise the code won't work correctly
			payload = {'tx':text,'tun':target_uname,'t':posting_time,'tid':target_id,'obid':None,\
				'sid':own_id,'dbid':blob_id if blob_id else '0','sun':sun,'ptun':None,'poid':group_id, \
				'ot':'7','idx':idx,'ptx':group_name}

			if img_url:
				payload['iu'] = img_url

			###############################################################
			# generating the actual reply for appearance in the 'direct response list' (in inbox) and the single notification across the website
			submit_direct_response(json_data=json.dumps(payload), time_now=posting_time, sender_id=own_id, target_user_id=target_id, \
				obj_type='7', parent_obj_id=group_id, reply_id=0)# reply_id doesn't matter for 1on1 groups
			
			###############################################################
			# delete the message that was responded to, if it exists in 'direct response list'
			delete_single_direct_response(target_user_id=own_id, obj_type='7', parent_obj_id=group_id, sender_id=target_id)

			###############################################################
			# generate footprint in 'reply history'
			log_location_for_sender(obj_type='7', obj_owner_id=target_id, parent_obj_id=group_id, replier_id=str(own_id),\
				target_uname=target_uname, time_now=posting_time, target_id=target_id)

			#################### Logging 1on1 message #####################
			# if txt_type == 'shared_img':
			# 	payload = str(posting_time)+":"+txt_type+":"+img_url[-47:]+":"+str(own_id)+":"+target_id+":"+text
			# else:
			# 	payload = str(posting_time)+":"+txt_type+":"+img_url+":"+str(own_id)+":"+target_id+":"+text
			# log_1on1_chat(payload=payload,oid=own_id,tid=target_id, group_id=group_id, is_creation=True if txt_type == 'creation' else False)
			###############################################################


@celery_app1.task(name='tasks.update_notif_object_anon')
def update_notif_object_anon(value,which_user,which_group):
	pass


@celery_app1.task(name='tasks.direct_response_tasks')
def direct_response_tasks(action_status, action_type, num_skips=None, parent_obj_id=None, obj_owner_id=None, obj_hash_name=None, \
	obj_type=None, commenter_id=None, time_now=None, log_location=False, target_uname=None, target_id=None, text_len=-1, \
	is_legacy_obj=False):
	"""
	Tasks to complete when a direct response is sent on a public post (text or image)
	"""
	############################
	if action_type == '1' and obj_type == '7':
		# don't log this metric for 1on1s
		pass
	else:
		# log the metric otherwise
		log_direct_response_metrics(action_status=action_status, action_type=action_type, num_skips=num_skips, obj_type=obj_type)
	
	############################
	if log_location:
		commenter_id = str(commenter_id)
		if (obj_type in ('3','4') and commenter_id == target_id):
			# don't log location when talking on own posts without a reference (since that's essentially talking to 'self')
			pass
		else:
			# otherwise, log the location for 'recent activity'
			log_location_for_sender(obj_type=obj_type, obj_owner_id=obj_owner_id, parent_obj_id=parent_obj_id, replier_id=commenter_id,\
				target_uname=target_uname, time_now=time_now, target_id=target_id)
	
	############################
	# it's a publicreply
	if obj_type == '3':
		# Logging who all visited a user's public posts
		set_comment_history(obj_hash_name=obj_hash_name, obj_owner_id=obj_owner_id, commenter_id=commenter_id, time_now=time_now)
		# Incrementing comment_count
		Link.objects.filter(id=parent_obj_id).update(reply_count=F('reply_count')+1)
		# Logging response rate (for rate limiting reasons)
		log_rate_of_reply(replier_id=commenter_id, text_len=text_len, time_now=time_now)
	
	# it's a photo comment
	elif obj_type == '4':
		# Logging who all visited a user's public posts
		set_comment_history(obj_hash_name=obj_hash_name, obj_owner_id=obj_owner_id, commenter_id=commenter_id, time_now=time_now)
		# Incrementing comment_count
		if is_legacy_obj:
			# this is a 'legacy' img obj - thus saved in the 'Photo' model
			Photo.objects.filter(id=parent_obj_id).update(comment_count=F('comment_count')+1)
		else:
			# this is a 'new' img obj - thus saved in the 'Link' model
			Link.objects.filter(id=parent_obj_id).update(reply_count=F('reply_count')+1)
		# Logging response rate (for rate limiting reasons)
		log_rate_of_reply(replier_id=commenter_id, text_len=text_len, time_now=time_now)


@celery_app1.task(name='tasks.hide_associated_direct_responses')
def hide_associated_direct_responses(obj_type,parent_obj_id,reply_id,sender_id,receiver_id,to_hide):
	"""
	Used when comments or chat is hidden in groups or in content comments, etc.
	"""
	hide_direct_response_in_inbox(obj_type=obj_type,parent_obj_id=parent_obj_id,reply_id=reply_id,to_hide=to_hide,sender_id=sender_id,\
	receiver_id=receiver_id)# in redis9
	
	# if the object in question belongs to the 'comments' ecosystem
	if obj_type in ('3','4'):
		# '3' is comment under text post, '4' is comment under img post
		hide_direct_response_in_db(obj_type, reply_id)
		hide_inline_direct_response(obj_type, parent_obj_id, reply_id)
	
	# if the object in question belongs to the 'mehfil' ecosystem
	elif obj_type in ('5','6'):
		# '5' is public, '6' is private
		hide_direct_response_in_group(obj_type, parent_obj_id,reply_id,to_hide)# redis6


@celery_app1.task(name='tasks.private_chat_seen')
def private_chat_seen(own_id, group_id, curr_time):
	"""
	Called every time a private chat is refreshed (or 'seen'). 

	But not called from 'from_unseen' or 'sharing'
	"""
	pass


# execute every 3 days
@celery_app1.task(name='tasks.delete_chat_from_idle_personal_group')
def delete_chat_from_idle_personal_group():
	deleted_group_ids_and_participants = personal_group_soft_deletion()
	if deleted_group_ids_and_participants:
		for group_id, user_1, user_2 in deleted_group_ids_and_participants:
			delete_single_direct_response(target_user_id=user_1, obj_type='7', parent_obj_id=group_id, sender_id=user_2)
			delete_single_direct_response(target_user_id=user_2, obj_type='7', parent_obj_id=group_id, sender_id=user_1)


# execute every 6 days
@celery_app1.task(name='tasks.delete_idle_personal_group')
def delete_idle_personal_group():
	deleted_group_ids_and_participants = personal_group_hard_deletion()
	if deleted_group_ids_and_participants:
		for group_id, user_1, user_2 in deleted_group_ids_and_participants:
			delete_single_direct_response(target_user_id=user_1, obj_type='7', parent_obj_id=group_id, sender_id=user_2)
			delete_single_direct_response(target_user_id=user_2, obj_type='7', parent_obj_id=group_id, sender_id=user_1)

# execute daily
@celery_app1.task(name='tasks.delete_exited_personal_group')
def delete_exited_personal_group():
	deleted_group_ids_and_participants = exited_personal_group_hard_deletion()
	if deleted_group_ids_and_participants:
		for group_id, user_1, user_2 in deleted_group_ids_and_participants:
			delete_single_direct_response(target_user_id=user_1, obj_type='7', parent_obj_id=group_id, sender_id=user_2)
			delete_single_direct_response(target_user_id=user_2, obj_type='7', parent_obj_id=group_id, sender_id=user_1)


@celery_app1.task(name='tasks.post_banning_tasks')
def post_banning_tasks(own_id, target_id):
	"""
	Remove's banner's notifications from from the bannee's inbox, also unfans them, and a bunch of other tasks!
	"""
	# this ensures they can't 1on1 chat with eachother
	# 1) Exit yourself if group is non-exited
	# 2) If 'target' has already exited group, tell them they can't re-enter because the other party outright blocked them!
	# 3) No notifications will be generated since we already sanitized each user's activity
	group_id, group_exists = exit_user_from_targets_priv_chat(own_id,target_id)
	if group_id:
		remove_1on1_direct_responses(group_id=group_id, first_user_id=target_id, second_user_id=own_id)
	################################################################################
	# remove any direct responses exchanged between the two (except for 1on1, which is handled in the previous step)
	delete_all_direct_responses_between_two_users(first_user_id=target_id, second_user_id=own_id)# order of passing user IDs does not matter
	################################################################################
	# ensure users custom home feeds are rid of eachother's content!
	sanitize_posts_after_pvp_ban(own_id, target_id)
	sanitize_posts_after_pvp_ban(target_id, own_id)
	################################################################################
	# remove eachother from follower lists
	verification_status = '1' if is_mobile_verified(target_id) else '0'
	remove_follower(follower_id=own_id,star_id=target_id,follower_verification_status=verification_status)

	verification_status = '1' if is_mobile_verified(own_id) else '0'
	remove_follower(follower_id=target_id,star_id=own_id,follower_verification_status=verification_status)
	################################################################################
	# remove locations owned by each other from 'reply history'
	cleanse_replier_history_when_pvp_blocked(replier_id_1=target_id, replier_id_2=own_id)
	################################################################################
	# we did a LOT of work, ensure banner didn't ban in vain!
	ratelimit_banner_from_unbanning_target(own_id,target_id)
	################################################################################


@celery_app1.task(name='tasks.sanitize_expired_bans')
def sanitize_expired_bans(own_id, banned_ids_to_unban):
	remove_banned_users_in_bulk(own_id, banned_ids_to_unban)


@celery_app1.task(name='tasks.increase_user_points')
def increase_user_points(user_id, increment):
	UserProfile.objects.filter(user_id=user_id).update(score=F('score')+increment)


@celery_app1.task(name='tasks.save_consumer_credentials')
def save_consumer_credentials(account_kit_id, mobile_data, user_id):
	save_consumer_number(account_kit_id=account_kit_id, mobile_data=mobile_data, user_id=user_id)


@celery_app1.task(name='tasks.save_unfinished_ad')
def save_unfinished_ad(context):
	save_single_unfinished_ad(context)


@celery_app1.task(name='tasks.save_ecomm_photo_hash')
def save_ecomm_photo_hash(photo1_payload, photo2_payload, photo3_payload):
	if photo1_payload:
		photo1_payload = ast.literal_eval(photo1_payload)
		insert_hash(photo1_payload[0],photo1_payload[1],'ecomm') #perceptual hash of item photo 1
	if photo2_payload:
		photo2_payload = ast.literal_eval(photo2_payload)
		insert_hash(photo2_payload[0],photo2_payload[1],'ecomm') #perceptual hash of item photo 2
	if photo3_payload:
		photo3_payload = ast.literal_eval(photo3_payload)
		insert_hash(photo3_payload[0],photo3_payload[1],'ecomm') #perceptual hash of item photo 3


@celery_app1.task(name='tasks.upload_ecomm_photo')
def upload_ecomm_photo(photo_id, user_id, ad_id):
	# insert_hash(photo_id, avghash, 'ecomm') #perceptual hash of the item photo
	save_used_item_photo(user_id, ad_id, photo_id)


@celery_app1.task(name='tasks.sanitize_unused_ecomm_photos')
def sanitize_unused_ecomm_photos():
	"""
	Scans all votes given by users and calculates sybil affinities via a Bayesian calculation

	Scheduled to run every 6 hours
	Mislabelled for legacy reasons
	"""
	study_voting_preferences()
	create_sybil_relationship_log()


@celery_app1.task(name='tasks.set_user_binding_with_twilio_notify_service')
def set_user_binding_with_twilio_notify_service(user_id,phone_number):
	bind_user_to_twilio_notify_service(user_id,phone_number)


# execute once a week
@celery_app1.task(name='tasks.expire_classifieds')
def expire_classifieds():
	"""
	Runs once a week - reconstructs the hell-banned list in redis from the DB

	Mislabeled due to legacy reasons
	"""
	recreate_hell_banned_list()


# execute every 2 days
@celery_app1.task(name='tasks.delete_expired_classifieds')
def delete_expired_classifieds():
	process_ad_final_deletion()


# execute every 24 hours
@celery_app1.task(name='tasks.calc_ecomm_metrics')
def calc_ecomm_metrics():
	insert_latest_metrics()


@celery_app1.task(name='tasks.log_user_action')
def log_user_activity(user_id, activity_dict, time_now, which_var=None):
	"""
	Logs user actions for retention analysis
	"""
	log_activity(user_id=user_id, activity_dict=activity_dict, time_now=time_now, which_var=which_var)


# @celery_app1.task(name='tasks.log_reply_rate')
# def log_reply_rate(replier_id, text, time_now, reply_target, marked_fast):
# 	"""
# 	TODO: temp logger that should be removed
# 	"""
# 	log_replier_reply_rate(replier_id, text, time_now, reply_target, marked_fast)


# @celery_app1.task(name='tasks.log_mehfil_reply')
# def log_mehfil_reply(replier_id, text, mehfil_type, time_now, reply_target):
# 	"""
# 	TODO: temp logger that should be removed
# 	"""
# 	log_mehfil_replier_reply_rate(replier_id=replier_id, text=text, time_now=time_now, target_id=reply_target, mehfil_type=mehfil_type)


# @celery_app1.task(name='tasks.set_section_retention')
# def set_variation_retention(user_id, which_var=None):
# 	"""
# 	Logs users for retention calculation of various cohorts

# 	'which_var' is the name of an experimental variation currently under progress
# 	"""
# 	set_variation_wise_retention(user_id,which_var=which_var)


@celery_app1.task(name='tasks.set_user_age')
def set_user_age(user_id):
	"""
	Task that increments user's age in the world
	"""
	set_world_age(user_id)


@celery_app1.task(name='tasks.log_404')
def log_404(type_of_404, time_of_404, type_of_url=None):
	"""
	Logs 404 errors seen throughout the website

	Currently only logging 404 errors emanating from UserProfilePhotosView()
	"""
	log_404_errors(type_of_404, time_of_404, type_of_url)


@celery_app1.task(name='tasks.save_online_user')
def save_online_user(user_id,user_ip):
	set_online_users(str(user_id),str(user_ip),get_world_age(user_id))


@celery_app1.task(name='tasks.whoseonline')
def whoseonline():
	"""
	Periodically assesses who all is online (to be shown to users in a global online page)
	"""
	user_ids_and_ages = get_recent_online()
	save_most_recent_online_users(user_ids_and_ages)


@celery_app1.task(name='tasks.detail_click_logger')
def detail_click_logger(ad_id, clicker_id):
	log_detail_click(ad_id, clicker_id)


@celery_app1.task(name='tasks.enqueue_sms')
def enqueue_sms(mobile_number, ad_id, status=None, buyer_number=None, item_name=None):
	process_sms(mobile_number,ad_id,status, buyer_number, item_name)


@celery_app1.task(name='tasks.enqueue_buyer_sms')
def enqueue_buyer_sms(mobile_number, ad_id, order_data, buyer_number=None):
	cleansed_data = "Name="+str(order_data['firstname'])+",City="+ str(order_data['address'])+",Phone=+92"+str(order_data['phonenumber'][1:])+",Order#="+ str(order_data['order_id'])+",Model="+str(order_data['model'])
	process_buyer_sms(mobile_number,ad_id,str(cleansed_data), buyer_number)


@celery_app1.task(name='tasks.enqueue_orderer_sms')
def enqueue_orderer_sms(mobile_number, ad_id, order_data, buyer_number=None):
	cleansed_data = "Assalam-o-Alikum! Apka "+str(order_data['model'])+" ka order hamarey pas agya hai. Mobile shop ka numainda apko jald call keray ga. Shukriya :-)"
	process_buyer_sms(mobile_number,ad_id,str(cleansed_data), buyer_number)

@celery_app1.task(name='tasks.send_orderer_pin')
def send_orderer_pin(mobile_number, pin, order_data, buyer_number=None):
	cleansed_data = "Aap ka pin code hai '"+str(pin)+"'. Iss pin ko mobile shop ki confirm order ki screen per dalien aur apna "+str(order_data)+" ghar mangaien."
	cleansed_data2 = "Pin code: '"+str(pin)+"' Mob# "+str(mobile_number)+"' Phone model: "+str(order_data)
	mobile_number2 = '+923491058364'
	process_buyer_sms(mobile_number,pin,str(cleansed_data), buyer_number)
	process_buyer_sms(mobile_number2,pin,str(cleansed_data2), buyer_number)

@celery_app1.task(name='tasks.send_user_pin')
def send_user_pin(sender_id, mobile_number):
	"""
	This function sends the pin code to user (for home-grown verification purposes)
	"""
	pin = retrieve_random_pin(sender_id)
	payload = "Salam! %s apka Damadam pin code hai. Isko pin code wali screen mein enter karein. Have a nice day & enjoy Damadam.pk :-)" % (pin)
	process_user_pin_sms(mobile_number,payload)

@celery_app1.task(name='tasks.enqueue_query_sms')
def enqueue_query_sms(mobile_number, ad_id, order_data, buyer_number=None):
	cleansed_data = "Assalam-o-Alikum! Apko 03105430851 se Damadam Mobile Shop ka numainda rabta kare ga. Ap khud bhi is number per rabta kr sakte hein. Shukriya :-)"
	process_buyer_sms(mobile_number,ad_id,str(cleansed_data), buyer_number)

@celery_app1.task(name='tasks.delete_notifications')
def delete_notifications(user_id):
	pass
	# clean_expired_notifications(user_id)

@celery_app1.task(name='tasks.calc_gibberish_punishment')
def calc_gibberish_punishment():
	"""
	Scheduled task to calculate 'like_probs' of voters/likers

	Mislabeled for legacy reasons
	"""
	archive_closed_objs_and_votes()


@celery_app1.task(name='tasks.calc_photo_quality_benchmark')
def calc_photo_quality_benchmark():
	pass

@celery_app1.task(name='tasks.bulk_create_notifications')
def bulk_create_notifications(user_id, photo_id, epochtime, photourl, name, caption):
	pass

@celery_app1.task(name='tasks.trim_whose_online')
def trim_whose_online():
	expire_online_users()


@celery_app1.task(name='tasks.trim_top_group_rankings')
def trim_top_group_rankings():
	"""
	Periodically trim the global sets containing all public submissions flowing into Damadam

	Mislabeled for legacy reasons
	"""
	time_now = time.time()

	# Step 1) taking care of user feeds in redis 9
	trim_expired_fanouts(time_now=time_now)# trims expired fan outs

	# Step 2) taking care of global feeds in redis 7
	trim_expired_user_submissions(time_now=time_now)# trims content submitted to public feeds (e.g. home, photos)


@celery_app1.task(name='tasks.remove_target_users_posts_from_all_feeds')
def remove_target_users_posts_from_all_feeds(target_user_id, cleanse_feeds):
	"""
	If defender bans a user, remove said users' content from all current feeds
	"""
	# Step 1) taking care of user feeds in redis 9
	deleted_fanned_out_objs = trim_expired_fanouts(submitter_id=target_user_id)

	# Step 2) taking care of global feeds in redis 7
	trim_expired_user_submissions(submitter_id=target_user_id, cleanse_feeds=cleanse_feeds, already_deleted_objs=deleted_fanned_out_objs)
	



@celery_app1.task(name='tasks.delete_temporarily_saved_content_data')
def delete_temporarily_saved_content_data(own_id):
	"""
	Delete temporarily saved data
	"""
	delete_temporarily_saved_content_details(own_id)


#paying back points spent by photo reporters
@celery_app1.task(name='tasks.process_reporter_payables')
def process_reporter_payables(payables):
	"""
	Paying back points spent by reporters (currently points paid are set to 0)
	"""
	if payables:
		for user_id,payable_score in payables:
			if payable_score:
				UserProfile.objects.filter(user_id=user_id).update(score=F('score')+payable_score)


# @celery_app1.task(name='tasks.populate_search_thumbs')
# def populate_search_thumbs(user_id,ids_with_urls):
# 	"""
# 	Auto-populating photo thumbs in search results, end of photo comments, etc

# 	Triggered whenever a user profile is visited
# 	"""
# 	bulk_add_search_photos(user_id,ids_with_urls)


@celery_app1.task(name='tasks.document_administrative_activity')
def document_administrative_activity(group_id, main_sentence, history_type):
	"""
	Logs an action in a mehfil's administrative activity

	Moreover, acts as a helper function for construct_administrative_activity()
	"""
	add_to_universal_group_activity(group_id, main_sentence, history_type)

@celery_app1.task(name='tasks.construct_administrative_activity')
def construct_administrative_activity(punisher_id, target_id, time_now, group_id, history_type, reply_id=None):
	"""
	Logs 'hide' and 'unhide' activity in publc mehfil administrative history

	A more involved version of document_administrative_activity() since it constructs the main sentence itself
	In the end, it calls document_administrative_activity() to get the job done
	"""    
	username_dictionary = retrieve_bulk_unames([punisher_id,target_id],decode=True)
	text = retrieve_single_group_submission(group_id, reply_id, text_only=True)
	if history_type == 'hide':
		partial_sentence = username_dictionary[punisher_id]+" ne "+username_dictionary[int(target_id)]+\
		" ki baat hide ki at {0}".format(exact_date(time_now))
	elif history_type == 'unhide':
		partial_sentence = username_dictionary[punisher_id]+" ne "+username_dictionary[int(target_id)]+\
		" ki baat unhide ki at {0}".format(exact_date(time_now))
	main_sentence = partial_sentence+". Text: "+text if text else partial_sentence
	document_administrative_activity(group_id, main_sentence, history_type)


@celery_app1.task(name='tasks.cleanse_complainers')
def cleanse_complainers():
	cleanse_inactive_complainers()


@celery_app1.task(name='tasks.rank_mehfils')
def rank_mehfils():
	pass
	# rank_mehfil_active_users()


@celery_app1.task(name='tasks.public_group_ranking_clean_up_task')
def public_group_ranking_clean_up_task():
	"""
	Calculates top list of photo-uploaders who have highest contributions to trending photos in a specific time period

	Mislabeled task due to legacy reasons
	"""
	calculate_top_trenders()
	###############################
	# giving each 'star' a score depending on ratio of pics in trending and recency of uploaded trending images
	calculate_trender_score()


@celery_app1.task(name='tasks.log_group_owner_interaction')
def log_group_owner_interaction(group_id, time_now):
	"""
	Logs the last 'seen' time of when a group owner did something meaninful in their public group
	"""
	group_owner_administrative_interest(group_id, time_now)


@celery_app1.task(name='tasks.group_attendance_tasks')
def group_attendance_tasks(group_id,user_id, time_now):#, private=False):
	"""
	Tracking user presence in a group so that we can show online users in a group or show their 'online' dots
	"""
	inactive_user_ids = group_attendance(group_id,user_id, time_now)
	if inactive_user_ids:
		remove_inactive_members(inactive_user_ids, group_id, time_now)

@celery_app1.task(name='tasks.update_group_topic')
def update_group_topic(group_id, topic, group_type):
	"""
	Updates group topic in notification object
	"""
	modify_direct_response_objs(parent_obj_type=group_type, parent_obj_id=group_id, modification_type='topic', payload=topic)

#####################################################################################################

# execute every 2 days
@celery_app1.task(name='tasks.empty_idle_public_and_private_groups')
def empty_idle_public_and_private_groups():
	"""
	Deletes all chat within an 'empty' group

	Idle groups are those that don't have any activity for 7 days (activity includes refreshes!)
	"""
	empty_idle_groups()


# execute every 4 days
@celery_app1.task(name='tasks.delete_idle_public_and_private_groups')
def delete_idle_public_and_private_groups():
	"""
	Deleting 'ghost' groups for good (when it's been idle for 30 days, we call it a 'ghost' group)
	"""
	# grp_ids_and_members is a dict of the sort { group_id:[member_ids] }

	deleted_groups = delete_ghost_groups()#redis6
	for group_id, group_type in deleted_groups:
		if group_type == 'public':
			delete_direct_responses_upon_obj_deletion(obj_type='5', obj_id=group_id)# deleting 'direct resposes' given in the group
		elif group_type == 'private':
			delete_direct_responses_upon_obj_deletion(obj_type='6', obj_id=group_id)# deleting 'direct resposes' given in the group
		else:
			pass


@celery_app1.task(name='tasks.trim_group_submissions')
def trim_group_submissions(group_id):
	"""
	Trims down mehfil submissions once it attains a certain size
	"""
	del_overflowing_group_submissions(group_id,NUM_TO_DELETE)


@celery_app1.task(name='tasks.group_notification_tasks')
def group_notification_tasks(group_id,sender_id,group_owner_id,topic,reply_time,poster_url,poster_username,reply_text,priv,\
	image_url,priority,from_unseen, slug=None, txt_type=None, notify_single_user=False, single_target_id=None):
	if txt_type == 'join':
		pass
	else:
		if priv == '1':
			log_group_chatter(group_id, sender_id)# redis 6
			if image_url:
				increment_pic_count(group_id, sender_id)#redis 6
	

@celery_app1.task(name='tasks.rank_all_photos')
def rank_all_photos():
	"""
	Used to find the single "best" photo from the current lot, criteria being an image with positive cumulative vote score, and at least 1 downvote

	Can also push hand-picked objects into trending lists (disabled for now)
	Mislabeled task due to legacy reasons
	"""
	time_now = time.time()
	pushed, obj_id, audience = select_hand_picked_obj_for_trending()#push_hand_picked_obj_into_trending()
	if pushed and obj_id and audience == 'p':
		#####################################################
		# if it wasn't already added to the sitemap - add it now so that crawlers can index the image
		if not Cooldown.objects.filter(content_id=obj_id).exists():
			cohort_num = int(time_now/604800)#cohort size is 1 week
			Cooldown.objects.create(content_id=obj_id,hot_score=cohort_num)
		#####################################################
		# Also send image to Facebook fan page (every few hours)
		if can_post_image_on_fb_fan_page():
			photo = Link.objects.only('image_file','description','submitter__username').get(id=obj_id)
			photo_poster(image_obj=photo.image_file, image_caption=photo.description, owner_username=photo.submitter.username, \
				photo_id=obj_id)
			set_best_photo_for_fb_fan_page(obj_id)
		#####################################################
	else:
		pass
		#####################################################
		# TODO : activate when 'handpicked_prob' has been built
		# fresh_photo_ids = get_photo_feed(feed_type='fresh_photos')#fresh photos in hash format
		# best_photo_ids = get_photo_feed(feed_type='best_photos')#trending photos in hash format
		# remaining_fresh_photo_ids = [id_ for id_ in fresh_photo_ids if id_ not in best_photo_ids]#unselected photos so far
		# trending_item_hash_name, item_score = extract_trending_obj(remaining_fresh_photo_ids, with_score=True)
		# if trending_item_hash_name:
		# 	highest_ranked_photo = retrieve_obj_feed([trending_item_hash_name])[0]
		# 	highest_ranked_photo['tos'] = time_now
		# 	highest_ranked_photo['like_prob'] = item_score# what probability exists that this content will be liked by at least 1 audience member
		# 	obj_id = trending_item_hash_name.split(":")[1]
		# 	add_single_trending_object(prefix="img:",obj_id=trending_item_hash_name.split(":")[1], obj_hash=highest_ranked_photo)
		# 	pushed = True


@celery_app1.task(name='tasks.rank_all_photos1')
def rank_all_photos1():
	"""
	Sanitize unused notification subscriptions
	"""
	sanitize_unused_subscriptions()


def extract_trending_obj(obj_hash_names, obj_type='img', with_score=False):
	"""
	Given a list of hashes, singles out the hash_obj which tops our score criteria

	Current criteria requires the top most obj to have the highest cumulative_vote_score but with at least one downvote
	"""
	only_liked = []
	if obj_type == 'img':
		obj_list = retrieve_img_obj_scores(obj_hash_names)
		for obj_hash, likes, score in obj_list:
			# ensure that the post is liked and has a positive 'score' (score is the prob it will get 'handpicked')
			
			if likes > 0 and score > 0:
				only_liked.append((obj_hash, score))# using 'score' as a means of ranking images (this is a measure of voter rep)
	
	elif obj_type == 'tx':
		obj_list = retrieve_text_obj_scores(obj_hash_names)
		for obj_hash, likes, score in obj_list:
			# ensure that the post is liked and has a positive 'score' (we don't have voter reps here yet)
			
			if likes > 0 and score > 0:
				only_liked.append((obj_hash, likes))# using 'likes' as a means of ranking texts

	#########################################
	# run this only when at least 2 posts are competing against one another - otherwise don't push anything into trending!
	if len(only_liked) > 1:

		only_liked.sort(key=itemgetter(1),reverse=True)
		trending_item_hash_name = only_liked[0][0]

		if with_score:
			return trending_item_hash_name, with_score
		else:
			return trending_item_hash_name

	###########################################

	if with_score:
		return '', None
	else:
		return ''


@celery_app1.task(name='tasks.rank_home_posts')
def rank_home_posts():
	"""
	Celery scheduled task used to create a 'best' list of home posts
	"""
	# Step 1) Isolate all fresh text posts (only 'text' - no 'img' type objs)
	fresh_obj_hashes = retrieve_all_home_text_obj_names()#get_home_feed()
	
	# Step 2) Isolate all best text posts
	trending_obj_hashes = get_best_home_feed(trending_home=True)
	
	# Step 3) Filter out fresh posts that are already in best
	if trending_obj_hashes:
		remaining_obj_hashes = [obj_hash_name for obj_hash_name in fresh_obj_hashes if obj_hash_name not in trending_obj_hashes]
	else:
		remaining_obj_hashes = fresh_obj_hashes
	
	# Step 4) From the remainder, extract the next 'best' text obj
	trending_item_hash_name = extract_trending_obj(remaining_obj_hashes, obj_type='tx')
	
	# Step 5) If trending obj has been found, push it into best
	if trending_item_hash_name:
		add_single_trending_object_in_feed(trending_item_hash_name, time.time())


@celery_app1.task(name='tasks.set_input_history')
def set_input_history(section,section_id,text,user_id):
	"""
	Keeps check of writing histories to rate limit repeated posting
	"""
	log_input_text(section,section_id,text,user_id)


@celery_app1.task(name='tasks.set_input_rate_and_history')
def set_input_rate_and_history(section,section_id,text,user_id,time_now):
	"""
	Keeps check of writing rates to rate limit abusive users
	"""
	log_input_text(section, section_id,text,user_id)
	log_input_rate(section,user_id,time_now)


@celery_app1.task(name='tasks.rank_photos')
def rank_photos():
	"""
	Calculates voting rep of voters, and expires rep older than 3 months

	Mislabeled due to legacy reasons
	"""
	pass


@celery_app1.task(name='tasks.fans')
def fans():
	"""
	Cleans up expired (i.e. old) direct responses

	Mislabeled due to legacy reasons
	"""
	cleanse_direct_response_list()


@celery_app1.task(name='tasks.salat_info')
def salat_info():
	"""
	deletes topics that are not getting any traffic

	Mislabeled due to legacy reasons
	"""
	retire_abandoned_topics()


@celery_app1.task(name='tasks.salat_streaks')
def salat_streaks():
	"""
	Cleans up user voting records saved in Redis
	Cleans auth details of users who have not been active since one year

	Mislabeled due to legacy reasons
	"""
	cleanse_voting_records()
	clean_log_logger()


@celery_app1.task(name='tasks.photo_upload_tasks')
def photo_upload_tasks(user_id, photo_id, upload_time, obj_hash_name, total_score):
	"""
	Tasks fired when a photo is uploaded in the photos section (for public viewing)
	"""
	pass
	# photo_img_file = Link.objects.only('image_file').get(id=photo_id).image_file
	# add_search_photo(photo_img_file, photo_id,user_id)# only adds public photo
	########################################################################
	# This determines whether to add the image into home's live feed (based on score of last few photos)
	# if total_score > PHOTO_HOT_SCORE_REQ:
	# 	add_obj_to_home_feed(user_id, upload_time, obj_hash_name)
	########################################################################
	# This saves the 'benchmark' score of the poster, helps in deciding whether to broadcast image in fans' matka or not
	# if number_of_photos:
	# 	set_uploader_score(user_id, ((total_score*1.0)/number_of_photos))


@celery_app1.task(name='tasks.cache_voting_history')
def cache_voting_history(user_id, page_num, json_data, data_type='new'):
	"""
	Caches voting history
	"""
	if data_type == 'old':
		# this caches voting history on 'old' user objects (pre-Follow feature)
		cache_old_detailed_voting_data(json_data=json_data, page_num=page_num, user_id=user_id)
	else:
		# this caches voting history on 'new' user objects (post-Follow feature)
		cache_detailed_voting_data(json_data=json_data, page_num=page_num, user_id=user_id)


@celery_app1.task(name='tasks.vote_tasks')
def vote_tasks(own_id, target_user_id, target_obj_id, revert_prev, is_pht, time_of_vote, is_editorial_vote):
	"""
	Processes vote on a post by a user

	Handles both textual or photo voting, both like and like-reversion
	"""
	if revert_prev:
		# undo a previous 'like'
		new_net_votes = log_like(obj_id=target_obj_id, own_id=own_id, revert_prev=True, is_pht=is_pht, target_user_id=target_user_id,\
			time_of_vote=time_of_vote, is_editorial_vote=is_editorial_vote)
		if is_pht == '1' and new_net_votes >= 0:
			# is a photo object
			# update_object(object_id=target_obj_id,object_type='0',vote_score=new_net_votes, just_vote=True)# updates vote count attached to notification object of photo
			# if it's a 'like' by a super-defender, handpick the object
			is_defender, is_super_defender = in_defenders(own_id, return_super_status=True)
			if is_super_defender:
				remove_obj_from_trending(prefix='img:',obj_id=target_obj_id)
	else:
		# cast a simple 'like' vote
		world_age_discount = calculate_world_age_discount(user_id=own_id)
		new_net_votes = log_like(obj_id=target_obj_id, own_id=own_id, revert_prev=False, is_pht=is_pht, target_user_id=target_user_id,\
			time_of_vote=time_of_vote, world_age_discount=world_age_discount, is_editorial_vote=is_editorial_vote)
		if is_pht == '1' and new_net_votes >= 0:
			# is a photo object
			# update_object(object_id=target_obj_id,object_type='0',vote_score=new_net_votes, just_vote=True)# updates vote count attached to notification object of photo
			# if it's a 'like' by a super-defender, handpick the object
			is_defender, is_super_defender = in_defenders(own_id, return_super_status=True)
			if is_super_defender:
				queue_obj_into_trending(prefix='img:',obj_owner_id=target_user_id,obj_id=target_obj_id,picked_by_id=own_id)


@celery_app1.task(name='tasks.registration_task')
def registration_task(ip,username):
	account_created(ip,username)

@celery_app1.task(name='tasks.log_sharing_click')
def log_sharing_click(photo_id, photo_owner_id, sharer_id, share_type, origin_key):
	try:
		origin = SHARE_ORIGIN[origin_key]
	except KeyError:
		origin = None
	log_share(photo_id, photo_owner_id, sharer_id, share_type, origin)


@celery_app1.task(name='tasks.publicreply_tasks')
def publicreply_tasks(user_id, reply_id, link_id, description, epochtime, is_someone_elses_post, link_writer_id):
	Link.objects.filter(id=link_id).update(reply_count=F('reply_count')+1, latest_reply=reply_id)  #updating comment count and latest_reply for DB link


@celery_app1.task(name='tasks.publicreply_notification_tasks')
def publicreply_notification_tasks(link_id,sender_id,link_submitter_url,link_submitter_id,link_submitter_username,link_desc,\
	reply_time,reply_poster_url,reply_poster_username,reply_desc,is_welc,reply_count,priority,from_unseen):
	pass


#############################################################################################################################
###################################################### Fanout ###############################################################
#############################################################################################################################

@celery_app1.task(name='tasks.post_to_followers')
def post_to_followers(own_id,obj_hash,time_now,expire_at,follower_list):
	"""
	"""
	fan_out_to_followers(own_id,obj_hash,time_now,expire_at,follower_list)

#############################################################################################################################
#############################################################################################################################

obj1 = locals()['expire_classifieds']# this recreated the hell-banned list in redis from the DB (upon startup)
obj1.run()