from django import template
from links.redis4 import show_survey

register = template.Library()

@register.assignment_tag(takes_context=True)
def can_show_survey(context):
	# return False
	user_id = context['request'].user.id
	if user_id:
		# only show to those who have not taken it
		return show_survey(user_id)
	else:
		return False#assume non-logged in users should not be shown the survey