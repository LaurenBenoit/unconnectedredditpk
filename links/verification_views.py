import uuid
from django.db.models import F
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import cache_control
from verification_forms import AddVerifiedUserForm, rate_limit_artificial_verification, MobileVerificationForm,PinVerifyForm
from tasks import send_user_pin, save_consumer_credentials, increase_user_points
from redis3 import save_consumer_number, rate_limit_sms_sending, retrieve_random_pin
from redis4 import retrieve_uname
from models import UserProfile
from score import NUMBER_VERIFICATION_BONUS



@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def verify_user_artificially(request):
	"""
	This renders a template where user_ids can be artificially verified (mobile)

	This also processes the verification step
	"""
	if retrieve_uname(request.user.id,decode=True) in ['pathan-e-khan','Damadam-Feedback','mhb11']:
		if request.method == "POST":
			processed_form = AddVerifiedUserForm(request.POST)
			if processed_form.is_valid():
				success = rate_limit_artificial_verification()
				if success:
					valid_user_id = processed_form.cleaned_data.get("user_id")
					random_string = str(uuid.uuid4())
					account_kid_id = 'artificial_verification'		
					mobile_data = {'national_number':random_string,'number':random_string,'country_prefix':'92'}
					with_points = request.POST.get("wth_pts",None)
					save_consumer_number(account_kid_id,mobile_data,valid_user_id)
					if with_points == '1':
						UserProfile.objects.filter(user_id=valid_user_id).update(score=F('score')+500)
					
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

############################## User number verification #################################
# @csrf_protect
# def buyer_details(request,origin,*args,**kwargs):


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def verify_user_mobile(request):
	"""
	This renders a template where user puts her number that she wants verified

	"""
	user_id = request.user.id
	if request.method == "POST":
		form = MobileVerificationForm(request.POST,user_id=user_id)
		if form.is_valid():
			phonenumber = form.cleaned_data.get("phonenumber")
			user_id = request.user.id
			pin = retrieve_random_pin(user_id)
			target_number = '+92'+phonenumber[-10:]
			send_user_pin.delay(target_number,pin)
			rate_limit_sms_sending(user_id)
			form = PinVerifyForm
			request.session['phonenumber']=phonenumber	
			request.session.modified = True
			return render(request,"verification/enter_pin_code.html",{'form':form,'phonenumber':phonenumber})
		else:
			return render(request,'verification/user_mobile_verification.html',{'form':form})
	else:		
		form = MobileVerificationForm()
		return render(request,'verification/user_mobile_verification.html',{'form':form})
	


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def pin_verification(request):
	"""
	This will verify the pin entered by the user

	"""
	if request.method == "POST":
		user_id = request.user.id
		form = PinVerifyForm(request.POST,user_id=user_id)
		phonenumber = request.session.get('phonenumber',None)
		if form.is_valid():
			pin_state = form.cleaned_data.get("pinnumber")
			if pin_state == 'pin_matched':
				account_kid_id = 'twilio_verification'
				national_number = phonenumber[-10:]
				number ='+92'+national_number	
				mobile_data = {'national_number':national_number,'number':number,'country_prefix':'92'}
				save_consumer_credentials.delay(account_kid_id, mobile_data, user_id)
				increase_user_points.delay(user_id=user_id, increment=NUMBER_VERIFICATION_BONUS)
				return render(request,"reward_earned.html",{})
		else:
			return render(request,"verification/enter_pin_code.html",{'form':form,'phonenumber':phonenumber})
	else:
		return redirect('missing_page')

	