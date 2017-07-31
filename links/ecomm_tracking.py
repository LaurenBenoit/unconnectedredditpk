import ast, time
from operator import itemgetter
from django.shortcuts import render
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from redis3 import get_and_reset_all_ecomm_clicks
from redis4 import get_and_reset_all_ecomm_visits, insert_todays_metrics, return_all_metrics_data


def unique_new_users(ids_and_joining_dates):
	unique_new_visitors = []
	for id_, date_joined in ids_and_joining_dates:
		if date_joined > (datetime.utcnow()-timedelta(days=1)):
			unique_new_visitors.append(id_)
	return unique_new_visitors

def unique_new_clicks_over_all_ads(unique_clicks, unique_new_visitors):
	# calculate clicks only by new users
	unique_new_clicks_over_all_ads = []
	for id_,ad_id in unique_clicks:
		if int(id_) in unique_new_visitors:
			unique_new_clicks_over_all_ads.append((id_,ad_id))
	return unique_new_clicks_over_all_ads


def retrieve_values_from_list_of_tuples(list_of_tuples):
	return map(itemgetter(0), list_of_tuples)


class EcommTrackingManager(object):
	obj = None

	def __init__(self, gross_visits, gross_clicks):
		clicks, visits = [], []
		for click in gross_clicks:
			clicks.append(ast.literal_eval(click))
		self.gross_clicks = clicks
		for visit in gross_visits:
			visits.append(ast.literal_eval(visit))
		self.gross_visits = visits # a list of all visits in the past 24 hours
		self.unique_visits = set(visits) # using set() makes the list unique
		self.unique_clicks = set(clicks)
		self.unique_visits_count = len(self.unique_visits) # len() gives the number of elements in the list (or set)
		self.unique_click_count = len(self.unique_clicks)
		self.unique_clickers = set(retrieve_values_from_list_of_tuples(list_of_tuples=clicks))
		self.unique_clickers_count = len(self.unique_clickers)
		self.unique_new_visitors = unique_new_users(ids_and_joining_dates=User.objects.filter(id__in=self.unique_visits).values_list('id','date_joined'))
		self.unique_new_clickers = unique_new_users(ids_and_joining_dates=User.objects.filter(id__in=self.unique_clickers).values_list('id','date_joined'))
		self.unique_new_visitor_count = len(self.unique_new_visitors)
		self.unique_new_clicker_count = len(self.unique_new_clickers)
		self.unique_new_clicks = unique_new_clicks_over_all_ads(unique_clicks=self.unique_clicks, unique_new_visitors=self.unique_new_visitors)
		self.unique_new_click_count = len(self.unique_new_clicks)

def calc_ecomm_metrics():
	metrics_obj = EcommTrackingManager(gross_visits=get_and_reset_all_ecomm_visits(), gross_clicks=get_and_reset_all_ecomm_clicks())
	###########################################################################################################################################
	# 1) unique_clicks/unique_visitors:
	try:
		unique_clicks_per_unique_visitor = "{0:.2f}".format(metrics_obj.unique_click_count/float(metrics_obj.unique_visits_count)) # resulted rounded to 2 decimal places using inbuilt 'format' method
	except ZeroDivisionError:
		unique_clicks_per_unique_visitor = None
	###########################################################################################################################################
	# 2) unique_clicks/unique_clicker:
	try:
		unique_clicks_per_unique_clicker = "{0:.2f}".format(metrics_obj.unique_click_count/float(metrics_obj.unique_clickers_count))
	except ZeroDivisionError:
		unique_clicks_per_unique_clicker = None
	###########################################################################################################################################
	# 3) unique_clickers/unique_visitors:
	try:
		proportion_of_clickers_to_visitors = "{0:.2f}".format(metrics_obj.unique_clickers_count/float(metrics_obj.unique_visits_count))
	except ZeroDivisionError:
		proportion_of_clickers_to_visitors = None
	###########################################################################################################################################
	# 4) new_clickers/new_visitors:
	try:
		unique_new_clickers_per_unique_new_visitors = "{0:.2f}".format(metrics_obj.unique_new_clicker_count/float(metrics_obj.unique_new_visitor_count))
	except ZeroDivisionError:
		unique_new_clickers_per_unique_new_visitors = None
	###########################################################################################################################################
	# 5_ new_clicks/new_visitors
	try:
		unique_new_clicks_per_unique_new_visitor = "{0:.2f}".format(metrics_obj.unique_new_click_count/float(metrics_obj.unique_new_visitor_count))
	except ZeroDivisionError:
		unique_new_clicks_per_unique_new_visitor = None
	###########################################################################################################################################
	total_unique_visitors = metrics_obj.unique_visits_count
	total_unique_clicks = metrics_obj.unique_click_count
	###########################################################################################################################################
	return unique_clicks_per_unique_visitor, unique_clicks_per_unique_clicker, proportion_of_clickers_to_visitors, unique_new_clickers_per_unique_new_visitors, \
	unique_new_clicks_per_unique_new_visitor, total_unique_visitors, total_unique_clicks


def insert_latest_metrics():
	calculation_time, latest_metrics = time.time(), calc_ecomm_metrics()
	insert_todays_metrics(latest_metrics, calculation_time)


def display_latest_metrics(request):
	metrics_history = return_all_metrics_data()# 'metrics_history' contains unusable 'stringified' dictionaries
	if metrics_history:
		metrics = []
		for row in metrics_history[:60]:
			row = ast.literal_eval(row) # making 'string' dictionaries readable
			row["entry_time"] = datetime.fromtimestamp(row["entry_time"])
			metrics.append(row)
		# import pandas as pd
		# print pd.DataFrame(metrics)
		template_context = {'unique_clicks_per_unique_visitor':metrics[0]["unique_clicks_per_unique_visitor"], 'unique_clicks_per_unique_clicker':metrics[0]["unique_clicks_per_unique_clicker"],\
		'proportion_of_clickers_to_visitors':metrics[0]["proportion_of_clickers_to_visitors"],'unique_new_clickers_per_unique_new_visitors':metrics[0]["unique_new_clickers_per_unique_new_visitors"],\
		'unique_new_clicks_per_unique_new_visitor':metrics[0]["unique_new_clicks_per_unique_new_visitor"], 'reporting_time':metrics[0]["entry_time"], 'total_unique_visitors':\
		metrics[0]["total_unique_visitors"],'total_unique_clicks':metrics[0]["total_unique_clicks"],'history':metrics}
	else:
		template_context = {}
	return render(request,"ecomm_metrics.html",template_context)