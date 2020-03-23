# -*- coding: utf-8 -*-
from django.conf.urls import patterns, include, url
from django.contrib.auth.decorators import login_required as auth
from django.contrib import admin
from django.views.generic.base import TemplateView
from urls_unauth import urlpatterns as urlpatterns_unauth
from urls_maint import urlpatterns as urlpatterns_maint
# from urls_advertiser import urlpatterns as urlpatterns_adv
from urls_retention import urlpatterns as urlpatterns_retention
# from urls_ads import urlpatterns as urlpatterns_ads
from urls_feedback import urlpatterns as urlpatterns_feedback
from urls_groups import urlpatterns as urlpatterns_groups
from urls_sharing import urlpatterns as urlpatterns_sharing
from urls_mehfil import urlpatterns as urlpatterns_mehfil
from urls_verification import urlpatterns as urlpatterns_verification
from urls_judgement import urlpatterns as urlpatterns_judgement
from urls_voting import urlpatterns as urlpatterns_voting
from urls_search import urlpatterns as urlpatterns_search
from urls_push_notif import urlpatterns as urlpatterns_push_notif
from urls_direct_response import urlpatterns as urlpatterns_direct_response
from urls_followers import urlpatterns as urlpatterns_followers
from urls_topics import urlpatterns as urlpatterns_topics
from links.installment_calculator import calculator
from links.webhooks import webhook_event
from links.views import user_profile_photo, welcome_reply, reauth, comment_pk, reply_to_photo, public_reply_view, link_create_pk, \
welcome_pk, sitemap, show_online_users,perm_redirect_to_home, logout_rules, best_home_page, home_page, best_home_redirect, \
best_photos_list, fresh_photos_list, display_link_detail, home_redirect, submit_text_post, display_image_comments, profile_pk, \
faces_pages, error, share_content, sharing_help, photo_sitemap, hide_comment, photo_sitemap_of_sitemaps, top_photo_help, \
reset_password, content_detail_view, display_text_comments, manage_user, manage_user_help, cut_user_score, kick_user, show_clones, \
hell_ban, remove_hell_ban,photo_top_trenders, user_profile_photos, missing_page, hide_jawab,photo_page, photo_redirect, \
upload_public_photo, website_rules, redirect_to_profile_photos,public_photo_upload_denied, user_profile_photos_redirect, \
display_old_image_comments, content_sitemap_of_sitemaps, private_or_expired, photo_detail_view, content_sitemap, kick_ban_user,\
show_templates, more_options
from links.views import FacesHelpView, UserActivityView, AboutView, ContactView, PrivacyPolicyView, PhotosHelpView, \
EmoticonsHelpView, LogoutHelpView, WelcomeView, WelcomeMessageView, LogoutPenaltyView, UserSettingsEditView, \
UserProfileDetailView, UserProfileEditView, LinkDeleteView, HelpView, PhotoShareView, RegisterHelpView, VerifyHelpView, \
HistoryHelpView
from links.redirection_views import redirect_to_content, main_navbar
from links.number_verification import verify_user_number
from links.voting_views import user_vote_history, user_old_vote_history
from links.announcement_views import export_survey_results, corona_virus, benefits_of_data_mode, survey

admin.autodiscover()

urlpatterns = patterns('',
	############################# home page ################################
	url(r'^$', best_photos_list, name='home'),
	###################### sitemaps and robots.txt #########################
	url(r'^sitemap\.xml$', sitemap, name='sitemap'),
	url(r'^robots\.txt/$', TemplateView.as_view(template_name="robots.txt", content_type='text/plain')),
	###################### legacy sitemap urls #############################
	url(r'^photo_sitemap_(?P<cohort>\d+)\.xml$', photo_sitemap, name='photo_sitemap'),
	url(r'^photo_sitemap_of_sitemaps\.xml$', photo_sitemap_of_sitemaps, name='photo_sitemap_of_sitemaps'),
	###################### latest sitemap urls #############################
	url(r'^content_sitemap_(?P<cohort>\d+)\.xml$', content_sitemap, name='content_sitemap'),
	url(r'^content_sitemap_of_sitemaps\.xml$', content_sitemap_of_sitemaps, name='content_sitemap_of_sitemaps'),
	########################################################################
	url(r'^administer_me/', include(admin.site.urls)),
	url(r'^redirect/text/$', auth(home_redirect), name='redirect_to_home'),
	url(r'^redirect/text/(?P<pk>\d+)/$', auth(home_redirect), name='redirect_to_home'),
	url(r'^redirect-to-content/$', auth(redirect_to_content), name='redirect_to_content'),
	url(r'^text/fresh-list/$', auth(home_page), name='fresh_text'),
	url(r'^redirect/text/best-list/$', auth(best_home_redirect), name='best_home_redirect'),
	url(r'^redirect/text/best-list/(?P<pk>\d+)/$', auth(best_home_redirect), name='best_home_redirect'),
	url(r'^text/best-list/$', auth(best_home_page), name='best_home_page'),
	url(r'^vun/$',verify_user_number, name="verify_user_number"),
	url(r'^calculator/$', auth(calculator), name='calculator'),
	url(r'^whook/$', webhook_event, name='webhook_event'),
	#########################################Logging out############################################
	url(r'^are_you_sure/$', auth(logout_rules), name="bahirniklo"),
	url(r'^logout_penalty/$', LogoutPenaltyView.as_view(), name='logout_penalty'),
	################################################################################################
	url(r'^logout_help/$', LogoutHelpView.as_view(), name='logout_help'),
	url(r'^user/(?P<slug>[\w.@+-]+)/$', redirect_to_profile_photos, name='profile_photos_redirect'),
	url(r'^user/likes/history/$', auth(user_vote_history), name='user_vote_history'),
	url(r'^user/likes/history/old/$', auth(user_old_vote_history), name='user_old_vote_history'),
	url(r'^user/(?P<slug>[\w.@+-]+)/(?P<type>[\w.@+-]+)/$', user_profile_photos, name='profile'),
	url(r'^user/redirect/(?P<slug>[\w.@+-]+)/(?P<list_type>[\w.@+-]+)/$', user_profile_photos_redirect, name='profile_photos_redirect'),
	url(r'^usrp/(?P<slug>[\w.@+-]+)/(?P<key>\d+)/$', profile_pk, name='profile_pk'),
	url(r'^user_prof/(?P<slug>[\w.@+-]+)/(?P<photo_pk>\d+)/$', user_profile_photo, name='user_profile_photo'),
	url(r'^user_prof/(?P<slug>[\w.@+-]+)/(?P<photo_pk>\d+)/(?P<is_notif>\d+)/$', user_profile_photo, name='user_profile_photo'),
	url(r'^users/(?P<slug>[\w.@+-]+)/$', UserProfileDetailView.as_view(), name='user_profile'),
	url(r'^edit_settings/$', auth(UserSettingsEditView.as_view()), name='edit_settings'),
	url(r'^edit_profile/$', auth(UserProfileEditView.as_view()), name='edit_profile'),
	url(r'^missing/$', missing_page, name='missing_page'),
	url(r'^error/$', error, name='error'),
	url(r'^online_kon/$', auth(show_online_users), name='online_kon'),
	url(r'^reauth/$', auth(reauth), name='reauth'),
	url(r'^users/(?P<slug>[\w.@+-]+)/activity/$', auth(UserActivityView.as_view()), name='user_activity'),
	url(r'^comment/(?P<pk>\d+)/$', display_old_image_comments, name='old_comment'),
	url(r'^comment/(?P<pk>\d+)/(?P<origin>\d+)/$', display_old_image_comments, name='old_comment'),

	url(r'^comments/image/(?P<pk>\d+)/$', display_image_comments, name='comment'),
	url(r'^comments/image/(?P<pk>\d+)/(?P<origin>\d+)/$', display_image_comments, name='comment'),

	url(r'^comments/text/(?P<parent_id>\d+)/$', auth(display_text_comments), name='publicreply_view'),
	url(r'^comments/text/(?P<parent_id>\d+)/(?P<origin>\d+)/$', auth(display_text_comments), name='publicreply_view'),

	url(r'^comment_pk/(?P<pk>\d+)/$', comment_pk, name='comment_pk'),
	url(r'^comment_pk/(?P<pk>\d+)/(?P<origin>\d+)/$', comment_pk, name='comment_pk'), #origin is an optional variable
	url(r'^comment_pk/(?P<pk>\d+)/(?P<origin>\d+)/(?P<ident>\d+)/$', comment_pk, name='comment_pk'), #origin and ident are an optional variable
	############################################################################################################################
	url(r'^content/(?P<pk>\d+)/$', content_detail_view, name='content_detail_view'),
	url(r'^content/(?P<pk>\d+)/(?P<origin>\d+)/$', content_detail_view, name='content_detail_view'),
	url(r'^content/(?P<pk>\d+)/(?P<obj_type>[\w.@+-]+)/$', content_detail_view, name='content_detail_view'),
	url(r'^content/(?P<pk>\d+)/(?P<origin>\d+)/(?P<obj_type>[\w.@+-]+)/$', content_detail_view, name='content_detail_view'),

	url(r'^photo_detail/(?P<pk>\d+)/$', photo_detail_view, name='photo_detail'),
	url(r'^photo_detail/(?P<pk>\d+)/(?P<origin>\d+)/$', photo_detail_view, name='photo_detail'),
	
	url(r'^text/detail/(?P<link_id>\d+)/$', auth(display_link_detail), name='display_link_detail'),
	url(r'^photo_reply/(?P<pk>\d+)/(?P<ident>\d+)/$', auth(reply_to_photo), name='reply_to_photo'),
	###################################################################################
	url(r'^photo/redirect/(?P<list_type>[\w.@+-]+)/(?P<pk>\d+)/$', auth(photo_redirect), name='redirect_to_photo'),
	url(r'^photo/redirect/(?P<list_type>[\w.@+-]+)/$', auth(photo_redirect), name='redirect_to_photo'),
	url(r'^photo/top-trenders/$', auth(photo_top_trenders), name='top_photo'),
	url(r'^photo/top-trenders/help/$', auth(top_photo_help), name='top_photo_help'),
	url(r'^photo/(?P<list_type>[\w.@+-]+)/$', photo_page, name='photo'),
	url(r'^topphotos/$', best_photos_list, name='best_photo'),
	###################################################################################
	url(r'^navigate/$', main_navbar, name='main_navbar'),
	url(r'^more/$', auth(more_options), name='more_options'),
	######################################################## Content Sharing ###################################################
	url(r'^share/$', auth(share_content), name='share_content'),
	url(r'^share/help/$', auth(sharing_help), name='sharing_help'),
	url(r'^share/photo/templates/$', auth(show_templates), name='show_templates'),
	url(r'^share/photo/upload-denied/$', auth(public_photo_upload_denied), name='public_photo_upload_denied'),
	url(r'^share/photo/upload/$', auth(upload_public_photo), name='upload_public_photo'),
	url(r'^share/text/$', auth(submit_text_post), name='link_create'),
	url(r'^share/text/redirect/$', auth(link_create_pk), name='link_create_pk'),
	url(r'^share/text/redirect/first-time/$', auth(link_create_pk), name='first_time_link'),
	############################################################################################################################
	url(r'^photos_help/(?P<slug>[\w.@+-]+)/(?P<pk>\d+)/$', PhotosHelpView.as_view(), name='photos_help'),
	url(r'^khushamdeed/$', auth(WelcomeView.as_view()), name='welcome'),
	url(r'^welcome/(?P<pk>\d+)/$', auth(welcome_pk), name='welcome_pk'),
	url(r'^damadam_par_khushamdeed/$', auth(welcome_reply), name='welcome_reply'),
	url(r'^khushamdeed/(?P<option>\d+)/$', auth(WelcomeMessageView.as_view()), name='welcome_message'),
	url(r'^history/$', auth(HistoryHelpView.as_view()), name='history_help'),
	url(r'^help/$', HelpView.as_view(), name='help'),
	url(r'^register_login/$', perm_redirect_to_home, name='register_login'),
	url(r'^login_walkthrough/$', perm_redirect_to_home, name='login_walkthrough'),
	url(r'^reset_pass/$', auth(reset_password), name='reset_password'),
	url(r'^verify_help/$', perm_redirect_to_home, name='verify_help'),
	url(r'^emoticons_help/$', EmoticonsHelpView.as_view(), name='emoticons_help'),
	url(r'^faces/$', FacesHelpView.as_view(), name='faces'),
	url(r'^facespage/$', faces_pages, name='faces_pages'), 
	url(r'^photo_share/(?P<pk>\d+)/(?P<loc>\d+)/$', PhotoShareView.as_view(), name='photo_share'),
	url(r'^photo_share/(?P<pk>\d+)/(?P<loc>\d+)/(?P<slug>[\w.@+-]+)/$', PhotoShareView.as_view(), name='photo_share'),
	url(r'^privacy_policy/$', PrivacyPolicyView.as_view(), name='privacy_policy'),
	url(r'^about/$', AboutView.as_view(), name='about'),
	url(r'^website-rules/$', website_rules, name='website_rules'),
	url(r'^contact/$', ContactView.as_view(), name='contact'),
	##################################################Publicreply####################################
	url(r'^jawab/(?P<parent_id>\d+)/$', auth(public_reply_view), name='old_publicreply_view'),
	#################################################################################################
	url(r'^reply/hide/(?P<publicreply_id>\d+)/(?P<link_id>\d+)/(?P<origin>\d+)/$', auth(hide_jawab), name='hide_jawab'),
	url(r'^comment/hide/(?P<comment_id>\d+)/(?P<photo_id>\d+)/(?P<origin>\d+)/$', auth(hide_comment), name='hide_comment'),
	#################################################################################################
	url(r'^manage_user/$', auth(manage_user),name='manage_user'),
	url(r'^manage_user_help/$', auth(manage_user_help),name='manage_user_help'),
	url(r'^cut_user_score/$', auth(cut_user_score),name='cut_user_score'),
	url(r'^kick_user/$', auth(kick_user),name='kick_user'),
	url(r'^kick_ban_user/$', auth(kick_ban_user),name='kick_ban_user'),
	url(r'^show_clones/$', auth(show_clones),name='show_clones'),
	url(r'^hell-ban/add/$', auth(hell_ban),name='hell_ban'),
	url(r'^hell-ban/remove/$', auth(remove_hell_ban),name='remove_hell_ban'),
	########################################## Survey Related ########################################
	url(r'^survey/answers/$', auth(survey),name='survey'),
	url(r'^survey/export/$', auth(export_survey_results), name='export_survey_results'),
	url(r'^corona-virus/$', corona_virus, name='corona_virus'),
	url(r'^corona-virus/(?P<lang>[\w.@+-]+)/$', corona_virus, name='corona_virus'),
	url(r'^announcement/data-mode/$', benefits_of_data_mode, name='benefits_of_data_mode'),
		############################# Permanent redirects ############################################
	url(r'^freshphotos/$', auth(fresh_photos_list), name='fresh_photos_list'),
	url(r'^unauth/$',perm_redirect_to_home, name='perm_redirect_to_home'),
	url(r'^izzat_ya_bezati/(?P<pk>\d+)/(?P<origin>\d+)/$',perm_redirect_to_home, name='perm_redirect_to_home'),
	url(r'^izzat_ya_bezati/(?P<pk>\d+)/(?P<origin>\d+)/(?P<slug>[\w.@+-]+)/$',perm_redirect_to_home, name='perm_redirect_to_home'),
	url(r'^content/limited/$', auth(private_or_expired), name='private_or_expired'),
)
# urlpatterns += urlpatterns_ecomm
# urlpatterns += urlpatterns_ads
# urlpatterns += urlpatterns_adv
urlpatterns += urlpatterns_feedback
urlpatterns += urlpatterns_unauth
urlpatterns += urlpatterns_retention
urlpatterns += urlpatterns_maint
urlpatterns += urlpatterns_groups
urlpatterns += urlpatterns_sharing
urlpatterns += urlpatterns_mehfil
urlpatterns += urlpatterns_verification
urlpatterns += urlpatterns_judgement
urlpatterns += urlpatterns_voting
urlpatterns += urlpatterns_search
urlpatterns += urlpatterns_push_notif
urlpatterns += urlpatterns_direct_response
urlpatterns += urlpatterns_followers
urlpatterns += urlpatterns_topics# must always be the last thing object to be concatenated

handler404 = 'links.error_views.not_found'
handler500 = 'links.error_views.server_error'
handler403 = 'links.error_views.permission_denied'
handler400 = 'links.error_views.bad_request'