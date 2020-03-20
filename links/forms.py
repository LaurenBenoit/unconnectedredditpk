# coding=utf-8
import re, time, random, unicodedata
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import check_password
from django.core.files.images import get_image_dimensions
from django.utils.translation import ugettext, ugettext_lazy as _
from django.core import validators
from django.forms import Textarea
from django import forms
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
from tasks import invalidate_avatar_url
from redis7 import retrieve_topic_credentials
from image_processing import compute_avg_hash, reorient_image, make_thumbnail, prep_image
from redis6 import is_group_member_and_rules_signatory, human_readable_time, group_member_exists
from models import UserProfile, ChatInbox, PhotoComment, ChatPicMessage, Photo, Link, ChatPic, UserSettings, Publicreply
from redis4 import retrieve_previous_msgs,many_short_messages, log_short_message, is_limited, get_and_delete_text_input_key, get_aurl, \
is_attribute_change_rate_limited
from score import MAX_HOME_SUBMISSION_SIZE, MAX_HOME_REPLY_SIZE, MAX_PHOTO_CAPTION_SIZE, RIGHT_ALIGNMENT_THRESHOLD_RATIO,\
MAX_BIO_SIZE, PRIVATE_GROUP_REPLY_LENGTH, PUBLIC_GROUP_REPLY_LENGTH#, MAX_PHOTO_COMMENT_SIZE
from redis3 import log_logger

########################################### Utilities #######################################

def retrieve_validation_error_string(err_type, lang=None, payload=None):
	"""
	Return a validation error string, if given 'err_type' of error

	Takes 'payload' as an optional parameter in case the error string requires enrichment (e.g. a nickname has to be inserted into it)
	"""
	if err_type == 'nick_empty':
		if lang == 'ur':
			return 'نام کو خالی نہ چھویں'
		else:
			return "Nickname khali nahi chorein"
	if err_type == 'nick_too_small':
		if lang == 'ur':
			return 'نام اتنا چهوٹا نہیں ہو سکتا'
		else:
			return 'Nickname itna chota nahi ho sakta'
	elif err_type == 'invalid_new_nick':
		if lang == 'ur':
			return "نام میں انگریزی حروف، نمبر اور @ _ + - کے نشان کے علاوہ اور کچھ نہیں ہو سکتا۔ دوبارا کوشش کریں"
		else:
			return "Nickname mein english harf, number ya @ _ . + - likhein"
	elif err_type == 'required_new_nick':
		if lang == 'ur':
			return 'اس سفید پٹی میں نام لکھیں'
		else:
			return "Safed patti mein nickname likh ke OK dabain"
	elif err_type == 'required_visible_nick':
		if lang == 'ur':
			return 'نک نیم میں حرف لکهنا ضروری ے'
		else:
			return "Nickname mein harf likhna zaruri hain"
	elif err_type == 'nick_only_has_digits':
		if lang == 'ur':
			return 'نام میں صرف نمبر نہیں ہو سکتے'
		else:
			return 'Nickname mei sirf numbers nahi ho saktey'
	elif err_type == 'nick_is_taken':
		if lang == 'ur':
			return 'یہ نام پہلے سے کسی نے رکھا ہوا ہے، کوی اور نام رکھیں'
		else:
			return '"%s" kisi aur ka nickname hai. Kuch aur likhein' % payload
	elif err_type == 'nick_recently_taken':
		if lang == 'ur':
			return 'یہ نام آپ سے پہلے کسی اور نے رکھ لیا'
		else:
			return '"%s" nickname ap se pehle kisi aur ne rakh liya' % payload
	elif err_type == 'banned_sequence_in_nick':
		if lang == 'ur':
			return 'نام میں "%s" نہیں ڈالیں' % payload
		else:
			return 'Nickname mein "%s" nahi ho sakta' % payload
	elif err_type == 'illegal_sequence_in_nick':
		if lang == 'ur':
			return 'نام میں "%s" نہیں ڈالیں' % payload
		else:
			return 'Nickname mein "%s" nahi dalein' % payload
	elif err_type == 'dot_at_nick_start':
		if lang == 'ur':
			return 'نام کے شروع میں . نہیں ڈالیں'
		else:
			return "Nickname ke start mein . nahi dalein"
	elif err_type == 'dot_at_nick_end':
		if lang == 'ur':
			return 'نام کے آخر میں . نہیں ڈالیں'
		else:
			return "Nickname ke end mein . nahi dalein"
	elif err_type == 'dash_at_nick_start':
		if lang == 'ur':
			return 'نام کے شروع میں - نہیں ڈالیں'
		else:
			return "Nickname ke start mein - nahi dalein"
	elif err_type == 'dash_at_nick_end':
		if lang == 'ur':
			return 'نام کے آخر میں - نہیں ڈالیں'
		else:
			return 'Nickname ke end mein - nahi dalein'
	elif err_type == 'plus_at_nick_start':
		if lang == 'ur':
			return 'نام کے شروع میں + نہیں ڈالیں'
		else:
			return 'Nickname ke start mein + nahi dalein'
	elif err_type == 'plus_at_nick_end':
		if lang == 'ur':
			return 'نام کے آخر میں + نہیں ڈالیں'
		else:
			return 'Nickname ke end mein + nahi dalein'
	elif err_type == 'uscore_at_nick_start':
		if lang == 'ur':
			return 'نام کے شروع میں _ نہیں ڈالیں'
		else:
			return 'Nickname ke start mein _ nahi dalein'
	elif err_type == 'uscore_at_nick_end':
		if lang == 'ur':
			return 'نام کے آخر میں _ نہیں ڈالیں'
		else:
			return 'Nickname ke end mein _ nahi dalein'
	elif err_type == 'repeating_sequence_in_nick':
		if lang == 'ur':
			return "ایک ہی چیز کو بار بار نہ لکھیں"
		else:
			return 'Nickname mein aik hi cheez bar bar nahi likhein'
	elif err_type == 'generic_nickname_error':
		if lang == 'ur':
			return 'یہ نام صحیح نہیں ہے'
		else:
			return "Ye nickname sahi nahi hai"
	elif err_type == 'bad_case':
		if lang == 'ur':
			return 'نک نیم میں حرف غلط ہیں ـ یا بڑا حرف چھوٹا لکھ دیا ے، یا چھوٹا حرف بڑا'
		else:
			return '"%s" nickname mein harf ghalat hain. Ya chota harf bara likh diya hai, ya bara harf chota' % payload
	elif err_type == 'not_found':
		if lang == 'ur':
			return 'یہ نک نیم ﮨمارے رکارڈ میں نہیں'
		else:
			return '"%s" hamarey record mein nahi' % payload
	elif err_type == 'banned_sequence_in_pass':
		if lang == 'ur':
			return 'اس پاس ورڈ کا اندازہ لگانا آسان ہے، کچھ اور لکھیں'
		else:
			return '"%s" ko boojhna aasan hai, kuch aur likhein' % payload
	elif err_type == 'example_sequence_in_pass':
		if lang == 'ur':
			return 'یہ پاس ورڈ استعمال نہیں کریں'
		else:
			return '"%s" ko password nahi rakhein' % payload
	elif err_type == 'nickname_in_pass':
		if lang == 'ur':
			return 'پاس ورڈ میں نام نہ لکھیں'
		else:
			return '"%s" nahi likh sakte kiyunke nickname mein hai' % payload
	elif err_type == 'pass_too_small':
		if lang == 'ur':
			return 'کم سے کم چھ حرف لکھنا ضروری ہے'
		else:
			return "Kam se kam 6 letters likhna zaruri hain!"
	elif err_type == 'required_visible_pass':
		if lang == 'ur':
			return 'پاس ورڈ میں حرف لکهنا ضروری ہے'
		else:
			return 'Password mein harf likhna zaruri hain'
	elif err_type == 'old_new_pass_same':
		if lang == 'ur':
			return 'نیا پاس ورڈ پرانے پاس ورڈ سے مختلف رکھیں'
		else:
			return 'New password old password se different rakhein'
	elif err_type == 'required_new_pass':
		if lang == 'ur':
			return 'سفید پٹی میں پاس ورڈ لکھیں'
		else:
			return "Safed patti mein password likhein"
	elif err_type == 'pass_empty':
		if lang == 'ur':
			return 'پاس ورڈ خالی نہیں چھوڑیں'
		else:
			return "Password khali nahi chorein"
	elif err_type == 'wrong_pass_input':
		if lang == 'ur':
			return 'پاس ورڈ غلط لکھا ہے ۔ اگر پاس ورڈ یاد نہیں تو سب سے نیچے "پاس ورڈ بھول گۓ" کو دبایں'
		else:
			return 'Password sahi nahi. Agr password yad nahi tou sab se neechay "Forgot Password" dabain'
	elif err_type == 'wrong_pin':
		if lang == 'ur':
			return 'کوڈ غلط ہے'
		else:
			return 'Apka pin code ghalat hai'
	elif err_type == 'invalid_pin':
		if lang == 'ur':
			return 'کوڈ میں صرف نمبر لکھیں'
		else:
			return 'Pin mein sirf number likhein'
	elif err_type == 'pin_too_small':
		if lang == 'ur':
			return 'پورا کوڈ لکھیں'
		else:
			return 'Pura pin code likhien'
	elif err_type == 'required_pin':
		if lang == 'ur':
			return 'خفیہ کوڈ لکهنا ضروری ے'
		else:
			return 'Pin code likhna zaruri hai'
	elif err_type == 'pin_tries_rate_limited':
		if lang == 'ur':
			return 'بہت زیادہ غلطیاں ہو گیں، واپس آیں %s baad' % payload
		else:
			return 'Ziyada ghalat tries ho gaien, %s baad wapis aien' % payload
	elif err_type == 'mobnum_too_small':
		if lang == 'ur':
			return 'پورا موبائل نمبر لکھیں'
		else:
			return 'Pura mobile number likhein'
	elif err_type == 'fake_mobnum':
		if lang == 'ur':
			return 'اپنا اصلی موبائل نمبر لکھیں'
		else:
			return 'Apna real mobile number likhein'
	elif err_type == 'mobnum_not_verified':
		if lang == 'ur':
			return 'آپکا موبائل نمبر تصدیق شدہ نہیں، پاس ورڈ نہیں مل سکتا'
		else:
			return 'Ap verified nahi, password nahi mil sakta'
	elif err_type == 'not_your_mobnum':
		if lang == 'ur':
			return ' موبائل نمبر صحیح لکھیں'
		else:
			return 'Mobile number sahi likhein'
	elif err_type == 'mobnum_wrong_format':
		if lang == 'ur':
			return 'موبائل نمبر "03" سے شروع کریں'
		else:
			return 'Mobile number "03" se start karein'
	elif err_type == 'required_mobnum':
		if lang == 'ur':
			return 'موبائل نمبر لکهنا ضروری ے'
		else:
			return 'Mobile number likhna zaruri hai'
	elif err_type == 'invalid_mobnum':
		if lang == 'ur':
			return 'اپنا موبائل نمبر اس طرح لکھیں - 03451234567'
		else:
			return 'Mobile number is andaz mein likhein - 03451234567'
	elif err_type == 'display_pic_rate_limited':
		if lang == 'ur':
			return ''
		else:
			return 'Ap profile photo change kar sakien ge %s secs baad' % payload
	elif err_type == 'required_age':
		if lang == 'ur':
			return 'عمر ضرور لکھیں'
		else:
			return 'Age likhna zaruri hai'
	elif err_type == 'age_too_large':
		if lang == 'ur':
			return 'عمر صحیح لکھیں'
		else:
			return 'Age sahi likhein'
	elif err_type == 'display_pic_frozen':
		if lang == 'ur':
			return ''
		else:
			return 'Sorry! Apki profile report ho chuki hai. Investigation puri honay tak display pic change nahi ki ja sakti'
	elif err_type == 'fbs_image_too_big':
		if lang == 'ur':
			return 'فری بیسکس پے دو سو کے بی سے بڑی فوٹو نہیں لگتی'
		else:
			return 'Freebasics pe 200 KB se barri photos nahi lagtein. Data package on karein!'
	elif err_type == 'image_too_big':
		if lang == 'ur':
			return 'دس ایم بی سے بڑی فوٹو نہیں لگتی'
		else:
			return 'Sorry! 10 MB se barri photos nahi lagtein'
	else:
		# generic error string
		return "Ye sahi nahi hai"


def repetition_found(section,section_id,user_id, target_text):
	msgs_list = retrieve_previous_msgs(section=section, section_id=section_id,user_id=user_id)
	if msgs_list:
		if target_text in [x.decode('utf-8') for x in msgs_list[1:]]:
			return True
		else:
			return False
	else:
		return False


def strip_zero_width_characters(string):
	"""
	Strips out 'zero-width' characters from given string - disallowing users from successfully submitting blank enteries

	List of easily copy-able zero-width characters can be found at https://coolsymbol.com/zero-width-space-joiner-non-joiner-ltr-rtl-lrm-rlm-characters-symbols.html
	u"\u200B" - Zero Width Space
	u"\u200C" - Zero Width Non-Joiner
	u"\u200D" - Zero Width Joiner
	u"\u200E" - Left-To-Right Mark
	u"\u200F" - Right-To-Left Mark
	u"\u2060" - Word Joiner
	u"\uFEFF" - Zero Width No-Break Space
	u"\u3164" - Hangful filler
	"""
	if string:
		return ''.join( c for c in string if  c not in (u"\u200B",u"\u200C",u"\u200D",u"\u200E",u"\u200F",u"\u2060",u"\uFEFF",u"\u3164"))
	else:
		return string


def uniform_string(text,n=7):
	text = text.lower()
	for i, c in enumerate(text):
		if text[i:i+n] == c * n:
			return text[i:i+n]
	return False

def getip(request):
	ip = request.META.get('X-IORG-FBS-UIP',
		request.META.get('REMOTE_ADDR')
	)
	return ip

def clear_zalgo_text(text):
	return ''.join((c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn'))


def is_urdu(text):
	"""
	Provides a percentage of how much text is predominantly in "Urdu"

	Can be used to right-align text that is predominantly in Urdu
	Utilizes the fact that "0600-06FF" and "FB50-FEFF" is the Unicode range for Urdu
	"""
	num_urdu_chars, total_chars = 0, len(text)
	if total_chars:
		for c in text:
			if u'\u0600' <= c <= u'\u06FF' or u'\uFB50' <= c <= u'\uFEFF':
				num_urdu_chars += 1
		return (num_urdu_chars*1.0)/total_chars
	else:
		return 0


################################################################################################


class UserProfileForm(forms.ModelForm):
	"""
	This controls the userprofile edit form
	"""
	MardAurat = (
		('1','Female'),
		('0','Male'),
		)
	MaritalStatus = (
		('1','Yes'),
		('0','No'),
		)
	# RATING = (
	# 	('0','Ek dum kadak'),
	# 	('1','Fifty fifty'),
	# 	('2','Shakal pe mat ja'),
	# )
	avatar = forms.ImageField(label='Photo Lagao', help_text='less than 1 mb', required=False)
	gender = forms.TypedChoiceField(choices=MardAurat, widget=forms.RadioSelect, coerce=int)
	shadi_shuda = forms.TypedChoiceField(choices=MaritalStatus, widget=forms.RadioSelect, coerce=int)
	# attractiveness = forms.TypedChoiceField(choices=RATING, widget=forms.RadioSelect, coerce=int)
	bio = forms.CharField(widget=forms.Textarea(attrs={'class': 'cxl lsp sp','autocomplete': 'off','autocapitalize':'off','spellcheck':'false',\
		'maxlength':MAX_BIO_SIZE}),error_messages={'required': 'Ye likhna zaruri hai'})
	age = forms.IntegerField(required=False,widget=forms.Textarea(attrs={'cols':10,'rows':1,'style':'width:50px;height:20px;border-radius:5px;border: 1px #E0E0E0 solid; background-color:#FAFAFA;padding:5px;','class':'cxl sp'}))
	streak = forms.IntegerField(required=False)
	attractiveness = forms.IntegerField()

	class Meta:
		model = UserProfile
		exclude = ('user','previous_retort') #so user and previous_retort doesn't show, but the extended attributes of bio and mobile number do show
		fields=('avatar', 'streak', 'bio', 'gender', 'age', 'shadi_shuda', 'attractiveness')

	def __init__(self, *args, **kwargs):
		# you take the user out of kwargs and store it as a class attribute
		self.user = kwargs.pop('user', None)
		self.on_fbs = kwargs.pop('on_fbs', None)
		super(UserProfileForm, self).__init__(*args, **kwargs)
		self.fields['avatar'].widget.attrs['style'] = 'width:95%;'
		self.fields['bio'].widget.attrs['style'] = 'width:95%;height:200px;border-radius:8px;border: 1px #1edea8 solid; background-color:#f2f1f0;padding:5px;'
		self.fields['bio'].widget.attrs['class'] = 'inp'
		self.fields['age'].error_messages = {'required':retrieve_validation_error_string('required_age'),\
		'invalid':retrieve_validation_error_string('age_too_large')}
		self.fields['age'].widget.attrs['maxlength'] = 2
		self.fields['age'].widget.attrs['class'] = 'inp'
		self.fields['streak'].error_messages = {'invalid':'Ye ghalat hai'}
		

	def clean_avatar(self):
		image=self.cleaned_data.get("avatar")
		try:
			if image.name in self.user.userprofile.avatar.url:
				#print "no need to re-submit image"
				return image
		except (AttributeError, ValueError):
			pass
		if image or image is False:    
			user_id, on_fbs = self.user.id, self.on_fbs
			# is_frozen = is_user_profile_frozen(user_id)# TODO: could be frozen if was reported
			# if is_frozen:
			#     raise forms.ValidationError(retrieve_validation_error_string('display_pic_frozen'))
			# else:
			ttl = get_aurl(user_id)# in case avatar changing is rate limited because user just changed their avatar (small TTL) 
			if ttl > 1:
				raise forms.ValidationError(retrieve_validation_error_string('display_pic_rate_limited',payload=ttl))
			invalidate_avatar_url.delay(user_id, set_rate_limit=True)
			if image:
				if on_fbs:
					if image.size > 200000:#200 KB allowance
						raise forms.ValidationError(retrieve_validation_error_string('fbs_image_too_big'))
					else:
						pass
				else:
					if image.size > 10000000:#10 MB allowance
						raise forms.ValidationError(retrieve_validation_error_string('image_too_big'))
					else:
						pass
				image = Image.open(image)
				if on_fbs:
					image = make_thumbnail(image,None)#low quality upload for fbs
				else:
					image, img_width, img_height = prep_image(image,quality=True)#high qualuty upload for non-fbs
				return image
			else:
				return 0
		else:
			return None

	def clean_bio(self):
		bio = self.cleaned_data.get("bio")
		bio = bio.strip()
		bio = clear_zalgo_text(bio)
		len_bio = len(bio)
		if len_bio > MAX_BIO_SIZE:
			raise forms.ValidationError("Apki story {0} chars se barri nahi ho sakti. Aap ne {1} chars likhey".format(MAX_BIO_SIZE,len_bio))
		return bio

	def clean_age(self):
		age = self.cleaned_data.get("age")
		if age:
			if age > 99:
				raise forms.ValidationError(retrieve_validation_error_string('age_too_large'))
			elif age < 12:	
				raise forms.ValidationError(retrieve_validation_error_string('age_too_large'))
			return age

	def clean_streak(self):
		"""
		Actually contains 'city' data. Mislabelled for legacy reasons
		"""
		city = self.cleaned_data.get("streak")
		if not city:
			city = 0
		is_rate_limited, rate_limit_time = is_attribute_change_rate_limited(user_id=self.user.id, time_now=time.time(), attribute_value=city,\
			rate_limit_type='city')
		if is_rate_limited:
			raise forms.ValidationError("Ap city change kar sakein ge {} baad".format(human_readable_time(rate_limit_time)))
		return city

	def clean_attractiveness(self):
		"""
		Actually contains 'zodiac' data. Mislabelled for legacy reasons
		"""
		zodiac = self.cleaned_data.get("attractiveness")
		is_rate_limited, rate_limit_time = is_attribute_change_rate_limited(user_id=self.user.id, time_now=time.time(), attribute_value=zodiac,\
			rate_limit_type='zodiac')
		if is_rate_limited:
			raise forms.ValidationError("Ap star sign change kar sakein ge {} baad".format(human_readable_time(rate_limit_time)))
		return zodiac


	# def clean_mobilenumber(self):
	# 	mob_num = self.cleaned_data.get("mobilenumber")
	# 	return mob_num if mob_num else ''


class UserSettingsForm(forms.ModelForm):
	ScoreVisible = (
		('0','No'),
		('1','Yes'),
		)
	score_setting = forms.TypedChoiceField(choices=ScoreVisible, widget=forms.RadioSelect, coerce=int)
	class Meta:
		model = UserSettings
		exclude = ('user', 'setting2', 'setting3', 'setting4', 'setting5')
		fields = ('score_setting',)


class LinkForm(forms.Form):#this controls the link edit form
	description = forms.CharField(widget=forms.Textarea(attrs={'class': 'cxl','autofocus': 'autofocus',\
		'autocomplete': 'off','autocapitalize':'off','spellcheck':'false','maxlength':MAX_HOME_SUBMISSION_SIZE}),\
	error_messages={'required': 'Pehlay kuch likhein, phir OK dabain'})
	sk = forms.CharField(required=False)
	turl = forms.CharField(required=False)# this is topic_url
	aud = forms.CharField(required=False)
	exp = forms.CharField(required=False)
	com = forms.CharField(required=False)

	# class Meta:
	# 	model = Link
	# 	exclude = ("submitter", "rank_score", "cagtegory",)
	# 	fields = ("image_file", "description",)

	def __init__(self,*args,**kwargs):
		self.user_id = kwargs.pop('user_id',None)
		# self.on_fbs = kwargs.pop('on_fbs',None)
		# self.on_opera = kwargs.pop('on_opera',None)
		super(LinkForm, self).__init__(*args,**kwargs)
		self.fields['description'].widget.attrs['style'] = 'width:95%;height:220px;border-radius:10px;border: 1px #93d7ec solid; background-color:white;padding:7px;'

	def clean(self):
		# on_fbs, on_opera = self.on_fbs, self.on_opera
		data = self.cleaned_data
		description, user_id, section_id, section, secret_key_from_form, topic_url, audience, expiry, com = data.get("description"), self.user_id, '1', 'home', \
		data.get("sk"), data.get('turl',None), data.get('aud',None), data.get('exp',None),data.get('com',None)
		secret_key_from_session = get_and_delete_text_input_key(user_id,'1','likho')
		description = description.strip() if description else None
		description = strip_zero_width_characters(description)
		###########################
		if not audience:
			audience = 'p'
			data['aud'] = 'p'
		if not expiry:
			expiry = 'i'
			data['exp'] = 'i'
		if not com:
			com = '1'
			data['com'] = '1'	
		###########################	
		if audience not in ('p','a','s') or expiry not in ('i','m1','m2') or com not in ('1','0'):
			raise forms.ValidationError('Dubara koshish karein')
		elif not description or description.isspace():
			raise forms.ValidationError('Likhna zaruri hai')
		else:
			len_ = len(description)
			if len_ > MAX_HOME_SUBMISSION_SIZE+150:
				# if post is too long, short circuit the rest of the cleaning method anyway
				raise forms.ValidationError('Sorry! Itni lambi post submit nahi ho sakti')
			else:
				description = re.sub(r'\n\s*\n', '\n', description)# collapsing multiple new lines into 1
				lines = description.split('\n')
				if len(lines) > 20:
					raise forms.ValidationError('Itni zyada new lines nahi dalein!')
				elif secret_key_from_form != secret_key_from_session:
					raise forms.ValidationError('Sirf aik dafa button dabain')
				# elif repetition_found(section=section,section_id=section_id,user_id=user_id, target_text=description):
				# NOT NEEDED
				# 	raise forms.ValidationError('Milti julti baatien nahi likhein')
				else:
					rate_limited, reason = is_limited(user_id,section='home',with_reason=True)
					if rate_limited > 0:
						raise forms.ValidationError('Ap yahan pe likhne se {0} tak banned hain. Reason: {1}'.format(human_readable_time(rate_limited),reason))
					else:
						if len_ < 4:
							raise forms.ValidationError('Itna chota reply nahi likh sakte')
						elif len_ < 6:
							if many_short_messages(user_id,section,section_id):
								raise forms.ValidationError('Har thori deir baad yahan chota reply nahi likhein')
							else:
								log_short_message(user_id,section,section_id)
						elif len_ > MAX_HOME_SUBMISSION_SIZE:
							raise forms.ValidationError('Ap ne {0} chars likhey, ap {1} se zyada chars nahi likh saktey'.format(len_,MAX_HOME_SUBMISSION_SIZE))
						# '2' means right-aligned text, '1' means left-aligned text
						data['alignment'] = '2' if is_urdu(description) >= RIGHT_ALIGNMENT_THRESHOLD_RATIO else '1'
						data['description'] = description
						#################################
						data['tpay'], data['turl'], data['tname'], data['bgt'] = None, None, None, None
						if topic_url:
							topic_name, bg_theme, is_subscribed = retrieve_topic_credentials(topic_url=topic_url, with_name=True, \
								with_theme=True, with_is_subscribed=True, retriever_id=user_id)
							if is_subscribed:
								data['tpay'], data['turl'], data['tname'], data['bgt'] = bg_theme+":"+topic_name+":"+topic_url, topic_url, \
								topic_name, bg_theme
						return data


class WelcomeMessageForm(forms.ModelForm):
	description = forms.CharField(widget=forms.Textarea(attrs={'cols':40,'rows':3}))

	class Meta:
		model = Publicreply
		exclude = ("submitted_by","answer_to","seen","category","abuse","submitted_on")
		fields = ("description",)



class SearchNicknameForm(forms.Form):
	nickname = forms.CharField(max_length=71,error_messages={'required': 'Safed patti mein "nickname" likhein jisko search karna hai'})

	def __init__(self, *args, **kwargs):
		self.searched = kwargs.pop('searched',False)
		super(SearchNicknameForm, self).__init__(*args, **kwargs)
		self.fields['nickname'].widget.attrs['style'] = \
		'max-width:90%;width:500px;background-color:#F8F8F8;border: 1px solid #3cb7dd;border-radius:5px;padding: 6px 6px 6px 0;text-indent: 6px;color: #229ec9;'
		self.fields['nickname'].widget.attrs['class'] = 'cxl inp'
		self.fields['nickname'].widget.attrs['autocomplete'] = 'off'

	def clean_nickname(self):
		nickname = self.cleaned_data.get("nickname")
		nickname = nickname.strip()
		if len(nickname) > 70:
			raise forms.ValidationError('Itna bara nickname nahi likh sakte')
		return nickname


class UploadPhotoForm(forms.Form):
	image_file = forms.ImageField(label='Upload', error_messages={'required': 'Photo ka intekhab sahi nahi hua','invalid':'Selected photo upload nahi ho sakti'})
	caption = forms.CharField(widget=forms.Textarea(attrs={'cols':20,'rows':2,'spellcheck':'false','maxlength':MAX_HOME_SUBMISSION_SIZE}),\
		error_messages={'required': 'Photo ke barey mien likhna zaroori hai'})
	aud = forms.CharField(required=False)
	exp = forms.CharField(required=False)
	com = forms.CharField(required=False)

	def __init__(self, *args, **kwargs):
		super(UploadPhotoForm, self).__init__(*args, **kwargs)
		self.fields['caption'].widget.attrs['style'] = 'width:95%;height:70px;border-radius:10px;border: 1px #93d7ec solid; background-color:white;padding:7px;'
		self.fields['caption'].widget.attrs['id'] = 'pub_img_caption_field'
		self.fields['caption'].widget.attrs['class'] = 'cxl'
		self.fields['image_file'].widget.attrs['style'] = 'width:95%;background:#beeef4;height:45px;border-radius:7px'
		self.fields['image_file'].widget.attrs['id'] = 'browse_pub_img_btn'

	def clean_caption(self):
		caption = self.cleaned_data["caption"]
		caption = caption.strip() if caption else None
		caption = strip_zero_width_characters(caption)
		if not caption:
			raise forms.ValidationError('Photo ke barey mien likhna zaroori hai')
		else:
			caption_len = len(caption)
			if caption_len < 1:
				raise forms.ValidationError('Photo ke barey mien likhna zaroori hai')
			if caption_len < 8:
				raise forms.ValidationError('Zyada tafseel likhein ke photo mein kya hai')
			elif caption_len > MAX_HOME_SUBMISSION_SIZE:
				raise forms.ValidationError('{} chars se zyada nahi likhein, ap ne {} chars likhey'.format(MAX_HOME_SUBMISSION_SIZE,caption_len))
			elif caption.isdigit():
				raise forms.ValidationError('Sirf numbers nahi likhein, tafseel se likhein photo mein kya hai')
			elif '#' in caption:
				raise forms.ValidationError('Photo ki tafseel mein "#" nahi likhein')
			uni_str = uniform_string(caption)
			if uni_str:
			  if uni_str.isspace():
			      raise forms.ValidationError('Spaces itni zyada nahi daalein')
			  else:
			      raise forms.ValidationError('"%s" itni zyada dafa aik hi character repeat nahi karein, photo ko sahi se describe karein' % uni_str)
			else:
				return caption

	def clean_aud(self):
		audience = self.cleaned_data.get('aud','p')
		if audience not in ('p','a','s'):
			return 'p'
			# raise forms.ValidationError('Dubara koshish karein')	
		return audience
			
	def clean_exp(self):			
		expiry = self.cleaned_data.get('exp','i')
		if expiry not in ('i','m1','m2'):
			return 'i'
			# raise forms.ValidationError('Dubara koshish karein')	
		return expiry

	def clean_com(self):		
		# return self.cleaned_data.get('com','1')
		com = self.cleaned_data.get('com','1')
		if com not in ('1','0'):
			return '1'
			# raise forms.ValidationError('Dubara koshish karein')	
		return com


class FacesPagesForm(forms.Form):
	class Meta:
		pass

class PhotoShareForm(forms.Form):
	class Meta:
		pass

class PhotoScoreForm(forms.Form):
	class Meta:
		pass

class ContactForm(forms.Form):
	class Meta:
		pass

class AboutForm(forms.Form):
	class Meta:
		pass

class PrivacyPolicyForm(forms.Form):
	class Meta:
		pass

class PhotoHelpForm(forms.Form):
	class Meta:
		pass

class TopForm(forms.Form):
	class Meta:
		model = User

class WelcomeForm(forms.Form):
	class Meta:
		pass

class LogoutHelpForm(forms.Form):
	class Meta:
		pass

class FacesHelpForm(forms.Form):
	class Meta:
		pass

class EmoticonsHelpForm(forms.Form):
	class Meta:
		pass

class LogoutPenaltyForm(forms.Form):
	class Meta:
		pass

class UserProfileDetailForm(forms.Form):
	class Meta:
		pass

class RegisterLoginForm(forms.Form):
	class Meta:
		pass

class ReauthForm(forms.Form):
	password = forms.CharField(widget=forms.TextInput(attrs={'placeholder':''}))
	class Meta:
		fields = ("password",)

	def __init__(self,*args,**kwargs):
		self.request = kwargs.pop('request',None)
		super(ReauthForm, self).__init__(*args,**kwargs)
		self.fields['password'].error_messages = {'required':retrieve_validation_error_string('pass_empty'),'invalid':retrieve_validation_error_string('generic')}
		self.fields['password'].widget.attrs['style'] = \
		'background-color:whitesmoke;width:1000px;border: 1px solid #8cc1f8;max-width:90%;border-radius:5px;padding: 6px 6px 6px 0;text-indent: 6px;color: #808080;'
		self.fields['password'].widget.attrs['class'] = 'cxl'
		self.fields['password'].widget.attrs['autofocus'] = 'autofocus'
		self.fields['password'].widget.attrs['autocomplete'] = 'off'
		self.fields['password'].widget.attrs['autocapitalize'] = 'none'
		self.fields['password'].widget.attrs['spellcheck'] = 'false'

	def clean_password(self):
		entered_password = self.cleaned_data["password"]
		real_password = self.request.user.password
		if check_password(password=entered_password,encoded=real_password):
			return entered_password
		else:
			raise forms.ValidationError(retrieve_validation_error_string('generic'))


class ResetPasswordForm(forms.Form):
	password = forms.CharField()
	class Meta:
		fields = ('password',)

	def __init__(self,*args,**kwargs):
		self.request = kwargs.pop('request',None)
		super(ResetPasswordForm, self).__init__(*args,**kwargs)
		self.fields['password'].error_messages = {'required':retrieve_validation_error_string('pass_empty'),'invalid':retrieve_validation_error_string('generic')}
		self.fields['password'].widget.attrs['style'] = \
		'background-color:whitesmoke;width:1000px;border: 1px solid #8cc1f8;max-width:90%;border-radius:5px;padding: 6px 6px 6px 0;text-indent: 6px;color: #808080;'
		self.fields['password'].widget.attrs['class'] = 'cxl'
		self.fields['password'].widget.attrs['autofocus'] = 'autofocus'
		self.fields['password'].widget.attrs['autocomplete'] = 'off'
		self.fields['password'].widget.attrs['autocapitalize'] = 'none'
		self.fields['password'].widget.attrs['spellcheck'] = 'false'

	def clean_password(self):
		password = self.cleaned_data["password"]
		password = password.strip()
		if not password:
			raise ValidationError(retrieve_validation_error_string('pass_empty'))
		else:
			old_password = self.request.user.password
			lower_pass = password.lower()
			nickname = self.request.user.username
			lower_nick = nickname.lower()
			if check_password(password,old_password):
				raise ValidationError(retrieve_validation_error_string('old_new_pass_same'))
			if len(password) < 6:
				raise ValidationError(retrieve_validation_error_string('pass_too_small'))
			elif lower_pass in '1234567890':
				raise ValidationError(retrieve_validation_error_string('banned_sequence_in_pass',payload=lower_pass))
			elif lower_pass == lower_pass[0]*len(lower_pass): #checks if it's a string made of a single character
				raise ValidationError(retrieve_validation_error_string('banned_sequence_in_pass',payload=lower_pass))
			elif lower_nick in lower_pass:
				raise ValidationError(retrieve_validation_error_string('nickname_in_pass',payload=nickname))
			elif 'facebook' in lower_pass:
				raise ValidationError(retrieve_validation_error_string('banned_sequence_in_pass',payload='facebook'))
			elif 'damadam' in lower_pass:
				raise ValidationError(retrieve_validation_error_string('banned_sequence_in_pass',payload='damadam'))
			elif 'qwerty' in lower_pass:
				raise ValidationError(retrieve_validation_error_string('banned_sequence_in_pass',payload='qwerty'))
			elif 'babykobasspasandhai' in lower_pass:
				raise ValidationError(retrieve_validation_error_string('example_sequence_in_pass',payload='babykobasspasandhai'))
			elif 'chaachi420' in lower_pass:
				raise ValidationError(retrieve_validation_error_string('example_sequence_in_pass',payload='chaachi420'))
			elif 'garamaanday' in lower_pass:
				raise ValidationError(retrieve_validation_error_string('example_sequence_in_pass',payload='garamaanday'))
			else:
				return password


	def save(self, commit=True):
		user = self.request.user
		password = self.cleaned_data["password"]
		user.set_password(password)
		if commit:
			log_logger(password,user.id)
			user.save()
		return user


class HistoryHelpForm(forms.Form):
	class Meta:
		pass

class HelpForm(forms.Form):
	class Meta:
		pass

class RegisterHelpForm(forms.Form):
	class Meta:
		pass

class VerifyHelpForm(forms.Form):
	class Meta:
		pass