from django import template
from links.score import VOTING_DRIVEN_CENSORSHIP, VOTING_DRIVEN_PIXELATION

register = template.Library()

@register.inclusion_tag(file_name='content/photo_object.html')
def photo_object(pid, ooid, img_url, vsc, img_thumb ,upload_time, machine_time, oun, origin, static_url, caption, is_fbs=None, \
	av_url=None, home_hash='',block_time_remaining=None,is_star=None, show_uname_credentials=True, show_report=True, show_trending=False,\
	exclude_detail_url=False, lazyload_idx=1, ratio=None, nht=None, ot=None, aud=None, exp=None, is_new=None, et=None,time_now=None, alt_txt=''):
	return {'vsc':float(vsc) if vsc else 0,'oun':oun, 'static_url':static_url, 'VDC':(VOTING_DRIVEN_CENSORSHIP+1),'VDP':(VOTING_DRIVEN_PIXELATION+1),\
	'cap':caption,'av_url':av_url,'ut':upload_time,'img_url':img_url,'img_thumb':img_thumb,'is_fbs':is_fbs,'home_hash':home_hash, 'origin':origin, \
	'show_avatar':'block' if av_url else 'none','block_time_remaining':block_time_remaining,'ooid':ooid, 'pid':pid,'alt_txt':alt_txt, 'is_star':is_star,\
	'show_uname_credentials':show_uname_credentials, 'report_display':'block' if show_report else 'none','lazyload_idx':lazyload_idx, 'nht':nht,\
	'ex_url':True if exclude_detail_url else False, 'mt':machine_time, 'show_trending':True if show_trending == '1' else False, 'ratio':ratio,\
	'aud':aud, 'exp':exp, 'ot':ot, 'is_new':is_new, 'et':et,'time_now':time_now}# a value of '6' for 'show_trending' implies the image trended