import redis, re
from django import forms
from django.contrib.auth.models import User
from redis3 import is_mobile_verified, someone_elses_number, is_sms_sending_rate_limited, verify_user_pin
from location import REDLOC3
TEN_SECS = 10
POOL = redis.ConnectionPool(connection_class=redis.UnixDomainSocketConnection, path=REDLOC3, db=0)

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



def rate_limit_artificial_verification():
	"""
	rate limits artificial verification for 30 mins for security reasons
	"""
	myserver = redis.Redis(connection_pool=POOL)
	if myserver.exists('avrl'):
		return False
	else:
		myserver.setex("avrl","1",TEN_SECS)
		return True

def is_artificial_verification_ratelimited():
	"""
	checks if artificial verification is ratelimited
	"""		
	ttl = redis.Redis(connection_pool=POOL).ttl("avrl")
	if ttl>0:
		return ttl
	else:
		return None

class AddVerifiedUserForm(forms.Form):
	user_id = forms.CharField(max_length=50)

	class Meta:
		fields = ("user_id",)

	def __init__(self, *args, **kwargs):
		# self.user_id = kwargs.pop('user_id',None)
		super(AddVerifiedUserForm, self).__init__(*args, **kwargs)
		self.fields['user_id'].widget.attrs['class'] = 'cxl sp'
		self.fields['user_id'].widget.attrs['autofocus'] = 'autofocus'
		self.fields['user_id'].widget.attrs['autocomplete'] = 'off'
		self.fields['user_id'].widget.attrs['style'] = 'max-width:90%;background-color:#F8F8F8;border: 1px solid lightgray;border-radius:5px;color: #404040;height:30px'

	def clean_user_id(self):
		user_id = self.cleaned_data.get("user_id")
		user_id = user_id.strip()
		try:
			user_id = int(user_id)
		except (ValueError,TypeError):
			raise forms.ValidationError('Does not compute')

		ttl=is_artificial_verification_ratelimited()
		if ttl:
			raise forms.ValidationError('Not possible till %s years' % ttl)
		else:	
			# does user exist
			if User.objects.filter(id=user_id).exists():
				# go on
				if is_mobile_verified(user_id):
					raise forms.ValidationError('This dude is already king')
				else:
					return user_id
			else:
				raise forms.ValidationError('Is gone with the wind')


##################### Mobile number verification form #####################################

class MobileVerificationForm(forms.Form):
	"""
	Generates a form for user mobile number verification
	"""	
	phonenumber = forms.RegexField(max_length=11, regex=re.compile("^[0-9]+$"),\
		error_messages={'required': 'Mobile number diay gaiey tareekay say likhna zaroori hai',\
		'invalid':'Mobile number di gai misaal ki tarah likhien'})
	
	class Meta:
		fields = ('phonenumber')

	def __init__(self, *args, **kwargs):
		self.user_id = kwargs.pop('user_id',None)
		super(MobileVerificationForm, self).__init__(*args, **kwargs)
		self.fields['phonenumber'].widget.attrs['style'] = \
		'background-color:#fffce6;width:100%;border: 1px solid #80acaa;border-radius:5px;padding: 6px 6px 6px 0;text-indent: 6px;color: #80acaa;'
		self.fields['phonenumber'].widget.attrs['autofocus'] = 'on'	
		self.fields['phonenumber'].widget.attrs['class'] = 'cxl'
		self.fields['phonenumber'].widget.attrs['autocomplete'] = 'off'

	
	def clean_phonenumber(self):
		phonenumber = self.cleaned_data.get('phonenumber')
		already_verified = is_mobile_verified(self.user_id)
		mobile_length = len(phonenumber)
		if phonenumber[0] != '0':
			raise forms.ValidationError('Mobile number "0" se start karein')
		elif phonenumber[0:2] != '03':
			raise forms.ValidationError('Mobile number "03" se start karein')
		elif mobile_length < 11:
			raise forms.ValidationError('Poora mobile number likhein')
		elif phonenumber == '03451234567':
			raise forms.ValidationError('Apna real mobile number likhein')
		elif already_verified:
			raise forms.ValidationError('Ap pehley se verified hain')
		ttl = is_sms_sending_rate_limited(self.user_id)
		if ttl:
			raise forms.ValidationError('Ap dubara SMS receive kar sakein ge {0} baad'.format(secs_to_mins(ttl)))
		#phonenumber = ''.join(re.split('[, \-_!?:]+',phonenumber)) #removes any excess characters from the mobile number
		check = someone_elses_number(phonenumber[-10:],self.user_id)
		if check: 
			raise forms.ValidationError('Ye number aik aur user ka hai, mukhtalif number likhien')
			#Check if phone number associated with another profile
			 
		return phonenumber[-11:]



class PinVerifyForm(forms.Form):
	pinnumber = forms.RegexField(max_length=5,regex=re.compile("^[0-9]+$"),error_messages={'required': 'Pin Code likhna zaroori hai','invalid':'Pin mein sirf number likhein'})

	class Meta:
		fields = ('pinnumber')

	def __init__(self, *args, **kwargs):
		self.user_id = kwargs.pop('user_id',None)
		super(PinVerifyForm, self).__init__(*args, **kwargs)		
		self.fields['pinnumber'].widget.attrs['style'] = \
		'background-color:#fffce6;width:65px;border: 1px solid #80acaa;border-radius:5px;padding: 6px 6px 6px 0;text-indent: 6px;color: #80acaa;'
		self.fields['pinnumber'].widget.attrs['class'] = 'cxl'
		self.fields['pinnumber'].widget.attrs['autofocus'] = 'autofocus'
		self.fields['pinnumber'].widget.attrs['autocomplete'] = 'off'
			
	def clean_pinnumber(self):
		pinnumber = self.cleaned_data.get('pinnumber')
		if len(pinnumber) < 5:
			raise forms.ValidationError('Poora pin code likhien')
		exists, status = verify_user_pin(self.user_id,pinnumber)	
		if exists:
			return status
		else:
			if status == 'pin_incorrect':
				raise forms.ValidationError('Apki pin ghalat hai')
			else:
				#runs when pin is invalid or has expired
				raise forms.ValidationError('Sorry! Apki pin expire ho gai hai. Dobara shuru say verify kerien')
				





