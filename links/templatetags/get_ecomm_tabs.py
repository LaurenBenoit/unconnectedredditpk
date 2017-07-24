from django import template

register = template.Library()

@register.inclusion_tag(file_name='classifieds_tabs.html')
def ecomm_tabs(origin=None, exchange=None, is_feature_phone=None):
	return {'origin':origin,'is_feature_phone':is_feature_phone,\
		'exchange':exchange}