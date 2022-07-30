import os, json, time, random, re, sys
from daniel_authenticator_web.database import Database

def main():
	db = Database()
	
	command = "help"
	if len(sys.argv) == 1:
		return
	
	if len(sys.argv) >= 2:
		command = sys.argv[1]
	
	if command == "help":
		print("""
		Usage: daniel-authenticator-cli SUBCOMMAND [ARGUMENT]...
		
		Valid subcommands:
			create_user USERNAME FULLNAME EMAIL PASSWORD
			set_user_password USERNAME PASSWORD
			set_user_password_using_freeipa_hash USERNAME PASSWORD_HASH
			unlock USERNAME
			superuser USERNAME
			set_user_uuid USERNAME UUID
			
			create_service SERVICE_USERNAME FULLNAME HYPERLINK PASSWORD
			set_service_password_using_freeipa_hash SERVICE_USERNAME PASSWORD_HASH
			
			create_group GROUP_USERNAME FULLNAME
			set_group_uuid GROUP_USERNAME UUID
			
			add_user_to_service USERNAME SERVICE_USERNAME
			add_user_to_group USERNAME GROUP_USERNAME
			add_group_to_service GROUP_USERNAME SERVICE_USERNAME
		""")
	
		
	elif command == "create_user" and len(sys.argv) == 6:
		try:
			db.create_user(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], True, False)
			print("created new user %s" % sys.argv[2])
		except:
			print("Database error when creating new user (probably duplicate username or email)")
			sys.exit(1)
	
	elif command == "set_user_password" and len(sys.argv) == 4:
		user_info = db.get_user_by_username(sys.argv[2])
		if user_info is None:
			print("No user with that username found")
			sys.exit(1)
		else:
			db.set_user_password(user_info['user_id'], sys.argv[3])
			print("changed password of user %s" % user_info['username'])
	
	elif command == "set_user_password_using_freeipa_hash" and len(sys.argv) == 4:
		user_info = db.get_user_by_username(sys.argv[2])
		if user_info is None:
			print("No user with that username found")
			sys.exit(1)
		else:
			db.set_user_password_using_freeipa_hash(user_info['user_id'], sys.argv[3])
			print("changed password of user %s" % user_info['username'])
	
	elif command == "unlock" and len(sys.argv) == 3:
		user_info = db.get_user_by_username(sys.argv[2])
		if user_info is None:
			print("No user with that username found")
			sys.exit(1)
		else:
			db.unlock_user(user_info['user_id'])
			print("unlocked user %s" % user_info['username'])
		
	elif command == "superuser" and len(sys.argv) == 3:
		user_info = db.get_user_by_username(sys.argv[2])
		if user_info is None:
			print("No user with that username found")
			sys.exit(1)
		else:
			db.set_user_superuser(user_info['user_id'], True)
			print("made user %s into superuser" % user_info['username'])
	
	elif command == "set_user_uuid" and len(sys.argv) == 4:
		user_info = db.get_user_by_username(sys.argv[2])
		if user_info is None:
			print("No user with that username found")
			sys.exit(1)
		else:
			db.set_user_uuid(user_info['user_id'], sys.argv[3])
			print("changed uuid of user %s" % user_info['username'])
	
	elif command == "create_service" and len(sys.argv) == 6:
		try:
			db.create_service(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], True)
			print("created new service %s" % sys.argv[2])
		except:
			print("Database error when creating new service (probably duplicate username)")
			sys.exit(1)
	
	elif command == "set_service_password_using_freeipa_hash" and len(sys.argv) == 4:
		service_info = db.get_service_by_username(sys.argv[2])
		if service_info is None:
			print("No service with that username found")
			sys.exit(1)
		else:
			db.set_service_password_using_freeipa_hash(service_info['service_id'], sys.argv[3])
			print("changed password of service %s" % service_info['username'])
	
	elif command == "create_group" and len(sys.argv) == 4:
		try:
			db.create_group(sys.argv[2], sys.argv[3])
			print("created new group %s" % sys.argv[2])
		except:
			print("Database error when creating new group (probably duplicate username)")
			sys.exit(1)
	
	elif command == "set_group_uuid" and len(sys.argv) == 4:
		group_info = db.get_group_by_username(sys.argv[2])
		if group_info is None:
			print("No group with that username found")
			sys.exit(1)
		else:
			db.set_group_uuid(group_info['group_id'], sys.argv[3])
			print("changed uuid of group %s" % group_info['username'])
	
	elif command == "add_user_to_service" and len(sys.argv) == 4:
		user_info = db.get_user_by_username(sys.argv[2])
		if user_info is None:
			print("No user with that username found")
			sys.exit(1)
		else:
			service_info = db.get_service_by_username(sys.argv[3])
			if service_info is None:
				print("No service with that username found")
				sys.exit(1)
			else:
				db.add_user_to_service(user_info['user_id'], service_info['service_id'])
				print("added user %s to service %s" % (user_info['username'], service_info['username']))
	
	elif command == "add_user_to_group" and len(sys.argv) == 4:
		user_info = db.get_user_by_username(sys.argv[2])
		if user_info is None:
			print("No user with that username found")
			sys.exit(1)
		else:
			group_info = db.get_group_by_username(sys.argv[3])
			if group_info is None:
				print("No group with that username found")
				sys.exit(1)
			else:
				db.add_user_to_group(user_info['user_id'], group_info['group_id'])
				print("added user %s to group %s" % (user_info['username'], group_info['username']))
	
	elif command == "add_group_to_service" and len(sys.argv) == 4:
		group_info = db.get_group_by_username(sys.argv[2])
		if group_info is None:
			print("No group with that username found")
			sys.exit(1)
		else:
			service_info = db.get_service_by_username(sys.argv[3])
			if service_info is None:
				print("No service with that username found")
				sys.exit(1)
			else:
				db.add_group_to_service(group_info['group_id'], service_info['service_id'])
				print("added group %s to service %s" % (group_info['group_id'], service_info['username']))
	
	else:
		print("unrecognized command or wrong number of arguments, try: daniel-authenticator-cli help")
		sys.exit(1)
	




