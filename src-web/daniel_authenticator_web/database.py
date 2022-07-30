
import os, sqlite3, uuid
from os.path import exists
import daniel_authenticator_web.password as pswd
from daniel_authenticator_web.password import check_password
from datetime import datetime

TIME_FORMAT = "%Y/%m/%d %H:%M:%S"

database_init_sql_script = """
  CREATE TABLE users(
	user_id INTEGER PRIMARY KEY NOT NULL,
	username TEXT NOT NULL,
	fullname TEXT NOT NULL,
	email TEXT NOT NULL,
	uuid TEXT NOT NULL,
	password_hash TEXT NOT NULL,
	active BOOLEAN NOT NULL,
	incorrect_login_attempts INTEGER NOT NULL,
	locked BOOLEAN NOT NULL,
	last_login_time TEXT NOT NULL,
	creation_time TEXT NOT NULL,
	superuser BOOLEAN NOT NULL
  );
  
  CREATE UNIQUE INDEX users_index_username ON users(username);
  CREATE UNIQUE INDEX users_index_email ON users(email);
  
  CREATE TABLE services(
	service_id INTEGER PRIMARY KEY NOT NULL,
	username TEXT NOT NULL,
	fullname TEXT NOT NULL,
	hyperlink TEXT NOT NULL,
	password_hash TEXT NOT NULL,
	active BOOLEAN NOT NULL
  );
  
  CREATE UNIQUE INDEX services_index_username ON services(username);
  
  CREATE TABLE user_service_memberships(
	user_service_membership_id INTEGER PRIMARY KEY NOT NULL,
	user_id INTEGER,
	service_id INTEGER,
	FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
	FOREIGN KEY(service_id) REFERENCES services(service_id) ON DELETE CASCADE
  );
  
  CREATE UNIQUE INDEX user_service_memberships_index ON user_service_memberships(user_id, service_id);
  
  CREATE TABLE groups(
	group_id INTEGER PRIMARY KEY NOT NULL,
	username TEXT NOT NULL,
	fullname TEXT NOT NULL,
	uuid TEXT NOT NULL
  );
  
  CREATE TABLE user_group_memberships(
	user_group_membership_id INTEGER PRIMARY KEY NOT NULL,
	user_id INTEGER,
	group_id INTEGER,
	FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
	FOREIGN KEY(group_id) REFERENCES groups(group_id) ON DELETE CASCADE
  );
  
  CREATE UNIQUE INDEX user_group_memberships_index ON user_group_memberships(user_id, group_id);
  
  CREATE TABLE group_service_memberships(
	group_service_membership_id INTEGER PRIMARY KEY NOT NULL,
	group_id INTEGER,
	service_id INTEGER,
	FOREIGN KEY(group_id) REFERENCES groups(group_id) ON DELETE CASCADE,
	FOREIGN KEY(service_id) REFERENCES services(service_id) ON DELETE CASCADE
  );
  
  CREATE UNIQUE INDEX group_service_memberships_index ON group_service_memberships(group_id, service_id);
"""

declarative = os.getenv('DANIEL_AUTHENTICATOR_DECLARATIVE_DATABASE') is not None
if declarative:
	database_file = "/tmp/daniel-authenticator-declarative-database.sqlite3"
else:
	database_file = "./data/daniel-authenticator.sqlite3"

def sort_by_username(input):
	return sorted(input, key=lambda x: x['username'])

class Database:
	def __init__(self):
		
		if(exists(database_file)):
			self.conn = sqlite3.connect(database_file)
		else:
			self.conn = sqlite3.connect(database_file)
			self.conn.executescript(database_init_sql_script)
			self.conn.commit()
				
		def dict_factory(cursor, row):
			d = {}
			for idx, col in enumerate(cursor.description):
				d[col[0]] = row[idx]
			return d
		
		#self.conn.row_factory = sqlite3.Row
		self.conn.row_factory = dict_factory
		self.conn.execute('PRAGMA foreign_keys = ON')
		self.conn.commit()
	
	def create_user(self, username, fullname, email, password, active, superuser):
		cursor = self.conn.cursor()
		cursor.execute("""INSERT INTO users(username, fullname, email, uuid, password_hash, active, incorrect_login_attempts, locked, last_login_time, creation_time, superuser)
						VALUES(?, ?, ?, ?, ?, ?, 0, false, "", datetime(), ?)""",
						(username, fullname, email, str(uuid.uuid4()), pswd.make_password_hash(password), active, superuser))
		user_id = cursor.lastrowid
		cursor.close()
		self.conn.commit()
		return user_id
	
	def update_user_successful_login(self, user_id):
		self.conn.execute('UPDATE users SET incorrect_login_attempts=0, last_login_time=datetime() WHERE user_id=?',
							(user_id,))
		self.conn.commit()
	
	def update_user_unsuccessful_login(self, user_id):
		result = self.conn.execute("SELECT incorrect_login_attempts FROM users WHERE user_id = ?",
									(user_id, )).fetchone()
		incorrect_login_attempts = result["incorrect_login_attempts"] + 1
		self.conn.execute('UPDATE users SET incorrect_login_attempts=? WHERE user_id=?',
							(incorrect_login_attempts, user_id))
		self.conn.commit()
		
		if incorrect_login_attempts >= 15:
			self.conn.execute('UPDATE users SET locked=1 WHERE user_id=?',
							(user_id,))
			self.conn.commit()
	
	def attempt_user_login(self, username, password, suppress_successful_log=False):
		user = self.get_user_by_username(username)
		if user is None:
			print("%s Login by user %s failed, user does not exist" % (datetime.now().strftime(TIME_FORMAT), username))
			return None, "Invalid Username or Password"
		elif user["active"] == False:
			print("%s Login by user %s failed, user does not exist" % (datetime.now().strftime(TIME_FORMAT), username))
			return None, "Account was set inactive by an administrator"
		elif user["locked"]:
			print("%s Login by user %s failed, user does not exist" % (datetime.now().strftime(TIME_FORMAT), username))
			return None, "Account is locked due to too many failed login attempts; Please contact an administrator"
		else:
			if check_password(password, user["password_hash"]):
				if not suppress_successful_log:
					print("%s Login by user %s succeeded" % (datetime.now().strftime(TIME_FORMAT), username))
				self.update_user_successful_login(user["user_id"])
				return user, "Login Successful"
			else:
				print("%s Login by user %s failed, incorrect password" % (datetime.now().strftime(TIME_FORMAT), username))
				self.update_user_unsuccessful_login(user["user_id"])
				return None, "Invalid Username or Password"
	
	def attempt_user_login_with_service(self, username, password, service_username):
		user = self.get_user_by_username(username)
		
		user_info, message = self.attempt_user_login(username, password, suppress_successful_log=True)
		if user_info is None:
			return None, message
		
		service_info = self.get_service_by_username(service_username)
		if service_info is None:
			print("%s Login by user %s failed because service %s does not exist" % (datetime.now().strftime(TIME_FORMAT), username, service_username))
			return None, "Invalid Username or Password"
		
		service_memberships = self.get_user_service_memberships(user_info['user_id'])
		if service_info in service_memberships:
			print("%s Login by user %s through service %s succeeded" % (datetime.now().strftime(TIME_FORMAT), username, service_username))
			return user_info, message
		else:
			print("%s Login by user %s failed because they are not a member of service %s" % (datetime.now().strftime(TIME_FORMAT), username, service_username))
			return None, "Invalid Username or Password"
	
	def attempt_service_login(self, username, password):
		service = self.get_service_by_username(username)
		if service is not None and service["active"]:
			if check_password(password, service["password_hash"]):
				return service
			else:
				print("%s Login by service %s failed, incorrect password" % (datetime.now().strftime(TIME_FORMAT), username))
				return None
		else:
			print("%s Login by service %s failed, services does not exist" % (datetime.now().strftime(TIME_FORMAT), username))
			return None
	
	def delete_user(self, user_id):
		self.conn.execute('DELETE FROM users WHERE user_id=?',
							(user_id,))
		self.conn.commit()
	
	def get_user_info(self, user_id):
		result = self.conn.execute("""SELECT user_id, username, fullname, email, uuid, password_hash,
									active, incorrect_login_attempts, locked, last_login_time, creation_time, superuser FROM users WHERE user_id = ?""",
									(user_id, )).fetchone()
		return result
	
	def get_user_by_username(self, username):
		result = self.conn.execute("""SELECT user_id, username, fullname, email, uuid, password_hash,
									active, incorrect_login_attempts, locked, last_login_time, creation_time, superuser FROM users WHERE username = ?""",
									(username, )).fetchall()
		if len(result) == 1:
			return result[0]
		else:
			return None
	
	def get_user_by_email(self, email):
		result = self.conn.execute("""SELECT user_id, username, fullname, email, uuid, password_hash,
									active, incorrect_login_attempts, locked, last_login_time, creation_time, superuser FROM users WHERE email = ?""",
									(email, )).fetchall()
		if len(result) == 1:
			return result[0]
		else:
			return None
	
	def get_all_users_info(self):
		result = self.conn.execute("""SELECT user_id, username, fullname, email, uuid, password_hash,
									active, incorrect_login_attempts, locked, last_login_time, creation_time, superuser FROM users""").fetchall()
		return sort_by_username(result)
	
	def create_service(self, username, fullname, hyperlink, password, active):
		cursor = self.conn.cursor()
		cursor.execute('INSERT INTO services(username, fullname, hyperlink, password_hash, active) VALUES(?, ?, ?, ?, ?)',
						(username, fullname, hyperlink, pswd.make_password_hash(password), active))
		service_id = cursor.lastrowid
		cursor.close()
		self.conn.commit()
		return service_id
	
	def delete_service(self, service_id):
		self.conn.execute('DELETE FROM services WHERE service_id=?',
							(service_id,))
		self.conn.commit()
	
	def get_service_info(self, service_id):
		result = self.conn.execute('SELECT service_id, username, fullname, hyperlink, password_hash, active FROM services WHERE service_id = ?',
									(service_id, )).fetchone()
		return result
	
	def get_service_by_username(self, username):
		result = self.conn.execute('SELECT service_id, username, fullname, hyperlink, password_hash, active FROM services WHERE username = ?',
									(username, )).fetchall()
		if len(result) == 1:
			return result[0]
		else:
			return None
	
	def get_all_services_info(self):
		result = self.conn.execute('SELECT service_id, username, fullname, hyperlink, password_hash, active FROM services').fetchall()
		return sort_by_username(result)
	
	def create_group(self, username, fullname):
		cursor = self.conn.cursor()
		cursor.execute('INSERT INTO groups(username, fullname, uuid) VALUES(?, ?, ?)',
						(username, fullname, str(uuid.uuid4())))
		group_id = cursor.lastrowid
		cursor.close()
		self.conn.commit()
		return group_id
	
	def delete_group(self, group_id):
		self.conn.execute('DELETE FROM groups WHERE group_id=?',
							(group_id,))
		self.conn.commit()
	
	def get_group_info(self, group_id):
		result = self.conn.execute('SELECT group_id, username, fullname, uuid FROM groups WHERE group_id = ?',
									(group_id,)).fetchone()
		return result
	
	def get_group_by_username(self, username):
		result = self.conn.execute('SELECT group_id, username, fullname, uuid FROM groups WHERE username = ?',
									(username,)).fetchall()
		if len(result) == 1:
			return result[0]
		else:
			return None
	
	def get_all_groups_info(self):
		result = self.conn.execute('SELECT group_id, username, fullname, uuid FROM groups').fetchall()
		return sort_by_username(result)
	
	def add_user_to_service(self, user_id, service_id):
		self.conn.execute('INSERT INTO user_service_memberships(user_id, service_id) VALUES(?, ?) ON CONFLICT DO NOTHING',
							(user_id, service_id))
		self.conn.commit()
	
	def remove_user_from_service(self, user_id, service_id):
		self.conn.execute('DELETE FROM user_service_memberships WHERE user_id=? AND service_id=?',
							(user_id, service_id))
		self.conn.commit()
	
	def add_user_to_group(self, user_id, group_id):
		self.conn.execute('INSERT INTO user_group_memberships(user_id, group_id) VALUES(?, ?) ON CONFLICT DO NOTHING',
							(user_id, group_id))
		self.conn.commit()
	
	def remove_user_from_group(self, user_id, group_id):
		self.conn.execute('DELETE FROM user_group_memberships WHERE user_id=? AND group_id=?',
							(user_id, group_id))
		self.conn.commit()
	
	def add_group_to_service(self, group_id, service_id):
		self.conn.execute('INSERT INTO group_service_memberships(group_id, service_id) VALUES(?, ?) ON CONFLICT DO NOTHING',
							(group_id, service_id))
		self.conn.commit()
		
	def remove_group_from_service(self, group_id, service_id):
		self.conn.execute('DELETE FROM group_service_memberships WHERE group_id=? AND service_id=?',
							(group_id, service_id))
		self.conn.commit()
	
	def get_users_in_service(self, service_id):
		result = self.conn.execute("""SELECT user_id, username, fullname, email, uuid, password_hash,
										active, incorrect_login_attempts, locked, last_login_time, creation_time, superuser
										FROM users INNER JOIN user_service_memberships USING (user_id) WHERE service_id=?""",
									(service_id,)).fetchall()
		return sort_by_username(result)
	
	def get_users_in_group(self, group_id):
		result = self.conn.execute("""SELECT user_id, username, fullname, email, uuid, password_hash,
										active, incorrect_login_attempts, locked, last_login_time, creation_time, superuser
										FROM users INNER JOIN user_group_memberships USING (user_id) WHERE group_id=?""",
									(group_id,)).fetchall()
		return sort_by_username(result)
	
	def get_users_in_group_for_service(self, group_id, service_id):
		result = self.conn.execute("""SELECT user_id, username, fullname, email, uuid, password_hash,
										active, incorrect_login_attempts, locked, last_login_time, creation_time, superuser
										FROM users INNER JOIN user_group_memberships USING (user_id)
										INNER JOIN user_service_memberships USING (user_id) WHERE group_id=? AND service_id=?""",
									(group_id,service_id)).fetchall()
		return sort_by_username(result)
	
	def get_groups_in_service(self, service_id):
		result = self.conn.execute("""SELECT group_id, username, fullname, uuid
										FROM groups INNER JOIN group_service_memberships USING (group_id) WHERE service_id=?""",
									(service_id,)).fetchall()
		return sort_by_username(result)
	
	def get_user_service_memberships(self, user_id):
		result = self.conn.execute("""SELECT service_id, username, fullname, hyperlink, password_hash, active
										FROM services INNER JOIN user_service_memberships USING (service_id) WHERE user_id=?""",
									(user_id,)).fetchall()
		return result
	
	def get_user_group_memberships(self, user_id):
		result = self.conn.execute("""SELECT group_id, username, fullname, uuid
										FROM groups INNER JOIN user_group_memberships USING (group_id) WHERE user_id=?""",
									(user_id,)).fetchall()
		return sort_by_username(result)
	
	def get_user_group_memberships_for_service(self, user_id, service_id):
		result = self.conn.execute("""SELECT group_id, username, fullname, uuid FROM groups
										INNER JOIN user_group_memberships USING (group_id)
										INNER JOIN group_service_memberships USING (group_id) WHERE user_id=? AND service_id=?""",
									(user_id,service_id)).fetchall()
		return sort_by_username(result)
	
	def get_group_service_memberships(self, group_id):
		result = self.conn.execute("""SELECT service_id, username, fullname, hyperlink, password_hash, active
										FROM services INNER JOIN group_service_memberships USING (service_id) WHERE group_id=?""",
									(group_id,)).fetchall()
		return sort_by_username(result)
	
	def set_user_fullname(self, user_id, fullname):
		self.conn.execute('UPDATE users SET fullname=? WHERE user_id=?',
							(fullname, user_id))
		self.conn.commit()
	
	def set_group_fullname(self, group_id, fullname):
		self.conn.execute('UPDATE groups SET fullname=? WHERE group_id=?',
							(fullname, group_id))
		self.conn.commit()
	
	def set_service_fullname(self, service_id, fullname):
		self.conn.execute('UPDATE services SET fullname=? WHERE service_id=?',
							(fullname, service_id))
		self.conn.commit()
	
	def set_user_password(self, user_id, password):
		self.conn.execute('UPDATE users SET password_hash=? WHERE user_id=?',
							(pswd.make_password_hash(password), user_id))
		self.conn.commit()
	
	def set_user_password_using_freeipa_hash(self, user_id, password_hash):
		self.conn.execute('UPDATE users SET password_hash=? WHERE user_id=?',
							(pswd.decode_freeipa(password_hash), user_id))
		self.conn.commit()
	
	def set_service_password_using_freeipa_hash(self, service_id, password_hash):
		self.conn.execute('UPDATE services SET password_hash=? WHERE service_id=?',
							(pswd.decode_freeipa(password_hash), service_id))
		self.conn.commit()
	
	def set_service_password(self, service_id, password):
		self.conn.execute('UPDATE services SET password_hash=? WHERE service_id=?',
							(pswd.make_password_hash(password), service_id))
		self.conn.commit()
	
	def set_user_email(self, user_id, email):
		self.conn.execute('UPDATE users SET email=? WHERE user_id=?',
							(email, user_id))
		self.conn.commit()
	
	def set_service_hyperlink(self, service_id, hyperlink):
		self.conn.execute('UPDATE services SET hyperlink=? WHERE service_id=?',
							(hyperlink, service_id))
		self.conn.commit()
	
	def set_user_active(self, user_id, active):
		self.conn.execute('UPDATE users SET active=? WHERE user_id=?',
							(active, user_id))
		self.conn.commit()
	
	def set_user_superuser(self, user_id, superuser):
		self.conn.execute('UPDATE users SET superuser=? WHERE user_id=?',
							(superuser, user_id))
		self.conn.commit()
	
	def set_service_active(self, service_id, active):
		self.conn.execute('UPDATE services SET active=? WHERE service_id=?',
							(active, service_id))
		self.conn.commit()
	
	def unlock_user(self, user_id):
		self.conn.execute('UPDATE users SET locked=0, incorrect_login_attempts=0 WHERE user_id=?',
							(user_id,))
		self.conn.commit()
		
	def set_user_uuid(self, user_id, uuid):
		self.conn.execute('UPDATE users SET uuid=? WHERE user_id=?',
							(uuid, user_id))
		self.conn.commit()
		
	def set_group_uuid(self, group_id, uuid):
		self.conn.execute('UPDATE groups SET uuid=? WHERE group_id=?',
							(uuid, group_id))
		self.conn.commit()
		
	
