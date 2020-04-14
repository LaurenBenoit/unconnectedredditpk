from django import template
from links.score import COMPETITION_ROUND
from links.redis4 import already_entered_competition

register = template.Library()

@register.assignment_tag(takes_context=True)
def can_show_competition_announcement(context):
	user_id = context['request'].user.id
	if user_id:
		# only show to those who have not taken it
		return not already_entered_competition(user_id, round_num=COMPETITION_ROUND)
	else:
		return False#assume non-logged in users should not be shown the survey