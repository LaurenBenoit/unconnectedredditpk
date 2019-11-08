import time
import ujson as json
from django.db.models import F
from django.http import Http404
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render, redirect
from score import DELETION_THRESHOLD
from redis3 import is_already_banned
from page_controls import ITEMS_PER_PAGE
from templatetags.s3 import get_s3_object
from topic_views import isolate_topic_data
from redirection_views import return_to_content
from group_views import personal_group_sanitization
from direct_response_forms import DirectResponseForm
from django.views.decorators.csrf import csrf_protect
from models import Publicreply, Link, PhotoComment, Photo
from redis4 import retrieve_uname, retrieve_bulk_unames, retrieve_avurl
from views import get_indices, break_text_into_prefix_and_postfix, convert_to_epoch
from redis7 import check_content_and_voting_ban, invalidate_cached_public_replies, store_inline_reply
from tasks import publicreply_notification_tasks, trim_group_submissions, set_input_rate_and_history, direct_response_tasks
from redis9 import retrieve_direct_response_list, delete_single_direct_response, bulk_delete_selective_dir_reps_of_single_user, \
submit_direct_response
from redis6 import retrieve_single_group_submission, save_group_submission, invalidate_cached_mehfil_replies, invalidate_presence,\
retrieve_group_uuid, populate_reply_mapping
from redis5 import add_content_to_personal_group, get_personal_group_anon_state, mark_personal_group_attendance, update_personal_group_last_seen,\
set_uri_metadata_in_personal_group


################################################# Utilities #################################################


def retrieve_target_text(obj_id, submitter_id, parent_obj_id, obj_type, is_main_reply):
	"""
	Helper function for retrieve_direct_response_data() below
	"""
	###################################################################
	# reply from text box under the post (img or text)
	if is_main_reply:
		if obj_type == '3':
			# return text post description
			link = Link.objects.values('url','description').filter(id=parent_obj_id)[0]
			return link['description'], link['url']
		elif obj_type == '4':
			# return img post caption and url
			photo = Photo.objects.values('image_file','caption').filter(id=parent_obj_id)[0]
			return photo['caption'], photo['image_file']
	
	###################################################################
	# 'reply to reply' under comments of various posts 
	else:
		if obj_type == '3':
			# text post: return target of "reply to reply", or simple reply
			try:
				target_text = Publicreply.objects.only('description').get(id=obj_id,submitted_by_id=submitter_id,answer_to=parent_obj_id).description
			except Publicreply.DoesNotExist:
				target_text = ''
			return target_text
		elif obj_type == '4':
			# img post: return target of "reply to reply", or simple reply
			try:
				target_text = PhotoComment.objects.only('text').get(id=obj_id,submitted_by_id=submitter_id,which_photo=parent_obj_id).text
			except:
				target_text = ''
			return target_text
		elif obj_type in ('5','6'):
			# public/private mehfil
			target_text, target_img_url, group_uuid, group_topic  = retrieve_single_group_submission(parent_obj_id, obj_id, text_img_tp_uuid=True)
			return target_text, target_img_url, group_topic, group_uuid


def retrieve_direct_response_data(obj_type, target_user_id, obj_id, parent_obj_id, is_main_reply, own_id, own_uname):
	"""
	Retrieves data required to handle various kinds of direct replies
	"""
	obj_exists, target_text, parent_uname, parent_text, topic_name, theme, c1, c2, topic_url, parent_user_id, image_url, group_topic, \
	group_uuid = False, '', '', '', '', '', '', '', '', None, None, None, None
	
	###################################################################
	# reply from text box under the post (img or text)
	if is_main_reply:
		if obj_type == '3':
			# reply under text post
			parent_text, topic_data = retrieve_target_text(obj_id=obj_id, submitter_id=target_user_id, parent_obj_id=parent_obj_id, \
				obj_type=obj_type, is_main_reply=is_main_reply)
			if topic_data:
				theme, topic_name, c1, c2, topic_url = isolate_topic_data(topic_data)
			else:
				theme, topic_name, c1, c2, topic_url = None, '', '', '', ''
			parent_user_id = target_user_id
			parent_uname = retrieve_uname(target_user_id,decode=True)
			obj_exists = True
		elif obj_type == '4':
			# reply under img post
			parent_text, image_url = retrieve_target_text(obj_id=obj_id, submitter_id=target_user_id, parent_obj_id=parent_obj_id, \
				obj_type=obj_type, is_main_reply=is_main_reply)
			parent_user_id = target_user_id
			parent_uname = retrieve_uname(target_user_id,decode=True)
			obj_exists = True
		elif obj_type == '7':
			# reply in 1on1 (even 'reply to reply' is deemed as a 'main_reply' for the purposes of a 1on1)
			own_anon_status, their_anon_status, group_id = get_personal_group_anon_state(own_id, target_user_id)
			if group_id == parent_obj_id:
				# performing a double check
				obj_exists = True
				parent_uname = retrieve_uname(target_user_id,decode=True)
				parent_text = '1 on 1 with {}'.format(own_uname.decode('utf-8')[:1].upper()) \
				if their_anon_status else '1 on 1 with {}'.format(own_uname)# group topic
			else:
				obj_exists = False
	
	###################################################################
	# 'reply to reply' under comments of various posts 
	else:
		if obj_type == '3':
			# 'reply to reply' under a text post
			target_text = retrieve_target_text(obj_id=obj_id, submitter_id=target_user_id, parent_obj_id=parent_obj_id, obj_type=obj_type,\
				is_main_reply=is_main_reply)
			if target_text:
				obj_exists = True
				data = Link.objects.values('url','description','submitter').filter(id=parent_obj_id)[0]
				if data:
					topic_data, parent_text, parent_user_id = data['url'], data['description'], data['submitter']
					parent_uname = retrieve_uname(parent_user_id,decode=True)
					if topic_data:
						theme, topic_name, c1, c2, topic_url = isolate_topic_data(topic_data)
					else:
						theme, topic_name, c1, c2, topic_url = None, '', '', '', ''
		elif obj_type == '4':
			# 'reply to reply' under an img post
			target_text = retrieve_target_text(obj_id=obj_id, submitter_id=target_user_id, parent_obj_id=parent_obj_id, obj_type=obj_type,\
				is_main_reply=is_main_reply)
			if target_text:
				obj_exists = True
				data = Photo.objects.values('image_file','caption','owner').filter(id=parent_obj_id)[0]
				if data:
					parent_text, parent_user_id, image_url = data['caption'], data['owner'], data['image_file']
					parent_uname = retrieve_uname(parent_user_id,decode=True)
		elif obj_type in ('5','6'):
			# reply to chat in public/private mehfil
			target_text, image_url, group_topic, group_uuid = retrieve_target_text(obj_id=obj_id, submitter_id=target_user_id, \
				parent_obj_id=parent_obj_id, obj_type=obj_type, is_main_reply=is_main_reply)
			if group_uuid:
				obj_exists = True
	return obj_exists, target_text, parent_uname, parent_text, parent_user_id, topic_name, theme, c1, c2, topic_url, image_url, group_topic, \
	group_uuid


################################################# Direct response functionality #################################################


@csrf_protect
def render_direct_response_form(request):
	"""
	Renders a form, using which, a user can send a "direct reply" to another user
	"""
	if request.method == "POST":
		if not request.mobile_verified:
			return render(request,"verification/unable_to_submit_without_verifying.html",{'direct_reply':True})
		else:
			direct_response_payload = request.POST.get("dr_pl",'')
			topic_url = request.POST.get('topic_url','')
			if direct_response_payload:
				data = direct_response_payload.split(":")
				try:
					origin, obj_type, parent_obj_id, target_obj_id, target_user_id, text = data[0], data[1], data[2], data[3], data[4], \
					data[5]
					return render(request,"direct_response/direct_response_form.html",{'origin':origin,'poid':parent_obj_id,\
						'form':DirectResponseForm(render_page_with_one_response=True),'tunm':retrieve_uname(target_user_id,True), \
						'tuid':target_user_id, 'text':text, 'obid':target_obj_id, 'lid':'tx:'+parent_obj_id,'obtp':obj_type,\
						'topic_url':topic_url})
				except IndexError:
					raise Http404("Data has been messed with!")
			else:
				raise Http404("Payload is missing")	
	else:
		raise Http404("Doesn't work with GET requests")


@csrf_protect
def post_direct_response(request):
	"""
	Processes a direct reply, a.k.a direct response (send, skip or block)
	
	A direct response is broadly originate from two places: 'main reply' (i.e. replied from text box under post), or 'reply of reply' (i.e. replied to a reply under a post)

	A direct response can be of various types (called ob_type), including:
	'3' reply to reply under text post, OR reply under text post
	'4' reply to reply under photo post, OR reply under img post
	'5' reply to chat in pub mehfil
	'6' reply to chat in priv mehfil
	'7' reply to chat in 1on1
	"""
	if request.method == "POST":
		if not request.mobile_verified:
			return render(request,"verification/unable_to_submit_without_verifying.html",{'direct_reply':True})
		elif request.user_banned:
			raise Http404("Hell banned users can't avail this facility")
		else:
			origin = request.POST.get("origin",None)
			target_id = request.POST.get("tuid",None)
			parent_obj_id = request.POST.get("poid",None)
			own_id = request.user.id
			username_dictionary = retrieve_bulk_unames([own_id,target_id],decode=True)
			own_username, target_uname = username_dictionary[own_id], username_dictionary[int(target_id)]
			banned, time_remaining, ban_detail = check_content_and_voting_ban(own_id, with_details=True)
			if banned:
				# display template announcing that the user is banned from doing this
				return render(request,"direct_response/direct_response_errors.html",{'content_ban':True,'org':origin,'uname':own_username,\
					'obid':parent_obj_id,'time_remaining':time_remaining,'ban_detail':ban_detail,'defender':False,'own_profile':True})
			else:
				decision = request.POST.get("dec",None)# dec: '0' means block, '1' means skip, '2' means cancel (non-JS), '3' means send
				single_response = request.POST.get("srep",None)
				obj_type = request.POST.get("obtp",None)
				from_direct_response_list = request.POST.get("drl",False)
				is_main_reply = request.POST.get("mr",False)# two kinds of replies: 'main' and 'line'. Main replies happen from text boxes under posts. Inline replies via the reply button next to a comment, or via direct_response_list
				is_single_response = True if single_response else False
				replying_on_own_post = False
				is_reply_to_reply = False
				topic_url = request.POST.get("top_url",None)
				if topic_url:
					request.session["origin_topic"] = topic_url

				############################################################
				if decision == '0':
					# 'block' the sender of this direct response (only works from direct response list)
					request.session['from_dir_rep_list'+str(own_id)] = origin# from direct response list
					request.session['tuid'+str(own_id)] = target_id
					return redirect("enter_inter_user_ban")
				elif decision == '1':
					# send the direct response
					############################################################
					# some more validation checks first

					if str(target_id) == str(own_id):
						if is_main_reply:
							# allowed to reply to 'self' from main text boxes (but not from inline 'reply' buttons next to each comment)
							replying_on_own_post = True
						else:
							# cannot reply to 'self' in other cases
							return render(request,"direct_response/direct_response_errors.html",{'resp_to_self':True,'org':origin,\
								'obid':parent_obj_id})
					else:
						banned_by, ban_time = is_already_banned(own_id=own_id,target_id=target_id, return_banner=True)
						if banned_by:
							# origins checked: inbox, home, best photos, fresh photos
							#############################################################
							# there's a block that exists between you and the target - disallowed from proceeding
							if origin in ('15','16'):
								# these are public and private groups
								parent_obj_id = retrieve_group_uuid(parent_obj_id)
							return render(request,"direct_response/direct_response_errors.html",{'blocked':True,'org':origin,\
								'obid':parent_obj_id})
					############################################################
					"""
					Data we need:
					- origin
					- parent_obj_id
					- target_obj_id (can be same as parent_obj_id)
					- target_id
					- target_obj_tp
					- text (submitted by replier)

					Data we still need:
					- topic_name
					- topic_theme
					"""
					obj_id = request.POST.get("obid",None)
					own_avurl = retrieve_avurl(own_id)
					if target_uname:
						form = DirectResponseForm(request.POST,obj_type=obj_type,parent_obj_id=parent_obj_id,sender_id=target_id,\
							receiver_id=own_id)
						if form.is_valid():
								
							#'3' reply on text, or reply to reply on text, '4' reply on photo, or reply on reply on photo, '5' comment on public mehfil text, '6' comment on private mehfil text
							
							is_main_reply = '1' if obj_type == '7' else is_main_reply# i.e. always a main_reply if obj_type is '7'
							
							obj_exists, target_text, parent_uname, parent_text, parent_user_id, topic_name, theme, c1, c2, \
							topic_url, image_url, group_topic, group_uuid = retrieve_direct_response_data(obj_type=obj_type,\
								target_user_id=target_id, obj_id=obj_id, parent_obj_id=parent_obj_id,is_main_reply=is_main_reply,\
								own_id=own_id, own_uname=own_username)
						
							###########################################################################
							if obj_exists:
								# process the direct response
								if target_text:
									target_text_prefix, target_text_postfix = break_text_into_prefix_and_postfix(target_text)
								else:
									target_text_prefix, target_text_postfix = '', ''
								text, tgt_is_hidden = form.cleaned_data['direct_response']# what the submitter wrote							
								lid, db_obj_id, created_obj_type, idx = None, None, None, None

								# this is a 'reply' from a text box under a post (img or txt)
								if is_main_reply:
									if obj_type == '3':
										# '1' reply under text post
										if replying_on_own_post:
											db_obj = Publicreply.objects.create(submitted_by_id=own_id, answer_to_id=parent_obj_id, \
												description=text, level=1)
										else:
											db_obj = Publicreply.objects.create(submitted_by_id=own_id, answer_to_id=parent_obj_id, \
												direct_reply_tgt_uname=target_uname, description=text, level=1)
										time_now = convert_to_epoch(db_obj.submitted_on)
										lid = 'tx:'+parent_obj_id
										# delete cached 'jawab' page
										invalidate_cached_public_replies(parent_obj_id)
										db_obj_id = db_obj.id
										created_obj_type = obj_type
									elif obj_type == '4':
										# '2' replying under image post
										if replying_on_own_post:
											db_obj = PhotoComment.objects.create(submitted_by_id=own_id, which_photo_id=parent_obj_id, \
												text=text, level=1)
										else:
											db_obj = PhotoComment.objects.create(submitted_by_id=own_id, which_photo_id=parent_obj_id, \
												direct_reply_tgt_uname=target_uname, text=text, level=1)
										time_now = convert_to_epoch(db_obj.submitted_on)
										lid = 'img:'+parent_obj_id
										db_obj_id = db_obj.id
										created_obj_type = obj_type
									elif obj_type == '7':
										# '7' replying to chat in 1on1 (always considered a 'main_reply')
										type_ = 'text'# the reply is a vanilla 'text' reply
										time_now = time.time()
										obj_count, obj_ceiling, gid, bid, idx, img_id, img_wid, hw_ratio = add_content_to_personal_group(content=text,\
											type_=type_, writer_id=own_id, group_id=parent_obj_id)
										personal_group_sanitization(obj_count, obj_ceiling, gid)
										
										# the following are usually called in private_chat_tasks.delay() - we're encapsulating them here
										mark_personal_group_attendance(own_id, target_id, parent_obj_id, time_now)
										update_personal_group_last_seen(own_id, parent_obj_id, time_now)
										set_uri_metadata_in_personal_group(own_id, text, parent_obj_id, bid, idx, type_)
										
										db_obj_id = bid# blob_id
										created_obj_type = obj_type
								
								# this is a 'reply to a reply', and can originate from a variety of places!
								else:
									if obj_type == '3':
										# '3' reply under text post, or reply to reply under text post
										level = Publicreply.objects.only('level').get(id=obj_id).level
										new_level = level+1 if level else 1
										db_obj = Publicreply.objects.create(submitted_by_id=own_id, answer_to_id=parent_obj_id, \
											direct_reply_tgt_uname=target_uname,direct_reply_tgt_text_prefix=target_text_prefix,\
											direct_reply_tgt_text_postfix=target_text_postfix, direct_reply_id=obj_id, \
											description=text, level=new_level)
										time_now = convert_to_epoch(db_obj.submitted_on)
										lid = 'tx:'+parent_obj_id
										# delete cached 'jawab' page
										invalidate_cached_public_replies(parent_obj_id)
										db_obj_id = db_obj.id
										created_obj_type = obj_type
									elif obj_type == '4':
										# '4' reply under img post, or reply to reply under img post
										level = PhotoComment.objects.only('level').get(id=obj_id).level
										new_level = level+1 if level else 1
										db_obj = PhotoComment.objects.create(submitted_by_id=own_id, which_photo_id=parent_obj_id, \
											direct_reply_tgt_uname=target_uname, direct_reply_tgt_text_prefix=target_text_prefix,\
											direct_reply_tgt_text_postfix=target_text_postfix, direct_reply_id=obj_id,text=text,\
											level=new_level)
										time_now = convert_to_epoch(db_obj.submitted_on)
										lid = 'img:'+parent_obj_id
										db_obj_id = db_obj.id
										created_obj_type = obj_type
									elif obj_type in ('5','6'):
										# '5' reply to chat in public mehfil, '6' is reply to chat in private mehfil
										# note: 'target_image' is an image url from the targeted (parent) text
										time_now = time.time()
										db_obj_id, num_submissions = save_group_submission(writer_id=own_id, \
											group_id=parent_obj_id, text=text, target_image=image_url, posting_time=time_now, \
											writer_avurl=get_s3_object(own_avurl,category='thumb'), category='11', \
											writer_uname=own_username, target_uname=target_uname, target_uid=target_id,\
											save_latest_submission=True, direct_reply_tgt_text_prefix=target_text_prefix,\
											direct_reply_tgt_text_postfix=target_text_postfix, tgt_is_hidden=tgt_is_hidden)
										if num_submissions > DELETION_THRESHOLD:
											# delete extra submissions in group
											trim_group_submissions.delay(parent_obj_id)
										created_obj_type = obj_type
										populate_reply_mapping(obj_type=created_obj_type, parent_obj_id=parent_obj_id, \
											targeted_reply_id=obj_id, reply_id=db_obj_id)
										invalidate_cached_mehfil_replies(parent_obj_id)
										invalidate_presence(parent_obj_id)
										set_input_rate_and_history.delay(section='pub_grp' if obj_type == '5' else 'prv_grp', \
											section_id=parent_obj_id, text=text, user_id=own_id, time_now=time_now)
									elif obj_type == '7':
										# '7' reply to 1on1 - this is always a "main_reply" so isn't handled here
										pass

								###########################################################################
								###########################################################################
								if db_obj_id and created_obj_type:
									if replying_on_own_post:
										###############################################################
										# no need to log this reply in any direct response list at all - op is commenting generally under their post
										pass
									else:
										###############################################################
										# Log the reply in the direct response list
										payload = {'tx':text,'tun':target_uname,'t':time_now,'tid':target_id,'obid':obj_id,\
										'sid':own_id,'dbid':db_obj_id,'sun':own_username,'ptun':parent_uname,'poid':parent_obj_id, \
										'ptx':parent_text,'ot':created_obj_type}

										# is there a text prefix? If so, add the following field
										if target_text_prefix:
											payload['ttxpre'] = target_text_prefix
										
										# is there a text postfix? If so, add the following field
										if target_text_postfix:
											payload['ttxpos'] = target_text_postfix
										
										# is there an image (either as a parent obj, or as chat content)? If so, add the following fields
										if image_url:
											if obj_type == '4':
												# photo obj: only add value for 'piu' (parent image url)
												payload['piu'] = image_url
											elif obj_type in ('5','6'):
												# mehfils: add value for 'tiu' (target_image url)
												payload['tiu'] = image_url
											elif obj_type == '7':
												# 1on1: the image is part of the chat the user sent
												payload['iu'] = image_url
											else:
												pass

										# add the following if topics are involved
										if topic_name:
											payload['tn'], payload['th'], payload['c1'], payload['c2'], payload['tu'] = topic_name, theme,\
											c1, c2, topic_url

										# add the following if groups (mehfils) are involved
										if group_topic and group_uuid:
											payload['gtp'] = group_topic
											payload['guid'] = group_uuid

										if idx:
											payload['idx'] = idx

										###############################################################
										# submitting for the 'direct response list' in inbox
										submit_direct_response(json_data=json.dumps(payload), time_now=time_now, sender_id=own_id, \
											target_user_id=target_id, obj_type=obj_type, parent_obj_id=parent_obj_id, reply_id=obj_id)
										
										###############################################################
										# delete the message that was responded to, if it exists in 'direct response list'
										is_reply_to_reply = delete_single_direct_response(target_user_id=own_id, obj_type=obj_type, \
											parent_obj_id=parent_obj_id, sender_id=target_id)

									###############################################################
									# updating said reply in the 'hash object' of the parent object (accessed by feeds, or mehfils, etc)
									if obj_type in ('3','4'):

										# a 'main' reply doesn't need to appear with any addendum
										if is_main_reply:
											if replying_on_own_post:
												# no need to include 'target_uname' in this case
												store_inline_reply(parent_obj_type=obj_type, parent_obj_id=parent_obj_id, reply_text=text, \
													reply_writer_id=own_id, reply_id=db_obj_id, reply_writer_uname=own_username, \
													time_now=time_now)
											else:
												# include comment_target (target_uname) so that 'uname' can be shown in the reply
												store_inline_reply(parent_obj_type=obj_type, parent_obj_id=parent_obj_id, reply_text=text, \
													reply_writer_id=own_id, reply_id=db_obj_id, reply_writer_uname=own_username, \
													time_now=time_now, reply_target=target_uname)
										
										# a 'reply to reply' needs to appear with an addendum (a.k.a reference)
										else:
											store_inline_reply(parent_obj_type=obj_type, parent_obj_id=parent_obj_id, reply_text=text, \
												reply_writer_id=own_id, reply_id=db_obj_id, reply_writer_uname=own_username, \
												time_now=time_now, reference_id=obj_id, reply_target=target_uname, \
												target_text_prefix=target_text_prefix,target_text_postfix=target_text_postfix)

									elif obj_type in ('5','6'):
										parent_obj_id = group_uuid# this is needed for return_to_content() below
									
									###############################################################
									if from_direct_response_list:
										request.session["dir_rep_sent"+str(own_id)] = target_uname
										request.session["dir_rep_tgt_obj_type"+str(own_id)] = obj_type
										request.session["dir_rep_tgt_obj_id"+str(own_id)] = target_id if obj_type == '7' else parent_obj_id

									# log direct response metrics, and some other stuff
									direct_response_tasks.delay(action_status=is_reply_to_reply, action_type='1', \
										parent_obj_id=parent_obj_id, obj_owner_id=parent_user_id,obj_hash_name=lid, \
										obj_type=obj_type, commenter_id=own_id, time_now=time_now)

									return return_to_content(request=request,origin=origin,obj_id=parent_obj_id,link_id=lid,\
										target_uname=request.POST.get('rorigin',None))#using target_uname as a 'placeholder' for some extra data
								else:
									# object not created
									raise Http404("Something went wrong - could not create the object!")
							
							# the obj doest not exist
							else:
								raise Http404("The parent object does not exist")

						else:
							# form is invalid - redirect to 'origin' and show relevant error message
							error_string = form.errors.as_text().split("*")[2]

							if from_direct_response_list:
								request.session["dir_rep_invalid"+str(own_id)] = error_string
								return return_to_content(request=request,origin=origin,obj_id=parent_obj_id,link_id=None,\
										target_uname=target_uname)
							elif is_single_response:
								return render(request,"direct_response/direct_response_form.html",{'origin':origin,'poid':parent_obj_id,\
									'form':form,'tunm':target_uname, 'tuid':target_id, 'obid':obj_id,'obtp':obj_type})
							else:
								# handle all cases where the user could have redirected
								if origin == '1':
									# fresh photos
									request.session["dir_rep_invalid"+str(own_id)] = error_string
									return redirect(reverse_lazy("photo", args=['fresh-list'])+'?page=1#error')#redirecting to special error section
								elif origin == '2':
									# best photos
									request.session["dir_rep_invalid"+str(own_id)] = error_string
									return redirect(reverse_lazy("photo", args=['best-list'])+'?page=1#error')#redirecting to special error section
								elif origin == '3':
									# text home
									request.session["dir_rep_invalid"+str(own_id)] = error_string
									return redirect(reverse_lazy("home")+'?page=1#error')#redirecting to special error section
								elif origin == '9':
									# text comment page
									request.session["dir_rep_invalid"+str(own_id)] = error_string
									return redirect(reverse_lazy("publicreply_view",kwargs={'parent_id':parent_obj_id})+'#error')#redirecting to special error section
								elif origin == '11':
									# text comment page
									request.session["dir_rep_invalid"+str(own_id)] = error_string
									return redirect(reverse_lazy("comment",kwargs={'pk':parent_obj_id,'origin':request.POST.get('rorigin',None)})+'#error')#redirecting to special error section
								elif origin == '16':
									# public mehfil
									request.session["dir_rep_invalid"+str(own_id)] = error_string
									request.session["public_uuid"] = retrieve_group_uuid(parent_obj_id)
									return redirect("public_group_reply")
								elif origin == '15':
									# priv mehfil
									request.session["dir_rep_invalid"+str(own_id)] = error_string
									request.session["unique_id"] = retrieve_group_uuid(parent_obj_id)
									return redirect("private_group_reply")
								elif origin == '19':
									# single notif on home
									request.session["dir_rep_invalid"+str(own_id)] = error_string
									return redirect(reverse_lazy("home")+'?page=1#error')#redirecting to special error section
								elif origin == '20':
									# single notif on fresh photos
									request.session["dir_rep_invalid"+str(own_id)] = error_string
									return redirect(reverse_lazy("photo", args=['fresh-list'])+'?page=1#error')#redirecting to special error section
								elif origin == '21':
									# single notif on best photos
									request.session["dir_rep_invalid"+str(own_id)] = error_string
									return redirect(reverse_lazy("photo", args=['best-list'])+'?page=1#error')#redirecting to special error section
								elif origin == '22':
									# topic page
									request.session["dir_rep_invalid"+str(own_id)] = error_string
									return redirect(reverse_lazy("topic_page",kwargs={'topic_url':topic_url})+'?page=1#error')#redirecting to special error section
								
								#####################################################
								# fallback if case remains unhandled
								return return_to_content(request=request,origin=origin,obj_id=parent_obj_id,link_id=None,\
									target_uname=None)

					else:
						# target_uname not found
						raise Http404("Not a legit user")
				elif decision == '3':
					# 'skip' this response and reload the page
					obj_type = request.POST.get("obtp",None)
					deleted = delete_single_direct_response(target_user_id=own_id, obj_type=obj_type, parent_obj_id=parent_obj_id, sender_id=target_id)
					if deleted:
						# log direct response metrics
						direct_response_tasks.delay(action_status=True, action_type='3', num_skips=1)
						# return to origin
						if from_direct_response_list:
							request.session["dir_rep_del"+str(own_id)] = retrieve_uname(target_id,decode=True)
						return return_to_content(request=request,origin=origin,obj_id=parent_obj_id,link_id=None,target_uname=None)
					else:
						# show error that 'could not be deleted'
						return render(request,"direct_response/direct_response_errors.html",{'unable_to_del':True,'org':origin,\
							'obid':parent_obj_id})
				elif decision == '2':
					# cancel sending direct response - and return to source
					obj_type = request.POST.get("obtp",None)
					if obj_type == '3':
						# link tabsra
						lid = 'tx:'+parent_obj_id
					elif obj_type == '4':
						# photo comment
						lid = 'img:'+parent_obj_id
					elif obj_type in ('5','6'):
						# mehfils
						lid = None
						parent_obj_id = retrieve_group_uuid(parent_obj_id)# needed for return_to_content() when we're dealing with mehfils
					return return_to_content(request=request,origin=origin,obj_id=parent_obj_id,link_id=lid, target_uname=None)
				else:
					raise Http404("Erroneous decision variable in direct repsonse")
	else:
		raise Http404("GET request is not allowed")


def retrieve_direct_responses(request):
	"""
	Renders all direct reponses received by the user as a 'direct repsonse list'
	"""
	page_num = request.GET.get('page', '1')
	start_index, end_index = get_indices(page_num, ITEMS_PER_PAGE)
	own_id = request.user.id

	response_data, list_total_size, obj_hash_name_list = retrieve_direct_response_list(own_id, start_idx=start_index, end_idx=end_index, \
		with_feed_size=True, with_obj_list=True)
	num_pages = list_total_size/ITEMS_PER_PAGE
	max_pages = num_pages if list_total_size % ITEMS_PER_PAGE == 0 else (num_pages+1)
	
	##########################
	# notifications
	dir_reps_skipped = request.session.pop("page_skipped"+str(own_id),None)
	uname_rep_sent_to = request.session.pop("dir_rep_sent"+str(own_id),None)
	obj_type_rep_sent_to = request.session.pop("dir_rep_tgt_obj_type"+str(own_id),None)
	parent_obj_id_rep_sent_to = request.session.pop("dir_rep_tgt_obj_id"+str(own_id),None)
	uname_of_deleted_rep = None if uname_rep_sent_to else request.session.pop("dir_rep_del"+str(own_id),None)
	rep_invalid = None if uname_rep_sent_to else request.session.pop("dir_rep_invalid"+str(own_id),None)
	##########################

	context = {'form':DirectResponseForm(render_page_with_one_response=False),'uname_rep_sent_to':uname_rep_sent_to,\
	'uname_of_deleted_rep':uname_of_deleted_rep,'response_data':response_data,'obj_type_rep_sent_to':obj_type_rep_sent_to,\
	'obj_hash_name_string':'-'.join(obj_hash_name_list) if obj_hash_name_list else '', 'rep_invalid':rep_invalid, \
	'parent_obj_id_rep_sent_to':parent_obj_id_rep_sent_to, 'dir_reps_skipped':dir_reps_skipped}

	page_num = int(page_num)

	context["page"] = {'number':page_num,'has_previous':True if page_num>1 else False,'has_next':True if page_num<max_pages else False,\
	'previous_page_number':page_num-1,'next_page_number':page_num+1}
	return render(request,"direct_response/direct_response_list.html",context)


@csrf_protect
def skip_direct_responses(request):
	"""
	Skips (actually deletes) all notifications in the inbox (on the current page)
	"""
	if request.method == 'POST':
		own_id = request.user.id
		objs_on_page = request.POST.get("oop",[])
		list_of_objs = objs_on_page.split("-") if objs_on_page else []
		bulk_delete_selective_dir_reps_of_single_user(user_id=own_id,dir_rep_list=list_of_objs)
		##################################
		# the following logs direct response metrics
		direct_response_tasks.delay(action_status=True, action_type='3', num_skips=len(list_of_objs))
		##################################
		# can be used to delete ALL direct replies in inbox - not shipped
		# bulk_delete_user_direct_responses(target_user_ids=[own_id])
		##################################
		request.session["page_skipped"+str(own_id)] = '1'
	return redirect(reverse_lazy("retrieve_direct_responses"))