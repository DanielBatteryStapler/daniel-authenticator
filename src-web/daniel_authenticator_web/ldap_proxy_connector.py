import os, json, time, random, re
from flask import Flask, g, render_template, request, url_for, flash, redirect, session, send_from_directory
from daniel_authenticator_web.database import Database

BASE_DN = "dc=daniel-authenticator"

SERVICES_BASE_DN = "ou=services," + BASE_DN

NEW_SERVICE_DN_REGEX = r"^ou=([a-zA-Z0-9_\-.@]+),%s$" % SERVICES_BASE_DN
NEW_TRAILING_SERVICE_DN_REGEX = r".*ou=([a-zA-Z0-9_\-.@]+),%s$" % SERVICES_BASE_DN

NEW_USERS_BASE_DN_REGEX = r"^ou=users,ou=([a-zA-Z0-9_\-.@]+),%s$" % SERVICES_BASE_DN
NEW_GROUPS_BASE_DN_REGEX = r"^ou=groups,ou=([a-zA-Z0-9_\-.@]+),%s$" % SERVICES_BASE_DN

NEW_USER_DN_REGEX = r"^uid=([a-zA-Z0-9_\-.@]+),ou=users,ou=([a-zA-Z0-9_\-.@]+),%s$" % SERVICES_BASE_DN
NEW_GROUP_DN_REGEX = r"^uid=([a-zA-Z0-9_\-.@]+),ou=groups,ou=([a-zA-Z0-9_\-.@]+),%s$" % SERVICES_BASE_DN

def make_null_entity():
	return {
		"DN": "",
		"Attributes": {
			"objectClass": ["top"],
			"vendorName": ["Daniel Authenticator"],
			"namingContexts": [BASE_DN],
			"defaultnamingcontext": [BASE_DN] 
		}
	}

"""
def make_entity_from_user_info(db, service_id, user_info):
	groups = db.get_user_group_memberships_for_service(user_info["user_id"], service_id)
	memberOfs = []
	for group in groups:
		memberOfs.append("uid=%s,%s" % (group["username"], GROUPS_BASE_DN))
	
	return {
		"DN": "uid=%s,%s" % (user_info["username"], USERS_BASE_DN),
		"Attributes": {
			"uid": [user_info["username"]],
			"cn": [user_info["fullname"]],
			"displayName": [user_info["fullname"]],
			"mail": [user_info["email"]],
			"ipaUniqueID": [user_info["uuid"]],
			"objectClass": ["posixaccount"],
			"memberOf": memberOfs
		}
	}

def make_entity_from_group_info(db, service_id, group_info):
	users = db.get_users_in_group_for_service(group_info["group_id"], service_id)
	members = []
	for user in users:
		members.append("uid=%s,%s" % (user["username"], USERS_BASE_DN))
	
	return {
		"DN": "uid=%s,%s" % (group_info["username"], GROUPS_BASE_DN),
		"Attributes": {
			"uid": [group_info["username"]],
			"cn": [group_info["fullname"]],
			"dsplayName": [group_info["fullname"]],
			"ipaUniqueID": [group_info["uuid"]],
			"objectClass": ["posixgroup"],
			"member": members
		}
	}
"""

def new_make_entity_from_user_info(db, service_id, user_info):
	service_info = db.get_service_info(service_id)
	groups = db.get_user_group_memberships_for_service(user_info["user_id"], service_id)
	memberOfs = []
	for group in groups:
		memberOfs.append("uid=%s,ou=groups,ou=%s,%s" % (group["username"], service_info['username'], SERVICES_BASE_DN))
	
	return {
		"DN": "uid=%s,ou=users,ou=%s,%s" % (user_info["username"], service_info['username'], SERVICES_BASE_DN),
		"Attributes": {
			"uid": [user_info["username"]],
			"cn": [user_info["fullname"]],
			"displayName": [user_info["fullname"]],
			"givenName": [user_info["fullname"]],
			"sn": [""],
			"mail": [user_info["email"]],
			"ipaUniqueID": [user_info["uuid"]],
			"objectClass": ["user"],
			"memberOf": memberOfs
		}
	}

def new_make_entity_from_group_info(db, service_id, group_info):
	service_info = db.get_service_info(service_id)
	users = db.get_users_in_group_for_service(group_info["group_id"], service_id)
	members = []
	for user in users:
		members.append("uid=%s,ou=users,ou=%s,%s" % (user["username"], service_info['username'], SERVICES_BASE_DN))
	
	return {
		"DN": "uid=%s,ou=groups,ou=%s,%s" % (group_info["username"], service_info['username'], SERVICES_BASE_DN),
		"Attributes": {
			"uid": [group_info["username"]],
			"cn": [group_info["fullname"]],
			"dsplayName": [group_info["fullname"]],
			"ipaUniqueID": [group_info["uuid"]],
			"objectClass": ["group"],
			"member": members
		}
	}

def create_ldap_app():
	app = Flask(__name__)
	
	@app.route('/bind', methods = ['POST'])
	def bind_route():
		db = Database()
		bindDN = request.form.get('bindDN', type=str)
		bindSimplePw = request.form.get('bindSimplePw', type=str)
		boundDN = request.form.get('boundDN', type=str)
		connection_number = request.form.get('connectionNumber', type=int)
		strand = request.form.get('strand', type=str)
		
		strand = strand + "bind(" + bindDN + " "
		
		new_service_result = re.match(NEW_SERVICE_DN_REGEX, bindDN)
		new_user_result = re.match(NEW_USER_DN_REGEX, bindDN)
		
		result = False
		if new_service_result is not None:
			service = db.attempt_service_login(new_service_result.group(1), bindSimplePw)
			if service is not None:
				strand += "service login allowed"
				result = True
			else:
				strand += "service login denied"
				result = False
			
		elif new_user_result is not None:
			user, message = db.attempt_user_login_with_service(new_user_result.group(1), bindSimplePw, new_user_result.group(2))
			if user is not None:
				strand += "user login allowed"
				result = True
			else:
				strand += "user login denied"
				result = False
		
		else:
			strand += "invalid DN denied"
			result = False
		
		strand = strand + ") -> "
		
		return json.dumps({
				"Result": result,
				"Strand": strand
			})
	
	@app.route('/search', methods = ['POST'])
	def search_route():
		db = Database()
		boundDN = request.form.get('boundDN', type=str)
		BaseDN = request.form.get('BaseDN', type=str)
		connection_number = request.form.get('connectionNumber', type=int)
		strand = request.form.get('strand', type=str)
		
		strand = strand + "search(" + BaseDN + " "
		
		new_service_result = re.match(NEW_SERVICE_DN_REGEX, boundDN)
		new_user_result = re.match(NEW_USER_DN_REGEX, boundDN)
		
		result = False
		entities = []
		
		def do_search():
			nonlocal result
			nonlocal entities
			nonlocal strand
			nonlocal new_service_result
			nonlocal new_user_result
			new_base_service_result = re.match(NEW_TRAILING_SERVICE_DN_REGEX, BaseDN)
				
			if new_base_service_result is not None:
				if new_service_result is not None and new_base_service_result.group(1) != new_service_result.group(1):
					strand += "mismatched bound service and search base denied"
					result = False
					entities = []
					
				elif new_user_result is not None and new_base_service_result.group(1) != new_user_result.group(2):
					strand += "mismatched bound user in service and search base denied"
					result = False
					entities = []
					
				else:
					service = db.get_service_by_username(new_base_service_result.group(1))
					
					new_users_base_result = re.match(NEW_USERS_BASE_DN_REGEX, BaseDN)
					new_groups_base_result = re.match(NEW_GROUPS_BASE_DN_REGEX, BaseDN)
					new_user_result = re.match(NEW_USER_DN_REGEX, BaseDN)
					new_group_result = re.match(NEW_GROUP_DN_REGEX, BaseDN)
					
					if new_users_base_result is not None:
						users = db.get_users_in_service(service["service_id"])
						for user in users:
							entities.append(new_make_entity_from_user_info(db, service["service_id"], user))
						strand += "users allowed"
						result = True
						
					elif new_groups_base_result is not None:
						groups = db.get_groups_in_service(service["service_id"])
						for group in groups:
							entities.append(new_make_entity_from_group_info(db, service["service_id"], group))
						strand += "groups allowed"
						result = True
					
					elif new_user_result is not None:
						user_info = db.get_user_by_username(new_user_result.group(1))
						if user_info is not None:
							if service in db.get_user_service_memberships(user_info['user_id']):
								entities = [new_make_entity_from_user_info(db, service["service_id"], user_info)]
								strand += "specific user allowed"
								result = True
							else:
								strand += "specific user not in service denied"
								result = False
								entities = []
						else:
							strand += "specific user does not exist denied"
							result = False
							entities = []
					
					elif new_group_result is not None:
						group_info = db.get_group_by_username(new_group_result.group(1))
						if group_info is not None:
							if service in db.get_group_service_memberships(group_info['group_id']):
								entities = [new_make_entity_from_group_info(db, service["service_id"], group_info)]
								strand += "specific group allowed"
								result = True
							else:
								strand += "specific group not in service denied"
								result = False
								entities = []
						else:
							strand += "specific group does not exist denied"
							result = False
							entities = []
					
					else:
						strand += "invalid search base denied"
						result = False
						entities = []
			else:
				strand += "invalid search base denied"
				result = False
				entities = []
			
		
		if BaseDN == "":
			entities.append(make_null_entity())
			strand += "null base allowed"
			result = True
		elif new_service_result is not None:
			service = db.get_service_by_username(new_service_result.group(1))
			
			if service is not None:
				do_search()
				
			else:
				strand += "service does not exist denied"
				result = False
				entities = []
			
		elif new_user_result is not None:
			user = db.get_user_by_username(new_user_result.group(1))
			
			if user is not None:
				do_search()
				
			else:
				strand += "user does not exist denied"
				result = False
				entities = []
			
		else:
			strand += "not bound denied"
			result = False
			entities = []
		
		strand = strand + ") -> "
		
		return json.dumps({
				"Result": result,
				"Entities": entities,
				"Strand": strand
			})
	
	@app.errorhandler(404)
	def page_not_found(e):
		return "404", 404
		
	return app
  
  


