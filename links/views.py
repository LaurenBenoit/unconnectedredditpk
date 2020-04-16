# coding=utf-8
from pytz import timezone
from math import log, ceil
import ujson as json
from urllib import quote
from collections import OrderedDict, defaultdict
from operator import attrgetter,itemgetter
import time, datetime
from datetime import datetime, timedelta
import re, urlmarker, StringIO, urlparse, random, string, uuid, pytz, ast
from target_urls import call_aasan_api
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.utils.decorators import method_decorator
from django.middleware import csrf
from django.core.files.uploadedfile import InMemoryUploadedFile
from scraper import read_image
from cricket_score import cricket_scr
from colors import COLOR_GRADIENTS
from page_controls import MAX_ITEMS_PER_PAGE, ITEMS_PER_PAGE, PHOTOS_PER_PAGE, FANS_PER_PAGE, STARS_PER_PAGE, PERSONAL_GROUP_IMG_WIDTH
from score import PUBLIC_GROUP_MESSAGE, PRIVATE_GROUP_MESSAGE, PUBLICREPLY, UPLOAD_PHOTO_REQ, VOTING_DRIVEN_CENSORSHIP, VOTING_DRIVEN_PIXELATION, \
NUM_SUBMISSION_ALLWD_PER_DAY, TRENDER_RANKS_TO_COUNT, ZODIAC, MAX_HOME_REPLY_SIZE, PREFIX_TEXT_LENGTH, LONG_LIVED_POST_TIME, SHORT_LIVED_POST_TIME,\
SEGMENT_STARTING_USER_ID
from django.core.cache import get_cache, cache
from django.views.decorators.csrf import csrf_protect
from django.db.models import Max, Count, Q, Sum, F
from verified import FEMALES
from django.views.decorators.debug import sensitive_post_parameters
from emoticons.settings import EMOTICONS_LIST
from namaz_timings import namaz_timings, streak_alive
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView, DetailView
from django.contrib.auth import get_user_model, authenticate, update_session_auth_hash
from django.contrib.auth import login as quick_login
from django.contrib.auth.models import User
from django.views.generic.edit import UpdateView, CreateView, DeleteView, FormView
from templatetags.s3 import get_s3_object
from templatetags.human_time import human_time
from image_processing import process_public_image, clean_image_file
from salutations import SALUTATIONS
from forms import UserProfileForm, PhotoScoreForm, FacesPagesForm, UploadPhotoForm, ContactForm, AboutForm, PrivacyPolicyForm, PhotoHelpForm, \
EmoticonsHelpForm, LinkForm, WelcomeMessageForm, LogoutHelpForm, LogoutPenaltyForm, SearchNicknameForm, UserProfileDetailForm, RegisterLoginForm, \
HistoryHelpForm, UserSettingsForm, HelpForm, RegisterHelpForm, VerifyHelpForm, ResetPasswordForm, WelcomeForm, PhotoShareForm, FacesHelpForm, ReauthForm
from django.core.urlresolvers import reverse_lazy, reverse
from django.shortcuts import redirect, get_object_or_404, render
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponsePermanentRedirect
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
#from django.utils import timezone
from django.utils.timezone import utc
from django.views.decorators.cache import cache_page, never_cache, cache_control
from brake.decorators import ratelimit
from tasks import hide_associated_direct_responses, log_404, group_attendance_tasks, publicreply_tasks, post_to_followers, \
publicreply_notification_tasks, log_user_activity, set_input_rate_and_history
from models import Link, Cooldown, PhotoStream, TutorialFlag, PhotoVote, Photo, PhotoComment, PhotoCooldown, ChatInbox, \
UserProfile, UserSettings, Publicreply, HellBanList, HotUser, UserFan, Salat, Logout
from redis4 import get_clones, set_photo_upload_key, get_and_delete_photo_upload_key, set_text_input_key, invalidate_avurl, \
retrieve_user_id, get_most_recent_online_users, retrieve_uname, retrieve_credentials, cache_image_count,cache_online_data,\
retrieve_online_cached_data, rate_limit_content_sharing, content_sharing_rate_limited, retrieve_avurl, get_cached_photo_dim, \
cache_photo_dim, retrieve_bulk_unames, set_attribute_change_rate_limit,retrieve_image_count, add_to_hell, add_to_hell_ban_in_bulk,\
is_user_hell_banned, remove_from_hell#, log_public_img
from redis3 import insert_nick_list, get_nick_likeness, find_nickname, get_search_history, set_user_choice, get_banned_users_count,\
log_text_submissions, del_search_history, tutorial_unseen, is_mobile_verified, get_temp_id, save_advertiser, get_advertisers, \
purge_advertisers, get_gibberish_punishment_amount, export_advertisers, temporarily_save_user_csrf, is_already_banned, \
log_pagination_button_click # log_erroneous_passwords
from redisads import get_user_loc, get_ad, store_click, get_user_ads, suspend_ad
from website_feedback_form import AdvertiseWithUsForm
from redirection_views import return_to_content
from redis6 import invalidate_cached_mehfil_replies, save_group_submission, retrieve_latest_user_owned_mehfils, group_member_exists, \
retrieve_group_reqd_data# invalidate_cached_mehfil_pages
from redis7 import add_text_post, get_home_feed, retrieve_obj_feed, get_best_photo_feed, get_photo_feed, retrieve_recent_votes,\
add_image_post, insert_hash, is_fbs_user_rate_limited_from_photo_upload, in_defenders, retrieve_photo_feed_index,retrieve_top_trenders,\
rate_limit_fbs_public_photo_uploaders, check_content_and_voting_ban, get_temp_post_data, get_all_image_star_ids, get_best_home_feed,\
invalidate_cached_public_replies, retrieve_cached_public_replies, cache_public_replies,retrieve_home_feed_index, retrieve_best_home_feed_index,\
retrieve_trending_photo_ids, retrieve_num_trending_photos, retrieve_subscribed_topics, retrieve_photo_feed_latest_mod_time, add_topic_post, \
get_recent_trending_photos, cache_recent_trending_images, get_cached_recent_trending_images, retrieve_last_vote_time, retreive_trending_rep, \
is_image_star, log_recent_text,set_temp_post_data, retrieve_fresh_image_count, save_recent_photo, retrieve_trenders_by_score
from redis2 import filter_following, check_if_follower, get_verified_follower_count, followers_exist, get_following_count, retrieve_follower_data, \
fan_out_to_followers, can_follower_view_post, invalidate_cached_user_feed_history, get_last_post_selected_followers, get_all_follower_count#, logging_post_data
from utilities import beautiful_date, convert_to_epoch, image_description_generator
from redis9 import retrieve_latest_direct_reply, get_last_comment_time
from redis8 import retrieve_variation_subset, set_tutorial_seen
from direct_response_forms import DirectResponseForm
from cities import CITY_TUP_LIST, REV_CITY_DICT
from imagestorage import upload_image_to_s3

# from optimizely_config_manager import OptimizelyConfigManager
# from unconnectedreddit.optimizely_settings import PID

# config_manager = OptimizelyConfigManager(PID)

condemned = HellBanList.objects.values_list('condemned_id', flat=True).distinct()


def retrieve_user_env(opera_mini, fbs):
	"""
	Does the user's environment support JS?

	Opera mini (extreme mode) and free basics do not support JS
	"""
	if fbs:
		return False# does NOT support JS
	elif opera_mini:
		return False# does NOT support JS
	else:
		return True# supports JS


def secs_to_mins(seconds):
	try:
		m, s = divmod(seconds, 60)
		h, m = divmod(m, 60)
		d, h = divmod(h, 24)
		mo, d = divmod(d, 30)
		if mo:
			if mo == 1:
				return "1 month"
			else:
				return "{} months".format(mo)
		elif d:
			if d == 1:
				return "1 day"
			else:
				return "{} days".format(d)
		elif h:
			if h == 1:
				return "1 hour"
			else:
				return "{} hours".format(h)
		elif m:
			if m == 1:
				return "1 min"
			else:
				return "{} mins".format(m)
		elif s:
			if s == 1:
				return "1 sec"
			else:
				return "{} secs".format(s)
		else:
			return ""
	except (NameError,TypeError):
		return ""


def set_rank():
	epoch = datetime(1970, 1, 1).replace(tzinfo=None)
	netvotes = 0
	order = log(max(abs(netvotes), 1), 10) #0.041392685 for zero votes, log 1 = 0
	sign = 1 if netvotes > 0 else -1 if netvotes < 0 else 0
	unaware_submission = datetime.utcnow().replace(tzinfo=None)
	td = unaware_submission - epoch 
	epoch_submission = td.days * 86400 + td.seconds + (float(td.microseconds) / 1000000) #number of seconds from epoch till date of submission
	secs = epoch_submission - 1432201843 #a recent date, coverted to epoch time
	invisible_score = round(sign * order + secs / 45000, 8)
	return invisible_score


def get_indices(page_number, obj_allotment):
	"""
	When fed a page_number, returns a start_index and end_index
	"""
	try:
		page_number = int(page_number)
	except (ValueError,TypeError):
		return 0,obj_allotment-1
	objs_per_page = obj_allotment
	index_ceiling = objs_per_page * page_number
	return (index_ceiling)-objs_per_page,index_ceiling-1


def break_text_into_prefix_and_postfix(target_text):
	"""
	Does a reasonable effort at breaking the string along 'space' character
	"""
	# This line turns a typical string into "unicode" string. "non-ascii" chars can sometimes crash without this line (esp in open/closed mehfils)
	target_text = target_text if isinstance(target_text,unicode) else unicode(target_text, "utf-8")
	######################
	if len(target_text) <= PREFIX_TEXT_LENGTH:
		return target_text, ''
	else:
		broken = False
		# go backward from 43rd char and break when the first space is encountered
		for z in xrange(PREFIX_TEXT_LENGTH, 0, -1):
			if target_text[z].isspace():
				# break at this point
				broken = True
				break
			else:
				# break at PREFIX_TEXT_LENGTH
				pass
		if broken:
			prefix, postfix = target_text[:z], target_text[z:].strip()
		else:
			# it is a continual string!
			prefix, postfix = target_text[:PREFIX_TEXT_LENGTH], target_text[PREFIX_TEXT_LENGTH:]
		return prefix, postfix


def create_sorted_invitee_list(username_data, user_ids):
	"""
	Prepares list of alphabetically sorted names (it's a mis-labeled function, inviting is only one of its responsibilities)

	This list is available to:
	- site-wide online listing
	- group inviters (both public and private)
	- posting to specific followers
	"""
	user_alpha_data = []#nicks starting with an alpha character
	user_digital_data = []#nicks starting with a digital character
	for online_id in user_ids:
		username = username_data[int(online_id)]
		username_lower = username.lower()
		if username[0].isalpha():
			user_alpha_data.append((online_id,username,username_lower))
		else:
			user_digital_data.append((online_id,username,username_lower))
	user_digital_data.sort(key=itemgetter(2))
	user_alpha_data.sort(key=itemgetter(2))
	user_data = user_alpha_data + user_digital_data
	final_data, previous_lower_username_first_alphabet = [] , ''
	for id_, uname, uname_lower in user_data:
		first_alphabet = uname_lower[0]
		new_alphabet = first_alphabet.upper() if (first_alphabet!=previous_lower_username_first_alphabet) else None
		final_data.append((id_,uname,uname_lower,new_alphabet))
		previous_lower_username_first_alphabet = first_alphabet
	return final_data


def create_sorted_online_list(username_data, user_ids_and_ages):
	"""
	"""
	if username_data and user_ids_and_ages:
		user_alpha_data = defaultdict(list)#nicks starting with an alpha character
		user_nonalpha_data = defaultdict(list)#nicks starting with other character
		for user_id, user_age in user_ids_and_ages:
			username = username_data[int(user_id)]
			username_lower = username.lower()
			first_letter = username[0]
			# rig world age such that everyone has the 'same age' (equal to -1), except when they're really new!
			if first_letter.isalpha():
				user_alpha_data[first_letter.upper()].append((user_id,username,username_lower,user_age if user_age < 5 else -1))#,user_age))
			else:
				user_nonalpha_data[first_letter].append((user_id,username,username_lower,user_age if user_age < 5 else -1))#,user_age))
		#############################
		alpha_list = [(header,users) for (header,users) in user_alpha_data.iteritems()] if user_alpha_data else []
		nonalpha_list = [(header,users) for (header,users) in user_nonalpha_data.iteritems()] if user_nonalpha_data else []
		alpha_with_sorted_elems, nonalpha_with_sorted_elems, sorted_alpha, sorted_nonalpha = [], [], [], []
		if alpha_list:
			for header, elems in alpha_list:
				alpha_with_sorted_elems.append((header,sorted(elems, key=itemgetter(3,2))))
			sorted_alpha = sorted(alpha_with_sorted_elems, key=itemgetter(0))
		if nonalpha_list:
			for header, elems in nonalpha_list:
				nonalpha_with_sorted_elems.append((header,sorted(elems, key=itemgetter(3,2))))
			sorted_nonalpha = sorted(nonalpha_with_sorted_elems, key=itemgetter(0))
		return sorted_alpha + sorted_nonalpha
	else:
		return []


def get_page_obj(page_num,obj_list,items_per_page):
	"""
	Pass list of objects and number of objects to show per page, it does the rest
	"""
	paginator = Paginator(obj_list, items_per_page)
	try:
		return paginator.page(page_num)
	except PageNotAnInteger:
		# If page is not an integer, deliver first page.
		return paginator.page(1)
	except EmptyPage:
		# If page is out of range (e.g. 9999), deliver last page of results.
		return paginator.page(paginator.num_pages)


def get_addendum(index, objs_per_page, only_addendum=False):
	"""
	Creates the addendum to be attached as a URL parameter
	"""
	page = (index // objs_per_page)+1 #determining page number
	section = index+1-((page-1)*objs_per_page) #determining section numberhome_redirect
	addendum = '?page='+str(page)+"#section"+str(section) #forming url addendum
	if only_addendum:
		return addendum
	else:
		return page, addendum #returing page and addendum both


def get_price(points):
	"""
	Determines price of anything, in accordance to how many points a user has

	Every user can be taxed a different amount via this mechanism
	"""
	if points < 500:
		price = 400#we over-tax sybils
	elif 500 <= points < 10001:
		x=((((20**(1/2.0))-2)*points)/9880)+1.96997405723 #scaling x between 2 and sqrt(20)
		base = x**2 #squaring x
		price = (((points/base)+9)//10)*10 #roundup the number to nearest 10
	elif 10001 <= points < 500001:
		sqrt1 = 20**(1/2.0)
		sqrt2 = 70**(1/2.0)
		numerator = sqrt2 - sqrt1
		x=((numerator*points)/490000)+4.39265709152 #scaling between sqrt(20) and sqrt(70)
		base = x**2 #squaring x
		price = (((points/base)+9)//10)*10 #roundup the number to nearest 10
	else:
		base = 71
		price = (((points/base)+9)//10)*10 #roundup the number to nearest 10
	return int(price)


def valid_uuid(uuid):
	if not uuid:
		return False
	else:
		regex = re.compile('^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}\Z', re.I)
		match = regex.match(uuid)
		return bool(match)


def format_post_times(list_of_dictionaries, with_machine_readable_times=False):
	"""
	Injects human readable times in place of epoch times

	"""
	if with_machine_readable_times:
		for obj in list_of_dictionaries:
			epoch_time = obj['t']
			obj['t'] = human_time(epoch_time)
			obj['mt'] = beautiful_date(epoch_time,format_type='2')
	else:
		for obj in list_of_dictionaries:
			obj['t'] = human_time(obj['t'])
	return list_of_dictionaries


def csrf_failure(request, reason=""):
	context = {'referrer':request.META.get('HTTP_REFERER',None)}
	return render(request,"CSRF_failure.html", context)


class NeverCacheMixin(object):
	@method_decorator(never_cache)
	def dispatch(self, *args, **kwargs):
		return super(NeverCacheMixin, self).dispatch(*args, **kwargs)


class HistoryHelpView(FormView):
	form_class = HistoryHelpForm
	template_name = "history_help.html"

class PhotosHelpView(FormView):
	form_class = PhotoHelpForm
	template_name = "photos_help.html"

	def get_context_data(self, **kwargs):
		context = super(PhotosHelpView, self).get_context_data(**kwargs)
		context["unique"] = self.kwargs.get("slug")
		context["decision"] = self.kwargs.get("pk")
		return context


class RegisterLoginView(FormView):
	form_class = RegisterLoginForm
	template_name = "register_login.html"


def website_rules(request):
	"""
	Renders website rules
	"""
	################### Retention activity logging ###################
	user_id = request.user.id
	if user_id > SEGMENT_STARTING_USER_ID:
		time_now = time.time()
		act = 'Z2' if request.mobile_verified else 'Z2.u'
		activity_dict = {'m':'GET','act':act,'t':time_now}# defines what activity just took place
		log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
	##################################################################
	return render(request,"website_rules.html",{})


def more_options(request):
	"""
	Renders a page containing the following options:

	- Mehfils
	- Search
	- Online
	- Topics
	- About
	- Help
	- Logout
	"""
	return render(request,"more_options.html",{})


class ContactView(FormView):
	form_class = ContactForm
	template_name = "contact.html"


class AboutView(FormView):
	form_class = AboutForm
	template_name = "about.html"

	def get_context_data(self, **kwargs):
		context = super(AboutView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			# pass
			################### Retention activity logging ###################
			user_id = self.request.user.id
			if user_id > SEGMENT_STARTING_USER_ID:
				time_now = time.time()
				act = 'Z3' if self.request.mobile_verified else 'Z3.u'
				activity_dict = {'m':'GET','act':act,'t':time_now}# defines what activity just took place
				log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
			##################################################################
		return context

class PrivacyPolicyView(FormView):
	form_class = PrivacyPolicyForm
	template_name = "privacy_policy.html"


class HelpView(FormView):
	form_class = HelpForm
	template_name = "help.html"

	def get_context_data(self, **kwargs):
		context = super(HelpView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			# pass
			################### Retention activity logging ###################
			user_id = self.request.user.id
			if user_id > SEGMENT_STARTING_USER_ID:
				time_now = time.time()
				act = 'Z1' if self.request.mobile_verified else 'Z1.u'
				activity_dict = {'m':'GET','act':act,'t':time_now}# defines what activity just took place
				log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
			##################################################################
		return context

class VerifyHelpView(FormView):
	form_class = VerifyHelpForm
	template_name = "verify_help.html"  

class RegisterHelpView(FormView):
	form_class = RegisterHelpForm
	template_name = "register_help.html"


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@sensitive_post_parameters()
@csrf_protect
def logout_rules(request):
	if request.method == "POST":
		return render(request,"logout/logout_rules.html",{})
	else:
		return render(request,"logout/logout_tutorial.html",{})


class LogoutPenaltyView(FormView):
	form_class = LogoutPenaltyForm
	template_name = "logout_penalty.html"


def faces_pages(request, *args, **kwargs):
	form = FacesPagesForm()
	oblist = EMOTICONS_LIST
	page_num = request.GET.get('page', '1')
	page_obj = get_page_obj(page_num,oblist,16)
	context = {'object_list': oblist, 'form':form, 'page':page_obj}
	return render(request, 'faces_pages.html', context)

class FacesHelpView(FormView):
	form_class = FacesHelpForm
	template_name = "faces.html"

	def get_context_data(self, **kwargs):
		context = super(FacesHelpView, self).get_context_data(**kwargs)
		if self.request.is_feature_phone:
			context["is_feature_phone"] = True
		else:
			context["is_feature_phone"] = False
		return context

class EmoticonsHelpView(FormView):
	form_class = EmoticonsHelpForm
	template_name = "emoticons_help.html"

	def get_context_data(self, **kwargs):
		context = super(EmoticonsHelpView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			context["random"] = random.sample(xrange(1,188),15) #select 15 random emoticons out of 188
		return context

class LogoutHelpView(FormView):
	form_class = LogoutHelpForm
	template_name = "logout_help.html"


@csrf_protect
def hide_comment(request,comment_id,photo_id,origin,*args,**kwargs):
	"""
	Processing hiding a 'tabsra' of a photo post
	"""
	if request.method == "POST":
		slug = request.POST.get("slug",None)
		own_id = request.user.id

		if Publicreply.objects.filter(id=comment_id, answer_to_id=photo_id, abuse=False) and \
		Link.objects.filter(id=photo_id,submitter_id=own_id).exists():

			photocomment_obj = Publicreply.objects.only('submitted_by','direct_reply').get(id=comment_id)
			submitted_by_id = photocomment_obj.submitted_by_id

			# mark as abusive
			Publicreply.objects.filter(pk=comment_id).update(abuse=True)

			################################################
			# handle direct replies
			direct_reply_id = photocomment_obj.direct_reply_id
			if direct_reply_id:
				target_user_id = Publicreply.objects.only('submitted_by').get(id=direct_reply_id).submitted_by_id
			else:
				target_user_id = None if submitted_by_id == own_id else own_id# there's no target_user_id if response targeted at self (else self is the target)

			hide_associated_direct_responses.delay(obj_type='4',parent_obj_id=photo_id,reply_id=comment_id,\
				sender_id=submitted_by_id,receiver_id=target_user_id,to_hide=True)
			################################################
			
		# prepare to redirect
		# return redirect("comment", pk=photo_id, origin=origin)
		return return_to_content(request,origin='11',obj_id=photo_id,source_origin=origin)
	else:
		raise Http404("Not a POST request")



@csrf_protect
def hide_jawab(request,publicreply_id,link_id,origin,*args,**kwargs):
	"""
	Processing hiding a 'jawab' of a home post
	"""
	if request.method == "POST":
		own_id = request.user.id
		if Publicreply.objects.filter(pk=publicreply_id,answer_to_id=link_id,abuse=False).exists() and \
		Link.objects.filter(pk=link_id,submitter_id=own_id).exists():
			publicreply_obj = Publicreply.objects.only('submitted_by','direct_reply').get(id=publicreply_id)
			submitted_by_id = publicreply_obj.submitted_by_id

			# mark as abusive
			Publicreply.objects.filter(pk=publicreply_id).update(abuse=True)

			################################################
			# handle direct replies
			direct_reply_id = publicreply_obj.direct_reply_id
			if direct_reply_id:
				target_user_id = Publicreply.objects.only('submitted_by').get(id=direct_reply_id).submitted_by_id
			else:	
				target_user_id = None if submitted_by_id == own_id else own_id# there's no target_user_id if response targeted at self (else self is the target)

			hide_associated_direct_responses.delay(obj_type='3',parent_obj_id=link_id,reply_id=publicreply_id,\
				sender_id=submitted_by_id,receiver_id=target_user_id,to_hide=True)
			################################################

			# invalidate cached replies
			invalidate_cached_public_replies(link_id)
		
		# return redirect("publicreply_view",link_id)
		return return_to_content(request,origin='9',obj_id=link_id,source_origin=origin)
	else:
		raise Http404("Not a POST request - cannot hide publicreply")


def content_detail_view(request, pk, origin=None, obj_type=None):
	"""
	Handles all type of content detail view
	"""
	own_id = request.user.id
	context = {}

	# object type is 'image'
	if obj_type == 'g':

		try:
			obj = Link.objects.only('description','net_votes','image_file','id','delete_status','submitter','expire_at',\
				'audience','type_of_content','submitted_on','reply_count','comment_status','web_link').get(id=pk)

		except Link.DoesNotExist:
			context["absent"] = True
			return render(request,"content_detail.html",context)
		#################################################################

		submitter_id = obj.submitter_id
		post_attributes = {'delete_status':obj.delete_status,'type_of_content':obj_type,'expire_at':obj.expire_at,'audience':obj.audience,\
		'obj_hash':'img:'+pk, 'submitter_id':submitter_id}
		
		privacy_setting, viewable_flag = check_if_post_is_viewable(own_id,post_attributes)

		######################################################################

		if viewable_flag == '0':
			return redirect('private_or_expired')
		elif not own_id and viewable_flag in ('1','2'):
			# unauth user wants to view a post which is Google indexed but hidden ('1') or expired ('2'): show the image (without the uploader name)
			request.session['image_file'] = obj.image_file
			request.session['image_caption'] = obj.description
			request.session['alt_text'] = obj.web_link
			img_height, img_width = get_cached_photo_dim(pk)
			if not img_height:
				img_height, img_width = obj.image_file.height, obj.image_file.width
				cache_photo_dim(pk,img_height,img_width)
			img_hw_ratio = (1.0*int(img_width)/int(img_height))
			request.session["img_ratio"] = round((100.0/img_hw_ratio),2)
			return redirect("photo",list_type='best-list')
		else:
			# post is viewable ('3')
			on_fbs = request.META.get('HTTP_X_IORG_FBS',False)
			context = {'obj_id':pk, 'privacy_setting':privacy_setting, 'obj':obj, 'is_owner':False,'viewable_status':viewable_flag,\
			'on_fbs':on_fbs,'submitter_username':retrieve_uname(submitter_id,decode=True)}
			if obj.type_of_content == 'g':
				img_height, img_width = get_cached_photo_dim(pk)
				if not img_height:
					img_height, img_width = obj.image_file.height, obj.image_file.width
					cache_photo_dim(pk,img_height,img_width)
				context["width"] = img_width
				context["height"] = img_height
				img_hw_ratio = (1.0*int(img_width)/int(img_height))
				context["ratio"] = round((100.0/img_hw_ratio),2)

			#################################################################
			try:
				context["av_url"] = retrieve_avurl(submitter_id)#obj.submitter.userprofile.avatar.url
			except:
				context["av_url"] = None

			context["is_js_env"] = False
			if on_fbs:
				context["show_copy_prompt"] = True
				context["regular_url"] = "https://damadam.pk"+reverse('content_detail_view',kwargs={"pk": pk,"obj_type":'g'})
			else:
				on_opera = request.is_opera_mini
				is_js_env = retrieve_user_env(opera_mini=on_opera, fbs = on_fbs)
				context["on_opera"] = on_opera
				if is_js_env:
					context["is_js_env"] = True
				
			#################################################################
			
			context["defender"] = False
			context["oun"] = retrieve_uname(submitter_id,decode=True)
			context["from_cull_queue"] = False
			context["latest_comments"] = None
			context["other_photos"] = Link.objects.filter(submitter_id=submitter_id,type_of_content='g',delete_status='0', audience='p').\
			exclude(id=pk).order_by('-id').values('image_file','id')[:10] #list of dictionaries

			if own_id:
				context["authenticated"] = True
				if in_defenders(own_id):
					context["defender"] = True
					if origin == '6':
						context["from_cull_queue"] = True
						context["latest_comments"] = Publicreply.objects.select_related('submitted_by').filter(answer_to_id=pk).order_by('-id')[:25]
					
				
				################### Retention activity logging ###################
				user_id = request.user.id
				if user_id > SEGMENT_STARTING_USER_ID:
					time_now = time.time()
					act = 'Z8' if request.mobile_verified else 'Z8.u'
					activity_dict = {'m':'GET','act':act,'t':time_now}# defines what activity just took place
					log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
				##################################################################

			return render(request,"content_detail.html",context)
	
	# object type is 'text'
	elif obj_type == 't':
		# UNUSED - display_link_detail() handles this at the moment
		if own_id:
			try:
				obj = Link.objects.values('id','description','submitted_on','submitter_id','net_votes','url','cagtegory',\
					'type_of_content','delete_status','audience','expire_at','submitted_on','reply_count','comment_status').get(id=pk)
			except Link.DoesNotExist:
				raise Http404("Object not found")

			submitter_id = obj['submitter_id']
			is_defender = in_defenders(own_id)
			own_profile = submitter_id == own_id

			home_hash = 'tx:'+pk
			post_attributes = {'delete_status':obj['delete_status'],'type_of_content':obj_type,'expire_at':obj['expire_at'],\
			'audience':obj['audience'],'obj_hash':home_hash,'submitter_id':submitter_id}

			privacy_setting, viewable_flag = check_if_post_is_viewable(own_id,post_attributes)

			# do NOT show this detail page to unrelated users, i.e. only self can view, or a defender (in line with our current policy)
			if is_defender or own_profile:

				return render(request,"content_detail.html",{'obj':obj,'obj_id':pk,'oun':retrieve_uname(submitter_id,decode=True),\
					'noindex':True,'authenticated':True,'viewable_status':viewable_flag,'on_fbs':request.META.get('HTTP_X_IORG_FBS',False)})

			else:
				return redirect('private_or_expired')
		else:
			return redirect('private_or_expired')


	# no 'object type' detected - try the 'old' photo_detail view (use a permanent redirect for SEO reasons)
	# Note: we didn't try redirecting to display_link_detail() because currently, text detail pages are not typicall visible
	else:
		if origin:
			return HttpResponsePermanentRedirect("/photo_detail/{0}/{1}/".format(pk, origin))
		else:
			return HttpResponsePermanentRedirect("/photo_detail/{}/".format(pk))



def display_link_detail(request, link_id):
	"""
	Displays a given Link object in a separate page

	Useful for defender who've banned a 'link' (and consequently it's been censored)
	Useful for SEO
	Renders both 'old' and 'new' type of text objs currently
	"""
	context = {}
	own_id = request.user.id
	
	try:
		obj = Link.objects.get(id=link_id)
	except Link.DoesNotExist:
		obj = None

	if obj.submitter_id == own_id or in_defenders(own_id):
		pass
	else:
		# do NOT show this detail page to unrelated users, remove this 'if else' to make it work for everyone
		obj = None
	
	if obj:
		context['obj']=obj
		return render(request,"link_detail.html",context)
	
	else:
		return redirect('private_or_expired')



def photo_detail_view(request, pk, origin=None):
	"""
	Displays an image's detail page (legacy view)

	Only 'old' history is handled here - useful for SEO
	"""
	own_id = request.user.id
	context = {}
	context["can_vote"] = False
	context["authenticated"] = False
	context["photo_id"] = pk
	try:
		photo = Photo.objects.get(id=pk)
		# context["privacy_setting"] = privacy_setting
		context["photo"] = photo
		context["own_photo"] = False
		img_height, img_width = get_cached_photo_dim(pk)
		if not img_height:
			img_height, img_width = photo.image_file.height, photo.image_file.width
			cache_photo_dim(pk,img_height,img_width)
		context["photo_width"] = img_width
		context["photo_height"] = img_height
		img_hw_ratio = (1.0*int(img_width)/int(img_height))
		context["ratio"] = round((100.0/img_hw_ratio),2)
	except:
		context["absent"] = True
		return render(request,"photo_detail.html",context)
	
	try:
		context["av_url"] = photo.owner.userprofile.avatar.url
	except:
		context["av_url"] = None
	
	on_fbs = request.META.get('HTTP_X_IORG_FBS',False)
	context["is_js_env"] = False
	if on_fbs:
		context["show_copy_prompt"] = True
		context["regular_url"] = "https://damadam.pk"+reverse('photo_detail',kwargs={"pk": pk})
	else:
		on_opera = request.is_opera_mini
		is_js_env = retrieve_user_env(opera_mini=on_opera, fbs = on_fbs)
		context["on_opera"] = on_opera
		if is_js_env:
			context["is_js_env"] = True
	context["defender"] = False
	context["is_star"] = is_image_star(user_id=photo.owner_id)
	context["oun"] = retrieve_uname(photo.owner_id,decode=True)
	context["from_cull_queue"] = False
	context["latest_photocomments"] = None
	context["other_photos"] = Link.objects.filter(submitter_id=photo.owner_id,type_of_content='g',delete_status='0', audience='p').exclude(id=pk).order_by('-id').values('image_file','id')[:10] #list of dictionaries
	if request.is_feature_phone or request.is_phone or request.is_mobile:
		context["is_mob"] = True
	if own_id:
		if origin == '6':
			context["from_cull_queue"] = True
		context["authenticated"] = True
		if in_defenders(own_id):
			context["defender"] = True
		if own_id == photo.owner_id:
			context["own_photo"] = True

	return render(request,"photo_detail.html",context)


def best_home_redirect(request, pk=None):
	"""
	Used to redirect to specific spot on trending home (e.g. after writing or 'liking' something)
	"""
	if pk:
		index = retrieve_best_home_feed_index(pk)
	else:
		pk = request.session.pop('home_hash_id',None)
		index = retrieve_best_home_feed_index(pk) if pk else 0
	if index is None:
		url = reverse_lazy("best_home_page")+'?page=1#section0'
	else:
		addendum = get_addendum(index,ITEMS_PER_PAGE, only_addendum=True)
		url = reverse_lazy("best_home_page")+addendum
	############################################
	############################################
	request.session['rd'] = '1'#used by retention activity loggers in home_page() - remove whenever
	############################################
	############################################
	return redirect(url)


def best_home_page(request):
	"""
	Displays the 'best' home page
	"""
	time_now, own_id, page_num = time.time(), request.user.id, request.GET.get('page', '1')
	start_index, end_index = get_indices(page_num, ITEMS_PER_PAGE)
	obj_list, list_total_size = get_best_home_feed(start_idx=start_index, end_idx=end_index, with_feed_size=True)
	num_pages = list_total_size/ITEMS_PER_PAGE
	max_pages = num_pages if list_total_size % ITEMS_PER_PAGE == 0 else (num_pages+1)
	page_num = int(page_num)
	list_of_dictionaries = retrieve_obj_feed(obj_list, with_colors=True)
	#######################
	# must be done in this line, since the 't' information is lost subsequently
	oldest_post_time = min(obj['t'] for obj in list_of_dictionaries) if list_of_dictionaries else 0.0
	#######################
	list_of_dictionaries = format_post_times(list_of_dictionaries, with_machine_readable_times=True)
	####################### Filter followers ####################	
	submitter_ids = set()
	for obj in list_of_dictionaries:
		 submitter_ids.add(str(obj['si']))
	ids_already_fanned = filter_following(submitter_ids,own_id)
	for obj in list_of_dictionaries:
		if str(obj['si']) in ids_already_fanned:
			obj['f'] = True
	#############################################################

	on_fbs = request.META.get('HTTP_X_IORG_FBS',False)
	on_opera = request.is_opera_mini
	is_js_env = retrieve_user_env(opera_mini=on_opera, fbs = on_fbs)
	# on_opera = True if (not on_fbs and not is_js_env) else False
	num = random.randint(1,4)
	#######################
	# enrich objs with information that 'own_id' liked them or not
	if retrieve_last_vote_time(voter_id=own_id) > oldest_post_time:
		recent_user_votes = retrieve_recent_votes(voter_id=own_id, oldest_post_time=oldest_post_time)
		# payload in recent_user_votes is voter_id+":"+target_user_id+":"+vote_value+":"+obj_type+":"+target_obj_id
		recent_user_voted_obj_hashes = set(obj.split(":",3)[-1] for obj in recent_user_votes)
		for obj in list_of_dictionaries:
			if obj['h'] in recent_user_voted_obj_hashes:
				obj['v'] = True# user 'liked' this particular object, so mark it

	is_mob_verified = request.mobile_verified

	###################### Retention activity logging ######################
	from_redirect = request.session.pop('rd',None)# remove this too when removing retention activity logger
	if not from_redirect and own_id > SEGMENT_STARTING_USER_ID:
		act = 'BT' if page_num == 1 else 'BT2'
		act = act if is_mob_verified else act+'.u'
		activity_dict = {'m':'GET','act':act,'t':time_now,'pg':page_num}# defines what activity just took place
		log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
	########################################################################

	context = {'link_list':list_of_dictionaries,'is_auth':True,'on_fbs':on_fbs,'ident':own_id,'on_opera':on_opera,\
	'mobile_verified':is_mob_verified,'random':num,'newbie_lang':request.session.get("newbie_lang",None),'time_now':time_now,\
	'dir_rep_form':DirectResponseForm(with_id=True),'latest_dir_rep':retrieve_latest_direct_reply(user_id=own_id),\
	'single_notif_dir_rep_form':DirectResponseForm(),'dir_rep_invalid':request.session.pop("dir_rep_invalid"+str(own_id),None),\
	'uname_rep_sent_to':request.session.pop("dir_rep_sent"+str(own_id),None),'thin_rep_form':DirectResponseForm(thin_strip=True),\
	'obj_type_rep_sent_to':request.session.pop("dir_rep_tgt_obj_type"+str(own_id),None),'max_home_reply_size':MAX_HOME_REPLY_SIZE,\
	'parent_obj_id_rep_sent_to':request.session.pop("dir_rep_tgt_obj_id"+str(own_id),None),'feed_type':'best_text',\
	'origin':'12','sn_origin':'13'}

	context["page"] = {'number':page_num,'has_previous':True if page_num>1 else False,'has_next':True if page_num<max_pages else False,\
	'previous_page_number':page_num-1,'next_page_number':page_num+1}
	
	newbie_flag = request.session.get("newbie_flag",None)
	if newbie_flag:
		context["newbie_flag"] = newbie_flag
		context["newbie_tutorial_page"] = 'tutorial3.html'# hardcoding to tutorial 3

	return render(request, 'text_page.html', context)


def home_redirect(request, pk=None):
	"""
	Used to redirect to specific spot on home (e.g. after writing or 'liking' something)
	"""
	if pk:
		index = retrieve_home_feed_index(pk)
	else:
		pk = request.session.pop('home_hash_id',None)
		index = retrieve_home_feed_index(pk) if pk else 0
	if index is None:
		url = reverse_lazy("fresh_text")+'?page=1#section0'
	else:
		addendum = get_addendum(index,ITEMS_PER_PAGE, only_addendum=True)
		url = reverse_lazy("fresh_text")+addendum
	############################################
	############################################
	request.session['rd'] = '1'#used by retention activity loggers in home_page() - remove whenever
	############################################
	############################################
	return redirect(url)


def home_page(request, lang=None):
	"""
	Displays the home page
	"""
	time_now, own_id, page_num = time.time(), request.user.id, request.GET.get('page', '1')
	start_index, end_index = get_indices(page_num, ITEMS_PER_PAGE)
	obj_list, list_total_size = get_home_feed(start_idx=start_index, end_idx=end_index, with_feed_size=True)
	num_pages = list_total_size/ITEMS_PER_PAGE
	max_pages = num_pages if list_total_size % ITEMS_PER_PAGE == 0 else (num_pages+1)
	page_num = int(page_num)
	list_of_dictionaries = retrieve_obj_feed(obj_list, with_colors=True)
	#######################
	# must be done in this line, since the 't' information is lost subsequently
	try:
		oldest_post_time = list_of_dictionaries[-1]['t']
	except:
		oldest_post_time = 0.0
	#######################
	list_of_dictionaries = format_post_times(list_of_dictionaries, with_machine_readable_times=True)
	####################### Filter followers ####################	
	submitter_ids = set()
	for obj in list_of_dictionaries:
		 submitter_ids.add(str(obj['si']))
	ids_already_fanned = filter_following(submitter_ids,own_id)
	for obj in list_of_dictionaries:
		if str(obj['si']) in ids_already_fanned:
			obj['f'] = True
	#############################################################

	on_fbs = request.META.get('HTTP_X_IORG_FBS',False)
	on_opera = request.is_opera_mini
	is_js_env = retrieve_user_env(opera_mini=on_opera, fbs = on_fbs)
	# on_opera = True if (not on_fbs and not is_js_env) else False
	num = random.randint(1,4)
	#######################
	# short-circuit in case user's previous voting time was BEFORE oldest_post_time on the page
	if retrieve_last_vote_time(voter_id=own_id) > oldest_post_time:
		recent_user_votes = retrieve_recent_votes(voter_id=own_id, oldest_post_time=oldest_post_time)
		# payload in recent_user_votes is voter_id+":"+target_user_id+":"+vote_value+":"+obj_type+":"+target_obj_id
		recent_user_voted_obj_hashes = set(obj.split(":",3)[-1] for obj in recent_user_votes)
		for obj in list_of_dictionaries:
			# enrich objs with information that 'own_id' liked them or not
			if obj['h'] in recent_user_voted_obj_hashes:
				obj['v'] = True# user 'liked' this particular object, so mark it

	is_mob_verified = request.mobile_verified

	###################### Retention activity logging ######################
	from_redirect = request.session.pop('rd',None)# remove this too when removing retention activity logger
	if not from_redirect and own_id > SEGMENT_STARTING_USER_ID:
		act = 'FT' if page_num == 1 else 'FT2'
		act = act if is_mob_verified else act+'.u'
		activity_dict = {'m':'GET','act':act,'t':time_now,'pg':page_num}# defines what activity just took place
		log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
	########################################################################

	context = {'link_list':list_of_dictionaries,'is_auth':True,'on_fbs':on_fbs,'ident':own_id,'on_opera':on_opera,\
	'mobile_verified':is_mob_verified,'random':num,'newbie_lang':request.session.get("newbie_lang",None),\
	'dir_rep_form':DirectResponseForm(with_id=True),'latest_dir_rep':retrieve_latest_direct_reply(user_id=own_id),\
	'single_notif_dir_rep_form':DirectResponseForm(),'dir_rep_invalid':request.session.pop("dir_rep_invalid"+str(own_id),None),\
	'uname_rep_sent_to':request.session.pop("dir_rep_sent"+str(own_id),None),'thin_rep_form':DirectResponseForm(thin_strip=True),\
	'obj_type_rep_sent_to':request.session.pop("dir_rep_tgt_obj_type"+str(own_id),None),'max_home_reply_size':MAX_HOME_REPLY_SIZE,\
	'parent_obj_id_rep_sent_to':request.session.pop("dir_rep_tgt_obj_id"+str(own_id),None),'time_now':time_now,'feed_type':'fresh_text',\
	'origin':'3','sn_origin':'19'}

	context["page"] = {'number':page_num,'has_previous':True if page_num>1 else False,'has_next':True if page_num<max_pages else False,\
	'previous_page_number':page_num-1,'next_page_number':page_num+1}
	
	newbie_flag = request.session.get("newbie_flag",None)
	if newbie_flag:
		context["newbie_flag"] = newbie_flag
		context["newbie_tutorial_page"] = 'tutorial3.html'# hardcoding to tutorial 3

	return render(request, 'text_page.html', context)


##############################################################################################################################
##############################################################################################################################

def turn_off_newbie(request,origin):
	"""
	Turn off newbie flag so that the tutorial can disappear

	Origin must match that which is defined in return_to_content()
	"""
	request.session.pop("newbie_flag",None)
	####################################################
	# fresh and trending images
	if origin == '1':
		return redirect("photo",list_type='fresh-list')
	elif origin == '2':
		return redirect("photo",list_type='best-list')
	####################################################
	# fresh and trending posts
	elif origin == '3':
		return redirect("fresh_text")
	elif origin == '12':
		return redirect('best_home_page')
	####################################################
	elif origin == '26':
		return redirect('for_me')	
	elif origin == '27':
		return redirect('topic_listing')
	# elif origin == '36':
	# 	return redirect('get_ranked_groups')
	else:
		return redirect('home')

def new_user_gateway(request,lang=None,*args,**kwargs):
	"""
	Set necessary newbie flags so user is shown the correct tutorial
	"""
	request.session["newbie_flag"] = '3'# defaulting all users to 'variation 3' (i.e. 'content' specific tutorial)
	request.session["newbie_lang"] = lang if lang else 'eng'
	request.session.modified = True
	############################################
	############################################
	user_id = request.user.id
	if user_id > SEGMENT_STARTING_USER_ID:
		time_now = time.time()
		request.session['rd'] = '1'
		activity_dict = {'m':'GET','act':'V3','t':time_now}# defines what activity just took place
		log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now, which_var='var3')
	############################################
	############################################
	return redirect("photo",list_type='best-list')
	# return redirect("first_time_choice", lang=lang)


def first_time_choice(request,lang=None, *args, **kwargs):
	"""
	Unused at the moment
	"""
	user_id = request.user.id
	if request.method == 'POST':
		request.session["newbie_lang"] = lang if lang else 'eng'
		# new 4-pronged onboarding funnel
		choice = request.POST.get("choice",None)
		if choice in ('1','2','3','4'):
			# if choice in ('2','3','4'):
			# 	# these particular variations have subsets too
			# 	choice = retrieve_variation_subset(user_id, choice)
			request.session["newbie_flag"] = choice
			############################################
			############################################
			if user_id > SEGMENT_STARTING_USER_ID:
				time_now = time.time()
				request.session['rd'] = '1'
				activity_dict = {'m':'POST','act':'V'+choice,'t':time_now}# defines what activity just took place
				log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now, which_var='var'+choice)
			############################################
			############################################
			return redirect('home')
			# if choice == '5':
			# 	return redirect("get_ranked_groups")
			# elif choice == '6':
			# 	return redirect("topic_listing")
			# elif choice == '7':
			# 	return redirect(reverse_lazy("photo", args=['best-list']))
			# else:
			# 	return redirect('home')
		else:
			request.session["redo_tut_selection"+str(user_id)] = '1'
			return redirect("first_time_choice",lang)
	else:
		# new 4-pronged onboarding funnel
		no_choice_selected = True if request.session.pop("redo_tut_selection"+str(user_id),None) == '1' else False
		if lang == 'ur':
			return render(request,"unauth/ftue_choices_ur.html",{'no_choice_selected':no_choice_selected})
		else:
			return render(request,"unauth/ftue_choices.html",{'no_choice_selected':no_choice_selected})


##############################################################################################################################
##############################################################################################################################


def show_online_users(request):
	"""
	Displays online users, sorted by world age, enriched by anchor tags for fast jumping between alphabets
	"""
	cached_data = retrieve_online_cached_data()
	if cached_data:
		try:
			data = json.loads(cached_data)
		except:
			import json as json_backup
			data = json_backup.loads(cached_data)
		final_data, num_online = data['final_data'], data['num_online']
	else:
		user_ids_and_ages = get_most_recent_online_users(with_ages=True)
		if user_ids_and_ages:
			user_ids = [user_id for user_id, user_age in user_ids_and_ages]
			username_data = retrieve_bulk_unames(user_ids, decode=True)
			final_data = create_sorted_online_list(username_data, user_ids_and_ages)
			num_online = len(user_ids)
			cache_online_data(json.dumps({'final_data':final_data,'num_online':num_online}))
		else:
			final_data, num_online = [], 0
	own_id = request.user.id
	################### Retention activity logging ###################
	if own_id > SEGMENT_STARTING_USER_ID:
		time_now = time.time()
		act = 'O' if request.mobile_verified else 'O.u'
		activity_dict = {'m':'GET','act':act,'t':time_now}# defines what activity just took place
		log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
	##################################################################
	return render(request,"online_list.html",{'online_data':final_data,'stars':get_all_image_star_ids(), 'num_online':num_online,\
		'own_id':str(own_id),'bottom':len(final_data),'on_fbs':request.META.get('HTTP_X_IORG_FBS',False)})


class LinkDeleteView(DeleteView):
	model = Link
	success_url = reverse_lazy('home')


def user_profile_photo(request, slug=None, photo_pk=None, is_notif=None, *args, **kwargs):
	"""
	Used in banning_history.html, etc
	
	TODO: remove 'is_notif' parameter - it's a redis2 legacy param
	"""
	if photo_pk:
		request.session["photograph_id"] = photo_pk
		return redirect("profile_photos_redirect",slug,'fotos')
		# return redirect("profile", slug, 'fotos')
	else:
		try:
			return redirect("profile", slug, 'fotos')
		except:
			return redirect("profile", request.user.username, 'fotos')


def user_profile_photos_redirect(request, slug, list_type):
	"""
	Used to redirect to specific spot on user_profile_photos (e.g. after returning from viewing own 'likes')
	"""
	own_id = request.user.id
	target_id = request.session.pop("photograph_id",None)
	if target_id:
		owner_id = retrieve_user_id(slug)
		PICS_PER_PAGE = 10
		obj_id_list = Photo.objects.only('id').filter(owner_id=owner_id,category='1',is_public=True).order_by('-id').values_list('id',flat=True)
		if obj_id_list:
			try:
				index = list(obj_id_list).index(int(target_id))
			except:
				index = 0
			addendum = get_addendum(index,PICS_PER_PAGE, only_addendum=True)
			url = reverse_lazy("profile",kwargs={'slug':slug,"type": list_type})+addendum
		else:
			url = reverse_lazy("profile",kwargs={'slug':slug,"type": list_type})+'?page=1#section0'
	else:
		url = reverse_lazy("profile",kwargs={'slug':slug,"type": list_type})+'?page=1#section0'
	############################################
	############################################
	if own_id:
		request.session['rd'] = '1'#used by retention activity loggers in home_page() - remove whenever
	############################################
	############################################
	return redirect(url)


class UserProfileDetailView(FormView):
	template_name = "user_detail.html"
	form_class = UserProfileDetailForm

	def get_context_data(self,**kwargs):
		context = super(UserProfileDetailView, self).get_context_data(**kwargs)
		username = self.kwargs["slug"]
		context["username"] = username
		context["image_base_width"] = PERSONAL_GROUP_IMG_WIDTH
		star_id = retrieve_user_id(username)
		try:
			user_obj = User.objects.only('id','date_joined').get(id=star_id)# get required fields only
			user_profile = UserProfile.objects.only('bio','age','gender','shadi_shuda','attractiveness','avatar','streak').get(user_id=star_id)# get required user profile fields
			context["object"] = user_obj
			context["user_profile"] = user_profile
		except User.DoesNotExist:
			raise Http404("User ID does not compute")
		if star_id:
			user_id = self.request.user.id
			verified_followers, unverified_followers = get_verified_follower_count(star_id, with_unverified=True)
			context["verif_follower_count"] = verified_followers
			context["unverif_follower_count"] = unverified_followers
			context["following_count"] = get_following_count(star_id)
			context["own_id"] = user_id
			context["star_id"] = star_id
			if user_id:
				context["is_follower"] = check_if_follower(user_id, star_id, with_db_lookup=True)
			num_trending_pics = is_image_star(user_id=star_id)
			context["is_star"] = int(num_trending_pics) if num_trending_pics else num_trending_pics
			star_score = retreive_trending_rep(user_id=star_id)
			context["star_score"] = int(star_score) if star_score > 0 else 0
			context["city_name"] = REV_CITY_DICT.get(user_profile.streak,0)
			context["zodiac"] = ZODIAC.get(user_profile.attractiveness,'None')
			user_id = str(user_id) if user_id else None
			is_defender, is_own_profile, ban_detail = in_defenders(user_id), user_id == star_id, None
			banned, time_remaining, ban_detail = check_content_and_voting_ban(star_id, with_details=True)
			context["star_av_url"] = retrieve_avurl(star_id)
			context["is_profile_banned"] = banned
			context["is_own_profile"] = is_own_profile
			is_defender, is_super_defender = in_defenders(user_id, return_super_status=True)
			if is_super_defender:
				context["manageable"] = True
			context["ban_detail"] = ban_detail
			context["is_defender"] = is_defender
			context["time_remaining"] = time_remaining
			context["origin"] = '10'#helps redirect back to this page if a user enter the "report" funnel
			context["mehfil_creation_ttl"] = self.request.session.pop("mehfil_creation_rate_limited",None)
			context["star_owner_mehfils"] = retrieve_latest_user_owned_mehfils(star_id)
			if star_id == user_id:
				context["subscribed_topics"] = retrieve_subscribed_topics(user_id)
				context["blocked"] = get_banned_users_count(user_id)
				context["mobile_verified"] = self.request.mobile_verified
				context["successfully_unsubscribed"] = self.request.session.pop("successfully_unsubscribed"+str(user_id),'')
			else:
				context["mobile_verified"] = is_mobile_verified(star_id)
			
			total_objs = Link.objects.filter(Q(submitter_id=star_id,audience='p',delete_status='0',mortality='i')|\
				Q(submitter_id=star_id,audience='p',delete_status='0',expire_at__gte=time.time())).count()
			
			context["num_posts"] = total_objs if total_objs < 1000 else '999+'
			context["noindex"] = True if (banned or not context["mobile_verified"]) else False
			################### Retention activity logging ###################
			if user_id:
				from_redirect = self.request.session.pop('rd',None)# remove this too when removing retention activity logger
				if not from_redirect and int(user_id) > SEGMENT_STARTING_USER_ID:
					time_now = time.time()
					if is_own_profile:
						act = 'A1' if self.request.mobile_verified else 'A1.u'
					else:
						act = 'A4' if self.request.mobile_verified else 'A4.u'
					activity_dict = {'m':'GET','act':act,'t':time_now,'tuid':star_id}# defines what activity just took place
					log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
			##################################################################
		else:
			# user does not exist
			raise Http404("User ID does not exist")
		return context

################################## Permanent redirects ################################################


def comment_pk(request, pk=None, origin=None, ident=None, *args, **kwargs):
	"""
	Permanent redirect to comment page of an image
	"""
	request.session["photo_id"] = pk
	if ident:
		request.session["user_ident"] = ident
	else:
		request.session["user_ident"] = None
	if origin:
		return HttpResponsePermanentRedirect("/comment/{0}/{1}/".format(pk, origin))
	else:
		return HttpResponsePermanentRedirect("/comment/{}/".format(pk))


def profile_pk(request, slug=None, key=None, *args, **kwargs):
	"""
	Permanent redirect to new user profile photos view
	"""
	if key:
		request.session["photograph_id"] = key
	return HttpResponsePermanentRedirect("/user/{}/fotos/".format(slug.encode('utf-8')))


def best_photos_list(request):
	"""
	Permanent redirect to the trending page
	"""
	return HttpResponsePermanentRedirect("/photo/best-list/")


def fresh_photos_list(request):
	"""
	Permanent redirect to the trending page
	"""
	return HttpResponsePermanentRedirect("/photo/fresh-list/")


def redirect_to_profile_photos(request,slug):
	"""
	Permanent redirect to new user profile photos view
	"""
	return HttpResponsePermanentRedirect("/user/{}/fotos/".format(slug.encode('utf-8')))


def redirect_to_search(request):
	"""
	Permanent redirect to search
	"""
	return HttpResponsePermanentRedirect("/search/nickname/")


def redirect_to_mehfil_list(request):
	"""
	Permanent redirect to mehfil joined list
	"""
	return HttpResponsePermanentRedirect("/mehfil/joined/list/")


def redirect_to_1on1_list(request):
	"""
	Permanent redirect to 1on1 friendlist
	"""
	return HttpResponsePermanentRedirect("/1-on-1/friends/")


def perm_redirect_to_home(request,pk=None,origin=None,slug=None):
	"""
	Permanent redirect to new user profile photos view
	"""
	return HttpResponsePermanentRedirect("/")

############################################################################################################


#rate limit this
@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@sensitive_post_parameters()
@csrf_protect
def reset_password(request,*args,**kwargs):
	if request.method == 'POST':
		form = ResetPasswordForm(data=request.POST,request=request)
		if form.is_valid():
			form.save()
			password = request.POST.get("password")
			username = request.user.username
			request.session.pop("authentic_password_owner", None)
			user = authenticate(username=username,password=password)
			update_session_auth_hash(request, user)# logging the user out of everywhere else
			quick_login(request,user)
			return render(request,'change_password/new_password.html',{'new_pass':password})
		else:
			allowed = request.session.get('authentic_password_owner',None)
			if allowed == '1':
				context={'form':form,'allowed':True}
			else:
				context={'form':form,'allowed':None}
			return render(request,'change_password/reset_password.html',context)    
	else:
		form = ResetPasswordForm()
		try:
			allowed = request.session.get('authentic_password_owner',None)
			if allowed == '1':
				#can press forward, user is 'allowed'
				return render(request,'change_password/reset_password.html',{'form':form,'allowed':True})
			else:
				#send back for reauth
				return redirect("reauth")
		except:
			#send back for reauth
			return redirect("reauth")

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
@ratelimit(method='POST', rate='25/h')
def reauth(request, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		return render(request, 'change_password/penalty_reauth.html', {'pk':'pk'})
	else:
		user_id = request.user.id
		if tutorial_unseen(user_id=user_id, which_tut='27', renew_lease=True):
			return render(request, 'change_password/password_change_tutorial.html', {'username':retrieve_uname(user_id,decode=True)})
		else:
			if request.method == 'POST':
				form = ReauthForm(data=request.POST,request=request)
				if form.is_valid():
					request.session['authentic_password_owner'] = '1'
					request.session.modified = True
					return redirect("reset_password")
				else:
					return render(request, 'change_password/reauth.html', {'form':form})
			else:
				return render(request, 'change_password/reauth.html', {'form':ReauthForm()})

############################################################################################################

def top_star_list(request):
	"""
	"""
	from redis4 import retrieve_bulk_credentials

	final_data = []
	own_id = request.user.id
	trender_ids = retrieve_trenders_by_score()
	ids_already_fanned = filter_following(trender_ids,own_id)
	trender_credential_dict = retrieve_bulk_credentials(trender_ids,decode_unames=False)
	trender_ids = map(int,trender_ids)
	
	for trender_id in trender_ids:
		username = trender_credential_dict[trender_id]['uname']
		av_url = trender_credential_dict[trender_id]['avurl']
		if trender_id in ids_already_fanned:
			final_data.append((trender_id, username, av_url, False))# 'False' means user cannot follow this person (because already following)
		else:
			final_data.append((trender_id, username, av_url, True))# 'True' means user can follow this person

	return render(request,"top_image_stars.html",{'final_data':final_data, 'ident':own_id})


def photo_top_trenders(request):
	"""
	Renders the top trending users (in terms of photos uploaded)
	"""
	################### Retention activity logging ###################
	user_id = request.user.id
	if user_id > SEGMENT_STARTING_USER_ID:
		time_now = time.time()
		act = 'Z9' if request.mobile_verified else 'Z9.u'
		activity_dict = {'m':'GET','act':act,'t':time_now}# defines what activity just took place
		log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
	##################################################################
	
	own_id = request.user.id
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
	
	return render(request,"top_photo.html",{'object_list':enriched_data,'list_size':TRENDER_RANKS_TO_COUNT,'ident':own_id})


@ratelimit(rate='3/s')
def reply_to_photo(request, pk=None, ident=None, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		return redirect("missing_page")
	else:
		if pk.isdigit():
			request.session["photo_id"] = pk
			request.session["related_photostream_id"] = ident
			return redirect("reply_options")
		else:
			return redirect("profile", request.user.username, 'fotos')


def display_text_comments(request, parent_id, origin=None):
	"""
	Render the comments page for text objs
	"""
	try:
		link = Link.objects.values('id','reply_count','description','submitted_on','submitter_id','net_votes','url','cagtegory',\
			'type_of_content','delete_status','audience','expire_at','comment_status').get(id=parent_id)
		link['machine_time'] = link['submitted_on']
		link['submitted_on'] = naturaltime(link['submitted_on'])
	except Link.DoesNotExist:
		return render(request, 'object_deleted.html',{})

	user_id = request.user.id
	obj_type = link['type_of_content']
	home_hash = 'tx:'+parent_id
	post_attributes = {'delete_status':link['delete_status'],'type_of_content':obj_type,'expire_at':link['expire_at'],\
	'audience':link['audience'],'obj_hash':home_hash,'submitter_id':link['submitter_id']}

	# this is a 'new' object
	if obj_type:
		privacy_setting, viewable_flag = check_if_post_is_viewable(user_id,post_attributes)

		if viewable_flag == '0':
			# request.session['privacy_setting'] = privacy_setting
			# request.session['viewable_flag'] = viewable_flag
			return redirect('private_or_expired')

	# this is an 'old' object - redirect (permanently) to old comments function
	else:
		return HttpResponsePermanentRedirect("/jawab/{}/".format(parent_id))
		
	##########################################################
	secret_key = uuid.uuid4()
	set_text_input_key(user_id, parent_id, 'home_rep', secret_key)
	##########################################################
	parent_submitter_id = link['submitter_id']
	parent_uname, parent_avurl = retrieve_credentials(parent_submitter_id,decode_uname=True)
	##########################################################
	context = {'main_rep_form': DirectResponseForm(),'dir_rep_invalid':request.session.pop("dir_rep_invalid"+str(user_id),None),\
	'dir_rep_form':DirectResponseForm(with_id=True),'is_auth':True,'user_id':user_id,'on_fbs':request.META.get('HTTP_X_IORG_FBS',False),\
	'mob_verified':True if request.mobile_verified else False,'sk':secret_key,'parent_submitter_id':parent_submitter_id,\
	'parent_av_url':parent_avurl,'parent_submitter_username':parent_uname,'is_star':is_image_star(user_id=parent_submitter_id),\
	'stars':get_all_image_star_ids(),'vote_score':link['net_votes'],'feature_phone':True if request.is_feature_phone else False,\
	'random':random.sample(xrange(1,188),15),'parent':link, 'user_is_owner':parent_submitter_id == user_id, 'lid':home_hash,\
	'privacy_setting':privacy_setting,'noindex':True if (privacy_setting == 'limited') else False, 'viewable_status':viewable_flag,\
	'origin':origin if origin else '0','com':link['comment_status']}
	##########################################################
	if link['url']:
		payload = link['url'].split(":")
		try:
			theme, context['topic_name'], context['topic_url'] = payload[0], payload[1], payload[2]
			color_grads = COLOR_GRADIENTS[theme]
			context["c1"], context["c2"] = color_grads[0], color_grads[1]
		except IndexError:
			pass
	############### Retention activity logging ###############
	from_redirect = request.session.pop('rd','')
	if not from_redirect and user_id > SEGMENT_STARTING_USER_ID:
		time_now = time.time()
		act = 'L1' if request.mobile_verified else 'L1.u'
		activity_dict = {'m':'GET','act':act,'t':time_now,'pc':link['description']}# defines what activity just took place
		log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
	##########################################################
	replies = retrieve_cached_public_replies(parent_id)
	if replies:
		replies_data = json.loads(replies)
	else:
		replies_data = Publicreply.objects.only('submitted_on','description','id','submitted_by','abuse','submitted_by__username',\
			'direct_reply_tgt_uname','direct_reply_tgt_text_prefix','direct_reply_tgt_text_postfix','direct_reply_id').\
		values('submitted_on','description','id','submitted_by','abuse','submitted_by__username','direct_reply_tgt_uname',\
			'direct_reply_tgt_text_prefix','direct_reply_tgt_text_postfix','direct_reply_id').filter(answer_to_id=parent_id).\
		order_by('-id')[:25]
		for reply in replies_data:
			reply["submitted_on"] = convert_to_epoch(reply["submitted_on"])
		cache_public_replies(json.dumps(replies_data),parent_id)
	context["replies"] = replies_data#replies
	##########################################################
	if request.user_banned:
		context["reply_time"] = None
	elif replies_data:
		# useful for showing  'NEW' tag next to comments
		last_seen_time = get_last_comment_time(commenter_id=user_id, obj_owner_id=parent_submitter_id, obj_hash_name=home_hash)
		# useful for showing a 'NEW' tag next to replies
		context["reply_time"] = float(last_seen_time) if last_seen_time else None
	else:
		context["reply_time"] = None
	##########################################################
	return render(request,"reply.html",context)


def display_image_comments(request,pk,origin=None):
	"""
	Render the comments page for image comments
	"""
	user_id = request.user.id
	try:
		photo = Link.objects.only('description','net_votes','image_file','id','delete_status','type_of_content','submitter',\
			'expire_at','audience','comment_status','web_link').get(id=pk)
	except Link.DoesNotExist:
		context = {}
		if user_id:
			context["obj_deleted"] = True
		else:
			context['target_username'] = 'User'
			context['authorized'] = False

		return render(request,"comments.html",context)
	####################################################
	obj_type = photo.type_of_content
	home_hash = 'img:'+pk
	post_attributes = {'delete_status':photo.delete_status,'type_of_content':obj_type,'expire_at':photo.expire_at,'audience':photo.audience,\
	'obj_hash':home_hash, 'submitter_id':photo.submitter_id}

	# this is a 'new' object
	if obj_type:
		privacy_setting, viewable_flag = check_if_post_is_viewable(user_id,post_attributes)

		if viewable_flag == '0':
			# request.session['privacy_setting'] = privacy_setting
			# request.session['viewable_flag'] = viewable_flag
			return redirect('private_or_expired')

	# this is an 'old' object - redirect (permanently) to old comments function
	else:
		if origin:
			return HttpResponsePermanentRedirect("/comment/{0}/{1}/".format(pk, origin))
		else:
			return HttpResponsePermanentRedirect("/comment/{}/".format(pk))

	####################################################

	photo_owner_id = photo.submitter_id
	secret_key = uuid.uuid4()
	target_username, av_url = retrieve_credentials(photo_owner_id,decode_uname=True)

	comments = Publicreply.objects.only('abuse','description','id','submitted_by','submitted_on','submitted_by__username',\
		'direct_reply_tgt_uname','direct_reply_tgt_text_prefix','direct_reply_tgt_text_postfix','direct_reply_id').\
	values('abuse','description','id','submitted_by','submitted_on','submitted_by__username','direct_reply_tgt_uname',\
		'direct_reply_tgt_text_prefix','direct_reply_tgt_text_postfix','direct_reply_id').filter(answer_to_id=pk).\
	order_by('-id')[:25]

	for comment in comments:
		comment["submitted_on"] = convert_to_epoch(comment["submitted_on"])

	context = {'feature_phone':True if request.is_feature_phone else False,'lid':home_hash,'photo_id':pk,'obj_deleted':False,\
	'photo':photo,'sk':secret_key,'stars':get_all_image_star_ids(), 'noindex':True if (privacy_setting == 'limited') else False,\
	'is_star':is_image_star(user_id=photo_owner_id),'on_fbs':request.META.get('HTTP_X_IORG_FBS',False),'authorized':True,\
	'random':random.sample(xrange(1,188),15),'VDC':VOTING_DRIVEN_CENSORSHIP+1,'target_username':target_username,\
	'latest_comment_time':comments[0]['submitted_on'] if comments else None,'origin':origin if origin else '0',\
	'photo_owner_id':photo_owner_id,'user_is_owner':photo_owner_id == user_id,'privacy_setting':privacy_setting,\
	'viewable_status':viewable_flag,'comments':comments,'av_url':av_url}

	if origin == '3':
		# originating from home            
		request.session["target_id"] = home_hash#turn pk into 'home_hash' (for accurate redirects)
		request.session.modified = True

	if user_id:
		set_text_input_key(user_id, pk, 'pht_comm', secret_key)
		time_now = time.time()
		context["dir_rep_form"] = DirectResponseForm(with_id=True)
		context["main_rep_form"] = DirectResponseForm()
		context["is_auth"] = True
		context["mob_verified"] = True
		context["user_id"] = user_id
		if not request.mobile_verified:
			context["mob_verified"] = False
		context["authenticated"] = True
		context["dir_rep_invalid"] = request.session.pop("dir_rep_invalid"+str(user_id),None)
		context["own_username"] = retrieve_uname(user_id,decode=True)
		
		if comments:	
			# useful for showing  'NEW' tag next to comments
			last_seen_time = get_last_comment_time(commenter_id=user_id, obj_owner_id=photo_owner_id, obj_hash_name=home_hash)
			# useful for showing a 'NEW' tag next to replies
			context["comment_time"] = float(last_seen_time) if last_seen_time else None
		
		################### Retention activity logging ###################
		from_redirect = request.session.pop('rd','')
		if not from_redirect and user_id > SEGMENT_STARTING_USER_ID:
			act = 'C1' if request.mobile_verified else 'C1.u'
			activity_dict = {'m':'GET','act':act,'t':time_now,'pi':photo.image_file.url,'pc':photo.description}# defines what activity just took place
			log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
		##################################################################
	else:
		context["authenticated"] = False

	return render(request,"comments.html",context)


#########################Views for fresh photos#########################


def photo_redirect(request, list_type='best-list', pk=None):
	"""
	Used to redirect to specific spot on photo pages (e.g. after writing something)
	"""
	if list_type == 'best-list':
		feed_type = 'best_photos'
	else:
		feed_type = 'fresh_photos'
	########################################################################
	if pk:
		index = retrieve_photo_feed_index("img:"+str(pk),feed_type=feed_type)
	else:
		pk = request.session.pop('photo_hash_id',None)
		index = retrieve_photo_feed_index("img:"+str(pk),feed_type=feed_type) if pk else 0
	if index is None:
		url = reverse_lazy("photo", args=[list_type])+'?page=1#section0'
	else:
		addendum = get_addendum(index, PHOTOS_PER_PAGE, only_addendum=True)
		url = reverse_lazy("photo", args=[list_type])+addendum
	############################################
	############################################
	request.session['rd'] = '1'#used by retention activity loggers in home_page() - remove whenever
	############################################
	############################################
	return redirect(url)


def photo_page(request,list_type='best-list'):
	"""
	Displays both the latest photos page (sorted by latest first) and the best photos page (sorted by best first)
	"""
	if list_type in ('best-list','fresh-list'):
		time_now, own_id, page_num, on_fbs = time.time(), request.user.id, request.GET.get('page', '1'), request.META.get('HTTP_X_IORG_FBS',False)
		photos_per_page = 10 if on_fbs else PHOTOS_PER_PAGE
		start_index, end_index = get_indices(page_num, photos_per_page)
		cached_image_count = retrieve_image_count(list_type=list_type)
		if list_type == 'best-list':
			type_, page_origin, char = 'best_photos', '2', 'BP'# 'char' is used in retention activity logging - can be removed
			navbar_type, single_notif_origin = 'best', '21'
			if cached_image_count:
				num_in_last_1_day = cached_image_count
			else:
				one_day_ago = datetime.utcnow()-timedelta(hours=24)
				num_in_last_1_day = Cooldown.objects.filter(time_of_casting__gte=one_day_ago).count()
				cache_image_count(num_images=num_in_last_1_day,list_type=list_type)
		else:
			type_, page_origin, char = 'fresh_photos', '1', 'FP'# 'char' is used in retention activity logging - can be removed
			navbar_type, single_notif_origin = 'fresh', '20'
			if cached_image_count:
				num_in_last_1_day = cached_image_count
			else:
				num_in_last_1_day = retrieve_fresh_image_count()
				cache_image_count(num_images=num_in_last_1_day,list_type=list_type)
		obj_list, list_total_size = get_photo_feed(start_idx=start_index, end_idx=end_index, feed_type=type_, with_feed_size=True)
		num_pages = list_total_size/photos_per_page
		max_pages = num_pages if list_total_size % photos_per_page == 0 else (num_pages+1)
		page_num = int(page_num)
		list_of_dictionaries = retrieve_obj_feed(obj_list)
		#######################
		# must be done in this line, since the 't' information in objs in list_of_dictionaries is lost subsequently
		if list_type == 'fresh-list':
			# retrieve 'oldest_post_time' from simply the tail-end of the list - since it's a time-sorted list
			try:
				oldest_post_time = list_of_dictionaries[-1]['t']
			except:
				oldest_post_time = 0.0
		else:
			# best-list is not necessarily in a sequence, so finding 'oldest_post_time' will require a different approach
			oldest_post_time = min(obj['t'] for obj in list_of_dictionaries) if list_of_dictionaries else 0.0
		#######################
		list_of_dictionaries = format_post_times(list_of_dictionaries, with_machine_readable_times=True)
		if own_id:
			is_auth = True
			secret_key = str(uuid.uuid4())
			set_text_input_key(user_id=own_id, obj_id='1', obj_type=type_, secret_key=secret_key)
			newbie_lang, newbie_flag = request.session.get("newbie_lang",None), request.session.get("newbie_flag",None)
			mobile_verified = request.mobile_verified
			####################### Filter followers ####################
			submitter_ids = set()
			for obj in list_of_dictionaries:
				 submitter_ids.add(str(obj['si']))
			ids_already_fanned = filter_following(submitter_ids,own_id)
			for obj in list_of_dictionaries:
				if str(obj['si']) in ids_already_fanned:
					obj['f'] = True
			#############################################################
			# short-circuit in case user's previous voting time was BEFORE oldest_post_time on the page
			if retrieve_last_vote_time(voter_id=own_id) > oldest_post_time:
				recent_user_votes = retrieve_recent_votes(voter_id=own_id, oldest_post_time=oldest_post_time)
				# payload in recent_user_votes is voter_id+":"+target_user_id+":"+vote_value+":"+obj_type+":"+target_obj_id
				recent_user_voted_obj_hashes = set(obj.split(":",3)[-1] for obj in recent_user_votes)
				for obj in list_of_dictionaries:
					# enrich objs with information that 'own_id' liked them or not
					if obj['h'] in recent_user_voted_obj_hashes:
						obj['v'] = True# user 'liked' this particular object, so mark it
			
			###################### Retention activity logging ######################
			from_redirect = request.session.pop('rd',None)# remove this too when removing retention activity logger
			if not from_redirect and own_id > SEGMENT_STARTING_USER_ID:
				char = char if page_num == 1 else char+'2'
				act = char if mobile_verified else char+".u"
				activity_dict = {'m':'GET','act':act,'t':time_now,'pg':page_num}# defines what activity just took place
				log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
			########################################################################

		else:
			is_auth = False
			secret_key = ''
			newbie_lang, newbie_flag = None, None
			mobile_verified = None

		on_opera = request.is_opera_mini
		is_js_env = retrieve_user_env(opera_mini=on_opera, fbs = on_fbs)
		# on_opera = True if (not on_fbs and not is_js_env) else False
		
		context = {'object_list':list_of_dictionaries,'single_notif_dir_rep_form':DirectResponseForm(),\
		'single_notif_origin':single_notif_origin, 'page_origin':page_origin,'fbs':on_fbs,'list_type':list_type,\
		'feed_type':type_,'navbar_type':navbar_type,'on_opera':on_opera,'num_in_last_1_day':num_in_last_1_day,\
		'dir_rep_form':DirectResponseForm(with_id=True),'thin_rep_form':DirectResponseForm(thin_strip=True),\
		'latest_dir_rep':retrieve_latest_direct_reply(user_id=own_id),'is_auth':is_auth,'sk':secret_key,\
		'time_now':time_now}#

		next_page_number = page_num+1 if page_num<max_pages else 1
		previous_page_number = page_num-1 if page_num>1 else max_pages
		context["page"] = {'number':page_num,'has_previous':True if page_num>1 else False,'has_next':True if page_num<max_pages else False,\
		'previous_page_number':previous_page_number,'next_page_number':next_page_number,'max_pages':max_pages}
		
		if own_id:
			# only pass these if user is logged in
			context['ident'] = own_id
			context['newbie_lang'] = newbie_lang
			context['newbie_flag'] = newbie_flag
			context['mobile_verified'] = mobile_verified
			context['dir_rep_invalid'] = request.session.pop("dir_rep_invalid"+str(own_id),None)
			context['uname_rep_sent_to'] = request.session.pop("dir_rep_sent"+str(own_id),None)
			context['obj_type_rep_sent_to'] = request.session.pop("dir_rep_tgt_obj_type"+str(own_id),None)
			context['parent_obj_id_rep_sent_to'] = request.session.pop("dir_rep_tgt_obj_id"+str(own_id),None)
			if newbie_flag:
				context["newbie_tutorial_page"] = 'tutorial3.html'# hardcoding to tutorial 3

		else:
			# supporting images that have been indexed by search engines (but hidden by the op)
			context["orp_img_file"] = request.session.pop('image_file','')
			context["orp_img_cap"] = request.session.pop('image_caption','')
			context["orp_img_alt_txt"] = request.session.pop('alt_text','')
			context["orp_img_ratio"] = request.session.pop('img_ratio','100')

		return render(request,"photos_page.html",context)
	else:
		raise Http404("Such a photo listing does not exist")


##################################################################


def show_templates(request):
	"""
	Renders templates that can be downloaded for creating original content
	"""
	on_fbs = request.META.get('HTTP_X_IORG_FBS',False)
	on_opera = request.is_opera_mini
	is_js_env = retrieve_user_env(opera_mini=on_opera, fbs = on_fbs)
	# on_opera = True if (not on_fbs and not is_js_env) else False
	if on_opera:
		# disallowing opera mini users from posting public text posts
		# mislabeled template - used to show some generic errors and such to posters
		return render(request, 'error_photo.html', {'opera_detected':True})
	else:
		return render(request,"content/content_templates.html",{})


def public_photo_upload_denied(request):
	"""
	Helper view for upload_public_photo
	"""
	which_msg = request.session.pop("public_photo_upload_denied",None)
	if which_msg == '0':
		ttl = request.session.pop("public_photo_upload_fbs_ttl",None)
		return render(request,'big_photo_fbs.html',{'rate_limited':True,'ttl':ttl})
	elif which_msg == '1':
		return render(request,"dont_click_again_and_again.html",{'from_public_photos':True,'from_ecomm':False})
	elif which_msg == '2':
		return render(request,"verification/unable_to_submit_without_verifying.html",{'upload_public_photo':True})
	elif which_msg in ('3','4'):
		ban_details = request.session.pop('public_photo_upload_denied_details',None)
		time_remaining = request.session.pop("public_photo_upload_denied_time_togo",None)
		return render(request, 'upload_public_photo.html', {'time_remaining': time_remaining,'ban_details':ban_details,'forbidden':True,'defender':None,\
			'own_profile':True})
	elif which_msg == '5':
		time_remaining = request.session.pop("public_photo_upload_rate_limit_ttl",None)
		type_of_rate_limit = request.session.pop("public_photo_upload_rate_limit_torl",None)
		return render(request, 'error_photo.html', {'time':time_remaining,'tp':type_of_rate_limit,'sharing_limit':NUM_SUBMISSION_ALLWD_PER_DAY})
	elif which_msg == '6':
		return render(request,'big_photo_fbs.html',{'pk':'pk'})
	elif which_msg == '7':
		return render(request,'big_photo_regular.html',{'pk':'pk'})
	elif which_msg == '8':
		pk = request.session.pop("public_photo_upload_denied_photo_pk",None)
		if pk:
			try:
				photo = Link.objects.get(id=int(pk))
				return render(request, 'duplicate_photo.html', {'photo': photo, 'is_star': is_image_star(user_id=photo.submitter_id)})
			except Link.DoesNotExist:
				return render(request, 'big_photo.html', {'photo':'photo'})
		else:
			return redirect("missing_page")
	elif which_msg == '9':
		return render(request, 'mehfil/notify_and_redirect.html',{'is_pub_photo':True,'img_too_big':True})
	elif which_msg == '10':
		return redirect("error")
	elif which_msg == '11':
		return render(request,'big_photo_regular.html',{'too_narrow':True})
	elif which_msg == '12':
		# the photo doesn't have a title
		caption_error = request.session.pop("public_photo_upload_denied_caption_error",None)
		image_error = request.session.pop("public_photo_upload_denied_image_error",None)
		return render(request,'error_pic.html',{'caption_error':caption_error,'image_error':image_error})
	else:
		raise Http404("Unknown photo upload error")



@csrf_protect
def upload_public_photo(request,*args,**kwargs):
	"""
	Responsible for rendering photo upload page and processing the submitted photo
	"""
	on_fbs = request.META.get('HTTP_X_IORG_FBS',False)
	is_ajax = request.is_ajax()
	if request.method == 'POST':
		time_now = time.time()
		user = request.user
		user_id = user.id
		if on_fbs:
			is_fbs_rate_limited, ttl = is_fbs_user_rate_limited_from_photo_upload(user_id)
		else:
			is_fbs_rate_limited, ttl = None, None
		if is_fbs_rate_limited:
			################### Retention activity logging ###################
			if user_id > SEGMENT_STARTING_USER_ID:
				activity_dict = {'m':'POST','act':'P1.i','t':time_now}# defines what activity just took place
				log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
			##################################################################
			request.session["public_photo_upload_fbs_ttl"] = ttl
			request.session["public_photo_upload_denied"] = '0'
			request.session.modified = True
			if is_ajax:
				return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
			else:
				return redirect('public_photo_upload_denied')
		else:
			mob_verified = request.mobile_verified
			secret_key_from_form, secret_key_from_session = request.POST.get('sk','0'), get_and_delete_photo_upload_key(user_id)
			if str(secret_key_from_form) != str(secret_key_from_session):
				request.session["public_photo_upload_denied"] = '1'
				request.session.modified = True
				if is_ajax:
					return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
				else:
					return redirect('public_photo_upload_denied')
			elif not mob_verified:
				################### Retention activity logging ###################
				if user_id > SEGMENT_STARTING_USER_ID:
					activity_dict = {'m':'POST','act':'P1.u','t':time_now}# defines what activity just took place
					log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
				##################################################################
				# only verified users can upload a photo
				request.session["public_photo_upload_denied"] = '2'
				request.session.modified = True
				if is_ajax:
					return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
				else:
					return redirect('public_photo_upload_denied')
			elif request.user_banned:
				request.session["public_photo_upload_denied"] = '10'
				request.session.modified = True
				if is_ajax:
					return HttpResponse(json.dumps({'success':False,'message':reverse('error')}),content_type='application/json',)
				else:
					return redirect("error") #errorbanning
			else:
				ttl, type_of_rate_limit = content_sharing_rate_limited(user_id)
				banned, time_remaining, ban_details = check_content_and_voting_ban(user_id, with_details=True)
				if ttl:
					request.session["public_photo_upload_rate_limit_ttl"] = ttl
					request.session["public_photo_upload_rate_limit_torl"] = type_of_rate_limit
					request.session["public_photo_upload_denied"] = '5'
					request.session.modified = True
					if is_ajax:
						return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
					else:
						return redirect('public_photo_upload_denied')
				elif banned:
					request.session["public_photo_upload_denied_details"] = ban_details
					request.session["public_photo_upload_denied_time_togo"] = time_remaining
					request.session["public_photo_upload_denied"] = '3'
					request.session.modified = True
					if is_ajax:
						return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
					else:
						return redirect('public_photo_upload_denied')
				else:    
					form = UploadPhotoForm(request.POST,request.FILES)
					if form.is_valid():
						content_type = 'g'# can possibly be ['t','g'] where {'t':text,'g':img}
						image_file = request.FILES['image_file']
						caption = form.cleaned_data.get("caption",None)
						audience_type = form.cleaned_data['aud']# can possibly be ['a','s','p'] where {'a':all,'s':some,'p':public}
						expiry_type = form.cleaned_data['exp']# can possibly be ['i','m1','m2'] where {'i':immortal,'m':mortal}
						coms = form.cleaned_data['com']# can possibly be ['on','off']
						if expiry_type == 'm1':
							expiry_type = 'm'
							expire_in = LONG_LIVED_POST_TIME 
						elif expiry_type == 'm2':
							expiry_type = 'm'
							expire_in = SHORT_LIVED_POST_TIME
						else:
							expire_in = -1# i.e. never expire
					else:
						################### Retention activity logging ###################
						if user_id > SEGMENT_STARTING_USER_ID:
							activity_dict = {'m':'POST','act':'P1.i','t':time_now}# defines what activity just took place
							log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
						##################################################################
						error_dict = dict(form.errors)
						caption_error = error_dict.get('caption',[])
						image_error = error_dict.get('image_file',[])
						if is_ajax:
							request.session["public_photo_upload_denied"] = '12'
							request.session["public_photo_upload_denied_caption_error"] = caption_error[0] if caption_error else ''
							request.session["public_photo_upload_denied_image_error"] = image_error[0] if image_error else ''
							request.session.modified = True
							return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
						else:
							secret_key = str(uuid.uuid4())
							set_photo_upload_key(user_id, secret_key)
							return render(request,"upload_public_photo.html",{'form':form,'sk':secret_key,'sharing_limit':NUM_SUBMISSION_ALLWD_PER_DAY,\
								'num_fans':followers_exist(user_id)})
					if image_file:
						if on_fbs:
							if image_file.size > 200000:
								################### Retention activity logging ###################
								if user_id > SEGMENT_STARTING_USER_ID:
									activity_dict = {'m':'POST','act':'P1.i','t':time_now}# defines what activity just took place
									log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
								##################################################################
								request.session["public_photo_upload_denied"] = '6'
								request.session.modified = True
								if is_ajax:
									return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
								else:
									return redirect('public_photo_upload_denied')
						else:
							if image_file.size > 10000000:
								################### Retention activity logging ###################
								if user_id > SEGMENT_STARTING_USER_ID:
									activity_dict = {'m':'POST','act':'P1.i','t':time_now}# defines what activity just took place
									log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
								##################################################################
								request.session["public_photo_upload_denied"] = '7'
								request.session.modified = True
								if is_ajax:
									return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
								else:
									return redirect('public_photo_upload_denied')
						reoriented = request.POST.get('reoriented',None)
						resized = request.POST.get('resized',None)
						image_file_new, img_height, dup_photo_id, avghash = process_public_image(image=image_file, quality=None if on_fbs else True,already_resized=resized, \
						already_reoriented=reoriented)#, caption=request.POST.get('caption',None))
						if isinstance(dup_photo_id,float):
							################### Retention activity logging ###################
							if user_id > SEGMENT_STARTING_USER_ID:
								activity_dict = {'m':'POST','act':'P1.i','t':time_now}# defines what activity just took place
								log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
							##################################################################
							request.session["public_photo_upload_denied"] = '8'
							request.session["public_photo_upload_denied_photo_pk"] = dup_photo_id
							request.session.modified = True
							if is_ajax:
								return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
							else:
								return redirect('public_photo_upload_denied')
						elif img_height == 'too_high':
							################### Retention activity logging ###################
							if user_id > SEGMENT_STARTING_USER_ID:
								activity_dict = {'m':'POST','act':'P1.i','t':time_now}# defines what activity just took place
								log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
							##################################################################
							request.session["public_photo_upload_denied"] = '9'
							request.session.modified = True
							if is_ajax:
								return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
							else:
								return redirect('public_photo_upload_denied')
						elif img_height == 'too_narrow':
							################### Retention activity logging ###################
							if user_id > SEGMENT_STARTING_USER_ID:
								activity_dict = {'m':'POST','act':'P1.i','t':time_now}# defines what activity just took place
								log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
							##################################################################
							# this image is too narrow, don't upload it since it's probably low quality
							request.session["public_photo_upload_denied"] = '11'
							request.session.modified = True
							if is_ajax:
								return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
							else:
								return redirect('public_photo_upload_denied')
						else:
							image_file = image_file_new if image_file_new else None
					else:
						request.session["public_photo_upload_denied"] = '12'
						request.session.modified = True
						if is_ajax:
							return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
						else:
							return redirect('public_photo_upload_denied')
					################################################################################
					# upload the image
					image_alt_text, image_filename, add_to_sitemap = image_description_generator(caption=caption)
					image_url = upload_image_to_s3(image_file, prefix='follower/', with_thumb=True, filename=image_filename)

					post_data = {'ct':content_type,'aud':audience_type,'exp':expiry_type,'ein':expire_in,'d':caption,'iu':image_url,\
					'com':coms,'ih':avghash, 'alt':image_alt_text,'add_to_sitemap':add_to_sitemap}
					set_temp_post_data(user_id=user_id,data=json.dumps(post_data),post_type='img',obj_id=None)

					if audience_type == 's':
						request.session['request_location'+str(user_id)] = 'valid'
						if is_ajax:
							return HttpResponse(json.dumps({'success':True,'message':reverse('finalize_audience')}),content_type='application/json',)
						else:
							return redirect('finalize_audience')
					else:
						if is_ajax:
							return HttpResponse(json.dumps({'success':True,'message':reverse('publish_post')}),content_type='application/json',)
						else:
							return redirect('publish_post')
	else:
		# if it's a GET request
		on_opera = request.is_opera_mini
		is_js_env = retrieve_user_env(opera_mini=on_opera, fbs = on_fbs)
		# on_opera = True if (not on_fbs and not is_js_env) else False
		if on_opera:
			# disallowing opera mini users from posting public text posts
			# mislabeled template - used to show some generic errors and such to posters
			return render(request, 'error_photo.html', {'opera_detected':True})
		else:
			context, own_id = {}, request.user.id
			banned, time_remaining, ban_details = check_content_and_voting_ban(own_id, with_details=True)
			if banned:
				context["defender"] = None
				context["own_profile"] = True
				context["forbidden"] = True
				context["ban_details"] = ban_details
				context["time_remaining"] = time_remaining
				return render(request,"upload_public_photo.html",context)
			else:
				if on_fbs:
					is_fbs_rate_limited, ttl = is_fbs_user_rate_limited_from_photo_upload(own_id)
				else:
					is_fbs_rate_limited, ttl = None, None
				if is_fbs_rate_limited:
					request.session["public_photo_upload_fbs_ttl"] = ttl
					request.session["public_photo_upload_denied"] = '0'
					request.session.modified = True
					if is_ajax:
						return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
					else:
						return redirect('public_photo_upload_denied')
				else:
					################### Retention activity logging ###################
					if own_id > SEGMENT_STARTING_USER_ID:
						time_now = time.time()
						if request.mobile_verified:
							activity_dict = {'m':'GET','act':'PL','t':time_now}# defines what activity just took place
						else:
							activity_dict = {'m':'GET','act':'PL.u','t':time_now}# defines what activity just took place
						log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
					##################################################################
					ttl, type_of_rate_limit = content_sharing_rate_limited(own_id)

					if ttl:
						context["ttl"] = ttl

					context["show_instructions"] = True if tutorial_unseen(user_id=own_id, which_tut='26', renew_lease=True) else False
					context["form"] = UploadPhotoForm()
					secret_key = str(uuid.uuid4())
					context["sk"] = secret_key
					context["sharing_limit"] = NUM_SUBMISSION_ALLWD_PER_DAY
					context['num_fans']= followers_exist(own_id)
					set_photo_upload_key(own_id, secret_key)
					return render(request,"upload_public_photo.html",context)


##################################################################


class PhotoShareView(FormView):
	form_class = PhotoShareForm
	template_name = "photo_share_help.html"

	def get_context_data(self, **kwargs):
		context = super(PhotoShareView, self).get_context_data(**kwargs)
		try:
			loc = self.kwargs["loc"]
			context["loc"] = loc
			username = self.kwargs["slug"]
			context["username"] = username
		except:
			loc = '1'
			context["loc"] = loc
			username = None
		try:
			context["no_id"] = False
			pk = self.kwargs["pk"]
			context["ident"] = pk
			context["lid"] = 'img:'+str(pk)
			context["regular_url"] = "https://damadam.pk/photo_detail/"+str(pk)
			#context["freebasics_url"] = "https://https-damadam-pk.0.freebasics.com/photo_detail/"+str(pk)
		except:
			context["no_id"] = True
		if self.request.user.is_authenticated():
			context["authenticated"] = True
		else:
			context["authenticated"] = False
		return context

##################################################################


@ratelimit(rate='3/s')
def welcome_pk(request, pk=None, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		return redirect("missing_page")
	else:
		if pk.isdigit():
			request.session["welcome_pk"] = pk
			return redirect("welcome")
		else:
			return redirect("group_help")

class WelcomeView(FormView):
	form_class = WelcomeForm
	template_name = "welcome.html"

	def get_context_data(self, **kwargs):
		context = super(WelcomeView, self).get_context_data(**kwargs)
		try:
			target_user = User.objects.get(id=self.request.session["welcome_pk"])
			context["authenticated"] = True
			context["target_user"] = target_user
		except:
			context["authenticated"] = False
			context["target_user"] = []
		return context

class WelcomeMessageView(CreateView):
	model = Publicreply
	form_class = WelcomeMessageForm
	template_name = "welcome_message.html"

	def get_context_data(self, **kwargs):
		context = super(WelcomeMessageView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			try:
				pk = self.request.session["welcome_pk"]
				context["target_user"] = User.objects.get(id=pk)
				context["authorized"] = True
				context["option"] = self.kwargs["option"]
			except:
				context["authorized"] = False
				context["target_user"] = None
				context["option"] = None
		return context


def top_photo_help(request,*args,**kwargs):
	"""
	Shows help page regarding how to get into 'trending'
	"""
	################### Retention activity logging ###################
	user_id = request.user.id
	if user_id > SEGMENT_STARTING_USER_ID:
		time_now = time.time()
		act = 'Z10' if request.mobile_verified else 'Z10.u'
		activity_dict = {'m':'GET','act':act,'t':time_now}# defines what activity just took place
		log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
	##################################################################
	return render(request,'top_photo_help.html',{'list_size':TRENDER_RANKS_TO_COUNT})


def private_or_expired(request):
	"""
	Renders a notice if post has expired or is not accessible for user
	"""
	# To Do: Uncomment context variables if error screen is to be customized
	# context = {'privacy_settings':request.session.pop('privacy_setting',None),'viewable_status':request.session.pop('viewable_flag',None)}
	return render(request,"follow/private_or_expired.html")#,context)


def check_if_post_is_viewable(user_id, post_attributes):
	"""
	Checks whether visitor can view a post (it may be limited because of audience, expiry or both). Useful when rendering 'reply' pages and/or 'detail' pages
	
	Return values:
	'0' - 'post inaccessible (no right to view)'
	'1' - 'post removed (but partially accessible)' 
	'2' - 'post expired (but partially accessible)'
	'3' - 'post fully accessible'
	"""
	privacy_setting = 'limited'# default value
	delete_status = post_attributes['delete_status']# '0' or '1'
	submitter_id = post_attributes['submitter_id']
	expireat = post_attributes['expire_at']# None or a float value
	audience = post_attributes['audience']# 'p', 'a' or 's'

	# if the user is viewing own post
	if user_id == submitter_id:
		
		if delete_status == '1':
			# can only view in 'removed' form since it's removed
			return privacy_setting, '1'

		elif expireat:

			if expireat > time.time():
				# can view the full form of the post
				return privacy_setting, '3'

			else:
				# can only view 'partial' (expired) form of the post
				return privacy_setting, '2'

		else:
			# can fully view the non-expiring post
			return privacy_setting, '3'

	##########
	# TODO: is this patch working?
	# Is user_id allowed to view this post?
	elif audience == 'p':

		if delete_status == '1':
			# can only view in 'removed' form since OP removed it
			return privacy_setting, '1'
		
		else:
			# can fully view the post
			if expireat:
				if expireat < time.time():
					return privacy_setting, '2'
				else:
					return privacy_setting, '3'	
			else:
				privacy_setting = 'unlimited'
				return privacy_setting, '3'

	##########

	elif audience == 'a':
		
		is_follower = check_if_follower(user_id,submitter_id,with_db_lookup=True)

		if is_follower:
			# there is a possibility this post is viewable for user_id

			if delete_status == '1':
				# can only view in 'removed' form since OP removed it
				return privacy_setting, '1'
			
			# the post is not deleted and has an expiry time associated to it
			elif expireat:

				# this post has not expired, user_id can fully view it
				if expireat > time.time():
					return privacy_setting, '3'
				
				# this post has expired, user_id can view it in expired form
				else:
					return privacy_setting, '2'
			
			# this post has no expiry, user_id can fully view it
			else:
				return privacy_setting, '3'
		
		# not a follower		
		else:
			# post is not viewable at all (not even comments) since user_id is not a follower
			return privacy_setting, '0'

	##########
	elif audience == 's':

		is_follower = check_if_follower(user_id,submitter_id,with_db_lookup=True)
		
		if is_follower:
			obj_hash = post_attributes['obj_hash']# the hash_name of the obj
			is_user_id_permitted_to_view = can_follower_view_post(user_id,obj_hash)

			# user_id is part of selection of users who can view this post
			if is_user_id_permitted_to_view:
				
				if delete_status == '1':
					# can only view in 'removed' form since OP removed it
					return privacy_setting, '1'

				# the post is not deleted and has an expiry time associated to it
				elif expireat:

					# this post has not expired, user_id can fully view it
					if expireat > time.time():
						return privacy_setting, '3'

					# this post has expired, user_id can view it in expired form
					else:
						return privacy_setting, '2'

				# this post has no expiry, user_id can fully view it
				else:
					return privacy_setting, '3'

			# this user does not have the requisite perm to view this post although they're a follower
			else:
				return privacy_setting, '0'
		
		# not a follower
		else:
			# post is not viewable at all (not even comments) since user_id is not a follower
			return privacy_setting, '0'



class UserSettingDetailView(DetailView):
	model = get_user_model()
	slug_field = "username"
	template_name = "user_detail.html"

	def get_object(self, queryset=None):
		user = super(UserSettingDetailView, self).get_object(queryset)
		UserSettings.objects.get_or_create(user=user)
		return user


class UserProfileEditView(UpdateView):
	model = UserProfile
	form_class = UserProfileForm
	template_name = "edit_profile.html"


	def get_initial(self):#initial is a keyword argument to a formfield that enables pre-filling in the formfield
		"""
		Returns the initial data to use for forms on this view.
		"""
		bio = UserProfile.objects.only('bio').get(user_id=self.request.user.id).bio
		context = {}
		context['bio'] = bio if bio else 'I am a Damadamian'
		return context# initial needs to be passed a dictionary

	
	def get_form_kwargs(self):
		"""
		Returns the keyword arguments for instantiating the form.
		"""
		kwargs = super(UserProfileEditView, self).get_form_kwargs()
		kwargs.update({'user': self.request.user,'on_fbs':self.request.META.get('HTTP_X_IORG_FBS',False)})
		return kwargs

	def get_object(self, queryset=None):
		return UserProfile.objects.get_or_create(user=self.request.user)[0]

	def get_context_data(self, **kwargs):
		own_id = self.request.user.id
		context = super(UserProfileEditView, self).get_context_data(**kwargs)
		context["is_own_profile"] = True
		context["cities"] = CITY_TUP_LIST
		context["streak"] =  UserProfile.objects.only('streak').get(user_id=own_id).streak
		context["zodiac"] =  UserProfile.objects.only('attractiveness').get(user_id=own_id).attractiveness
		context["username"] = retrieve_uname(own_id,decode=True)
		################### Retention activity logging ###################
		from_redirect = self.request.session.pop("rd",None)
		if not from_redirect and own_id > SEGMENT_STARTING_USER_ID:
			time_now = time.time()
			act = 'D' if self.request.mobile_verified else 'D.u'
			activity_dict = {'m':'GET','act':act,'t':time_now}# defines what activity just took place
			log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
		##################################################################
		return context

	def form_invalid(self, form):
		"""
		If the form is invalid, log the data point (if need be)
		"""
		################### Retention activity logging ###################
		user_id = self.request.user.id
		time_now = time.time()
		if user_id > SEGMENT_STARTING_USER_ID:
			self.request.session['rd'] = '1'
			act = 'D.i' if self.request.mobile_verified else 'D.u.i'
			activity_dict = {'m':'POST','act':act,'t':time_now}# defines what activity just took place
			log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
		##################################################################
		return self.render_to_response(self.get_context_data(form=form))

	def form_valid(self, form):
		time_now = time.time()
		user_id = self.request.user.id
		f = form.save(commit=False) #getting form object, and telling database not to save (commit) it just yet
		zodiac_value = f.attractiveness# using 'attractiveness' attribute for legacy reasons
		city_value = f.streak# using 'streak' attribute for legacy reasons
		set_attribute_change_rate_limit(user_id, zodiac_value, city_value, time_now)
		################### Retention activity logging ###################
		if user_id > SEGMENT_STARTING_USER_ID:
			self.request.session['rd'] = '1'
			if f.avatar.name == 'temp.jpg':
				# new avatar uploaded
				act = 'D1' if self.request.mobile_verified else 'D1.u'
				activity_dict = {'m':'POST','act':act,'t':time_now}# defines what activity just took place
				log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
			old_bio = UserProfile.objects.only('bio').get(user_id=user_id).bio
			if f.bio != old_bio:
				# bio has been updated
				act = 'D2' if self.request.mobile_verified else 'D2.u'
				activity_dict = {'m':'POST','act':act,'t':time_now}# defines what activity just took place
				log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
		##################################################################
		return super(UpdateView, self).form_valid(form) # saves automatically


class UserSettingsEditView(UpdateView):
	model = UserSettings
	form_class = UserSettingsForm
	template_name = "edit_settings.html"

	def get_object(self, queryset=None): #loading the current state of settings
		return UserSettings.objects.get_or_create(user=self.request.user)[0]

	def get_success_url(self): #which URL to go back once settings are saved?
		return reverse_lazy("user_profile", kwargs={'slug': self.request.user})

# @ratelimit(rate='7/s')
def sharing_help(request):
	"""
	Renders a page about sharing ettiquette
	"""
	################### Retention activity logging ###################
	own_id = request.user.id
	if own_id > SEGMENT_STARTING_USER_ID:
		time_now = time.time()
		act = 'H' if request.mobile_verified else 'H.u'
		activity_dict = {'m':'GET','act':act,'t':time_now}# defines what activity just took place
		log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
	##################################################################
	return render(request,"content/share_content_help.html",{})


#@ratelimit(rate='7/s')
def share_content(request):
	"""
	Renders content sharing page, from where would-be sharer can select 'photo' or 'text' type sharing

	Redirects to text or photo sharing pages accordingly
	"""
	################### Retention activity logging ###################
	own_id = request.user.id
	if own_id > SEGMENT_STARTING_USER_ID:
		time_now = time.time()
		act = 'XP' if request.mobile_verified else 'XP.u'
		activity_dict = {'m':'GET','act':act,'t':time_now}# defines what activity just took place
		log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
	##################################################################
	return render(request,"content/share_content.html",{'first_time':True if tutorial_unseen(user_id=request.user.id, which_tut='25',\
	renew_lease=True) else False})


# @ratelimit(rate='7/s')
def link_create_pk(request, *args, **kwargs):
	"""
	Unused
	"""
	request.session["link_create_token"] = str(uuid.uuid4())
	return redirect("link_create")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def submit_text_post(request):
	"""
	Submit public textual post
	"""
	time_now = time.time()
	own_id = request.user.id
	mobile_verified = request.mobile_verified
	on_fbs = request.META.get('HTTP_X_IORG_FBS',False)
	if request.method == "POST":
		banned, time_remaining, ban_details = check_content_and_voting_ban(own_id, with_details=True)
		if banned:
			return render(request, 'links/link_form.html', {'time_remaining': time_remaining,'ban_details':ban_details,'forbidden':True,\
				'own_profile':True,'defender':None,'is_profile_banned':True})
		else:
			ttl, type_of_rate_limit = content_sharing_rate_limited(own_id)
			if not mobile_verified:
				################### Retention activity logging ###################
				if own_id > SEGMENT_STARTING_USER_ID:
					activity_dict = {'m':'POST','act':'X1.u','t':time_now,'tx':request.POST.get("description",None)}# defines what activity just took place
					log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
				##################################################################
				return render(request, 'verification/unable_to_submit_without_verifying.html', {'share_on_home':True})
			elif request.user_banned:
				return redirect("error")
			elif ttl:
				return render(request, 'error_photo.html', {'time':ttl,'origin':'1','tp':type_of_rate_limit,\
				'sharing_limit':NUM_SUBMISSION_ALLWD_PER_DAY})# this is wrongly named, but tells the user to wait
			else:
				form = LinkForm(request.POST,user_id=own_id)#, on_fbs=on_fbs, on_opera=on_opera)
				if form.is_valid():
					########################### Retrieve Post Settings ############################
					content_type = 't'# can possibly be ['t','g'] where {'t':text,'g':img}
					audience_type = form.cleaned_data['aud']# can possibly be ['a','s','p'] where {'a':all,'s':some,'p':public}
					expiry_type = form.cleaned_data['exp']# can possibly be ['i','m1','m2'] where {'i':immortal,'m':mortal}
					com = form.cleaned_data['com']# can possibly be ['1','0']
					if expiry_type == 'm1':
						expiry_type = 'm'
						expire_in = LONG_LIVED_POST_TIME 
					elif expiry_type == 'm2':
						expiry_type = 'm'
						expire_in = SHORT_LIVED_POST_TIME
					else:
						expire_in = -1
					########################### Retrieve Post Details #########################
					description = form.cleaned_data['description']
					alignment = form.cleaned_data['alignment']
					topic_payload = form.cleaned_data['tpay']
					topic_url = form.cleaned_data['turl']
					topic_name = form.cleaned_data['tname']
					topic_bg = form.cleaned_data['bgt']
					####################### Create Postgresql Footprint ########################
					post_data = {'ct':content_type,'aud':audience_type,'exp':expiry_type,'com':com,'ein':expire_in,'d':description,\
					'a':alignment,'tp':topic_payload,'turl':topic_url,'tn':topic_name,'tbg':topic_bg}
					set_temp_post_data(user_id=own_id,data=json.dumps(post_data),post_type='tx',obj_id=None)
					if audience_type == 's':
						request.session['request_location'+str(own_id)] = 'valid'
						return redirect("finalize_audience")
					
					else:
						return redirect ('publish_post')
					#########################################################

				else:
					# form is invalid
					################### Retention activity logging ###################
					if own_id > SEGMENT_STARTING_USER_ID:
						activity_dict = {'m':'POST','act':'X1.i','t':time_now,'tx':request.POST.get("description",None)}# defines what activity just took place
						log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
					##################################################################
					secret_key = str(uuid.uuid4())
					set_text_input_key(own_id, '1', 'likho', secret_key)
					return render(request,"links/link_form.html",{'form':form,'sk':secret_key,'sharing_limit':NUM_SUBMISSION_ALLWD_PER_DAY,\
						'random':random.sample(xrange(1,188),15),'subscribed_topics':retrieve_subscribed_topics(str(own_id)),\
						'num_fans':followers_exist(own_id)})
	else:
		on_opera = request.is_opera_mini
		is_js_env = retrieve_user_env(opera_mini=on_opera, fbs = on_fbs)
		# on_opera = True if (not on_fbs and not is_js_env) else False
		if on_opera:
			# disallowing opera mini users from posting public text posts
			# mislabeled template - used to show some generic errors and such to posters
			return render(request, 'error_photo.html', {'opera_detected':True})
		else:
			banned, time_remaining, ban_details = check_content_and_voting_ban(own_id, with_details=True)
			if banned:
				context = {'time_remaining':time_remaining,'ban_details':ban_details,'forbidden':True, 'own_profile':True, 'defender':None,\
				'is_profile_banned':True}
			else:
				################### Retention activity logging ###################
				if own_id > SEGMENT_STARTING_USER_ID:
					if mobile_verified:
						activity_dict = {'m':'GET','act':'XL','t':time_now}# defines what activity just took place
					else:
						activity_dict = {'m':'GET','act':'XL.u','t':time_now}# defines what activity just took place
					log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
				##################################################################
				secret_key = str(uuid.uuid4())
				set_text_input_key(own_id, '1', 'likho', secret_key)
				context = {'sk':secret_key,'sharing_limit':NUM_SUBMISSION_ALLWD_PER_DAY,'random':random.sample(xrange(1,188),15),\
				'show_instructions':True if tutorial_unseen(user_id=own_id, which_tut='11', renew_lease=True) else False,'form':LinkForm(),\
				'subscribed_topics':retrieve_subscribed_topics(str(own_id)),'num_fans':followers_exist(own_id)}
			return render(request,"links/link_form.html",context)


def finalize_audience(request):
	"""
	Finalize relative audience from selected followers
	"""
	own_id = request.user.id
	if request.method == "POST":
		selected_follower_ids = request.POST.getlist('fids',[])# contains group_ids in list format
		if selected_follower_ids:
			# some followers were selected - check other stuff
			all_follower_ids = request.session.pop('all_follower_ids'+str(own_id),None)
			real_selected_follower_ids = [int(x) for x in selected_follower_ids if int(x) in all_follower_ids]
			total_followers = request.session.pop('num_followers'+str(own_id),None)
			if len(real_selected_follower_ids) == total_followers:
				if total_followers > 1:
					# this poster selected all followers - they should simply have used the 'all followers' option - notify them accordingly
					request.session['follower_selection_err'+str(own_id)] = 'selected_all'
					request.session['request_location'+str(own_id)] = 'valid'
					return redirect("finalize_audience")
				else:
					if real_selected_follower_ids:
						request.session['selected_follower_ids'+str(own_id)] = real_selected_follower_ids 
						return redirect("publish_post")
					else:
						# no followers were selected - show relevant validation error alongwith the follower list again
						request.session['follower_selection_err'+str(own_id)] = 'selected_invalid_followers_only'
						request.session['request_location'+str(own_id)] = 'valid'
						return redirect("finalize_audience")
			else:
				if real_selected_follower_ids:
					request.session['selected_follower_ids'+str(own_id)] = real_selected_follower_ids 
					return redirect("publish_post")
				else:
					# no followers were selected - show relevant validation error alongwith the follower list again
					request.session['follower_selection_err'+str(own_id)] = 'selected_invalid_followers_only'
					request.session['request_location'+str(own_id)] = 'valid'
					return redirect("finalize_audience")
		else:
			# no followers were selected - show relevant validation error alongwith the follower list again
			request.session['follower_selection_err'+str(own_id)] = 'selected_none'
			request.session['request_location'+str(own_id)] = 'valid'
			return redirect("finalize_audience")
		# return render(request,'follow/select_followers.html',{'all_followers':alphabetically_sorted_followers,\
		# 		'num_followers':num_followers,'on_fbs':request.META.get('HTTP_X_IORG_FBS',False)})
	else:
		is_valid = request.session.pop('request_location'+str(own_id),None)
		if is_valid:
			context = {}
			final_data = []
			final_data_last_selected = []
			previously_selected_list = False
			err_type = request.session.pop('follower_selection_err'+str(own_id),None)
			if err_type:
				#'form invalid' type error exists
				context["err_type"] = err_type

			# default case
			############################################################################
			all_followers, num_followers = retrieve_follower_data(user_id=own_id,with_follower_count=True)

			follower_ids = [(follower_id) for follower_id, follow_time, username, avurl, is_new in all_followers]

			if follower_ids:	
				request.session['all_follower_ids'+str(own_id)] = follower_ids	
				last_selected_followers = list(get_last_post_selected_followers(own_id))
				real_last_selected_followers = [int(x) for x in last_selected_followers if int(x) in follower_ids]
				
				if real_last_selected_followers:
					previously_selected_list = True
					follower_ids = list(set(follower_ids) - set(real_last_selected_followers))
					
					real_last_selected_follower_ids_and_ages = [(selected_follower_id,1) for selected_follower_id in real_last_selected_followers]
					follower_ids_and_ages = [(follower,1) for follower in follower_ids]

					selected_username_data = retrieve_bulk_unames(real_last_selected_followers, decode=True)
					username_data = retrieve_bulk_unames(follower_ids, decode=True)

					final_data_last_selected = create_sorted_online_list(selected_username_data, real_last_selected_follower_ids_and_ages)
					final_data = create_sorted_online_list(username_data, follower_ids_and_ages)

				else:	
					follower_ids_and_ages = [(follower,1) for follower in follower_ids]	
					if follower_ids_and_ages:
						username_data = retrieve_bulk_unames(follower_ids, decode=True)
						final_data = create_sorted_online_list(username_data, follower_ids_and_ages)
						request.session['all_follower_ids'+str(own_id)] = follower_ids
			
			# alphabetically_sorted_followers = create_sorted_invitee_list(username_data=follower_id_and_uname_dict, user_ids=follower_ids)
			request.session['num_followers'+str(own_id)] = num_followers#len(follower_ids_and_unames)
			if previously_selected_list:
				context["previously_selected_list"] = previously_selected_list
				context["previously_selected_followers"] = final_data_last_selected
			context["all_followers"] = final_data
			context["num_followers"] = num_followers
			context["on_fbs"] = request.META.get('HTTP_X_IORG_FBS',False)
			context['bottom']=len(final_data)

			return render(request,'follow/select_followers.html',context)
		else:
			raise Http404("Not a valid request")


def publish_post(request):
	"""
	This saves a finalized post to Postgres (for poster history) and various redis feeds (public feeds for all consumers, or private feeds for followers)
	"""
	own_id = request.user.id
	temporarily_saved_json_data = get_temp_post_data(own_id)
	if temporarily_saved_json_data:
		temporarily_saved_data = json.loads(temporarily_saved_json_data)
	else:
		temporarily_saved_data = None
	if temporarily_saved_data:
		# proceed
		audience, expiry, coms = temporarily_saved_data['aud'], temporarily_saved_data['exp'], temporarily_saved_data['com']
		description, alignment = temporarily_saved_data['d'], temporarily_saved_data.get('a',None)
		img_url, img_avghash = temporarily_saved_data.get('iu',None), temporarily_saved_data.get('ih',None) 
		img_alt_text, add_img_to_sitemap = temporarily_saved_data.get('alt',''), temporarily_saved_data.get('add_to_sitemap',False)
		img_height, img_width = temporarily_saved_data.get('img_height',None), temporarily_saved_data.get('img_width',None) 
		content_type = temporarily_saved_data['ct'] 
		topic_name, topic_url, topic_bg, topic_payload = temporarily_saved_data.get('tn',None), temporarily_saved_data.get('turl',None), \
		temporarily_saved_data.get('tbg',None), temporarily_saved_data.get('tp',None)
		origin = temporarily_saved_data.get('origin',None)
		add_to_public_feed, add_to_photo_feed, post_to_all_followers = False, False, False
		expire_in = temporarily_saved_data.get('ein',-1)# only use in audience type 'a' and 's'
		time_now = time.time()
		expire_at = expire_in+time_now if expire_in > 0 else None
		on_fbs = request.META.get('HTTP_X_IORG_FBS',False)
		is_star = is_image_star(user_id=own_id)
		#######################################################################

		if content_type == 't':

			#######################################################################
			# Step 1) Categorize objects and invalidate caching
			
			if topic_payload:
				obj = Link.objects.create(description=description, submitter_id=own_id, cagtegory=alignment, is_visible=False, \
					url=topic_payload if topic_payload else '', trending_status='0',comment_status=coms, delete_status='0',\
					type_of_content='t',audience=audience, mortality=expiry, expire_at=expire_at)
			else:
				obj = Link.objects.create(description=description, submitter_id=own_id, cagtegory=alignment, is_visible=False,\
				trending_status='0', comment_status=coms, delete_status='0', type_of_content='t',audience=audience, mortality=expiry,\
				expire_at=expire_at) 

			obj_id = obj.id
		
			if audience == 'p':
				if expiry == 'i':
					type_of_object = ('t','p','i')#'gai'
				
				elif expiry == 'm':
					type_of_object = ('t','p','m')#'gam'

				# invalidate_cached_user_feed_history(own_id, 'public')# all 'p' type posts are 'public'
				# add_to_public_feed = True
				# post_to_all_followers = True

			elif audience == 'a':
				# post_to_all_followers = True
				
				# if expiry == 'i':
				# 	type_of_object = ('t','a','i')#'tai'
				# 	invalidate_cached_user_feed_history(own_id, 'limited')# all 't','a','i' type posts are 'limited'
				
				# elif expiry == 'm':
				# 	type_of_object = ('t','a','m')#'tam'
				# 	invalidate_cached_user_feed_history(own_id, 'limited')# all posts apart from 't','p' and 't','a','i' are 'private' in user feed history
				
				# else:
				# 	# not a valid expiry type
				raise Http404("Not a valid audience type")

			elif audience == 's':
				# if expiry == 'i':
				# 	type_of_object = ('t','s','i')#'tsi'
				# 	invalidate_cached_user_feed_history(own_id, 'private')

				# elif expiry == 'm':
				# 	type_of_object = ('t','s','m')#'tsm'
				# 	invalidate_cached_user_feed_history(own_id, 'private')

				# else:
					# not a valid expiry type
				raise Http404("Not a valid audience type")
			
			else:
				raise Http404("Not a valid audience type")	
			
			invalidate_cached_user_feed_history(own_id, 'public')# all 'p' type posts are 'public'
			add_to_public_feed = True
			post_to_all_followers = True

			#######################################################################
			# Step 2) Handle Redis Object(s)
			obj_hash = "tx:"+str(obj_id)
			submitter_name, av_url = retrieve_credentials(own_id,decode_uname=True)
			if topic_payload:
				log_text_submissions('topic')#Logs the number of submisions in topic vs number of submissions of regular text posts
				add_topic_post(obj_id=obj_id, obj_hash=obj_hash, categ=alignment, submitter_id=str(own_id), \
					submitter_av_url=av_url, is_star=is_star, submission_time=time_now, text=description, \
					from_fbs=on_fbs, topic_url=topic_url, topic_name=topic_name, bg_theme=topic_bg, \
					add_to_public_feed=add_to_public_feed,submitter_username=submitter_name,\
					type_of_object=type_of_object, poster_defined_expiry_time=expire_at,comments=coms)#type_of_object
				
				################### Retention activity logging ###################
				from_topic = request.session.pop('ft',None)
				if not from_topic and own_id > SEGMENT_STARTING_USER_ID:
					request.session['rd'] = '1'
					if expiry == 'm':
						# mortal post
						if coms == '1':
							# comments are on
							act = 'X3.t'
						elif coms == '0':
							# comments are off
							act = 'X4.t'
					elif expiry == 'i':
						# immportal post
						if coms == '1':
							# comments are on
							act = 'X1.t'
						elif coms == '0':
							# comments are off
							act = 'X2.t'
					activity_dict = {'m':'POST','act':act,'t':time_now,'tx':description,'url':topic_url}# defines what activity just took place
					log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
				##################################################################
			else:
				log_text_submissions('text')
				add_text_post(obj_id=obj_id, categ=alignment, submitter_id=own_id, submitter_av_url=av_url, \
					submitter_username=submitter_name, submission_time=time_now, add_to_feed=add_to_public_feed, \
					is_star=is_star, text=description, from_fbs=on_fbs, type_of_object=type_of_object, \
					poster_defined_expiry_time=expire_at,comments=coms)#type_of_object
				
				log_recent_text(user_id=own_id, description=description)# useful for text content rep creation, duplicate checks, etc
				
				################### Retention activity logging ###################
				if own_id > SEGMENT_STARTING_USER_ID:
					request.session['rd'] = '1'
					if expiry == 'm':
						# mortal post
						if coms == '1':
							# comments are on
							act = 'X3'
						elif coms == '0':
							# comments are off
							act = 'X4'
					elif expiry == 'i':
						# immportal post
						if coms == '1':
							# comments are on
							act = 'X1'
						elif coms == '0':
							# comments are off
							act = 'X2'
					activity_dict = {'m':'POST','act':act,'t':time_now,'tx':description}# defines what activity just took place
					log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
				##################################################################

			if post_to_all_followers:
				# fan_out_to_followers(own_id,obj_hash,time_now,expire_at=expire_at,follower_list=None)
				post_to_followers(own_id,obj_hash,time_now,expire_at=expire_at,follower_list=None)
		
			else:
				selected_follower_ids = request.session.pop('selected_follower_ids'+str(own_id),None)
				if selected_follower_ids:
					post_to_followers(own_id,obj_hash,time_now, expire_at=expire_at,follower_list=selected_follower_ids)
					# fan_out_to_followers(own_id,obj_hash,time_now, expire_at=expire_at,follower_list=selected_follower_ids)
				else:
					# No selected followers exist - redirect to sharing page with the requisite prompt
					raise Http404("No selected followers exist")

			#######################################################################
			# Step 3) Set requisite rate-limits and such
			rate_limit_content_sharing(own_id, set_long_ratelimit=add_to_public_feed)#rate limiting for 5 mins (and hard limit set at 50 submissions per day)

			#######################################################################
			

			###########################################################################
			############################### Post Logger ###############################
			###########################################################################
			# num_fans = get_all_follower_count(own_id)
			# num_vfans = get_verified_follower_count(own_id)
			# data = {'aud':audience,'exp':expiry,'coms':coms, 'desc':description,'align':alignment,'uid':own_id, 'top':topic_name, 'orig':origin, \
			# 'Lid':obj_id,'expt':expire_at,'numf':num_fans,'num_vf':num_vfans,'image':'NA'}
			# logging_post_data(data)
			###########################################################################
			###########################################################################	
			###########################################################################

			# Step 4a) redirect to topic home if from topic
			if origin =='from_topic_page':
				#redirect to the original topic page
				return redirect("topic_redirect", topic_url=topic_url, obj_hash=obj_hash)
			else:
				if audience == 'p':
			# Step 4b) redirect to the kind of audience the post was targetted at
					return redirect("display_user_public_feed_history",submitter_name)# redirecting to own profile
				elif audience == 'a':
					return redirect("display_user_follower_feed_history",submitter_name)# redirecting to own profile
				elif audience == 's':
					return redirect("display_user_private_feed_history",submitter_name)# redirecting to own profile
				else:
					return redirect("display_user_public_feed_history",submitter_name)# redirecting to own profile

		#######################################################################

		elif content_type == 'g':
			# handle images

			#######################################################################
			# Step 1) Categorize objects and invalidate caching

			obj = Link.objects.create(image_file=img_url, submitter_id=own_id, description=description, is_visible=False,\
				trending_status='0',comment_status=coms,delete_status='0',type_of_content='g',audience=audience,\
				mortality=expiry,expire_at=expire_at,web_link=img_alt_text)# web_link used as a store for image's 'alt' description

			obj_id = obj.id
			img_height, img_width = obj.image_file.height, obj.image_file.width
			cache_photo_dim(str(obj_id),img_height,img_width)

			if audience == 'p':
				if expiry == 'i':
					type_of_object = ('g','p','i')#'gai'
					if add_img_to_sitemap:
						# adding 'public' image to sitemap so that it can be indexed by crawlers
						Cooldown.objects.create(content_id=obj_id, hot_score=int(time_now/604800))# 'hot_score' contains 'cohort number'
				
				elif expiry == 'm':
					type_of_object = ('g','p','m')#'gam'
				
				invalidate_cached_user_feed_history(own_id, 'public')# all posts apart from 'gp' and 'gai' are 'private' in user feed history
				add_to_photo_feed = True
				post_to_all_followers = True

			elif audience == 'a':
				# post_to_all_followers = True
				# if expiry == 'i':
				# 	type_of_object = ('g','a','i')#'gai'
				# 	invalidate_cached_user_feed_history(own_id, 'limited')# all 'gai' type post are 'limited'
				# elif expiry == 'm':
				# 	type_of_object = ('g','a','m')#'gam'
				# 	invalidate_cached_user_feed_history(own_id, 'limited')# all posts apart from 'gp' and 'gai' are 'private' in user feed history
				
				# else:
				# 	# not a valid expiry type
				raise Http404("Not a valid audience type")

			elif audience == 's':
				
				# if expiry == 'i':
				# 	type_of_object = ('g','s','i')#'gsi'
				# 	invalidate_cached_user_feed_history(own_id, 'private')# all posts apart from 'gp' and 'gai' are 'private' in user feed history
					
				# elif expiry == 'm':
				# 	type_of_object = ('g','s','m')#'gsm'
				# 	invalidate_cached_user_feed_history(own_id, 'private')# all posts apart from 'gp' and 'gai' are 'private' in user feed history

				# else:
				# 	# not a valid expiry type
				raise Http404("Not a valid audience type")

			else:
				pass
			
			#######################################################################
			# Step 2) Handle Redis Object(s)
			submitter_name, av_url = retrieve_credentials(own_id,decode_uname=True)
			obj_hash = add_image_post(obj_id=obj_id, categ='6', submitter_id=own_id, submitter_av_url=av_url, submitter_username=submitter_name, \
				img_url=get_s3_object(img_url), is_star=is_star, img_caption=description, submission_time=time_now, from_fbs=on_fbs, \
				type_of_object=type_of_object, add_to_photo_feed=add_to_photo_feed, poster_defined_expiry_time=expire_at, comments=coms, \
				img_height=img_height, img_width=img_width, alt_text=img_alt_text)#type_of_object

			if post_to_all_followers:
				# fan_out_to_followers(own_id,obj_hash,time_now,expire_at=expire_at,follower_list=None)
				post_to_followers(own_id,obj_hash,time_now,expire_at=expire_at,follower_list=None)
			
			else:
				selected_follower_ids = request.session.pop('selected_follower_ids'+str(own_id),None)
				if selected_follower_ids:
					# fan_out_to_followers(own_id,obj_hash,time_now, expire_at=expire_at,follower_list=selected_follower_ids)
					post_to_followers(own_id,obj_hash,time_now,expire_at=expire_at,follower_list=selected_follower_ids)
				else:
					# No selected followers exist - redirect to sharing page with the requisite prompt
					raise Http404("Not selected followers exist")

			#######################################################################
			
			# Step 3) Set requisite rate-limits and such
			rate_limit_content_sharing(own_id, set_long_ratelimit= add_to_photo_feed)#rate limiting for 5 mins (and hard limit set at 50 submissions per day)
			
			if add_to_photo_feed:
				# since being posted to a 'public' feed, ensure basic anti-duplication measures are in place
				insert_hash(obj_id, img_avghash)#disallowing duplication for 'public' audience type
				
				# adding the image to some redis sets
				save_recent_photo(user_id=own_id, photo_id=obj_id, time_now=time_now)

				if on_fbs:
					# prevent FBS users from rapidly uploading tons of images
					rate_limit_fbs_public_photo_uploaders(own_id)

			#######################################################################

			################### Retention activity logging ###################
			if own_id > SEGMENT_STARTING_USER_ID:
				request.session['rd'] = '1'
				if expiry == 'm':
					# mortal post
					if coms == '1':
						# comments are on
						act = 'P3'
					elif coms == '0':
						# comments are off
						act = 'P4'
				elif expiry == 'i':
					# immportal post
					if coms == '1':
						# comments are on
						act = 'P1'
					elif coms == '0':
						# comments are off
						act = 'P2'
				activity_dict = {'m':'POST','act':act,'t':time_now,'pi':img_url,'pc':description}# defines what activity just took place
				log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
			##################################################################
			
			###########################################################################
			############################### Post Logger ###############################
			###########################################################################
			# num_fans = get_all_follower_count(own_id)
			# num_vfans = get_verified_follower_count(own_id)
			# data = {'aud':audience,'exp':expiry,'coms':coms, 'desc':description,'align':alignment,'uid':own_id, 'top':topic_name, \
			# 'orig':origin, 'Lid':obj_id,'expt':expire_at,'numf':num_fans,'num_vf':num_vfans,'image':get_s3_object(img_url)}
			# logging_post_data(data)
			###########################################################################
			###########################################################################	
			###########################################################################
			if audience == 'p':
			# Step 4) redirect to the kind of audience the post was targetted at
				return redirect("display_user_public_feed_history",submitter_name)# redirecting to own profile
			elif audience == 'a':
				return redirect("display_user_follower_feed_history",submitter_name)# redirecting to own profile
			elif audience == 's':
				return redirect("display_user_private_feed_history",submitter_name)# redirecting to own profile
			else:
				return redirect("display_user_public_feed_history",submitter_name)# redirecting to own profile			
		else:
			raise Http404("Unsupported content type")
	else:
		# temporarily saved data has expired - return user to the posting screen with a helpful message
		raise Http404("Temp data has expired, please retry")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def welcome_reply(request,*args,**kwargs):
	"""
	"""
	if request.user_banned:
		return redirect("error")
	user_id = request.user.id
	username = retrieve_uname(user_id,decode=True)#request.user.username
	banned, time_remaining, ban_details = check_content_and_voting_ban(user_id, with_details=True)
	if banned:
		# Cannot submit welcome reply since user is banned
		return render(request, 'judgement/cannot_comment.html', {'time_remaining': time_remaining,'ban_details':ban_details,\
			'forbidden':True,'own_profile':True,'defender':None,'is_profile_banned':True, 'org':'19','tun':username})
	else:
		if request.method == 'POST':
			pk = request.session.pop("welcome_pk",None)
			try:
				target = User.objects.get(pk=pk)
			except User.DoesNotExist:
				return redirect("user_profile", slug=username)# redirecting to own profile
			current = User.objects.latest('id')
			num = current.id
			if (num-100) <= int(pk) <= (num+100):
				option = request.POST.get("opt")
				message = request.POST.get("msg")
				try:
					av_url = target.userprofile.avatar.url
				except ValueError:
					av_url = None
				if Link.objects.filter(submitter=target).exists():
					parent = Link.objects.filter(submitter=target).latest('id')
					parent.reply_count = parent.reply_count + 1
				else:
					num = random.randint(1,len(SALUTATIONS))
					text = SALUTATIONS[num-1]
					target_username = target.username
					parent = Link.objects.create(description=text, submitter=target, reply_count=1)
					add_text_post(obj_id=parent.id, categ='1', submitter_id=target.id, submitter_av_url=av_url, submitter_username=target_username, \
						is_star=is_image_star(user_id=target.id),submission_time=time.time(),text=text, from_fbs=request.META.get('HTTP_X_IORG_FBS',False),\
						add_to_feed=False)
				if option == '1' and message == 'Barfi khao aur mazay urao!':
					description = target.username+" welcum damadam pe! Kiya hal hai? Barfi khao aur mazay urao (barfi)"
					reply = Publicreply.objects.create(submitted_by_id=user_id, answer_to=parent, description=description)
				elif option == '1' and message == 'Yeh zalim barfi try kar yar!':
					description = target.username+" welcome! Kesey ho? Yeh zalim barfi try kar yar (barfi)"
					reply = Publicreply.objects.create(submitted_by_id=user_id, answer_to=parent, description=description)
				elif option == '1' and message == 'Is barfi se mu meetha karo!':
					description = target.username+" assalam-u-alaikum! Is barfi se mu meetha karo (barfi)"
					reply = Publicreply.objects.create(submitted_by_id=user_id, answer_to=parent, description=description)
				elif option == '2' and message == 'Aik plate laddu se life set!':
					description = target.username+" Damadam pe welcome! One plate laddu se life set (laddu)"
					reply = Publicreply.objects.create(submitted_by_id=user_id, answer_to=parent, description=description)
				elif option == '2' and message == 'Ye saray laddu aap ke liye!':
					description = target.username+" kya haal he? Ye laddu aap ke liye (laddu)"
					reply = Publicreply.objects.create(submitted_by_id=user_id, answer_to=parent, description=description)
				elif option == '2' and message == 'Laddu khao, jaan banao yar!':
					description = target.username+" welcum! Life set hei? Laddu khao, jaan banao (laddu)"
					reply = Publicreply.objects.create(submitted_by_id=user_id, answer_to=parent, description=description)
				elif option == '3' and message == 'Jalebi khao aur ayashi karo!':
					description = target.username+" welcomeee! Yar kya hal he? Jalebi khao aur ayashi karo (jalebi)"
					reply = Publicreply.objects.create(submitted_by_id=user_id, answer_to=parent, description=description)
				elif option == '3' and message == 'Jalebi meri pasandida hai!':
					description = target.username+" kaisey ho? Jalebi meri pasandida hai! Tumhari bhi? (jalebi)"
					reply = Publicreply.objects.create(submitted_by_id=user_id, answer_to=parent, description=description)
				elif option == '3' and message == 'Is jalebi se mu metha karo!':
					description = target.username+" salam! Is jalebi se mu meetha karo (jalebi)"
					reply = Publicreply.objects.create(submitted_by_id=user_id, answer_to=parent, description=description)
				else:
					return redirect('home')
				parent.latest_reply = reply
				parent.save()
				try:
					url = request.user.userprofile.avatar.url
				except ValueError:
					url = None
				reply_time = convert_to_epoch(reply.submitted_on)
				amnt = update_comment_in_home_link(reply=description,writer=username,reply_id=reply.id,time=reply_time,writer_id=user_id,\
					link_pk=parent.id)
				publicreply_notification_tasks.delay(link_id=parent.id,link_submitter_url=av_url, sender_id=user_id,\
					link_submitter_id=pk,link_submitter_username=target.username, link_desc=parent.description, \
					reply_time=reply_time,reply_poster_url=url,reply_poster_username=username,reply_desc=reply.description,\
					is_welc=False,reply_count=parent.reply_count,priority='home_jawab',from_unseen=False)
				
				##################################################################
				return redirect('home')
			else:
				return render(request,'old_user.html',{'username':target.username})
		else:
			raise Http404("Not a POST request")


######################## HELL BANNING FUNCTIONALITY ########################

@csrf_protect
def remove_hell_ban(request):
	"""
	Removes a user's ID from the hell-ban-list
	"""
	if request.method == "POST":
		target_id = request.POST.get("t_id",None)
		is_defender, is_super_defender = in_defenders(request.user.id, return_super_status=True)
		if is_defender:
			decision = request.POST.get('dec',None)
			if decision == '1':
				if target_id:
					if HellBanList.objects.filter(condemned_id=target_id).exists():
						HellBanList.objects.filter(condemned_id=target_id).delete()
						remove_from_hell(target_id)
					return redirect("user_profile",retrieve_uname(target_id,decode=True))
				else:
					raise Http404("No target_id exists")
			else:
				return render(request,"hell_ban.html",{'remove':True,'t_id':target_id,'target_uname':retrieve_uname(target_id,decode=True),\
					'own_id':request.user.id,'banned':is_user_hell_banned(target_id)})
		else:
			raise Http404("This can't be accessed")
	else:
		raise Http404("This can't be accessed")


@csrf_protect
def hell_ban(request,*args,**kwargs):
	"""
	Hell-bans a perp
	"""
	if request.method == "POST":
		ghost_ban = request.POST.get("ghost_ban","")
		if ghost_ban:
			counter = request.POST.get("counter","")
			username = request.POST.get("original_target_username","")
			if counter == '1':
				target = request.POST.get("target1","")
				if HellBanList.objects.filter(condemned_id=target).exists():
					HellBanList.objects.filter(condemned_id=target).delete()
					HellBanList.objects.create(condemned_id=target)
				else:
					HellBanList.objects.create(condemned_id=target)
				######### populating the hell-ban in redis as well #########
				add_to_hell(target_id=target)
				return redirect("user_profile",username)
			else:
				try:
					counter = int(counter)
					temp = 1
					target_ids = []
					while temp < (counter+1):
						target_id = request.POST.get("target"+str(temp),"")
						if target_id:
							target_ids.append(target_id)
						temp += 1
					if target_ids:
						hellbanned =[]
						HellBanList.objects.filter(condemned_id__in=target_ids).delete()
						for target_id in target_ids:
							hellbanned.append(HellBanList(condemned_id=target_id))
						HellBanList.objects.bulk_create(hellbanned)
						add_to_hell_ban_in_bulk(target_ids)
						return redirect("user_profile",username)
					else:
						return redirect("user_profile",username)
				except:
					return redirect('home')
		else:
			target_username = request.POST.get("t_uname")
			target_id = request.POST.get("t_id")
			clone_ids = get_clones(target_id)
			own_id = request.user.id
			if clone_ids:
				if len(clone_ids) > 1:
					targets = User.objects.filter(id__in=clone_ids).values('id','username')
					hellbanned = list(HellBanList.objects.filter(condemned_id__in=clone_ids).values_list('condemned_id',flat=True))
					if hellbanned:
						for target in targets:
							if target['id'] in hellbanned:
								target['banned'] = True
							else:
								target['banned'] = False
					else:
						for target in targets:
							target['banned'] = False
					context = {'offline':False,'own_id':own_id,'targets':targets,'counter':len(clone_ids),'original_target_id':target_id,\
					'original_target_uname':target_username}
					return render(request,'hell_ban.html',context)
				elif len(clone_ids) == 1:
					if HellBanList.objects.filter(condemned_id=target_id).exists():
						targets = [{'id':target_id,'username':target_username,'banned':True}]
					else:
						targets = [{'id':target_id,'username':target_username,'banned':False}]
					context = {'offline':False,'counter':1,'original_target_id':target_id,'own_id':own_id,'targets':targets,\
					'original_target_uname':target_username}
					return render(request,'hell_ban.html',context)
				else:
					if HellBanList.objects.filter(condemned_id=target_id).exists():
						banned = True
					else:
						banned = False
					context={'offline':True,'original_target_id':target_id,'counter':1,'own_id':own_id,'banned':banned,\
					'original_target_uname':target_username}
					return render(request,'hell_ban.html',context)
			else:
				if HellBanList.objects.filter(condemned_id=target_id).exists():
					banned = True
				else:
					banned = False
				context={'offline':True,'original_target_id':target_id,'counter':1,'own_id':own_id,'banned':banned,\
				'original_target_uname':target_username}
				return render(request,'hell_ban.html',context)
	else:
		raise Http404("This can't be accessed")


@csrf_protect
def show_clones(request,*args,**kwargs):
	if request.method == "POST":
		target_username = request.POST.get("t_uname")
		target_id = request.POST.get("t_id")
		clone_ids = get_clones(target_id)
		if clone_ids:
			usernames = User.objects.filter(id__in=clone_ids).values_list('username',flat=True)
			context={'usernames':usernames,'original_target_id':target_id,'original_target_uname':target_username,\
			'own_id':request.user.id}
			return render(request,"show_clones.html",context)
		else:
			context={'usernames':None,'original_target_id':target_id,'original_target_uname':target_username,\
			'own_id':request.user.id}
			return render(request,"show_clones.html",context)
	else:
		raise Http404("This can't be accessed")


@csrf_protect
def kick_ban_user(request,*args,**kwargs):
	"""
	TODO: 'Session' table is no more - need to update this functionality
	"""
	if request.method == "POST":
		kick_ban = request.POST.get("kick_ban","")
		if kick_ban:
			counter = request.POST.get("counter","")
			username = request.POST.get("original_target_username","")
			if counter == '1':
				target = request.POST.get("target1","")
				# Session.objects.filter(user_id=target).delete()
				# BAN IP or USER_ID or BOTH?
				return redirect("user_profile",username)
			else:
				try:
					counter = int(counter)
					temp = 1
					target_ids = []
					while temp < (counter+1):
						target_id = request.POST.get("target"+str(temp),"")
						if target_id:
							target_ids.append(target_id)
						temp += 1
					# Session.objects.filter(user_id__in=target_ids).delete()
					return redirect("user_profile",username)
				except:
					return redirect('home')
		else:
			target_username = request.POST.get("t_uname")
			target_id = request.POST.get("t_id")
			clone_ids = get_clones(target_id)
			if clone_ids:
				if len(clone_ids) > 1:
					targets = User.objects.filter(id__in=clone_ids).values('id','username')
					context={'offline':False,'targets':targets,'original_target_id':target_id,'original_target_uname':target_username,\
					'counter':len(clone_ids),'own_id':request.user.id}
					return render(request,'kick_ban_user.html',context)
				elif len(clone_ids) == 1:
					targets = [{'id':target_id,'username':target_username}]
					context={'offline':False,'targets':targets,'original_target_id':target_id,'original_target_uname':target_username,\
					'counter':1,'own_id':request.user.id}
					return render(request,'kick_ban_user.html',context)
				else:
					context={'offline':True,'original_target_uname':target_username,'original_target_id':target_id,'counter':1,\
					'own_id':request.user.id}
					return render(request,'kick_ban_user.html',context)
			else:
				context={'offline':True,'original_target_uname':target_username,'original_target_id':target_id,'counter':1,\
				'own_id':request.user.id}
				return render(request,'kick_ban_user.html',context)
	else:
		raise Http404("This can't be accessed")


@csrf_protect
def kick_user(request,*args,**kwargs):
	"""
	TODO: 'Session' table is no more - need to update this functionality
	"""
	if request.method == "POST":
		kick = request.POST.get("kick","")
		if kick:
			counter = request.POST.get("counter","")
			username = request.POST.get("original_target_username","")
			if counter == '1':
				target = request.POST.get("target1","")
				# Session.objects.filter(user_id=target).delete()
				return redirect("user_profile",username)
			else:
				try:
					counter = int(counter)
					temp = 1
					target_ids = []
					while temp < (counter+1):
						target_id = request.POST.get("target"+str(temp),"")
						if target_id:
							target_ids.append(target_id)
						temp += 1
					# Session.objects.filter(user_id__in=target_ids).delete()
					return redirect("user_profile",username)
				except:
					return redirect('home')
		else:
			target_username = request.POST.get("t_uname")
			target_id = request.POST.get("t_id")
			clone_ids = get_clones(target_id)
			if clone_ids:
				if len(clone_ids) > 1:
					targets = User.objects.filter(id__in=clone_ids).values('id','username')
					context={'offline':False,'targets':targets,'original_target_id':target_id,'original_target_uname':target_username,\
					'counter':len(clone_ids),'own_id':request.user.id}
					return render(request,'kick_user.html',context)
				elif len(clone_ids) == 1:
					targets = [{'id':target_id,'username':target_username}]
					context={'offline':False,'targets':targets,'original_target_id':target_id,'original_target_uname':target_username,\
					'counter':1,'own_id':request.user.id}
					return render(request,'kick_user.html',context)
				else:
					context={'offline':True,'original_target_uname':target_username,'original_target_id':target_id,'counter':1,\
					'own_id':request.user.id}
					return render(request,'kick_user.html',context)
			else:
				context={'offline':True,'original_target_id':target_id,'counter':1,'own_id':request.user.id,\
				'original_target_uname':target_username}
				return render(request,'kick_user.html',context)
	else:
		raise Http404("This can't be accessed")


@csrf_protect
def cut_user_score(request,*args,**kwargs):
	if request.method == "POST":
		penalty = request.POST.get("penalty","")
		if penalty:
			target_username = request.POST.get("t_uname")
			target_id = request.POST.get("t_id")
			UserProfile.objects.filter(user_id=target_id).update(score=F('score')-int(penalty))
			return redirect("user_profile",target_username)
		else:
			target_username = request.POST.get("t_uname")
			target_id = request.POST.get("t_id")
			target_score = UserProfile.objects.get(user_id=target_id).score
			penalty1 = get_price(target_score)
			penalty2 = get_price(target_score)*2
			penalty3 = get_price(target_score)*3
			penalty4 = target_score
			context={'target_uname':target_username,'target_scr':target_score,'own_id':request.user.id,\
			'penalty1':penalty1,'penalty2':penalty2,'penalty3':penalty3,'penalty4':penalty4,'t_id':target_id}
			return render(request,'cut_user_score.html',context)
	else:
		raise Http404("This can't be accessed")


@csrf_protect   
def manage_user(request,*args,**kwargs):
	if request.method == "POST":
		manager_id = request.POST.get("m_id")
		if str(request.user.id) == manager_id:
			request.session["manager_id"] = manager_id
			target_id = request.POST.get("t_id")
			target = User.objects.get(id=target_id)
			context={'target_uname':target.username,'target_id':target_id}
			return render(request,"manage_user.html",context)
		else:
			raise Http404("This can't be accessed")   
	else:
		raise Http404("This can't be accessed")


@csrf_protect    
def manage_user_help(request,*args,**kwargs):
	if request.method == "POST":
		help_type = request.POST.get("htype")
		target_uname = request.POST.get("t_uname")
		target_id = request.POST.get("t_id")
		own_id = request.user.id
		context={'target_uname':target_uname,'target_id':target_id,'own_id':own_id,'authorized':True}
		if help_type == 'ctscr':
			return render(request,'cut_score.html',context)
		elif help_type == 'kout':
			return render(request,'kick_out.html',context)
		elif help_type == 'kban':
			return render(request,'kick_ban.html',context)
		elif help_type == 'ghban':
			return render(request,'ghost_ban.html',context)
		elif help_type == 'oclone':
			return render(request,'check_clones.html',context)
		elif help_type == 'sybil':
			return render(request,'check_sybils.html',context)
		elif help_type == 'revsyb':
			return render(request,'check_reverse_sybils.html',context)
		elif help_type == 'vhist':
			return render(request,'check_voting_hist.html',context)
		else:
			raise Http404("This can't be accessed")   
	else:
		raise Http404("This can't be accessed")


def missing_page(request,*args,**kwargs):
	"""
	Responsible for giving a 404 HTTP Response
	"""
	raise Http404("The page you requested has gone AWOL")


def error(request):
	"""
	Displays error to hell-banned profiles

	TODO: Provide a more descriptive message
	"""
	return render(request,"500.html",{})

##################################################### Sitemaps #####################################################


def sitemap(request):
	"""
	Renders a sitemap
	"""
	latest_trending_mod_time, latest_fresh_mod_time = retrieve_photo_feed_latest_mod_time(both=True)
	return render(request, 'sitemap/sitemap.xml', {'latest_trending_mod_time': beautiful_date(latest_trending_mod_time,format_type='4'),\
	'latest_fresh_mod_time':beautiful_date(latest_fresh_mod_time,format_type='4')},content_type="application/xml")

# legacy sitemap
def photo_sitemap_of_sitemaps(request):
	"""
	Renders a sitemap of sitemaps for photo_detail pages
	"""
	sitemap_cohorts, latest_obj_trending_time = retrieve_indexable_photo_detail_cohorts()
	return render(request, 'sitemap/photo_sitemap_of_sitemaps.xml', {'latest_obj_trending_time':latest_obj_trending_time,\
		'sitemap_cohorts': sitemap_cohorts},content_type="application/xml")

# legacy sitemap
def photo_sitemap(request, cohort):
	"""
	Renders a sitemap for photo_detail pages falling within a certain time cohort
	"""
	photo_ids_and_times = retrieve_indexable_photo_detail_list(cohort=cohort)
	return render(request, 'sitemap/photo_sitemap.xml', {'photo_ids_and_times': photo_ids_and_times},content_type="application/xml")

# legacy sitemap
def retrieve_indexable_photo_detail_list(cohort):
	"""
	Retreiving all photo_ids belonging to a certain sitemap cohort
	"""
	trending_photo_objs = Logout.objects.filter(pre_logout_score=cohort).values_list('logout_user_id','logout_time')
	final_data = []
	for photo_id, trending_time in trending_photo_objs:
		final_data.append((photo_id,trending_time.strftime("%Y-%m-%dT%I:%M:%S+00:00")))
	return final_data


# legacy sitemap
def retrieve_indexable_photo_detail_cohorts():
	"""
	Retrieves IDs of photos that have trended since 28th June 2019, and creates cohorts of sitemaps out of them
	"""
	latest_obj = Logout.objects.latest('id')
	latest_obj_trending_time = latest_obj.logout_time.strftime("%Y-%m-%dT%I:%M:%S+00:00")
	earliest_obj = Logout.objects.order_by('id')[:1][0]
	latest_cohort = latest_obj.pre_logout_score# this is cohort num
	first_cohort = earliest_obj.pre_logout_score# this is cohort num
	cohorts = range(first_cohort, latest_cohort+1, 1)
	return cohorts, latest_obj_trending_time


################################################################


# new sitemap
def content_sitemap_of_sitemaps(request):
	"""
	Renders a sitemap of sitemaps for content_detail pages
	"""
	sitemap_cohorts, latest_obj_trending_time = retrieve_indexable_content_detail_cohorts()
	return render(request, 'sitemap/content_sitemap_of_sitemaps.xml', {'latest_obj_trending_time':latest_obj_trending_time,\
		'sitemap_cohorts': sitemap_cohorts},content_type="application/xml")


# new sitemap
def content_sitemap(request, cohort):
	"""
	Renders a sitemap for content_detail pages falling within a certain time cohort
	"""
	content_ids_times_and_types = retrieve_indexable_content_detail_list(cohort=cohort)
	return render(request, 'sitemap/content_sitemap.xml', {'content_ids_times_and_types': content_ids_times_and_types},\
		content_type="application/xml")


# new sitemap
def retrieve_indexable_content_detail_list(cohort):
	"""
	Retreiving all content_ids belonging to a certain sitemap cohort
	"""
	trending_content_objs = Cooldown.objects.select_related('content__image_file').\
	filter(hot_score=cohort).values_list('content_id','time_of_casting','content__image_file')# web_link used as a store for image's 'alt' description
	final_data = []
	for content_id, time_of_casting, image_url in trending_content_objs:
		final_data.append((content_id,time_of_casting.strftime("%Y-%m-%dT%I:%M:%S+00:00"),'https:{}'.format(get_s3_object(image_url))))
	return final_data


# new sitemap
def retrieve_indexable_content_detail_cohorts():
	"""
	Retrieves IDs of content that has trended since Follow feature went live, and creates cohorts of sitemaps out of them
	"""
	latest_obj = Cooldown.objects.latest('id')
	latest_obj_trending_time = latest_obj.time_of_casting.strftime("%Y-%m-%dT%I:%M:%S+00:00")
	earliest_obj = Cooldown.objects.order_by('id')[:1][0]
	latest_cohort = latest_obj.hot_score# this is cohort num
	first_cohort = earliest_obj.hot_score# this is cohort num
	cohorts = range(first_cohort, latest_cohort+1, 1)
	return cohorts, latest_obj_trending_time


#######################################################################################
##################################### Legacy code #####################################

"""
This code supports 'old' data uploaded by users 
We have to support it because of SEO reasons
"""

def public_reply_view(request,parent_id):
	"""
	Render the 'old' comments page for text comments
	"""
	user_id = request.user.id

	try:
		link = Link.objects.values('id','reply_count','description','submitted_on','submitter','net_votes','url','cagtegory').get(id=parent_id)
		link['machine_time'] = link['submitted_on']
		link['submitted_on'] = naturaltime(link['submitted_on'])
	except Link.DoesNotExist:
		# purge single notification and matka of request.user.id
		# remove_erroneous_notif(notif_name="np:"+str(user_id)+":2:"+str(parent_id), user_id=user_id)
		return render(request, 'object_deleted.html',{})
	##########################################################
	# secret_key = uuid.uuid4()
	# set_text_input_key(user_id, parent_id, 'home_rep', secret_key)
	##########################################################
	parent_submitter_id = link['submitter']
	parent_uname, parent_avurl = retrieve_credentials(parent_submitter_id,decode_uname=True)
	##########################################################
	context = {'is_auth':True,'on_fbs':request.META.get('HTTP_X_IORG_FBS',False),'random':random.sample(xrange(1,188),15),\
	'mob_verified':True if request.mobile_verified else False,'parent':link,'parent_submitter_id':parent_submitter_id,\
	'parent_av_url':parent_avurl,'parent_submitter_username':parent_uname,'is_star':is_image_star(user_id=parent_submitter_id),\
	'stars':get_all_image_star_ids(),'vote_score':link['net_votes'],'feature_phone':True if request.is_feature_phone else False,\
	'user_id':user_id,'user_is_owner':parent_submitter_id == user_id}
	##########################################################
	if link['url']:
		payload = link['url'].split(":")
		try:
			theme, context['topic_name'], context['topic_url'] = payload[0], payload[1], payload[2]
			color_grads = COLOR_GRADIENTS[theme]
			context["c1"], context["c2"] = color_grads[0], color_grads[1]
		except IndexError:
			pass
	##########################################################
	replies = retrieve_cached_public_replies(parent_id)
	if replies:
		replies_data = json.loads(replies)
	else:
		replies_data = Publicreply.objects.only('submitted_on','description','id','submitted_by','abuse','submitted_by__username',\
			'direct_reply_tgt_uname','direct_reply_tgt_text_prefix','direct_reply_tgt_text_postfix','direct_reply_id').\
		values('submitted_on','description','id','submitted_by','abuse','submitted_by__username','direct_reply_tgt_uname',\
			'direct_reply_tgt_text_prefix','direct_reply_tgt_text_postfix','direct_reply_id').filter(answer_to_id=parent_id).\
		order_by('-id')[:25]
		for reply in replies_data:
			reply["submitted_on"] = convert_to_epoch(reply["submitted_on"])
		cache_public_replies(json.dumps(replies_data),parent_id)
	context["replies"] = replies_data#replies
	##########################################################
	return render(request,"legacy/old_reply.html",context)


def display_old_image_comments(request,pk,origin=None):
	"""
	Render the comments page for 'old' image comments
	"""
	user_id = request.user.id
	try:
		photo = Photo.objects.select_related('owner').get(id=pk)
		photo_owner_id = photo.owner_id
	except Photo.DoesNotExist:
		context = {}
		if user_id:
			# remove_erroneous_notif(notif_name="np:"+str(user_id)+":0:"+str(pk), user_id=user_id)
			context["obj_deleted"] = True
		else:
			context['target_username'] = 'User'
			context['authorized'] = False
		
		return render(request,"legacy/old_comments.html",context)
	###################################################
	secret_key = uuid.uuid4()
	home_hash = 'img:'+pk
	target_username = retrieve_uname(photo_owner_id,decode=True)
	
	comments = PhotoComment.objects.only('abuse','text','id','submitted_by','submitted_on','submitted_by__username',\
		'direct_reply_tgt_uname','direct_reply_tgt_text_prefix','direct_reply_tgt_text_postfix','direct_reply_id').\
	values('abuse','text','id','submitted_by','submitted_on','submitted_by__username','direct_reply_tgt_uname',\
		'direct_reply_tgt_text_prefix','direct_reply_tgt_text_postfix','direct_reply_id').filter(which_photo_id=pk).\
	order_by('-id')[:25]

	for comment in comments:
		comment["submitted_on"] = convert_to_epoch(comment["submitted_on"])

	context = {'feature_phone':True if request.is_feature_phone else False,'lid':home_hash,'photo_id':pk,'obj_deleted':False,\
	'photo':photo,'sk':secret_key,'stars':get_all_image_star_ids(), 'user_is_owner':photo_owner_id == user_id, \
	'is_star':is_image_star(user_id=photo_owner_id),'on_fbs':request.META.get('HTTP_X_IORG_FBS',False),'authorized':True,\
	'random':random.sample(xrange(1,188),15),'VDC':VOTING_DRIVEN_CENSORSHIP+1,'target_username':target_username,\
	'latest_comment_time':comments[0]['submitted_on'] if comments else None,'origin':origin if origin else '3',\
	'comments':comments,'photo_owner_id':photo_owner_id}

	if origin == '3':
		# originating from home            
		request.session["target_id"] = home_hash#turn pk into 'home_hash' (for accurate redirects)
		request.session.modified = True

	if user_id:
		set_text_input_key(user_id, pk, 'pht_comm', secret_key)
		time_now = time.time()
		# context["dir_rep_form"] = DirectResponseForm(with_id=True)
		# context["main_rep_form"] = DirectResponseForm()
		context["is_auth"] = True
		context["mob_verified"] = True
		context["user_id"] = user_id
		if not request.mobile_verified:
			context["mob_verified"] = False
		context["authenticated"] = True
		context["own_username"] = retrieve_uname(user_id,decode=True)
		
	else:
		context["authenticated"] = False

	return render(request,"legacy/old_comments.html",context)


def user_profile_photos(request,slug,type):
	"""
	Renders a user's photo page
	"""
	context = {}
	page_num = request.GET.get('page', '1')
	username, list_type = slug, type
	if username and list_type in ('fotos','trending-fotos'):
		target_id = retrieve_user_id(username)
		if target_id:
			PICS_PER_PAGE = 10
			start_index, end_index = get_indices(page_num, PICS_PER_PAGE)# showing 10 items per page
			if list_type == 'fotos':
				# retrieve latest images uploaded by the user
				obj_list = Photo.objects.only('id','caption','image_file','vote_score','upload_time','comment_count','device').filter(owner_id=target_id,\
					category='1',is_public=True).order_by('-id')[start_index:end_index+1]
				list_total_size = Photo.objects.filter(owner_id=target_id,category='1',is_public=True).count()
			else:
				# retrieve past week's trending images
				photo_ids = retrieve_trending_photo_ids(target_id)
				if photo_ids:
					obj_list = Photo.objects.only('id','caption','image_file','vote_score','upload_time','comment_count').filter(id__in=photo_ids).\
					order_by('-id')[start_index:end_index+1]
					list_total_size = len(photo_ids)
					num_pages = list_total_size/PICS_PER_PAGE
				else:
					obj_list = []
					list_total_size = 0
				
			num_pages = list_total_size/PICS_PER_PAGE
			max_pages = num_pages if list_total_size % PICS_PER_PAGE == 0 else (num_pages+1)
			page_num = int(page_num)
			context['object_list'] = obj_list
		else:
			log_404.delay(type_of_404='1b',time_of_404=time.time())
			raise Http404("This user does not exist")
	else:
		log_404.delay(type_of_404='1a',time_of_404=time.time())
		raise Http404("No username provided or malformed type")
	###############################################################
	try:
		subject = User.objects.only('date_joined').get(id=target_id)
	except User.DoesNotExist:
		log_404.delay(type_of_404='1c',time_of_404=time.time())
		raise Http404("User ID does not compute")
	if list_type == 'trending-fotos':
		context["is_trending"] = True
	context["slug"] = username
	context["is_star"] = is_image_star(user_id=target_id)
	star_id = target_id
	context["num_trending"] = retrieve_num_trending_photos(star_id)
	if request.user:
		user_id = request.user.id
		context["user_id"] = user_id
		context["origin"] = '4'#helps redirect back to this page if a user enters the "report" funnel
		context["authenticated"] = True
		is_defender, is_super_defender = in_defenders(user_id, return_super_status=True)
		if is_super_defender:
			context["manageable"] = True
		own_profile = star_id == user_id
		context["own_profile"] = own_profile
		if not own_profile:
			# someone else's profile AND user is logged in
			context["subject_id"] = star_id
	else:
		user_id = None
		is_defender = False
		own_profile = False
		context["authenticated"] = False
		context["own_profile"] = False
	context["mobile_verified"] = request.mobile_verified if own_profile else is_mobile_verified(star_id)
	###########
	banned, time_remaining, ban_details = check_content_and_voting_ban(star_id, with_details=True)
	context["ban_detail"] = ban_details
	context["is_profile_banned"] = banned
	context["noindex"] = True if (banned or not context["mobile_verified"]) else False
	context["defender"] = is_defender
	context["time_remaining"] = time_remaining
	###########
	on_fbs = request.META.get('HTTP_X_IORG_FBS',False)
	on_opera = request.is_opera_mini
	is_js_env = retrieve_user_env(opera_mini=on_opera, fbs = on_fbs)
	context["on_opera"] = on_opera
	context["on_fbs"] = on_fbs
	###########
	context["subject"] = subject
	context["star_id"] = star_id
	context["star_av_url"] = retrieve_avurl(star_id)
	context["page_obj"] = {'number':page_num,'has_previous':True if page_num>1 else False,'has_next':True if page_num<max_pages else False,\
	'previous_page_number':page_num-1,'next_page_number':page_num+1}
	
	##################################################################
	return render(request,"user_detail1.html",context)


class UserActivityView(ListView):
	model = Link
	slug_field = "username"
	template_name = "user_activity.html"
	paginate_by = 20

	def get_queryset(self):
		username = self.kwargs.get('slug',None)
		if username:
			target_id = retrieve_user_id(username)
			if target_id:
				if target_id == str(self.request.user.id):
					data = Link.objects.values('id','description','submitted_on','net_votes','reply_count','url','cagtegory').\
					filter(submitter_id=target_id,is_visible=True).order_by('-id')[:200]
				else:
					data = Link.objects.values('id','description','submitted_on','net_votes','reply_count','url','cagtegory').\
					filter(submitter_id=target_id,is_visible=True).order_by('-id')[:60]
				return data
			else:
				raise Http404("This user does not exist")
		else:
			raise Http404("No username provided")


	def get_context_data(self, **kwargs):
		context = super(UserActivityView, self).get_context_data(**kwargs)
		username = self.kwargs['slug']
		target_id = retrieve_user_id(username)
		for obj in context["object_list"]:
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
		if target_id:
			context["is_star"] = is_image_star(user_id=target_id)
			context["verified"] = False
			context["is_profile_banned"] = False
			context["on_fbs"] = self.request.META.get('HTTP_X_IORG_FBS',False)
			if self.request.user.is_authenticated():
				own_id = self.request.user.id
				is_defender, is_own_profile, ban_detail = in_defenders(own_id), str(own_id) == target_id, None
				banned, time_remaining, ban_detail = check_content_and_voting_ban(target_id, with_details=True)
				context["is_profile_banned"] = banned
				context["noindex"] = True if banned else False
				context["is_own_profile"] = is_own_profile
				context["ban_detail"] = ban_detail
				context["time_remaining"] = time_remaining
				context["ident"] = own_id
				context["is_defender"] = is_defender
				context["uname"] = username
				context["submitter_id"] = target_id
				context["submitter_av_url"] = retrieve_avurl(target_id)
				##################################################################
			return context
		else:
			raise Http404("This user does not exist!")




########################################################################################
########################################################################################


# Report run on 26/1/2019
#                      relation                     |  size   
# --------------------------------------------------+---------
#  public.user_sessions_session_expire_date         | 13 GB
#  public.links_publicreply                         | 8751 MB
#  public.links_reply                               | 7889 MB
#  public.links_photocomment                        | 5893 MB
#  public.links_reply__which_group_id__submitted_on | 4316 MB
#  public.links_link                                | 4020 MB
#  public.links_link_latest_reply_id_idx            | 3680 MB
#  public.links_reply_writer_id                     | 3051 MB
#  public.user_sessions_session                     | 2999 MB
#  public.links_publicreply_answer_to_id            | 2742 MB
#  public.links_publicreply_submitted_by_id         | 2686 MB
#  public.links_reply_submitted_on                  | 2652 MB
#  public.links_reply_pkey                          | 2652 MB
#  public.links_reply_which_group_id                | 2503 MB
#  public.links_publicreply_pkey                    | 2192 MB
#  public.user_sessions_session_user_id             | 1866 MB
#  public.links_photocomment_which_photo_id         | 1787 MB
#  public.links_photocomment_submitted_by_id        | 1785 MB
#  public.links_photo_latest_comment_id             | 1609 MB
#  public.links_photocomment_pkey                   | 1534 MB



# Report run on 15/3/2018
#             relation             | total_size 
# ---------------------------------+------------
#  public.links_reply              | 14 GB
#  public.links_publicreply        | 8396 MB
#  public.links_photocomment       | 7377 MB
#  public.user_sessions_session    | 6689 MB
#  public.links_link               | 3769 MB
#  public.links_photo              | 1882 MB
#  public.links_photo_which_stream | 429 MB
#  public.links_photostream        | 408 MB
#  public.auth_user                | 294 MB
#  public.links_userprofile        | 239 MB
#  public.links_userfan            | 214 MB
#  public.links_salatinvite        | 152 MB
#  public.links_hotuser            | 43 MB
#  public.links_group              | 42 MB
#  public.links_totalfanandphotos  | 38 MB
#  public.links_salat              | 28 MB
#  public.links_tutorialflag       | 13 MB
#  public.links_cooldown           | 10112 kB
#  public.links_latestsalat        | 6208 kB
#  public.links_groupcaptain       | 6072 kB


# Report run on 18/3/2017
#              Table               |  Size   | External Size 
# ----------------------------------+---------+---------------
#  user_sessions_session            | 8583 MB | 6917 MB
#  links_publicreply                | 5999 MB | 3078 MB
#  links_photocomment               | 2920 MB | 1401 MB
#  links_photo                      | 2527 MB | 2202 MB
#  links_link                       | 1430 MB | 374 MB
#  links_reply                      | 880 MB  | 664 MB
#  links_photo_which_stream         | 237 MB  | 159 MB
#  links_photostream                | 226 MB  | 119 MB
#  links_userprofile                | 131 MB  | 54 MB
#  links_userfan                    | 105 MB  | 67 MB
#  auth_user                        | 99 MB   | 38 MB

###################################################
