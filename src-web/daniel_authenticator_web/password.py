import base64
import struct

from passlib.hash import pbkdf2_sha256
from passlib.utils.binary import ab64_encode

def decode_freeipa(raw):
	packed = base64.b64decode(raw).decode("utf-8")
	assert packed[0:15] == "{PBKDF2_SHA256}"
	packed = packed[15:]
	assert len(packed) == 432
	binary = base64.b64decode(packed)
	iterations = struct.unpack(">i", binary[0:4])[0]
	salt = binary[4:(4+64)]
	hash = binary[(4+64):(4+64+32)]#the freeipa hash is 256, but passlib only wants 32
	
	return "$pbkdf2-sha256$%i$%s$%s" % (iterations, ab64_encode(salt).decode("utf-8"), ab64_encode(hash).decode("utf-8"))

def check_password(password, hash):
	return pbkdf2_sha256.verify(password, hash)

def make_password_hash(password):
	return pbkdf2_sha256.hash(password)
  
  
