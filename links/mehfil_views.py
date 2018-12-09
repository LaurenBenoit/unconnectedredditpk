import ujson as json
import random, uuid, time
from operator import itemgetter
from brake.decorators import ratelimit
# from user_sessions.models import Session
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.edit import CreateView, FormView
from django.core.urlresolvers import reverse_lazy, reverse
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import redirect, render
from django.contrib.auth.models import User
from django.views.generic import ListView
from django.core.cache import get_cache
from django.http import HttpResponse
from django.middleware import csrf
from django.utils import timezone
from django.http import Http404
from django.db.models import F
from verified import FEMALES
from templatetags.s3 import get_s3_object
from page_controls import GROUPS_PER_PAGE
from imagestorage import upload_image_to_s3
from judgement_views import ordered_list_of_tup
from image_processing import process_group_image

from group_views import retrieve_user_env, get_indices

from models import Group, Reply, HellBanList, UserProfile, GroupBanList

from views import condemned, valid_uuid, convert_to_epoch, get_page_obj, get_price

from redis3 import del_from_rankings, retrieve_mobile_unverified_in_bulk, is_mobile_verified, tutorial_unseen, get_ranked_public_groups,\
exact_date

from redis4 import set_text_input_key, retrieve_credentials,retrieve_bulk_credentials,retrieve_uname, retrieve_bulk_unames,\
get_most_recent_online_users

from redis2 import update_notification, remove_group_notification, remove_group_object, get_replies_with_seen,create_notification, create_object, \
bulk_remove_group_notification

from tasks import log_private_mehfil_session, set_input_rate_and_history, group_notification_tasks, group_attendance_tasks, rank_public_groups,\
construct_administrative_activity, update_group_topic, trim_group_submissions, document_administrative_activity

from redis1 import bulk_check_group_invite, bulk_check_group_membership, get_group_members, add_group_member, remove_group_invite, add_user_group,\
remove_all_group_members, remove_latest_group_reply, check_group_member, check_group_invite, add_group_invite, set_latest_group_reply, get_user_groups, \
get_latest_group_replies, get_active_invites, remove_group_members,bulk_remove_user_group, legacy_mehfil_exit#, remove_group_member, remove_user_group

from mehfil_forms import PrivateGroupReplyForm, PublicGroupReplyForm, ReinviteForm, ReinvitePrivateForm, GroupTypeForm, ChangePrivateGroupTopicForm,\
ChangeGroupTopicForm, ChangeGroupRulesForm, GroupHelpForm, ClosedGroupHelpForm, DirectMessageCreateForm, DirectMessageForm, ClosedGroupCreateForm, \
OpenGroupCreateForm, OpenGroupHelpForm, GroupFeedbackForm, GroupPriceOfferForm, OfficerApplicationForm#, GroupOnlineKonForm

from score import PRIVATE_GROUP_MESSAGE, PUBLIC_GROUP_MESSAGE, POINTS_DEDUCTED_WHEN_GROUP_SUBMISSION_HIDDEN, PRIVATE_GROUP_COST, PUBLIC_GROUP_COST,\
PRIVATE_GROUP_MAX_TITLE_SIZE, PUBLIC_GROUP_MAX_TITLE_SIZE, PUBLIC_GROUP_MAX_RULES_SIZE, GROUP_FEEDBACK_SIZE, MAX_OWNER_INVITES_PER_PUBLIC_GROUP,\
MAX_OFFICER_INVITES_PER_PUBLIC_GROUP, CANCEL_INVITE_AFTER_TIME_PASSAGE, PUBLIC_GROUP_MAX_SELLING_PRICE, USER_AGE_AFTER_WHICH_PUBLIC_MEHFIL_CAN_BE_CREATED,\
GROUP_AGE_AFTER_WHICH_IT_CAN_BE_TRANSFERRED, PUBLIC_GROUP_MIN_SELLING_PRICE, GROUP_MEMBERS_PER_PAGE, GROUP_VISITORS_PER_PAGE, PRIVATE_GROUP_MAX_MEMBERSHIP,\
MAX_OWNER_INVITES_PER_PRIVATE_GROUP, MIN_MEMBERSHIP_AGE_FOR_GIVING_PUBLIC_GRP_FEEDBACK, MIN_MEMBERSHIP_AGE_FOR_REQUESTING_GRP_OWNERSHIP, \
MAX_MEMBER_INVITES_PER_PRIVATE_GROUP, DELETION_THRESHOLD, MEHFIL_REPORT_PROMPT, MAX_OFFICER_APPOINTMENTS_ALLWD, GROUP_OFFICER_QUESTIONS, \
MIN_APP_MEMBERSHIP_AGE_FOR_REQUESTING_GRP_OFFICERSHIP, MIN_GRP_MEMBERSHIP_AGE_FOR_REQUESTING_GRP_OFFICERSHIP, TOTAL_LIST_SIZE, MEHFIL_LIST_PAGE_SIZE

from redis6 import appoint_public_mehfil_officer, is_officer_appointments_rate_limited, retrieve_cached_attendance_data, get_latest_presence, \
cache_group_attendance_data, get_attendance, retrieve_all_officers, remove_public_mehfil_officers, retrieve_group_category, save_group_submission, \
retrieve_group_submissions, retrieve_cached_mehfil_replies, group_submission_exists, invalidate_cached_mehfil_replies, hide_group_submission,\
temporarily_save_group_credentials, get_temporarily_saved_group_credentials, rate_limit_group_creation, retrieve_group_rules, save_group_rules, \
create_group_credentials, cache_mehfil_replies, is_group_creation_rate_limited, permanently_delete_group, invalidate_presence, retrieve_group_topic, \
retrieve_group_meta_data, hide_writers_group_messages, is_group_member_and_rules_signatory, create_group_membership_and_rules_signatory, rescind_offer,\
insert_rules_signatory, retrieve_group_id, retrieve_group_owner_id, retrieve_group_privacy, retrieve_group_owner_unames_and_uniques_and_topics_in_bulk,\
save_group_topic_and_rules, invalidate_all_rule_signatories, purge_group_membership, purge_group_invitation, save_group_invite, remove_group_officer,\
group_member_exists, retrieve_immune_ids, group_officer_targeted, kick_users_from_group, is_group_officer, add_kick_feedback, banned_from_group,\
get_ban_details, unkick_users_from_group, add_unkick_feedback, retrieve_group_administrative_activity, filter_non_members, filter_non_recents,\
retrieve_kicked_user_ids, retrieve_group_officer_perms, get_group_info, show_public_group_invite_instructions,retrieve_open_group_remaining_invites, \
invite_allowed, retrieve_outstanding_invite_report, log_open_group_feedback, save_officer_application, rescind_officer_applications, exit_group, \
can_officer_kick_out, retrieve_open_group_feedback, delete_specific_group_feedback, retrieve_outstanding_requests, can_leave_group, get_prev_request,\
accept_group_ownership_transfer_request, retrieve_offer_details, group_ownership_transfer_blocked_by_rate_limit, retrieve_group_creation_time,\
submit_group_ownership_request, cancel_invite, is_ownership_request_legit, save_group_topic, retrieve_group_owner_uname,retrieve_group_joining_time,\
retrieve_all_member_ids, cache_group_membership_data, retrieve_cached_membership_data, retrieve_group_buying_time_and_price,retrieve_group_uuid, \
get_num_group_members, show_private_group_invite_instructions, retrieve_group_topic_log, retrieve_biggest_pic_sharer_in_group,retrieve_group_chatter, \
retrieve_closed_group_remaining_invites, recently_quit_group, can_officer_change_topic, hide_private_group_submission, retrieve_single_group_submission,\
retrieve_group_reqd_data, is_ownership_transfer_frozen, is_deletion_frozen, is_membership_frozen, retrieve_cached_ranked_groups, cache_ranked_groups, \
get_ranked_mehfils, retrieve_single_group_application, officer_appointed_too_many_times, retrieve_all_current_applications, officer_application_exists,\
retrieve_officer_stats, invalidate_cached_ranked_groups, invalidate_cached_mehfil_pages, retrieve_cached_mehfil_pages, retrieve_topic_and_rules_ttl, \
cache_mehfil_pages#, cache_mehfil_list#, retrieve_latest_group_replies, remove_public_mehfil_captain


################################### Mehfil info #####################################

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def display_group_info_page(request):
	"""
	Renders a public or private mehfil's info page
	"""
	if request.method == "POST":
		group_uuid = request.POST.get("guid",None)
		if group_uuid:
			group_id = retrieve_group_id(group_uuid)
			own_id = request.user.id
			if group_member_exists(group_id, own_id):
				is_public = False if retrieve_group_privacy(group_id) == '1' else True
				data = get_group_info(group_id, is_public = is_public)
				data['uj'] = retrieve_group_joining_time(group_id, own_id)# this is different for each user, so retrieved separately
				if is_public:
					data['7nm'] = int(data['7nm']) if '7nm' in data else 0
				return render(request,"mehfil/group_info.html",{'data':data,'guid':group_uuid, 'is_public':is_public})
			else:
				# not a member or group does not exist
				return redirect("group_page")
		else:
			# no group uuid available
			return redirect("group_page")
	else:
		# not a POST request
		return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def display_detailed_info(request):
	"""
	Renders detailed info regarding each mehfil statistic available to users for viewing
	"""
	if request.method == "POST":
		group_uuid = request.POST.get("guid",None)
		if group_uuid:
			group_id, own_id = retrieve_group_id(group_uuid), request.user.id
			if group_member_exists(group_id, own_id):
				which_info = request.POST.get("inf",None)
				is_public = False if retrieve_group_privacy(group_id) == '1' else True
				if is_public:
					if which_info in ('1','2','3','4','5','6','7','8','9','10','11'):
						if which_info in ('1','2'):
							# mehfil owner and creation time details
							creation_time = retrieve_group_creation_time(group_id)
							return render(request,"mehfil/group_info_detail.html",{'guid':group_uuid,'oun':retrieve_group_owner_uname(group_id),\
								'created_at':exact_date(creation_time),'info':which_info,'is_public':True})
						elif which_info == '3':
							# mehfil joining details
							user_join_time = retrieve_group_joining_time(group_id, own_id)
							return render(request,"mehfil/group_info_detail.html",{'guid':group_uuid, 'joined_at':exact_date(user_join_time),'info':\
								which_info,'is_public':True})
						elif which_info == '4':
							# total members
							return redirect("display_group_users_list",grp_priv='public', list_type='members')
						elif which_info == '5':
							# last 1-day visitors
							return redirect("display_group_users_list",grp_priv='public', list_type='visitors')
						elif which_info == '6':
							# net 7-day joiners
							net_joiners = request.POST.get("nj",0)
							try:
								net_joiners = int(net_joiners)
							except ValueError:
								net_joiners = 0
							return render(request,"mehfil/group_info_detail.html",{'guid':group_uuid,'info':which_info,'net_joiners':net_joiners,\
								'is_public':True})
						elif which_info == '7':
							# total officers
							aggregate_officers = request.POST.get("ao",0)
							try:
								aggregate_officers = int(aggregate_officers)
							except ValueError:
								aggregate_officers = 0
							return render(request,"mehfil/group_info_detail.html",{'guid':group_uuid,'info':which_info,'total_officers':aggregate_officers,\
								'is_public':True})
						elif which_info == '8':
							# average sign up age
							average_age = request.POST.get("aa",'')
							return render(request,"mehfil/group_info_detail.html",{'guid':group_uuid,'info':which_info,'average_age':average_age,\
								'is_public':True})
						elif which_info == '9':
							# mehfil size
							size = request.POST.get("sz",None)
							return render(request,"mehfil/group_info_detail.html",{'guid':group_uuid,'info':which_info,'mehfil_size':size,\
								'is_public':True})
						else:
							# mehfil bought date and price
							buying_time, price_paid = retrieve_group_buying_time_and_price(group_id)
							owner_uname = retrieve_group_owner_uname(group_id)
							return render(request,"mehfil/group_info_detail.html",{'guid':group_uuid,'info':which_info,'bought_at':exact_date(float(buying_time)),\
								'owner_uname':owner_uname,'price_paid':price_paid,'is_public':True})
					else:
						# back to info page
						data = get_group_info(group_id, is_public = True)
						data['uj'] = retrieve_group_joining_time(group_id, own_id)# this is different for each user, so retrieved separately
						data['7nm'] = int(data['7nm']) if '7nm' in data else 0
						return render(request,"mehfil/group_info.html",{'data':data,'guid':group_uuid,'is_public':True})
				else:
					# is a private group
					if which_info in ('1','2','3','4','5','6','7','8','9'):
						if which_info in ('1','2'):
							# mehfil owner and creation time details
							creation_time = retrieve_group_creation_time(group_id)
							return render(request,"mehfil/group_info_detail.html",{'guid':group_uuid,'oun':retrieve_group_owner_uname(group_id),\
								'created_at':exact_date(creation_time),'info':which_info})
						elif which_info == '3':
							# mehfil joining details
							user_join_time = retrieve_group_joining_time(group_id, own_id)
							return render(request,"mehfil/group_info_detail.html",{'guid':group_uuid, 'joined_at':exact_date(user_join_time),'info':\
								which_info})
						elif which_info == '4':
							# total members
							return redirect("display_group_users_list",grp_priv='private', list_type='members')
						elif which_info == '5':
							# last 1-day visitors
							return redirect("display_group_users_list",grp_priv='private', list_type='visitors')
						elif which_info == '6':
							# topic change history
							topic_data = retrieve_group_topic_log(group_id)
							return render(request,"mehfil/group_info_detail.html",{'guid':group_uuid, 'topic_data':topic_data,'info':which_info})
						elif which_info in ('7','8'):
							# most talkative/silent
							chatter_data = retrieve_group_chatter(group_id)
							return render(request,"mehfil/group_info_detail.html",{'guid':group_uuid, 'chatter_data':chatter_data,'info':which_info})
						else:
							# most pics shared
							pic_sharer_uname = retrieve_biggest_pic_sharer_in_group(group_id)
							return render(request,"mehfil/group_info_detail.html",{'guid':group_uuid, 'pic_sharer_uname':pic_sharer_uname,'info':which_info})
					else:
						# back to info page
						data = get_group_info(group_id, is_public = False)
						data['uj'] = retrieve_group_joining_time(group_id, own_id)# this is different for each user, so retrieved separately
						return render(request,"mehfil/group_info.html",{'data':data,'guid':group_uuid,'is_public':False})

			else:
				# not a member or group does not exist
				return redirect("group_page")
		else:
			# no group uuid available
			return redirect("group_page")
	else:
		# not a POST request
		return redirect("public_group")


############################## Mehfil ownership transfer #################################

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def processing_group_ownership_transfer(request, slug):
	"""
	Goes ahead and processes the transfer (public and private both)
	"""
	if slug not in ('public','private'):
		return redirect("missing_page")
	elif request.method == "POST":
		decision = request.POST.get("ratify",None)
		if decision == '1':
			group_uuid = request.POST.get("guid",None)
			group_owner_id, group_id, group_privacy = retrieve_group_owner_id(group_uuid=group_uuid,with_group_id=True,with_group_privacy=True)
			if group_owner_id:
				own_id = request.user.id
				if group_owner_id == str(own_id):
					# ensure target user is verified
					is_public = False if group_privacy == '1' else True
					if is_ownership_transfer_frozen(group_id):
						# unable to progress because public mehfil has been reported and thus any transfer operation is frozen for the time being
						return render(request,"mehfil/notify_and_redirect.html",{'action_frozen':True,'unique':group_uuid,'is_public':is_public})
					else:
						offerer_id = request.POST.get("oid",None)
						if is_ownership_request_legit(group_id, offerer_id):
							if is_mobile_verified(offerer_id):# offerer must be mobile verified
								offer_details = retrieve_offer_details(group_id, offerer_id)	
								if offer_details:
									# {'sid':submitter_id,'suname':submitter_uname,'savurl':submitter_avurl,'t':time_now,'pts':points_offered,'gid':group_id}
									points_offered = offer_details.get('pts',0)
									submitter_uname = retrieve_uname(offerer_id,decode=True)
									if submitter_uname:
										user_ttl, ttl_type = group_ownership_transfer_blocked_by_rate_limit(group_id, own_id, offerer_id)
										if user_ttl:
											# cannot proceed since owner or requestor are rate-limited
											return render(request,"mehfil/notify_and_redirect.html",{'owner_rl_due_to_prev_transaction':True,'unique':group_uuid,\
												'ttl_type':ttl_type,'ttl':user_ttl,'is_public':is_public})
										else:
											time_now, points_offered = time.time(), int(points_offered)
											if time_now - retrieve_group_creation_time(group_id) < GROUP_AGE_AFTER_WHICH_IT_CAN_BE_TRANSFERRED:
												# group too young to be transferred
												return render(request,"mehfil/notify_and_redirect.html",{'group_too_young_to_be_transferred':True,'unique':group_uuid,\
													'is_public':is_public})
											elif time_now - retrieve_group_joining_time(group_id, offerer_id) < MIN_MEMBERSHIP_AGE_FOR_REQUESTING_GRP_OWNERSHIP:
												# user only recently joined the group - cannot become owner
												return render(request,"mehfil/notify_and_redirect.html",{'member_too_young_to_become_owner':True,'unique':group_uuid,\
													'is_public':is_public})
											elif is_public and points_offered < PUBLIC_GROUP_MIN_SELLING_PRICE:
												# not enough points offered (i.e. less than 5000 points)
												rescind_offer(group_id=group_id, offerer_id=offerer_id)
												return render(request,"mehfil/notify_and_redirect.html",{'not_enough_price_offered':True,'unique':group_uuid,\
													'min_price':PUBLIC_GROUP_MIN_SELLING_PRICE})
											elif is_public and points_offered > PUBLIC_GROUP_MAX_SELLING_PRICE:
												# too much price offered
												rescind_offer(group_id=group_id, offerer_id=offerer_id)
												return render(request,"mehfil/notify_and_redirect.html",{'too_much_price_offered':True,'unique':group_uuid})
											elif not group_member_exists(group_id, offerer_id):
												# offerer_id is not currently a member
												rescind_offer(group_id=group_id, offerer_id=offerer_id)
												return render(request,"mehfil/notify_and_redirect.html",{'offerer_not_a_member':True,'unique':group_uuid,\
													'is_public':is_public})
											elif is_public and retrieve_group_category(group_id) == '2' and submitter_uname not in FEMALES:
												# only a pink star can become an owner of this kind of group
												rescind_offer(group_id=group_id, offerer_id=offerer_id)
												return render(request,"mehfil/notify_and_redirect.html",{'only_pinkstar_can_be_owner':True,'unique':group_uuid})
											else:
												try:
													target_user = User.objects.get(id=offerer_id)
												except User.DoesNotExist:
													# this user does not exist thus data incomplete
													return redirect("group_page")
												if (time_now - convert_to_epoch(target_user.date_joined) > USER_AGE_AFTER_WHICH_PUBLIC_MEHFIL_CAN_BE_CREATED) \
												or not is_public:
													# the user is the appropriate age, proceed
													topic_ttl, rules_ttl = retrieve_topic_and_rules_ttl(own_id, group_uuid, is_public)
													if topic_ttl or rules_ttl:
														# do not allow accepting ownership - the owner recently changed the topic (which might have been abusive!)
														topic_ttl = topic_ttl if topic_ttl else 0
														rules_ttl = rules_ttl if rules_ttl else 0
														if topic_ttl > rules_ttl:
															ttl_type = 'topic'
															ttl = topic_ttl
														else:
															ttl_type = 'rules'
															ttl = rules_ttl
														return render(request,"mehfil/notify_and_redirect.html",{'topic_or_rules_rl_cannot_transfer':True,\
															'unique':group_uuid,'ttl':ttl,'ttl_type':ttl_type,'is_public':is_public})
													elif is_public and UserProfile.objects.only('score').get(user_id=offerer_id).score < points_offered:
														# the offerer can't keep their end of the bargain any more - i.e. they dont have enough score :(
														rescind_offer(group_id=group_id, offerer_id=offerer_id)
														return render(request,"mehfil/notify_and_redirect.html",{'cannot_afford':True,'unique':group_uuid})
													elif HellBanList.objects.filter(condemned_id=offerer_id).exists():
														# the offerer is hell banned
														rescind_offer(group_id=group_id, offerer_id=offerer_id)
														return render(request,"mehfil/notify_and_redirect.html",{'offerer_is_hellbanned':True,'unique':group_uuid,\
															'is_public':is_public})
													else:
														# change owner object in Group model and create a reply
														Group.objects.filter(unique=group_uuid).update(owner=target_user)
														# charge the offerer the score they offered
														if is_public:
															UserProfile.objects.filter(user_id=offerer_id).update(score=F('score')-points_offered)
														### process redis6 related stuff ### 
														# change owner object in redis6 data
														# ensure ownership change is seen in administrative activity
														# ensure ownership change is reflected in information page
														# ensure price paid by new owner is reflected in information page if it's a public mehfil
														own_uname, own_avurl = retrieve_credentials(own_id,decode_uname=True)
														accept_group_ownership_transfer_request(group_id=group_id, group_uuid=group_uuid, owner_id=own_id, \
															own_uname=own_uname, requestor_id=offerer_id, requestor_uname=submitter_uname, time_now=time_now, \
															points_offered=points_offered, is_public=is_public)
														###################################
														save_group_submission(writer_id=own_id, group_id=group_id, text=submitter_uname,posting_time=time_now,\
															category='8', writer_uname=own_uname, writer_avurl=get_s3_object(own_avurl,category='thumb'))
														invalidate_cached_mehfil_replies(group_id)
														invalidate_presence(group_id)
														return render(request,"mehfil/transfer_final_status.html",{'guid':group_uuid,'ouname':submitter_uname,\
															'is_public':is_public})
												else:
													# user not old enough to own a public mehfil
													return render(request,"mehfil/notify_and_redirect.html",{'too_young_to_become_owner':True,'unique':group_uuid})
									else:
										# data incomplete
										return redirect("public_group")
								else:
									# such an offer does not exist - maybe it expired?
									mehfil_type = 'public' if is_public else 'private'
									ownership_requests = retrieve_outstanding_requests(group_id)
									num_requests = len(ownership_requests) if ownership_requests else 0
									return render(request,"mehfil/ownership_transfer_tac.html",{'unique':group_uuid,'ownership_requests':ownership_requests,\
										'max_price':int(PUBLIC_GROUP_MAX_SELLING_PRICE) if is_public else None,'review_ownership_transfer_requests':True,\
										'min_price':int(PUBLIC_GROUP_MIN_SELLING_PRICE) if is_public else None,'num_requests':num_requests,mehfil_type:True})
							else:
								return render(request,"mehfil/notify_and_redirect.html",{'only_verified_can_be_owner':True,'unique':group_uuid,'is_public':is_public})
						else:
							# maybe offer expired - or was bogus, user-tempered data to begin with
							return render(request,"mehfil/notify_and_redirect.html",{'offer_does_not_exist':True,'unique':group_uuid,'is_public':is_public})
				else:
					# not authorized to do this
					return redirect("group_page")
			else:
				# group does not exist
				return redirect("group_page")
		else:
			# return to main group - the decision was 'No'
			if slug == 'public':
				return redirect("public_group")
			else:
				return redirect("private_group_reply")
	else:
		# not a POST request
		if slug == 'public':
			return redirect("public_group")
		else:
			return redirect("private_group_reply")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def send_request_to_owner(request, slug):
	"""
	Requests owner to transfer the mehfil ownership to user
	
	Works for public and private both
	If public owner, must include a non-zero price in points the user is willing to pay
	If private owner, just send a plain request
	"""
	if request.user_banned:
		return redirect("error")
	elif slug not in ('public','private'):
		return redirect("missing_page")
	elif request.method == "POST":
		group_uuid = request.POST.get("guid",None)
		group_owner_id, group_id, group_privacy = retrieve_group_owner_id(group_uuid=group_uuid,with_group_id=True,with_group_privacy=True)
		if group_owner_id:
			is_public = False if group_privacy == '1' else True
			if is_ownership_transfer_frozen(group_id):
				# unable to progress because public mehfil has been reported and thus any transfer operation is frozen for the time being
				return render(request,"mehfil/notify_and_redirect.html",{'action_frozen':True,'unique':group_uuid,'is_public':is_public})
			else:
				own_id, time_now = request.user.id, time.time()
				own_uname, own_avurl = retrieve_credentials(own_id,decode_uname=True)
				if is_public:
					form = GroupPriceOfferForm(data=request.POST,user_id=own_id, user_uname=own_uname,time_now=time_now, score=request.user.userprofile.score, \
						group_id=group_id, group_owner_id=group_owner_id, is_mob_verified=request.mobile_verified)
					if form.is_valid():
						# can send quote to mehfil owner
						points_offered = form.cleaned_data.get('price',1)
						requestor_ttl, ttl_type = submit_group_ownership_request(group_id, own_id, own_uname, own_avurl, time_now, \
							points_offered=points_offered)
						if requestor_ttl:
							return render(request,"mehfil/notify_and_redirect.html",{'sent_ownership_request_recently':True,'unique':group_uuid,'ttl':requestor_ttl,\
								'ttl_type':ttl_type,'is_public':is_public})
						else:
							main_sentence = own_uname+" ne mehfil owner banney ke liye {0} points offer kiye at {1}".format(points_offered, exact_date(time_now))
							document_administrative_activity.delay(group_id, main_sentence, 'public_ownership_request')
							return render(request,"mehfil/notify_and_redirect.html",{'ownership_request_successful':True,'unique':group_uuid,'is_public':is_public})
					else:
						# form is invalid
						time_elapsed = time_now - retrieve_group_joining_time(group_id, own_id)
						if time_elapsed > MIN_MEMBERSHIP_AGE_FOR_REQUESTING_GRP_OWNERSHIP:
							# enough time has elapsed
							allowed_to_request = True
							wait_time = None
						else:
							allowed_to_request = False
							wait_time = MIN_MEMBERSHIP_AGE_FOR_REQUESTING_GRP_OWNERSHIP - time_elapsed
						return render(request,"mehfil/ownership_transfer_tac.html",{'group_price':int(PUBLIC_GROUP_MAX_SELLING_PRICE),'public':True,\
							'unique':group_uuid,'send_ownership_request':True,'least_price':int(PUBLIC_GROUP_MIN_SELLING_PRICE),'form':form,'wait_time':wait_time,\
							'prev_request':get_prev_request(group_id,own_id),'allowed_to_request':allowed_to_request})
				else:
					# is a private group
					requestor_ttl, ttl_type = submit_group_ownership_request(group_id, own_id, own_uname, own_avurl, time_now)
					if requestor_ttl:
						return render(request,"mehfil/notify_and_redirect.html",{'sent_ownership_request_recently':True,'unique':group_uuid,'ttl':requestor_ttl,\
							'ttl_type':ttl_type,'is_public':is_public})
					else:
						main_sentence = own_uname+" ne mehfil owner banney ki request ki at {0}".format(exact_date(time_now))
						document_administrative_activity.delay(group_id, main_sentence, 'private_ownership_request')
						return render(request,"mehfil/notify_and_redirect.html",{'ownership_request_successful':True,'unique':group_uuid,'is_public':is_public})
		else:
			# group does not exist
			return redirect("group_page")
	else:
		# not a POST request
		if slug == 'public':
			return redirect("public_group")
		else:
			return redirect("private_group_reply")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def cancel_ownership_request(request, slug):
	"""
	Cancels an outstanding request sent by a user to become a mefil owner
	"""
	if slug not in ('public','private'):
		return redirect("missing_page")
	elif request.method == "POST":
		group_uuid = request.POST.get("guid",None)
		group_owner_id, group_id, group_privacy = retrieve_group_owner_id(group_uuid=group_uuid,with_group_id=True,with_group_privacy=True)
		if group_owner_id:
			own_id = request.user.id
			rescind_offer(group_id=group_id, offerer_id=own_id)
			is_public = False if group_privacy == '1' else True
			own_uname = retrieve_uname(own_id,decode=True)
			if is_public:
				main_sentence = own_uname+" ne mehfil owner banney ki offer wapis le li at {}".format(exact_date(time.time()))
				document_administrative_activity.delay(group_id, main_sentence, 'cancel_public_ownership_request')
				mehfil_type = 'public'
			else:
				# is a private mehfil
				main_sentence = own_uname+" ne mehfil owner banney ki request wapis le li at {}".format(exact_date(time.time()))
				document_administrative_activity.delay(group_id, main_sentence, 'cancel_private_ownership_request')
				mehfil_type = 'private'
			return render(request,"mehfil/ownership_transfer_tac.html",{'group_price':int(PUBLIC_GROUP_MAX_SELLING_PRICE) if is_public else None,\
				mehfil_type:True,'form':GroupPriceOfferForm() if is_public else None,'unique':group_uuid,'send_ownership_request':True,\
				'least_price':int(PUBLIC_GROUP_MIN_SELLING_PRICE) if is_public else None,'allowed_to_request':True})
		else:
			# group does not exist
			return redirect("group_page")
	else:
		# not a POST request
		if slug == 'public':
			return redirect("public_group")
		else:
			return redirect("private_group_reply")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def group_ownership_transfer_tac(request, slug):
	"""
	Renders owner transfership terms and conditions (tac)
	Renders any outstanding owner transfer requests (by officers or group members)

	PUBLIC:
	i) Allows user to ask an 'officer' for an offer (in terms of points)
	ii) If offer is agreeable, the ower can finalize transaction and change the ownership

	PRIVATE:
	i) Allows user to transfer ownership to any other member (including owner rights and invite limits)
	"""
	if slug not in ('public','private'):
		return redirect("missing_page")
	elif request.method == "POST":
		group_uuid = request.POST.get("guid",None)
		if group_uuid:
			group_owner_id, group_id, group_privacy = retrieve_group_owner_id(group_uuid=group_uuid,with_group_id=True,with_group_privacy=True)
			own_id = request.user.id
			if group_owner_id == str(own_id):
				# authorized to take action
				is_public = False if group_privacy == '1' else True
				offerer_id = request.POST.get("sid",None)
				decision = request.POST.get("dec",None)
				if decision == '1':
					# is it a legit offer?
					offer_exists = is_ownership_request_legit(group_id, offerer_id)
					if offer_exists:
						# throw an 'ARE YOU SURE' prompt since it's a big decision
						return render(request,"mehfil/notify_and_redirect.html",{'ratify_ownership_transfer':True,'unique':group_uuid,'offerer_id':offerer_id,\
							'ouname':retrieve_uname(offerer_id,decode=True),'is_public':is_public, 'slug':'public' if is_public else 'private'})
					else:
						# maybe offer expired, was canceled - or was bogus, user-tempered data to begin with
						return render(request,"mehfil/notify_and_redirect.html",{'offer_does_not_exist':True,'unique':group_uuid,'is_public':is_public})
				else:
					# delete the offer, owner no likie!
					rescind_offer(group_id=group_id, offerer_id=offerer_id)
					ownership_requests = retrieve_outstanding_requests(group_id)
					num_requests = len(ownership_requests) if ownership_requests else 0
					if is_public:
						return render(request,"mehfil/ownership_transfer_tac.html",{'max_price':int(PUBLIC_GROUP_MAX_SELLING_PRICE),'public':True,\
							'unique':group_uuid,'ownership_requests':ownership_requests,'min_price':int(PUBLIC_GROUP_MIN_SELLING_PRICE),\
							'review_ownership_transfer_requests':True,'num_requests':num_requests})
					else:
						# is a private mehfil
						return render(request,"mehfil/ownership_transfer_tac.html",{'private':True,'unique':group_uuid,'ownership_requests':ownership_requests,\
							'review_ownership_transfer_requests':True,'num_requests':num_requests})
			else:
				# not an owner of this mehfil - abort
				return redirect("group_page")
		else:
			# group uuid didn't exist
			return redirect("group_page")
	else:
		# not a POST request
		if slug == 'public':
			return redirect("public_group")
		else:
			return redirect("private_group_reply")


############################## Private mehfil administration ##############################


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def private_mehfil_oversight_dashboard(request):
	"""
	Renders admin and regular member options for private mehfils

	Admin can i) ban/unban ii) invite upto 3 users, iii) transfer ownership ,iv) delete mehfil
	Normal can i) invite upto 1 other user, ii) request ownership, iii) exit mehfil
	"""
	if request.method == "POST":
		group_uuid = request.POST.get("guid",None)
		data = retrieve_group_reqd_data(group_uuid=group_uuid, with_group_owner_id=True)
		if data:
			owner_id = data['oi']
			group_id = data['gi']
			own_id = str(request.user.id)
		else:
			# no group found
			return redirect("group_page")
		if owner_id == own_id:
			# group admin
			decision = request.POST.get("dec",None)
			if decision in ('1','2','3','4','5','8'):
				if decision == '1':
					# owner wants to change topic
					request.session["unique_id"] = group_uuid
					request.session.modified = True
					return redirect("change_private_topic")
				elif decision == '2':
					# owner wants to invite new members
					request.session["unique_id"] = group_uuid
					request.session.modified = True
					return redirect("invite_private_group")
				elif decision == '3':
					# owner wants to kick out
					membership_data = retrieve_cached_membership_data(group_id)
					if membership_data:
						final_member_data = json.loads(membership_data)
					else:
						all_member_ids_and_joining_times = retrieve_all_member_ids(group_id,with_num_members = False, with_times=True)
						only_member_ids = [member_id for (member_id,joining_time) in all_member_ids_and_joining_times]
						credentials, final_member_data = retrieve_bulk_credentials(only_member_ids, decode_unames=True), []#returned data {int(user_id):{'uname':uname,'avurl':avurl}}
						for member_id, joining_time in all_member_ids_and_joining_times:
							final_member_data.append((member_id, credentials[int(member_id)],joining_time))
						cache_group_membership_data(json.dumps(final_member_data),group_id)
					return render(request,'mehfil/kick_out_group_members.html',{'topic':data['tp'],'members':final_member_data,'legit':FEMALES,\
						'guid':group_uuid,'immune_ids':[own_id],'own_id':own_id})
				elif decision == '4':
					# owner wants to transfer ownership
					ownership_requests = retrieve_outstanding_requests(group_id)
					num_requests = len(ownership_requests) if ownership_requests else 0
					return render(request,"mehfil/ownership_transfer_tac.html",{'private':True,'unique':group_uuid,'ownership_requests':ownership_requests,\
						'review_ownership_transfer_requests':True,'num_requests':num_requests})
				elif decision == '5':
					# delete mehfil
					return render(request,'mehfil/delete_private_group.html',{'unique':group_uuid, 'pk':group_id, 'topic':data['tp'], 'inside_grp':'1'})
				else:
					# user wants to view history
					request.session["administrative_activity_uuid"] = group_uuid
					request.session.modified = True
					return redirect("display_administrative_activity",'private')
			else:
				# owner has not made a decision - show default 'owner' screen
				return render(request,"mehfil/private_group_administration.html",{'topic':data['tp'],'owner':True,'unique':group_uuid,'group_id':group_id})
		elif group_member_exists(group_id, own_id):
			# a regular member
			decision = request.POST.get("dec",None)
			if decision in ('1','2','6','7','8'):
				if decision == '1':
					# member wants to change topic
					request.session["unique_id"] = group_uuid
					request.session.modified = True
					return redirect("change_private_topic")
				elif decision == '2':
					# member wants to invite new members
					request.session["unique_id"] = group_uuid
					request.session.modified = True
					return redirect("invite_private_group")
				elif decision == '6':
					# member wants to request ownership transfer
					time_elapsed = time.time() - retrieve_group_joining_time(group_id, own_id)
					if time_elapsed > MIN_MEMBERSHIP_AGE_FOR_REQUESTING_GRP_OWNERSHIP:
						# enough time has elapsed
						allowed_to_request = True
						wait_time = None
					else:
						allowed_to_request = False
						wait_time = MIN_MEMBERSHIP_AGE_FOR_REQUESTING_GRP_OWNERSHIP - time_elapsed
					previous_request = get_prev_request(group_id,own_id)
					prev_request_exists = True if previous_request else False
					return render(request,"mehfil/ownership_transfer_tac.html",{'private':True,'unique':group_uuid,'send_ownership_request':True,\
						'prev_request':previous_request, 'allowed_to_request':allowed_to_request,'wait_time':wait_time,'prev_req_exists':prev_request_exists})
				elif decision == '7':
					# exit mehfil
					return render(request, 'mehfil/leave_private_group.html', {'unique':group_uuid, 'pk':group_id, 'topic':data['tp'], 'inside_grp':'1'})
				else:
					# user wants to view history
					request.session["administrative_activity_uuid"] = group_uuid
					request.session.modified = True
					return redirect("display_administrative_activity",'private')
			else:
				# member has not made a decision - show default 'member' screen
				return render(request,"mehfil/private_group_administration.html",{'topic':data['tp'],'owner':False,'unique':group_uuid,'group_id':group_id})
		else:
			# not authorized to be here
			return redirect("group_page")
	else:
		group_uuid = request.session.get('unique_id',None)
		request.session["unique_id"] = group_uuid
		return redirect("private_group_reply")


############################## Public mehfil administration ##############################

def can_make_officer(user_id, group_id, group_owner_id):
	"""
	Checks whether a given user_id can become an officer in a public group

	Ensure user is a member, not the group's owner, and not already a member
	"""
	if group_member_exists(group_id, user_id) and not is_group_officer(group_id,user_id) and group_owner_id != str(user_id):
		return True
	else:
		return False


def user_too_young_to_become_officer(user_id, time_now, app_joining_time_in_epoch, group_joining_time_in_epoch):
	"""
	Decides whether the user_id has aged enough to merit submitting an officer application to a public group
	"""
	if (time_now-app_joining_time_in_epoch) < MIN_APP_MEMBERSHIP_AGE_FOR_REQUESTING_GRP_OFFICERSHIP:
		# user joined our app way too recently
		return True, None
	elif (time_now-group_joining_time_in_epoch) < MIN_GRP_MEMBERSHIP_AGE_FOR_REQUESTING_GRP_OFFICERSHIP:
		# user joined the group way too recently
		return False, True
	else:
		return False, False
	

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def public_group_officer_management(request):
	"""
	Manage officers of public mehfil
	"""
	if request.method == "POST":
		group_uuid = request.POST.get("guid",None)
		decision = request.POST.get("dec",None)
		if decision == '4':
			return redirect("public_group", slug=group_uuid)
		elif decision in ('1','2','3'):
			data = retrieve_group_reqd_data(group_uuid=group_uuid, with_group_owner_id=True)
			if data:
				owner_id = data['oi']
				group_id = data['gi']
			else:
				# no group found
				return redirect("group_page")
			own_id = str(request.user.id)
			if owner_id == own_id:
				if decision == '1':
					# add more officers
					return render(request,"mehfil/manage_public_group_officers.html",{'topic':data['tp'],'add_officers':True,\
						'females':FEMALES,'guid':group_uuid,'applications':retrieve_all_current_applications(group_id=group_id)})
				elif decision == '2':
					# remove officers
					officer_ids_times_and_powers = retrieve_all_officers(group_id, with_power_levels=True)# tup of the sort (officer_id, time, can_hide, can_kick)
					officer_ids, interim_data = [], {}
					for officer_id, appointment_time, can_hide, can_kick, can_topic in officer_ids_times_and_powers:
						officer_ids.append(officer_id)
						interim_data[officer_id] = (officer_id, appointment_time, can_hide, can_kick, can_topic)#tuple
					officers = User.objects.select_related('userprofile').filter(id__in=officer_ids)
					officer_data = []
					for officer in officers:
						tup = interim_data[str(officer.id)]
						officer_data.append((tup[0],officer,tup[1],tup[2],tup[3],tup[4]))#(officer_id, officer_obj, appointment_time, can_hide, can_kick, can_topic)
					return render(request,"mehfil/manage_public_group_officers.html",{'females':FEMALES,'topic':data['tp'],\
						'rem_officers':True,'officer_data':officer_data,'guid':group_uuid})
				else:
					# view officer history
					request.session["administrative_activity_uuid"] = group_uuid
					request.session.modified = True
					return redirect("display_administrative_activity",'public')
			else:
				return redirect("group_page")
		else:
			raise Http404("This option is invalid")
	else:
		# not a POST request
		return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def public_mehfil_oversight_dashboard(request):
	"""
	Renders admin, officer and regular user options

	Admin can i) create/remove officers, ii) ban/unban iii) view history iv) check user complaints/feedback v) invite
	Officers can i) ban/unban, ii) view history, iii) invite
	Normal users can i) complain/praise/provide feedback, ii) report mehfil's topic and rules
	"""
	if request.method == "POST":
		group_uuid = request.POST.get("guid",None)
		data = retrieve_group_reqd_data(group_uuid=group_uuid, with_group_owner_id=True)
		if data:
			owner_id = data['oi']
			group_id = data['gi']
			own_id = str(request.user.id)
		else:
			# no group found
			return redirect("group_page")
		if owner_id == own_id:
			# group admin
			decision = request.POST.get("dec",None)
			if decision in ('1','2','3','4','5','6','11','13','17'):
				# make a decision
				if decision == '1':
					# manage officers (i.e. default to 'add officers'. From there, user can go to remove officers or view history)
					return render(request,"mehfil/manage_public_group_officers.html",{'topic':data['tp'],'guid':group_uuid,\
						'applications':retrieve_all_current_applications(group_id=group_id),'add_officers':True,\
						'show_tut':tutorial_unseen(user_id=own_id, which_tut='29', renew_lease=True),'females':FEMALES})
				elif decision == '2':
					# kick out users
					attendance_data = retrieve_cached_attendance_data(group_id,term='short')
					if attendance_data:
						final_visitor_data = json.loads(attendance_data)
					else:
						attendance_data = get_attendance(group_id,withscores=True)
						#removing banned IDs (in case they are still showing up online)
						filtered_attendance_data = [(visitor_id,visit_time) for (visitor_id,visit_time) in attendance_data if visitor_id not in \
						retrieve_kicked_user_ids(group_id)]
						final_visitor_data = []
						if filtered_attendance_data:
							all_online_ids = [visitor_id for (visitor_id,visit_time) in filtered_attendance_data]
							credentials = retrieve_bulk_credentials(all_online_ids, decode_unames=True)#dictionary of dictionaries is returned
							for visitor_id,visit_time in filtered_attendance_data:
								final_visitor_data.append((str(visitor_id),credentials[int(visitor_id)],visit_time))
							cache_group_attendance_data(json.dumps(final_visitor_data),group_id,term='short')#micro-cached for 11 seconds
					return render(request,'mehfil/take_action_against_group_visitors.html',{'topic':data['tp'],'visitors':final_visitor_data,\
						'legit':FEMALES,'guid':group_uuid,'kick':True,'owner':True,'immune_ids':retrieve_immune_ids(group_id,own_id,is_officer=False),\
						'own_id':own_id})
				elif decision == '3':
					# invite
					return redirect("invite")
				elif decision == '4':
					# see feedback
					return redirect("show_open_group_feedback",'2')
				elif decision == '5':
					# change topic
					return redirect("change_topic")
				elif decision == '6':
					# decision == '6', i.e. change rules
					return redirect("change_rules")
				elif decision == '11':
					# decision == '11', change ownership
					ownership_requests = retrieve_outstanding_requests(group_id)
					num_requests = len(ownership_requests) if ownership_requests else 0
					return render(request,"mehfil/ownership_transfer_tac.html",{'max_price':int(PUBLIC_GROUP_MAX_SELLING_PRICE),'public':True,\
						'unique':group_uuid,'ownership_requests':ownership_requests,'min_price':int(PUBLIC_GROUP_MIN_SELLING_PRICE),\
						'review_ownership_transfer_requests':True,'num_requests':num_requests})
				elif decision == '13':
					# delete mehfil
					return render(request, 'mehfil/delete_public_group.html', {'pk':group_id,'inside_grp':'1','unique':group_uuid,\
						'topic':data['tp']})
				else:
					# view officer history
					request.session["administrative_activity_uuid"] = group_uuid
					request.session.modified = True
					return redirect("display_administrative_activity",'public')
			else:
				# owner has not made a decision - show default 'owner' screen
				return render(request,"mehfil/public_group_administration.html",{'topic':data['tp'],'owner':True,'unique':group_uuid})
		elif is_group_officer(group_id,own_id):
			# group officer, can use their powers here
			decision = request.POST.get("dec",None)
			if decision in ('2','3','5','7','8','9','10','12','13','14'):
				if decision == '2':
					# kick out
					can_kick = can_officer_kick_out(group_id, own_id)
					if can_kick:
						attendance_data = retrieve_cached_attendance_data(group_id,term='short')
						if attendance_data:
							final_visitor_data = json.loads(attendance_data)
						else:
							attendance_data = get_attendance(group_id,withscores=True)
							#removing banned IDs (in case they are still showing up online)
							filtered_attendance_data = [(visitor_id,visit_time) for (visitor_id,visit_time) in attendance_data if visitor_id not in \
							retrieve_kicked_user_ids(group_id)]
							final_visitor_data = []
							if filtered_attendance_data:
								all_online_ids = [visitor_id for (visitor_id,visit_time) in filtered_attendance_data]
								credentials = retrieve_bulk_credentials(all_online_ids, decode_unames=True)#dictionary of dictionaries is returned
								for visitor_id,visit_time in filtered_attendance_data:
									final_visitor_data.append((str(visitor_id),credentials[int(visitor_id)],visit_time))
								cache_group_attendance_data(json.dumps(final_visitor_data),group_id,term='short')#micro-cached for 11 seconds
						return render(request,'mehfil/take_action_against_group_visitors.html',{'topic':data['tp'],'visitors':final_visitor_data,\
							'legit':FEMALES,'guid':group_uuid,'kick':True,'officer':True,'immune_ids':retrieve_immune_ids(group_id,own_id,is_officer=True),\
							'own_id':own_id})
					else:
						return redirect("public_group",slug=group_uuid)
				elif decision == '3':
					# invite
					return redirect("invite")
				elif decision == '5':
					# change topic
					can_topic = can_officer_change_topic(group_id, own_id)
					if can_topic:
						return redirect("change_topic")
					else:
						return redirect("public_group",slug=group_uuid)
				elif decision == '7':
					# officer history
					request.session["administrative_activity_uuid"] = group_uuid
					request.session.modified = True
					return redirect("display_administrative_activity",'public')
				elif decision == '8':
					# provide praise
					return render(request,"mehfil/open_group_feedback_submission.html",{'form':GroupFeedbackForm(),'praise':True,'guid':group_uuid,\
						'title':'Submit praise','feedback_type':'1','show_instr':tutorial_unseen(user_id=own_id, which_tut='22', renew_lease=True),\
						'length_limit':GROUP_FEEDBACK_SIZE})
				elif decision == '9':
					# lodge complaint
					return render(request,"mehfil/open_group_feedback_submission.html",{'form':GroupFeedbackForm(),'complaint':True,'guid':group_uuid,\
						'title':'Submit complaint','feedback_type':'2','show_instr':tutorial_unseen(user_id=own_id, which_tut='22', renew_lease=True),\
						'length_limit':GROUP_FEEDBACK_SIZE})
				elif decision == '10':
					# provide feedback
					return render(request,"mehfil/open_group_feedback_submission.html",{'form':GroupFeedbackForm(),'feedback':True,'guid':group_uuid,\
						'title':'Submit idea','feedback_type':'3','show_instr':tutorial_unseen(user_id=own_id, which_tut='22', renew_lease=True),\
						'length_limit':GROUP_FEEDBACK_SIZE})
				elif decision == '12':
					# request ownership
					time_elapsed = time.time() - retrieve_group_joining_time(group_id, own_id)
					if time_elapsed > MIN_MEMBERSHIP_AGE_FOR_REQUESTING_GRP_OWNERSHIP:
						# enough time has elapsed
						allowed_to_request = True
						wait_time = None
					else:
						allowed_to_request = False
						wait_time = MIN_MEMBERSHIP_AGE_FOR_REQUESTING_GRP_OWNERSHIP - time_elapsed
					return render(request,"mehfil/ownership_transfer_tac.html",{'group_price':int(PUBLIC_GROUP_MAX_SELLING_PRICE),'public':True,\
						'unique':group_uuid,'send_ownership_request':True,'least_price':PUBLIC_GROUP_MIN_SELLING_PRICE,'wait_time':wait_time,\
						'form':GroupPriceOfferForm(),'prev_request':get_prev_request(group_id,own_id),'allowed_to_request':allowed_to_request})
				elif decision == '13':
					# exit mehfil
					return render(request, 'mehfil/leave_public_group.html', {'unique':group_uuid,'pk':group_id,'topic':data['tp'],'inside_grp':'1'})
				else:
					# read rules
					return render(request,"mehfil/notify_and_redirect.html",{'read_rules':True,'rules':retrieve_group_rules(group_id),'unique':group_uuid,\
						'topic':data['tp']})
			else:
				# officer has not made a decision - show default 'officer' screen
				can_hide, can_kick, can_topic = retrieve_group_officer_perms(group_id, own_id)
				return render(request,"mehfil/public_group_administration.html",{'topic':data['tp'],'officer':True,'unique':group_uuid,\
					'can_hide':can_hide,'can_kick':False if can_kick == '0' else True,'can_topic':False if can_topic == '0' else True,\
					'show_tut':tutorial_unseen(user_id=own_id, which_tut='30', renew_lease=True)})
		elif group_member_exists(group_id, own_id):
			# just an onlooker
			decision = request.POST.get("dec",None)
			if decision in ('8','9','10','12','13','14','15','16'):
				if decision == '8':
					# provide praise
					return render(request,"mehfil/open_group_feedback_submission.html",{'form':GroupFeedbackForm(),'praise':True,'guid':group_uuid,\
						'title':'Submit praise','feedback_type':'1','show_instr':tutorial_unseen(user_id=own_id, which_tut='22', renew_lease=True),\
						'length_limit':GROUP_FEEDBACK_SIZE})
				elif decision == '9':
					# lodge complaint
					return render(request,"mehfil/open_group_feedback_submission.html",{'form':GroupFeedbackForm(),'complaint':True,'guid':group_uuid,\
						'title':'Submit complaint','feedback_type':'2','show_instr':tutorial_unseen(user_id=own_id, which_tut='22', renew_lease=True),\
						'length_limit':GROUP_FEEDBACK_SIZE})
				elif decision == '10':
					# provide feedback
					return render(request,"mehfil/open_group_feedback_submission.html",{'form':GroupFeedbackForm(),'feedback':True,'guid':group_uuid,\
						'title':'Submit idea','feedback_type':'3','show_instr':tutorial_unseen(user_id=own_id, which_tut='22', renew_lease=True),\
						'length_limit':GROUP_FEEDBACK_SIZE})
				elif decision == '12':
					# request ownership
					time_elapsed = time.time() - retrieve_group_joining_time(group_id, own_id)
					if time_elapsed > MIN_MEMBERSHIP_AGE_FOR_REQUESTING_GRP_OWNERSHIP:
						# enough time has elapsed
						allowed_to_request = True
						wait_time = None
					else:
						allowed_to_request = False
						wait_time = MIN_MEMBERSHIP_AGE_FOR_REQUESTING_GRP_OWNERSHIP - time_elapsed
					return render(request,"mehfil/ownership_transfer_tac.html",{'group_price':int(PUBLIC_GROUP_MAX_SELLING_PRICE),'public':True,\
						'unique':group_uuid,'send_ownership_request':True,'least_price':int(PUBLIC_GROUP_MIN_SELLING_PRICE),'form':GroupPriceOfferForm(),\
						'prev_request':get_prev_request(group_id,own_id),'wait_time':wait_time,'allowed_to_request':allowed_to_request})
				elif decision == '13':
					# exit mehfil
					return render(request, 'mehfil/leave_public_group.html', {'unique':group_uuid,'pk':group_id,'topic':data['tp'],'inside_grp':'1'})
				elif decision == '14':
					# read rules
					return render(request,"mehfil/notify_and_redirect.html",{'read_rules':True,'rules':retrieve_group_rules(group_id),'unique':group_uuid,\
						'topic':data['tp']})
				elif decision == '15':
					# report mehfil
					pass
					# user_score = request.user.userprofile.score
					# price_of_report = get_price(user_score)
					# if price_of_report > user_score:
					# 	#disallow reporting (user doesn't have requisite score)
					# 	request.session["redirect_reason"+own_id] = 'not_enough_score_to_report_mehfil'
					# 	request.session["redirect_guid"+own_id] = group_uuid
					# 	return redirect("judge_not_and_red")#judgement module's notify_and_redirect function
					# else:
					# 	context = {'price':price_of_report, 'group_uuid':group_uuid,'rep_opt':ordered_list_of_tup(MEHFIL_REPORT_PROMPT), 'gid':group_id, \
					# 	'topic':data['tp'],'rules':retrieve_group_rules(group_id)}
					# 	return render(request,"judgement/mehfil_report.html",context)
				else:
					# drop an application to become an officer
					return render(request,"mehfil/officership_application.html",{'unique':group_uuid,'form':OfficerApplicationForm(),\
						'show_tut':tutorial_unseen(user_id=own_id, which_tut='28', renew_lease=True),'q1':GROUP_OFFICER_QUESTIONS['1'],\
						'q2':GROUP_OFFICER_QUESTIONS['2']})
			else:
				# user has not made a decision - show default 'user' screen
				return render(request,"mehfil/public_group_administration.html",{'topic':data['tp'],'regular_user':True,'unique':group_uuid})
		else:
			# not authorized to be here
			return redirect("group_page")
	else:
		return redirect("public_group")
		

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def process_open_group_feedback(request):
	"""
	Validates and saves praise, complaint or feedback type content in open groups
	"""
	if request.method == "POST":
		send_feedback = request.POST.get("sf",None)
		if send_feedback == '1':
			group_uuid = request.POST.get("guid",None)
			group_owner_id, group_id = retrieve_group_owner_id(group_uuid=group_uuid,with_group_id=True)
			own_id = str(request.user.id)
			if group_owner_id == own_id:
				# owner cant give feedback to self
				return redirect("public_group")
			elif group_member_exists(group_id, own_id):
				# can give feedback
				time_now = time.time()
				time_elapsed = time_now - retrieve_group_joining_time(group_id, own_id)
				feedback_type = request.POST.get("ftp",None)
				if time_elapsed < MIN_MEMBERSHIP_AGE_FOR_GIVING_PUBLIC_GRP_FEEDBACK:
					# user too young a member to give feedback - we don't want users to become members and immediately fire off feedback do we
					return render(request,"mehfil/notify_and_redirect.html",{'too_young_to_give_feedback':True,'unique':group_uuid,\
						'time_remaining':MIN_MEMBERSHIP_AGE_FOR_GIVING_PUBLIC_GRP_FEEDBACK-time_elapsed})
				elif feedback_type in ('1','2','3'):
					form = GroupFeedbackForm(data=request.POST)
					if form.is_valid():
						feedback = form.cleaned_data.get("feedback")
						# save in redis 6
						own_uname, own_avurl = retrieve_credentials(own_id,decode_uname=True)
						ttl = log_open_group_feedback(feedback, feedback_type, group_id, own_id, own_uname, own_avurl, time_now)
						if ttl:
							return render(request,"mehfil/notify_and_redirect.html",{'feedback_rate_limited':True,'ttl':ttl,'unique':group_uuid})
						else:
							return render(request,"mehfil/notify_and_redirect.html",{'feedback_thanks':True,'unique':group_uuid})
					else:
						# provide feedback
						if feedback_type == '1':
							feedback = 'feedback'
						elif feedback_type == '2':
							feedback = 'complaint'
						elif feedback_type == '3':
							feedback = 'feedback'
						return render(request,"mehfil/open_group_feedback_submission.html",{'form':form, feedback:True ,'guid':group_uuid,\
							'title':request.POST.get("title",None),'feedback_type':feedback_type,'length_limit':GROUP_FEEDBACK_SIZE})
				else:
					# tinkered
					return redirect("group_page")
			else:
				# not authorized to give feedback
				return redirect("public_group")
		else:
			# decided against submitting feedback
			return redirect("public_group")	
	else:
		# not a POST request
		return redirect("public_group")



@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def process_officer_application_result(request):
	"""
	Appoints (or rejects) an officer in public mehfil

	Can also bestow powers selectively
	"""
	if request.method == "POST":
		group_uuid = request.POST.get("guid",None)
		decision = request.POST.get("dec",None)
		pwr_decision = request.POST.get("pdec",None)
		if pwr_decision == '0':
			# simply return to officer screen - this implies no decision
			request.session.pop('final_officer_idx'+str(group_uuid),None)
			request.session.pop('final_officer_id'+str(group_uuid),None)# clearing out (in case it was populated)
			group_owner_id, group_id = retrieve_group_owner_id(group_uuid=group_uuid,with_group_id=True)
			return render(request,"mehfil/manage_public_group_officers.html",{'topic':retrieve_group_topic(group_id),\
				'guid':group_uuid,'applications':retrieve_all_current_applications(group_id=group_id),'add_officers':True,\
				'females':FEMALES})
		elif pwr_decision == '1':
			# powers are selected (to be given to the selected officer)
			own_id = str(request.user.id)
			group_owner_id, group_id = retrieve_group_owner_id(group_uuid=group_uuid,with_group_id=True)
			if group_owner_id == own_id:
				power_ids = request.POST.getlist('pids',[])
				power_levels = ['1']#adding '1' by default (i.e. 'hide')
				for power_id in power_ids:
					if power_id in ('2','3'):
						power_levels.append(power_id)
				idx = request.session.pop('final_officer_idx'+str(group_uuid),None)
				candidate_id = request.session.pop('final_officer_id'+str(group_uuid),None)
				if candidate_id:
					case_exists = officer_appointed_too_many_times(candidate_id)
					if case_exists:
						# any user with more than MAX_OFFICER_APPOINTMENTS_ALLWD should NOT be made an officer
						return render(request,"mehfil/public_group_administration.html",{'topic':retrieve_group_topic(group_id),\
							'owner':True,'uname':retrieve_uname(candidate_id,decode=True),'cannot_make_officer':True, \
							'unique':group_uuid,'limit':MAX_OFFICER_APPOINTMENTS_ALLWD})
					elif can_make_officer(candidate_id, group_id, group_owner_id):
						can_proceed = officer_application_exists(group_id, candidate_id)
						if can_proceed:
							# finally perform the deed!
							appoint_public_mehfil_officer(group_owner_id, group_id, candidate_id, idx, power_levels=power_levels, \
								appointment_time=time.time(), owner_uname=retrieve_uname(group_owner_id,decode=True))
							return render(request,"mehfil/public_group_administration.html",{'topic':retrieve_group_topic(group_id),\
								'officers_appointed':True,'owner':True,'unique':group_uuid})
						else:
							# the application is not found! - simply return to officer screen
							return render(request,"mehfil/manage_public_group_officers.html",{'topic':retrieve_group_topic(group_id),\
								'guid':group_uuid,'applications':retrieve_all_current_applications(group_id=group_id),'add_officers':True,\
								'females':FEMALES})
					else:
						# not legal to make this person an officer any more
						rescind_officer_applications(candidate_id, group_id)#
						# redirect to default 'owner' screen
						return render(request,"mehfil/public_group_administration.html",{'topic':retrieve_group_topic(group_id),\
							'cannot_process_officer_application':True,'applier_name':retrieve_uname(candidate_id,decode=True),\
							'owner':True,'unique':group_uuid})
				else:
					# no ID available to be made an officer!?
					return redirect("public_group", slug=group_uuid)
			else:
				# user isn't authorized to do this
				raise Http404("You are not authorized to decide an officer's application")

		elif decision in ('0','1'):
			# application accepted or rejected
			own_id = str(request.user.id)
			group_owner_id, group_id = retrieve_group_owner_id(group_uuid=group_uuid,with_group_id=True)
			if group_owner_id == own_id:
				candidate_id = request.POST.get("cid",None)
				if decision == '1':
					# make candidate an officer
					if can_make_officer(candidate_id, group_id, group_owner_id):
						ttl = is_officer_appointments_rate_limited(group_owner_id,group_id)
						if ttl:
							# officer appointments are rate-limited
							return render(request,"mehfil/public_group_administration.html",{'topic':retrieve_group_topic(group_id),\
								'owner':True,'ttl':ttl,'unique':group_uuid})
						else:
							#proceed
							case_exists = officer_appointed_too_many_times(candidate_id)
							if case_exists:
								# any user with more than MAX_OFFICER_APPOINTMENTS_ALLWD should NOT be made an officer
								return render(request,"mehfil/public_group_administration.html",{'topic':retrieve_group_topic(group_id),\
									'owner':True,'uname':retrieve_uname(candidate_id,decode=True),'cannot_make_officer':True, \
									'unique':group_uuid,'limit':MAX_OFFICER_APPOINTMENTS_ALLWD})
							else:
								can_proceed = officer_application_exists(group_id, candidate_id)
								if can_proceed:
									# decide candidate perms - they are well on their way to becoming an offier
									request.session['final_officer_idx'+str(group_uuid)] = request.POST.get("idx",None)
									request.session["final_officer_id"+str(group_uuid)] = candidate_id
									request.session.modified = True
									return render(request,"mehfil/manage_public_group_officers.html",{'guid':group_uuid,\
										'set_priveleges':True})
								else:
									# officer's application does not exist - simply return to officer screen
									return render(request,"mehfil/manage_public_group_officers.html",{'topic':retrieve_group_topic(group_id),\
										'guid':group_uuid,'applications':retrieve_all_current_applications(group_id=group_id),'add_officers':True,\
										'females':FEMALES})

					else:
						# it's not legal to make this user an officer
						rescind_officer_applications(candidate_id, group_id)#
						# simply return to officer screen - this implies no decision
						return render(request,"mehfil/manage_public_group_officers.html",{'topic':retrieve_group_topic(group_id),\
							'guid':group_uuid,'applications':retrieve_all_current_applications(group_id=group_id),'add_officers':True,\
							'females':FEMALES})
				else:
					# reject application (owner's decision = '0')
					rescind_officer_applications(candidate_id, group_id, rejection=True)#
					# simply return to officer screen - this implies no decision
					return render(request,"mehfil/manage_public_group_officers.html",{'topic':retrieve_group_topic(group_id),\
						'guid':group_uuid,'applications':retrieve_all_current_applications(group_id=group_id),'add_officers':True,\
						'females':FEMALES})
			else:
				# not authorized to be doing this
				raise Http404("You are not authorized to decide an officer's application")
		else:
			# invalid 'decision' value
			return redirect("public_group", slug=group_uuid)
	else:
		# not a POST request
		return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def remove_officer(request):
	"""
	Removes officers in public mehfil
	"""
	group_uuid = request.session.get("public_uuid",None)
	if request.method == "POST":
		decision = request.POST.get("dec",None)
		if decision == '0':
			return redirect("public_group", slug=group_uuid)
		elif decision == '1':
			# officer IDs are selected
			officer_ids = request.POST.getlist('oids',[])
			if officer_ids:
				group = retrieve_group_meta_data(group_uuid=group_uuid)
				if group:
					owner_id = group['oi']
				else:
					# no group found
					return redirect("group_page")
				if owner_id == str(request.user.id):
					num_to_remove = len(officer_ids)
					remove_public_mehfil_officers(officer_ids=officer_ids,group_id=group['gi'],num_to_remove=num_to_remove,\
						remover_uname=retrieve_uname(owner_id,decode=True),removal_time=time.time())
					return render(request,"mehfil/public_group_administration.html",{'topic':group['tp'],'officers_removed':True,\
						'owner':True,'num_removed':num_to_remove,'unique':group_uuid})
				else:
					# unauthorized user
					return redirect("group_page")
			else:
				return redirect("public_group", slug=group_uuid)
		else:
			return redirect("group_page")
	else:
		return redirect("public_group", slug=group_uuid)


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def apply_for_officer(request):
	"""
	Enables a public mehfil member to apply to become an officer
	"""
	if request.method == 'POST':
		group_uuid = request.POST.get('guid',None)
		decision = request.POST.get('dec',None)
		if decision == '1':
			# is user currently a member of the said group (but not officer, neither owner)?
			own_id = request.user.id
			group_owner_id, group_id = retrieve_group_owner_id(group_uuid=group_uuid,with_group_id=True)
			if can_make_officer(own_id, group_id, group_owner_id):
				try:
					join_date = convert_to_epoch(User.objects.only('date_joined').get(id=own_id).date_joined)
				except User.DoesNotExist:
					# this user does not exist thus data incomplete
					raise Http404("You cannot apply to become an officer because you don't exist!")
				time_now = time.time()
				recent_app_joiner, recent_mehfil_joiner = user_too_young_to_become_officer(own_id, time_now,join_date, \
					retrieve_group_joining_time(group_id, own_id))
				if recent_app_joiner or recent_mehfil_joiner:
					# the user is a recent arrival - gently turn them away
					return render(request,"mehfil/notify_and_redirect.html",{'too_young_for_officer':True,'unique':group_uuid,\
						'youth_type':'recent_app_joiner' if recent_app_joiner else 'recent_mehfil_joiner'})
				else:
					form = OfficerApplicationForm(data=request.POST)
					if form.is_valid():
						own_uname, own_avurl = retrieve_credentials(own_id,decode_uname=True)
						ttl, ttl_type = save_officer_application(applier_id=own_id,group_id=group_id, time_now=time_now, \
							payload={'ans1':form.cleaned_data.get("answer1"),'ans2':form.cleaned_data.get("answer2"),\
							'user_id':own_id,'gid':group_id,'uname':own_uname,'own_avurl':own_avurl,'t':time_now})
						if ttl:
							# rate limited from sending an application
							return render(request,"mehfil/notify_and_redirect.html",{'officer_app_rate_limited':True,'unique':group_uuid,\
								'ttl':ttl,'ttl_type':ttl_type})
						else:
							return render(request,"mehfil/notify_and_redirect.html",{'officer_app_submitted':True,'unique':group_uuid})
					else:
						return render(request,"mehfil/officership_application.html",{'unique':group_uuid,'q1':GROUP_OFFICER_QUESTIONS['1'],\
							'q2':GROUP_OFFICER_QUESTIONS['2'],'form':form})
			else:
				# this person is a not a member of the said group, or is an officer already, or is an owner
				raise Http404("You cannot apply to become an officer")
		else:
			# the user pressed 'Cancel', return to group
			return redirect("public_group", slug=group_uuid)
	else:
		# not a POST request
		return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def view_officer_application_form(request):
	"""
	Displays officer application form so that a user can fill it and submit it

	Once this form is submitted, the POST data is handled by apply_for_officer() above
	"""
	if request.method == "POST":
		own_id = request.user.id
		group_uuid = request.POST.get("guid",None)
		return render(request,"mehfil/officership_application.html",{'form':OfficerApplicationForm(),'q1':GROUP_OFFICER_QUESTIONS['1'],\
			'q2':GROUP_OFFICER_QUESTIONS['2'],'unique':group_uuid})
	else:
		# not a POST request
		return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def view_own_officer_app_history(request):
	"""
	Displays own history of officer applications to various public groups
	"""
	if request.method == "POST":
		own_id = request.user.id
		group_uuid = request.POST.get("guid",None)
		apps_submitted, apps_accepted, num_officers = retrieve_officer_stats(user_id=own_id)
		historical_records = retrieve_all_current_applications(user_id=own_id)
		records_truncated = len(historical_records) < int(apps_submitted)
		return render(request,"mehfil/user_officer_app_history.html",{'unique':group_uuid,'q1':GROUP_OFFICER_QUESTIONS['1'],\
			'q2':GROUP_OFFICER_QUESTIONS['2'],'user_officer_app_history':historical_records,'apps_submitted':apps_submitted, \
			'apps_accepted':apps_accepted,'currently_officer':num_officers,'records_truncated':records_truncated})
	else:
		# not a POST request
		return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def view_officer_app_help(request):
	"""
	Renders help page regarding dropping officer applications to public groups
	"""
	if request.method == "POST":
		own_id = request.user.id
		group_uuid = request.POST.get("guid",None)
		return render(request,"mehfil/user_officer_app_help.html",{'q1':GROUP_OFFICER_QUESTIONS['1'],'q2':GROUP_OFFICER_QUESTIONS['2'],\
			'unique':group_uuid})
	else:
		# not a POST request
		return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def view_officer_app_history(request):
	"""
	Displays applier's history of officer applications to various public groups

	This is the view shown to a public mehfil owner
	"""
	if request.method == "POST":
		own_id = request.user.id
		group_uuid = request.POST.get("guid",None)
		applier_id = request.POST.get("uid",None)
		group_owner_id, group_id = retrieve_group_owner_id(group_uuid=group_uuid,with_group_id=True)
		if group_owner_id == str(own_id):
			# did applier apply to this public group?
			can_proceed = officer_application_exists(group_id, applier_id)
			if can_proceed:
				idx = request.POST.get("idx",'')
				target_uname, target_avurl = retrieve_credentials(applier_id,decode_uname=True)
				apps_submitted, apps_accepted, num_officers = retrieve_officer_stats(user_id=applier_id)
				historical_records = retrieve_all_current_applications(user_id=applier_id)
				records_truncated = len(historical_records) < int(apps_submitted)
				return render(request,"mehfil/user_officer_app_history.html",{'unique':group_uuid,'q1':GROUP_OFFICER_QUESTIONS['1'],\
					'q2':GROUP_OFFICER_QUESTIONS['2'],'user_officer_app_history':historical_records,'mehfil_owner_mode':True,'idx':idx,\
					'target_uname':target_uname,'target_id':applier_id,'target_group_id':group_id,'target_avurl':target_avurl,\
					'apps_submitted':apps_submitted,'apps_accepted':apps_accepted,'females':FEMALES,'currently_officer':num_officers,\
					'records_truncated':records_truncated})
			else:
				# the application is not found! - simply return to officer screen
				return render(request,"mehfil/manage_public_group_officers.html",{'topic':retrieve_group_topic(group_id),\
					'guid':group_uuid,'applications':retrieve_all_current_applications(group_id=group_id),'add_officers':True,\
					'females':FEMALES})
		else:
			# not authorized to view this
			raise Http404("You cannot view this application")
	else:
		# not a POST request
		return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def display_officer_application(request):
	"""
	Retrieves and renders application officer for the viewing pleasure of the group owner
	"""
	if request.method == "POST":
		group_uuid = request.POST.get('guid',None)
		own_id = request.user.id
		group_owner_id, group_id = retrieve_group_owner_id(group_uuid=group_uuid,with_group_id=True)
		if group_owner_id == str(own_id):
			candidate_id = request.POST.get('cid',None)
			# is candidate legit?
			if can_make_officer(candidate_id, group_id, group_owner_id):
				app_idx = request.POST.get('idx',None)
				data = retrieve_single_group_application(candidate_id, group_id, app_idx)
				if data:
					# render the application data for the viewing pleasure of the owner
					request.session["public_uuid"] = group_uuid
					request.session.modified = True
					return render(request,"mehfil/view_officer_application.html",{'application':data,'guid':group_uuid,\
						'q1':GROUP_OFFICER_QUESTIONS['1'],'q2':GROUP_OFFICER_QUESTIONS['2'],'females':FEMALES})
				else:
					# data could not be loaded (maybe it has expired), so rescind their application(s)
					rescind_officer_applications(candidate_id, group_id)
					# redirect to default 'owner' screen
					return render(request,"mehfil/public_group_administration.html",{'topic':retrieve_group_topic(group_id),\
						'cannot_process_officer_application':True,'applier_name':retrieve_uname(candidate_id,decode=True),\
						'owner':True,'unique':group_uuid})
			else:
				# candidate is not legit, so rescind their application(s)
				rescind_officer_applications(candidate_id, group_id)
				# redirect to default 'owner' screen
				return render(request,"mehfil/public_group_administration.html",{'topic':retrieve_group_topic(group_id),\
					'cannot_process_officer_application':True,'applier_name':retrieve_uname(candidate_id,decode=True),\
					'owner':True,'unique':group_uuid})
		else:
			# not your group
			raise Http404("You cannot view this application")
	else:
		# not a POST request
		return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def display_officer_app_detailed_info(request):
	"""
	Displays detailed definition behind officer app metrics (e.g. number of applications submitted, how many accepted, etc)
	"""
	if request.method == "POST":
		which_info = request.POST.get("inf",None)
		if which_info in ('1','2','3'):
			for_self = request.POST.get("fself",None)
			if for_self in ('1','0'):
				group_uuid = request.POST.get("guid",None)
				own_id = request.user.id
				if for_self == '1':
					# this detail page is for self (can view own statistics)
					if which_info == '1':
						# num apps submitted
						data = retrieve_officer_stats(user_id=own_id,stat_type='apps_submitted')
					elif which_info == '2':
						# num apps accepted
						data = retrieve_officer_stats(user_id=own_id,stat_type='apps_accepted')
					else:
						# num officerships (currently)
						data = retrieve_officer_stats(user_id=own_id,stat_type='currently_officer')
					return render(request,"mehfil/officer_app_detailed_info.html",{'info':which_info,'guid':group_uuid,'data':data})
				else:
					# this detail page is for group owner (can view stats if legit)
					canonical_group_owner_id, group_id = retrieve_group_owner_id(group_uuid=group_uuid,with_group_id=True)
					if (str(own_id) == canonical_group_owner_id):
						target_id = request.POST.get("tid",None)
						if officer_application_exists(group_id, target_id):
							# target_id indeed applied for officership in group owner's group
							if which_info == '1':
								# num apps submitted
								data = retrieve_officer_stats(user_id=target_id,stat_type='apps_submitted')
							elif which_info == '2':
								# num apps accepted
								data = retrieve_officer_stats(user_id=target_id,stat_type='apps_accepted')
							else:
								# num officerships (currently)
								data = retrieve_officer_stats(user_id=target_id,stat_type='currently_officer')
							target_uname, target_avurl = retrieve_credentials(target_id,decode_uname=True)
							return render(request,"mehfil/officer_app_detailed_info.html",{'info':which_info,'guid':group_uuid,\
								'data':data, 'mehfil_owner_mode':True,'target_uname':target_uname,'target_avurl':target_avurl,\
								'females':FEMALES})
						else:
							# target_id doesn't have an outstanding application in owner's group
							return redirect("public_group")
					else:
						# you do not own the group
						raise Http404("You cannot view this detail")
			else:
				# data tinkered
				raise Http404("You cannot view this detail")
		else:
			# data tinkered
			raise Http404("You cannot view this detail")
	else:
		# not a POST request
		return redirect("public_group")


def display_administrative_activity(request, slug):
	"""
	Displays administrative activity taking place in a public or private group
	"""
	if slug not in ('public','private'):
		return redirect("missing_page")
	else:
		guid = request.session.pop("administrative_activity_uuid",None)
		if guid:
			group_owner_id, group_id, group_privacy = retrieve_group_owner_id(group_uuid=guid,with_group_id=True,with_group_privacy=True)
			if group_id:
				own_id = str(request.user.id)
				is_public = False if group_privacy == '1' else True
				if is_public:
					is_owner = own_id == group_owner_id
					if is_owner or is_group_officer(group_id, own_id):
						# this data is only available to group officers or group owners
						return render(request,"mehfil/group_history.html",{'object_list':retrieve_group_administrative_activity(group_id),'unique':guid,\
							'show_tut':tutorial_unseen(user_id=own_id, which_tut='18', renew_lease=True),'owner':is_owner,'is_public':True})
					else:
						# not authorized to view this
						return redirect("public_group")
				else:
					# private group - only members can view
					if group_member_exists(group_id, own_id):
						# allowed to view history
						return render(request,"mehfil/group_history.html",{'object_list':retrieve_group_administrative_activity(group_id),'unique':guid,\
							'show_tut':tutorial_unseen(user_id=own_id, which_tut='24', renew_lease=True),'is_public':False})
					else:
						# not a member - unauthorized
						return redirect("group_page")
			else:
				# group doesn't exist
				return redirect("group_page")
		else:
			return redirect("public_group")


def show_open_group_feedback(request,pk,*args,**kwargs):
	"""
	Displays feedback received by a mehfil owner
	"""
	group_uuid = request.session.get("public_uuid",None)
	if pk:
		group_owner_id, group_id = retrieve_group_owner_id(group_uuid=group_uuid,with_group_id=True)
		own_id = str(request.user.id)
		if group_owner_id == own_id:
			# authorized to view feedback
			feedback = retrieve_open_group_feedback(group_id, feedback_type=pk)# returns list of dicts
			return render(request,"mehfil/open_group_feedback.html",{'feedback':feedback,'type':pk,'guid':group_uuid,\
				'show_instr':True if (pk=='2' and tutorial_unseen(user_id=own_id, which_tut='21', renew_lease=True)) else False})
		else:
			# unauthorized option
			return redirect("group_page")
	else:
		return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def delete_open_group_feedback(request):
	"""
	Deleting a feedback section, initiated by public mehfil owner
	"""
	if request.method == "POST":
		decision = request.POST.get("dec",None)
		if decision == '1':
			guid = request.POST.get("guid",None)
			group_owner_id, group_id = retrieve_group_owner_id(group_uuid=guid,with_group_id=True)
			if group_owner_id == str(request.user.id):
				# authorized to perform this function
				feedback_type = request.POST.get("type",None)
				delete_specific_group_feedback(group_id, feedback_type)
				return redirect("show_open_group_feedback",feedback_type)
			else:
				# unauthorized option
				return redirect("group_page")
		else:
			return redirect("public_group")
	else:
		# not a POST method
		return redirect("public_group")


############################## Mehfil punishments ##############################

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def process_kicking_feedback(request, slug):
	"""
	Saves the reason provided by punisher, making it visible to the kicked out user(s)
	"""
	if slug not in ('public','private'):
		return redirect("missing_page")
	elif request.method == "POST":
		unkick_feedback_decision = request.POST.get("ukfb",None)
		kick_feedback_decision = request.POST.get("kfdec",None)
		if unkick_feedback_decision == '1':
			group_id = request.session.pop("affected_group_id",None)
			group_privacy = request.session.pop("affected_group_privacy"+str(group_id),'') if group_id else ''
			guid = request.session.pop("affected_group_uuid"+str(group_id),None) if group_id else None
			activity_id = request.session.pop("affected_group_activity_id"+str(group_id)) if group_id else None
			form = GroupFeedbackForm(data=request.POST)
			if form.is_valid():
				feedback = form.cleaned_data.get("feedback")
				add_unkick_feedback(group_id, activity_id, feedback)
				if group_privacy == '1':
					# private group
					request.session["unique_id"] = guid
					return redirect("private_group_reply")
				elif group_privacy == '0':
					# public group
					return redirect("public_group")
				else:
					if slug == 'public':
						return redirect("public_group")
					else:
						return redirect("private_group_reply")
			else:
				if group_privacy == '0':
					return render(request,'mehfil/take_action_against_group_visitors.html',{'show_unkick_feedback_options':True,'form':form,\
						'reason_len':GROUP_FEEDBACK_SIZE})
				elif group_privacy == '1':
					return render(request,"mehfil/kick_out_group_members.html",{'show_unkick_feedback_options':True,'form':form,\
						'reason_len':GROUP_FEEDBACK_SIZE})
				else:
					if slug == 'public':
						return redirect("public_group")
					else:
						return redirect("private_group_reply")
		elif kick_feedback_decision == '1':
			group_id = request.session.pop("affected_group_id",None)
			activity_id = request.session.pop("affected_group_activity_id"+str(group_id),None) if group_id else None
			culprit_ids = request.session.pop("final_kick_ids"+str(group_id),[]) if group_id else []
			group_privacy = request.session.pop("affected_group_privacy"+str(group_id),'') if group_id else ''
			guid = request.session.pop("affected_group_uuid"+str(group_id),None) if group_id else None
			form = GroupFeedbackForm(data=request.POST)
			if form.is_valid():
				feedback = form.cleaned_data.get("feedback")
				add_kick_feedback(group_id, culprit_ids, activity_id, kick_feedback=feedback)
				if group_privacy == '1':
					# private group
					request.session["unique_id"] = guid
					return redirect("private_group_reply")
				elif group_privacy == '0':
					# public group
					return redirect("public_group", guid)
				else:
					if slug == 'public':
						return redirect("public_group")
					else:
						return redirect("private_group_reply")
			else:
				if group_privacy == '0':
					return render(request,'mehfil/take_action_against_group_visitors.html',{'show_kick_feedback_options':True,'form':form,\
						'reason_len':GROUP_FEEDBACK_SIZE})
				elif group_privacy == '1':
					return render(request,"mehfil/kick_out_group_members.html",{'show_kick_feedback_options':True,'form':form,\
						'reason_len':GROUP_FEEDBACK_SIZE})
				else:
					if slug == 'public':
						return redirect("public_group")
					else:
						return redirect("private_group_reply")
		else:
			# the user decided to not give any feedback
			if slug == 'public':
				return redirect("public_group")
			else:
				return redirect("private_group_reply")
	else:
		if slug == 'public':
			return redirect("public_group")
		else:
			return redirect("private_group_reply")



@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def unkick_users(request, slug):
	"""
	Removes users from kicked list (in public mehfil)
	"""
	if request.user_banned:
		return redirect("error")
	elif slug not in ('private','public'):
		return redirect("missing_page")
	elif request.method == "POST":
		own_id = str(request.user.id)
		unkick_decision = request.POST.get("ukdec",None)
		if unkick_decision == '1':
			guid = request.POST.get("guid",None)
			group_owner_id, group_id, group_privacy = retrieve_group_owner_id(group_uuid=guid,with_group_id=True,with_group_privacy=True)
			if group_id:
				is_public = False if group_privacy == '1' else True
				if is_public:
					authorized_officer = can_officer_kick_out(group_id, own_id)
					if group_owner_id == own_id or authorized_officer:
						# authorized to unban the user
						target_ids = request.POST.getlist('tids',[])#in list format
						if not target_ids:
							# nothing was selected, return to mehfil
							return redirect("public_group")
						else:
							# unkick/unban the relevant users
							ttl, activity_id = unkick_users_from_group(group_id, target_ids, time.time(), retrieve_uname(own_id,decode=True), own_id)
							if ttl:
								# cannot do it since rate limited
								return render(request,"mehfil/notify_and_redirect.html",{'kick_rate_limited':True,'ttl':ttl,'unique':guid})
							elif activity_id:
								# provide optional form where original kickers of unkicked user(s) can be given feedback - so that they don't get pissed off (i.e. "who unbanned this dude? I had banned him for a good reason!")
								request.session["affected_group_id"] = group_id
								request.session["affected_group_activity_id"+str(group_id)] = activity_id
								request.session.modified = True
								return render(request,'mehfil/take_action_against_group_visitors.html',{'show_unkick_feedback_options':True,'form':GroupFeedbackForm(),\
									'reason_len':GROUP_FEEDBACK_SIZE})
							else:
								# no unkicking activity generated - perhaps culprits already kicked by an officer
								return redirect("public_group")
					else:
						# unauthorized option
						return redirect("group_page")
				else:
					# is a private group
					if group_owner_id == own_id:
						# authorized to unban the user
						target_ids = request.POST.getlist('tids',[])#in list format
						if not target_ids:
							# nothing was selected, return to mehfil
							request.session["unique_id"] = guid
							return redirect("private_group_reply")
						else:
							# unkick/unban the relevant users
							ttl, activity_id = unkick_users_from_group(group_id, target_ids, time.time(), retrieve_uname(own_id,decode=True), own_id)
							if ttl:
								# cannot do it since rate limited
								return render(request,"mehfil/notify_and_redirect.html",{'kick_rate_limited':True,'unique':guid,'is_public':is_public,\
									'ttl':ttl})
							elif activity_id:
								# provide optional form where original kickers of unkicked user(s) can be given feedback - so that they don't get pissed off (i.e. "who unbanned this dude? I had banned him for a good reason!")
								request.session["affected_group_id"] = group_id
								request.session["affected_group_activity_id"+str(group_id)] = activity_id
								request.session["affected_group_privacy"+str(group_id)] = '0' if is_public else '1'
								request.session["affected_group_uuid"+str(group_id)] = guid
								request.session.modified = True
								if is_public:
									return render(request,'mehfil/take_action_against_group_visitors.html',{'show_unkick_feedback_options':True,\
										'form':GroupFeedbackForm(), 'reason_len':GROUP_FEEDBACK_SIZE})
								else:
									return render(request,"mehfil/kick_out_group_members.html",{'show_unkick_feedback_options':True,'form':GroupFeedbackForm(),\
										'reason_len':GROUP_FEEDBACK_SIZE})
								# return render(request,'mehfil/take_action_against_group_visitors.html',{'show_unkick_feedback_options':True,'form':GroupFeedbackForm(),\
								# 	'reason_len':GROUP_FEEDBACK_SIZE})
							else:
								# no unkicking activity generated - perhaps culprits already kicked by an officer
								if is_public:
									return redirect("public_group")
								else:
									request.session["unique_id"] = guid
									return redirect("private_group_reply")
					else:
						# unauthorized access
						return redirect("group_page")
			else:
				# group doesnt exist
				return redirect("group_page")
		else:
			# the user decided to not do anything - return to mehfil
			if slug == 'public':
				# not a POST method
				return redirect("public_group")
			else:
				return redirect("private_group_reply")
	else:
		if slug == 'public':
			# not a POST method
			return redirect("public_group")
		else:
			return redirect("private_group_reply")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def show_kicked_users(request, slug):
	"""
	Renders a list of all kicked users of a mehfil - useful for unblocking them
	"""
	if slug not in ('public','private'):
		return redirect("missing_page")
	elif request.method == "POST":
		guid = request.POST.get("guid",None)
		group_owner_id, group_id, group_privacy = retrieve_group_owner_id(group_uuid=guid,with_group_id=True,with_group_privacy=True)
		if group_id:
			is_public = False if group_privacy == '1' else True
			if is_public:
				own_id = str(request.user.id)
				authorized_officer = can_officer_kick_out(group_id, own_id)
				if group_owner_id == own_id or authorized_officer:
					# authorized to see this list
					return render(request,"mehfil/banned_users_in_group.html",{'guid':guid,'banned_users':retrieve_kicked_user_ids(group_id, \
						with_details=True, prune_list=True),'privacy':'0','slug':'public'})
				else:
					# not authorized
					return redirect("group_page")
			else:
				# is a private group
				if group_owner_id == str(request.user.id):
					# authorized to view this list
					return render(request,"mehfil/banned_users_in_group.html",{'guid':guid,'banned_users':retrieve_kicked_user_ids(group_id, \
						with_details=True, prune_list=True),'privacy':'1','slug':'private'})
				else:
					# not authorized
					return redirect("group_page")
		else:
			# group not found
			return redirect("group_page")
	else:
		# not a POST method
		if slug == 'private':
			return redirect("private_group_reply")
		else:
			return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def kick_out(request, slug):
	"""
	Processing the kicking-out of an errant user from a public mehfil
	"""
	if request.user_banned:
		return redirect("error")
	elif slug not in ('public','private'):
		return redirect("missing_page")
	elif request.method == "POST":
		guid = request.POST.get("guid",None)
		kick_decision = request.POST.get("kdec",None)
		decision = request.POST.get("dec",None)
		group_owner_id, group_id, group_privacy = retrieve_group_owner_id(group_uuid=guid,with_group_id=True,with_group_privacy=True)
		if not group_owner_id:
			# group doesnt exist
			return redirect("group_page")
		elif kick_decision == '1':
			own_id = str(request.user.id)
			if group_owner_id == own_id:
				is_public = False if group_privacy == '1' else True
				kick_duration = request.POST.get("kdur",None)
				if kick_duration in ('1','2','3','4','5','6'):
					# take action
					time_now = time.time()
					own_uname, own_avurl = retrieve_credentials(own_id,decode_uname=True)
					culprit_ids = request.session.get("final_kick_ids"+str(group_id),[])
					culprit_ids = map(str,culprit_ids) if culprit_ids else culprit_ids
					ttl, kicked_nicknames, nickname_list, activity_id = kick_users_from_group(group_id, culprit_ids, time_now, own_uname, own_id, \
						kick_duration, is_public=is_public)
					if ttl:
						# cannot do it since rate limited
						return render(request,"mehfil/notify_and_redirect.html",{'kick_rate_limited':True,'ttl':ttl,'unique':guid,'is_public':is_public})
					elif kicked_nicknames and activity_id:
						# hide all messages of kicked culprits
						hide_writers_group_messages(group_id,culprit_ids)# works for public, private both
						###### remove from redis 1 legacy ##################
						remove_group_members(group_id, nickname_list)
						removed_culprit_ids = bulk_remove_user_group(culprit_ids, group_id, return_member_ids=True)
						bulk_remove_group_notification(removed_culprit_ids,group_id)# redis 2 - not legacy
						####################################################
						# produce group message of kicking out user
						save_group_submission(writer_id=own_id, group_id=group_id, text=kicked_nicknames,posting_time=time_now,\
							category='2',writer_uname=own_uname, writer_avurl=get_s3_object(own_avurl,category='thumb'))
						invalidate_cached_mehfil_replies(group_id)
						invalidate_presence(group_id)
						####################################################
						# provide optional form where kicked user(s) can receive feedback so that recidivism doesn't happen
						request.session["affected_group_id"] = group_id
						request.session["affected_group_activity_id"+str(group_id)] = activity_id
						request.session["affected_group_privacy"+str(group_id)] = '0' if is_public else '1'
						request.session["affected_group_uuid"+str(group_id)] = guid
						request.session.modified = True
						if is_public:
							return render(request,'mehfil/take_action_against_group_visitors.html',{'show_kick_feedback_options':True,\
								'form':GroupFeedbackForm(), 'reason_len':GROUP_FEEDBACK_SIZE})
						else:
							return render(request,"mehfil/kick_out_group_members.html",{'show_kick_feedback_options':True,'form':GroupFeedbackForm(),\
								'reason_len':GROUP_FEEDBACK_SIZE})
					else:
						# no kicking activity generated - perhaps culprits already kicked by an officer
						if is_public:
							return redirect("public_group", guid)
						else:
							request.session["unique_id"] = guid
							return redirect("private_group_reply")
				else:
					# the user decided to not take any action
					if is_public:
						return redirect("public_group", guid)
					else:
						request.session["unique_id"] = guid
						return redirect("private_group_reply")
			elif can_officer_kick_out(group_id, own_id):
				kick_duration = request.POST.get("kdur",None)
				if kick_duration in ('1','2','3'):
					# take action
					time_now = time.time()
					own_uname, own_avurl = retrieve_credentials(own_id,decode_uname=True)
					culprit_ids = request.session.get("final_kick_ids"+str(group_id),[])
					culprit_ids = map(str,culprit_ids) if culprit_ids else culprit_ids
					ttl, kicked_nicknames, nickname_list, activity_id = kick_users_from_group(group_id, culprit_ids, time_now, own_uname, own_id, \
						kick_duration, is_public=True)
					if ttl:
						# cannot do it since rate limited
						return render(request,"mehfil/notify_and_redirect.html",{'kick_rate_limited':True,'ttl':ttl,'unique':guid})
					elif kicked_nicknames and activity_id:
						# hide all messages of kicked culprits
						hide_writers_group_messages(group_id,culprit_ids)
						###### remove from redis 1 legacy ##################
						remove_group_members(group_id, nickname_list)
						removed_culprit_ids = bulk_remove_user_group(culprit_ids, group_id, return_member_ids=True)
						bulk_remove_group_notification(removed_culprit_ids,group_id)
						####################################################
						# produce group message
						save_group_submission(writer_id=own_id, group_id=group_id, text=kicked_nicknames,posting_time=time_now,\
							category='2',writer_uname=own_uname, writer_avurl=get_s3_object(own_avurl,category='thumb'))
						invalidate_cached_mehfil_replies(group_id)
						invalidate_presence(group_id)
						####################################################
						# provide optional form where kicked user(s) can receive feedback so that recidivism doesn't happen
						request.session["affected_group_id"] = group_id
						request.session["affected_group_activity_id"+str(group_id)] = activity_id
						request.session["affected_group_privacy"+str(group_id)] = '0'
						request.session["affected_group_uuid"+str(group_id)] = guid
						request.session.modified = True
						return render(request,'mehfil/take_action_against_group_visitors.html',{'show_kick_feedback_options':True,\
							'form':GroupFeedbackForm(), 'reason_len':GROUP_FEEDBACK_SIZE})
					else:
						# no kicking activity generated - perhaps culprits already kicked by another officer
						return redirect("public_group")
				else:
					# the user decided to not take any action
					return redirect("public_group")
			else:
				# the user is unauthorized to do this
				return redirect("group_page")
		elif decision == '1':
			own_id = str(request.user.id)
			time_now = time.time()
			if own_id == group_owner_id:
				# show owner's kicking out options
				is_public = False if group_privacy == '1' else True
				if is_public:
					culprit_ids = request.POST.getlist('cids',[])
				else:
					culprit_id = request.POST.get('cid',None)
					culprit_ids = [culprit_id] if culprit_id else culprit_id#changing to list format since the rest of the function supports that
				if not culprit_ids:
					# no one was selected
					if is_public:
						return redirect("public_group", guid)
					else:
						request.session["unique_id"] = guid
						return redirect("private_group_reply")
				elif own_id in culprit_ids:
					return render(request,"mehfil/notify_and_redirect.html",{'cannot_target_self':True, 'is_public':is_public,'unique':guid})
				else:
					culprit_ids = filter_non_members(culprit_ids, group_id)# remove non-members from the list (ensures group admins can't kick "non-members")
					culprit_ids = filter_non_recents(culprit_ids, group_id, time_now) if is_public else culprit_ids# remove non-recents from the list if public group - in private, any user can be kicked out (even if non-recent)
					if culprit_ids:
						request.session["final_kick_ids"+str(group_id)] = culprit_ids
						request.session.modified = True
						if is_public:
							return render(request,"mehfil/take_action_against_group_visitors.html",{'show_punishment_options':True,'owner':True,'kick':True,\
								'guid':guid})
						else:
							return render(request,"mehfil/kick_out_group_members.html",{'guid':guid,'show_punishment_options':True})
					else:
						# no selection remains (i.e. all IDs filtered out)
						if is_public:
							return redirect("public_group", guid)
						else:
							request.session["unique_id"] = guid
							return redirect("private_group_reply")
			elif can_officer_kick_out(group_id, own_id):
				# show officer's kicking out options (only related to public mehfil - does not exist for private groups)
				culprit_ids = request.POST.getlist('cids',[])#in list format (ensure these ids are RECENT AND MEMBERS)
				if not culprit_ids:
					# no one was selected
					return redirect("public_group")
				elif group_owner_id in culprit_ids:
					return render(request,"mehfil/notify_and_redirect.html",{'cannot_target_owner':True})
				elif own_id in culprit_ids:
					return render(request,"mehfil/notify_and_redirect.html",{'cannot_target_self':True})
				elif group_officer_targeted(group_id,culprit_ids):
					return render(request,"mehfil/notify_and_redirect.html",{'cannot_target_officers':True})
				else:
					culprit_ids = filter_non_members(culprit_ids, group_id)# remove non-members from the list
					culprit_ids = filter_non_recents(culprit_ids, group_id, time_now)# remove non-recents from the list
					if culprit_ids:
						request.session["final_kick_ids"+str(group_id)] = culprit_ids
						request.session.modified = True
						return render(request,"mehfil/take_action_against_group_visitors.html",{'show_punishment_options':True,'officer':True,'kick':True,\
							'guid':guid})
					else:
						# no selection remains
						return redirect("public_group")
			else:
				# unauthorized user
				return redirect("group_page")	
		else:
			# the user decided to not take any action
			is_public = False if group_privacy == '1' else True
			if is_public:
				return redirect("public_group", guid)
			else:
				request.session["unique_id"] = guid
				return redirect("private_group_reply")
	else:
		# not a POST method
		if slug == 'public':
			return redirect("public_group")
		elif slug == 'private':
			return redirect("private_group_reply")
		else:
			return redirect("group_page")



# @cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
# @csrf_protect
# def slow_down(request):
# 	"""
# 	Processing the slowing down of an errant user from a public mehfil
# 	"""
# 	if request.user_banned:
# 		return redirect("error")
# 	elif request.method == "POST":
# 		kick_decision = request.POST.get("kdec",None)
# 		decision = request.POST.get("dec",None)
# 		if kick_decision == '1':
# 			group_owner_id, group_id = retrieve_group_owner_id(group_uuid=request.POST.get("guid",None),with_group_id=True)
# 			if group_owner_id:
# 				own_id = str(request.user.id)
# 				if group_owner_id == own_id:
# 					slow_duration = request.POST.get("sdur",None)
# 					if slow_duration in ('1','2','3','4','5','6'):
# 						# take action
# 						time_now = time.time()
# 						culprit_ids = request.session.get("final_slow_ids"+str(group_id),[])
# 						culprit_ids = map(str,culprit_ids) if culprit_ids else culprit_ids
# 						# ttl = slow_users_in_group(group_id, culprit_ids, time_now, retrieve_uname(own_id,decode=True), own_id, slow_duration)
# 						# provide optional form where slowed user(s) can receive feedback so that recidivism doesn't happen
# 					else:
# 						# the user decided to not take any action
# 						return redirect("public_group")
# 				elif is_group_officer(group_id,own_id):
# 					slow_duration = request.POST.get("sdur",None)
# 					if slow_duration in ('1','2','3'):
# 						# take action
# 						time_now = time.time()
# 						culprit_ids = request.session.get("final_slow_ids"+str(group_id),[])
# 						culprit_ids = map(str,culprit_ids) if culprit_ids else culprit_ids
# 						# ttl = slow_users_in_group(group_id, culprit_ids, time_now, retrieve_uname(own_id,decode=True), own_id, slow_duration)
# 						# provide optional form where slowed user(s) can receive feedback so that recidivism doesn't happen
# 					else:
# 						# the user decided to not take any action
# 						return redirect("public_group")
# 				else:
# 					# the user is unauthorized to do this
# 					return redirect("group_page")
# 			else:
# 				# group probably does not exist
# 				return redirect("group_page")	
# 		elif decision == '1':
# 			group_owner_id, group_id = retrieve_group_owner_id(group_uuid=request.POST.get("guid",None),with_group_id=True)
# 			if group_owner_id:
# 				own_id = str(request.user.id)
# 				if own_id == group_owner_id:
# 					# show owner's slowing down options
# 					culprit_ids = request.POST.getlist('cids',[])#in list format
# 					if not culprit_ids:
# 						# no one was selected
# 						return redirect("public_group")
# 					elif own_id in culprit_ids:
# 						return render(request,"mehfil/notify_and_redirect.html",{'cannot_target_self':True})
# 					else:
# 						# punish the rest!
# 						request.session["final_slow_ids"+str(group_id)] = culprit_ids
# 						request.session.modified = True
# 						return render(request,"mehfil/take_action_against_group_visitors.html",{'show_punishment_options':True,'owner':True,'slow':True})
# 				elif is_group_officer(group_id,own_id):
# 					# show officer's slowing down options
# 					culprit_ids = request.POST.getlist('cids',[])
# 					if not culprit_ids:
# 						# no one was selected
# 						return redirect("public_group")
# 					elif group_owner_id in culprit_ids:
# 						return render(request,"mehfil/notify_and_redirect.html",{'cannot_target_owner':True})
# 					elif own_id in culprit_ids:
# 						return render(request,"mehfil/notify_and_redirect.html",{'cannot_target_self':True})
# 					elif group_officer_targeted(group_id,culprit_ids):
# 						return render(request,"mehfil/notify_and_redirect.html",{'cannot_target_officers':True})
# 					else:
# 						# punish the rest!
# 						request.session["final_slow_ids"+str(group_id)] = culprit_ids
# 						request.session.modified = True
# 						return render(request,"mehfil/take_action_against_group_visitors.html",{'show_punishment_options':True,'officer':True,'slow':True})
# 				else:
# 					# unauthorized user
# 					return redirect("group_page")	
# 			else:
# 				# group probably does not exist
# 				return redirect("group_page")
# 		else:
# 			# the user decided to not take any action
# 			return redirect("public_group")
# 	else:
# 		# not a POST method
# 		return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def private_group_hide_submission(request):
	"""
	Hide/unhide a private mehfil submission
	
	RULES:
	1) A regular member can hide their own submission
	2) The owner can hide any submission
	3) A regular member can unhide their submission if it wasn't hidden by the owner
	4) The owner can unhide a user's submission only if it was hidden by the owner
	"""
	if request.method == "POST":
		group_id = request.POST.get("gid",None)
		group_owner_id = retrieve_group_owner_id(group_id=group_id)
		if group_owner_id:
			submission_id = request.POST.get("pk",None)# reply id
			decision = request.POST.get("dec",None)# 'h' for hide, 'u' for unhide
			if decision not in ('h','u'):
				# tinkered with
				return redirect("group_page")
			elif not submission_id:
				# cannot proceed since no submission ID provided
				return redirect("private_group_reply")
			else:
				own_id = request.user.id
				unique = retrieve_group_uuid(group_id)
				is_group_owner = str(own_id) == group_owner_id
				writer_id = retrieve_single_group_submission(group_id, submission_id, writer_id_only=True)# returns writer_id if hash exists
				is_writer = str(own_id) == writer_id
				is_member = group_member_exists(group_id, own_id)
				if is_group_owner and is_writer:
					# can both hide and unhide the submission with impunity
					if decision == 'h':
						# hide
						action_successful = hide_private_group_submission(group_id,submission_id,action_by='owner')
						if action_successful:
							####### construct and add to administrative activity #######
							construct_administrative_activity.delay(own_id, writer_id, time.time(), group_id, 'hide', submission_id)
							############################################################
						invalidate_cached_mehfil_replies(group_id)
						invalidate_presence(group_id)
						request.session["unique_id"] = unique
						return redirect("private_group_reply")
					else:
						# unhide
						action_successful = hide_private_group_submission(group_id,submission_id,unhide=True,action_by='owner')
						if action_successful:
							####### construct and add to administrative activity #######
							construct_administrative_activity.delay(own_id, writer_id, time.time(), group_id, 'unhide', submission_id)
							############################################################
						invalidate_cached_mehfil_replies(group_id)
						invalidate_presence(group_id)
						request.session["unique_id"] = unique
						return redirect("private_group_reply")
				elif is_group_owner:
					# can hide submission, can only unhide if hidden by self
					if decision == 'h':
						# hide
						action_successful = hide_private_group_submission(group_id,submission_id,action_by='owner')
						if action_successful:
							####### construct and add to administrative activity #######
							construct_administrative_activity.delay(own_id, writer_id, time.time(), group_id, 'hide', submission_id)
							############################################################
						invalidate_cached_mehfil_replies(group_id)
						invalidate_presence(group_id)
						request.session["unique_id"] = unique
						return redirect("private_group_reply")
					else:
						# can only unhide if it was hidden by group_owner, otherwise has no right to do it
						action_successful = hide_private_group_submission(group_id,submission_id,unhide=True,action_by='owner')
						if action_successful:
							####### construct and add to administrative activity #######
							construct_administrative_activity.delay(own_id, writer_id, time.time(), group_id, 'unhide', submission_id)
							############################################################
							invalidate_cached_mehfil_replies(group_id)
							invalidate_presence(group_id)
							request.session["unique_id"] = unique
							return redirect("private_group_reply")
						else:
							return render(request,"mehfil/notify_and_redirect.html",{'cannot_hide_or_unhide':True,'unique':unique,\
								'reason':'hidden_by_op'})
				elif is_writer and is_member:
					# ensure is_writer and currently a group member (i.e. wasn't kicked out for instance)
					if decision == 'h':
						# hide
						action_successful = hide_private_group_submission(group_id,submission_id,action_by='writer')
						if action_successful:
							####### construct and add to administrative activity #######
							construct_administrative_activity.delay(own_id, writer_id, time.time(), group_id, 'hide', submission_id)
							############################################################
						invalidate_cached_mehfil_replies(group_id)
						invalidate_presence(group_id)
						request.session["unique_id"] = unique
						return redirect("private_group_reply")
					else:
						# unhide, if possible
						action_successful = hide_private_group_submission(group_id,submission_id,unhide=True,action_by='writer')
						if action_successful:
							####### construct and add to administrative activity #######
							construct_administrative_activity.delay(own_id, writer_id, time.time(), group_id, 'unhide', submission_id)
							############################################################
							invalidate_cached_mehfil_replies(group_id)
							invalidate_presence(group_id)
							request.session["unique_id"] = unique
							return redirect("private_group_reply")
						else:
							return render(request,"mehfil/notify_and_redirect.html",{'cannot_hide_or_unhide':True,'unique':unique,\
								'reason':'hidden_by_owner'})
				elif not is_writer and is_member:
					# do not have permission to do this
					return render(request,"mehfil/notify_and_redirect.html",{'cannot_hide_or_unhide':True,'unique':unique})
				else:
					# not allowed
					return redirect("group_page")
		else:
			# group doe snot exist
			return redirect("group_page")
	else:
		# not a POST request
		return redirect("private_group_reply")



@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def group_hide_submission(request, *args, **kwargs):
	"""
	Hide a submission in a public mehfil
	"""
	if request.method == 'POST':
		pk = request.POST.get("pk",None)# reply id
		gid = request.POST.get("gid",None)
		decision = request.POST.get("dec",None)# 'h' for hide, 'u' for unhide
		own_id = request.user.id
		if decision == 'h':#i.e. hide it
			context = {}
			data = retrieve_group_reqd_data(group_id=gid,with_group_owner_id=True,with_uuid=True)
			if data:
				owner_id = data['oi']
			else:
				# no group data found
				return redirect("group_page")
			submission_exists = group_submission_exists(gid,pk)
			if submission_exists and (is_group_officer(gid,own_id) or owner_id == str(own_id)):
				# hide the submission:
				writer_id = hide_group_submission(gid,pk)#hides group submission and returns writer ID by default
				if not is_group_officer(gid,writer_id) and owner_id != writer_id:
					# cut points only if the writer was NOT a group owner or a group officer
					UserProfile.objects.filter(user_id=writer_id).update(score=F('score')-POINTS_DEDUCTED_WHEN_GROUP_SUBMISSION_HIDDEN)
				invalidate_cached_mehfil_replies(gid)
				invalidate_presence(gid)
				####### construct and add to administrative activity #######
				construct_administrative_activity.delay(own_id, writer_id, time.time(), gid, 'hide', pk)
				############################################################
				url = reverse_lazy("public_group", args=[data['u']])+"#sectionJ"
				return redirect(url)
			elif not submission_exists:
				context["non_existence"] = True
				context["unique"] = data['u']
				return render(request,"mehfil/group_report.html",context)
			else:
				context["allowed"] = False
				context["unique"] = data['u']
				return render(request,"mehfil/group_report.html",context)
		elif decision == 'u':#i.e. unhide it
			context = {}
			data = retrieve_group_reqd_data(group_id=gid,with_group_owner_id=True,with_uuid=True)
			if data:
				owner_id = data['oi']
			else:
				# no group data found
				return redirect("group_page")
			own_id = request.user.id
			submission_exists = group_submission_exists(gid,pk)
			if submission_exists and (is_group_officer(gid,own_id) or owner_id == str(own_id)):
				# unhide the submission:
				writer_id = hide_group_submission(gid,pk,unhide=True)
				if not is_group_officer(gid,writer_id) and owner_id != writer_id:
					# return points only if the writer was NOT a group owneror a group officer
					UserProfile.objects.filter(user_id=writer_id).update(score=F('score')+POINTS_DEDUCTED_WHEN_GROUP_SUBMISSION_HIDDEN)
				invalidate_cached_mehfil_replies(gid)
				invalidate_presence(gid)
				####### construct and add to administrative activity #######
				construct_administrative_activity.delay(own_id, writer_id, time.time(), gid, 'unhide', pk)
				############################################################
				url = reverse_lazy("public_group", args=[data['u']])+"#sectionJ"
				return redirect(url)
			elif not submission_exists:
				context["cant_restore"] = True
				context["unique"] = data['u']
				return render(request,"mehfil/group_report.html",context)
			else:
				context["no_priv"] = True
				context["unique"] = data['u']
				return render(request,"mehfil/group_report.html",context)
		else:
			return redirect("group_page")
	else:
		# not a POST request
		return redirect("public_group")

############################## Mehfil online list ##############################

def display_group_users_list(request, grp_priv, list_type):
	"""
	Displays members or visitors of a mehfil

	Works for both public and private mehfils
	"""
	if grp_priv == 'private':
		# this is for a group with privacy = '1'
		group_uuid = request.session.get("unique_id",None)
		group_privacy = retrieve_group_privacy(group_uuid=group_uuid)
		if group_privacy == '0':
			# it's a public group - abort
			return redirect("group_page")
	elif grp_priv == 'public':
		# this is for a public group
		group_uuid = request.session.get("public_uuid",None)
		group_privacy = retrieve_group_privacy(group_uuid=group_uuid)
		if group_privacy == '1':
			# it's a private group - abort
			return redirect("group_page")
	else:
		# unrecognized parameter - abort
		raise Http404("The page you are looking for does not exist")
	#################################################
	own_id = request.user.id
	group_owner_id, group_id = retrieve_group_owner_id(group_uuid=group_uuid,with_group_id=True)
	if group_member_exists(group_id, own_id):
		# user can view this groups listing
		if list_type == 'visitors':
			# this is for displaying recent visitors
			attendance_data = retrieve_cached_attendance_data(group_id)
			if attendance_data:
				final_visitor_data = json.loads(attendance_data)
			else:
				attendance_data, final_visitor_data = get_attendance(group_id,time_ago='one_day_ago',withscores=True), []
				if attendance_data:
					all_online_ids = [visitor_id for (visitor_id,visit_time) in attendance_data]
					credentials = retrieve_bulk_credentials(all_online_ids, decode_unames=True)#dictionary of dictionaries is returned
					row_num = 1
					for visitor_id,visit_time in attendance_data:
						final_visitor_data.append((visitor_id,credentials[int(visitor_id)],visit_time,row_num))
						row_num += 1
					cache_group_attendance_data(json.dumps(final_visitor_data),group_id)
			if group_privacy == '0':
				which_tutorial = '15'
				template_name = 'public_group_online_kon'
			else:
				which_tutorial = '16'
				template_name = 'group_online_kon'
			############# paginating (if required) #############
			page_num = request.GET.get('page', '1')
			page = get_page_obj(page_num,final_visitor_data,GROUP_VISITORS_PER_PAGE)
			start_index, end_index = get_indices(page_num, GROUP_VISITORS_PER_PAGE)
			visitor_data = final_visitor_data[start_index:(end_index+1)]
			return render(request,"mehfil/{0}.html".format(template_name),{'object_list':visitor_data,'group_owner_id':group_owner_id,\
				'show_init_msg':tutorial_unseen(user_id=own_id, which_tut=which_tutorial, renew_lease=True),'unique':group_uuid, \
				'legit':FEMALES,'is_paginated': True if len(final_visitor_data) > GROUP_VISITORS_PER_PAGE else False, 'page_obj':page,\
				'is_owner':group_owner_id == str(own_id),'visitors':True})
		elif list_type == 'members':
			# this is for displaying all members
			membership_data = retrieve_cached_membership_data(group_id)
			if membership_data:
				final_member_data = json.loads(membership_data)
				num_members = len(final_member_data)
			else:
				all_member_ids_and_joining_times, num_members = retrieve_all_member_ids(group_id,with_num_members = True, with_times=True)
				all_member_ids = [member_id for (member_id,joining_time) in all_member_ids_and_joining_times]
				credentials, final_member_data = retrieve_bulk_credentials(all_member_ids, decode_unames=True), []#returned data {int(user_id):{'uname':uname,'avurl':avurl}}
				row_num = 1
				for member_id, joining_time in all_member_ids_and_joining_times:
					final_member_data.append((member_id, credentials[int(member_id)],joining_time,row_num))
					row_num += 1
				cache_group_membership_data(json.dumps(final_member_data),group_id)
			template_name = 'public_group_online_kon' if group_privacy == '0' else 'group_online_kon'
			############# paginating (if required) #############
			page_num = request.GET.get('page', '1')
			page = get_page_obj(page_num,final_member_data,GROUP_MEMBERS_PER_PAGE)
			start_index, end_index = get_indices(page_num, GROUP_MEMBERS_PER_PAGE)
			member_data = final_member_data[start_index:(end_index+1)]
			return render(request,"mehfil/{0}.html".format(template_name),{'object_list':member_data,'group_owner_id':group_owner_id,\
				'unique':group_uuid, 'legit':FEMALES,'is_paginated': True if num_members > GROUP_MEMBERS_PER_PAGE else False, \
				'page_obj':page,'members':True})
		else:
			# unrecognized parameter - abort
			return redirect("group_page")
	else:
		#unauthorized access attempt, group does not exist or user is not authorized
		return redirect("group_page")			

############################## Changing public and private mehfil topic ##############################


class ChangePrivateGroupTopicView(CreateView):
	"""
	Changes the topic of a private mehfil
	"""
	model = Group
	form_class = ChangePrivateGroupTopicForm
	template_name = "mehfil/change_private_group_topic.html"

	def get_initial(self):
		"""
		Returns the initial data to use for forms on this view.
		"""
		uuid = self.request.session.get("unique_id",None)
		if uuid:
			group_id = retrieve_group_id(uuid)
			return {'topic':retrieve_group_topic(group_id)}
		else:
			return {}

	def get_form_kwargs(self):
		kwargs = super(ChangePrivateGroupTopicView,self).get_form_kwargs()
		group_uuid = self.request.session.get("unique_id",None)
		kwargs['unique'] = group_uuid
		kwargs['user_id'] = self.request.user.id
		kwargs['group_id'] = retrieve_group_id(group_uuid)
		return kwargs

	def get_context_data(self, **kwargs):
		context = super(ChangePrivateGroupTopicView, self).get_context_data(**kwargs)
		user = self.request.user
		if user.is_authenticated():
			unique = self.request.session.get("unique_id",None)
			group_privacy = retrieve_group_privacy(group_uuid=unique,requestor_id=user.id)
			if group_privacy:
				context["unique"] = unique
				if group_privacy == '1':
					context["unauthorized"] = False
					context["topic_char_limit"] = PRIVATE_GROUP_MAX_TITLE_SIZE
					return context
				else:
					context["unauthorized"] = True
					return context
			else:
				# remove_group_invite(user.id, group_id) <------------- but we dont have group_id! what to do? we need to call this whenever '99' is encountered in any "retrieve" function in redis6! Alternative: pass user_id into ALL retrieve functions. Yuck!
				context["unauthorized"] = True
				return context
		else:
			context["unauthorized"] = True
			return context

	def form_valid(self, form):
		if self.request.user_banned:
			return redirect("error")
		else:
			topic = form.cleaned_data.get("topic")
			unique = self.request.session["unique_id"]
			group_owner_id, group_id, group_privacy = retrieve_group_owner_id(group_uuid=unique, with_group_id=True,with_group_privacy=True)
			if group_owner_id:
				if group_privacy == '1':
					user_id = self.request.user.id
					invalidate_cached_mehfil_replies(group_id)
					invalidate_presence(group_id)
					Group.objects.filter(unique=unique).update(topic=topic)
					# Reply.objects.create(text=topic ,which_group_id=group_id, writer_id=user_id, category='4')
					##########################
					##########################
					update_group_topic.delay(group_id=group_id, topic=topic)#redis 2 object's "topic" field is updated
					own_uname, own_avurl = retrieve_credentials(user_id,decode_uname=True)
					save_group_topic(group_id, topic, writer_id=user_id, time_now=time.time(), private=True)# redis 6 mehfil object is updated
					submission_id, num_submissions = save_group_submission(writer_id=user_id, group_id=group_id, text=topic,posting_time=time.time(),\
						category='4',writer_uname=own_uname, writer_avurl=get_s3_object(own_avurl,category='thumb'))# entry made in mehfil chat
					if num_submissions > DELETION_THRESHOLD:
						# delete extra submissions
						trim_group_submissions.delay(group_id)
					main_sentence = own_uname+" ne ye new topic rakha at {0}: {1}".format(exact_date(time.time()), topic)
					document_administrative_activity.delay(group_id, main_sentence, 'topic')
					invalidate_cached_mehfil_pages(user_id)
					##########################
					##########################
					self.request.session["unique_id"] = unique
					return redirect("private_group_reply")
				else:
					return redirect("group_page")
			else:
				# group does not exist
				return redirect("group_page")


class ChangeGroupTopicView(CreateView):
	"""
	Changes the topic of a public mehfil
	"""
	model = Group
	form_class = ChangeGroupTopicForm
	template_name = "mehfil/change_group_topic.html"

	def get_initial(self):
		"""
		Returns the initial data to use for forms on this view.
		"""
		uuid = self.request.session.get("public_uuid",None)
		if uuid:
			group_id = retrieve_group_id(uuid)
			return {'topic':retrieve_group_topic(group_id)}
		else:
			return {}

	def get_form_kwargs(self):
		kwargs = super(ChangeGroupTopicView,self).get_form_kwargs()
		group_uuid = self.request.session.get("public_uuid",None)
		kwargs['unique'] = group_uuid
		kwargs['user_id'] = self.request.user.id
		kwargs['group_id'] = retrieve_group_id(group_uuid)
		return kwargs

	def get_context_data(self, **kwargs):
		context = super(ChangeGroupTopicView, self).get_context_data(**kwargs)
		user = self.request.user
		if user.is_authenticated():
			unique = self.request.session.get("public_uuid",None)
			if unique:	
				context["unique"] = unique
				group_owner_id, group_id, group_privacy = retrieve_group_owner_id(group_uuid=unique, with_group_id=True,with_group_privacy=True)
				own_id = str(user.id)
				if group_privacy == '0':
					if group_owner_id == own_id or can_officer_change_topic(group_id, own_id):
						context["unauthorized"] = False
						context["topic_char_limit"] = PUBLIC_GROUP_MAX_TITLE_SIZE
					else:
						context["unauthorized"] = True
					return context
				else:
					context["unauthorized"] = True
					return context
			else:
				context["unauthorized"] = True
				return context
		else:
			context["unauthorized"] = True
			return context


	def form_valid(self, form): #this processes the form before it gets saved to the database
		user_id = self.request.user.id
		if self.request.user_banned:
			return redirect("error")
		else:
			topic = form.cleaned_data.get("topic")
			unique = self.request.session.get("public_uuid",None)
			group_owner_id, group_id, group_privacy = retrieve_group_owner_id(group_uuid=unique, with_group_id=True,with_group_privacy=True)
			if group_owner_id:
				if group_privacy == '0' and (group_owner_id == str(user_id) or can_officer_change_topic(group_id, user_id)):
					Group.objects.filter(unique=unique).update(topic=topic)
					invalidate_cached_mehfil_replies(group_id)
					invalidate_presence(group_id)
					# Reply.objects.create(text=topic, which_group_id=group_id, writer_id=user_id, category='4')
					#############
					own_uname, own_avurl = retrieve_credentials(user_id,decode_uname=True)
					update_group_topic.delay(group_id=group_id, topic=topic)#redis 2
					save_group_topic(group_id, topic)#redis 6
					save_group_submission(writer_id=user_id, group_id=group_id, text=topic,posting_time=time.time(),category='4',\
						writer_uname=own_uname, writer_avurl=get_s3_object(own_avurl,category='thumb'))
					main_sentence = own_uname+" ne ye new topic rakha at {0}: {1}".format(exact_date(time.time()), topic)
					document_administrative_activity.delay(group_id, main_sentence, 'topic')
					invalidate_cached_mehfil_pages(user_id)
					invalidate_cached_ranked_groups()
					#############
					return redirect("public_group", slug=unique)
				else:
					return redirect("group_page")
			else:
				# group does not exist
				return redirect("group_page")

############################## Changing public mehfil rules ##############################

def example_group_rules(request):
	"""
	Shows a quick help page with some example rules
	"""
	return render(request,"mehfil/example_group_rules.html",{'uuid':request.session.get("public_uuid",None)})


class ChangeGroupRulesView(CreateView):
	"""
	Renders public mehfil change rules form and processes new POST requests
	"""
	model = Group
	form_class = ChangeGroupRulesForm
	template_name = "mehfil/change_group_rules.html"

	def get_initial(self):
		"""
		Returns the initial data to use for forms on this view.
		"""
		uuid = self.request.session.get("public_uuid",None)
		if uuid:
			group_id = retrieve_group_id(uuid)
			return {'rules':retrieve_group_rules(group_id,raw=True)}
		else:
			return {}	

	def get_form_kwargs( self ):
		kwargs = super(ChangeGroupRulesView,self).get_form_kwargs()
		group_uuid = self.request.session.get("public_uuid",None)
		kwargs['user_id'] = self.request.user.id
		kwargs['unique_id'] = group_uuid
		kwargs['group_id'] = retrieve_group_id(group_uuid)
		return kwargs

	def get_context_data(self, **kwargs):
		context = super(ChangeGroupRulesView, self).get_context_data(**kwargs)
		context["unauthorized"] = True
		if self.request.user.is_authenticated():
			user_id = self.request.user.id
			unique = self.request.session.get("public_uuid",None)
			context["unique"] = unique
			group_owner_id, group_privacy = retrieve_group_owner_id(group_uuid=unique, with_group_privacy=True)
			context["group_privacy"] = group_privacy
			if group_privacy == '0':
				if group_owner_id == str(user_id):
					context["unauthorized"] = False
					context["rules_char_limit"] = PUBLIC_GROUP_MAX_RULES_SIZE
				else:
					context["unauthorized"] = True
		return context

	def form_valid(self, form): #this processes the form before it gets saved to the database
		user_id = str(self.request.user.id)
		if self.request.user_banned:
			return redirect("profile", slug=user.username)
		else:
			rules, raw_rules = form.cleaned_data.get("rules")
			unique = self.request.session.get("public_uuid",None)
			group_owner_id, group_id, group_privacy = retrieve_group_owner_id(group_uuid=unique, with_group_id=True,with_group_privacy=True)
			if group_owner_id:
				if group_privacy == '0' and group_owner_id == user_id:
					Group.objects.filter(unique=unique).update(rules=rules)
					invalidate_cached_mehfil_replies(group_id)
					invalidate_presence(group_id)
					# Reply.objects.create(text=rules ,which_group_id=group_id ,writer_id=user_id ,category='5')
					#############
					save_group_rules(group_id, rules, raw_rules)
					own_uname, own_avurl = retrieve_credentials(user_id,decode_uname=True)
					save_group_submission(writer_id=user_id, group_id=group_id, text=rules,posting_time=time.time(),category='5',\
						writer_uname=own_uname, writer_avurl=get_s3_object(own_avurl,category='thumb'))
					#############
					return render(self.request,"mehfil/force_members_to_accept_rules.html",{'gid':group_id})
				else:
					return redirect("group_page")
			else:
				# this group does not exist
				return redirect("group_page")


############################## Deleting or exiting public and private mehfils ##############################


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def leave_private_group(request, *args, **kwargs):
	"""
	Renders the leaving page of private mehfil

	Called from group_page (inside the group, all 'exit' calls are routed through the dashboard function)
	"""
	if request.method == "POST":
		pk = request.POST.get("gid",None)
		unique = request.POST.get("guuid",None)
		inside_grp = request.POST.get('insg',None)
		group_owner_id = retrieve_group_owner_id(group_id=pk)
		user_id = request.user.id
		if group_owner_id:
			if str(user_id) == group_owner_id:
				context={'unique':unique, 'pk':pk, 'topic':retrieve_group_topic(group_id=pk, requestor_id=user_id), 'inside_grp':inside_grp}
				return render(request,'mehfil/delete_private_group.html',context)
			else:
				context={'unique':unique, 'pk':pk, 'topic':retrieve_group_topic(group_id=pk, requestor_id=user_id), 'inside_grp':inside_grp}
				return render(request, 'mehfil/leave_private_group.html', context)
		else:
			# group does not exist
			remove_group_invite(user_id, pk)# in case redis 1 invite exists, delete it (DEPRECATE REDIS 1 LATER)
			return redirect("group_page")
	else:
		# not a POST request
		return redirect("private_group_reply")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def leave_public_group(request):
	"""
	Displays public group abandonment options

	Called from group_page (inside the group, all 'exit' calls are routed through the dashboard function)
	"""
	if request.method == "POST":
		pk = request.POST.get("gid",None)
		unique = request.POST.get("guuid",None)
		inside_grp = request.POST.get('insg',None)
		group_owner_id = retrieve_group_owner_id(group_id=pk)
		own_id = request.user.id
		if group_owner_id:
			if group_owner_id == str(own_id):
				return render(request, 'mehfil/delete_public_group.html', {'unique':unique, 'pk':pk, 'inside_grp':inside_grp,\
					'topic':retrieve_group_topic(group_id=pk,requestor_id=own_id)})
			else:
				return render(request, 'mehfil/leave_public_group.html', {'unique':unique, 'pk':pk, 'inside_grp':inside_grp,\
					'topic':retrieve_group_topic(group_id=pk,requestor_id=own_id)})
		else:
			# group does not exist
			remove_group_invite(own_id, pk)# in case redis 1 invite exists, delete it (DEPRECATE REDIS 1 LATER)
			return redirect("group_page")
	else:
		# not a POST request
		return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def del_public_group(request, pk=None, unique=None, *args, **kwargs):
	"""
	Processes public mehfil deletion
	"""
	if request.method == "POST":
		deletion_decision = request.POST.get("ddec",None)
		if deletion_decision == '2':
			group_owner_id, group_id = retrieve_group_owner_id(group_uuid=unique,with_group_id=True)
			# REPLACE get_group_members() WITH SIMILAR FUNCTION FROM REDIS 6
			member_ids = list(User.objects.filter(username__in=get_group_members(pk)).values_list('id',flat=True))
			own_id = str(request.user.id)
			if group_owner_id:
				if group_owner_id == own_id and group_id == str(pk):
					if is_deletion_frozen(group_id):
						# mehfil reported - thus deletion is frozen for now
						return render(request,"mehfil/notify_and_redirect.html",{'action_frozen':True,'unique':unique,'is_public':True})
					else:
						# removing group related notifications seen by owner of group (redis 2):
						remove_group_notification(user_id=own_id,group_id=group_id)
						# removing group notification parent object (redis 2)
						remove_group_object(group_id)

						# removing from popular group list that contains top 20 ranked groups (redis 3)
						del_from_rankings(group_id)

						# removing the group member set (redis 1)
						remove_all_group_members(group_id)
						# removing group's separately saved 'latest' reply (redis 1)
						remove_latest_group_reply(group_id)
						# purging group for all members (redis 1)
						bulk_remove_user_group(member_ids, group_id, return_member_ids=False)
						
						# marking postgresql group data (deprecate this later)
						Group.objects.filter(id=group_id).update(category='99')#'99' implies deleted

						# # removing postgresql group data (canceling plans to do this since it cascades over ALL replies in the group and can lock up the table)
						# replies = Reply.objects.filter(which_group_id=group_id).order_by('-id').values_list('id',flat=True)[:1000]
						# if replies.exists():
						# 	# very ambitious to delete ALL replies - just deleting the latest 1000 replies for now
						# 	Reply.objects.filter(id__in=replies).delete()
						# banned_users = GroupBanList.objects.filter(which_group_id=group_id)
						# if banned_users.exists():
						# 	banned_users.delete()
						# Group.objects.get(id=group_id).delete()

						# purging redis 6 group related data structures:
						permanently_delete_group(group_id, group_type='public')# get rid of all redis 6 data related to the group
						
						return render(request,'mehfil/notify_and_redirect.html', {'deleted':True,'is_public':True})
				elif group_id != str(pk):
					# maybe the input was tinkered with?
					return render(request,'mehfil/notify_and_redirect.html', {'wrong_input_by_owner':True,'is_public':True,'unique':unique})
				else:
					# not group owner
					return redirect("group_page")
			else:
				# group does not exist
				return redirect("group_page")
		elif deletion_decision == '1':
			# deletion called from group page
			return redirect("group_page")
		elif deletion_decision == '0':
			# deletion called from inside public group
			return redirect("public_group", slug=unique)
		else:
			return redirect("group_page")
	else:
		# not a POST request
		return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def del_private_group(request, pk=None, unique=None, *args, **kwargs):
	"""
	Processes private mehfil deletion
	"""
	if request.method == "POST":
		deletion_decision = request.POST.get("ddec",None)
		if deletion_decision == '2':
			group_owner_id, group_id = retrieve_group_owner_id(group_uuid=unique,with_group_id=True)
			own_id = request.user.id
			if group_owner_id == str(own_id) and group_id == str(pk):
				if is_deletion_frozen(group_id):
					# mehfil reported - thus deletion is frozen for now
					return render(request,"mehfil/notify_and_redirect.html",{'action_frozen':True,'unique':unique,'is_public':False})
				else:
					# removing group related notifications seen by owner of group (redis 2):
					remove_group_notification(user_id=own_id,group_id=group_id)
					# removing group notification parent object (redis 2)
					remove_group_object(group_id)

					# removing the group member set (redis 1)
					remove_all_group_members(group_id)
					# removing group's separately saved 'latest' reply (redis 1)
					remove_latest_group_reply(group_id)
					# purging group for all members (redis 1)
					member_ids = list(User.objects.filter(username__in=get_group_members(group_id)).values_list('id',flat=True))
					bulk_remove_user_group(member_ids, group_id, return_member_ids=False)
					
					# marking postgresql group data (deprecate this later)
					Group.objects.filter(id=group_id).update(category='99')#'99' implies deleted

					# # removing postgresql group data (didn't do it since it cascades over ALL replies - that could lock table for a long time)
					# replies = Reply.objects.filter(which_group_id=group_id).order_by('-id').values_list('id',flat=True)[:1000]
					# if replies.exists():
					# 	# very ambitious to delete ALL replies - just deleting the latest 1000 replies for now
					# 	Reply.objects.filter(id__in=replies).delete()
					# Group.objects.get(id=group_id).delete()

					# purging redis 6 group related data structures:
					permanently_delete_group(group_id, group_type='private')# get rid of all redis 6 data related to the group

					return render(request,'mehfil/notify_and_redirect.html', {'deleted':True,'is_public':False})
			elif group_id != str(pk):
				# maybe the input was tinkered with?
				return render(request,'mehfil/notify_and_redirect.html', {'wrong_input_by_owner':True,'is_public':False,'unique':unique})
			else:
				# not group owner
				return redirect("group_page")
		elif deletion_decision == '1':
			# deletion called from group page
			return redirect("group_page")
		elif deletion_decision == '0':
			# deletion called from inside private group
			request.session["unique_id"] = unique
			return redirect("private_group_reply")
		else:
			return redirect("group_page")
	else:
		# not a POST request
		return redirect("private_group_reply")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def left_public_group(request, *args, **kwargs):
	"""
	Processes leaving a public mehfil
	"""
	if request.method == "POST":
		pk = request.POST.get("pk",None)
		inside_group = request.POST.get("igrp",None)
		unique = request.POST.get("slug",None)
		leaving_decision = request.POST.get("ldec",None)
		if leaving_decision == '1':
			user_id = request.user.id
			own_uname = retrieve_uname(user_id,decode=True)
			time_now = time.time()
			#replace below 'if' condition with group_member_exists(group_id, user_id) - from redis 6
			if check_group_member(pk, own_uname):
				ttl = can_leave_group(pk, user_id)#stops from joining and then immediately leaving
				if ttl:
					return render(request,"mehfil/notify_and_redirect.html",{'cannot_exit':True,'time_remaining':ttl,'is_public':True,'unique':unique})
				else:
					legacy_mehfil_exit(pk, user_id, own_uname, group_type='public')# legacy redis 1 - please remove
					############################ Redis 6 ###############################
					exit_group(pk, user_id, time_now, is_public=True)# redis 6 function - remove redis 1 funcs in the future
					invalidate_cached_mehfil_pages(user_id)
					####################################################################

			elif check_group_invite(user_id, pk):
				
				remove_group_invite(user_id, pk)# group invite removed from user invites pir:user_id (redis 1)
				
				############################ Redis 6 ###############################
				# purge_group_membership(group_id=pk, member_id=user_id, is_public=True, time_now=time_now)# redis 6 function - remove all others in the future
				purge_group_invitation(group_id=pk, member_id=user_id, is_public=True)# redis 6 function - remove all others in the future
				remove_group_officer(group_id=pk,target_user_id=user_id)# redis 6 function - remove all others in the future
				invalidate_cached_mehfil_pages(user_id)
				####################################################################

			else:
				pass
			return redirect("group_page")
		else:
			if inside_group == '1':
				return redirect("public_group", slug=unique)
			else:
				return redirect("group_page")
	return redirect("group_page")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def left_private_group(request, *args, **kwargs):
	"""
	Processes leaving a private mehfil
	"""
	if request.method=="POST":
		user_id = request.user.id
		pk = request.POST.get("gid",None)
		unique = request.POST.get("guid",None)
		own_uname, own_avurl = retrieve_credentials(user_id,decode_uname=True)
		time_now = time.time()
		if check_group_member(pk, own_uname):
			#replace this if condition with group_member_exists(group_id, user_id) from redis 6
			ttl = can_leave_group(pk, user_id)#stops user from repeating entering/exiting a group
			if ttl:
				return render(request,"mehfil/notify_and_redirect.html",{'cannot_exit':True,'time_remaining':ttl, 'is_public':False,'unique':unique})
			else:
				legacy_mehfil_exit(pk, user_id, own_uname, group_type='private')# legacy redis 1 - please remove
				############################ Redis 6 ###############################
				exit_group(pk, user_id, time_now, own_uname, get_s3_object(own_avurl,category='thumb'), is_public=False)
				invalidate_cached_mehfil_pages(user_id)
				####################################################################

		elif check_group_invite(user_id, pk):#sorted set containing user invites ipg:user_id: (redis 1)
			#replace this if condition with group_invite_exists(group_id, user_id) from redis 6
			remove_group_invite(user_id, pk)# group invite removed from user invites pir:user_id (redis 1)
			############################ Redis 6 ###############################
			save_group_submission(writer_id=user_id, group_id=pk, text='unaccepted invite',posting_time=time.time(),\
				category='7', writer_uname=own_uname, writer_avurl=get_s3_object(own_avurl,category='thumb'))
			purge_group_invitation(group_id=pk, member_id=user_id)# redis 6 function - remove redis 1 funcs in the future
			invalidate_cached_mehfil_pages(user_id)# redis6 function
			invalidate_cached_mehfil_replies(pk)#redis6 function
			invalidate_presence(pk)
			####################################################################
		else:
			pass
	return redirect("group_page")


############################## Rendering and posting to private mehfil ##############################

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@sensitive_post_parameters()
@csrf_protect
def priv_group(request,*args,**kwargs):
	"""
	Redirecting incoming to PrivateGroupView()
	"""
	if request.method == 'POST':
		slug = request.POST.get("private_uuid")
		if valid_uuid(slug):
			request.session["unique_id"] = slug
			return redirect("private_group_reply")
		else:
			return redirect("group_page")	
	else:
		return redirect("group_page")


def private_group_request_denied(request):
	"""
	Renders errors resulting from posting in a private mehfil
	"""
	which_msg = request.session.pop("private_group_request_denied",None)
	if which_msg == '1':
		return render(request,'big_photo_fbs.html',{'pk':'pk'})
	elif which_msg == '2':
		return render(request,'big_photo_regular.html',{'origin':'prv_grp'})
	elif which_msg == '3':
		uuid = request.session.pop("private_group_upload_uuid",None)
		return render(request, 'mehfil/notify_and_redirect.html',{'is_prv_grp':True,'img_too_big':True,'unique':uuid})
	else:
		return redirect("missing_page")


class PrivateGroupView(CreateView):
	"""
	Renders and processes submissions to private mehfil
	"""
	model = Reply
	form_class = PrivateGroupReplyForm		
	template_name = "mehfil/private_group_reply.html"

	# @cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
	# def dispatch(self, request, *args, **kwargs):
	# 	# Try to dispatch to the right method; if a method doesn't exist,
	# 	# defer to the error handler. Also defer to the error handler if the
	# 	# request method isn't on the approved list.
	# 	if request.method.lower() in self.http_method_names:
	# 		handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
	# 	else:
	# 		handler = self.http_method_not_allowed
	# 	self.request = request
	# 	self.args = args
	# 	self.kwargs = kwargs
	# 	return handler(request, *args, **kwargs)

	def get_form_kwargs( self ):
		kwargs = super(PrivateGroupView,self).get_form_kwargs()
		kwargs['is_mob_verified'] = self.request.mobile_verified
		kwargs['user_id'] = self.request.user.id
		return kwargs

	def get_context_data(self, **kwargs):
		context = super(PrivateGroupView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			user_id = self.request.user.id
			unique = self.request.session.get('unique_id',None)
			data = retrieve_group_reqd_data(group_uuid=unique,requestor_id=user_id)#group privacy, group_id, group_topic, group_owner_id (optional), 'pics'(optional)
			if data:
				context["unique"] = unique
			else:
				raise Http404("Mehfil does not exist")
			if data['p'] =='1':
				context["switching"] = False
				group_id = data['gi']
				context["own_id"] = user_id
				if group_member_exists(group_id, user_id):
					# is a full member
					context["furl"] = reverse_lazy("private_group_reply")
					context["full_member"] = True
					context["group_topic"] = data['tp']
					context["group_id"] = group_id
					context["display"] = 'inline' if retrieve_user_env(user_agent=self.request.META.get('HTTP_USER_AGENT',None), \
						fbs=self.request.META.get('HTTP_X_IORG_FBS',False)) else 'none'
					secret_key = uuid.uuid4()
					context["sk"] = secret_key
					set_text_input_key(user_id, group_id, 'prv_grp', secret_key)
					on_fbs = self.request.META.get('HTTP_X_IORG_FBS',False)
					context["ensured"] = FEMALES
					prev_form = self.request.session.pop("private_group_form",None)
					context["form"] = prev_form if prev_form else PrivateGroupReplyForm()
					latest_replies = retrieve_cached_mehfil_replies(group_id)
					if latest_replies:
						# getting from cache
						latest_replies = json.loads(latest_replies)
					else:
						# reconstructing replies and caching them
						latest_data = retrieve_group_submissions(group_id)
						latest_replies = []
						for data in latest_data:
							latest_replies.append({'category':data['c'],'submitted_on':data['t'],'text':data['tx'],'wid':data['wi'],'writer_uname':data['wu'],\
								'image':data.get('iu',None),'writer_avurl':data.get('wa',None),'writer_score':data.get('ws',None),'id':data['si'],\
								'tu':data.get('tu',None)})
						cache_mehfil_replies(json.dumps(latest_replies),group_id)
					log_private_mehfil_session.delay(group_id, user_id)
					updated_at = time.time()#convert_to_epoch(timezone.now())
					group_attendance_tasks.delay(group_id=group_id, user_id=user_id, time_now=updated_at)#, private=True)# fills group visitors
					presence_dict = get_latest_presence(group_id,set(reply["wid"] for reply in latest_replies),updated_at)
					presence_dict[str(user_id)] = 'green'#ensures own status is 'green'
					context["replies"] = [(reply,presence_dict.get(reply["wid"],'gone')) for reply in latest_replies]
					context["unseen"] = False
					if not self.request.user_banned:#do the following ONLY if user isn't hell-banned
						# members = get_group_members(group_id)# redis 1 legacy function
						if latest_replies:# and self.request.user.username in members:
							# flip "unseen" notification here
							context["unseen"] = True #i.e. replies exist; the prospect of unseen replies exists
							update_notification(viewer_id=user_id, object_id=group_id, object_type='3', seen=True, updated_at=updated_at, \
								single_notif=False, unseen_activity=True, priority='priv_mehfil',bump_ua=False) #just seeing means notification is updated, but not bumped up in matka (bump_ua handles bumping up in matka)
							try:
								#finding latest time user herself replied - helps showing (new) inside mehfil
								context["reply_time"] = max(reply["submitted_on"] for reply in latest_replies if str(reply["wid"]) == str(user_id))
							except ValueError:
								context["reply_time"] = None #i.e. it's the first reply in the last 35 replies (i.e. all were unseen)
						else:
							context["reply_time"] = None
				else:
					# give membership option
					context["full_member"] = False
					context["group_topic"] = data['tp']
					context["group_id"] = group_id
					context["score"] = self.request.user.userprofile.score
			else:
				context["switching"] = True
		return context

	
	def form_invalid(self, form):
		"""
		If the form is invalid, re-render the context data with the
		data-filled form and errors.
		"""
		self.request.session["private_group_form"] = form
		self.request.session.modified = True
		if self.request.is_ajax():
			return HttpResponse(json.dumps({'success':False,'message':reverse('private_group_reply')}),content_type='application/json',)
		else:
			return self.render_to_response(self.get_context_data(form=form))

	
	def form_valid(self, form): #this processes the form before it gets saved to the database
		is_ajax = self.request.is_ajax()
		if self.request.user_banned:
			if is_ajax:
				return HttpResponse(json.dumps({'success':False,'message':reverse('error')}),content_type='application/json',)
			else:
				return redirect("error")
		else:
			user_id = self.request.user.id
			group_id = self.request.POST.get('gp',None)
			data = retrieve_group_reqd_data(group_id=group_id, with_group_owner_id=True, with_uuid=True)#group privacy, group_id, group_topic, group_owner_id (optional), 'pics'(optional), uuid(option)
			if data:
				if not group_member_exists(group_id, user_id):
					# not a group member
					if is_ajax:
						return HttpResponse(json.dumps({'success':False,'message':reverse('private_group_reply')}),content_type='application/json',)
					else:
						return redirect("private_group_reply")
				else:
					f = form.save(commit=False) #getting form object, and telling database not to save (commit) it just yet
					invalidate_cached_mehfil_replies(group_id)
					invalidate_presence(group_id)
					text = f.text #text of the reply
					if f.image:
						on_fbs = self.request.META.get('HTTP_X_IORG_FBS',False)
						if on_fbs:
							if f.image.size > 200000:
								self.request.session["private_group_request_denied"] = '1'
								self.request.session.modified = True
								if is_ajax:
									return HttpResponse(json.dumps({'success':False,'message':reverse('private_group_request_denied')}),content_type='application/json',)
								else:
									return redirect("private_group_request_denied")
						else:
							if f.image.size > 10000000:
								self.request.session["private_group_request_denied"] = '2'
								self.request.session.modified = True
								if is_ajax:
									return HttpResponse(json.dumps({'success':False,'message':reverse('private_group_request_denied')}),content_type='application/json',)
								else:
									return redirect("private_group_request_denied")
						image_file, img_width, img_height = process_group_image(image=f.image,quality=None if on_fbs else True,\
							already_reoriented=self.request.POST.get('reoriented',None),already_resized=self.request.POST.get('resized',None))
						if img_height == 'too_high':
							self.request.session["private_group_request_denied"] = '3'
							self.request.session["private_group_upload_uuid"] = data['u']
							self.request.session.modified = True
							if is_ajax:
								return HttpResponse(json.dumps({'success':False,'message':reverse('private_group_request_denied')}),content_type='application/json',)
							else:
								return redirect('private_group_request_denied')
						else:
							uploaded_img_loc = upload_image_to_s3(image_file,prefix='mehfils/')
					else: 
						uploaded_img_loc = None
					UserProfile.objects.filter(user_id=user_id).update(score=F('score')+PRIVATE_GROUP_MESSAGE)
					time_now = time.time()
					set_input_rate_and_history.delay(section='prv_grp',section_id=group_id,text=text,user_id=user_id,time_now=time_now)
					reply = Reply.objects.create(writer_id=user_id, which_group_id=group_id, text=text, image='')
					###########################################
					###########################################
					writer_id = str(form.cleaned_data.get('wid','-1'))# the target_id of the writer we're about to directly respond to
					if writer_id not in ('-1','None',str(user_id)) and group_member_exists(group_id, writer_id):	
						# if the writer is not self, and is indeed a member of this group
						raw_user_cred = retrieve_bulk_credentials([user_id,writer_id],decode_unames=True)
						own_uname, own_avurl = raw_user_cred[user_id]['uname'], raw_user_cred[user_id]['avurl']
						other_uname, other_avurl = raw_user_cred[int(writer_id)]['uname'], raw_user_cred[int(writer_id)]['avurl']
						submission_id, num_submissions = save_group_submission(writer_id=user_id, group_id=group_id, text=text, \
							image=uploaded_img_loc, posting_time=time_now,writer_avurl=get_s3_object(own_avurl,category='thumb'),\
							writer_score=self.request.user.userprofile.score,category='0',writer_uname=own_uname,target_uname=other_uname, \
							target_uid=writer_id, save_latest_submission=True)
						notify_single_user = True
						notif_text = "@ "+other_uname+" - "+text
					else:
						own_uname, own_avurl = retrieve_credentials(user_id,decode_uname=True)
						submission_id, num_submissions = save_group_submission(writer_id=user_id, group_id=group_id, text=text, image=uploaded_img_loc, \
							posting_time=time_now,writer_avurl=get_s3_object(own_avurl,category='thumb'),writer_score=self.request.user.userprofile.score,\
							category='0',writer_uname=own_uname,save_latest_submission=True)
						notify_single_user = False
						notif_text = text
					if num_submissions > DELETION_THRESHOLD:
						# delete extra submissions
						trim_group_submissions.delay(group_id)
					###########################################
					###########################################
					unique_id = data['u']
					group_notification_tasks.delay(group_id=group_id,sender_id=user_id,group_owner_id=data['oi'], topic=data['tp'], \
						reply_time=time_now, poster_url=own_avurl, poster_username=own_uname, reply_text=notif_text, priv='1', \
						slug=unique_id,image_url=uploaded_img_loc,priority='priv_mehfil',from_unseen=False,reply_id=reply.id,\
						notify_single_user=notify_single_user, single_target_id=writer_id)
					if is_ajax:
						return HttpResponse(json.dumps({'success':True,'message':reverse('private_group_reply')}),content_type='application/json',)
					else:
						self.request.session['unique_id'] = unique_id
						url = reverse_lazy("private_group_reply")+"#sectionJ"
						return redirect(url)
			else:
				# group does not exist - perhaps was deleted
				if is_ajax:
					return HttpResponse(json.dumps({'success':False,'message':reverse('group_page')}),content_type='application/json',)
				else:
					return redirect("group_page")


############################## Rendering and posting to public mehfil ##############################

@ratelimit(rate='3/s')
def public_group(request, slug=None, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if not slug:
		slug = request.session.get("public_uuid",None)
	else:
		request.session["public_uuid"] = slug
		request.session.modified = True
	if valid_uuid(slug):
		if was_limited:
			return redirect("missing_page")
		else:
			return redirect("public_group_reply")
	else:
		return redirect("group_page")


def public_group_request_denied(request):
	"""
	Renders errors resulting from posting in a public mehfil
	"""
	which_msg = request.session.pop("public_group_request_denied",None)
	if which_msg == '1':
		return render(request,'big_photo_fbs.html',{'pk':'pk'})
	elif which_msg == '2':
		return render(request,'big_photo_regular.html',{'origin':'pub_grp'})
	elif which_msg == '3':
		uuid = request.session.pop("public_group_upload_uuid",None)
		return render(request, 'mehfil/notify_and_redirect.html',{'is_pub_grp':True,'img_too_big':True,'unique':uuid})
	else:
		return redirect("missing_page")



class PublicGroupView(CreateView):
	model = Reply
	form_class = PublicGroupReplyForm
	template_name = "mehfil/public_group_reply.html"

	# @cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
	# def dispatch(self, request, *args, **kwargs):
	# 	# Try to dispatch to the right method; if a method doesn't exist,
	# 	# defer to the error handler. Also defer to the error handler if the
	# 	# request method isn't on the approved list.
	# 	if request.method.lower() in self.http_method_names:
	# 		handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
	# 	else:
	# 		handler = self.http_method_not_allowed
	# 	self.request = request
	# 	self.args = args
	# 	self.kwargs = kwargs
	# 	return handler(request, *args, **kwargs)

	def get_form_kwargs(self):
		kwargs = super(PublicGroupView,self).get_form_kwargs()
		kwargs['user_id'] = self.request.user.id
		kwargs['is_mob_verified'] = self.request.mobile_verified
		return kwargs

	def get_context_data(self, **kwargs):
		context = super(PublicGroupView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			user_id = self.request.user.id
			unique = self.request.session.get("public_uuid",None)
			#####################
			group_data = retrieve_group_reqd_data(group_uuid=unique, with_group_owner_id=True, with_pics_perm=True,requestor_id=user_id)
			#####################
			if group_data:
				group_id = group_data['gi']
				context["unique"] = unique
				context["group_id"] = group_id
			else:
				raise Http404("Mehfil does not exist")
			if group_data['p'] == '0':
				context["own_id"] = user_id
				context["ensured"] = FEMALES
				context["csrf"] = csrf.get_token(self.request)
				context["score"] = self.request.user.userprofile.score
				context["group_topic"] = group_data['tp']
				context["group_owner_uname"] = retrieve_uname(group_data['oi'],decode=True)
				updated_at = time.time()
				credentials = is_group_member_and_rules_signatory(group_id, user_id)
				is_member, is_signatory = credentials[0], credentials[1]# data contains exact time stamp when user became member and signatory
				if is_member and is_signatory:
					context["pics_perms"] = group_data['pics']
					context["furl"] = reverse_lazy("public_group", args=[unique])
					context["full_member"] = True
					context["member_since"] = is_member
					context["display"] = 'inline' if retrieve_user_env(user_agent=self.request.META.get('HTTP_USER_AGENT',None), \
						fbs=self.request.META.get('HTTP_X_IORG_FBS',False)) else 'none'
					secret_key = uuid.uuid4()
					context["sk"] = secret_key
					set_text_input_key(user_id, group_id, 'pub_grp', secret_key)
					prev_form = self.request.session.pop("public_group_form",None)
					context["form"] = prev_form if prev_form else PublicGroupReplyForm()
					context["switching"] = False
					group_attendance_tasks.delay(group_id=group_id, user_id=user_id, time_now=updated_at)
					latest_replies = retrieve_cached_mehfil_replies(group_id)
					if latest_replies:
						latest_replies = json.loads(latest_replies)
					else:
						latest_data = retrieve_group_submissions(group_id)
						latest_replies = []
						for data in latest_data:
							latest_replies.append({'category':data['c'],'submitted_on':data['t'],'text':data['tx'],'wid':data['wi'],'writer_uname':data['wu'],\
								'image':data.get('iu',None),'writer_avurl':data.get('wa',None),'writer_score':data.get('ws',None),'id':data['si'],\
								'gid':data['gi'],'tu':data.get('tu',None)})
						cache_mehfil_replies(json.dumps(latest_replies),group_id)
					presence_dict = get_latest_presence(group_id,set(reply["wid"] for reply in latest_replies),updated_at)
					presence_dict[str(user_id)] = 'green'#ensures own status is 'green'
					context["replies"] = [(reply,presence_dict.get(reply["wid"],'gone')) for reply in latest_replies]
					context["unseen"] = False
					context["on_fbs"] = self.request.META.get('HTTP_X_IORG_FBS',False)
					if not self.request.user_banned:#do the following ONLY if user isn't hell-banned
						members = get_group_members(group_id)
						if self.request.user.username in members and context["replies"]:
							update_notification(viewer_id=user_id, object_id=group_id, object_type='3', seen=True, updated_at=updated_at, \
								single_notif=False, unseen_activity=True, priority='public_mehfil', bump_ua=False) #just seeing means notification is updated, but not bumped up in ua:
				else:
					if is_member:
						context["partial_member"] = True
						context["rules"] = retrieve_group_rules(group_id)
					if retrieve_group_category(group_id) == '2':
						context["only_pinkstars"] = True
					############################################################
					latest_replies = retrieve_cached_mehfil_replies(group_id)
					if latest_replies:
						latest_replies = json.loads(latest_replies)
					else:
						latest_data = retrieve_group_submissions(group_id)
						latest_replies = []
						for data in latest_data:
							latest_replies.append({'category':data['c'],'submitted_on':data['t'],'text':data['tx'],'wid':data['wi'],'writer_uname':data['wu'],\
								'image':data.get('iu',None),'writer_avurl':data.get('wa',None),'writer_score':data.get('ws',None),'id':data['si'],\
								'gid':data['gi']})
						cache_mehfil_replies(json.dumps(latest_replies),group_id)
					presence_dict = get_latest_presence(group_id,set(reply["wid"] for reply in latest_replies),updated_at)
					presence_dict[str(user_id)] = 'green'#ensures own status is 'green'
					context["replies"] = [(reply,presence_dict.get(reply["wid"],'gone')) for reply in latest_replies]
			else:
				context["switching"] = True
		return context

	def form_invalid(self, form):
		"""
		If the form is invalid, re-render the context data with the
		data-filled form and errors.
		"""
		self.request.session["public_group_form"] = form
		self.request.session.modified = True
		if self.request.is_ajax():
			return HttpResponse(json.dumps({'success':False,'message':reverse('public_group')}),content_type='application/json',)
		else:
			return self.render_to_response(self.get_context_data(form=form))

	def form_valid(self, form): #this processes the public form before it gets saved to the database
		"""
		If the form is valid, redirect to the supplied URL.
		"""
		is_ajax = self.request.is_ajax()
		if self.request.user_banned:
			if is_ajax:
				return HttpResponse(json.dumps({'success':False,'message':reverse('error')}),content_type='application/json',)
			else:
				return redirect("error")
		user_id = self.request.user.id
		group_id = self.request.POST.get('gp',None)
		public_uuid = self.request.session.get("public_uuid",None)
		group_data = retrieve_group_reqd_data(group_uuid=public_uuid, with_group_owner_id=True, with_pics_perm=True)
		if not group_data:
			# group does not exist
			if is_ajax:
				return HttpResponse(json.dumps({'success':False,'message':reverse('group_page')}),content_type='application/json',)
			else:
				return redirect("group_page")
		else:
			credentials = is_group_member_and_rules_signatory(group_id, user_id)
			is_member, is_signatory = credentials[0], credentials[1]
			if is_signatory and is_member:
				f = form.save(commit=False) #getting form object, and telling database not to save (commit) it just yet
				if f.image and group_data['pics'] == '1':
					on_fbs = self.request.META.get('HTTP_X_IORG_FBS',False)
					if on_fbs:
						if f.image.size > 200000:
							self.request.session["public_group_request_denied"] = '1'
							self.request.session.modified = True
							if is_ajax:
								return HttpResponse(json.dumps({'success':False,'message':reverse('public_group_request_denied')}),\
									content_type='application/json',)
							else:
								return redirect("public_group_request_denied")
					else:
						if f.image.size > 10000000:
							self.request.session["public_group_request_denied"] = '2'
							self.request.session.modified = True
							if is_ajax:
								return HttpResponse(json.dumps({'success':False,'message':reverse('public_group_request_denied')}),\
									content_type='application/json',)
							else:
								return redirect("public_group_request_denied")
					image_file, img_width, img_height = process_group_image(image=f.image, quality=None if on_fbs else True,\
						already_reoriented=self.request.POST.get('reoriented',None),already_resized=self.request.POST.get('resized',None))
					if img_height == 'too_high':
						self.request.session["public_group_request_denied"] = '3'
						self.request.session["public_group_upload_uuid"] = public_uuid
						self.request.session.modified = True
						if is_ajax:
							return HttpResponse(json.dumps({'success':False,'message':reverse('public_group_request_denied')}),\
								content_type='application/json',)
						else:
							return redirect('public_group_request_denied')
					else:
						uploaded_img_loc = upload_image_to_s3(image_file,prefix='mehfils/')
				else: 
					uploaded_img_loc = None
				UserProfile.objects.filter(user_id=user_id).update(score=F('score')+PUBLIC_GROUP_MESSAGE)
				topic = group_data['tp']
				invalidate_cached_mehfil_replies(group_id)
				invalidate_presence(group_id)
				reply_time = time.time()
				set_input_rate_and_history.delay(section='pub_grp',section_id=group_id,text=f.text,user_id=user_id,time_now=reply_time)
				############################
				############################
				writer_id = str(form.cleaned_data.get('wid','-1'))# the target_id of the writer we're about to directly respond to
				if writer_id not in ('-1','None',str(user_id)) and group_member_exists(group_id, writer_id):
					# ensure writer wasn't self
					raw_user_cred = retrieve_bulk_credentials([user_id,writer_id],decode_unames=True)
					own_uname, own_avurl = raw_user_cred[user_id]['uname'], raw_user_cred[user_id]['avurl']
					other_uname, other_avurl = raw_user_cred[int(writer_id)]['uname'], raw_user_cred[int(writer_id)]['avurl']
					notif_text = "@ "+other_uname+" - "+f.text
					reply = Reply.objects.create(writer_id=user_id, which_group_id=group_id, text=notif_text, image='')
					submission_id, num_submissions = save_group_submission(writer_id=user_id, group_id=group_id, text=f.text, \
						image=uploaded_img_loc, posting_time=reply_time,writer_avurl=get_s3_object(own_avurl,category='thumb'),\
						writer_score=self.request.user.userprofile.score,category='0',writer_uname=own_uname,target_uname=other_uname, \
						target_uid=writer_id, save_latest_submission=True)
					notify_single_user = True
				else:
					own_uname, own_avurl = retrieve_credentials(user_id,decode_uname=True)
					notif_text = f.text
					reply = Reply.objects.create(writer_id=user_id, which_group_id=group_id, text=notif_text, image='')
					submission_id, num_submissions = save_group_submission(writer_id=user_id, group_id=group_id, text=notif_text, \
						image=uploaded_img_loc, posting_time=reply_time,writer_avurl=get_s3_object(own_avurl,category='thumb'),\
						writer_score=self.request.user.userprofile.score,category='0',writer_uname=own_uname,save_latest_submission=True)
					notify_single_user = False
				if num_submissions > DELETION_THRESHOLD:
					# delete extra submissions
					trim_group_submissions.delay(group_id)
				############################
				############################
				rank_public_groups.delay(group_id=group_id,writer_id=user_id)# legacy ranking redis3 function - please review_ownership_transfer_requests
				group_notification_tasks.delay(group_id=group_id,sender_id=user_id,group_owner_id=group_data['oi'], topic=topic, \
					reply_time=reply_time, poster_url=own_avurl, poster_username=own_uname, reply_text=notif_text, priv='0', \
					slug=public_uuid,image_url=uploaded_img_loc,priority='public_mehfil',from_unseen=False,reply_id=reply.id,\
					notify_single_user=notify_single_user, single_target_id=writer_id)
				if is_ajax:
					return HttpResponse(json.dumps({'success':True,'message':reverse('public_group')}),content_type='application/json',)
				else:
					# url = reverse_lazy("public_group_reply")+"#sectionJ"
					url = reverse_lazy("public_group", args=[public_uuid])+"#sectionJ"
					return redirect(url)
			else:
				# not a member and / or signatory
				if is_ajax:
					return HttpResponse(json.dumps({'success':False,'message':reverse('public_group')}),content_type='application/json',)
				else:
					return redirect("public_group")

#################### Rendering list of all mehfils #####################


# class NewGroupPageView(ListView):
# 	"""
# 	Renders list of all joined and invited mehfils (public and private both)
# 	"""
# 	# model = Reply
# 	form_class = GroupPageForm
# 	template_name = "mehfil/group.html"
# 	paginate_by = 20

# 	def get_queryset(self):
# 		groups = []
# 		replies = []
# 		user_id = self.request.user.id
# 		group_ids = get_user_groups(user_id)
# 		replies = filter(None, get_latest_group_replies(group_ids))
# 		replies_qset = Reply.objects.filter(id__in=list(set(replies))).values('id','writer__username','which_group__topic','submitted_on','text','which_group',\
# 			'which_group__unique','writer__userprofile__avatar','which_group__private','category').order_by('-id')[:80]
# 		for reply in replies_qset:
# 			print reply
# 		invited_group_ids_and_times = retrieve_group_invites(user_id)#list of tuples containing invited groups and invite times
# 		print invited_group_ids_and_times
# 		reply_req = reply.category, reply.writer_uname, reply.writer_avurl, reply.posting_time, reply.group.private, reply.text, reply.group.unique, reply.group.id, reply.group.topic, 

# 		invite_req = reply.category, reply.writer_uname, reply.writer_avurl, reply.posting_time, reply.group.private, reply.group.unique, reply.group.id, reply.group.topic

# 		reply_data = get_replies_with_seen(group_replies=replies_qset,viewer_id=user_id,object_type='3')

# 	def get_context_data(self, **kwargs):
# 		context = super(GroupPageView, self).get_context_data(**kwargs)
# 		if self.request.user.is_authenticated():
# 			context["verified"] = FEMALES
# 		return context


# i) Set TOTAL_LIST_SIZE in score.py
# ii) Set MEHFIL_LIST_PAGE_SIZE in score.py
# iii) Set 25 second micro-cache in redis6
# iv) Update get_latest_group_replies() in redis1
# v) Update group.html (done)
# vi) Create group_page(request)
# vii) Create a separate url for group_page(request)
# viii) Take group_page(request) live
# ix) Paginate group_page(request)

def paginate_group_list(data):
	"""
	Divides provided data list into pages
	"""
	pages = {}
	if data:
		data_len, max_pages = len(data), TOTAL_LIST_SIZE/MEHFIL_LIST_PAGE_SIZE#i.e. 4 pages
		for page_num in xrange(1,(max_pages+1),1):
			page_data = data[MEHFIL_LIST_PAGE_SIZE*(page_num-1):MEHFIL_LIST_PAGE_SIZE*page_num]
			if page_data:
				pages[str(page_num)] = page_data
	return pages, len(pages)


def group_page(request):	
	"""
	Renders list of all joined and invited mehfils (public and private both)

	DEPRECATE LATER (ALONGWITH REDIS 1 GROUP FUNCTIONALITY)
	"""
	user_id, page_num = request.user.id, request.GET.get('page', '1')
	page_data_from_micro_cache, num_pages = retrieve_cached_mehfil_pages(user_id,page_num)
	if page_data_from_micro_cache:
		data = json.loads(page_data_from_micro_cache)
	else:
		groups, replies = [], []
		group_ids = get_user_groups(user_id)
		replies = filter(None, get_latest_group_replies(group_ids))#'latest_group_reply' is the latest reply in any given group, saved with a TTL of TWO WEEKS
		num_replies = len(replies)
		##################
		if num_replies == 0:
			# only have invites to show
			invite_reply_ids = get_active_invites(user_id) #contains all current invites (they have associated replies to them)
			num_invites = len(invite_reply_ids)
			if num_invites > TOTAL_LIST_SIZE:
				most_recent_invites = sorted(invite_reply_ids, key=int,reverse=True)[:TOTAL_LIST_SIZE]
			elif not num_invites:
				most_recent_invites = []
			else:
				most_recent_invites = sorted(invite_reply_ids, key=int,reverse=True)
			replies_qset = Reply.objects.filter(id__in=most_recent_invites).values('id','category','text','submitted_on','which_group',\
				'writer__username','which_group__topic','which_group__unique','writer__userprofile__avatar','which_group__private').order_by('-id')
			for data in replies_qset:
				data['submitted_on'] = convert_to_epoch(data['submitted_on'])
			data = get_replies_with_seen(group_replies=replies_qset,viewer_id=user_id,object_type='3')
			pages, num_pages = paginate_group_list(data)
			data = pages[page_num] if pages else []
			cache_mehfil_pages(pages,user_id)
		elif num_replies >= TOTAL_LIST_SIZE:
			# only use replies to populate the list
			most_recent_replies = sorted(replies, key=int,reverse=True)[:TOTAL_LIST_SIZE]
			replies_qset = Reply.objects.filter(id__in=most_recent_replies).values('id','category','text','submitted_on','which_group',\
				'writer__username','which_group__topic','which_group__unique','writer__userprofile__avatar','which_group__private').order_by('-id')
			for data in replies_qset:
				data['submitted_on'] = convert_to_epoch(data['submitted_on'])
			data = get_replies_with_seen(group_replies=replies_qset,viewer_id=user_id,object_type='3')
			pages, num_pages = paginate_group_list(data)
			data = pages[page_num]
			cache_mehfil_pages(pages,user_id)
		else:
			#concatenate at least 1 invite!
			sorted_replies = sorted(replies, key=int,reverse=True)
			invite_reply_ids = get_active_invites(user_id) #contains all current invites (they have associated replies to them)
			##################
			if invite_reply_ids:
				empty_invite_slots_available = TOTAL_LIST_SIZE - num_replies
				most_recent_invites = sorted(invite_reply_ids, key=int,reverse=True)[:empty_invite_slots_available]
				final_ids = sorted_replies + most_recent_invites
				replies_qset = Reply.objects.filter(id__in=set(final_ids)).values('id','category','text','submitted_on','which_group',\
					'writer__username','which_group__topic','which_group__unique','writer__userprofile__avatar','which_group__private')
				for data in replies_qset:
					data['submitted_on'] = convert_to_epoch(data['submitted_on'])
				# re-arrange replies_qset in the same order as the list "final_ids"
				unsorted_final_data = {}
				for item in replies_qset:
					unsorted_final_data[item['id']] = item
				sorted_final_data = []
				for item_id in map(int,final_ids):
					data = unsorted_final_data.get(item_id,None)
					if data:
						sorted_final_data.append(data)
				# get 'Seen' status
				data = get_replies_with_seen(group_replies=sorted_final_data,viewer_id=user_id,object_type='3')
				pages, num_pages = paginate_group_list(data)
				data = pages[page_num]
				# cache and return data
				cache_mehfil_pages(pages,user_id)
			else:
				replies_qset = Reply.objects.filter(id__in=sorted_replies).values('id','category','text','submitted_on','which_group',\
					'writer__username','which_group__topic','which_group__unique','writer__userprofile__avatar','which_group__private').order_by('-id')
				for data in replies_qset:
					data['submitted_on'] = convert_to_epoch(data['submitted_on'])
				data = get_replies_with_seen(group_replies=replies_qset,viewer_id=user_id,object_type='3')
				pages, num_pages = paginate_group_list(data)
				data = pages[page_num]
				cache_mehfil_pages(pages,user_id)
	page_num = int(page_num)
	return render(request,'mehfil/group.html',{'verified':FEMALES,'own_uname':retrieve_uname(user_id,decode=True),\
		'object_list':data,'page_num':page_num,'page_obj':{'previous_page_number':page_num-1,'next_page_number':page_num+1,\
		'has_next':True if page_num<num_pages else False,'has_previous':True if page_num>1 else False}})


def group_list(request):	
	"""
	Renders list of all joined and invited mehfils (public and private both)
	DEPRECATE LATER (ALONGWITH REDIS 1 GROUP FUNCTIONALITY)
	"""
	groups, replies = [], []
	user_id, page_num = request.user.id, request.GET.get('page', '1')
	group_ids = get_user_groups(user_id)
	replies = filter(None, get_latest_group_replies(group_ids))#'latest_group_reply' is the latest reply in any given group, saved with a TTL of TWO WEEKS
	invite_reply_ids = get_active_invites(user_id) #contains all current invites (they have associated replies to them)
	invite_reply_ids |= set(replies) #doing union of two sets. Gives us all latest reply ids, minus any deleted replies (e.g. if the group object had been deleted)
	replies_qset = Reply.objects.filter(id__in=invite_reply_ids).values('id','category','text','submitted_on','which_group','writer__username',\
		'which_group__topic','which_group__unique','writer__userprofile__avatar','which_group__private').order_by('-id')[:80]
	for data in replies_qset:
		data['submitted_on'] = convert_to_epoch(data['submitted_on'])
	data = get_replies_with_seen(group_replies=replies_qset,viewer_id=user_id,object_type='3')
	pages, num_pages = paginate_group_list(data)
	data = pages[page_num] if pages else []
	page_num = int(page_num)
	return render(request,"mehfil/group.html",{'verified':FEMALES,'own_uname':retrieve_uname(user_id, decode=True),\
		'object_list':data,'page_num':page_num,'page_obj':{'previous_page_number':page_num-1,'next_page_number':page_num+1,\
		'has_next':True if page_num<num_pages else False,'has_previous':True if page_num>1 else False}})


##################### Mehfil membership #####################

def time_reqd_to_read(lenght_of_text):
	"""
	Determines time required to read rules (in seconds) so that user can be stalled for that time
	"""
	base_str_len = 9
	base_ttr = 2#2 seconds
	max_ttr = 20#20 seconds

	if lenght_of_text < base_str_len:
		return base_ttr
	else:
		bigness_ratio = (lenght_of_text-base_str_len)*1.0 / (lenght_of_text+base_str_len)#tends to 0 for very small strings, and tends to 1 for very large ones
		scale_factor = 1+(3.5*bigness_ratio)# scale up base_ttr according to this (between 1 and 4.2)
		determined_ttr = round(base_ttr**scale_factor)# base_ttr raised to the power scale_factor
		if determined_ttr > max_ttr:
			return max_ttr
		else:
			return determined_ttr


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def join_private_group(request):
	"""
	Officially joining a private group
	"""
	if request.method == "POST":
		group_id = request.POST.get("gid",None)
		own_id = str(request.user.id)
		group_owner_id = retrieve_group_owner_id(group_id=group_id)
		joiner_is_owner = group_owner_id == own_id
		if request.user_banned:
			# user is hell-banned
			return redirect("error")
		elif not request.mobile_verified:
			# do not let user join a mehfil if they're not verified
			return render(request,'verification/unable_to_submit_without_verifying.html',{'join_private_mehfil':True})
		elif is_membership_frozen(group_id):
			# group has been reported - its membership is currently frozen
			return render(request,"mehfil/notify_and_redirect.html",{'action_frozen':True,'unique':retrieve_group_uuid(group_id),'is_public':False})
		elif group_member_exists(group_id, own_id):
			# already a member
			request.session["unique_id"] = retrieve_group_uuid(group_id)
			return redirect("private_group_reply")
		# IMPLEMENT THE BELOW A FEW WEEKS AFTER LAUNCH - SO THAT NO ONE CAN JOIN PRIV MEHFIL WITHOUT AN INVITE (EVEN IF THEY NAVIGATE TO IT)
		# and once implemented - ensure would-be joiner see basic mehfil stats at the 'join' page (who are the members, who owns it, etc.) - also see first_time_refresh() comments for another tweak
		# elif not invite_exists(group_id, own_id):
		#     # reject user if uninvited
		#     return render(request,"mehfil/notify_and_redirect.html",{'uninvited':True,'owner_uname':retrieve_group_owner_uname(group_id)})
		elif banned_from_group(group_id, own_id):
			# user is banned from group, turn them away
			ban_details = get_ban_details(group_id, own_id)
			ban_start_time = float(ban_details['kt'])
			time_elapsed = time.time() - ban_start_time
			ban_reason  = ban_details.get('kr',None)
			ban_reason = ban_reason.decode('utf-8') if ban_reason else ban_reason
			ban_duration = ban_details.get('kd',None)
			ban_time_remaining = (float(ban_duration) - time_elapsed) if ban_duration else None
			return render(request,"mehfil/notify_and_redirect.html",{'cannot_join':True,'ban_reason':ban_reason,'time_remaining':ban_time_remaining,\
				'is_private':True})
		elif recently_quit_group(group_id, own_id):
			# quit recently, don't allow immediate rejoining
			return render(request,"mehfil/notify_and_redirect.html",{'recently_quit':True,'is_public':False})
		else:
			has_owner_joined = group_member_exists(group_id, group_owner_id)
			if has_owner_joined:
				membership_threshold = PRIVATE_GROUP_MAX_MEMBERSHIP
				owner_spot_saved = False
			else:
				membership_threshold = PRIVATE_GROUP_MAX_MEMBERSHIP-1
				owner_spot_saved = True
			if not joiner_is_owner and get_num_group_members(group_id) >= membership_threshold:
				# group cannot accomodate more members - an attribute of private groups (but exception is made for mehfil owner)
				return render(request,"mehfil/notify_and_redirect.html",{'member_limit_reached':True,'owner_uname':retrieve_group_owner_uname(group_id),\
					'owner_spot_saved':owner_spot_saved})
			else:
				# proceed and add the joiner as a member
				time_now = time.time()
				own_uname, own_avurl = retrieve_credentials(own_id,decode_uname=True)
				##############################################
				# legacy redis 1 functionality
				add_group_member(group_id, own_uname)
				remove_group_invite(own_id, group_id)
				add_user_group(own_id, group_id)
				##############################################
				reply = Reply.objects.create(which_group_id=group_id, writer_id=own_id, text='join', category='9')# to take care of grouppageview
				group_notification_tasks.delay(group_id=group_id,sender_id=own_id,group_owner_id=group_owner_id, topic=retrieve_group_topic(group_id=group_id),\
					reply_time=time_now,poster_url=own_avurl,poster_username=own_uname,reply_text='join', priv='1',image_url=None,priority='priv_mehfil',\
					from_unseen=False, reply_id=reply.id, txt_type='join')# to take care of matka, priv is group privacy. uniqud_id is group uniqud
				submission_id, num_submissions = save_group_submission(writer_id=own_id, group_id=group_id, text='join',posting_time=time_now,category='9', \
					writer_uname=own_uname, writer_avurl=get_s3_object(own_avurl,category='thumb'))
				if num_submissions > DELETION_THRESHOLD:
					# delete extra submissions
					trim_group_submissions.delay(group_id)
				invalidate_cached_mehfil_replies(group_id)#redis6 function
				main_sentence = own_uname+" ne mehfil join ki at {0}".format(exact_date(time_now))
				document_administrative_activity.delay(group_id, main_sentence, 'join')
				##############################################
				added = create_group_membership_and_rules_signatory(group_id=group_id, member_id=own_id, time_now=time_now, \
					member_is_owner=joiner_is_owner)
				if added:
					request.session["unique_id"] = retrieve_group_uuid(group_id)
					return redirect("private_group_reply")
				else:
					# not added (e.g. group was recently deleted)
					return redirect("group_page")
	else:
		return redirect("group_page")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def owner_rejoining_public_group(request):
	"""
	Processing owner's attempt to rejoin a mehfil
	"""
	if request.method == "POST":
		own_id = str(request.user.id)
		decision = request.POST.get("dec",None)
		group_id = request.POST.get("gid",None)
		category = request.POST.get("cat",None)
		if group_id and decision is None:
			form = OpenGroupCreateForm(data=request.POST,verified=request.mobile_verified, score=request.user.userprofile.score, rejoin='1')
			if form.is_valid():
				# form is valid
				topic = form.cleaned_data.get("topic")
				formatted_rules, rules = form.cleaned_data.get("rules")
				group_owner_id = retrieve_group_owner_id(group_id=group_id)
				# ensure user really is this group's owner
				if own_id == group_owner_id:
					# show preview
					temporarily_save_group_credentials(user_id=own_id, topic=topic, rules=rules, formatted_rules=formatted_rules, category=category, \
						group_id=group_id)
					return render(request,"mehfil/new_open_group_preview.html",{'topic':topic,'rules':formatted_rules,'category':category,\
						'owner_rejoining':True})
				else:
					# not own group
					return redirect("group_page")
			else:
				# form is invalid
				return render(request,"mehfil/create_new_open_group_or_rejoin.html",{'form':form,'topic_char_limit':PUBLIC_GROUP_MAX_TITLE_SIZE,\
					'rules_char_limit':PUBLIC_GROUP_MAX_RULES_SIZE,'owner_rejoining':True,'gid':group_id,'cat':category})
		elif decision in ('0','1','2'):
			if decision == '0':
				# return to group
				return redirect("public_group")
			elif decision == '1':
				# change credentials
				data = get_temporarily_saved_group_credentials(own_id)
				if data:
					form = OpenGroupCreateForm(initial=data)# prepopulating the form with user's data (but not calling validation on it)
					return render(request,"mehfil/create_new_open_group_or_rejoin.html",{'form':form,'topic_char_limit':PUBLIC_GROUP_MAX_TITLE_SIZE,\
						'rules_char_limit':PUBLIC_GROUP_MAX_RULES_SIZE,'owner_rejoining':True,'gid':data['gid'],'cat':data['category']})
				else:
					# the data does not exist any more (expired)
					form = OpenGroupCreateForm()
					return render(request,"mehfil/create_new_open_group_or_rejoin.html",{'form':form,'topic_char_limit':PUBLIC_GROUP_MAX_TITLE_SIZE,\
						'rules_char_limit':PUBLIC_GROUP_MAX_RULES_SIZE,'owner_rejoining':True,'gid':data['gid'],'cat':data['category']})
			elif decision == '2':
				# accept credentials
				time_now = time.time()
				data = get_temporarily_saved_group_credentials(own_id)
				topic, rules, group_category, raw_rules, group_id = data['topic'], data['formatted_rules'], data["category"], data['rules'], data['gid']
				Group.objects.filter(id=group_id).update(topic=topic,rules=rules)
				update_group_topic.delay(group_id=group_id, topic=topic)#redis 2
				saved = save_group_topic_and_rules(group_id, topic=topic, rules=rules, raw_rules=raw_rules)
				if saved:
					own_uname, own_avurl = retrieve_credentials(own_id,decode_uname=True)
					##############################################
					# legacy functionality
					add_group_member(group_id, own_uname)
					remove_group_invite(own_id, group_id)
					add_user_group(own_id, group_id)#to take care of grouppageview()
					##############################################
					reply = Reply.objects.create(which_group_id=group_id, writer_id=own_id, text='join', category='9')
					group_notification_tasks.delay(group_id=group_id,sender_id=own_id,group_owner_id=own_id,topic=topic,reply_time=time_now,\
						poster_url=own_avurl,poster_username=own_uname,reply_text='join',priv='0',image_url=None,priority='public_mehfil',\
						from_unseen=False, reply_id=reply.id, txt_type='join')# to take care of matka, priv is group privacy
					submission_id, num_submissions = save_group_submission(writer_id=own_id, group_id=group_id, text='join',posting_time=time_now,\
						category='9', writer_uname=own_uname, writer_avurl=get_s3_object(own_avurl,category='thumb'))# makes 'joining' announcement appear inside group
					if num_submissions > DELETION_THRESHOLD:
						# delete extra submissions
						trim_group_submissions.delay(group_id)
					invalidate_cached_mehfil_replies(group_id)#redis6 function
					##############################################
					try:
						join_date = convert_to_epoch(User.objects.only('date_joined').get(id=own_id).date_joined)
					except User.DoesNotExist:
						# this user does not exist thus data incomplete
						join_date = None
					added = create_group_membership_and_rules_signatory(group_id=group_id, member_id=own_id, member_join_time=join_date, \
						time_now=time_now, is_public=True, member_is_owner=True)
					if added:
						return render(request,"mehfil/force_members_to_accept_rules.html",{'gid':group_id})
					else:
						# group was recently deleted
						return redirect("group_page")
				else:
					return redirect("group_page")
		else:
			# invalid entry
			return redirect("public_group")
	else:
		return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def force_rules_onto_members(request):
	"""
	Enforces members to accept mehfil rules before participating
	"""
	if request.method == "POST":
		group_id = request.POST.get("gid",None)
		owner_id = retrieve_group_owner_id(group_id=group_id)
		if owner_id == str(request.user.id):
			decision = request.POST.get("dec",None)
			if decision == '1':
				invalidate_all_rule_signatories(group_id, owner_id=owner_id, time_now=time.time())
			return redirect("public_group")
		else:
			# unauthorized
			return redirect("group_page")
	else:
		# not a POST request
		return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def join_public_group(request):
	"""
	Officially joining a public group (step BEFORE signing the rules)
	"""
	if request.method == "POST":
		group_id = request.POST.get("gid",None)
		own_id = request.user.id
		if request.user_banned:
			# user is hell-banned
			return redirect("error")
		elif not request.mobile_verified:
			# do not let user join a mehfil if they're not verified
			return render(request,'verification/unable_to_submit_without_verifying.html',{'join_public_mehfil':True})
		elif is_membership_frozen(group_id):
			# group has been reported - its membership is currently frozen
			return render(request,"mehfil/notify_and_redirect.html",{'action_frozen':True,'unique':retrieve_group_uuid(group_id),'is_public':True})
		elif group_member_exists(group_id, own_id):
			# already a member
			return redirect("public_group")
		elif banned_from_group(group_id, own_id):
			# user is banned from group, turn them away
			ban_details = get_ban_details(group_id, own_id)
			ban_start_time = float(ban_details['kt'])
			time_elapsed = time.time() - ban_start_time
			ban_reason  = ban_details.get('kr',None)
			ban_reason = ban_reason.decode('utf-8') if ban_reason else ban_reason
			ban_duration = ban_details.get('kd',None)
			ban_time_remaining = (float(ban_duration) - time_elapsed) if ban_duration else None
			return render(request,"mehfil/notify_and_redirect.html",{'cannot_join':True,'ban_reason':ban_reason,'time_remaining':ban_time_remaining})
		else:
			# proceed
			group_uuid_from_session = request.session.get('public_uuid',None)
			group_uuid = request.POST.get("uid",None)
			group_meta_data = retrieve_group_meta_data(group_id=group_id)
			if group_meta_data:
				group_uuid = str(group_uuid)
				if group_meta_data['u'] == group_uuid and group_uuid == str(group_uuid_from_session):
					# group credentials confirmed
					if group_meta_data['grp_categ'] == '2':
						# this group solely entertains pink stars
						own_username = retrieve_uname(own_id,decode=True)
						if own_username in FEMALES:
							# this group entertains everyone
							if str(own_id) == group_meta_data['oi']:
								# force owner change topic and rules before rejoining
								form = OpenGroupCreateForm(initial={'topic':group_meta_data['tp'],'rules':group_meta_data['r']})
								return render(request,"mehfil/create_new_open_group_or_rejoin.html",{'form':form,'topic_char_limit':PUBLIC_GROUP_MAX_TITLE_SIZE,\
									'rules_char_limit':PUBLIC_GROUP_MAX_RULES_SIZE,'gid':group_meta_data['gi'],'cat':group_meta_data['grp_categ'],\
									'owner_rejoining':True})
							else:
								# membership hopeful
								rules = group_meta_data['r']
								return render(request,"mehfil/accept_open_group_rules.html",{'rules':rules,'ttr':int(time_reqd_to_read(len(rules))),\
									'st':time.time(),'gid':group_id,'uid':group_uuid})
						else:
							return render(request,"mehfil/accept_open_group_rules.html",{'only_pinkstars_allowed':True})
					else:
						# this group entertains everyone
						if str(own_id) == group_meta_data['oi']:
							# force owner change topic and rules before rejoining
							form = OpenGroupCreateForm(initial={'topic':group_meta_data['tp'],'rules':group_meta_data['r']})
							return render(request,"mehfil/create_new_open_group_or_rejoin.html",{'form':form,'topic_char_limit':PUBLIC_GROUP_MAX_TITLE_SIZE,\
								'rules_char_limit':PUBLIC_GROUP_MAX_RULES_SIZE,'gid':group_meta_data['gi'],'cat':group_meta_data['grp_categ'],\
								'owner_rejoining':True})
						else:
							# membership hopeful
							rules = group_meta_data['r']
							return render(request,"mehfil/accept_open_group_rules.html",{'rules':rules,'ttr':int(time_reqd_to_read(len(rules))),\
								'st':time.time(),'gid':group_id,'uid':group_uuid})
				else:
					# group credentials fudged
					return redirect("public_group")
			else:
				# group does not exist any more
				return redirect("public_group")
	else:
		return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def accept_open_group_rules(request):
	"""
	Process user response to group rules (final act of joining the group)
	"""
	if request.method == "POST":
		own_id = request.user.id
		if not request.mobile_verified:
			return render(request,'verification/unable_to_submit_without_verifying.html',{'join_public_mehfil':True})
		else:
			group_id = request.POST.get("gid",None)
			group_uuid = request.POST.get("uid",None)
			accept_rules = request.POST.get("acc",None)
			start_time = request.POST.get("st",None)
			time_to_read = request.POST.get("ttr",None)
			if banned_from_group(group_id, own_id):
				# user is banned from group, turn them away
				ban_details = get_ban_details(group_id, own_id)
				ban_start_time = float(ban_details['kt'])
				time_elapsed = time.time() - ban_start_time
				ban_reason  = ban_details.get('kr',None)
				ban_reason = ban_reason.decode('utf-8') if ban_reason else ban_reason
				ban_duration = ban_details.get('kd',None)
				ban_time_remaining = (float(ban_duration) - time_elapsed) if ban_duration else None
				return render(request,"mehfil/notify_and_redirect.html",{'cannot_join':True,'ban_reason':ban_reason,'time_remaining':ban_time_remaining})
			elif accept_rules == '0':
				# rules are unnacceptable to the user, thus return
				return redirect("public_group")
			elif recently_quit_group(group_id, own_id):
				# quit recently, don't allow immediate rejoining
				return render(request,"mehfil/notify_and_redirect.html",{'recently_quit':True,'is_public':True})
			elif accept_rules == '1':
				group_meta_data = retrieve_group_meta_data(group_id=group_id)
				if group_meta_data.get('u','') == str(group_uuid):
					# group credentials confirmed
					own_uname, own_avurl = retrieve_credentials(own_id,decode_uname=True)
					time_now = time.time()
					if group_meta_data['grp_categ'] == '2':
						# only for pink stars
						if own_uname in FEMALES:
							if (time_now-float(start_time)) >= float(time_to_read):
								# rules are acceptable to the user and they took the prescribed time to read them
								##############################################
								# legacy functionality
								add_group_member(group_id, own_uname)
								remove_group_invite(own_id, group_id)
								add_user_group(own_id, group_id)
								##############################################
								reply = Reply.objects.create(which_group_id=group_id, writer_id=own_id, text='join', category='9')# to take care of grouppageview
								group_owner_id = group_meta_data['oi']
								group_notification_tasks.delay(group_id=group_id,sender_id=own_id,group_owner_id=group_owner_id,topic=group_meta_data['tp'],\
									reply_time=time_now,poster_url=own_avurl,poster_username=own_uname,reply_text='join',priv='0',image_url=None,\
									priority='public_mehfil',from_unseen=False, reply_id=reply.id, txt_type='join')# to take care of matka, priv is group privacy. uniqud_id is group uniqud
								submission_id, num_submissions = save_group_submission(writer_id=own_id, group_id=group_id, text='join',posting_time=time_now,\
									category='9', writer_uname=own_uname, writer_avurl=get_s3_object(own_avurl,category='thumb'))
								if num_submissions > DELETION_THRESHOLD:
									# delete extra submissions
									trim_group_submissions.delay(group_id)
								invalidate_cached_mehfil_replies(group_id)#redis6 function
								##############################################
								try:
									join_date = convert_to_epoch(User.objects.only('date_joined').get(id=own_id).date_joined)
								except User.DoesNotExist:
									# this user does not exist thus data incomplete
									join_date = None
								added = create_group_membership_and_rules_signatory(group_id=group_id, member_id=own_id,  member_join_time=join_date, \
									time_now=time_now,is_public=True,member_is_owner=True if group_owner_id==str(own_id) else False)
								if added:
									return redirect("public_group")
								else:
									# not added because group was recently deleted
									return redirect("group_page")
							else:
								# they didn't take their required time to read the rules, go back
								rules = group_meta_data['r']
								return render(request,"mehfil/accept_open_group_rules.html",{'rules':rules,'ttr':int(time_reqd_to_read(len(rules))),\
									'st':time_now,'show_help_msg':True,'gid':group_id,'uid':group_uuid})
						else:
							# this user is trying to enter a pink star area without a pink star
							return redirect("public_group")
					else:
						# this group allows users other than pink stars
						if (time_now-float(start_time)) >= float(time_to_read):
							# rules are acceptable to the user and they took the prescribed time to read them
							##############################################
							# legacy functionality
							add_group_member(group_id, own_uname)
							remove_group_invite(own_id, group_id)
							add_user_group(own_id, group_id)
							##############################################
							reply = Reply.objects.create(which_group_id=group_id, writer_id=own_id, text='join', category='9')# to take care of grouppageview
							group_owner_id = group_meta_data['oi']
							group_notification_tasks.delay(group_id=group_id,sender_id=own_id,group_owner_id=group_owner_id,topic=group_meta_data['tp'],\
								reply_time=time_now,poster_url=own_avurl,poster_username=own_uname,reply_text='join',priv='0',image_url=None,\
								priority='public_mehfil',from_unseen=False, reply_id=reply.id,txt_type='join')# to take care of matka, priv is group privacy. uniqud_id is group uniqud
							submission_id, num_submissions = save_group_submission(writer_id=own_id, group_id=group_id, text='join',posting_time=time_now,\
								category='9', writer_uname=own_uname, writer_avurl=get_s3_object(own_avurl,category='thumb'))
							if num_submissions > DELETION_THRESHOLD:
								# delete extra submissions
								trim_group_submissions.delay(group_id)
							invalidate_cached_mehfil_replies(group_id)#redis6 function
							##############################################
							try:
								join_date = convert_to_epoch(User.objects.only('date_joined').get(id=own_id).date_joined)
							except User.DoesNotExist:
								# this user does not exist thus data incomplete
								join_date = None
							added = create_group_membership_and_rules_signatory(group_id=group_id, member_id=own_id, member_join_time=join_date, \
								time_now=time_now,is_public=True, member_is_owner=True if group_owner_id == str(own_id) else False)
							if added:
								return redirect("public_group")
							else:
								# not added because group was recently deleted
								return redirect("group_page")
						else:
							# they didn't take their required time to read the rules, go back
							rules = group_meta_data['r']
							return render(request,"mehfil/accept_open_group_rules.html",{'rules':rules,'ttr':int(time_reqd_to_read(len(rules))),\
								'st':time_now,'show_help_msg':True,'gid':group_id,'uid':group_uuid})
				else:
					# group credentials unconfirmed, just return
					return redirect("group_page")
			else:
				# input was tinkered with?
				return redirect("group_page")
	else:
		return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def quick_accept_open_group_rules(request):
	"""
	Process user response to group rules (bypasses 'ttr' checkup this function's more invovled counterpart in accept_open_group_rules() carries out)
	"""
	if request.method == "POST":
		pk = request.POST.get("gid",None)
		own_id = request.user.id
		if not request.mobile_verified:
			return render(request,'verification/unable_to_submit_without_verifying.html',{'join_public_mehfil':True})
		elif banned_from_group(pk, own_id):
			return redirect("public_group")
		else:
			decision = request.POST.get("dec",None)
			unique = request.POST.get("uid",None)
			data = retrieve_group_reqd_data(group_id=pk,with_group_owner_id=True,with_uuid=True)#group privacy, group_id, group_topic, group_owner_id (optional), 'pics'(optional)
			if data:
				if data['u'] == str(unique):
					# group credentials confirmed
					if decision == '1':
						#accept the rules
						insert_rules_signatory(pk, own_id, time.time())
						return redirect("public_group")
					else:
						# tantamount to exiting the mehfil
						context={'unique':unique, 'pk':pk, 'topic':data['tp'], 'inside_grp':'1'}
						if data['oi'] == str(own_id):
							return render(request, 'mehfil/delete_public_group.html', context)
						else:
							return render(request, 'mehfil/leave_public_group.html', context)
				else:
					return redirect("public_group")
			else:
				# group does not exist
				return redirect("group_page")
	else:
		return redirect("public_group")

#################### Inviting users to mehfils #####################


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def process_public_group_invite(request,*args, **kwargs):
	"""
	Sending a prospective user an invite to a public mehfil

	If prospective member was already invited, ensure invite not sent
	"""
	if request.user_banned:
		return redirect("group_page")
	elif request.method == "POST":	
		uuid = request.POST.get("puid",None)
		pk = request.POST.get("vid",None)#visitor id
		group_owner_id, group_id = retrieve_group_owner_id(group_uuid=uuid,with_group_id=True)
		if group_owner_id:
			own_id = str(request.user.id)
			is_officer = is_group_officer(group_id,own_id)
			is_owner = own_id == group_owner_id
			if is_officer or is_owner:
				can_invite = invite_allowed(group_id,inviter='owner' if is_owner else 'officer',is_public=True)
				if can_invite:
					invitee_username = retrieve_uname(pk,decode=True)
					if check_group_invite(pk, group_id) or check_group_member(group_id, invitee_username):
						# REPLACE check_group_invite() WITH reinviting() redis 6 later
						# REPLACE check_group_member() WITH group_member_exists() redis 6 later
						# calling ReinviteView() - invite already exists (target is being 'double-invited')
						return redirect("reinvite_help", slug= uuid)
					else:
						#################################################################################
						# this person ought to be sent an invite                                        #
						# create reply and then use its ID in add_group_invite()                        #
						# this is legacy that can be removed once Reply and Group models are deprecated #
						reply = Reply.objects.create(text=invitee_username, category='1', which_group_id=group_id,writer_id=own_id)
						add_group_invite(pk, group_id,reply.id)
						############# REDIS 6 #############
						save_group_invite(group_id=group_id, target_id=pk, time_now=time.time(),is_public=True,sent_by='owner' if is_owner else 'officer')# redis 6 function, remove add_group_invite (redis 1) later
						own_uname = retrieve_uname(own_id,decode=True)
						partial_sentence = own_uname+" ne "+invitee_username
						main_sentence = partial_sentence+" ko invite kiya at {0}".format(exact_date(time.time()))
						document_administrative_activity.delay(group_id, main_sentence, 'public_invite')
						###################################
						return redirect("invite")
				else:
					#exhausted invites or not authorized, either way redirect user
					return redirect("group_page")
			else:
				# not authorized to invite
				return redirect("group_page")
		else:
			# group does not exist
			return redirect("group_page")
	else:
		# not a POST
		return redirect("public_group")



@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def process_private_group_invite(request, *args, **kwargs):
	"""
	Sending a prospective user an invite to a private mehfil

	If prospective member was already invited, ensure invite not sent
	"""
	if request.user_banned:
		return redirect("group_page")
	elif request.method=="POST":
		uuid = request.POST.get("puid",None)
		pk = request.POST.get("vid",None)#visitor_id
		group_owner_id, group_id = retrieve_group_owner_id(group_uuid=uuid,with_group_id=True)
		if group_id:
			user_id = str(request.user.id)
			is_owner = user_id == group_owner_id
			if group_member_exists(group_id, user_id):
				can_invite, reason = invite_allowed(group_id,inviter='owner' if is_owner else 'member',is_public=False,\
					inviter_id=user_id)
				if can_invite:
					invitee_username = retrieve_uname(pk,decode=True)
					if check_group_invite(pk, group_id) or check_group_member(group_id, invitee_username):
						# REPLACE check_group_invite() WITH reinviting() redis 6 later
						# REPLACE check_group_member() WITH group_member_exists() redis 6 later
						# calling ReinvitePrivateView(), ensures already invited user not invited again
						return redirect("reinvite_private_help")
					else:
						#################################################################################
						# this person ought to be sent an invite                                        #
						# create reply and then use its ID in add_group_invite()                        #
						# this is legacy that can be removed once Reply and Group models are deprecated #
						reply = Reply.objects.create(text=invitee_username, category='1', which_group_id=group_id,writer_id=user_id)
						reply_id = reply.id
						add_group_invite(pk, group_id,reply_id)#redis 1 legacy function
						##############################
						##############################
						time_now = time.time()
						own_uname, own_avurl = retrieve_credentials(user_id,decode_uname=True)
						submission_id, num_submissions = save_group_submission(writer_id=user_id, group_id=group_id, text=invitee_username,\
							posting_time=time_now,category='1', writer_uname=own_uname, writer_avurl=get_s3_object(own_avurl,category='thumb'))# shows invite in group
						if num_submissions > DELETION_THRESHOLD:
							# delete extra submissions
							trim_group_submissions.delay(group_id)
						save_group_invite(group_id=group_id, target_id=pk, time_now=time_now,is_public=False, \
						sent_by='owner' if is_owner else 'member',sent_by_id=user_id)# redis 6 function, remove add_group_invite() (redis 1) later
						invalidate_cached_mehfil_replies(group_id)
						invalidate_presence(group_id)
						partial_sentence = own_uname+" ne "+invitee_username
						main_sentence = partial_sentence+" ko invite kiya at {0}".format(exact_date(time_now))
						document_administrative_activity.delay(group_id, main_sentence, 'private_invite')
						##############################
						##############################
						set_latest_group_reply(group_id,reply_id)# populates grouppageview()
						request.session.pop("unique_id",None)
						return redirect("invite_private", slug=uuid)
				else:
					if reason == 'mem_overflow':
						# member limit reached
						return render(request,"mehfil/notify_and_redirect.html",{'member_overflow':True,'max_members':PRIVATE_GROUP_MAX_MEMBERSHIP,\
							'unique':uuid})
					elif reason == 'ivt_overflow':
						# invite limit reached
						return render(request,"mehfil/notify_and_redirect.html",{'invite_overflow':True,'unique':uuid,'is_public':False})
					else:
						# some other generic error, redirect user
						return redirect("group_page")
			else:
				# not authorized to invite
				return redirect("group_page")
	else:
		return redirect("group_page")

############################################################

# class InviteUsersToPrivateGroupView(ListView):
# 	"""
# 	Renders list of currently online users, and allows inviter to select users from there for their private mehfil
# 	"""
# 	# model = Session
# 	template_name = "mehfil/invite_for_private_group.html"
# 	paginate_by = 100

# 	def get_queryset(self):
# 		if self.request.user_banned:
# 			return []
# 		else:
# 			global condemned
# 			user_ids = get_most_recent_online_users()#cache_mem.get('online')
# 			try:
# 				group = Group.objects.get(unique=self.request.session["unique_id"])
# 				users_purified = [pk for pk in user_ids if pk not in condemned]
# 				non_invited_online_ids = bulk_check_group_invite(users_purified,group.id)
# 				non_invited_non_member_online_ids = bulk_check_group_membership(non_invited_online_ids,group.id)
# 				print "kads"
# 				print User.objects.filter(id__in=non_invited_non_member_online_ids).values('id','userprofile__score','userprofile__avatar','username')
# 				return User.objects.filter(id__in=non_invited_non_member_online_ids).values('id','userprofile__score','userprofile__avatar','username')
# 			except:
# 				return []

# 	def get_context_data(self, **kwargs):
# 		context = super(InviteUsersToPrivateGroupView, self).get_context_data(**kwargs)
# 		if self.request.user.is_authenticated():
# 			context["legit"] = FEMALES
# 			try:	
# 				unique = self.request.session["unique_id"]
# 				context["unique"] = unique
# 				group = Group.objects.get(unique=unique)
# 				context["authorized"] = True
# 				context["group"] = group
# 			except:
# 				context["authorized"] = False
# 		return context				


############################################################


class InviteUsersToPrivateGroupView(ListView):
	"""
	Renders list of currently online users, and allows inviter to select users from there for their private mehfil
	"""
	# model = Session
	template_name = "mehfil/invite_for_private_group.html"
	paginate_by = 100

	def get_queryset(self):
		if self.request.user_banned:
			return [{'id':-4}]
		else:
			group_owner_id, group_id = retrieve_group_owner_id(group_uuid=self.request.session.get("unique_id",None),with_group_id=True)
			if group_owner_id:
				own_id = str(self.request.user.id)
				if group_member_exists(group_id, own_id):
					user_ids = get_most_recent_online_users()#cache_mem.get('online')
					# user_ids = [1,9, 11,22,33,44,55,66,77,88,99]
					if user_ids:
						users_purified = [pk for pk in user_ids if pk not in condemned]
						non_invited_online_ids = bulk_check_group_invite(users_purified,group_id)# removes already invited users (redis 1 legacy function - remove)
						non_invited_non_member_online_ids = bulk_check_group_membership(non_invited_online_ids,group_id)# removes already member users (redis 1 function)
						user_data = retrieve_bulk_credentials(non_invited_non_member_online_ids, decode_unames=True)#returned data {int(user_id):{'uname':uname,'avurl':avurl}}
						if user_data:
							final_data = []#list of dictionaries
							for online_id in non_invited_non_member_online_ids:
								online_id = int(online_id)
								final_data.append({'id':online_id,'username':user_data[online_id]['uname'],'avurl':user_data[online_id]['avurl']})
							return final_data
						else:
							# no one online
							return [{'id':-1}]
					else:
						# no one online
						return [{'id':-1}]
				else:
					# not allowed to invite users (e.g. isn't a member of the mehfil)
					return [{'id':-2}]
			else:
				# no group found
				return [{'id':-3}]


	def get_context_data(self, **kwargs):
		context = super(InviteUsersToPrivateGroupView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			unique = self.request.session.get("unique_id",None)
			context["unique"] = unique
			marker = context["object_list"][0]['id']
			if marker < 0:
				# cannot invite users
				context["group"] = False
				if marker == -1:
					# no one online
					context["no_online"] = True
				elif marker == -2:
					# not allowed to invite users
					context["cant_invite"] = True
				elif marker == -3:
					# group not found
					context["no_group"] = True
				elif marker == -4:
					# user is banned
					context["banned"] = True
			else:
				# can invite
				own_id = self.request.user.id
				group_topic = retrieve_group_topic(group_uuid=unique,requestor_id=own_id)
				if group_topic:
					show_instr, instr_type = show_private_group_invite_instructions(unique,own_id)
					if instr_type:
						context["show_instr"] = show_instr
						if show_instr:
							context["max_invites"] = MAX_OWNER_INVITES_PER_PRIVATE_GROUP if instr_type == 'owner' else MAX_MEMBER_INVITES_PER_PRIVATE_GROUP
							context["one_less"] = context["max_invites"] - 1
							context["instr_type"] = instr_type
						else:
							invites_remaining = retrieve_closed_group_remaining_invites(unique,user_type=instr_type,inviter_id=own_id)
							if invites_remaining == -1:
								# this is a general error
								context["cant_invite"] = True
								context["group"] = False
							elif invites_remaining == 0:
								context["invites_remaining"] = 0
								context["no_more_invites"] = True
							else:
								context["invites_remaining"] = invites_remaining
						context["private_max_members"] = PRIVATE_GROUP_MAX_MEMBERSHIP
						context["group_topic"] = group_topic
						context["legit"] = FEMALES
						context["group"] = True
					else:
						context["cant_invite"] = True
						context["group"] = False
				else:
					context["no_group"] = True
					context["group"] = False
		return context	

	
	# def get_context_data(self, **kwargs):
	# 	context = super(InviteUsersToPrivateGroupView, self).get_context_data(**kwargs)
	# 	if self.request.user.is_authenticated():
	# 		unique = self.request.session.get("unique_id",None)
	# 		context["unique"] = unique
	# 		marker = context["object_list"][0]['id']
	# 		if marker < 0:
	# 			# cannot invite users
	# 			context["group"] = False
	# 			if marker == -1:
	# 				# no one online
	# 				context["no_online"] = True
	# 			elif marker == -2:
	# 				# not allowed to invite users
	# 				context["cant_invite"] = True
	# 			elif marker == -3:
	# 				# group not found
	# 				context["no_group"] = True
	# 			elif marker == -4:
	# 				# user is banned
	# 				context["banned"] = True
	# 		else:
	# 			# can invite
	# 			own_id = self.request.user.id
	# 			group_topic = retrieve_group_topic(group_uuid=unique,requestor_id=own_id)
	# 			if group_topic:
	# 				show_instr, instr_type = show_private_group_invite_instructions(unique,own_id)
	# 				if instr_type:
	# 					context["show_instr"] = show_instr
	# 					if show_instr:
	# 						context["max_invites"] = MAX_OWNER_INVITES_PER_PRIVATE_GROUP if instr_type == 'owner' else MAX_MEMBER_INVITES_PER_PRIVATE_GROUP
	# 						context["one_less"] = context["max_invites"] - 1
	# 						context["instr_type"] = instr_type
	# 					else:
	# 						invites_remaining = retrieve_closed_group_remaining_invites(unique,user_type=instr_type)
	# 						if invites_remaining == -1:
	# 							# this is a general error
	# 							context["cant_invite"] = True
	# 							context["group"] = False
	# 						elif invites_remaining == 0:
	# 							context["invites_remaining"] = 0
	# 							context["no_more_invites"] = True
	# 						else:
	# 							context["invites_remaining"] = invites_remaining
	# 					context["private_max_members"] = PRIVATE_GROUP_MAX_MEMBERSHIP
	# 					context["group_topic"] = group_topic
	# 					context["legit"] = FEMALES
	# 					context["group"] = True
	# 				else:
	# 					context["cant_invite"] = True
	# 					context["group"] = False
	# 			else:
	# 				context["no_group"] = True
	# 				context["group"] = False
	# 	return context				


@csrf_protect
def private_group_invite_help(request):
	"""
	Renders invite instructions for private group handlers regarding invites
	"""
	if request.method == "POST":
		unique = request.POST.get("guid",None)
		group_owner_id, group_id = retrieve_group_owner_id(group_uuid=unique,with_group_id=True)
		own_id = str(request.user.id)
		if group_member_exists(group_id, own_id):
			return render(request,'mehfil/private_group_invite_help.html',{'owner_max':MAX_OWNER_INVITES_PER_PRIVATE_GROUP,'guid':unique,\
				'member_max':MAX_MEMBER_INVITES_PER_PRIVATE_GROUP,'one_less_owner':MAX_OWNER_INVITES_PER_PRIVATE_GROUP-1,\
				'private_max_members': PRIVATE_GROUP_MAX_MEMBERSHIP})
		else:
			# not authorized to view this
			return redirect("group_page")
	else:
		# not a POST request
		return redirect("group_page")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def unaccepted_private_mehfil_invites(request):
	"""
	Renders a list of users who were invited to the private mehfil but never accepted the invite
	"""
	if request.method == "POST":
		unique = request.POST.get("guid",None)
		group_owner_id, group_id = retrieve_group_owner_id(group_uuid=unique,with_group_id=True)
		own_id = str(request.user.id)
		if group_member_exists(group_id, own_id):
			# show list of invited IDs who haven't yet accepted the invite, along with time of sending invite
			invites_and_times = retrieve_outstanding_invite_report(group_id)
			invited_ids = [invited_id for(invited_id,invite_time) in invites_and_times]#only IDs
			invited_data = retrieve_bulk_credentials(invited_ids, decode_unames=True)#returned data {int(user_id):{'uname':uname,'avurl':avurl}}
			final_data, time_now = [], time.time()
			for invite_id, invite_time in invites_and_times:
				invited_id = int(invite_id)
				can_cancel = (time_now - int(invite_time)) > CANCEL_INVITE_AFTER_TIME_PASSAGE
				final_data.append((invited_id,invited_data[invited_id]['uname'],invited_data[invited_id]['avurl'],invite_time, can_cancel))
			return render(request,'mehfil/closed_group_invited_list.html',{'guid':unique,'final_data':final_data,\
				'show_instr':tutorial_unseen(user_id=own_id, which_tut='23', renew_lease=True),'females':FEMALES})
		else:
			# not authorized to view this
			return redirect("group_page")
	else:
		# not a POST request
		return redirect("group_page")


@csrf_protect
def cancel_closed_group_invite(request):
	"""
	Cancels stale closed group invite (initiated by any group member)
	"""
	if request.method == "POST":
		unique = request.POST.get("guid",None)
		group_owner_id, group_id = retrieve_group_owner_id(group_uuid=unique,with_group_id=True)
		own_id = request.user.id
		if group_member_exists(group_id, own_id):
			# cancel invite
			target_user_id = request.POST.get("tgt",None)
			time_now = time.time()
			successful = cancel_invite(group_id, target_user_id, False, time_now)
			if successful:
				########## legacy redis 1 function ##########
				remove_group_invite(target_user_id, group_id)
				##### adding to administrative activity #####
				username_dictionary = retrieve_bulk_unames([own_id,target_user_id],decode=True)
				main_sentence = username_dictionary[own_id]+" ne "+username_dictionary[int(target_user_id)]+\
				" ka invite cancel kiya at {0}".format(exact_date(time_now))
				document_administrative_activity.delay(group_id, main_sentence, 'cancel_private_invite')
			# show list of invited IDs who haven't yet accepted the invite, along with time of sending invite
			invites_and_times = retrieve_outstanding_invite_report(group_id)
			invited_ids = [invited_id for(invited_id,invite_time) in invites_and_times]#only IDs
			invited_data = retrieve_bulk_credentials(invited_ids, decode_unames=True)#returned data {int(user_id):{'uname':uname,'avurl':avurl}}
			final_data, time_now = [], time_now
			for invite_id, invite_time in invites_and_times:
				invited_id = int(invite_id)
				can_cancel = (time_now - int(invite_time)) > CANCEL_INVITE_AFTER_TIME_PASSAGE
				final_data.append((invited_id,invited_data[invited_id]['uname'],invited_data[invited_id]['avurl'],invite_time, can_cancel))
			return render(request,'mehfil/closed_group_invited_list.html',{'guid':unique,'final_data':final_data,'females':FEMALES})
		else:
			# not authorized
			return redirect("group_page")
	else:
		# not a POST request
		return redirect("group_page")


class InviteUsersToGroupView(ListView):
	"""
	Inviting users to public mehfil
	"""
	template_name = "mehfil/invite_for_groups.html"
	paginate_by = 100
	
	def get_queryset(self):
		if self.request.user_banned:
			return [{'id':-4}]
		else:
			group_owner_id, group_id = retrieve_group_owner_id(group_uuid=self.request.session.get("public_uuid",None),with_group_id=True)
			if group_owner_id:
				own_id = str(self.request.user.id)
				allowed_to_invite = own_id == group_owner_id or is_group_officer(group_id,own_id)
				if allowed_to_invite:
					user_ids = get_most_recent_online_users()#cache_mem.get('online')
					# user_ids = [3,9, 11,22,33,44,55,66,77,88,99]
					if user_ids:
						users_purified = [pk for pk in user_ids if pk not in condemned]
						non_invited_online_ids = bulk_check_group_invite(users_purified, group_id)
						non_invited_non_member_online_ids = bulk_check_group_membership(non_invited_online_ids, group_id)
						user_data = retrieve_bulk_credentials(non_invited_non_member_online_ids, decode_unames=True)#returned data {int(user_id):{'uname':uname,'avurl':avurl}}
						if user_data:
							final_data = []#list of dictionaries
							for online_id in non_invited_non_member_online_ids:
								online_id = int(online_id)
								final_data.append({'id':online_id,'username':user_data[online_id]['uname'],'avurl':user_data[online_id]['avurl']})
							return final_data
						else:
							# no one online
							return [{'id':-1}]
					else:
						# no one online
						return [{'id':-1}]
				else:
					# not allowed to invite users (e.g. is just a regular user, and not the mehfil owner or an officer)
					return [{'id':-2}]
			else:
				# no group found
				return [{'id':-3}]
			

	def get_context_data(self, **kwargs):
		context = super(InviteUsersToGroupView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			unique = self.request.session.get("public_uuid",None)
			context["unique"] = unique
			marker = context["object_list"][0]['id']
			if marker < 0:
				# cannot invite users
				context["group"] = False
				if marker == -1:
					# no one online
					context["no_online"] = True
				elif marker == -2:
					# not allowed to invite users
					context["cant_invite"] = True
				elif marker == -3:
					# group not found
					context["no_group"] = True
				elif marker == -4:
					# user is banned
					context["banned"] = True
			else:
				# can invite users
				own_id = self.request.user.id
				group_topic = retrieve_group_topic(group_uuid=unique,requestor_id=own_id)
				if group_topic:
					show_instr, instr_type = show_public_group_invite_instructions(unique,own_id)
					if instr_type:
						context["show_instr"] = show_instr
						if show_instr:
							context["max_invites"] = MAX_OWNER_INVITES_PER_PUBLIC_GROUP if instr_type == 'owner' else MAX_OFFICER_INVITES_PER_PUBLIC_GROUP
							context["one_less"] = context["max_invites"] - 1
							context["instr_type"] = instr_type
						else:
							invites_remaining = retrieve_open_group_remaining_invites(unique,user_type=instr_type)
							if invites_remaining == -1:
								context["cant_invite"] = True
								context["group"] = False
							elif invites_remaining == 0:
								context["invites_remaining"] = 0
								context["no_more_invites"] = True
							else:
								context["invites_remaining"] = invites_remaining
						context["group_topic"] = group_topic
						context["legit"] = FEMALES
						context["group"] = True
					else:
						context["cant_invite"] = True
						context["group"] = False
				else:
					context["no_group"] = True
					context["group"] = False
		return context


@csrf_protect
def public_group_invite_help(request):
	"""
	Renders invite instructions for public group handlers regarding invites
	"""
	if request.method == "POST":
		unique = request.POST.get("guid",None)
		group_owner_id, group_id = retrieve_group_owner_id(group_uuid=unique,with_group_id=True)
		own_id = str(request.user.id)
		if group_owner_id == own_id or is_group_officer(group_id, own_id):
			return render(request,'mehfil/public_group_invite_help.html',{'owner_max':MAX_OWNER_INVITES_PER_PUBLIC_GROUP,'guid':unique,\
				'officer_max':MAX_OFFICER_INVITES_PER_PUBLIC_GROUP,'one_less_owner':MAX_OWNER_INVITES_PER_PUBLIC_GROUP-1})
		else:
			# not authorized to view this
			return redirect("group_page")
	else:
		# not a POST request
		return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def unaccepted_public_mehfil_invites(request):
	"""
	Renders a list of users who were invited to the public mehfil but never accepted the invite
	"""
	if request.method == "POST":
		unique = request.POST.get("guid",None)
		group_owner_id, group_id = retrieve_group_owner_id(group_uuid=unique,with_group_id=True)
		own_id = str(request.user.id)
		is_owner = group_owner_id == own_id
		is_officer = is_group_officer(group_id, own_id)
		if is_owner or is_officer:
			# show list of invited IDs who haven't yet accepted the invite, along with time of sending invite
			invites_and_times = retrieve_outstanding_invite_report(group_id)
			invited_ids = [invited_id for(invited_id,invite_time) in invites_and_times]#only IDs
			invited_data = retrieve_bulk_credentials(invited_ids, decode_unames=True)#returned data {int(user_id):{'uname':uname,'avurl':avurl}}
			final_data, time_now = [], time.time()
			for invite_id, invite_time in invites_and_times:
				invited_id = int(invite_id)
				can_cancel = (time_now - int(invite_time)) > CANCEL_INVITE_AFTER_TIME_PASSAGE
				final_data.append((invited_id,invited_data[invited_id]['uname'],invited_data[invited_id]['avurl'],invite_time, can_cancel))
			return render(request,'mehfil/open_group_invited_list.html',{'owner':is_owner,'guid':unique,'final_data':final_data,\
				'show_instr':tutorial_unseen(user_id=own_id, which_tut='19', renew_lease=True),'females':FEMALES})
		else:
			# not authorized to view this
			return redirect("group_page")
	else:
		# not a POST request
		return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def cancel_open_group_invite(request):
	"""
	Cancels stale open group invite (initiated by group owner)
	"""
	if request.method == "POST":
		unique = request.POST.get("guid",None)
		group_owner_id, group_id = retrieve_group_owner_id(group_uuid=unique,with_group_id=True)
		own_id = request.user.id
		if group_owner_id == str(own_id):
			# cancel invite
			target_user_id = request.POST.get("tgt",None)
			time_now = time.time()
			successful = cancel_invite(group_id, target_user_id, True, time_now)
			if successful:
				########## legacy redis 1 function ##########
				remove_group_invite(target_user_id, group_id)
				##### adding to administrative activity #####
				username_dictionary = retrieve_bulk_unames([own_id,target_user_id],decode=True)
				main_sentence = username_dictionary[own_id]+" ne "+username_dictionary[int(target_user_id)]+\
				" ka invite cancel kiya at {0}".format(exact_date(time_now))
				document_administrative_activity.delay(group_id, main_sentence, 'cancel_public_invite')
			# show list of invited IDs who haven't yet accepted the invite, along with time of sending invite
			invites_and_times = retrieve_outstanding_invite_report(group_id)
			invited_ids = [invited_id for(invited_id,invite_time) in invites_and_times]#only IDs
			invited_data = retrieve_bulk_credentials(invited_ids, decode_unames=True)#returned data {int(user_id):{'uname':uname,'avurl':avurl}}
			final_data, time_now = [], time_now
			for invite_id, invite_time in invites_and_times:
				invited_id = int(invite_id)
				can_cancel = (time_now - int(invite_time)) > CANCEL_INVITE_AFTER_TIME_PASSAGE
				final_data.append((invited_id,invited_data[invited_id]['uname'],invited_data[invited_id]['avurl'],invite_time, can_cancel))
			return render(request,'mehfil/open_group_invited_list.html',{'owner':True,'guid':unique,'final_data':final_data,\
				'females':FEMALES})
		else:
			# not authorized
			return redirect("public_group")
	else:
		# not a POST request
		return redirect("public_group")


class ReinviteView(FormView):
	"""
	Renders error message if someone tries to 'double-invite' a user to a public mehfil

	Called from process_public_group_invite()
	"""
	form_class = ReinviteForm
	template_name = "mehfil/reinvite.html"

	def get_context_data(self, **kwargs):
		context = super(ReinviteView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			context["unique"] = self.kwargs.get("slug")
		return context

class ReinvitePrivateView(FormView):
	"""
	Renders error message if someone tries to 'double-invite' a user to a private mehfil

	Called from process_private_group_invite()
	"""
	form_class = ReinvitePrivateForm
	template_name = "mehfil/reinvite_private.html"

	def get_context_data(self, **kwargs):
		context = super(ReinvitePrivateView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			context["unique"] = self.request.session.get("unique_id",None)
		return context


def invite_private(request, slug=None, *args, **kwargs):
	"""
	A redirect to InviteUsersToPrivateGroupView()

	Is a legacy view and should be excised from the code, it's a superfluous redirect
	"""
	if valid_uuid(slug):
		request.session["unique_id"] = slug
		return redirect("invite_private_group")
	else:
		return redirect("group_page")


#################### Refreshing mehfils #####################


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def first_time_public_refresh(request):
	"""
	Using the refresh button for the first time in a public mehfil
	"""
	if request.method == "POST":
		unique = request.POST.get('uid',None)
		if tutorial_unseen(user_id=request.user.id, which_tut='14', renew_lease=True):
			return render(request, 'mehfil/public_mehfil_refresh.html', {'unique': unique})
		else:
			url = reverse_lazy("public_group", args=[unique])+"#sectionJ"
			return redirect(url)
	else:
		return redirect("public_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def first_time_refresh(request, unique=None, *args, **kwargs):
	"""
	Using the refresh button for the first time in a private mehfil
	"""
	if request.method == "POST":
		if tutorial_unseen(user_id=request.user.id, which_tut='14', renew_lease=True):
			return render(request, 'mehfil/mehfil_refresh.html', {'unique': unique})
		else:
			request.session["unique_id"] = unique
			url = reverse_lazy("private_group_reply")+"#sectionJ"
			return redirect(url)
	else:
		# ONCE MEHFIL IS ONLY ENTERED BY INVITED USERS, REMOVE THIS ERROR SO "GET" REQUESTS ARE NOT TOO FATAL
		raise Http404("Not a POST request")


########################## Mehfil Help #########################


class GroupHelpView(FormView):
	"""
	Renders the help page for mehfils
	"""
	form_class = GroupHelpForm
	template_name = "mehfil/group_help.html"

	def get_context_data(self, **kwargs):
		context = super(GroupHelpView, self).get_context_data(**kwargs)
		context["private_price"] = PRIVATE_GROUP_COST
		context["public_price"] = PUBLIC_GROUP_COST
		context["public_owner_invites"] = MAX_OWNER_INVITES_PER_PUBLIC_GROUP
		context["public_officer_invites"] = MAX_OFFICER_INVITES_PER_PUBLIC_GROUP
		context["private_max_members"] = PRIVATE_GROUP_MAX_MEMBERSHIP
		context["private_member_invites"] = MAX_MEMBER_INVITES_PER_PRIVATE_GROUP
		context["private_owner_invites"] = MAX_OWNER_INVITES_PER_PRIVATE_GROUP
		return context


########################## Popular mehfil list #########################

def get_ranked_groups(request):
	"""
	Displays top public mehfils, sorted by 'stickiness'
	"""
	"""
	('5',12) does not exist in test_list (used for testing purposes)
	
	test_list = [('12',12),('54',11),('78',54),('11',12),('53',11),('77',54),('13',12),('55',11),('79',54),\
	('4',12),('56',11),('80',54),('5',12),('50',11),('81',54),('2',12),('44',11),('72',54),('1',12),('45',11)\
	,('10',54),('34',12),('35',11),('36',54),('39',54),('37',12),('38',11)]
	
	group_ids_list = test_list
	"""
	groups_data = retrieve_cached_ranked_groups()
	if groups_data:
		trending_groups = json.loads(groups_data)
	else:
		trending_groups = []
		group_ids_list = get_ranked_public_groups()#get_ranked_mehfils()
		group_ids_dict = dict(group_ids_list)
		group_ids = map(itemgetter(0), group_ids_list)
		groups = retrieve_group_owner_unames_and_uniques_and_topics_in_bulk(group_ids)
		for group in groups:
			if group['oun']:
				group_id = group['gi']
				trending_groups.append((group['oun'],group['tp'],group['u'],group_id,group_ids_dict[group_id]))#group_ids_dict[group_id] is group_score
		trending_groups.sort(key=itemgetter(4), reverse=True)
		cache_ranked_groups(json.dumps(trending_groups))
	return render(request,"mehfil/group_ranking.html",{'object_list':trending_groups})

########################## Mehfil creation #########################


class GroupTypeView(FormView):
	"""
	Renders a 'choice' form when user tries to create a mehfil from the group page
	"""
	form_class = GroupTypeForm
	template_name = "mehfil/group_type.html"


class OpenGroupHelpView(FormView):
	"""
	Renders form where user has to decide whether they are willing to pay the required price
	"""
	form_class = OpenGroupHelpForm
	template_name = "mehfil/open_group_help.html"

	def get_context_data(self, **kwargs):
		context = super(OpenGroupHelpView, self).get_context_data(**kwargs)
		own_id = self.request.user.id
		context["public_price"] = PUBLIC_GROUP_COST
		try:
			join_date = User.objects.only('date_joined').get(id=own_id).date_joined
		except User.DoesNotExist:
			# this user does not exist thus data incomplete
			context["invalid_user"] = True
			return context
		ttl = USER_AGE_AFTER_WHICH_PUBLIC_MEHFIL_CAN_BE_CREATED - (time.time() - convert_to_epoch(join_date))
		if ttl > 4:
			# this user isn't allowed to create a group
			context["user_age_inadequate"] = True
			context["age_inadequate_ttl"] = ttl
		return context


class ClosedGroupHelpView(FormView):
	"""
	Renders form where user has to decide whether they are willing to pay the required price
	"""
	form_class = ClosedGroupHelpForm
	template_name = "mehfil/closed_group_help.html"

	def get_context_data(self, **kwargs):
		context = super(ClosedGroupHelpView, self).get_context_data(**kwargs)
		context["private_price"] = PRIVATE_GROUP_COST
		return context


def direct_message(request, pk=None, *args, **kwargs):
	"""
	Assists in calling private mehfil creation directly from user's profile
	"""
	if pk.isdigit():
		request.session["dm"] = pk
		return redirect("direct_message_help")
	else:
		return redirect("group")


class DirectMessageView(FormView):
	"""
	Renders form where user has to decide whether they are willing to pay the required price

	Same as ClosedGroupHelpView(), except this is sourced directly from user's profile
	"""
	form_class = DirectMessageForm
	template_name = "mehfil/direct_message_help.html"

	def get_context_data(self, **kwargs):
		context = super(DirectMessageView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			context["nopk"] = False
			context["private_price"] = PRIVATE_GROUP_COST
			pk = self.request.session.pop("dm",None)
			if pk:
				target = User.objects.get(id=pk)
				context["target"] = target
			else:
				context["nopk"] = True
		return context


class DirectMessageCreateView(FormView):
	"""
	Validates and creates private mehfil when request generated straight from a target user's profile
	"""
	form_class = DirectMessageCreateForm

	def form_valid(self, form):
		if self.request.method == 'POST':
			pk = self.kwargs["pk"]# invitee's primary key
			invitee = retrieve_uname(pk,decode=True)
			if invitee:
				own_id = self.request.user.id
				own_score = self.request.user.userprofile.score
				if not self.request.mobile_verified:
					return render(self.request,"verification/unable_to_submit_without_verifying.html",{'create_private_mehfil':True})
				elif own_score >= PRIVATE_GROUP_COST:
					ttl = is_group_creation_rate_limited(own_id, which_group='private')
					if ttl:
						self.request.session["mehfil_creation_rate_limited"] = ttl
						self.request.session.modified = True
						return redirect("user_profile", invitee)
					else:
						topic, unique = invitee+" se gupshup", uuid.uuid4()
						group = Group.objects.create(topic=topic, rules='', owner_id=own_id, private ='1', unique=unique)
						group_id, created_at = group.id, convert_to_epoch(group.created_at)
						reply = Reply.objects.create(text=invitee, category='1', which_group_id=group_id, writer_id=own_id)
						UserProfile.objects.filter(user_id=own_id).update(score=F('score')-PRIVATE_GROUP_COST)
						reply_time = convert_to_epoch(reply.submitted_on)
						own_uname, own_avurl = retrieve_credentials(own_id,decode_uname=True)
						###################
						create_group_credentials(owner_id=own_id, owner_uname=own_uname, owner_join_time=None, group_id=group_id,privacy='1',uuid=unique,\
							topic=topic,pics='1',created_at=created_at, grp_categ='1')#grp_categ is set to '1', '2' being a group only pink stars can join
						save_group_submission(writer_id=own_id, group_id=group_id, text=invitee, posting_time=reply_time,category='1',\
							writer_avurl=get_s3_object(own_avurl,category='thumb'),writer_score=(own_score - PRIVATE_GROUP_COST),\
							writer_uname=own_uname,save_latest_submission=True)
						group_attendance_tasks.delay(group_id=group_id, user_id=own_id, time_now=reply_time)#, private=True)
						main_sentence = own_uname+" ne mehfil create ki at {0}".format(exact_date(reply_time))
						document_administrative_activity.delay(group_id, main_sentence, 'create')
						###################
						add_group_member(group_id, own_uname)
						add_group_invite(pk, group_id,reply.id)
						add_user_group(own_id, group_id)
						group_notification_tasks.delay(group_id=group_id,sender_id=own_id,group_owner_id=own_id,topic=topic,reply_time=reply_time,\
							poster_url=own_avurl,poster_username=own_uname,reply_text=invitee,priv='1',slug=str(unique),image_url=None,\
							priority='priv_mehfil',from_unseen=False,reply_id=reply.id)
						rate_limit_group_creation(own_id, which_group='private')
						invalidate_cached_mehfil_pages(own_id)
						self.request.session["unique_id"] = unique
						return redirect("private_group_reply")
				else:
					return redirect("profile",slug=invitee)
			else:
				# invitee doesn't exist
				return redirect("home")


class ClosedGroupCreateView(CreateView):
	"""
	Resposible for rendering and validating private mehfil creation form. Also creates the private mehfil.
	"""
	model = Group
	form_class = ClosedGroupCreateForm
	template_name = "mehfil/create_new_closed_group.html"

	def get_form_kwargs(self):
		kwargs = super(ClosedGroupCreateView,self).get_form_kwargs()
		kwargs['score'] = self.request.user.userprofile.score
		return kwargs

	def get_context_data(self, **kwargs):
		context = super(ClosedGroupCreateView, self).get_context_data(**kwargs)
		context["topic_char_limit"] = PRIVATE_GROUP_MAX_TITLE_SIZE
		return context

	def form_valid(self, form):
		if not self.request.mobile_verified:
			return render(self.request,"verification/unable_to_submit_without_verifying.html",{'create_private_mehfil':True})
		elif self.request.user.userprofile.score >= PRIVATE_GROUP_COST:
			user_id = self.request.user.id
			ttl = is_group_creation_rate_limited(user_id, which_group='private')
			if ttl:
				return render(self.request,"mehfil/group_type.html",{'ttl':ttl})
			else:
				f = form.save(commit=False) #getting form object, and telling database not to save (commit) it just yet
				user = self.request.user
				f.owner_id = user_id
				f.private = 1
				unique = uuid.uuid4()
				f.unique = unique
				f.rules = ''
				f.category = '1'
				f.save()#creating private mehfil
				created_at = convert_to_epoch(f.created_at)
				creation_text = 'meri new mehfil mein welcome'
				reply = Reply.objects.create(text=creation_text,which_group=f,writer_id=user_id)
				# subtract cost of private mehfil
				UserProfile.objects.filter(user_id=user_id).update(score=F('score')-PRIVATE_GROUP_COST)
				reply_time = convert_to_epoch(reply.submitted_on)
				own_uname, own_avurl = retrieve_credentials(user_id,decode_uname=True)
				####################
				create_group_credentials(owner_id=user_id, owner_uname=own_uname,owner_join_time=None, group_id=f.id,privacy='1',uuid=f.unique,\
					topic=f.topic,pics='1',created_at=created_at, grp_categ='1')
				save_group_submission(writer_id=user_id, group_id=f.id, text=creation_text, posting_time=reply_time,category='0',\
					writer_avurl=get_s3_object(own_avurl,category='thumb'),writer_score=self.request.user.userprofile.score,\
					writer_uname=own_uname, save_latest_submission=True)
				group_attendance_tasks.delay(group_id=f.id, user_id=user_id, time_now=reply_time)#, private=True)
				main_sentence = own_uname+" ne mehfil create ki at {0}".format(exact_date(reply_time))
				document_administrative_activity.delay(f.id, main_sentence, 'create')
				invalidate_cached_mehfil_pages(user_id)
				####################
				add_group_member(f.id, own_uname)
				add_user_group(user_id, f.id)
				group_notification_tasks.delay(group_id=f.id,sender_id=user_id,group_owner_id=user_id,topic=f.topic,reply_time=reply_time,\
					poster_url=own_avurl,poster_username=own_uname,reply_text=creation_text,priv='1',slug=str(f.unique),image_url=None,\
					priority='priv_mehfil',from_unseen=False,reply_id=reply.id)
				# rate limit further public mehfil creation by this user (for 1 day)
				rate_limit_group_creation(user_id, which_group='private')
				self.request.session["unique_id"] = f.unique
				return redirect("invite_private", slug=f.unique)
		else:
			return render(self.request,"mehfil/group_type.html",{'score_inadequate':True})


@csrf_protect
def create_open_group(request):
	"""
	Creating open group after successful validation/submission in preview_open_group()
	"""
	if request.method == "POST":
		own_id = request.user.id
		decision = request.POST.get("dec",None)
		if decision == '0':
			return redirect("group_type")
		elif decision == '1':
			# re-enter the credentials
			data = get_temporarily_saved_group_credentials(own_id,only_raw=True)
			if data:
				form = OpenGroupCreateForm(initial=data)# prepopulating the form with user's data (but not calling validation on it)
				return render(request,"mehfil/create_new_open_group_or_rejoin.html",{'form':form,'is_female':retrieve_uname(own_id,decode=True) in FEMALES,\
					'topic_char_limit':PUBLIC_GROUP_MAX_TITLE_SIZE,'rules_char_limit':PUBLIC_GROUP_MAX_RULES_SIZE})
			else:
				# the data does not exist any more (expired)
				form = OpenGroupCreateForm()
				return render(request,"mehfil/create_new_open_group_or_rejoin.html",{'form':form,'is_female':retrieve_uname(own_id,decode=True) in FEMALES,\
					'data_expired':True,'topic_char_limit':PUBLIC_GROUP_MAX_TITLE_SIZE,'rules_char_limit':PUBLIC_GROUP_MAX_RULES_SIZE})
		elif decision == '2':
			# create the group
			ttl = is_group_creation_rate_limited(own_id, which_group='public')
			if ttl:
				return render(request,"mehfil/group_type.html",{'ttl':ttl})
			else:
				# us user old enough to create a public mehfil?
				try:
					join_date = User.objects.only('date_joined').get(id=own_id).date_joined
				except User.DoesNotExist:
					# this user does not exist thus data incomplete
					return redirect("home")
				ttl = USER_AGE_AFTER_WHICH_PUBLIC_MEHFIL_CAN_BE_CREATED - (time.time() - convert_to_epoch(join_date))
				if ttl > 4:
					# this user isn't allowed to create a group
					return render(request,"mehfil/group_type.html",{'user_age_inadequate':True,'age_inadequate_ttl':ttl})
				else:
					data = get_temporarily_saved_group_credentials(own_id)
					score = request.user.userprofile.score
					if data and score >= PUBLIC_GROUP_COST:
						unique = uuid.uuid4()
						creation_text = 'meri public mehfil mein welcome'
						topic, rules, group_category, raw_rules = data['topic'], data['formatted_rules'], data["category"], data['rules']
						group = Group.objects.create(topic=topic, rules=rules, owner_id=own_id, private=0, category=group_category,unique=unique, \
							pics_ki_ijazat=1)
						group_id = group.id
						unique_id = group.unique
						created_at = convert_to_epoch(group.created_at)
						reply = Reply.objects.create(text=creation_text,which_group_id=group_id,writer_id=own_id)# to ensure group shows up in grouppageview()
						# subtract cost of public mehfil
						UserProfile.objects.filter(user_id=own_id).update(score=F('score')-PUBLIC_GROUP_COST)
						reply_time = convert_to_epoch(reply.submitted_on)
						own_uname, own_avurl = retrieve_credentials(own_id,decode_uname=True)
						########### legacy redis 1 functions ###########
						add_group_member(group_id, own_uname)
						add_user_group(own_id, group_id)
						################################################
						try:
							join_date = convert_to_epoch(User.objects.only('date_joined').get(id=own_id).date_joined)
						except User.DoesNotExist:
							# this user does not exist thus data incomplete
							join_date = None
						create_group_credentials(owner_id=own_id, owner_uname=own_uname, owner_join_time=join_date, group_id=group_id,privacy='0',\
							uuid=unique_id,topic=topic,pics='1',created_at=created_at, grp_categ=group_category,rules=rules, raw_rules=raw_rules)
						# writer_score is request.user.userprofile.score, to reflect the PUBLIC_GROUP_COST that was recently subtracted from score
						save_group_submission(writer_id=own_id, group_id=group_id, text=creation_text, posting_time=reply_time,category='0',\
							writer_avurl=get_s3_object(own_avurl,category='thumb'),writer_score=request.user.userprofile.score,writer_uname=own_uname,\
							save_latest_submission=True)
						main_sentence = own_uname+" ne mehfil create ki at {0}".format(exact_date(reply_time))
						document_administrative_activity.delay(group_id, main_sentence, 'create')
						################################################
						group_notification_tasks.delay(group_id=group_id,sender_id=own_id,group_owner_id=own_id,topic=topic,reply_time=reply_time,\
							poster_url=own_avurl,poster_username=own_uname,reply_text=creation_text,priv='0',slug=str(unique_id),image_url=None,\
							priority='public_mehfil',from_unseen=False, reply_id=reply.id)
						rank_public_groups.delay(group_id=group_id,writer_id=own_id)# legacy ranking redis3 function - please revert
						group_attendance_tasks.delay(group_id=group_id, user_id=own_id, time_now=reply_time)
						# rate limit further public mehfil creation by this user (for 1 day)
						rate_limit_group_creation(own_id, which_group='public')
						# go to newly created public mehfil's invite page
						request.session["public_uuid"] = unique_id
						request.session.modified = True
						return redirect("invite")
					elif score < PUBLIC_GROUP_COST:
						return render(request,"mehfil/group_type.html",{'score_inadequate':True})
					else:
						# data has expired, tell the person to redo
						form = OpenGroupCreateForm()
						return render(request,"mehfil/create_new_open_group_or_rejoin.html",{'form':form,'is_female':retrieve_uname(own_id,decode=True) in FEMALES,\
							'data_expired':True,'topic_char_limit':PUBLIC_GROUP_MAX_TITLE_SIZE,'rules_char_limit':PUBLIC_GROUP_MAX_RULES_SIZE})
		else:
			# the 'dec' option is not recognized
			return redirect("missing")	
	else:
		return redirect("missing")


@csrf_protect
def preview_open_group(request):
	"""
	Renders, validates and submits open group creation form
	"""
	if request.user_banned:
		return redirect("error")
	else:
		own_id = request.user.id
		if request.method == "POST":
			form = OpenGroupCreateForm(data=request.POST,verified=request.mobile_verified, score=request.user.userprofile.score)
			if form.is_valid():
				topic = form.cleaned_data.get("topic")
				formatted_rules, rules = form.cleaned_data.get("rules")
				category = form.cleaned_data.get("category")
				temporarily_save_group_credentials(own_id, topic, rules, formatted_rules, category)
				return render(request,"mehfil/new_open_group_preview.html",{'topic':topic,'rules':formatted_rules,'category':category})
			else:
				return render(request,"mehfil/create_new_open_group_or_rejoin.html",{'form':form,'is_female':retrieve_uname(own_id,decode=True) in FEMALES,\
					'topic_char_limit':PUBLIC_GROUP_MAX_TITLE_SIZE,'rules_char_limit':PUBLIC_GROUP_MAX_RULES_SIZE})
		else:
			form = OpenGroupCreateForm()
			return render(request,"mehfil/create_new_open_group_or_rejoin.html",{'form':form,'is_female':retrieve_uname(own_id,decode=True) in FEMALES,\
				'topic_char_limit':PUBLIC_GROUP_MAX_TITLE_SIZE,'rules_char_limit':PUBLIC_GROUP_MAX_RULES_SIZE})