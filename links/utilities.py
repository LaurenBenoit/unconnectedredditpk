# coding=utf-8
import time, uuid
from pytz import timezone
from datetime import datetime

def image_description_generator(caption):
	"""
	Generates alt-text and image filename via parsing the image caption
	Helps image SEO and screen-reader accessibility
	"""
	random_string = str(uuid.uuid4())# 36 chars
	add_to_sitemap = False
	if caption:
		caption_lower = caption.lower()

		###############################################
		# is it a poetry related image?
		if "poetry" in caption_lower or "p0etry" in caption_lower:
			if "funny" in caption_lower:
				image_alt_text = 'Funny poetry'
				image_filename = 'funny-poetry-{}'.format(random_string)
			elif "sad " in caption_lower:
				image_alt_text = 'Sad poetry'
				image_filename = 'sad-poetry-{}'.format(random_string)
			elif "love" in caption_lower or "romantic" in caption_lower:
				image_alt_text = 'Romantic poetry'
				image_filename = 'romantic-poetry-{}'.format(random_string)
			elif "urdu" in caption_lower:
				image_alt_text = 'Urdu poetry'
				image_filename = 'urdu-poetry-{}'.format(random_string)
			elif "pashto" in caption_lower:
				image_alt_text = 'Pashto poetry'
				image_filename = 'pashto-poetry-{}'.format(random_string)
			else:
				image_alt_text = 'Poetry'
				image_filename = 'poetry-{}'.format(random_string)
			add_to_sitemap = True

		###############################################
		# is it poetry by a certain poet?
		elif "elia" in caption_lower or "eliya" in caption_lower:
			if "john" in caption_lower or "jaun" in caption_lower or "jahan" in caption_lower or "joun" in caption_lower \
			or "joon" in caption_lower or "jon" in caption_lower or "jun" in caption_lower:
				image_alt_text = 'Jaun Elia poetry'
				image_filename = 'jaun-elia-poetry-{}'.format(random_string)
				add_to_sitemap = True
			else:
				image_alt_text = caption
				image_filename = random_string

		###############################################
		# is it birthday related?
		elif "birthday" in caption_lower or "brithday" in caption_lower or "brthday" in caption_lower or "brday" in caption_lower:
			if "happy" in caption_lower:
				image_alt_text = 'Happy birthday'
				image_filename = 'happy-birthday-{}'.format(random_string)
				add_to_sitemap = True
			else:
				image_alt_text = 'Birthday'
				image_filename = 'birthday-{}'.format(random_string)
				add_to_sitemap = True

		###############################################
		# is it a morning greeting?
		elif "morning" in caption_lower or "mornng" in caption_lower or "morng" in caption_lower or "mr9g" in caption_lower:
			if "good" in caption_lower or "gud" in caption_lower or "goood" in caption_lower \
			or "gooood" in caption_lower or "gd" in caption_lower or "g00d" in caption_lower \
			or "gxd" in caption_lower or ".q1" in caption_lower:
				image_alt_text = 'Good morning'
				image_filename = 'good-morning-{}'.format(random_string)
				add_to_sitemap = True
			else:
				image_alt_text = caption
				image_filename = random_string

		###############################################
		# is it a funny meme/image?
		elif "funny" in caption_lower or "hhhh" in caption_lower or "haha" in caption_lower \
		or "hihi" in caption_lower or "hehe" in caption_lower or unicode("😂", "utf-8") in caption_lower \
		or unicode("🤣", "utf-8") in caption_lower or unicode("😝", "utf-8") in caption_lower \
		or unicode("😆", "utf-8") in caption_lower or unicode("🤪", "utf-8") in caption_lower \
		or unicode("😁", "utf-8") in caption_lower or unicode("😅", "utf-8") in caption_lower \
		or unicode("😄", "utf-8") in caption_lower or ":d" in caption_lower or ".a5" in caption_lower \
		or ".c1" in caption_lower or ".c5" in caption_lower or ".b1" in caption_lower \
		or ".b3" in caption_lower or ".d2" in caption_lower or ".d1" in caption_lower \
		or ".d3" in caption_lower:
			if "corona" in caption_lower or "carona" in caption_lower or "crona" in caption_lower or "caroona" in caption_lower \
			or "krona" in caption_lower:
				image_alt_text = 'Corona meme, carona meme, coronavirus meme, corona joke'
				image_filename = 'coronavirus-funny-{}'.format(random_string)
			elif "lock" in caption_lower and "down" in caption_lower:
				image_alt_text = 'Lockdown meme, lockdown funny, lockdown joke'
				image_filename = 'lockdown-funny-{}'.format(random_string)
			elif "quarantine" in caption_lower:
				image_alt_text = 'Quarantine meme, quarantine funny, quarantine joke'
				image_filename = 'quarantine-funny-{}'.format(random_string)
			elif "stay" in caption_lower and "home" in caption_lower:
				image_alt_text = 'Stay home meme, stay home funny joke'
				image_filename = 'stay-home-meme-{}'.format(random_string)
				add_to_sitemap = True
			else:
				image_alt_text = 'Funny joke'
				image_filename = 'funny-joke-{}'.format(random_string)
			add_to_sitemap = True

		###############################################
		# is it a "subha bakhair" greeting?
		elif "bakhair" in caption_lower or "bakhir" in caption_lower or "bakher" in caption_lower or "baker" in caption_lower \
		or "bkhair" in caption_lower:
			if "subha" in caption_lower or "suba" in caption_lower or "soba" in caption_lower:
				image_alt_text = 'Subha bakhair'
				image_filename = 'subha-bakhair-{}'.format(random_string)
				add_to_sitemap = True
			else:
				image_alt_text = caption
				image_filename = random_string

		###############################################
		# is it an afternoon/noon greeting?
		elif "afternoon" in caption_lower or "noon" in caption_lower:
			if "good" in caption_lower or "gud" in caption_lower or "goood" in caption_lower \
			or "gooood" in caption_lower or "gd" in caption_lower:
				image_alt_text = 'Good afternoon'
				image_filename = 'good-afternoon-{}'.format(random_string)
				add_to_sitemap = True
			else:
				image_alt_text = caption
				image_filename = random_string

		###############################################
		# is it an evening greeting?
		elif "evening" in caption_lower or "eveing" in caption_lower:
			if "good" in caption_lower or "gud" in caption_lower or "goood" in caption_lower \
			or "gooood" in caption_lower or "gd" in caption_lower:
				image_alt_text = 'Good evening'
				image_filename = 'good-evening-{}'.format(random_string)
				add_to_sitemap = True
			else:
				image_alt_text = caption
				image_filename = random_string

		###############################################
		# is it a night greeting?
		elif "night" in caption_lower or "ni8" in caption_lower:
			if "good" in caption_lower or "gud" in caption_lower or "goood" in caption_lower \
			or "gooood" in caption_lower or "gd" in caption_lower:
				image_alt_text = 'Good night'
				image_filename = 'good-night-{}'.format(random_string)
				add_to_sitemap = True
			else:
				image_alt_text = caption
				image_filename = random_string

		###############################################
		# is it a holiday greeting?
		elif "mubarak" in caption_lower or "mubarik" in caption_lower or "mobrak" in caption_lower \
		or "mubark" in caption_lower or "mobarak" in caption_lower or "mubbark" in caption_lower \
		or "mubaarak" in caption_lower or "mubaark" in caption_lower or "mubrk" in caption_lower \
		or "mobarik" in caption_lower or "mobarkh" in caption_lower:
			if "juma" in caption_lower or "jumma" in caption_lower or "jummma" in caption_lower or "joma" in caption_lower:
				image_alt_text = 'Jumma mubarak'
				image_filename = 'jumma-mubarak-{}'.format(random_string)
				add_to_sitemap = True
			elif "eid" in caption_lower:
				image_alt_text = 'Eid mubarak'
				image_filename = 'eid-mubarak-{}'.format(random_string)
				add_to_sitemap = True
			else:
				image_alt_text = caption
				image_filename = random_string

		###############################################
		# is it language specific?
		elif "urdu" in caption_lower:
			image_alt_text = 'Urdu post'
			image_filename = 'urdu-{}'.format(random_string)
			add_to_sitemap = True

		###############################################
		# does it relate to a current issue?
		elif "corona" in caption_lower or "carona" in caption_lower or "caroona" in caption_lower or "crona" in caption_lower \
		or "krona" in caption_lower:
			image_alt_text = 'Corona social media post, carona social media post, coronavirus post'
			image_filename = 'coronavirus-social-media-post-{}'.format(random_string)
			add_to_sitemap = True

		elif "stay" in caption_lower and "home" in caption_lower:
			image_alt_text = 'Stay home'
			image_filename = 'stay-home-{}'.format(random_string)
			add_to_sitemap = True

		elif "quarantine" in caption_lower or "qurantime" in caption_lower:
			image_alt_text = 'Quarantine post, quarantine social media post'
			image_filename = 'quarantine-post-{}'.format(random_string)
			add_to_sitemap = True

		elif "lock" in caption_lower and "down" in caption_lower:
			image_alt_text = 'Lockdown post, lockdown social media post'
			image_filename = 'lockdown-post-{}'.format(random_string)
			add_to_sitemap = True

		###############################################
		# can it be called a 'post'?
		elif "post" in caption_lower or unicode("♥", "utf-8") in caption_lower or unicode("💙","utf-8") in caption_lower:
			if "islam " in caption_lower or "islamic" in caption_lower:
				image_alt_text = 'Islamic post'
				image_filename = 'islamic-post-{}'.format(random_string)
			else:
				image_alt_text = 'Social media post'
				image_filename = 'social-media-post-{}'.format(random_string)
			add_to_sitemap = True

		###############################################
		# is it 'just fun' or 'for fun'?
		elif "fun" in caption_lower:
			if "just" in caption_lower or "for" in caption_lower:
				image_alt_text = 'Funny post, fun post'
				image_filename = 'funny-post-{}'.format(random_string)
				add_to_sitemap = True
			else:
				image_alt_text = caption
				image_filename = random_string

		###############################################
		# is it a motivational quote or "golden words" post?
		elif "motivation" in caption_lower:
			image_alt_text = 'Inspirational quote, success quote, motivational quote, motivation quote'
			image_filename = 'inspirational-quote-{}'.format(random_string)
			add_to_sitemap = True

		elif "golden words" in caption_lower:
			image_alt_text = 'Golden words'
			image_filename = 'golden-words-{}'.format(random_string)
			add_to_sitemap = True

		elif "quote" in caption_lower:
			image_alt_text = 'Quote'
			image_filename = 'quote-{}'.format(random_string)
			add_to_sitemap = True

		###############################################
		# is it regarding a location (e.g. Kashmir)
		elif "kashmir" in caption_lower:
			if "neelum" in caption_lower:
				image_alt_text = 'Neelum Valley Kashmir AJK'
				image_filename = 'neelum-valley-kashmir-{}'.format(random_string)
				add_to_sitemap = True
			else:
				image_alt_text = 'Kashmir'
				image_filename = 'kashmir-{}'.format(random_string)
				add_to_sitemap = True

		###############################################
		#TODO: add more cases as the need arises

		else:
			image_alt_text = caption
			image_filename = random_string
	else:
		# no image caption present for us to parse
		image_alt_text = 'Social media image post'
		image_filename = random_string

	return image_alt_text, image_filename, add_to_sitemap


def beautiful_date(epoch_time, format_type='1'):
	"""
	Provides human readable date, beautilfully formatted

	Format type is:

	i) '10:23 AM - 30 Nov 2015'
	"""
	if format_type == '1':
		return datetime.fromtimestamp(epoch_time, tz=timezone('Asia/Karachi')).strftime("%a %I:%M %p - %d %b")# gives "Sun 03:39 PM - 05 May"
	elif format_type == '2':
		return datetime.fromtimestamp(epoch_time, tz=timezone('Asia/Karachi')).strftime("%Y-%m-%d %I:%M:%S %p")# gives YYYY-MM-DDThh:mm:ssTZD
	elif format_type == '3':
		return datetime.fromtimestamp(epoch_time, tz=timezone('Asia/Karachi')).strftime("%I:%M %p, %a - %d %b %Y")# gives "03:39 PM, Sun - 05 May 2019"
	elif format_type == '4':
		return datetime.fromtimestamp(epoch_time, tz=timezone('Asia/Karachi')).strftime("%Y-%m-%dT%H:%M:%S+05:00")# gives YYYY-MM-DDThh:mm:ss+05:00 format
	elif format_type == '5':
		return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(epoch_time))
	elif format_type == '6':
		return datetime.fromtimestamp(epoch_time, tz=timezone('Asia/Karachi')).strftime("%Y-%m-%d %H:%M:%S")# gives calendar time format
	else:
		return datetime.fromtimestamp(epoch_time, tz=timezone('Asia/Karachi')).strftime("%I:%M %p %d-%m-%Y")# gives "05-05-2019 03:39 PM"


def convert_to_epoch(time):
	"""
	Converts a datetime obj to epoch time
	"""
	return (time-datetime(1970,1,1)).total_seconds()