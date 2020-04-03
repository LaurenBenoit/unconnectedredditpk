# coding=utf-8
import time, requests
import ujson as json
from django.http import Http404
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import cache_control
from django.views.decorators.debug import sensitive_post_parameters
from forms import strip_zero_width_characters
from redis4 import log_superhuman_survey_answers, has_already_answered_superhuman_survey, retrieve_uname, retrieve_survey_records
from redis7 import in_defenders, get_num_topics
from redis3 import get_world_age, exact_date
from redis2 import get_all_follower_count
from utilities import convert_to_epoch
from redis6 import get_num_groups
from redis5 import get_num_grps
from models import Link, Photo

# def get_latest_post(user_id, post_type,only_time):
# 	"""
# 	Useful in enriching survey results with data about user's public posting habits

# 	post_type can either be 'tx' or 'img'
# 	"""
# 	if only_time:
# 		if post_type == 'tx':
# 			try:
# 				return Link.objects.only('submitted_on').filter(submitter_id=user_id).latest('submitted_on').submitted_on
# 			except Link.DoesNotExist:
# 				return None
# 		elif post_type == 'img':
# 			try:
# 				return Photo.objects.only('upload_time').filter(owner_id=user_id).latest('upload_time').upload_time
# 			except Photo.DoesNotExist:
# 				return None
# 		else:
# 			return None
# 	else:
# 		###### Write if needed ######
# 		if post_type == 'tx':
# 			return None
# 		elif post_type == 'img':
# 			return None
# 		else:
# 			return None

####################################


def export_survey_results(request):
	"""
	Exports all survey results into a CSV file for analysis
	"""
	own_id = request.user.id
	is_defender, is_super_defender = in_defenders(own_id, return_super_status=True)
	if is_super_defender:
		data_to_write_to_csv = retrieve_survey_records()# list of lists (where each list is a list of dictionaries)
		if data_to_write_to_csv:
			import csv
			filename = 'survey_data.csv'
			with open(filename,'wb') as f:
				wtr = csv.writer(f)
				columns = ['Submission time','Skipped survey','Joining time','via FBS','Num followers','World age','Verified','Username',\
				'Gender','Age bracket','Do you watch talent vids?','I watch comedy','I watch singing','I watch dancing','I watch physical stunts',\
				'I watch magic tricks','I watch pranks','I watch parody','I watch roasting','I watch none of these','I watch other genre(s)',\
				'Do you create talent vids?','I create comedy','I create singing','I create dancing','I create physical stunts',\
				'I create magic tricks','I create pranks','I create parody','I create roasting','I create none of these','I create other genre(s)',\
				'Frequency of video consumption','Most used app for videos','Optional talent video link']
				
				wtr.writerow(columns)
				for json_data in data_to_write_to_csv:
					data = json.loads(json_data)
					verified = 'Yes' if data['verif'] else 'No'
					#########################################
					if data['skipped'] == '0':
						# survey was taken
						gender = 'Male' if data['ans4'] == '1' else 'Female'
						age_code = data['ans5']
						if age_code == '1':
							age_bracket = '12-17'
						elif age_code == '2':
							age_bracket = '18-22'
						elif age_code == '3':
							age_bracket = '22 se zyada'
						ans1_string = 'Yes' if data['ans1'] == '1' else 'No'
						watch_none, watch_comedy, watch_singing, watch_dancing, watch_stunts, watch_magic, watch_pranks, watch_parody, \
						watch_roasting = '-','-','-','-','-','-','-','-','-'
						for ans in data['ans2']:
							if ans == '1':
								watch_none = 'Yes'
							elif ans == '2':
								watch_comedy = 'Yes'
							elif ans == '3':
								watch_singing = 'Yes'
							elif ans == '4':
								watch_dancing = 'Yes'
							elif ans == '5':
								watch_stunts = 'Yes'
							elif ans == '6':
								watch_magic = 'Yes'
							elif ans == '7':
								watch_pranks = 'Yes'
							elif ans == '8':
								watch_parody = 'Yes'
							elif ans == '9':
								watch_roasting = 'Yes'
						create_none, create_comedy, create_singing, create_dancing, create_stunts, create_magic, create_pranks, create_parody,\
						create_roasting = '-','-','-','-','-','-','-','-','-'
						for ans in data['ans3']:
							if ans == '1':
								create_none = 'Yes'
								ans3_string = 'No'
							elif ans == '2':
								create_comedy = 'Yes'
								ans3_string = 'Yes'
							elif ans == '3':
								create_singing = 'Yes'
								ans3_string = 'Yes'
							elif ans == '4':
								create_dancing = 'Yes'
								ans3_string = 'Yes'
							elif ans == '5':
								create_stunts = 'Yes'
								ans3_string = 'Yes'
							elif ans == '6':
								create_magic = 'Yes'
								ans3_string = 'Yes'
							elif ans == '7':
								create_pranks = 'Yes'
								ans3_string = 'Yes'
							elif ans == '8':
								create_parody = 'Yes'
								ans3_string = 'Yes'
							elif ans == '9':
								create_roasting = 'Yes'
								ans3_string = 'Yes'
						ans3_string = 'Yes' if data['ans3b'] else ans3_string
						freq_code = data['ans6']
						if freq_code == '1':
							freq_of_vid_consumption = 'Takreeban rozaana'
						elif freq_code == '2':
							freq_of_vid_consumption = 'Har 2-3 days baad'
						elif freq_code == '3':
							freq_of_vid_consumption = 'Har 1 week baad'
						elif freq_code == '4':
							freq_of_vid_consumption = 'Buhut kamm'
						app_code = data['ans7']
						if app_code == '1':
							app_name = 'Youtube'
						elif app_code == '2':
							app_name = 'TikTok'
						elif app_code == '3':
							app_name = 'Facebook'
						elif app_code == '4':
							app_name = 'Likee'
						elif app_code == '5':
							app_name = 'Helo'
						elif app_code == '6':
							app_name = 'Kwai'
						elif app_code == '7':
							app_name = 'VidMate'
						elif app_code == '8':
							app_name = 'Instagram'
						elif app_code == '9':
							app_name = 'I dont use any'
						vid_link = data.get('ans8','-')
						to_write = [exact_date(data['submission_time']),'No',exact_date(data['join_date']),data['on_fbs'],data['num_followers'],\
						data['world_age'],verified,data['username'].encode('utf-8'),gender,age_bracket,ans1_string,watch_comedy,watch_singing,\
						watch_dancing,watch_stunts,watch_magic,watch_pranks,watch_parody,watch_roasting,watch_none,data['ans2b'].encode('utf-8'),\
						ans3_string,create_comedy, create_singing, create_dancing, create_stunts, create_magic, create_pranks, create_parody, \
						create_roasting,create_none,data['ans3b'].encode('utf-8'),freq_of_vid_consumption,app_name,vid_link.encode('utf-8') if vid_link else '-']
					else:
						# survey was skipped
						to_write = [exact_date(data['submission_time']),'Yes',exact_date(data['join_date']),data['on_fbs'],data['num_followers'],\
						data['world_age'],verified,data['username'].encode('utf-8'),'-','-','-','-','-','-','-','-','-','-','-','-','-','-','-',\
						'-','-','-','-','-','-','-','-','-','-','-','-']
					
					wtr.writerows([to_write])
	raise Http404("Completed ;)")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@sensitive_post_parameters()
@csrf_protect
def survey(request):
	"""
	Conducting surveys to guage user feedback and product-market-fit
	"""
	if request.method == "POST":
		user_id = request.user.id
		time_now = time.time()
		finalize_submission = request.POST.get("fdec",None)#'1' means submit, '0' means skip
		skip_survey = request.POST.get("sdec",None)#'1' means skip for sure, '0' means don't skip
		ans1 = request.POST.get("q1",None)
		ans2 = request.POST.getlist('q2',[u''])
		ans2b = request.POST.get('q2b','')
		ans3 = request.POST.getlist('q3',[u''])
		ans3b = request.POST.get('q3b','')
		ans4 = request.POST.get("q4",None)
		ans5 = request.POST.get("q5",None)
		ans6 = request.POST.get("q6",None)
		ans7 = request.POST.get("q7",None)
		ans8 = request.POST.get("q8",'')
		###############
		ans2_exists = True if (ans2[0] or ans2b) else False
		ans3_exists = True if (ans3[0] or ans3b) else False
		processed_ans2 = [u'',u'',u'',u'',u'',u'',u'',u'',u'']
		processed_ans3 = [u'',u'',u'',u'',u'',u'',u'',u'',u'']
		len_ans2, len_ans3 = len(ans2), len(ans3)
		for i in range(len_ans2):
			value = ans2[i]
			if value:
				idx = int(value)-1
				if idx < 9:
					processed_ans2[idx] = value
		for i in range(len_ans3):
			value = ans3[i]
			if value:
				idx = int(value)-1
				if idx < 9:
					processed_ans3[idx] = value
		###############
		if skip_survey == '1':
			answers = {}
			answers['skipped'] = '1'
			answers['num_followers'] = get_all_follower_count(user_id)
			answers['join_date'] = convert_to_epoch(User.objects.only('date_joined').get(id=user_id).date_joined)
			answers['on_fbs'] = request.META.get('HTTP_X_IORG_FBS',False)
			answers['world_age'] = get_world_age(user_id)
			answers['username'] = retrieve_uname(user_id,decode=True)
			answers['submission_time'] = time_now
			answers['verif'] = request.mobile_verified
			answers['ans1'] = ''
			answers['ans2'] = ''
			answers['ans3'] = ''
			answers['ans4'] = ''
			answers['ans5'] = ''
			answers['ans6'] = ''
			answers['ans7'] = ''
			answers['ans8'] = ''
			log_superhuman_survey_answers(user_id=user_id, answers_dict=answers, time_now=time_now)
			return render(request,"announcement/hxu_survey.html",{'skipped':True})
		elif skip_survey == '0':
			# return person to 'home'
			return redirect('home')
		elif finalize_submission == '0':
			# display 'are you sure you want to skip survey' prompt. I.e. always give them a warning they're about to skip the survey for good
			return render(request,"announcement/hxu_survey.html",{'sure_about_skipping':True})
		elif finalize_submission == '1':
			# user has submitted their answers - validate them
			if ans1 and ans2_exists and ans3_exists and ans4 and ans5 and ans6 and ans7:
				# all questions answered - but are the answers valid?
				answers = {}
				errors = {}
				###############################
				if ans1 in ('1','2'):
					answers['ans1'] = ans1
				else:
					# invalid
					errors['ans1'] = '2nd sawal ka jawab sahi se chunein'
					ans1 = None
				###############################
				ans2_invalid = False
				for ans in ans2:
					if ans:
						if ans not in ('1','2','3','4','5','6','7','8','9'):
							ans2_invalid = True
							break
				if ans2_invalid:
					errors['ans2'] = '3rd sawal ka jawab sahi se chunein'
					ans2 = None
				else:
					answers['ans2'] = processed_ans2
					answers['ans2b'] = ans2b[:1000]# only save 1000 chars
				###############################
				ans3_invalid = False
				for ans in ans3:
					if ans:
						if ans not in ('1','2','3','4','5','6','7','8','9'):
							ans3_invalid = True
							break
				if ans3_invalid:
					errors['ans3'] = '4th sawal ka jawab sahi se chunein'
					ans3 = None
				else:
					answers['ans3'] = processed_ans3
					answers['ans3b'] = ans3b[:1000]# only save 1000 chars
				###############################
				if ans4 in ('1','2'):
					# sounds about right
					answers['ans4'] = ans4
				else:
					# invalid
					errors['ans4'] = '5th sawal ka jawab sahi se chunein'
					ans4 = None
				###############################
				if ans5 in ('1','2','3'):
					# sounds about right
					answers['ans5'] = ans5
				else:
					# invalid
					errors['ans5'] = '6th sawal ka jawab sahi se chunein'
					ans5 = None
				###############################
				if ans6 in ('1','2','3','4'):
					# sounds about right
					answers['ans6'] = ans6
				else:
					# invalid
					errors['ans6'] = '1st sawal ka jawab sahi se chunein'
					ans6 = None
				###############################
				if ans7 in ('1','2','3','4','5','6','7','8','9'):
					# sounds about right
					answers['ans7'] = ans7
				else:
					# invalid
					errors['ans7'] = '7th sawal ka jawab sahi se chunein'
					ans7 = None
				###############################
				if ans8:
					ans8 = ans8.strip()
					ans8 = strip_zero_width_characters(ans8)
					if ans8:
						# only save 1000 chars
						answers['ans8'] = ans8[:600]
				if errors:
					# also repopulate answers that were given
					return render(request,"announcement/hxu_survey.html",{'invalid_answers':True,'errors':errors,\
						'ans1':ans1,'ans2':processed_ans2,'ans2b':ans2b,'ans3':processed_ans3,'ans3b':ans3b,'ans4':ans4,\
						'ans5':ans5,'ans6':ans6,'ans7':ans7,'ans8':ans8})
				else:
					# no errors - log the answers!
					time_now = time.time()
					answers['skipped'] = '0'
					answers['num_followers'] = get_all_follower_count(user_id)
					answers['join_date'] = convert_to_epoch(User.objects.only('date_joined').get(id=user_id).date_joined)
					answers['on_fbs'] = request.META.get('HTTP_X_IORG_FBS',False)
					answers['world_age'] = get_world_age(user_id)
					answers['username'] = retrieve_uname(user_id,decode=True)
					answers['submission_time'] = time_now
					answers['verif'] = request.mobile_verified
					log_superhuman_survey_answers(user_id=user_id, answers_dict=answers, time_now=time_now)
					return render(request,"announcement/hxu_survey.html",{'submitted':True})
			else:
				# must answer all questions!
				missing_ques = ''
				if not ans6:
					missing_ques += ' 1 '
				if not ans1:
					missing_ques += ' 2 '
				if not ans2_exists:
					missing_ques += ' 3 '
				if not ans3_exists:
					missing_ques += ' 4 '
				if not ans4:
					missing_ques += ' 5 '
				if not ans5:
					missing_ques += ' 6 '
				if not ans7:
					missing_ques += ' 7 '
				# also repopulate answers that were given
				return render(request,"announcement/hxu_survey.html",{'must_answer_all':True,'missing_ques':missing_ques,\
					'ans1':ans1,'ans2':processed_ans2,'ans2b':ans2b,'ans3':processed_ans3,'ans3b':ans3b,'ans4':ans4,'ans5':ans5,\
					'ans6':ans6,'ans7':ans7,'ans8':ans8})
		else:
			# response of "finalize_submission" of "skip_survey" does not make sense, restart!
			return render(request,"announcement/hxu_survey.html",{'error_final_dec':True,'ans1':ans1,'ans2':processed_ans2,\
				'ans2b':ans2b,'ans3':processed_ans3,'ans3b':ans3b,'ans4':ans4,'ans5':ans5,'ans6':ans6,'ans7':ans7,'ans8':ans8})
	else:
		already_answered, was_skipped = has_already_answered_superhuman_survey(request.user.id)
		if already_answered:
			# render a 'thank you, you've already answered' screen
			return render(request,"announcement/hxu_survey.html",{'already_answered':already_answered, 'was_skipped':was_skipped})
		else:
			# render basic survey
			return render(request,"announcement/hxu_survey.html")


# @cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
# @sensitive_post_parameters()
# @csrf_protect
# def survey(request):
# 	"""
# 	Conducting surveys to guage user feedback and product-market-fit
# 	"""
# 	if request.method == "POST":
# 		user_id = request.user.id
# 		time_now = time.time()
# 		finalize_submission = request.POST.get("fdec",None)
# 		skip_survey = request.POST.get("sdec",None)
# 		ans9 = request.POST.get("q1",None)
# 		ans10 = request.POST.get("q2",None)
# 		ans11 = request.POST.get("q3",None)
# 		ans12 = request.POST.get("q4",'')
# 		if skip_survey == '1':
# 			answers = {}
# 			answers['2nd_submission'] = '1'
# 			answers['2nd_sub_skipped'] = '1'
# 			answers['num_topics'] = get_num_topics(user_id)
# 			fan_count = get_fan_counts_in_bulk([str(user_id)])
# 			answers['num_fans'] = fan_count[str(user_id)]
# 			answers['ans9'] = ''
# 			answers['ans10'] = ''
# 			answers['ans11'] = ''
# 			answers['ans12'] = ''
# 			log_superhuman_survey_answers(user_id=user_id, answers_dict=answers, time_now=time_now)
# 			return render(request,"announcement/superhuman2.html",{'skipped':True})
# 		elif skip_survey == '0':
# 			# return person to 'for_me'
# 			return redirect('for_me')
# 		elif finalize_submission == '0':
# 			# display 'are you sure you want to skip survey' prompt. I.e. always give them a warning they're about to skip the survey for good
# 			return render(request,"announcement/superhuman2.html",{'sure_about_skipping':True})
# 		elif finalize_submission == '1':
# 			# user has submitted their answers - validate them
# 			if ans9 and ans10 and ans11 and ans12:
# 				# all questions answered - but are the answers valid?
# 				answers = {}
# 				errors = {}
# 				###############################
# 				ans9 = ans9.strip()
# 				ans9 = strip_zero_width_characters(ans9)
# 				if ans9:
# 					# only save 100 chars
# 					answers['ans9'] = ans9[:100]
# 				else:
# 					# invalid
# 					errors['ans9'] = '1st sawal ke jawab mein sirf spaces nahi daalein'
# 					ans9 = ''
# 				###############################
# 				if ans10 in ('1','2','3','4','5','6','7','8','9','10','11'):
# 					# sounds about right
# 					answers['ans10'] = ans10
# 				else:
# 					# invalid
# 					errors['ans10'] = '2nd sawal ka jawab sahi se chunein'
# 					ans10 = None
# 				###############################
# 				if ans11 in ('1','2','3'):
# 					# sounds about right
# 					answers['ans11'] = ans11
# 				else:
# 					# invalid
# 					errors['ans11'] = '3rd sawal ka jawab sahi se chunein'
# 					ans11 = None
# 				###############################
# 				if ans12 in ('1','2','3','4'):
# 					# sounds about right
# 					answers['ans12'] = ans12
# 				else:
# 					# invalid
# 					errors['ans12'] = '4th sawal ka jawab sahi se chunein'
# 					ans12 = None
# 				###############################
# 				if errors:
# 					# also repopulate answers that were given
# 					return render(request,"announcement/superhuman2.html",{'invalid_answers':True,'errors':errors,\
# 						'ans1':ans9,'ans2':ans10,'ans3':ans11,'ans4':ans12})
# 				else:
# 					# no errors - log the answers!
# 					time_now = time.time()
# 					answers['2nd_submission'] = '1'
# 					answers['2nd_sub_skipped'] = '0'
# 					answers['num_topics'] = get_num_topics(user_id)
# 					fan_count = get_fan_counts_in_bulk([str(user_id)])
# 					answers['num_fans'] = fan_count[str(user_id)]
# 					log_superhuman_survey_answers(user_id=user_id, answers_dict=answers, time_now=time_now)
# 					return render(request,"announcement/superhuman2.html",{'submitted':True})
# 			else:
# 				# must answer all questions!
# 				missing_ques = ''
# 				if not ans9:
# 					missing_ques += ' 1 '
# 				if not ans10:
# 					missing_ques += ' 2 '
# 				if not ans11:
# 					missing_ques += ' 3 '
# 				if not ans12:
# 					missing_ques += ' 4 '
# 				# also repopulate answers that were given
# 				return render(request,"announcement/superhuman2.html",{'must_answer_all':True,'missing_ques':missing_ques,\
# 					'ans1':ans9,'ans2':ans10,'ans3':ans11,'ans4':ans12})
# 		else:
# 			# response of "finalize_submission" of "skip_survey" does not make sense, restart!
# 			return render(request,"announcement/superhuman2.html",{'error_final_dec':True,'ans1':ans9,'ans2':ans10,'ans3':ans11,\
# 				'ans4':ans12})
# 	else:
# 		already_answered, was_skipped = has_already_answered_superhuman_survey(request.user.id)
# 		if already_answered:
# 			# render a 'thank you, you've already answered' screen
# 			return render(request,"announcement/superhuman2.html",{'already_answered':already_answered, 'was_skipped':was_skipped})
# 		else:
# 			# render basic survey
# 			return render(request,"announcement/superhuman2.html")


# @cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
# @sensitive_post_parameters()
# @csrf_protect
# def survey(request):
# 	"""
# 	Conducting surveys to guage user feedback and product-market-fit
# 	"""
# 	if request.method == "POST":
# 		user_id = request.user.id
# 		time_now = time.time()
# 		finalize_submission = request.POST.get("fdec",None)
# 		skip_survey = request.POST.get("sdec",None)
# 		ans1 = request.POST.get("q1",None)
# 		ans2 = request.POST.get("q2",'')
# 		ans3 = request.POST.get("q3",'')
# 		ans4 = request.POST.get("q4",'')
# 		ans5 = request.POST.get("q5",None)
# 		ans6 = request.POST.get("q6",None)
# 		ans7 = request.POST.get("q7",None)
# 		ans8 = request.POST.get("q8",'')
# 		if skip_survey == '1':
# 			answers = {}
# 			answers['user_id'] = user_id
# 			answers['skipped'] = '1'
# 			if request.is_feature_phone:
# 				answers['device'] = '1'
# 			elif request.is_phone:
# 				answers['device'] = '2'
# 			elif request.is_tablet:
# 				answers['device'] = '4'
# 			elif request.is_mobile:
# 				answers['device'] = '5'
# 			else:
# 				answers['device'] = '3'
# 			answers['num_pub_grps'], answers['num_prv_grps'] = get_num_groups(user_id)
# 			answers['join_date'] = convert_to_epoch(User.objects.only('date_joined').get(id=user_id).date_joined)
# 			answers['on_fbs'] = request.META.get('HTTP_X_IORG_FBS',False)
# 			answers['world_age'] = get_world_age(user_id)
# 			answers['username'] = retrieve_uname(user_id,decode=True)
# 			answers['num_1on1s'] = get_num_grps(user_id)
# 			answers['submission_time'] = time_now
# 			answers['ans1'] = ''
# 			answers['ans2'] = ''
# 			answers['ans3'] = ''
# 			answers['ans4'] = ''
# 			answers['ans5'] = ''
# 			answers['ans6'] = ''
# 			answers['ans7'] = ''
# 			answers['ans8'] = ''
# 			answers['verif'] = request.mobile_verified
# 			log_superhuman_survey_answers(user_id=user_id, answers_dict=answers, time_now=time_now)
# 			return render(request,"announcement/superhuman.html",{'skipped':True})
# 		elif skip_survey == '0':
# 			# return person to 'for_me'
# 			return redirect('for_me')
# 		elif finalize_submission == '0':
# 			# display 'are you sure you want to skip survey' prompt. I.e. always give them a warning they're about to skip the survey for good
# 			return render(request,"announcement/superhuman.html",{'sure_about_skipping':True})
# 		elif finalize_submission == '1':
# 			# user has submitted their answers - validate them
# 			if ans1 and ans2 and ans3 and ans4 and ans5 and ans6 and ans7 and ans8:
# 				# all questions answered - but are the answers valid?
# 				answers = {}
# 				errors = {}
# 				if ans1 in ('1','2','3','4'):
# 					# sounds about right
# 					answers['ans1'] = ans1
# 				else:
# 					# invalid
# 					errors['ans1'] = '1st sawal ka jawab sahi se chunein'
# 					ans1 = None
# 				###############################
# 				ans2 = ans2.strip()
# 				ans2 = strip_zero_width_characters(ans2)
# 				if ans2:
# 					# only save 1000 chars
# 					answers['ans2'] = ans2[:1000]
# 				else:
# 					# invalid
# 					errors['ans2'] = '2nd sawal ke jawab mein sirf spaces nahi daalein'
# 					ans2 = ''
# 				###############################
# 				ans3 = ans3.strip()
# 				ans3 = strip_zero_width_characters(ans3)
# 				if ans3:
# 					# only save 1000 chars
# 					answers['ans3'] = ans3[:1000]
# 				else:
# 					# invalid
# 					errors['ans3'] = '3rd sawal ke jawab mein sirf spaces nahi daalein'
# 					ans3 = ''
# 				###############################
# 				ans4 = ans4.strip()
# 				ans4 = strip_zero_width_characters(ans4)
# 				if ans4:
# 					# only save 1000 chars
# 					answers['ans4'] = ans4[:1000]
# 				else:
# 					# invalid
# 					errors['ans4'] = '4th sawal ke jawab mein sirf spaces nahi daalein'
# 					ans4 = ''
# 				###############################	
# 				if ans5 in ('1','2'):
# 					# sounds about right
# 					answers['ans5'] = ans5
# 				else:
# 					# invalid
# 					errors['ans5'] = '5th sawal ke jawab mein sirf spaces nahi daalein'
# 					ans5 = None
# 				###############################
# 				if ans6 in ('1','2','3'):
# 					# sounds about right
# 					answers['ans6'] = ans6
# 				else:
# 					# invalid
# 					errors['ans6'] = '6th sawal ka jawab sahi se chunein'
# 					ans6 = None
# 				###############################
# 				if ans7 in ('1','2','3'):
# 					# sounds about right
# 					answers['ans7'] = ans7
# 				else:
# 					# invalid
# 					errors['ans7'] = '7th sawal ka jawab sahi se chunein'
# 					ans7 = None
# 				###############################
# 				ans8 = ans8.strip()
# 				ans8 = strip_zero_width_characters(ans8)
# 				if ans8:
# 					# only save 1000 chars
# 					answers['ans8'] = ans8[:1000]
# 				else:
# 					# invalid
# 					errors['ans8'] = '8th sawal ke jawab mein sirf spaces nahi daalein'
# 					ans8 = ''
# 				###############################
# 				if errors:
# 					# also repopulate answers that were given
# 					return render(request,"announcement/superhuman.html",{'invalid_answers':True,'errors':errors,\
# 						'ans1':ans1,'ans2':ans2,'ans3':ans3,'ans4':ans4,'ans5':ans5,'ans6':ans6,'ans7':ans7,'ans8':ans8})
# 				else:
# 					time_now = time.time()
# 					answers['user_id'] = user_id
# 					if request.is_feature_phone:
# 						answers['device'] = '1'
# 					elif request.is_phone:
# 						answers['device'] = '2'
# 					elif request.is_tablet:
# 						answers['device'] = '4'
# 					elif request.is_mobile:
# 						answers['device'] = '5'
# 					else:
# 						answers['device'] = '3'
# 					answers['skipped'] = '0'
# 					answers['num_pub_grps'], answers['num_prv_grps'] = get_num_groups(user_id)
# 					answers['join_date'] = convert_to_epoch(User.objects.only('date_joined').get(id=user_id).date_joined)
# 					answers['on_fbs'] = request.META.get('HTTP_X_IORG_FBS',False)
# 					answers['world_age'] = get_world_age(user_id)
# 					answers['username'] = retrieve_uname(user_id,decode=True)
# 					answers['num_1on1s'] = get_num_grps(user_id)
# 					answers['submission_time'] = time_now
# 					answers['verif'] = request.mobile_verified
# 					log_superhuman_survey_answers(user_id=user_id, answers_dict=answers, time_now=time_now)
# 					return render(request,"announcement/superhuman.html",{'submitted':True})
# 			else:
# 				# must answer all questions!
# 				missing_ques = ''
# 				if not ans1:
# 					missing_ques += ' 1 '
# 				if not ans2:
# 					missing_ques += ' 2 '
# 				if not ans3:
# 					missing_ques += ' 3 '
# 				if not ans4:
# 					missing_ques += ' 4 '
# 				if not ans5:
# 					missing_ques += ' 5 '
# 				if not ans6:
# 					missing_ques += ' 6 '
# 				if not ans7:
# 					missing_ques += ' 7 '
# 				if not ans8:
# 					missing_ques += ' 8 '
# 				# also repopulate answers that were given
# 				return render(request,"announcement/superhuman.html",{'must_answer_all':True,'missing_ques':missing_ques,\
# 					'ans1':ans1,'ans2':ans2,'ans3':ans3,'ans4':ans4,'ans5':ans5,'ans6':ans6,'ans7':ans7, 'ans8':ans8})
# 		else:
# 			# response of "finalize_submission" of "skip_survey" does not make sense, restart!
# 			return render(request,"announcement/superhuman.html",{'error_final_dec':True,'ans1':ans1,'ans2':ans2,'ans3':ans3,\
# 				'ans4':ans4,'ans5':ans5,'ans6':ans6,'ans7':ans7, 'ans8':ans8})
# 	else:
# 		already_answered, was_skipped = has_already_answered_superhuman_survey(request.user.id)
# 		if already_answered:
# 			# render a 'thank you, you've already answered' screen
# 			return render(request,"announcement/superhuman.html",{'already_answered':already_answered, 'was_skipped':was_skipped})
# 		else:
# 			# render basic survey
# 			log_survey_referrer(request.user.id, request.META.get('HTTP_REFERER',None))
# 			return render(request,"announcement/superhuman.html")

##############################################################################################
##############################################################################################
##############################################################################################

def corona_virus_management(request, lang=None):
	"""
	Renders an info page about COVID-19
	"""
	if lang=='ur':
		return render(request,"announcement/corona2_ur.html",{})
	else:
		return render(request,"announcement/corona2.html",{})


def corona_virus(request, lang=None):
	"""
	Renders an info page about COVID-19
	"""
	if lang=='ur':
		return render(request,"announcement/corona_ur.html",{})
	else:
		return render(request,"announcement/corona.html",{})


def coming_soon(request):
	"""
	Renders the detail of an announcement
	"""
	return render(request,"announcement/coming_soon_detail.html",{})


def maintainance_notice(request):
	"""
	Renders the detail of an announcement
	"""
	return render(request,"announcement/maintainance_detail.html",{})


@csrf_protect
def benefits_of_data_mode(request):
	"""
	Renders the detail of an announcement
	"""
	if request.method == "POST":
		r = requests.get(url = "https://damadam.pk", params = {'click_out':True}) 
		return redirect(r.url)
	else:
		return render(request,"announcement/benefits_of_data_mode.html",{})