from django.contrib import admin
from .models import Link, Vote, Photo, PhotoVote, PhotoComment, PhotoStream, ChatInbox, ChatPic, ChatPicMessage, UserProfile, \
UserSettings, Publicreply, GroupBanList, HellBanList, Seen, Unseennotification, GroupInvite, GroupSeen, UserFan, \
Salat, SalatInvite, Logout, Video, VideoComment
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
#these will appear in the admin panel
class LinkAdmin(admin.ModelAdmin): pass
admin.site.register(Link, LinkAdmin)

class PhotoStreamAdmin(admin.ModelAdmin): pass
admin.site.register(PhotoStream, PhotoStreamAdmin)

class UserFanAdmin(admin.ModelAdmin): pass
admin.site.register(UserFan, UserFanAdmin)

class SalatAdmin(admin.ModelAdmin): pass
admin.site.register(Salat, SalatAdmin)

class SalatInviteAdmin(admin.ModelAdmin): pass
admin.site.register(SalatInvite, SalatInviteAdmin)

class VideoAdmin(admin.ModelAdmin): pass
admin.site.register(Video, VideoAdmin)

class VideoCommentAdmin(admin.ModelAdmin): pass
admin.site.register(VideoComment, VideoCommentAdmin)

class PhotoAdmin(admin.ModelAdmin): pass
admin.site.register(Photo, PhotoAdmin)

class PhotoCommentAdmin(admin.ModelAdmin): pass
admin.site.register(PhotoComment, PhotoCommentAdmin)

class PhotoVoteAdmin(admin.ModelAdmin): pass
admin.site.register(PhotoVote, PhotoVoteAdmin)

# class GroupCreateAdmin(admin.ModelAdmin): pass
# admin.site.register(Group, GroupCreateAdmin)

class GroupBanListAdmin(admin.ModelAdmin): pass
admin.site.register(GroupBanList, GroupBanListAdmin)

class HellBanListAdmin(admin.ModelAdmin): pass
admin.site.register(HellBanList, HellBanListAdmin)

class GroupInviteAdmin(admin.ModelAdmin): pass
admin.site.register(GroupInvite, GroupInviteAdmin)

class LogoutAdmin(admin.ModelAdmin): pass
admin.site.register(Logout, LogoutAdmin)

class GroupSeenAdmin(admin.ModelAdmin): pass
admin.site.register(GroupSeen, GroupSeenAdmin)

class UnseennotificationAdmin(admin.ModelAdmin): pass
admin.site.register(Unseennotification, UnseennotificationAdmin)

# class ReplyAdmin(admin.ModelAdmin): pass
# admin.site.register(Reply, ReplyAdmin)

class PublicreplyAdmin(admin.ModelAdmin): pass
admin.site.register(Publicreply, PublicreplyAdmin)

class SeenAdmin(admin.ModelAdmin): pass
admin.site.register(Seen, SeenAdmin)

class VoteAdmin(admin.ModelAdmin): pass
admin.site.register(Vote, VoteAdmin)

class ChatInboxAdmin(admin.ModelAdmin): pass
admin.site.register(ChatInbox, ChatInboxAdmin)

class ChatPicAdmin(admin.ModelAdmin): pass
admin.site.register(ChatPic, ChatPicAdmin)

class ChatPicMessageAdmin(admin.ModelAdmin): pass
admin.site.register(ChatPicMessage, ChatPicMessageAdmin)

class UserProfileInline(admin.StackedInline):
	model = UserProfile
	can_delete = False

class UserSettingsInline(admin.StackedInline):
	model = UserSettings
	can_delete = False

class UserProfileSettingsAdmin(UserAdmin):
	inlines=[
	UserProfileInline,
	UserSettingsInline, 
	]

admin.site.unregister(get_user_model())
admin.site.register(get_user_model(), UserProfileSettingsAdmin)