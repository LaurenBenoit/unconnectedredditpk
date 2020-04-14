import re
from django import forms
from score import COMPETITION_ROUND
from redis4 import check_participant_video_url, check_participant_mob_num

class YoutubeVideoSubmissionForm(forms.Form):
	"""
	"""
	youtube_url = forms.CharField(max_length=600,error_messages={'required': 'Youtube ka link likhna zaruri hai'})
	phonenumber = forms.RegexField(max_length=20, required=False, regex=re.compile("^[0-9]+$"),\
		error_messages={'invalid':'Mobile number mein sirf digits likhein, e.g. 03451234567'})

	class Meta:
		fields = ('youtube_url','phonenumber')

	def __init__(self, *args, **kwargs):
		self.user_id = kwargs.pop('user_id',None)
		super(YoutubeVideoSubmissionForm, self).__init__(*args, **kwargs)		
		self.fields['youtube_url'].widget.attrs['style'] = 'width:90%;max-width:360px;border:1px solid #C8C8C8;height:36px;border-radius:6px;background:#fff5f5;padding-left:4px;'
		self.fields['phonenumber'].widget.attrs['style'] = 'width:90%;max-width:360px;border:1px solid #C8C8C8;height:36px;border-radius:6px;background:#fff5f5;padding-left:4px;'
		self.fields['youtube_url'].widget.attrs['class'] = 'mt cl sp'
		self.fields['phonenumber'].widget.attrs['class'] = 'mt cl sp'
		self.fields['youtube_url'].widget.attrs['autocomplete'] = 'off'
		self.fields['phonenumber'].widget.attrs['autocomplete'] = 'off'


	def clean_youtube_url(self):
		youtube_url, own_id = self.cleaned_data.get('youtube_url'), self.user_id

		#Check if youtube_url associated with another entry
		previously_submitted = check_participant_video_url(video_url=youtube_url)
		if previously_submitted:
			raise forms.ValidationError('Ye YouTube ka link pehlay bhi submit ho chuka hai')

		return youtube_url


	def clean_phonenumber(self):
		phonenumber, own_id = self.cleaned_data.get('phonenumber'), self.user_id

		#Check if phonenumber associated with another entry
		previously_submitted = check_participant_mob_num(mob_num=phonenumber, participant_id=own_id)
		if previously_submitted: 
			raise forms.ValidationError('Ye number kisi aur user ka hai, different number likhien!')

		return phonenumber