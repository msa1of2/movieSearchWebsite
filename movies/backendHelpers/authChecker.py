from .cookieManager import CookieManager


class Auth:
	passes = { #Look, this is a small thing, I don't care about proper password storage until the thought of exposing this to the internet crosses my mind
		'admin': 'admin'
	}
	perms = {
		'admin': [CookieManager.AUTH_ADMIN,]
	}
	initalized = False

	def __init__():
		initalized = True

	def init():
		__init__()

	def loginAdmin(user, password):
		return password == Auth.passes['admin']

	#Returns all the flags this type has associated with it
	def getPerms(authType):
		result = 0
		if authType not in Auth.perms or not isinstance(Auth.perms[authType], list):
			return 0
		for i in Auth.perms[authType]:
			result |= i
		return result

	def login(user, password, request):
		if (request.lower() == 'admin'):
			return Auth.loginAdmin(user, password)
		else:
			return False

	def loginCookie(CM, username, password, authType):
		if (not Auth.login(username, password, authType)):
			return None
		#Logged in successfully	
		cookie = CM.newCookie(Auth.getPerms(authType), 60*60*24) #Lasts for 1 day
		cookie.username = username
		return cookie
