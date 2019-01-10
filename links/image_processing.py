# coding=utf-8

# import arabic_reshaper
# from bidi.algorithm import get_display
import imagehash
import StringIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image, ImageFont, ImageDraw, ImageFile, ImageEnhance, ExifTags
ImageFile.LOAD_TRUNCATED_IMAGES = True
from redis7 import already_exists
from page_controls import PERSONAL_GROUP_IMG_WIDTH
from score import MIN_PUBLIC_IMG_WIDTH



def enhance_image(image):
	enhancer = ImageEnhance.Brightness(image)
	enhancer = enhancer.enhance(1.06)
	enhancer2 = ImageEnhance.Contrast(enhancer)
	enhancer2 = enhancer2.enhance(1.02)
	enhancer3 = ImageEnhance.Color(enhancer2)
	return enhancer3.enhance(1.10)

def compute_avg_hash(image):
	"""
	This is a 'diff perceptual hash' - it gives us an image's unique signature in hex format

	The function is erroneously named - it used to be an 'avg perceptual hash' computation but we've changed that
	"""
	# small_image_bw = image.resize((8,8), Image.ANTIALIAS).convert("L")
	# pixels = list(small_image_bw.getdata())
	# avg = sum(pixels) / len(pixels)
	# bits = "".join(map(lambda pixel: '1' if pixel > avg else '0', pixels)) #turning the image into string of 0s and 1s
	# photo_hash = int(bits, 2).__format__('16x').upper()
	# return photo_hash
	return str(imagehash.dhash(image))

def resize_image(image, max_width=None):
	if not max_width:
		max_width = PERSONAL_GROUP_IMG_WIDTH#400
	resize_ranges = [max_width, int(0.9*max_width),int(0.8*max_width), int(0.7*max_width),int(0.6*max_width),int(0.5*max_width),int(0.4*max_width),\
	int(0.3*max_width),int(0.2*max_width)]
	img_width, img_height = image.size
	if img_width < resize_ranges[8]:
		benchmark_width = resize_ranges[8]
	elif img_width < resize_ranges[7]:
		benchmark_width = resize_ranges[8]
	elif img_width < resize_ranges[6]:
		benchmark_width = resize_ranges[7]
	elif img_width < resize_ranges[5]:
		benchmark_width = resize_ranges[6]
	elif img_width < resize_ranges[4]:
		benchmark_width = resize_ranges[5]
	elif img_width < resize_ranges[3]:
		benchmark_width = resize_ranges[4]
	elif img_width < resize_ranges[2]:
		benchmark_width = resize_ranges[3]
	elif img_width < resize_ranges[1]:
		benchmark_width = resize_ranges[2]
	elif img_width < resize_ranges[0]:
		benchmark_width = resize_ranges[1]
	else:
		benchmark_width = resize_ranges[0]
	wpercent = (benchmark_width/float(img_width))
	hsize = int((float(img_height)*float(wpercent)))
	image_resized = image.resize((benchmark_width,hsize), Image.ANTIALIAS)
	return image_resized, image_resized.size[0],image_resized.size[1]

	
def reorient_image(im):
	try:
		image_exif = im._getexif()
		image_orientation = image_exif[274]
		if image_orientation in (2,'2'):
			return im.transpose(Image.FLIP_LEFT_RIGHT)
		elif image_orientation in (3,'3'):
			return im.transpose(Image.ROTATE_180)
		elif image_orientation in (4,'4'):
			return im.transpose(Image.FLIP_TOP_BOTTOM)
		elif image_orientation in (5,'5'):
			return im.transpose(Image.ROTATE_90).transpose(Image.FLIP_TOP_BOTTOM)
		elif image_orientation in (6,'6'):
			return im.transpose(Image.ROTATE_270)
		elif image_orientation in (7,'7'):
			return im.transpose(Image.ROTATE_270).transpose(Image.FLIP_TOP_BOTTOM)
		elif image_orientation in (8,'8'):
			return im.transpose(Image.ROTATE_90)
		else:
			return im
	except (KeyError, AttributeError, TypeError, IndexError):
		return im


def make_thumbnail(img,quality,caption=None,already_resized=None):
	img = img.convert("RGB") if img.mode != 'RGB' else img
	img = enhance_image(img)
	#############
	if not already_resized:
		# JS users' images are resized in JS to 400x400. Non-JS users get to 300x300 below
		img.thumbnail((300, 300),Image.ANTIALIAS)
	# fillcolor = (255,255,255)#(255,0,0)red#(0,100,0)green#(0,0,0)black#(0,0,255)blue
	# shadowcolor = (0,0,0)
	# text = caption
	# draw_text(img,text,fillcolor,shadowcolor)
	#############
	thumbnailString = StringIO.StringIO()
	if quality:
		img.save(thumbnailString, 'JPEG', optimize=True,quality=80)
	else:
		img.save(thumbnailString, 'JPEG', optimize=True,quality=40)
	newFile = InMemoryUploadedFile(thumbnailString, None, 'temp.jpg', 'image/jpeg', thumbnailString.len, None)
	return newFile


def prep_image(img,quality,max_width=None, already_resized=None):
	img = img.convert("RGB") if img.mode != 'RGB' else img
	if already_resized:
		img_width, img_height = img.size
	else:
		img, img_width, img_height = resize_image(img,max_width=max_width)
	img = enhance_image(img)
	thumbnailString = StringIO.StringIO()
	if quality:
		img.save(thumbnailString, 'JPEG', optimize=True,quality=70)
	else:
		img.save(thumbnailString, 'JPEG', optimize=True,quality=15)
	newFile = InMemoryUploadedFile(thumbnailString, None, 'temp.jpg', 'image/jpeg', thumbnailString.len, None)
	return newFile, img_width, img_height



def clean_image_file(image,quality=None,already_reoriented=None, already_resized=None):
	"""
	Used in PhotoReplyView (unreleased), PicsChatUploadView, AdImageView (unreleased)
	"""
	image = Image.open(image)
	if float(image.height)/image.width > 7.0:
		return False
	else:
		image = image if already_reoriented else reorient_image(image)
		return make_thumbnail(img=image,quality=quality,already_resized=already_resized)


def process_group_image(image, quality=None, already_resized=None, already_reoriented=None):
	"""
	Used by post_image_in_personal_group() in group_views.py and by PublicGroupView(), PrivateGroupView() in mehfil_views.py
	"""
	image = Image.open(image)
	if float(image.height)/image.width > 7.0:
		return None, 'too_high', 'too_high'
	else:
		image = image if already_reoriented else reorient_image(image)
		return prep_image(image,quality,max_width=PERSONAL_GROUP_IMG_WIDTH,already_resized=already_resized)


def process_public_image(image, quality=None, already_resized=None, already_reoriented=None):
	"""
	Used by upload_public_photo() in views.py
	"""
	image = Image.open(image)
	img_width = image.width
	if img_width < MIN_PUBLIC_IMG_WIDTH:
		return None, 'too_narrow', None, None
	elif float(image.height)/img_width > 7.0:
		return None, 'too_high', None, None
	else:
		image = image if already_reoriented else reorient_image(image)
		avghash = compute_avg_hash(image) #to ensure a duplicate image hasn't been posted before
		exists = already_exists(avghash)
		if exists:
			return image, None, exists, avghash
		else:
			image_file, img_width, img_height = prep_image(image,quality,max_width=PERSONAL_GROUP_IMG_WIDTH,already_resized=already_resized)
			return image_file, img_height, None, avghash


def clean_image_file_with_hash(image,quality=None,categ=None, caption=None, already_resized=None, already_reoriented=None):
	"""
	Used in ecomm.py
	"""
	if image:
		image = Image.open(image)
		if categ != 'ecomm' and float(image.height)/image.width > 7.0:
			return None, 'too_high', 'too_high'
		if not already_reoriented:
			image = reorient_image(image) #so that it appears the right side up
		avghash = compute_avg_hash(image) #to ensure a duplicate image hasn't been posted before
		exists = already_exists(avghash, categ)
		if exists:
			return image, avghash, exists
		else:
			image = make_thumbnail(img=image,quality=quality,caption=caption, already_resized=already_resized)
			return image, avghash, None
	else:
		return (0,-1)

################### DRAW TEXT ON IMAGE ###################

# def text_with_stroke(draw,width,height,line,font,fillcolor,shadowcolor):
#     reshaped_text = arabic_reshaper.reshape(line)
#     line = get_display(reshaped_text)
#     draw.text((width-1, height), line, font=font, fill=shadowcolor)
#     draw.text((width+1, height), line, font=font, fill=shadowcolor)
#     draw.text((width, height-1), line, font=font, fill=shadowcolor)
#     draw.text((width, height+1), line, font=font, fill=shadowcolor)
#     draw.text((width, height), line, font=font, fill=fillcolor)

# def draw_text(img, text, fillcolor, shadowcolor, position='bottom'):
#     text = text.strip()
#     base_width, base_height = img.size #The image's size in pixels, as 2-tuple (width,height)
#     font_size = base_width/15
#     if font_size < 13:
#         print "bad result"
#     font = ImageFont.truetype("/usr/share/fonts/truetype/droid/DroidNaskh-Bold.ttf", font_size)
#     ################Converting single-line text into multiple lines#################
#     line = ""
#     lines = []
#     width_of_line = 0
#     number_of_lines = 0
#     for token in text.split():
#         token = token+' '
#         token_width = font.getsize(token)[0]
#         if width_of_line+token_width < base_width:
#             line+=token
#             width_of_line+=token_width
#         else:
#             lines.append(line)
#             number_of_lines += 1
#             width_of_line = 0
#             line = ""
#             line+=token
#             width_of_line+=token_width
#     if line:
#         lines.append(line)
#         number_of_lines += 1
#     #################################################################################
#     draw = ImageDraw.Draw(img)#(background)
#     if position == 'top':
#         y = 2
#         for line in lines:
#             width, height = font.getsize(line)
#             x = (base_width - width) / 2
#             text_with_stroke(draw,x,y,line,font,fillcolor,shadowcolor)
#             y += height
#     elif position == 'middle':
#         font_height = font.getsize('|')[1]
#         text_height = font_height * number_of_lines
#         y = (base_height-text_height)/2
#         for line in lines:
#             width, height = font.getsize(line)
#             x = (base_width - width) / 2
#             text_with_stroke(draw,x,y,line,font,fillcolor,shadowcolor)
#             y += height
#     else:
#         font_height = font.getsize('|')[1]
#         y = base_height-(font_height+3)#0
#         for line in reversed(lines):
#             width, height = font.getsize(line)
#             x = (base_width - width) / 2
#             text_with_stroke(draw,x,y,line,font,fillcolor,shadowcolor)
#             y -= (height+2)