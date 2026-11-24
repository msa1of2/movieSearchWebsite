import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

class CookieManager:
	AUTH_ADMIN = 1 # Can change the admin console to affect the website's behaviours

	def __init__(self):
		self.cookies = {}

	def newCookie(self, privliges = 0, expiration = 60*60):
		cookie = Cookie.newCookie(privliges, expiration)
		
		for cookKey, cookVal in self.cookies.items():
			if (cookVal.expiration > datetime.now()):
				del self.cookies[cookKey]

		self.cookies[cookie.tokenID] = cookie
		return cookie

	# Safely removes old cookie and makes a new one with specified privliges and expiration
	def replaceCookie(self, tokenID, newPrivliges = 0, newExpiration = 60*60):
		if (tokenID in self.cookies):
			if (newPrivliges != self.cookies[tokenID].auth): #Wrong privliges, dont do anything
				return None
			del self.cookies[tokenID]
		# Old cookie is gone now
		return self.newCookie(newPrivliges, newExpiration)

	def deleteCookie(self, tokenID):
		if (tokenID in self.cookies):
			del self.cookies[tokenID]
			return True
		return False

	def cookieHasPrivlige(self, tokenID, authCheck):
		if (tokenID not in self.cookies):
			return False 
		if (self.cookies[tokenID].expiration > datetime.now()): #deleting old cookies
			del self.cookies[tokenID]
			return False
		# only when bitwise & operation equals itself, does it have at least these privliges
		return ((self.cookies[tokenID].auth & authCheck) == authCheck)

	def cookieExists(self, tokenID):
		return tokenID in self.cookies

@dataclass
class Cookie:
	auth:int = 0 # What privliges does this cookie have
	tokenID:str = field(default_factory=secrets.token_urlsafe) # What is the cookie token associated with this
	expiration:datetime|None = None # When should this cookie delete itself
	username:str = ""
	
	def newCookie(privliges = 0, expiration = 60*60):
		timeExpired = datetime.now() + timedelta(seconds = expiration)
		return Cookie(auth = privliges, tokenID = secrets.token_urlsafe(32), expiration = timeExpired)


