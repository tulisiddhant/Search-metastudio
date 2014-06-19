from django.shortcuts import render
from django.http import HttpResponse
from gnowsys_ndf.ndf.models import *
from django.template import RequestContext
from stemming.porter2 import stem
# from bson.json_util import dumps
import json
from collections import OrderedDict
import difflib
#############
collection = get_database()[Node.collection_name]
#############

class Encoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, ObjectId):
			return str(obj)
		else:
			return obj

def insert_all_links():
        col = get_database()[Node.collection_name] 	
	all_GSystemTypes = col.Node.find({"_type":"GSystemType"}, {"name":1, "_id":1})

	for GSystem in all_GSystemTypes:
		instance = col.allLinks()
		instance.link = GSystem.name
		instance.member_of = ObjectId(GSystem._id)
		instance.required_for = u"Links"
		instance.save()
	
def search_query(request, group_id):
	"""Renders a list of all 'Page-type-GSystems' available within the database.
	"""
	# Check if no link objects are added and add them if required	
	col = get_database()[Node.collection_name]
	link_instances = col.Node.find({"required_for":"Links"}, {"name":1})
	
	if (link_instances.count() == 0):
		print "Adding links\n"
		insert_all_links()

	ins_objectid  = ObjectId()
	if ins_objectid.is_valid(group_id) is False :
		group_ins = collection.Node.find_one({'_type': "Group","name": group_id})
		auth = collection.Node.one({'_type': 'Author', 'name': unicode(request.user.username) })
		if group_ins:
			group_id = str(group_ins._id)
		else:
	    		auth = collection.Node.one({'_type': 'Author', 'name': unicode(request.user.username) })
	    		if auth :
				group_id = str(auth._id)
	else:
		pass

	# print "In search form the request " + request.GET['search_text']
	return render(request, 'ndf/search_home.html', {"groupid":group_id}, context_instance=RequestContext(request))


def results_search(request, group_id):
	
	# DECLARE THE VARIABLES
	search_by_name = 1
	search_by_tags = 0
	search_by_contents = 0
	user = ""

#	try:
	if request.method == "GET":
		# PRINT THE VALUES TO SEE IF STEMMING, ARTICLE REMOVAL IS RIGHT

		search_str_user = str(request.GET['search_text'])
		print "\noriginal search string:", search_str_user, "\n"
		search_str_user = search_str_user.lower()

		search_str_noArticles = list(removeArticles(str(search_str_user)))
		print "\narticles removed:",search_str_noArticles,"\n"

		search_str_stemmed = list(stemWords(search_str_noArticles, search_str_user))
		print "\nwords stemmed:",search_str_stemmed,"\n\n\n"

		# -------------------------------------------------------
		print "Search string lowercase:", search_str_user

		# GET THE LIST OF CHECKBOXES TICKED AND SET CORR. FLAGS
		checked_fields = request.GET.getlist('search_fields')
		nam = "name"
	
		print "fields: ", checked_fields	
		if (nam in checked_fields):
			print "by_name"
			search_by_name = 1

		nam = "tags"
		if (nam in checked_fields):
			print "by_tags"
			search_by_tags = 1
		
		nam = "contents"
		if (nam in checked_fields):
			print "by_contents"
			search_by_contents = 1

		user = str(request.GET['author'])				# GET THE VALUE OF AUTHOR FROM THE FORM

		col = get_database()[Node.collection_name]			# COLLECTION NAME

		print "Checking USER:"

		if (user != ""):
			user = User.objects.get(username = user).pk	# GET THE PK CORRESPONDING TO THE USERNAME IF IT EXISTS
		else:
			user = "None"

		print "USER:", user

		# FORMAT OF THE RESULTS RETURNED
		search_results_ex = {'name':[], 'tags':[], 'content':[], 'user':[]}
		search_results_st = {'name':[], 'tags':[], 'content':[], 'user':[]}
		search_results_li = {'name':[], 'tags':[], 'content':[], 'user':[]}
		
		# ALL SORTED SEARCH RESULTS
		search_results = {'exact':search_results_ex, 'stemmed':search_results_st, 'like':search_results_li}

		# STORES OBJECTID OF EVERY SEARCH RESULT TO CHECK FOR DUPLICATES
		all_ids = []

		# GET A CURSOR ON ALL THE GSYSTEM TYPES 
		all_GSystemTypes = col.Node.find({"_type":"GSystemType"}, {"name":1, "_id":1})
		len1 = all_GSystemTypes.count()
		
		if (search_by_name == 1):					# IF 1, THEN SEARCH BY NAME
			all_GSystemTypes.rewind()
			count = 0

			for GSType in all_GSystemTypes:
				print GSType.name
				print "------------------"

				# EXACT MATCH OF SEARCH_USER_STR IN NAME OF GSYSTEMS OF ONE GSYSTEM TYPE
				exact_match = col.Node.find({"member_of":GSType._id, "name":{"$regex":search_str_user, "$options":"i"}}, {"name":1, "_id":1, "member_of":1})

				# SORT THE NAMES ACCORDING TO THEIR SIMILARITY WITH THE SEARCH STRING
				exact_match = list(exact_match)				
				exact_match = sort_names_by_similarity(exact_match, search_str_user)

				for j in exact_match:
					if j._id not in all_ids:
						print "adding type \n"
						j = addType(j)
						print j, "\n"
						search_results_ex['name'].append(j)
						all_ids.append(j['_id'])

				# split stemmed match
				split_stem_match = []
				len_stemmed = len(search_str_stemmed)
				c = 0								# GEN. COUNTER 

				while c < len_stemmed:
					word = search_str_stemmed[c]
					temp = col.Node.find({"member_of":GSType._id, "name":{"$regex":word, "$options":"i"}}, {"name":1, "_id":1, "member_of":1})
					temp_sorted = sort_names_by_similarity(temp, search_str_user)
				#	add_types = 
					split_stem_match.append(temp_sorted)
					c += 1
				print "split_stemmed", split_stem_match
				
				for j in split_stem_match:
					c = 0
					for k in j:
						if (k._id not in all_ids):
							search_results_st['name'].append(k)
							all_ids.append(k._id)
							c += 1


		if (search_by_tags == 1):						# IF 1, THEN SEARCH BY TAGS

			all_GSystemTypes.rewind()
			count = 0

			for GSType in all_GSystemTypes:
				print GSType.name
				print "------------------"

				# EXACT MATCH OF SEARCH_USER_STR IN NAME OF GSYSTEMS OF ONE GSYSTEM TYPE
				exact_match = col.Node.find({"member_of":GSType._id, "tags":search_str_user}, {"name":1, "_id":1})
				
				exact_match = sort_names_by_similarity(exact_match, search_str_user)
				
				for j in exact_match:
					if j._id not in all_ids:
						search_results_ex['tags'].append(j)
						all_ids.append(j._id)


				# split stemmed match
				split_stem_match = []
				c = 0						# GEN. COUNTER 
				len_stemmed = len(search_str_stemmed)

				while c < len_stemmed:
					word = search_str_stemmed[c]

					temp = col.Node.find({"member_of":GSType._id, "tags":word}, {"name":1, "_id":1})
					temp_sorted = sort_names_by_similarity(temp, search_str_user)
					
					split_stem_match.append(temp_sorted)
					c += 1

				for j in split_stem_match:
					c = 0
					for k in j:
						if k._id not in all_ids:
							search_results_st['tags'].append(k)
							all_ids.append(k._id)
							c += 1


		if (search_by_contents == 1):
			all_GSystemTypes.rewind()
			count = 0
			print "Searching by tags:\n\n"

			for GSType in all_GSystemTypes:
				print GSType.name
				print "------------------"

				# EXACT MATCH OF SEARCH_USER_STR IN NAME OF GSYSTEMS OF ONE GSYSTEM TYPE
				exact_match = col.Node.find({"member_of":GSType._id, "content_org":search_str_user}, {"name":1, "_id":1})
		
				# split stemmed match
				split_stem_match = []
				c = 0						# GEN. COUNTER 
				len_stemmed = len(search_str_stemmed)

				while c < len_stemmed:
					split_stem_match.append(col.Node.find({"member_of":GSType._id, "content_org":{"$regex":search_str_stemmed[c], "$options":"i"}}, {"name":1, "_id":1, "member_of":1}))
					c += 1

				# like search
				f = col.Node.find({"member_of":GSType._id, "content_org":{"$regex":search_str_user}}, {"name":1, "_id":1})
				len2 = f.count()

				print "By exact search: \n"
				for j in exact_match:
					search_results_ex['content'].append(j)

				print "By stemmed search: \n"
				for j in split_stem_match:
					c = 0
					for k in j:
						search_results_st['content'].append(k)
						c += 1

				print "By like search: \n"
				if (len2 == 0):
					print "NILL"
				for j in f:
					print j.name, j._id
					search_results_li['content'].append(j)
					count += 1
				print "------------------\n\n"

		"""
		if (user != "None"):
			print "All GSystems by the user", user
			all_GSystemTypes.rewind()
			count = 0
			print "Searching by user:\n\n"

			for GSType in all_GSystemTypes:
				print GSType.name
				print "------------------"

				# EXACT MATCH OF SEARCH_USER_STR IN NAME OF GSYSTEMS OF ONE GSYSTEM TYPE
				exact_match = col.Node.find({"member_of":GSType._id, "created_by":user}, {"name":1, "_id":1})
		
				# split stemmed match
				split_stem_match = []
				c = 0						# GEN. COUNTER 
				len_stemmed = len(search_str_stemmed)

				while c < len_stemmed:
					split_stem_match.append(col.Node.find({"member_of":GSType._id, "created_by":user}, {"name":1, "_id":1}))
					c += 1

				# like search
				f = col.Node.find({"member_of":GSType._id, "created_by":user}, {"name":1, "_id":1})
				len2 = f.count()

				print "By exact search: \n"
				for j in exact_match:
					print j.name, j._id
					search_results_ex['user'].append(j)

				print "By stemmed search: \n"
				for j in split_stem_match:
					c = 0
					for k in j:
						print k.name, k._id
						search_results_st['user'].append(k)
						c += 1

				print "By like search: \n"
				if (len2 == 0):
					print "NILL"
				for j in f:
					print j.name#, j._id
					search_results_li['user'].append(j)
					count += 1
				print "------------------\n\n"
			b"""	
		print search_results
		
		search_results = json.dumps(search_results, cls=Encoder)
		#print "\nJSON: ", search_results

		return render(request, 'ndf/search_results.html', {'processed':1, 'search_results':search_results, "groupid":group_id})
	#except Exception, arg:
		#print arg
		return HttpResponse("You are at results. No search key entered")


def addType(obj):
	print "received: ", obj.member_of[0]
	i = ObjectId(obj.member_of[0])
	links = collection.Node.find({"member_of":i, "required_for":"Links"}, {"link":1})
	obj2 = {}
	print "links count", links.count(), "\n"

	for ob in links:
		obj2['_id'] = obj._id
		obj2['name'] = obj.name
		obj2['link'] = ob.link
		print "obj", obj2
	return obj2

def sort_names_by_similarity(exact_match, search_str_user):
	matches = []					# TO STORE A LIST OF SORTED MATCH PERCENTAGE
	final_list = []					# FINAL LIST OF SORTED OBJECTS

	for obj in exact_match:

		match = difflib.SequenceMatcher(None, obj.name, search_str_user)
		per_match = match.ratio()
		print "sorting", obj.name, ": ", per_match, "\n"

		if len(matches) == 0:
			matches.append(per_match)
			final_list.append(obj)
		else:
			c = 0
			while ((c < len(matches)) and (per_match < matches[c])):
				c += 1
			matches.insert(c, per_match)
			final_list.insert(c, obj)

	print "sorted list: "
	for obj in final_list:
		print obj.name, ", "

	print "\n"

	return final_list


def removeArticles(text):
	words = text.split()
	articles=['a', 'an', 'and', 'the', 'i', 'is', 'this', 'that', 'there', 'here', 'am', 'on', 'at', 'of']
	for w in articles:
		if w in words:
			words.remove(w)
	words = removeDuplicateWords(words)
	return words


def removeDuplicateWords(words):
	return list(OrderedDict.fromkeys(words))

def stemWords(words, search_str_user):
	stemmed = []
	l = len(words)
	c = 0	
	
	while (c < l):
		temp = stem(words[c])
		if (temp != search_str_user):
			stemmed.append(temp)
		c+=1
	
	print stemmed
	return stemmed
