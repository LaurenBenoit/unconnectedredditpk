from django import template
from links.redis4 import show_survey

register = template.Library()

@register.assignment_tag(takes_context=True)
def has_taken_survey(context):
	user_id = context['request'].user.id
	if user_id:
		return show_survey(user_id)
	else:
		return True#assume non-logged in users have taken survey