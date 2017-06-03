# coding=utf-8
import redis, time
from location import REDLOC3

'''
##########Redis Namespace##########

latest_user_ip = "lip:"+str(user_id)
sorted_set = "online_users"
user_ban = "ub:"+str(user_id)

###########
'''

POOL = redis.ConnectionPool(connection_class=redis.UnixDomainSocketConnection, path=REDLOC3, db=0)

TEN_MINS = 10*60
FIVE_MINS = 5*60

#######################Test Function######################

# def set_test_payload(payload_list):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	try:
# 		return my_server.lpush("my_test",payload_list)
# 	except:
# 		return None

#######################Whose Online#######################

#expires online_users from tasks.py
def expire_online_users():
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "online_users"
	my_server.zremrangebyscore(sorted_set,'-inf','('+str(time.time()-TEN_MINS))

#invoked from WhoseOnline.py middleware
def set_online_users(user_id,user_ip):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "online_users"
	latest_user_ip = "lip:"+str(user_id) #latest ip of user with 'user_id'
	my_server.zadd(sorted_set,str(user_id)+":"+str(user_ip),time.time())
	my_server.set(latest_user_ip,user_ip)
	my_server.expire(latest_user_ip,FIVE_MINS)
	# storelogin(keys=[sorted_set,latest_user_ip],args=[time.time(),user_id,user_ip])

# invoked by tasks.py to show whoever is online in OnlineKon
def get_recent_online():
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "online_users"
	ten_mins_ago = time.time() - TEN_MINS
	online_users = my_server.zrangebyscore(sorted_set,ten_mins_ago,'+inf')
	# print online_users
	online_ids = []
	for user in online_users:
		online_ids.append(user.split(":",1)[0])
	# print online_ids
	return online_ids
	# return getlatestlogins(keys=[sorted_set],args=[time.time()])

# invoked in views.py to show possible clones of users
def get_clones(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "online_users"
	latest_user_ip = "lip:"+str(user_id) #latest ip of user with 'user_id'
	user_ip = my_server.get(latest_user_ip)
	if user_ip:
		clones = []
		five_mins_ago = time.time() - FIVE_MINS
		online_users = my_server.zrangebyscore(sorted_set,five_mins_ago,'+inf')
		for user in online_users:
			if user_ip == user.split(":",1)[1]:
				clones.append(user.split(":",1)[0])
		return clones
	else:
		return None

# def set_site_ban(user_id):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	user_ban = "ub:"+str(user_id) # banning user's ip from logging into website
# 	my_server.set(user_ban,1)
# 	my_server.expire(user_ban,ONE_HOUR)