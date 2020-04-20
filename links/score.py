# coding=utf-8
MAX_BIO_SIZE = 1000
REPLY_OBJECT_TTL = 604800# 7 days set as ttl for how long a direct response object lives
MAX_HOME_SUBMISSION_SIZE = 750
MAX_HOME_REPLY_SIZE = 350# i.e. Publicreply
MAX_PHOTO_COMMENT_SIZE = 350# i.e. PhotoComment
MAX_PHOTO_CAPTION_SIZE = 100
THRESHOLD_WORLD_AGE = 17# world age after which a user is considered an 'experienced' user
POST_HISTORY_TTL = 259200# 3 days - time length a user's post visitors are logged for
PUBLIC_TEXT_QUALITY_THRESHOLD_LENGTH = 40# text-length below which a public text post is considered 'low quality'
PREFIX_TEXT_LENGTH = 43# useful when splitting a sentence into prefix and postfix parts (for 'reference' display)
NUM_ACTIVITY_ITEMS_PER_PAGE = 10# num items to be shown in reply history
###############################################################################################################
COMPETITION_ROUND = '1'# control competition rounds from here
###############################################################################################################
VOTING_CLOSED_ARCHIVE_OVERFLOW_TIME = 2419200# i.e. 28 days. This is the amount of time closed-voting objs are kept around for 'like_prob' or 'handpicked_prob' analysis
################################################ Follow Feature Related Variables ##################################
REMOVAL_RATE_LIMIT_TIME = 300# 5 mins in seconds
RATELIMIT_REMOVED_FOLLOWER = 172800
SHORT_RATELIMIT_UNFOLLOWER = 180#2 mins
LONG_LIVED_POST_TIME = 86400 # 1 day in seconds
SHORT_LIVED_POST_TIME = 900#15 mins in seconds TO DO:
TTL_FOLLOWER_LIST = 691200# 8 days, in seconds - must be > PUBLIC_SUBMISSION_TTL. This is TTL for 'Follower List' (a list of user's followers, saved in redis)
TTL_FOLLOWER_STRING = 777600# 9 days, in seconds - must be > TTL_FOLLOWER_LIST. This is TTL for 'Follower String' (a string obj of user's followers, concatenated with ":", saved in redis)
###############################################################################################################
PUBLIC_SUBMISSION_TTL = 604800#7 days set as ttl for links and photos submitted to Damadam (i.e. redis object TTL)
UPLOAD_PHOTO_REQ = 30 #score below which you're not allowed photo uploads
NUM_TRENDING_PHOTOS = 200 #how many trending photos to keep in a sorted set for users' viewing?
NUM_SUBMISSION_ALLWD_PER_DAY = 150#num of home and photo posts allowed in one day
CONTENT_SHARING_SHORT_RATELIMIT = 45#amount of time to wait between sharing posts (time pooled between home and photos) 
CONTENT_SHARING_LONG_RATELIMIT = 86400# 1 day in seconds
HOURS_LOOKBACK_FOR_CHECKING_CONTENT_CLONES = 50#how many hours to look back when reporting a content clone (used in get_content_history in judgement_views.py)
CONTEST_LENGTH = 604800 #Length of time to calculate top trending photo contributors
RIGHT_ALIGNMENT_THRESHOLD_RATIO = 0.5 #if a text has more 'urdu' characters than this ratio, right align it
################################################ Topics ################################################
TOPIC_LIFELINE = 1728000#20 days - i.e. how long a topic should exist even if it has no visits
TOPIC_SUBMISSION_TTL = 604800#7 days set as ttl for content submitted into a topic
TOPIC_UNSUB_LOCKING_TIME = 7200#2 hours is how long a subscriber must stay inside a topic after subscribing to it
MAX_TOPIC_SIZE = 80
MIN_TOPIC_SIZE = 3
MIN_TOPIC_DESCRIPTION_SIZE = 20
################################################ Judgement Related Variables ##################################
USER_REBAN_ACTION_RATELIMIT = 86400#1 day is the length of time a user should be rate limited from re-blocking a target (right after unblocking them)
USER_UNBAN_ACTION_RATELIMIT = 86400#1 day is the length of time a user should be rate limited from unblocking a target (right after blocking them)
###############################################################################################################
TRENDER_RANKS_TO_COUNT = 20 #of top trenders to be shown
# SEARCH_FEATURE_THRESHOLD = 100# REMOVE
# SUPER_UPVOTE = 20# REMOVE
# PERMANENT_RESIDENT_SCORE = 300#REMOVE
# SUPER_DOWNVOTE = -20# REMOVE
# PHOTO_CASE_COMPLETION_BONUS = 6#REMOVE
GIBBERISH_PUNISHMENT_MULTIPLIER = 5#REMOVE
CITIES = ["Rawalpindi","Islamabad"]#REMOVE
SHARE_ORIGIN = {'1':'fresh_photos','3':'user_albums'}#REMOVE
SHARED_PHOTOS_CEILING = 120#REMOVE
PHOTO_DELETION_BUFFER = 15#REMOVE
VOTE_TEXT = {'1':'<span style="font-size:80%;color:#009940;"> ne barri si <b>jhappi</b> di</span><br>',\
'-1':'<span style="font-size:80%;color:#F4511E;"> ne bharey bazar mein <b>chupair</b> mari</span><br>',\
'2': '<span style="font-size:80%;color:#009940;"> ne zordar <b>jhappi</b> di <b>(+20)</b></span><br>',\
'-2': '<span style="font-size:80%;color:#F4511E;"> ne <b>chupair</b> mr mr ke nani yad kra di <b>(-20)</b></span><br>',\
'3': '<span style="font-size:80%;color:#009940;"> ko ye photo <b>zabrdast</b> lagi</span><br>',\
'-3': '<span style="font-size:80%;color:#F4511E;"> ko ye photo <b>bekaar</b> lagi</span><br>',\
'4':'<span style="font-size:80%;color:#009940;"> ne iski shot pe <b>taliyan</b> bajaien</span><br>',\
'-4':'<span style="font-size:80%;color:#F4511E;"> ne isko ghuma ke <b>balla</b> mara</span><br>',\
'5': '<span style="font-size:80%;color:#009940;"> ne iske <b>six</b> pe chalangein lagaien <b>(+20)</b></span><br>',\
'-5': '<span style="font-size:80%;color:#F4511E;"> ne isko <b>andey</b> pe out kr diya <b>(-20)</b></span><br>'}#REMOVE
###############################################################################################################
THUMB_HEIGHT = 38
MIN_PUBLIC_IMG_WIDTH = 315# this number must belong to this interval: [450, 405, 360, 315, 270, 225, 180, 135, 90] (equal to resize_ranges in image_processing.py)
MAX_PUBLIC_IMG_WIDTH = 450
###############################################################################################################
FBS_VERIFICATION_WAIT_TIME = 86400# amount of time (1 day) a free basics person has to wait before mobile verification is allowed
FBS_PUBLIC_PHOTO_UPLOAD_RL = 900#amount of time an FBS user has to wait before being allowed to upload a public photo again. MUST be greater than CONTENT_SHARING_SHORT_RATELIMIT
###############################################################################################################
VOTE_SPREE_ALWD = 25# number of votes allowed on link objects within a small time window before cooldown begins (applied separately to photo voting too)
UPVOTE = 2#number to add to user score
DOWNVOTE = -2#number to subtract from user score
VOTING_DRIVEN_CENSORSHIP = -15# at what total vote count should a photo be completely disappeared
VOTING_DRIVEN_PIXELATION = -7# at what total vote count should a photo be pixellated
###############################################################################################################
BAYESIAN_PROB_THRESHOLD_FOR_VOTE_NERFING = 0.3# if a voter shows a bias of at least (or greater than) this magnitude, their vote counts for zilch!
UPPER_RELATIONSHIP_UVOTE_CUTOFF = 4# upper threshold for 'score' used when doing a sequential scan of UVOTER_AFFINITY sorted set
UPPER_RELATIONSHIP_DVOTE_CUTOFF = 4# upper threshold for 'score' used when doing a sequential scan of DVOTER_AFFINITY sorted set
MEANINGFUL_VOTING_SAMPLE_SIZE = 10# threshold used to determine whether a 'voting relationship' should be investigated or not
NUM_VOTES_TO_TGT = 5# a target user must have received these many votes from voter to make calculating their Bayesian affinity worthwhile (upvotes and downvotes both)
###############################################################################################################
MICRO_CACHE_TTL = 15# useful for micro caching some fast changing keys in groups (do a ctrl+f in redis6 to see examples)
PRIVATE_GROUP_MAX_TITLE_SIZE = 150 #more than 150 chars not allowed
PRIVATE_GROUP_MAX_MEMBERSHIP = 50
PUBLIC_GROUP_MAX_TITLE_SIZE = 150 #more than 150 chars not allowed
PUBLIC_GROUP_MAX_RULES_SIZE = 500 #more than 500 chars not allowed
PUBLIC_GROUP_REPLY_LENGTH = 500
NUM_PUBLIC_GROUPS_OWNED_SHOWN_ON_PROFILE = 6#how many public groups to show on user profile
PRIVATE_GROUP_REPLY_LENGTH = 500

###### Mehfil list ######
TOTAL_LIST_SIZE = 80
MEHFIL_LIST_PAGE_SIZE = 20
#########################

###### Officer applications in public groups ######
PUBLIC_GROUP_OFFICER_APPLICATION_ANSWER_LEN = 200# each answer in officer application is going to be this many chars in length
MAX_OFFICER_APPOINTMENTS_ALLWD = 3 #num of officers one ID can be
MAX_ARCHIVED_OFFICER_APPS_PER_GROUP = 4#when the same user submits an officer app to the same group again and again, how many should we keep in the user history?
OFFICER_APPLICATION_EXPIRY_TIME = 259200# 3 days
OFFICER_APPLICATIONS_RATE_LIMIT = 345600# 4 days - must ALWAYS be greater than 'OFFICER_APPLICATION_EXPIRY_TIME'
MIN_GRP_MEMBERSHIP_AGE_FOR_REQUESTING_GRP_OFFICERSHIP = 86400#1 day
MIN_APP_MEMBERSHIP_AGE_FOR_REQUESTING_GRP_OFFICERSHIP = 604800#7 days
OFFICER_APP_ARCHIVE_EXPIRY_TIME = 10368000#4 months
GROUP_OFFICER_QUESTIONS = {'1':'Ap mehfil ka mahol khush gawar rakhney mein owner ki kya kya help karo ge?',\
'2':'Ap is mehfil ko daily kitna time do ge?'}
###################################################

########## Invites in groups ##########
GROUP_INVITE_LOCK_DURATION = 1209600#2 weeks - use this key to disallow reinviting the same user again and again
INVITER_PRIVATE_INVITE_LOCK_DURATION = 259200#3 days - use this key to disallow reinviting by the same user again and again (even to different groups)
INVITER_PUBLIC_INVITE_LOCK_DURATION = 259200#3 days - use this key to disallow reinviting by the same user again and again (even to different groups)
CANCEL_PUBLIC_INVITE_AFTER_TIME_PASSAGE = 259200#3 days after inviting, a public group owner can cancel their invite
CANCEL_PRIVATE_INVITE_AFTER_TIME_PASSAGE = 86400#1 day after inviting, a private group owner can cancel their invite
PRIVATE_GROUP_INVITE_TTL = 604800#7 days ttl for private group invites. Must be shorter than INVITE_LOCK_DURATION and longer than CANCEL_PRIVATE_INVITE_AFTER_TIME_PASSAGE to work
PUBLIC_GROUP_INVITE_TTL = 604800#7 days ttl for public group invites. Must be shorter than INVITE_LOCK_DURATION and longer than CANCEL_PUBLIC_INVITE_AFTER_TIME_PASSAGE to work
MAX_OWNER_INVITES_PER_PUBLIC_GROUP = 30 #num users an owner can invite into a group within a week
MAX_OWNER_INVITES_PER_PRIVATE_GROUP = 30 #num users a priv mehfil owner can invite
MAX_OFFICER_INVITES_PER_PUBLIC_GROUP = 10 #num users all officers can invite into a group
MAX_MEMBER_INVITES_PER_PRIVATE_GROUP = 10 # num users a priv mehfil member can invite
#######################################

########## Group transactions #########
MIN_MEMBERSHIP_AGE_FOR_REQUESTING_GRP_OWNERSHIP = 172800#2 days
GROUP_TRANSACTION_RATE_LIMIT = 2592000# number of days (30) to rate limit the participants of a successfully concluded group transaction
GROUP_AGE_AFTER_WHICH_IT_CAN_BE_TRANSFERRED = 864000# group must be at least 10 days in age before it can be transferred
FOLLOW_UP_REQUEST_RATE_LIMIT = 604800#7 days rate limit for re-requesting group transfer from the same group owner
#######################################

######## Public/Private group creation ########
USER_AGE_AFTER_WHICH_PUBLIC_MEHFIL_CAN_BE_CREATED = 604800# age requirement is 7 days in seconds
PUBLIC_GROUP_COST = 5000 # cost of buying a public group
PRIVATE_GROUP_CREATION_RATE_LIMIT = 14400#4 hrs
PUBLIC_GROUP_CREATION_RATE_LIMIT = 604800#7 days

####### Group topic changing rate limits #######
TOPIC_SHORT_RATE_LIMIT = 1800#30 mins rate limiting
TOPIC_LONG_RATE_LIMIT = 86400#1 day rate limiting
RULES_CHANGE_RATE_LIMIT = 86400#1 day rate limiting
NUM_TOPIC_CHANGE_ATTEMPTS_ALLOWED = 3 # num of topic change 'failed' attempts in groups after which the user is rate limited
MAX_TIME_BETWEEN_TOPIC_CHANGE_ATTEMPTS = 300#if less than 5 mins between topic change attempts, increment the 'attempts' counter
MAX_TIME_BETWEEN_RULE_CHANGE_ATTEMPTS = 300#if less than 5 mins between rule change attempts, increment the 'attempts' counter
EXCESSIVE_ATTEMPTS_TO_CHANGE_TOPIC_RATE_LIMIT = 1200#20 min rate limit if user tries excessive amount of times to change topic
EXCESSIVE_ATTEMPTS_TO_CHANGE_RULES_RATE_LIMIT = 1200#20 min rate limit if user tries excessive amount of times to change rules
NUM_RULES_CHANGE_ATTEMPTS_ALLOWED = 4 # num of rules change 'failed' attempts in groups after which the user is rate limited
################################################

####### Group messaging thresholds #######
GROUP_GREEN_DOT_CUTOFF = 60# if seen in last 60 seconds, show green dot
GROUP_IDLE_DOT_CUTOFF = 210# if seen later than 60 but before 210, show idle dot
MSGS_TO_SHOW_IN_GROUP = 35# number of messages to show in groups (public and private both)
DELETION_THRESHOLD = 70# number of messages to keep in group list (before deletion sets in)
NUM_TO_DELETE = 35#number of messages to delete once DELETION_THRESHOLD HITS
PUBLIC_GROUP_MESSAGE = 2 # score for messaging in public group
PRIVATE_GROUP_MESSAGE = 2 # score for messaging in privte group
##########################################

########## Group exiting ##########
PUBLIC_GROUP_EXIT_LOCK = 7200# lock public mehfil enterer from exiting for 2 hours (they can however be kicked)
PRIVATE_GROUP_EXIT_LOCK = 2400# lock private mehfil enterer from exiting for 40 mins (they can however be kicked)
GROUP_REENTRY_LOCK = 54000#lock group reentry (after exiting) for 15 hours (both public and private groups)
###################################

############ Group feedback ############
MIN_MEMBERSHIP_AGE_FOR_GIVING_PUBLIC_GRP_FEEDBACK = 108000#30 hours (a little more than a day)
GROUP_FEEDBACK_SIZE = 200 #num of chars in feedback provided to kicked users or by users to admins
FEEDBACK_TTL = 1209600#2 weeks;num seconds feedback stays alive for
FEEDBACK_RATELIMIT = 259200#3 days; num seconds user is rate limited from sending feedback again
FEEDBACK_CACHE = 86400#1 day, num seconds the feedback list is cached for
########################################

MAX_PUNCTUATION_REPETITIONS_IN_MEHFIL_TOPIC = 2# how many times can '.' or '-' (etc) occur in a mehfil topic
GROUP_MEMBERS_PER_PAGE = 50 #num of group members per page, shown in a mehfil's group members page
GROUP_VISITORS_PER_PAGE = 50 #num of group members per page, shown in a mehfil's group members page

POINTS_DEDUCTED_WHEN_GROUP_SUBMISSION_HIDDEN = 2
PRIVATE_GROUP_COST = 500 # cost of buying a private group
PUBLIC_GROUP_MAX_SELLING_PRICE = 0#(PUBLIC_GROUP_COST*2)-1
PUBLIC_GROUP_MIN_SELLING_PRICE = 0#PUBLIC_GROUP_COST#PUBLIC_GROUP_COST*0.3
GROUP_HARD_DELETION_CUTOFF = 2479680#30 days old groups are targets of hard deletion (i.e. full deletion)
GROUP_SOFT_DELETION_CUTOFF = 604800#7 days old groups are target of soft deletion (i.e. emptying content)

PUBLICREPLY = 2 #score for leaving publicreply on a home 'link'
###############################################################################################################
PHOTOS_WITH_SEARCHED_NICKNAMES = 5
#REPORTED_CASE_COMPLETION_BONUS = 0#15#turning case completion bonus to '0' for now (revert if defenders complain)

PHOTO_REPORT_PROMPT = {'0':'Report rehne dein','1':'Photo mein porn hai','2':'Photo mein firqa wariyat hai','3':'Photo mein khoon kharaba ya aziyat hai',\
'4':'Photo dehshat gardi ki himayat kar rahi hai','11':'Photo apkey barey mein ghalat rumor phela rahi hai'}# 9 and 10 keys of this dictionary MUST MATCH 9 and 10 keys of TEXT_REPORT_PROMPT
GET_PHOTO_REPORT_HELP_LABEL = {'0':'','1':'photo_nudity_or_sex','2':'photo_firqa_wariyat','3':'photo_bloodshed','4':'photo_terrorism',\
'5':'photo_screenshot','6':'photo_low_quality','7':'photo_wrong_title','8':'photo_title_solicitation','9':'photo_plagiarism',\
'10':'photo_double_posting','11':'photo_rumor'}

TEXT_REPORT_PROMPT = {'0':'Report rehne dein','1':'1 on 1 mein bulaney ki post ki hai','2':'Dhamkiyan di hain','3':'Sex or romance ki bheek mangi hai',\
'4':'Betukki typing yani spamming ki hai (e.g. "sadfsadfa")','5':'Repeat honay wali cheez likhi hai (e.g. "سلام, سلام, سلام")',\
'7':'Firqa wariyat wali post ki hai','8':'Dehshat gardi ki himayat ki hai','12':'Fake news phelai hai (e.g. "Admin users ke phone number bech raha hai")'}
GET_TEXT_REPORT_HELP_LABEL = {'0':'','1':'text_fan_to_fan','2':'text_abuse','3':'text_vulgar','4':'text_crap','5':'text_repeating','6':'text_chat',\
'7':'text_firqa_wariyat','8':'text_terrorism','9':'text_plagiarism','10':'text_double_posting','11':'text_romantic_solicitation','12':'text_rumor',\
'13':'text_multi_new_line'}

VIDEO_REPORT_PROMPT = {'0':'Report rehne dein','1':'Video mein porn hai','2':'Video mein firqa wariyat hai','3':'Video mein khoon kharaba ya aziyat hai',\
'4':'Video dehshat gardi ki himayat kar rahi hai','5':'Video apkey bare mein ghalat rumor phela rahi hai'}
GET_VIDEO_REPORT_HELP_LABEL = {'0':'','1':'video_nudity_or_sex','2':'video_firqa_wariyat','3':'video_bloodshed','4':'video_terrorism',\
'5':'video_rumor'}

MEHFIL_REPORT_PROMPT = {'0':'Report rehne dein','1':'Topic ganda hai','2':'Topic mein abuse hai','3':'Topic mein firqa wariyat hai',\
'4':'Topic mein jhooti afwah hai','5':'Rules gandey hain','6':'Rules mein abuse hai','7':'Rules mein firqa wariyat hai',\
'8':'Rules mein jhooti afwah hai'}# do NOT add '9' and '10' (those are reserved for TEXT_REPORT_PROMPT and PHOTO_REPORT_PROMPT)
GET_MEHFIL_REPORT_HELP_LABEL = {'0':'','1':'mehfil_topic_vulgar','2':'mehfil_topic_abuse','3':'mehfil_topic_firqa_wariyat',\
'4':'mehfil_topic_rumor','5':'mehfil_rules_vulgar','6':'mehfil_rules_abuse','7':'mehfil_rules_firqa_wariyat','8':'mehfil_rules_rumor'}

PROFILE_REPORT_PROMPT = {'0':'Report rehne dein','1':'Nickname ganda hai','2':'Nickname mein abuse hai','3':'Nickname mein firqa wariyat hai',\
'4':'Profile photo gandi hai','5':'Profile photo mein screenshot hai','6':'Profile photo mein firqa wariyat hai','7':'Profile photo mein jhooti afwah hai'}# do NOT add '9' and '10'
GET_PROFILE_REPORT_HELP_LABEL = {'0':'','1':'username_vulgar','2':'username_abuse','3':'username_firqa_wariyat','4':'profile_pic_vulgar',\
'5':'profile_pic_screenshot','6':'profile_pic_firqa_wariyat','7':'profile_pic_rumor'}

EXIT_DISCOUNT = 1
KICK_DISCOUNT = 0.5
GROUP_SIZE_PERCENTILE_CUTOFF = 0.95#what percentile of groups to consider when ranking public groups
###############################################################################################################
ON_FBS_PHOTO_THRESHOLD = 200000
OFF_FBS_PHOTO_THRESHOLD = 10000000
LEAST_CLICKS = 5
MOST_CLICKS = 45
MEDIUM_CLICKS = 15
MOST_DURATION = 336 # Two weeks in hours
LEAST_DURATION = 168 # One week in hours
TWILIO_NOTIFY_THRESHOLD = 20
###############################################################################################################
NUMBER_VERIFICATION_THRESHOLD = 0
NUMBER_VERIFICATION_BONUS = 500
###############################################################################################################
PW = 'F1l2O3c4C5i6N7a8U9c1I2n3I4h5I6l7I8p9I1l2I3f4I5c6A7t8I9o1N2'
###############################################################################################################
PERSONAL_GROUP_NOTIF_IVT_RATE_LIMIT = 86400#1 day breather between sending notification invites in personal groups
PERSONAL_GROUP_NOTIF_RATE_LIMIT = 1800#rate limit a person for 30 mins after they've sent a push notification
PERSONAL_GROUP_ERR = {'too_high':'Ye photo buhut lambi hai, koi aur chunein',\
'mismatch':'Rabta munqata ho gaya, phir se karien','generic':'Internet ka rabta munqata ho gaya, phir se karien'}
PERSONAL_GROUP_DEFAULT_SMS_TXT = ' ne apko Damadam ki 1 on 1 mein bulaya'
EXTRA_PADDING = 20 #used to adjust image sizes in cases where CSS uses box-sizing:border-box property
PERSONAL_GROUP_SAVE_MSGS = {'err2':'Ye msg mita diye janey ki waja se save nahi ho saka',\
'err3':'Ye msg hide honay ki waja se save nahi ho saka','err4':'Ye msg apkey save karney se pehlay delete ho gya',\
'err5':'Ap is msg ko save kar sakein ge ','err1':'Ye msg save nahi ho sakta','msg1':'Msg save kar dia gya',\
'err6':'Ye msg save karney ke liye apney pichley saved msgs mein se kuch delete karein',\
'err7':'Ye msg pehley bhi save kia ja chuka hai, dubara nahi ho sakta',\
'err8':'Kharabi ho geyi, phir se koshish karein','err9':'Ap ko ye msg save karney ki ijazat nahi'}
###############################################################################################################
# helps in setting TTL on rate limits set on abusive users. Each key defines 'level' of offense, values are ttl
BAN_REASON = {'flooding':'tez tez likhna (flooding or spamming)'}
RATELIMIT_TTL = {'0':60*4,'1':60*10,'2':60*30,'3':60*60*2,'4':60*60*8,'5':60*60*24,'6':60*60*24*3,'7':60*60*24*7,'8':60*60*24*30}
SUPER_FLOODING_THRESHOLD = 3 # 3 seconds on avg between multiple sentences
FLOODING_THRESHOLD = 5 # 5 seconds on avg between multiple sentences
LAZY_FLOODING_THRESHOLD = 7 # 7 seconds on avg between multiple sentences
SHORT_MESSAGES_ALWD = 4
MERCH = { 
'1': {'price':'4200' ,'discounted_price':'4200', 'points_cost': '5000', 'discount':'Rs. 400', 'name':'Qmobile Noir X29' }, \
'2': {'price':'4500' ,'discounted_price':'4500', 'points_cost': '5000', 'discount':'Rs. 500', 'name':'QMobile Noir X33'}, \
'3': {'price':'7800' ,'discounted_price':'7800', 'points_cost': '5000', 'discount':'Rs. 680', 'name':'QMobile Noir i8i'}, \
'4': {'price':'6570' ,'discounted_price':'6570', 'points_cost': '5000', 'discount':'Rs. 730', 'name':'QMobile Noir i6 Metal One'}, \
'5': {'price':'8100','discounted_price':'8100', 'points_cost': '5000', 'discount':'Rs. 900', 'name':'Samsung J1 Mini Prime'}, \
'6': {'price':'9630','discounted_price':'9630', 'points_cost': '5000', 'discount':'Rs. 1070', 'name':'QMobile Noir S6'}, \
'7': {'price':'7000','discounted_price':'6500', 'points_cost': '5000', 'discount':'Rs. 500', 'name':'QMobile Noir 4G LT550'}, \
'8': {'price':'8500','discounted_price':'8500', 'points_cost': '5000', 'discount':'Rs. 500', 'name':'Infinix Smart'}, \
'9': {'price':'8840','discounted_price':'8840', 'points_cost': '5000', 'discount':'Rs. 500', 'name':'Huawei Y3 3G 2017'}, \
'10': {'price':'9630','discounted_price':'9630', 'points_cost': '5000', 'discount':'Rs. 500', 'name':'QMobile Energy X2'}, \
'11': {'price':'13800','discounted_price':'13800', 'points_cost': '5000', 'discount':'Rs. 500', 'name':'Samsung Galaxy Grand Prime Plus'}, \
'12': {'price':'18900','discounted_price':'18900', 'points_cost': '5000', 'discount':'Rs. 500', 'name':'Samsung J5 Prime'}, \
'13': {'price':'5500','discounted_price':'5500', 'points_cost': '5000', 'discount':'Rs. 0', 'name':'QMobile Noir X36'}, \
'14': {'price':'11300','discounted_price':'11300', 'points_cost': '5000', 'discount':'Rs. 0', 'name':'Huawei Ascend G700'}, \
'15': {'price':'11000','discounted_price':'11000', 'points_cost': '5000', 'discount':'Rs. 0', 'name':'Nokia 2'}, \
}#REMOVE
###############################################################################################################
# '2' DELIBERATELY SKIPPED DUE TO LEGACY REASONS
ZODIAC = {'1':'None','3':'Aquarius','4':'Pisces','5':'Aries','6':'Taurus','7':'Gemini','8':'Cancer','9':'Leo','10':'Virgo',\
'11':'Libra','12':'Scorpio','13':'Sagittarius','14':'Capricorn'}
###############################################################################################################
PROJ_ZUCK_STARTING_USER_ID = 20000000#1975000
SEGMENT_STARTING_USER_ID = 2268720000# starting user ID of user segment analysis

"""
TYPES OF USER ACTIVITIES:
note: we only log authenticated users. Non-auth users are not logged at the moment

'.u' is added if the user is attempting the action while 'unverified'
'.i' is added if the user is attempting an 'invalid' action (but while verified)
'.h' is added if the user hid/unhid a text in a group
---------------------
A1 - loaded own about page
A2 - loaded own post history
A3 - loaded own trending post history
A4 - loaded other's about page
A5 - loaded other's post history
A6 - loaded 'Followers' page from own about
A7 - loaded 'Following' page from own about
A1.u - loaded own about page (while unverified)
A2.u - loaded own post history (while unverified)
A3.u - loaded own trending post history (while unverified)
A4.u - loaded other's about page (while unverified)
A5.u - loaded other's post history (while unverified)
A6.u - loaded 'Followers' page from own about (while unverified)
A7.u - loaded 'Following' page from own about (while unverified)
---------------------
D - visited edit profile page
D.u - visited edit profile page (while unverified)
D.i - profile changes were invalid (whether it was an image change, bio change, etc)
D.u.i - profile changes were invalid (whether it was an image change, bio change, etc), and the user was unverified (doesn't matter - they're allowed to change their profiles)
D1 - new avatar uploaded
D1.u - new avatar uploaded (while unverified)
D2 - bio has been updated
D2.u - bio has been updated (while unverified)
---------------------
FE - landing on 'For Me' when it has no posts
FO - landing on 'For Me' when it has old posts
FN- landing on 'For Me' when it has new posts
F2 - landing on 'For Me' page 2 (or beyond)
FE.u - landing on 'For Me' when it has no posts
FO.u - landing on 'For Me' when it has old posts
FN.u - landing on 'For Me' when it has new posts
F2.u - landing on 'For Me' page 2 (or beyond)
---------------------	
BP - landing on 'best photos' page 1
BP2 - landing on 'best photos' page 2 (or beyond)
BP.u - landing on 'best photos' (while unverified)
BP2.u - landing on 'best photos' page 2 or beyond (while unverified)

FP - landing on 'fresh photos' page 1
FP2 - landing on 'fresh photos' page 2 or beyond
FP.u - landing on 'fresh photos' (while unverified)
FP2.u - landing on 'fresh photos' page 2 or beyond (while unverified)

BT - landing on 'best text' page 1
BT2 - landing on 'best text' page 2 (or beyond)
BT.u - landing on 'best text' page (while unverified)
BT2.u - landing on 'best text' page 2 or beyond (while unverified)

FT - landing on 'fresh text' page 1
FT2 - landing on 'fresh text' page 2 (or beyond)
FT.u - landing on 'fresh text' page (while unverified)
FT2.u - landing on 'fresh text' page 2 or beyond (while unverified)
---------------------
K1 - wrote inline 'best photo' reply
K2 - wrote inline 'fresh photo' reply
K3 - wrote inline 'best text' reply
K4 - wrote inline 'fresh text' reply
K5 - wrote inline 'topic' reply
K6 - wrote inline 'for me' reply
K1.i - wrote inline 'best photo' reply (invalid)
K2.i - wrote inline 'fresh photo' reply (invalid)
K3.i - wrote inline 'best text' reply (invalid)
K4.i - wrote inline 'fresh text' reply (invalid)
K5.i - wrote inline 'topic' reply (invalid)
K6.i - wrote inline 'for me' reply (invalid)
K1.u - wrote inline 'best photo' reply (while unverified)
K2.u - wrote inline 'fresh photo' reply (while unverified)
K3.u - wrote inline 'best text' reply (while unverified)
K4.u - wrote inline 'fresh text' reply (while unverified)
K5.u - wrote inline 'topic' reply (while unverified)
K6.u - wrote inline 'for me' reply (while unverified)
---------------------
C - reply successfully sent from photo-comment page
C.u - reply attempt from photo-comment page (while unverified)
C.i - reply attempt from photo-comment page (invalid)
C1 - landed on photo-comment page
C1.u - landed on photo-comment page (while unverified)
---------------------
L - reply successfully sent from text-comment page
L.u - reply attempt from text-comment page (while unverified)
L.i - reply attempt from text-comment page (invalid)
L1 - landed on text-comment page
L1.u - landed on text-comment page (while unverified)
---------------------
T - landing on 'topic'
T1 - text post shared from 'topic' page
T.u - landing on 'topic' (while unverified)
T1.u - text post unsuccesfully shared from 'topic' page (while unverified)
T1.i - text post unsuccesfully shared from 'topic' page (invalid)
---------------------
X1 - Successfully shared text post, replies on, long-lived
X2 - Successfully shared text post, replies off, long-lived
X3 - Successfully shared text post, replies on, short-lived
X4 - Successfully shared text post, replies off, short-lived
X1.t - Successfully shared text post, with topic, replies on, long-lived
X2.t - Successfully shared text post, with topic, replies off, long-lived
X3.t - Successfully shared text post, with topic, replies on, short-lived
X4.t - Successfully shared text post, with topic, replies off, short-lived
X1.u - Tried sharing text post, replies on/off, long-lived/short-lived (while unverified)
X1.i - Tried sharing text post, replies on/off, long-lived/short-lived (invalid)

XL - landed on the page from where user can share a text post
XL.u - landed on the page from where user can share a text post (while unverified)

P1 - Successfully shared photo post, replies on, long-lived
P2 - Successfully shared photo post, replies off, long-lived
P3 - Successfully shared photo post, replies on, short-lived
P4 - Successfully shared photo post, replies off, short-lived
P1.u - Tried sharing photo post, replies on/off, long-lived/short-lived (while unverified)
P1.i - Tried sharing photo post, replies on/off, long-lived/short-lived (invalid)

PL - landed on the page from where user can share a photo post
PL.u - landed on the page from where user can share a photo post (while unverified)

XP - landed on page where one can select 'text' or 'photos' for sharing
XP.u - landed on page where one can select 'text' or 'photos' for sharing (while unverified)

H - landed on sharing help page
H.u - landed on sharing help page (while unverified)
---------------------
N - Followed someone
N.u - Followed someone (while unverified)
N1 - Unfollowed someone
N1.u - Unfollowed someone (while unverified)
N2 - loaded 'you have new followers' prompt from 'For Me'
N2.u - loaded 'you have new followers' prompt from 'For Me' (while unverified)
N3 - Remove your follower
N3.u - Remove your follower (while unverified)
---------------------
S1 - responded to text-post single notification
S2 - responded to photo-post single notification
S3 - responded to 1on1 single notification
S4 - responded to public mehfil single notification
S5 - responded to private mehfil single notification
S1.s - skipped text-post single notification
S2.s - skipped photo-post single notification
S3.s - skipped 1on1 single notification
S4.s - skipped public mehfil single notification
S5.s - skipped private mehfil single notification
S1.i - responded unsuccesfully to text-post single notification (invalid)
S2.i - responded unsuccesfully to photo-post single notification (invalid)
S3.i - responded unsuccesfully to 1on1 single notification (invalid)
S4.i - responded unsuccesfully to public mehfil single notification (invalid)
S5.i - responded unsuccesfully to private mehfil single notification (invalid)
S1.u - responded unsuccesfully to text-post single notification (unverified)
S2.u - responded unsuccesfully to photo-post single notification (unverified)
S3.u - responded unsuccesfully to 1on1 single notification (unverified)
S4.u - responded unsuccesfully to public mehfil single notification (unverified)
S5.u - responded unsuccesfully to private mehfil single notification (unverified)
---------------------
IR - Loaded non-empty inbox replies
IR.u - Loaded non-empty inbox replies (while unverified)
IRE - Loaded empty inbox replies
IRE.u - Loaded empty inbox replies (while unverified)
IA - Loaded non-empty inbox activity
IAE - Loaded empty inbox activity
IA.u - Loaded non-empty inbox activity (while unverified)
IAE.u - Loaded empty inbox activity (while unverified)
IL - Inbox likes loaded
IL.u - Inbox likes loaded (while unverified)

I1 - responded to text-post reply from inbox
I2 - responded to photo-post reply from inbox
I3 - responded to 1on1 reply from inbox
I4 - responded to public mehfil from inbox
I5 - responded to private mehfil from inbox
I1.s - responded to text-post reply from inbox
I2.s - responded to photo-post reply from inbox
I3.s - responded to 1on1 reply from inbox
I4.s - responded to public mehfil from inbox
I5.s - responded to private mehfil from inbox
I1.i - attempted to respond to text-post reply from inbox (invalid)
I2.i - attempted to respond to photo-post reply from inbox (invalid)
I3.i - attempted to respond to 1on1 reply from inbox (invalid)
I4.i - attempted to respond to public mehfil from inbox (invalid)
I5.i - attempted to respond to private mehfil from inbox (invalid)
I1.u - attempted to respond to text-post reply from inbox (while unverified)
I2.u - attempted to respond to photo-post reply from inbox (while unverified)
I3.u - attempted to respond to 1on1 reply from inbox (while unverified)
I4.u - attempted to respond to public mehfil from inbox (while unverified)
I5.u - attempted to respond to private mehfil from inbox (while unverified)
---------------------
V - voted on an object
V.i - voted on an object (invalid)
V.u - voted on an object (while unverified)
---------------------
V1 - selected 'var1' in the tutorial
V2 - selected 'var2' in the tutorial
V3 - witnessed 'var3' tutorial while on 'best photos' page
V4 - selected 'var4' in the tutorial
---------------------
G1 - loaded list of joined mehfils
G2 - loaded mehfil invite list
G3 - loaded mehfil creation page
G4 - loaded popular mehfil list

G1.u - loaded list of joined mehfils (while unverified)
G2.u - loaded mehfil invite list (while unverified)
G3.u - loaded mehfil creation page (while unverified)
G4.u - visited popular mehfil list (while unverified)
---------------------
R - joined private mehfil
R1 - visited joined private mehfil
R2 - visited unjoined private mehfil
R3 - created private mehfil
R4 - visited joined private mehfil's settings as a regular member
R5 - visited joined private mehfil's settings as an owner
R6 - visited joined private mehfil's 'info' page
R7 - visited joined private mehfil's 'visitor' page
R.u - attempted to join private mehfil (while unverified)
R1.u - visited joined private mehfil (while unverified)
R2.u - visited unjoined private mehfil (while unverified)
R3.u - attempted to create a private mehfil (while unverified)
R3.i - attempted to create a private mehfil (invalid)
---------------------
U - joined public mehfil
U0 - entered unjoined public mehfil rules screen
U1 - visited joined public mehfil
U2 - visited unjoined public mehfil
U3 - created public mehfil
U5 - visited joined public mehfil's settings as a normal member
U6 - visited joined public mehfil's settings as an officer
U7 - visited joined public mehfil's settings as an owner
U8 - visited joined public mehfil's 'guidance' page
U9 - visited joined public mehfil's 'info' page
U10 - visited joined public mehfil's 'visitor' page
U.u - attempted to join public mehfil (while unverified)
U2.u - visited unjoined public mehfil (while unverified)
U3.u - attempted to create a public mehfil (while unverified)
U3.i - attempted to create a public mehfil (invalid)
---------------------
W0 - exited a 1on1
W1 - posted in 1on1
W2 - posted regular message in private mehfil
W3 - posted regular message in public mehfil
W5 - posted a reply-to-reply in private mehfil
W6 - posted a reply-to-reply in public mehfil

W2.h - hide/unhide a posting in a public mehfil
W3.h - hide/unhide a posting in a private mehfil

W2.u - attempted to post in private mehfil (while unverified)
W3.u - attempted to post in public mehfil (while unverified)
W5.u - attempted to post a reply-to-reply in private mehfil (while unverified)
W6.u - attempted to post a reply-to-reply in public mehfil (while unverified)

W1.i - attempted to post in 1on1 (invalid)
W2.i - attempted to post in private mehfil (invalid)
W3.i - attempted to post in pubic mehfil (invalid)
W5.i - attempted to post a reply-to-reply in private mehfil (invalid)
W6.i - attempted to post a reply-to-reply in public mehfil (invalid)

W4.s - subscribed successfully to a topic
W4.u - attempted to subscribe to a topic (while unverified)
---------------------
O - loaded online page
O.u - loaded online page (while unverified)
---------------------
Y.v - visited a joined 1on1
Y.s - visited a joined 1on1's settings
---------------------
Y - sent 1on1 invite successfully
Y.d - declined 1on1 invite successfully
Y.a - accepted 1on1 invite successfully
Y1- initiated 1on1 invite (i.e. first screen)
Y3 - loaded 1on1 invites received screen
Y4 - loaded 1on1 invites sent screen
Y5 - loaded 1on1 list screen
Y1.i - attempted to send a 1on1 invite but ran into the 'this user must be follow you' requirement for 1on1 invites
Y1.u - attempted to send 1on1 invite (while unverified)
Y2.u - attempted to change 1on1 invite privacy setting (while unverified)
Y3.u - attempted to load 1on1 invites received screen (while unverified)
Y4.u - attempted to load 1on1 invites sent screen (while unverified)
Y5.u - attempted to load 1on1 list screen (while unverified). This never displays - instead user is redirected to a 'verify-now' prompt
---------------------
Z1 - visited website 'help' page
Z1.u - visited website 'help' page (while unverified)
Z2 - visited website 'rules' page
Z2.u - visited website 'rules' page (while unverified)
Z3 - visited website 'about' page
Z3.u - visited website 'about' page (while unverified)
Z4 - visited 'search' page
Z4.u - visited 'search' page (while unverified)
---------------------
Z5 - visited 'topic list' page
Z5.u - visited 'topic list' page (while unverified)
Z8 - visited content detail page
Z8.u - visited content detail page (while unverified)
Z9 - visited 'top stars' page
Z9.u - visited 'top stars' page (while unverified)
Z10 - visited help page on how to get an image into trending
Z10.u - visited help page on how to get an image into trending (while unverified)
---------------------
Z11 - landed on 1st page of pvp blocking
Z11.u - landed on 1st page of pvp blocking (while unverified)
Z12 - landed on 1st page of 'content reporting'
Z12.u - landed on 1st page of 'content reporting' (while unverified). This never displays - instead user is redirected to a 'verify-now' prompt

Z - verified successfully
Z.u - visited verification page, JS user
Z.o.u - visited verification page, opera mini user (but non-fbs)
Z.f.u - visited verification page, freebasics user
---------------------
J1 - reported content
J - blocking another user successfully (pvp)
J.u - blocking another user successfully (pvp), while unverified
---------------------
G - searched a username, and some results were obtained
G.u - searched a username, and some results were obtained (while unverified)
G.i - searched a username (but no results obtained)
G.u.i - searched a username (but no results obtained - while unverified)
---------------------
E - public image shared in a 1on1, successfully
E.i - invalid attempt at sharing a public image in a 1on1 (because no 1on1s selected, or none of the selected 1on1s have given img sharing perm)

E1 - landed on "share image in 1on1" 1st page
E1.u - landed on "share image in 1on1" 1st page (while unverified)

"""