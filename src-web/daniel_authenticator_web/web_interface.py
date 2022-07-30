import os, json, time, random, re, sys
from flask import Flask, render_template, request, url_for, flash, redirect, session, send_from_directory
from flask_wtf.csrf import CSRFProtect
from daniel_authenticator_web.database import Database, declarative

def username_valid(username):
	return re.match(r"^[a-zA-Z0-9_\-.@]+$", username) is not None

def create_interface_app():
	
	template_folder = os.path.join(os.path.dirname(__file__), 'templates')
	static_folder = os.path.join(os.path.dirname(__file__), 'static')
	print("using template folder %s" % template_folder)
	print("using static folder %s" % static_folder)
	
	app = Flask(__name__,
		template_folder=template_folder,
		static_url_path='/static',
		static_folder=static_folder)
	
	secret_key = os.getenv('DANIEL_AUTHENTICATOR_SECRET_KEY')
	if secret_key is None:
		sys.exit("DANIEL_AUTHENTICATOR_SECRET_KEY environment variable is not set. Exiting.")
	
	app.secret_key = secret_key
	
	csrf = CSRFProtect()
	csrf.init_app(app)
	
	def is_logged_in(user_info):
		return user_info is not None
	
	app.jinja_env.globals.update(is_logged_in=is_logged_in)
	
	def handle_session():
		db = Database()
		user_id = session.get('user_id')
		if user_id is not None:
			user_info = db.get_user_info(user_id)
			if user_info is not None and user_info["locked"] == False and user_info["active"]:
				return user_info, db
			else:
				session.pop('user_id')
				return None, db
		else:
			return None, db
	
	@app.route('/', methods = ['GET'])
	def index_route():
		user_info, db = handle_session()
		if user_info is None:
			return redirect(url_for("login_route"))
		elif user_info['superuser']:
			return redirect(url_for("overview_route"))
		else:
			return redirect(url_for("profile_route"))
	
	@app.route('/overview', methods = ['GET'])
	def overview_route():
		user_info, db = handle_session()
		if user_info is None:
			return redirect(url_for("login_route"))
		elif user_info['superuser']:
			services=db.get_all_services_info()
			groups=db.get_all_groups_info()
			users=db.get_all_users_info()
			for user in users:
				service_memberships = db.get_user_service_memberships(user['user_id'])
				user['service_matrix'] = []
				for service in services:
					user['service_matrix'].append(service in service_memberships)
				
				group_memberships = db.get_user_group_memberships(user['user_id'])
				user['group_matrix'] = []
				for group in groups:
					user['group_matrix'].append(group in group_memberships)
			
			for group in groups:
				service_memberships = db.get_group_service_memberships(group['group_id'])
				group['service_matrix'] = []
				for service in services:
					group['service_matrix'].append(service in service_memberships)
				
			return render_template("overview.html", user_info=user_info, users=users, groups=groups, services=services)
		else:
			return render_template("404.html", user_info=user_info), 404
	
	@app.route('/login', methods = ['GET'])
	def login_route():
		user_info, db = handle_session()
		if user_info is None:
			return render_template("login.html", user_info=user_info, status="")
		else:
			return redirect(url_for("index_route"))
	
	@app.route('/login', methods = ['POST'])
	def login_post_route():
		user_info, db = handle_session()
		
		username = request.form.get("username")
		password = request.form.get("password")
		
		user, message = db.attempt_user_login(username, password)
		if user is not None:
			session['user_id'] = user['user_id']
			return redirect(url_for("index_route"))
		else:
			return render_template("login.html", user_info=user_info, status=message)
	
	@app.route('/logout', methods = ['POST'])
	def logout_post_route():
		if session.get('user_id') is not None:
			session.pop('user_id')
		return redirect(url_for("login_route"))
	
	@app.route('/profile', methods = ['GET'])
	def profile_route():
		user_info, db = handle_session()
		if user_info is None:
			return redirect(url_for("login_route"))
		else:
			group_memberships = db.get_user_group_memberships(user_info["user_id"])
			service_memberships = db.get_user_service_memberships(user_info["user_id"])
			return render_template("profile.html", user_info=user_info, group_memberships=group_memberships, service_memberships=service_memberships)
	
	@app.route('/users/<user_id>', methods = ['GET'])
	def user_route(user_id):
		user_info, db = handle_session()
		if user_info is None:
			return redirect(url_for("login_route"))
		elif user_info['superuser']:
			target_user_info = db.get_user_info(user_id)
			if target_user_info is None:
				return render_template("404.html", user_info=user_info), 404
			else:
				group_memberships = db.get_user_group_memberships(target_user_info["user_id"])
				groups = db.get_all_groups_info()
				service_memberships = db.get_user_service_memberships(target_user_info["user_id"])
				services = db.get_all_services_info()
				return render_template("user.html", user_info=user_info, target_user_info=target_user_info, group_memberships=group_memberships, service_memberships=service_memberships, groups=groups, services=services)
		else:
			return render_template("404.html", user_info=None), 404
	
	@app.route('/groups/<group_id>', methods = ['GET'])
	def group_route(group_id):
		user_info, db = handle_session()
		if user_info is None:
			return redirect(url_for("login_route"))
		else:
			target_group_info = db.get_group_info(group_id)
			if target_group_info is None:
				return render_template("404.html", user_info=user_info), 404
			else:
				user_memberships = db.get_users_in_group(target_group_info["group_id"])
				users = db.get_all_users_info()
				service_memberships = db.get_group_service_memberships(target_group_info["group_id"])
				services = db.get_all_services_info()
				return render_template("group.html", user_info=user_info, target_group_info=target_group_info, user_memberships=user_memberships, service_memberships=service_memberships, users=users, services=services)
	
	@app.route('/services/<service_id>', methods = ['GET'])
	def service_route(service_id):
		user_info, db = handle_session()
		if user_info is None:
			return redirect(url_for("login_route"))
		else:
			target_service_info = db.get_service_info(service_id)
			if target_service_info is None:
				return render_template("404.html", user_info=None), 404
			else:
				group_memberships = db.get_groups_in_service(target_service_info["service_id"])
				groups = db.get_all_groups_info()
				user_memberships = db.get_users_in_service(target_service_info["service_id"])
				users = db.get_all_users_info()
				return render_template("service.html", user_info=user_info, target_service_info=target_service_info, group_memberships=group_memberships, user_memberships=user_memberships, groups=groups, users=users)
	
	@app.route('/new_user', methods = ['POST'])
	def new_user_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				username = request.form.get("username").strip()
				password = request.form.get("password")
				repeat_password = request.form.get("repeat_password")
				fullname = request.form.get("fullname").strip()
				email = request.form.get("email").strip()
				
				if len(username) == 0 or len(password) == 0 or len(fullname) == 0 or len(email) == 0:
					return render_template("error.html", user_info=user_info, error="Username, password, fullname, and email cannot be empty")
				elif not username_valid(username):
					return render_template("error.html", user_info=user_info, error="Username can only contain a-z, A-Z, 0-9, _, -, and .")
				elif len(password) < 10:
					return render_template("error.html", user_info=user_info, error="Password must be at least 10 characters")
				elif password != repeat_password:
					return render_template("error.html", user_info=user_info, error="Passwords do not match")
				else:
					try:
						user_id = db.create_user(username, fullname, email, password, True, False)
						return redirect(url_for("user_route", user_id=user_id))
					except:
						return render_template("error.html", user_info=user_info, error="Database error when creating user (probably duplicate username or email)")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/new_group', methods = ['POST'])
	def new_group_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				username = request.form.get("username").strip()
				fullname = request.form.get("fullname").strip()
				
				if len(username) == 0 or len(fullname) == 0:
					return render_template("error.html", user_info=user_info, error="Username and fullname cannot be empty")
				elif not username_valid(username):
					return render_template("error.html", user_info=user_info, error="Username can only contain a-z, A-Z, 0-9, _, -, and .")
				else:
					try:
						group_id = db.create_group(username, fullname)
						return redirect(url_for("group_route", group_id=group_id))
					except:
						return render_template("error.html", user_info=user_info, error="Database error when creating group (probably duplicate username)")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/new_service', methods = ['POST'])
	def new_service_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				username = request.form.get("username").strip()
				password = request.form.get("password")
				repeat_password = request.form.get("repeat_password")
				fullname = request.form.get("fullname").strip()
				hyperlink = request.form.get("hyperlink")
				
				if len(username) == 0 or len(password) == 0 or len(fullname) == 0:
					return render_template("error.html", user_info=user_info, error="Username, password, and fullname cannot be empty")
				elif not username_valid(username):
					return render_template("error.html", user_info=user_info, error="Username can only contain a-z, A-Z, 0-9, _, -, and .")
				elif len(password) < 10:
					return render_template("error.html", user_info=user_info, error="Password must be at least 10 characters")
				elif password != repeat_password:
					return render_template("error.html", user_info=user_info, error="Passwords do not match")
				else:
					try:
						service_id = db.create_service(username, fullname, hyperlink, password, True)
						return redirect(url_for("service_route", service_id=service_id))
					except:
						return render_template("error.html", user_info=user_info, error="Database error when creating service (probably duplicate username)")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/add_user_to_group', methods = ['POST'])
	def add_user_to_group_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				user_id = request.form.get("user_id")
				group_id = request.form.get("group_id")
				next_url = request.form.get("next_url")
				try:
					db.add_user_to_group(user_id, group_id)
					return redirect(next_url)
				except:
					return render_template("error.html", user_info=user_info, error="Database error when adding user to group")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/remove_user_from_group', methods = ['POST'])
	def remove_user_from_group_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				user_id = request.form.get("user_id")
				group_id = request.form.get("group_id")
				next_url = request.form.get("next_url")
				try:
					db.remove_user_from_group(user_id, group_id)
					return redirect(next_url)
				except:
					return render_template("error.html", user_info=user_info, error="Database error when removing user from group")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/add_user_to_service', methods = ['POST'])
	def add_user_to_service_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				user_id = request.form.get("user_id")
				service_id = request.form.get("service_id")
				next_url = request.form.get("next_url")
				try:
					db.add_user_to_service(user_id, service_id)
					return redirect(next_url)
				except:
					return render_template("error.html", user_info=user_info, error="Database error when adding user to service")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/remove_user_from_service', methods = ['POST'])
	def remove_user_from_service_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				user_id = request.form.get("user_id")
				service_id = request.form.get("service_id")
				next_url = request.form.get("next_url")
				try:
					db.remove_user_from_service(user_id, service_id)
					return redirect(next_url)
				except:
					return render_template("error.html", user_info=user_info, error="Database error when removing user from service")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/add_group_to_service', methods = ['POST'])
	def add_group_to_service_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				group_id = request.form.get("group_id")
				service_id = request.form.get("service_id")
				next_url = request.form.get("next_url")
				try:
					db.add_group_to_service(group_id, service_id)
					return redirect(next_url)
				except:
					return render_template("error.html", user_info=user_info, error="Database error when adding group to service")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/remove_group_from_service', methods = ['POST'])
	def remove_group_from_service_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				group_id = request.form.get("group_id")
				service_id = request.form.get("service_id")
				next_url = request.form.get("next_url")
				try:
					db.remove_group_from_service(group_id, service_id)
					return redirect(next_url)
				except:
					return render_template("error.html", user_info=user_info, error="Database error when removing group from service")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/delete_user', methods = ['POST'])
	def delete_user_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				user_id = request.form.get("user_id")
				try:
					db.delete_user(user_id)
					return redirect(url_for("overview_route"))
				except:
					return render_template("error.html", user_info=user_info, error="Database error when deleting user")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/delete_service', methods = ['POST'])
	def delete_service_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				service_id = request.form.get("service_id")
				try:
					db.delete_service(service_id)
					return redirect(url_for("overview_route"))
				except:
					return render_template("error.html", user_info=user_info, error="Database error when deleting service")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/delete_group', methods = ['POST'])
	def delete_group_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				group_id = request.form.get("group_id")
				try:
					db.delete_group(group_id)
					return redirect(url_for("overview_route"))
				except:
					return render_template("error.html", user_info=user_info, error="Database error when deleting group")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/set_group_fullname', methods = ['POST'])
	def set_group_fullname_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				group_id = request.form.get("group_id")
				fullname = request.form.get("fullname").strip()
				if len(fullname) == 0:
					return render_template("error.html", user_info=user_info, error="Group fullname cannot be empty")
				
				try:
					db.set_group_fullname(group_id, fullname)
					return redirect(url_for("group_route", group_id=group_id))
				except:
					return render_template("error.html", user_info=user_info, error="Database error when setting group fullname")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/set_service_fullname', methods = ['POST'])
	def set_service_fullname_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				service_id = request.form.get("service_id")
				fullname = request.form.get("fullname").strip()
				if len(fullname) == 0:
					return render_template("error.html", user_info=user_info, error="Service fullname cannot be empty")
				
				try:
					db.set_service_fullname(service_id, fullname)
					return redirect(url_for("service_route", service_id=service_id))
				except:
					return render_template("error.html", user_info=user_info, error="Database error when setting service fullname")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/set_user_fullname', methods = ['POST'])
	def set_user_fullname_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				user_id = request.form.get("user_id")
				fullname = request.form.get("fullname").strip()
				if len(fullname) == 0:
					return render_template("error.html", user_info=user_info, error="User fullname cannot be empty")
				
				try:
					db.set_user_fullname(user_id, fullname)
					return redirect(url_for("user_route", user_id=user_id))
				except:
					return render_template("error.html", user_info=user_info, error="Database error when setting user fullname")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/set_password', methods = ['POST'])
	def set_password_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			else:
				password = request.form.get("password")
				repeat_password = request.form.get("repeat_password")
				if len(password) < 10:
					return render_template("error.html", user_info=user_info, error="Password must be at least 10 characters")
				
				if password != repeat_password:
					return render_template("error.html", user_info=user_info, error="Passwords do not match") 
				
				try:
					db.set_user_password(user_info['user_id'], password)
					return redirect(url_for("profile_route"))
				except:
					return render_template("error.html", user_info=user_info, error="Database error when setting password")
	
	@app.route('/set_user_password', methods = ['POST'])
	def set_user_password_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				user_id = request.form.get("user_id")
				password = request.form.get("password")
				repeat_password = request.form.get("repeat_password")
				if len(password) < 10:
					return render_template("error.html", user_info=user_info, error="User password must be at least 10 characters")
				
				if password != repeat_password:
					return render_template("error.html", user_info=user_info, error="User passwords do not match") 
				
				try:
					db.set_user_password(user_id, password)
					return redirect(url_for("user_route", user_id=user_id))
				except:
					return render_template("error.html", user_info=user_info, error="Database error when setting user password")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/set_service_password', methods = ['POST'])
	def set_service_password_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				service_id = request.form.get("service_id")
				password = request.form.get("password")
				repeat_password = request.form.get("repeat_password")
				if len(password) < 10:
					return render_template("error.html", user_info=user_info, error="Service password must be at least 10 characters")
				
				if password != repeat_password:
					return render_template("error.html", user_info=user_info, error="Service passwords do not match") 
				
				try:
					db.set_service_password(service_id, password)
					return redirect(url_for("service_route", service_id=service_id))
				except:
					return render_template("error.html", user_info=user_info, error="Database error when setting service password")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/set_user_email', methods = ['POST'])
	def set_user_email_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				user_id = request.form.get("user_id")
				email = request.form.get("email").strip()
				if len(email) == 0:
					return render_template("error.html", user_info=user_info, error="User email cannot be empty")
				
				try:
					db.set_user_email(user_id, email)
					return redirect(url_for("user_route", user_id=user_id))
				except:
					return render_template("error.html", user_info=user_info, error="Database error when setting user email")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/set_service_hyperlink', methods = ['POST'])
	def set_service_hyperlink_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				service_id = request.form.get("service_id")
				hyperlink = request.form.get("hyperlink").strip()
				
				try:
					db.set_service_hyperlink(service_id, email)
					return redirect(url_for("service_route", service_id=service_id))
				except:
					return render_template("error.html", user_info=user_info, error="Database error when setting service hyperlink")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/set_service_active', methods = ['POST'])
	def set_service_active_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				service_id = request.form.get("service_id")
				active = request.form.get("active")
				
				try:
					db.set_service_active(service_id, active == "true")
					return redirect(url_for("service_route", service_id=service_id))
				except:
					return render_template("error.html", user_info=user_info, error="Database error when setting service active")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/set_user_active', methods = ['POST'])
	def set_user_active_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				user_id = request.form.get("user_id")
				active = request.form.get("active")
				
				try:
					db.set_user_active(user_id, active == "true")
					return redirect(url_for("user_route", user_id=user_id))
				except:
					return render_template("error.html", user_info=user_info, error="Database error when setting user active")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/set_user_superuser', methods = ['POST'])
	def set_user_superuser_post_route():
		user_info, db = handle_session()
		if declarative:
			return render_template("error.html", user_info=user_info, error="Database error, cannot edit database while in declarative database mode")
		else:
			if user_info is None:
				return redirect(url_for("login_route"))
			elif user_info['superuser']:
				user_id = request.form.get("user_id")
				superuser = request.form.get("superuser")
				
				try:
					db.set_user_superuser(user_id, superuser == "true")
					return redirect(url_for("user_route", user_id=user_id))
				except:
					return render_template("error.html", user_info=user_info, error="Database error when setting user superuser")
			else:
				return render_template("404.html", user_info=user_info), 404
	
	@app.route('/unlock_user', methods = ['POST'])
	def unlock_user_post_route():
		user_info, db = handle_session()
		if user_info is None:
			return redirect(url_for("login_route"))
		elif user_info['superuser']:
			user_id = request.form.get("user_id")
			
			try:
				db.unlock_user(user_id)
				return redirect(url_for("user_route", user_id=user_id))
			except:
				return render_template("error.html", user_info=user_info, error="Database error when unlocking user")
		else:
			return render_template("404.html", user_info=user_info), 404
	
	@app.route('/robots.txt', methods = ['GET'])
	def robots_route():
		return "User-agent: *\nDisallow: /\n"
	
	@app.errorhandler(404)
	def page_not_found(e):
		user_info, db = handle_session()
		return render_template("404.html", user_info=user_info, ), 404
		
	return app
  
  

