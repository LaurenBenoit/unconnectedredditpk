import time, uuid
import ujson as json
from operator import itemgetter
from django.shortcuts import redirect, render
from django.core.urlresolvers import reverse_lazy
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import cache_control
from django.http import Http404, HttpResponsePermanentRedirect
from topic_forms import SubmitInTopicForm, CreateTopicform
from page_controls import ITEMS_PER_PAGE
from models import Link
from direct_response_forms import DirectResponseForm
from tasks import set_input_history, log_user_activity
from views import get_indices, get_addendum, format_post_times, retrieve_user_env
from redis4 import retrieve_credentials, set_text_input_key, content_sharing_rate_limited, rate_limit_content_sharing
from colors import PRIMARY_COLORS, SECONDARY_COLORS, COLOR_GRADIENTS, PRIMARY_COLOR_DISTANCE, SECONDARY_COLOR_DISTANCE, \
PRIMARY_COLOR_GRADIENT_MAPPING
from redis7 import get_topic_feed, check_content_and_voting_ban, add_topic_post, create_topic_feed, retrieve_topic_feed_data, \
retrieve_topic_feed_index, retrieve_recently_used_color_themes, retrieve_topic_credentials, subscribe_topic, in_defenders, \
retire_abandoned_topics, retrieve_subscribed_topics, bulk_unsubscribe_topic, retrieve_last_vote_time, retrieve_recent_votes,\
is_image_star, set_temp_post_data
from redis2 import filter_following, fan_out_to_followers#TODO: call relevant function from tasks instead of fan_out_to_followers
from score import NUM_SUBMISSION_ALLWD_PER_DAY, SEGMENT_STARTING_USER_ID


##########################################################################################################
#################################### Calculate Topic Background Color ####################################
##########################################################################################################

def retrieve_highest_contrast_color(colors_and_dists):
	"""
	Returns the color with the greatest cumulative distance

	Receives data in this format: [('#6292ff', [70, 40]), ('#ffbe69', [35, 35]), ('#f4d140', [45, 35]), ('#977aff', [25, 55])]
	Synthesizes this data into: [('#6292ff', 110), ('#ffbe69', 70), ('#f4d140', 80), ('#977aff', 80)]
	Finally, retrieves the color with the highest 'score' (i.e. greatest cumulative contrast from all other color candidates)
	"""
	flattened_tups = []
	for color, dist_list in colors_and_dists:
		dimensions = len(dist_list)
		total_dist = 0
		for i in xrange(dimensions):
			total_dist += dist_list[i]
		flattened_tups.append((color, total_dist))
	color_candidates = sorted(flattened_tups, key=itemgetter(1), reverse=True)
	return color_candidates[0][0]


def retrieve_color_distance(theme_used_and_freq, color_dict, dist_calc_dict, color_idx):
	"""


	'dist_calc_dict' is either PRIMARY_COLOR_DISTANCE or SECONDARY_COLOR_DISTANCE
	"""
	unused_color_dist, used_color_dist = {}, {}
	for main_color in color_dict:
		coords, num_coords = [], 0
		for theme_num, occurances in theme_used_and_freq:
			colors = COLOR_GRADIENTS[theme_num]# retrieving colors, e.g. '1a':("#f574ff","#28d7ff")
			already_selected_color = colors[color_idx]
			calc_dict = PRIMARY_COLOR_DISTANCE if dist_calc_dict == 'primary' else SECONDARY_COLOR_DISTANCE# which color dictionary to use
			distance_from_main_color = calc_dict[main_color+":"+already_selected_color]
			coords.append(distance_from_main_color)
			num_coords += 1
		is_coord_zero = False
		for i in xrange(num_coords):
			if not coords[i]:
				is_coord_zero = True
		if is_coord_zero:
			# save into the dict of already used points, since a coordinate being 0 implies this color is already used
			used_color_dist[main_color] = coords
		else:
			# save into the dict of unused points
			unused_color_dist[main_color] = coords
	return unused_color_dist, used_color_dist


def categorize_color_contrasts(color_dist):
	"""
	Separates colors into sets of varying contrasts
	"""
	high_contrast_set, medium_contrast_set, low_contrast_set = [], [], []
	color_dist_tup = color_dist.items()
	for color, dists in color_dist_tup:
		dimensions = len(dists)
		for i in xrange(dimensions):
			if dists[i] <= 15:
				low_contrast_set.append((color,dists))
				break
	low_contrast_colors = [c for c,d in low_contrast_set]
	for color, dists in color_dist_tup:
		dimensions = len(dists)
		for i in xrange(dimensions):
			if dists[i] <= 30 and color not in low_contrast_colors:
				medium_contrast_set.append((color,dists))
				break
	medium_contrast_colors = [c for c,d in medium_contrast_set]
	for color, dists in color_dist_tup:
		dimensions = len(dists)
		for i in xrange(dimensions):
			if color not in low_contrast_colors and color not in medium_contrast_colors:
				high_contrast_set.append((color, dists))
				break
	return high_contrast_set, medium_contrast_set, low_contrast_set


def allot_topic_bg():
	"""
	Allots a family of background colors to a given topic

	Ensures it's as 'contrasty' as can be from current topics in circulation (uses a 'greedy' algorithm)
	"""
	theme_used_and_freq = retrieve_recently_used_color_themes()
	if theme_used_and_freq:

		unused_color_dist, used_color_dist = retrieve_color_distance(theme_used_and_freq=theme_used_and_freq, color_dict=PRIMARY_COLORS, \
			dist_calc_dict='primary', color_idx=0)

		if unused_color_dist:
			high_contrast_set, medium_contrast_set, low_contrast_set = categorize_color_contrasts(unused_color_dist)
			if high_contrast_set:
				selected_primary_color = retrieve_highest_contrast_color(high_contrast_set)
			elif medium_contrast_set:
				selected_primary_color = retrieve_highest_contrast_color(medium_contrast_set)
			else:
				# i.e low_contrast_set
				selected_primary_color = retrieve_highest_contrast_color(low_contrast_set)
		else:
			# all colors used up? just select the least used primary color now
			selected_theme = sorted(theme_used_and_freq, key=itemgetter(1))[0][0]
			colors = COLOR_GRADIENTS[selected_theme]
			selected_primary_color = colors[0]

		available_pairs = PRIMARY_COLOR_GRADIENT_MAPPING[selected_primary_color]
		available_secondary_colors, available_secondary_colors_with_idx, idx = [], [], 0
		for theme in available_pairs:
			color = COLOR_GRADIENTS[theme][1]
			available_secondary_colors.append(color)
			available_secondary_colors_with_idx.append((color,idx))
			idx += 1

		unused_secondary_color_dist, used_secondary_color_dist = retrieve_color_distance(theme_used_and_freq=theme_used_and_freq, \
			color_dict=available_secondary_colors, dist_calc_dict='secondary', color_idx=1)

		if unused_secondary_color_dist:
			high_contrast_set, medium_contrast_set, low_contrast_set = categorize_color_contrasts(unused_secondary_color_dist)
		else:
			high_contrast_set, medium_contrast_set, low_contrast_set = categorize_color_contrasts(used_secondary_color_dist)
		if high_contrast_set:
			selected_secondary_color = retrieve_highest_contrast_color(high_contrast_set)
		elif medium_contrast_set:
			selected_secondary_color = retrieve_highest_contrast_color(medium_contrast_set)
		else:
			# i.e low_contrast_set
			selected_secondary_color = retrieve_highest_contrast_color(low_contrast_set)

		if selected_primary_color and selected_secondary_color and available_secondary_colors_with_idx:
			# now pick the theme these colors represent
			for secondary_color, idx in available_secondary_colors_with_idx: 
				if secondary_color == selected_secondary_color:
					selected_theme = PRIMARY_COLOR_GRADIENT_MAPPING[selected_primary_color][idx]

		return selected_theme, selected_primary_color, selected_secondary_color

	else:	
		selected_primary_color = PRIMARY_COLORS[6]
		selected_secondary_color = SECONDARY_COLORS[4]
		selected_theme = PRIMARY_COLOR_GRADIENT_MAPPING[selected_primary_color][0]
		return selected_theme, selected_primary_color, selected_secondary_color
	

##########################################################################################################
######################################### Create or Edit a Topic #########################################
##########################################################################################################


def change_topic_bg():
	"""
	Change the pre-set background color of a topic to a theme of your own choosing
	"""
	return ''


def change_topic_composer_options():
	"""
	Change the pre-set composer or 'posting type' options of a given topic

	posting_type: '0001' is only text, '0010' is only images, '0011' is only urls, '0100' is text+images, '0101' is images+url, '0110' is text+url, '0111' is text+images+url
	"""
	return ''


def change_topic_description():
	"""
	"""
	return ''


def change_topic_name():
	"""
	Change both topic name and topic url

	Problem: Doing this could undo SEO already generated around the topic
	"""
	return ''


def delete_topic(request, topic_url):
	"""
	Deletes given topic from redis, but PSQL data related to topics is untouched
	"""
	own_id = request.user.id
	is_defender, is_super_defender = in_defenders(own_id, return_super_status=True)
	if is_super_defender:
		if retrieve_topic_credentials(topic_url=topic_url, existence_only=True):
			retire_abandoned_topics(topic_urls=[topic_url])
		else:
			request.session["topic_gone"+str(own_id)] = '1'
			return redirect("topic_gone", topic_url)
	else:
		raise Http404("Not authorized to delete a topic")


def suggest_new_topic_feed(request):
	"""
	Topic suggestion form - doubling as a "creation" form currently
	"""
	if request.method == "POST":
		form = CreateTopicform(request.POST)
		if form.is_valid():
			topic_name, topic_in_url_form = form.cleaned_data['topic']
			description = form.cleaned_data['description']
			topic_owner_id = form.cleaned_data['topic_owner_id']
			time_now = time.time()
			theme_num, primary_color, secondary_color = allot_topic_bg()
			payload = {'d':description,'t':time_now,'oid':topic_owner_id,'tn':topic_name, 'url':topic_in_url_form,'priv':'0','th':theme_num,\
			'pt':'0001','num':0,'lpt':''}
			# 'num' is number of posts submitted to the given topic so far
			# 'lpt' is the time of the most recently submitted post
			# 'pt' is posting_type: '0001' is only text, '0010' is only images, '0011' is only urls, '0100' is text+images, '0101' is images+url, '0110' is text+url, '0111' is text+images+url
			
			# if topic_categories_exist:
			# 	counter = 0
			# 	for categ in categories:
			# 		payload['categ'+str(counter)] = categ
			# 		counter += 1
			
			created = create_topic_feed(topic_owner_id, payload, time_now)
			if created:
				secret_key = str(uuid.uuid4())
				set_text_input_key(user_id=topic_owner_id, obj_id='1', obj_type='home', secret_key=secret_key)
				context = {'c1':primary_color,'c2':secondary_color,'submissions':[],'form':SubmitInTopicForm(),\
				'topic':topic_name,'sk':str(secret_key),'topic_started':True,'topic_description':description,\
				'page':{},'topic_url':topic_in_url_form,'on_fbs':request.META.get('HTTP_X_IORG_FBS',False)}
				return render(request, 'topics/topic_home.html', context)
			else:
				# it already existed, so redirect to it
				request.session["cannot_recreate"+str(request.user.id)] = '1'
				return redirect("topic_page",topic_url=topic_in_url_form)
		else:
			return render(request,"topics/create_topic.html",{'form':form})
	else:
		return render(request,"topics/create_topic.html",{'form':CreateTopicform()})


##########################################################################################################
######################################### Populate a Topic Page ##########################################
##########################################################################################################


def topic_redirect(request, topic_url=None, obj_hash=None, *args, **kwargs):
	"""
	Used to redirect to specific spot in a specific topic (e.g. after writing or 'liking' something)
	"""
	############################################
	############################################
	request.session['rd'] = '1'#used by retention activity loggers in home_page() or topic_page() - can be removed
	############################################
	############################################
	if topic_url:
		if obj_hash:
			index = retrieve_topic_feed_index(topic_url, obj_hash)
		else:
			obj_hash = request.session.pop('home_hash_id',None)
			index = retrieve_topic_feed_index(topic_url, obj_hash) if obj_hash else 0
		if index is None:
			url = reverse_lazy("topic_page",args=[topic_url])+'?page=1#section0'
		else:
			addendum = get_addendum(index,ITEMS_PER_PAGE, only_addendum=True)
			url = reverse_lazy("topic_page",args=[topic_url])+addendum
		return redirect(url)
	else:
		return redirect('home')


def retrieve_topic_contribution_page_data(topic_url, page_num, with_oldest=False):
	"""
	Retrieves all contributions to a topic which are to be displayed in a particular page
	"""
	start_index, end_index = get_indices(page_num, ITEMS_PER_PAGE)
	obj_list, list_total_size = get_topic_feed(topic_url=topic_url, start_idx=start_index, end_idx=end_index, with_feed_size=True, touch_topic=True)
	num_pages = list_total_size/ITEMS_PER_PAGE
	max_pages = num_pages if list_total_size % ITEMS_PER_PAGE == 0 else (num_pages+1)
	page_num = int(page_num)
	list_of_dictionaries = retrieve_topic_feed_data(obj_list, topic_url)
	#######################
	if with_oldest:
		# must be done in this line, since the 't' information is lost subsequently
		try:
			oldest_post_time = list_of_dictionaries[-1]['t']
		except:
			oldest_post_time = 0.0
		#######################
		list_of_dictionaries = format_post_times(list_of_dictionaries, with_machine_readable_times=True)# move redis3's beautiful_date into views - that's where it belongs!
		return list_of_dictionaries, page_num, max_pages, oldest_post_time
	else:
		list_of_dictionaries = format_post_times(list_of_dictionaries, with_machine_readable_times=True)# move redis3's beautiful_date into views - that's where it belongs!
		return list_of_dictionaries, page_num, max_pages



def topic_page(request,topic_url):
	"""
	Displays all the posts related to a certain topic
	"""
	if topic_url:
		own_id = request.user.id
		time_now = time.time()
		if own_id:
			description, topic_name, bg_theme, is_subscribed = retrieve_topic_credentials(topic_url=topic_url, with_desc=True, with_name=True, \
				with_theme=True, with_is_subscribed=True, retriever_id=own_id)
			if description:
				page_num = request.GET.get('page', '1')
				list_of_dictionaries, page_num, max_pages, oldest_post_time = retrieve_topic_contribution_page_data(topic_url, page_num, \
					with_oldest=True)
				color_grads = COLOR_GRADIENTS[bg_theme]
				#######################
				# replyforms = {}
				# for obj in list_of_dictionaries:
				# 	replyforms[obj['h']] = PublicreplyMiniForm() #passing home_hash to forms dictionary
				#######################
				secret_key = str(uuid.uuid4())
				set_text_input_key(user_id=own_id, obj_id='1', obj_type='home', secret_key=secret_key)
				####################### Filter followers ####################	
				submitter_ids = set()
				for obj in list_of_dictionaries:
					 submitter_ids.add(str(obj['si']))

				ids_already_fanned = filter_following(submitter_ids,own_id)
				for obj in list_of_dictionaries:
					if str(obj['si']) in ids_already_fanned:
						obj['f'] = True
				#############################################################
				# enrich objs with information that 'own_id' liked them or not
				if retrieve_last_vote_time(voter_id=own_id) > oldest_post_time:
					recent_user_votes = retrieve_recent_votes(voter_id=own_id, oldest_post_time=oldest_post_time)
					# payload in recent_user_votes is voter_id+":"+target_user_id+":"+vote_value+":"+obj_type+":"+target_obj_id
					recent_user_voted_obj_hashes = set(obj.split(":",3)[-1] for obj in recent_user_votes)
					for obj in list_of_dictionaries:
						if obj['h'] in recent_user_voted_obj_hashes:
							obj['v'] = True# user voted for this particular object, mark it
				#######################

				page = {'next_page_number':page_num+1,'number':page_num,'has_previous':True if page_num>1 else False,\
				'has_next':True if page_num<max_pages else False,'previous_page_number':page_num-1}

				context = {'submissions':list_of_dictionaries,'form':SubmitInTopicForm(),'topic':topic_name,\
				'sk':str(secret_key),'topic_description':description,'c1':color_grads[0],'c2':color_grads[1],\
				'dir_rep_invalid':request.session.pop("dir_rep_invalid"+str(own_id),None),'time_now':time_now,\
				'ident':own_id, 'validation_error':request.session.pop("validation_error",''),'topic_url':topic_url,\
				'is_subscribed':is_subscribed, 'new_subscriber':request.session.pop("subscribed"+str(own_id),None),\
				'cannot_recreate':request.session.pop("cannot_recreate"+str(own_id),None), 'page':page,\
				'thin_rep_form':DirectResponseForm(thin_strip=True),'dir_rep_form':DirectResponseForm(with_id=True),\
				'on_fbs':request.META.get('HTTP_X_IORG_FBS',False)}
				
				################### Retention activity logging ###################
				from_redirect = request.session.pop('rd',None)
				if not from_redirect and own_id > SEGMENT_STARTING_USER_ID:
					time_now = time_now
					act = 'T' if request.mobile_verified else 'T.u'
					activity_dict = {'m':'GET','act':act,'url':topic_url,'t':time_now,'pg':page_num}# defines what activity just took place
					log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
				###################################################################

				return render(request, 'topics/topic_home.html', context)
			else:
				# topic does not exist - perhaps it was older than 7 days and has expired?
				request.session["topic_gone"+str(own_id)] = '1'
				return HttpResponsePermanentRedirect("/topic/gone/{}/".format(topic_url))
		else:
			# user is not authenticated
			topic_name, description, bg_theme = retrieve_topic_credentials(topic_url=topic_url, existence_only=False, with_desc=True,\
			with_name=True, with_theme=True)
			if description:

				page_num = request.GET.get('page', '1')

				list_of_dictionaries, page_num, max_pages = retrieve_topic_contribution_page_data(topic_url, page_num)
				color_grads = COLOR_GRADIENTS[bg_theme]
				#######################
				# replyforms = {}
				# for obj in list_of_dictionaries:
				# 	replyforms[obj['h']] = PublicreplyMiniForm() #passing home_hash to forms dictionary
				#######################
				
				page = {'next_page_number':page_num+1,'number':page_num,'has_previous':True if page_num>1 else False,\
				'has_next':True if page_num<max_pages else False,'previous_page_number':page_num-1}

				context = {'submissions':list_of_dictionaries,'form':SubmitInTopicForm(),'topic':topic_name,'page':page,\
				'sk':'','topic_description':description,'c1':color_grads[0],'c2':color_grads[1], 'is_subscribed':False,\
				'thin_rep_form':DirectResponseForm(thin_strip=True),'dir_rep_form':DirectResponseForm(with_id=True),\
				'topic_url':topic_url,'ident':None,'on_fbs':request.META.get('HTTP_X_IORG_FBS',False),'time_now':time_now}
				
				return render(request, 'topics/unauth_topic_home.html', context)
			else:
				raise Http404("This topic no longer exists")
	else:
		raise Http404("Topic is required")


def topic_gone(request, topic_url):
	"""
	If topic has expired, we render a special page for it here
	"""
	user_id = request.user.id
	if user_id:
		is_topic_gone = request.session.pop("topic_gone"+str(user_id),'')
		if is_topic_gone:
			return render(request,"topics/topic_gone.html",status=404)
		else:
			# user is hitting the page without being prompted - this is a generic 404
			raise Http404("This page cannot be populated")
	else:
		raise Http404("There is nothing here")


##########################################################################################################
######################################### Display topic listing ##########################################
##########################################################################################################


def topic_listing(request):
	"""
	Displays all topics currently available in Damadam
	"""
	################### Retention activity logging ###################
	own_id = request.user.id
	from_redirect = request.session.pop('rd',None)# remove this too when removing retention activity logger
	if not from_redirect and  own_id > SEGMENT_STARTING_USER_ID:
		time_now = time.time()
		act = 'Z5' if request.mobile_verified else 'Z5.u'
		activity_dict = {'m':'GET','act':act,'t':time_now}# defines what activity just took place
		log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
	##################################################################
	context = {}
	newbie_flag = request.session.get("newbie_flag",None)
	if newbie_flag == '6':
		context["newbie_flag"] = True
		context["newbie_tutorial_page"] = 'tutorial6.html'
		context["newbie_lang"] = request.session.get("newbie_lang",None)
		context['origin'] = '27'
	return render(request,"topics/topics_list.html",context)


##########################################################################################################
########################################## Submit a Topic Post ###########################################
##########################################################################################################


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def submit_topic_post(request,topic_url):
	"""
	Submit's a user's post into a topic
	"""
	own_id = request.user.id
	if request.method == "POST":
		on_fbs = request.META.get('HTTP_X_IORG_FBS',False)
		on_opera = request.is_opera_mini
		is_js_env = retrieve_user_env(opera_mini=on_opera, fbs = on_fbs)
		# on_opera = True if (not on_fbs and not is_js_env) else False
		if on_opera:
			# disallowing opera mini users from posting public text posts on topics
			# mislabeled template - used to show some generic errors and such to posters
			return render(request, 'error_photo.html', {'opera_detected':True, 'topic':topic_url})
		else:
			banned, time_remaining, ban_details = check_content_and_voting_ban(own_id, with_details=True)
			if banned:
				return render(request, 'links/link_form.html', {'time_remaining': time_remaining,'ban_details':ban_details,'forbidden':True,\
					'own_profile':True,'defender':None,'is_profile_banned':True})
			else:
				topic_name, bg_theme, is_subscribed = retrieve_topic_credentials(topic_url=topic_url, with_name=True, with_theme=True, \
					with_is_subscribed=True, retriever_id=own_id)
				if is_subscribed:
					time_now = time.time()
					mobile_verified = request.mobile_verified
					if not mobile_verified:
						################### Retention activity logging ###################
						if own_id > SEGMENT_STARTING_USER_ID:
							activity_dict = {'m':'POST','act':'T1.u','t':time_now}
							log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
						###################################################################
						return render(request, 'verification/unable_to_submit_without_verifying.html', {'share_on_home':True})
					elif request.user_banned:
						return redirect("error")
					else:
						ttl, type_of_rate_limit = content_sharing_rate_limited(own_id)
						if ttl:
							# this is wrongly named, but tells the user to wait
							return render(request, 'error_photo.html', {'time':ttl,'origin':'22','tp':type_of_rate_limit,'topic_url':topic_url,\
								'sharing_limit':NUM_SUBMISSION_ALLWD_PER_DAY})
						else:
							banned, time_remaining, ban_details = check_content_and_voting_ban(own_id, with_details=True)
							if banned:
								# Cannot submit topic contribution if banned
								request.session["origin_topic"] = topic_url
								return render(request, 'judgement/cannot_comment.html', {'time_remaining': time_remaining,'ban_details':ban_details,\
									'forbidden':True,'own_profile':True,'defender':None,'is_profile_banned':True, 'org':'22'})
							else:
								form = SubmitInTopicForm(request.POST,user_id=own_id)
								if form.is_valid():
									text = form.cleaned_data['description']
									alignment = form.cleaned_data['alignment']
									submitter_name, av_url = retrieve_credentials(own_id,decode_uname=True)
									# parking bg_theme, topic url and name in 'url'
									url = bg_theme+":"+topic_name+":"+topic_url

									post_data = {'ct':'t','aud':'p','exp':'i','ein':-1,'d':text,'a':alignment,\
									'tp':url,'turl':topic_url,'tn':topic_name,'tbg':bg_theme,'origin':'from_topic_page',\
									'com':'1'}
									
									set_temp_post_data(user_id=own_id,data=json.dumps(post_data),post_type='tx',obj_id=None)
									
									################### Retention activity logging ###################
									if own_id > SEGMENT_STARTING_USER_ID:
										request.session['ft'] = '1'
										request.session['rd'] = '1'
										activity_dict = {'m':'POST','act':'T1','t':time_now,'tx':text,'url':topic_url}
										log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
									###################################################################

									return redirect("publish_post")
								else:
									################### Retention activity logging ###################
									if own_id > SEGMENT_STARTING_USER_ID:
										request.session['rd'] = '1'
										activity_dict = {'m':'POST','act':'T1.i','t':time_now,'tx':request.POST.get("description",''),'url':topic_url}
										log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
									###################################################################
									error_string = form.errors.as_text().split("*")[2]
									if error_string:
										request.session["validation_error"] = error_string
									return redirect("topic_page", topic_url=topic_url)
				else:
					# Some kind of error, just redirect to topic page
					return redirect("topic_page", topic_url=topic_url)
	else:
		# this is a GET request
		return redirect("topic_page",topic_url=topic_url)


##########################################################################################################
########################################### Topic Subscription ###########################################
##########################################################################################################


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def subscribe_to_topic(request, topic_url):
	"""
	Subscribe user to a given topic
	"""
	if request.mobile_verified:
		if request.method == "POST":
			subscription_screen = request.POST.get("sub_scr",'')
			if subscription_screen == '1':
				topic_name, description, theme = retrieve_topic_credentials(topic_url, existence_only=False, with_desc=True, with_name=True, \
					with_theme=True)
				colors = COLOR_GRADIENTS[theme]
				return render(request,'topics/subscribe_to_topic.html',{'topic_url':topic_url,'topic_name':topic_name,'desc':description,\
					'org':'22','c1':colors[0],'c2':colors[1]})
			elif subscription_screen == '2':
				if retrieve_topic_credentials(topic_url=topic_url, existence_only=True):
					own_id, time_now = request.user.id, time.time()
					subscribe_topic(own_id, topic_url, time_now)
					request.session["subscribed"+str(own_id)] = '1'
					response = redirect("topic_page",topic_url=topic_url)
					response['Location'] += '?subscribed=True#section0'# added 'subscribe' parameter so that the act of subscription is measured separately in GA
					################### Retention activity logging ###################
					if own_id > SEGMENT_STARTING_USER_ID:
						request.session['rd'] = '1'
						activity_dict = {'m':'POST','act':'W4.s','t':time_now,'url':topic_url}
						log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
					###################################################################
					return response
				else:
					# didn't work because topic has ceased to exist!
					return redirect("topic_page",topic_url=topic_url)
			else:
				# it won't work
				return redirect("topic_page",topic_url=topic_url)
		else:
			# this is a GET request
			return redirect("topic_page",topic_url=topic_url)
	else:
		################### Retention activity logging ###################
		own_id = request.user.id
		if own_id > SEGMENT_STARTING_USER_ID:
			time_now = time.time()
			activity_dict = {'m':'POST','act':'W4.u','t':time_now}
			log_user_activity.delay(user_id=own_id, activity_dict=activity_dict, time_now=time_now)
		###################################################################
		return render(request,"verification/unable_to_submit_without_verifying.html",{'subscribe_to_topic':True})



def unsubscribe_topics(request):
	"""
	Render a list of user's topics, and provide "unsubscribe" functionalitys
	"""
	own_id = request.user.id
	if request.method == "POST":
		topic_urls = request.POST.getlist("turl",[])
		decision = request.POST.get("dec",0)
		if decision == '1' and topic_urls:
			# there are topics to unsubscribe from
			untouched_topics = bulk_unsubscribe_topic(subscriber_id=own_id, topic_urls=topic_urls)
			if untouched_topics:
				request.session["successfully_unsubscribed"+str(own_id)] = '2'
			else:
				request.session["successfully_unsubscribed"+str(own_id)] = '1'
		return redirect("user_profile",request.user.username)
	else:
		# render unsubscription options
		return render(request,"topics/unsubscribe_topics.html",{'subscribed_topics':retrieve_subscribed_topics(str(own_id))})


##########################################################################################################
############################################### Utilities ################################################
##########################################################################################################


def isolate_topic_data(topic_data, colors_only=False):
	"""
	Isolate topic data from composite payload of type "theme:topic_name:topic_url"

	Used by retrieve_direct_response_data() in direct_response_views.py
	"""
	if colors_only:
		color_grads = COLOR_GRADIENTS[topic_data]
		return color_grads[0], color_grads[1]
	else:
		data = topic_data.split(":")
		theme, topic_name, topic_url = data[0], data[1], data[2]
		color_grads = COLOR_GRADIENTS[theme]
		c1, c2 = color_grads[0], color_grads[1]
		return theme, topic_name, c1, c2, topic_url