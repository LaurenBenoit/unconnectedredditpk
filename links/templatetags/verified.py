# -*- coding: utf-8 -*-
from django import template
from django.db import models
from django.contrib.auth.models import User

register = template.Library()

FEMALES = [u'Š0nîКa_Pārììï', 'poja', 'FaRyAaL_GoHaR', 'sangat', 'sumaira.khan', 'fasiha_93', 'Princess_asi', 'Aysha.khan', 'Seep', 'khazaen', 'noshihaider', 'Phool', 'Jannat_ch' , 'hayakhan', 'sandul', 'Annu', 't', 'Alveena_rani476', 'AnfaaL', 'Bisma.Azam', 'zahra', 'Anjilina', 'Aamina','Manhi','rabiaali', 'Sana', 'Aishmato', 'Jaana', 'ayla', 'Maleenjaslee', 'Hoor', 'Tani_789', 'Sanam_khan', 'Esha-ali-subhani', 'dipika', 'Pomi', 'Hina', 'July', 'Juhikhan', 'gori', 'samreen', 'Farheen', 'pholi', 'AlinaNoor_786', 'rabika', 'mehro', 'Sheeery', 'Maleenjalee','RimiShah','Remsha','sherikhokhar5','Roshni_malik_53','Rahat',]

@register.assignment_tag(takes_context=True)
def check_user_is_verified(context):
	user = context['request'].user
	#print "user is %s" % user
	#print "user in females is %s" % (user.username in VIP)
	return user and user.username in FEMALES