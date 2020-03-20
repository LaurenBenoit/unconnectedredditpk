import time, requests, uuid
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import cache_control
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse_lazy, reverse
from account_kit_config_manager import account_kit_handshake
from verification_forms import AddVerifiedUserForm, rate_limit_artificial_verification, MobileVerificationForm, PinVerifyForm, UnverifyUserIDForm
from redis3 import save_consumer_number, is_mobile_verified, is_sms_sending_rate_limited, save_user_account_kit_server_secret,\
retrieve_user_account_kit_secret, someone_elses_number, unverify_user_id
#twiliolog_pin_sms_sent, twiliolog_user_verified,twiliolog_reverification_pin_sms_sent, twiliolog_user_reverified, log_fbs_please_wait,\
#log_fbs_user_verification,log_ak_entered, log_ak_user_verification_outcome
from redis5 import can_change_number, get_personal_group_target_id, get_personal_group_anon_state, set_personal_group_mobile_num_cooloff
from tasks import send_user_pin, save_consumer_credentials, increase_user_points, log_user_activity
from score import NUMBER_VERIFICATION_BONUS, FBS_VERIFICATION_WAIT_TIME, SEGMENT_STARTING_USER_ID
from redis3 import save_consumer_details, someone_elses_data, log_firebase_user_verification_outcome,log_firebase_entered
from redis2 import change_verification_status
from utilities import convert_to_epoch
from redis4 import retrieve_uname
from redis8 import retrieve_var
from models import UserProfile
import ujson as json


############################## Firebase Verification  #################################

@csrf_protect
def firebase_verification(request,*args,**kwargs):
	"""
	Handles firebase-led verification

	JS is required for this to work, otherwise we redirect the user to "home"
	"""
	is_ajax = request.is_ajax()
	if is_ajax:
		if request.method == 'POST':
			user_id = request.user.id
			uid = request.POST.get('uid')# firebase ID
			provider = request.POST.get('Provider')# Google, FB or mobile device
			puid = request.POST.get('ProviderUID')# Any ID specific to the provider above (e.g. FB ID)
			name = request.POST.get('Name')# Name (if available)
			email = request.POST.get('email')# Email (if available)
			purl = request.POST.get('PhotoURL')# Image (if available)
			num = request.POST.get('phoneNumber')# Phone number (if available)

			preexisting_verification = someone_elses_data(firebase_id=uid,user_id=user_id, mob_num=num)
			if preexisting_verification in ('0','1'):
				request.session["firebase_verification_failed"] = '1'
				request.session["firebase_verification_failure_reason"] = preexisting_verification#number already used up
				request.session.modified = True
				log_firebase_user_verification_outcome('data_already_used')
				return HttpResponse(json.dumps({'success':False,'message':reverse("firebase_verification_failed",kwargs={})}),content_type='application/json',)

			else:
				user_verification_data = {'uid':uid,'provider':provider,'puid':puid,'name':name,'email':email,'purl':purl,'num':num,'verif_time':time.time()}
				save_consumer_details(user_verification_data,user_id)
				change_verification_status(user_id,'verified')# updating 'fan_verification_status' in postgresql table UserFan
				request.session["firebase_verification_succeeded"] = '1'
				log_firebase_user_verification_outcome('verified')
				return HttpResponse(json.dumps({'success':True,'message':reverse("firebase_verification_successful",kwargs={})}),content_type='application/json')
		else:
			return redirect('verify_user_mobile_unpaid')
	##############################
	else:
		return redirect('home')


def firebase_verification_result(request):
	"""
	Shows failure or success state to user after processing their firebase credentials
	"""
	verification_successful = request.session.pop("firebase_verification_succeeded",'')
	if verification_successful:
		request.session.pop("newbie_flag",None)# verified users aren't newbies by definition
		request.session.pop("newbie_lang",None)# verified users aren't newbies by definition
		user_id = request.user.id
		return render(request,"verification/reward_earned.html",{'user_var':retrieve_var(user_id=user_id)})
	else:
		verification_failed = request.session.pop("firebase_verification_failed",'')
		if verification_failed:
			reason = request.session.pop('firebase_verification_failure_reason','')
			return render(request,"verification/verification_failed.html",{'reason':reason})
		else:
			raise Http404("This is an invalid result")


############################## Number verification administration  #################################


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def verify_user_artificially(request):
	"""
	This renders a template where user_ids can be artificially verified (mobile)

	This also processes the verification step
	"""
	if retrieve_uname(request.user.id,decode=True) in ['pathan-e-khan','Damadam-Feedback','mhb11','ZippoLighter']:
		if request.method == "POST":
			processed_form = AddVerifiedUserForm(request.POST)
			if processed_form.is_valid():
				success = rate_limit_artificial_verification()
				if success:
					from django.db.models import F
					valid_user_id = processed_form.cleaned_data.get("user_id")
					random_string = str(uuid.uuid4())
					# account_kid_id = 'artificial_verification'		
					# mobile_data = {'national_number':random_string,'number':random_string,'country_prefix':'92','verif_time',time.time()}
					user_verification_data = {'uid':random_string,'provider':'artificial','puid':random_string,'name':'artificial','email':'artificial','purl':'artificial','verif_time':time.time()}
					# with_points = request.POST.get("wth_pts",None)
					save_consumer_details(user_verification_data,valid_user_id)
					# save_consumer_number(account_kid_id,mobile_data,valid_user_id)
					change_verification_status(valid_user_id,'verified')
					# if with_points == '1':
					# 	UserProfile.objects.filter(user_id=valid_user_id).update(score=F('score')+500)
					return render(request,"verification/artificial_verification.html",{'form':AddVerifiedUserForm(),\
						'verified_id':valid_user_id})
				else:
					return redirect('missing_page')
			else:
				return render(request,"verification/artificial_verification.html",{'form':processed_form})
		else:
			# it's a GET request
			return render(request,"verification/artificial_verification.html",{'form':AddVerifiedUserForm()})
	else:
		return redirect('missing_page')


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def unverify_user(request):
	"""
	This renders a form field which can take user ids and unverify them
	"""
	if retrieve_uname(request.user.id,decode=True) in ['pathan-e-khan','Damadam-Feedback','mhb11','ZippoLighter']:
		if request.method == "POST":
			processed_form = UnverifyUserIDForm(request.POST)
			if processed_form.is_valid():
				target_id = processed_form.cleaned_data['user_id']
				numbers_released = unverify_user_id(target_id)
				change_verification_status(target_id,'unverified')
				return render(request,"verification/unverify_user.html",{'form':UnverifyUserIDForm(),\
					'unverified_id':target_id,'numbers_released':numbers_released})
			else:
				return render(request,"verification/unverify_user.html",{'form':processed_form})
		else:
			# it's a GET request
			return render(request,"verification/unverify_user.html",{'form':UnverifyUserIDForm()})
	else:
		raise Http404("This does not work for typical users")


############################## Account Kit enabled verification #################################


def get_requirements(request, secret, secret_omitted=False):
	"""
	Ensures account kit handshake happened correctly
	"""
	status = request.GET.get('status', None)
	auth_code = request.GET.get('code', None) #authorization code which our server may exchange for a user access token.
	returned_state = request.GET.get('state', None) #to verify that FB's servers returned with the response
	return account_kit_handshake(secret=secret, state=returned_state, status=status, auth_code=auth_code, secret_omitted=secret_omitted)



# @cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
# @csrf_protect
# def account_kit_verification_commencement(request):
# 	"""
# 	Passes required data to FB's Account Kit
# 	"""
# 	if request.method == "POST":
# 		user_id = request.user.id
# 		form = MobileVerificationForm(request.POST,user_id=user_id,allow_reverification=False)
# 		if form.is_valid():
# 			phonenumber = form.cleaned_data.get("phonenumber")
# 			target_number = '+92'+phonenumber[-10:]
# 			# send GET request to Account Kit url
# 			user_account_kit_server_secret = str(uuid.uuid4())# save locally
# 			save_user_account_kit_server_secret(user_id, user_account_kit_server_secret)
# 			URL = "https://www.accountkit.com/v1.0/basic/dialog/sms_login/"
# 			PARAMS = {'counter_code':'PK','app_id':'1758220174446684','state':user_account_kit_server_secret,\
# 			#'redirect':'http://127.0.0.1:8000/verification/mobile/via-account-kit/process-verification/',\
# 			'redirect':'https://damadam.pk/verification/mobile/via-account-kit/process-verification/',\
# 			'phone_number':phonenumber,'fbAppEventsEnabled':'true','debug':'false'}
# 			log_ak_entered()
# 			r = requests.get(url = URL, params = PARAMS) 
# 			return redirect(r.url)
# 		else:
# 			return render(request,'verification/user_mobile_verification.html',{'form':form})
# 	else:
# 		raise Http404("This does not work with a GET request")


# def account_kit_verification_processing(request):
# 	"""
# 	UNUSED: Processes data returned from account kit when a user goes through the profile verification flow

# 	Acts as an endpoint for account kit when it return user credentials
# 	"""
# 	# did server token match 
# 	# is the user mobile number still valid (i.e. has not been used up already, is a Pakistani number, etc)
# 	# are the user credentials complete
# 	if request.mobile_verified:
# 		request.session["account_kit_verification_failed"] = '1'
# 		log_ak_user_verification_outcome("id_already_verified")	
# 		request.session["account_kit_verification_failure_reason"] = '0'#user is already verified
# 		request.session.modified = True
# 		return redirect("account_kit_verification_failed")
# 	else:
# 		user_id = request.user.id
# 		original_secret = retrieve_user_account_kit_secret(identifier=str(user_id))
# 		if original_secret:
# 			AK_ID, MN_data, err = get_requirements(request=request,secret=original_secret)
# 			if AK_ID and MN_data:
# 				if someone_elses_number(national_number=MN_data['national_number'], user_id=user_id):
# 					request.session["account_kit_verification_failed"] = '1'
# 					log_ak_user_verification_outcome("number_already_used")
# 					request.session["account_kit_verification_failure_reason"] = '1'#number already used up done
# 					request.session.modified = True
# 					return redirect("account_kit_verification_failed")
# 				else:
# 					# verify the user
# 					save_consumer_credentials.delay(AK_ID, MN_data, user_id)
# 					change_verification_status(user_id,'verified')
# 					increase_user_points.delay(user_id=user_id, increment=NUMBER_VERIFICATION_BONUS)
# 					log_ak_user_verification_outcome("verified")
# 					################### Retention activity logging ###################
# 					if user_id > SEGMENT_STARTING_USER_ID:
# 						time_now = time.time()
# 						activity_dict = {'m':'GET','act':'Z','t':time_now}# defines what activity just took place
# 						log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
# 					##################################################################
# 					request.session["account_kit_verification_succeeded"] = '1'
# 					request.session.modified = True
# 					return redirect("account_kit_verification_successful")
# 			elif AK_ID == 'generic' or AK_ID == 'used' or AK_ID == 'expired' or AK_ID == 'invalid':
# 				# return render(request,"unverified_number.html",{'referrer':'home','reason':AK_ID,'from_ecomm':False})
# 				request.session["account_kit_verification_failed"] = '1'
# 				request.session["account_kit_verification_failure_reason"] = '2'#could not be verified
# 				request.session.modified = True
# 				return redirect("account_kit_verification_failed")
# 			elif err['status'] == "NOT_AUTHENTICATED":
# 				# return render(request,"dont_worry_just_authenticate.html",{'csrf':original_secret,'referrer':'home','type':'user',\
# 				# 	'from_ecomm':False})
# 				request.session["account_kit_verification_failed"] = '1'
# 				log_ak_user_verification_outcome("pressed_cross")
# 				request.session["account_kit_verification_failure_reason"] = '3'#encourage user to go back and verify 
# 				request.session.modified = True
# 				#pressed cross
# 				return redirect("account_kit_verification_failed")
# 			elif err['status'] == "PARTIALLY_AUTHENTICATED":
# 				# return render(request,"try_again.html",{'type':'user','from_ecomm':False})
# 				request.session["account_kit_verification_failed"] = '1'
# 				request.session["account_kit_verification_failure_reason"] = '4'#could not be verified 
# 				log_ak_user_verification_outcome("verification_failed_reason4")
# 				request.session.modified = True
# 				return redirect("account_kit_verification_failed")
# 			else:
# 				# return render(request,"unverified_number.html",{'referrer':'home','from_ecomm':False})
# 				request.session["account_kit_verification_failed"] = '1'
# 				log_ak_user_verification_outcome("verification_failed_reason5")
# 				request.session["account_kit_verification_failure_reason"] = '5'#could not be verified
# 				request.session.modified = True
# 				return redirect("account_kit_verification_failed")
# 		else:
# 			# return render(request,"try_again.html",{'type':'user','from_ecomm':False})
# 			request.session["account_kit_verification_failed"] = '1'
# 			log_ak_user_verification_outcome("sms_expired")
# 			request.session["account_kit_verification_failure_reason"] = '6'#user too late or secret never generated (simply loading URL)
# 			request.session.modified = True
# 			return redirect("account_kit_verification_failed")


# def account_kit_verification_result(request):
# 	"""
# 	Shows failure or success state to user after processing their account kit credentials
# 	"""
# 	verification_successful = request.session.pop("account_kit_verification_succeeded",'')
# 	if verification_successful:
# 		request.session.pop("newbie_flag",None)# verified users aren't newbies by definition
# 		request.session.pop("newbie_lang",None)# verified users aren't newbies by definition
# 		user_id = request.user.id
# 		return render(request,"verification/reward_earned.html",{'user_var':retrieve_var(user_id=user_id)})
# 	else:
# 		verification_failed = request.session.pop("account_kit_verification_failed",'')
# 		if verification_failed:
# 			reason = request.session.pop('account_kit_verification_failure_reason','')
# 			return render(request,"verification/verification_failed.html",{'reason':reason})
# 		else:
# 			raise Http404("This is an invalid result")


############################## User number verification #################################


def number_verification_help(request):
	"""
	Renders help page showing the advantages of verification
	"""
	return render(request,"verification/num_verification_help.html",{})


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def verify_user_mobile_unpaid(request):
	"""
	This renders a template where user selects verification method (FB, Goog, Mobile)

	"""
	if is_mobile_verified(request.user.id): 
		# not allowed to proceed
		log_firebase_user_verification_outcome('id_already_verified_firebase')
		return redirect("home")
	else:
		if request.META.get('HTTP_X_IORG_FBS',False):
			template_name = 'verification/user_mobile_verification_fbs.html'
			action = 'Z.f.u'
			log_firebase_entered(not_supported=True)
		elif request.is_opera_mini:
			template_name = 'verification/user_mobile_verification_fbs.html'
			action = 'Z.o.u'
			log_firebase_entered(not_supported=True)
		else:
			template_name = 'verification/user_mobile_verification.html'
			action = 'Z.u'
			log_firebase_entered()
		################### Retention activity logging ###################
		user_id = request.user.id
		if user_id > SEGMENT_STARTING_USER_ID:
			time_now = time.time()
			activity_dict = {'m':'GET','act':action,'t':time_now}# defines what activity just took place
			log_user_activity.delay(user_id=user_id, activity_dict=activity_dict, time_now=time_now)
		##################################################################
		return render(request,template_name,{'form':MobileVerificationForm()})	


def unable_to_verify_on_fbs(request):	
		"""	
		Renders the verfication template alongwith the error that user can't verify on FBS (or via opera mini)
		"""	
		return render(request,'verification/user_mobile_verification_fbs.html',{'is_fbs':request.META.get('HTTP_X_IORG_FBS',False),\
			'is_opera':request.GET.get('is_opera',None)})


# @cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
# @csrf_protect
# def verify_user_mobile_paid(request):
# 	"""
# 	This renders a template where user puts her number that she wants verified

# 	"""
# 	on_fbs = request.META.get('HTTP_X_IORG_FBS',False)# Use when using paid verification process
# 	user_id = request.user.id
# 	if on_fbs:
# 		joining_epoch_time = convert_to_epoch(request.user.date_joined)
# 		if joining_epoch_time + FBS_VERIFICATION_WAIT_TIME - time.time() > 0:
# 			# rate limited from verifying currently, inform accordingly
# 			return redirect("wait_before_verifying")
# 	if is_mobile_verified(user_id): 
# 		if can_change_number(user_id) and get_personal_group_target_id(user_id):
# 			# allow this user to proceed, even though (s)he is already verified
# 			if request.method == "POST":
# 				form = MobileVerificationForm(request.POST,user_id=user_id,allow_reverification=True)
# 				ttl = is_sms_sending_rate_limited(user_id)
# 				if ttl:
# 					return render(request,"verification/enter_pin_code.html",{'form':PinVerifyForm(),'ttl':ttl,'reentry_instr':True})
# 				elif form.is_valid():
				
# 					phonenumber = form.cleaned_data.get("phonenumber")
# 					target_number = '+92'+phonenumber[-10:]
# 					# generate and send a pin code to the given mobile number
# 					send_user_pin.delay(user_id, target_number)
# 					twiliolog_reverification_pin_sms_sent()
# 					request.session['phonenumber'+str(user_id)] = phonenumber
# 					request.session['for_personal_group'] = '1'
# 					request.session.modified = True
# 					return render(request,"verification/enter_pin_code.html",{'form':PinVerifyForm()})
# 				else:
# 					return render(request,'verification/user_mobile_verification.html',{'form':form})
# 			else:
# 				# it's a GET request
# 				ttl = is_sms_sending_rate_limited(user_id)
# 				if ttl:
# 					return render(request,"verification/enter_pin_code.html",{'form':PinVerifyForm(),'ttl':ttl,'reentry_instr':True})
# 				else:
# 					return render(request,'verification/user_mobile_verification.html',{'form':MobileVerificationForm(),\
# 						'pin_expired':request.session.pop("start_verification_again"+str(user_id),None),'for_personal_group':True})
# 		else:
# 			# not allowed to proceed
# 			return redirect("missing_page")
# 	else:
# 		# is allowed to proceed
# 		if request.method == "POST":
# 			form = MobileVerificationForm(request.POST,user_id=user_id,allow_reverification=False)
# 			ttl = is_sms_sending_rate_limited(user_id)
# 			if ttl:
# 				return render(request,"verification/enter_pin_code.html",{'form':PinVerifyForm(),'ttl':ttl,'reentry_instr':True})
# 			elif form.is_valid():
# 				phonenumber = form.cleaned_data.get("phonenumber")
# 				target_number = '+92'+phonenumber[-10:]
# 				# generate and send a pin code to the given mobile number
# 				send_user_pin.delay(user_id, target_number)
# 				twiliolog_pin_sms_sent()
# 				request.session['phonenumber'+str(user_id)] = phonenumber    
# 				request.session.modified = True
# 				return render(request,"verification/enter_pin_code.html",{'form':PinVerifyForm()})
# 			else:
# 				return render(request,'verification/user_mobile_verification.html',{'form':form})
# 		else:
# 			# it's a GET request
# 			ttl = is_sms_sending_rate_limited(user_id)
# 			if ttl:
# 				return render(request,"verification/enter_pin_code.html",{'form':PinVerifyForm(),'ttl':ttl,'reentry_instr':True})
# 			else:
# 				return render(request,'verification/user_mobile_verification.html',{'form':MobileVerificationForm(),\
# 					'pin_expired':request.session.pop("start_verification_again"+str(user_id),None)})

	
# ############################## Pink star verification #################################