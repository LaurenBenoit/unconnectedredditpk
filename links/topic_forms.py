import re
from django import forms
from django.core.urlresolvers import get_resolver
from django.core.exceptions import ValidationError
from score import MAX_HOME_SUBMISSION_SIZE, MAX_TOPIC_SIZE, MIN_TOPIC_SIZE, MIN_TOPIC_DESCRIPTION_SIZE, RIGHT_ALIGNMENT_THRESHOLD_RATIO
from forms import repetition_found, strip_zero_width_characters, is_urdu
from redis6 import human_readable_time


def is_alpha_numeric(string):
	"""
	Performs validation checks on provided string
	"""
	string_tokens = string.split()
	alpha_numeric = True
	for token in string_tokens:
		if not token.isalnum():
			alpha_numeric = False
			break
	return alpha_numeric


def will_topic_collide_with_urls(string):
	"""
	Checks if a topic name collides with one of our existing URLs

	Reason being all topic pages are of the sort: https://example.com/<topic> which can easily collide with an existing url
	Avoid creating new single-word urls after topics are live
	"""
	final_urls = []
	for url in set(v[1] for k,v in get_resolver(None).reverse_dict.iteritems()):
		first_token = url.split('/')[0]
		if first_token:
			final_urls.append(first_token)
	if string in final_urls:
		return True
	else:
		return False


def topic_urlizer(topic):
	"""
	"""
	return '-'.join(topic.lower().split())


class CreateTopicform(forms.Form):
	"""
	Renders and validates the topic creation form
	"""
	topic = forms.CharField(max_length=MAX_TOPIC_SIZE,widget=forms.Textarea(attrs={'autofocus': 'autofocus','autocomplete': 'off',\
		'autocapitalize':'off','spellcheck':'false','maxlength':MAX_TOPIC_SIZE}),error_messages={'required': 'Topic likhna zaruri hai'})
	description = forms.CharField(widget=forms.Textarea(attrs={'cols':40,'rows':3,'autofocus': 'autofocus','autocomplete': 'off',\
		'autocapitalize':'off','spellcheck':'false','maxlength':MAX_HOME_SUBMISSION_SIZE}),\
	error_messages={'required': 'Topic ke barey mein likhna zaruri hai'})
	topic_owner_id = forms.IntegerField(widget=forms.Textarea(attrs={'cols':40,'rows':3,'autocomplete': 'off','autocapitalize':'off',\
		'spellcheck':'false'}),error_messages={'invalid': "Enter valid ID",'required':"An ID is required!"})
	
	# example = forms.CharField(widget=forms.Textarea(attrs={'cols':40,'rows':3,'autofocus': 'autofocus','autocomplete': 'off',\
	# 	'autocapitalize':'off','spellcheck':'false','maxlength':MAX_HOME_SUBMISSION_SIZE}),\
	# error_messages={'required': 'Example likhna zaruri hai'})
	# expiry = forms.
	# categ_tag1 = forms.
	# categ_tag2 = forms.
	# categ_tag3 = forms.


	def __init__(self,*args,**kwargs):
		super(CreateTopicform, self).__init__(*args,**kwargs)
		self.fields['topic'].widget.attrs['style'] = 'width:100%;border-bottom-right-radius:7px;border-bottom-left-radius:7px;height:45px;border:none;background-color:#fff4f1;overflow: auto;padding:10px;box-sizing: border-box;'
		self.fields['topic'].widget.attrs['class'] = 'cxl sp lsp'
		self.fields['topic'].widget.attrs['placeholder'] = 'Topic likhein ...'
		############################################################################
		self.fields['description'].widget.attrs['style'] = 'width:100%;border-bottom-right-radius:7px;border-bottom-left-radius:7px;height:220px;border:none;background-color:#f2fafd;overflow: auto;padding:10px;box-sizing: border-box;'
		self.fields['description'].widget.attrs['class'] = 'cxl sp lsp'
		self.fields['description'].widget.attrs['placeholder'] = 'Maslan is mein kis kissam ki posts hon gi?'
		############################################################################
		self.fields['topic_owner_id'].widget.attrs['style'] = 'width:100%;border-bottom-right-radius:7px;border-bottom-left-radius:7px;height:45px;border:none;background-color:#e9fcf6;overflow: auto;padding:10px;box-sizing: border-box;'
		self.fields['topic_owner_id'].widget.attrs['class'] = 'cxl sp lsp'
		self.fields['topic_owner_id'].widget.attrs['placeholder'] = 'User ID likhein ...'


	def clean_topic(self):
		topic = self.cleaned_data.get("topic")
		topic = strip_zero_width_characters(topic)
		len_topic = len(topic)
		if will_topic_collide_with_urls(topic):
			raise ValidationError('"{}" topic ka naam allowed nahi hai, koi aur choose karein'.format(topic))
		elif len_topic > MAX_TOPIC_SIZE:
			raise ValidationError('Topic mein {} se zyada chars nahi ho saktey, ap ne {} chars likhey'.format(MAX_TOPIC_SIZE,len_topic))
		elif len_topic < MIN_TOPIC_SIZE:
			raise ValidationError('Topic mein tafseel ka izafa karein')
		is_alnum = is_alpha_numeric(topic)
		if not is_alnum:
			raise ValidationError('Topic mein sirf english letters ya numbers likhein')
		topic_url = topic_urlizer(topic)
		return topic, topic_url


	def clean_description(self):
		description = self.cleaned_data.get("description")
		description = strip_zero_width_characters(description)
		len_description = len(description)
		if ' ' not in description:
			raise ValidationError('Spaces zarur daalein')
		elif len_description > MAX_HOME_SUBMISSION_SIZE:
			raise ValidationError('Is mein {} se zyada chars nahi ho saktey, ap ne {} chars likhey'.format(MAX_HOME_SUBMISSION_SIZE,len_description))
		elif len_description < MIN_TOPIC_DESCRIPTION_SIZE:
			raise ValidationError('Is mein tafseel ka izafa karein')
		# is_alnum = is_alpha_numeric(topic)
		# if not is_alnum:
		# 	raise ValidationError('Topic mein sirf english letters ya numbers likhein')
		description = re.sub(r'\n\s*\n', '\n', description)# collapsing multiple new lines into 1
		return description

	# def clean_example(self):
	# 	example = self.cleaned_data.get("example")
	# 	example = strip_zero_width_characters(example)
	# 	example = re.sub(r'\n\s*\n', '\n', example)
	# 	return example

	def clean_topic_owner_id(self):
		return self.cleaned_data.get("topic_owner_id")

		


class SubmitInTopicForm(forms.Form):
	description = forms.CharField(widget=forms.Textarea(attrs={'cols':40,'rows':3,'autocomplete': 'off',\
		'autocapitalize':'off','spellcheck':'false','maxlength':MAX_HOME_SUBMISSION_SIZE}),\
	error_messages={'required': 'Pehlay kuch likhein, phir SUBMIT dabain'})
	# sk = forms.CharField(required=False)


	def __init__(self,*args,**kwargs):
		self.user_id = kwargs.pop('user_id',None)
		super(SubmitInTopicForm, self).__init__(*args,**kwargs)
		############################################################################
		self.fields['description'].widget.attrs['style'] = 'margin:0;border-radius:0;width:100%;height:150px;border:none;background-color:#ecfffb;overflow: auto;padding:10px;box-sizing: border-box'
		self.fields['description'].widget.attrs['class'] = 'cxl sp lsp'
		self.fields['description'].widget.attrs['placeholder'] = 'Post likhein ...'
		self.fields['description'].widget.attrs['aria-label'] = 'Add new submission ...'


	def clean(self):
		section_id, section = '1', 'home'
		user_id = self.user_id
		data = self.cleaned_data
		description = data.get("description")
		description = description.strip() if description else None
		description = strip_zero_width_characters(description)
		if not description or description.isspace():
			raise forms.ValidationError('Yahan likhna zaruri hai')
		else:
			len_desc = len(description)
			if len_desc > MAX_HOME_SUBMISSION_SIZE+150:
				# if post is too long, short circuit the rest of the cleaning method
				raise forms.ValidationError('Itni lambi post submit nahi hoti kiyun ke parhney waley bore ho jatey hain')
			else:
				description = re.sub(r'\n\s*\n', '\n', description)# collapsing multiple new lines into 1
				lines = description.split('\n')
				if len(lines) > 20:
					raise forms.ValidationError('Itni zyada new lines nahi dalein!')
				elif repetition_found(section=section,section_id=section_id,user_id=user_id, target_text=description):
					raise forms.ValidationError('Milti julti cheezain nahi likhein')
				else:
					if len_desc < 15:
						raise forms.ValidationError('Itni choti post nahi submit kar sakte')
					elif len_desc > MAX_HOME_SUBMISSION_SIZE:
						raise forms.ValidationError('Post mein {0} chars se ziyada na likhein. Ap ne {1} chars likhey'.format(MAX_HOME_SUBMISSION_SIZE,len_desc))
					data['alignment'] = '2' if is_urdu(description) >= RIGHT_ALIGNMENT_THRESHOLD_RATIO else '1'
					data['description'] = description
					return data