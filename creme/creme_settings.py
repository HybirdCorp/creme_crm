# -*- coding: utf-8 -*-

CREME_EMAIL = "" 
CREME_EMAIL_SERVER  = "" 
CREME_EMAIL_USERNAME  = ""
CREME_EMAIL_PASSWORD  = ""
CREME_EMAIL_PORT = 25

CREME_SAMOUSSA_URL = 'http://localhost:8001/'
CREME_SAMOUSSA_USERNAME = 'compte21'
CREME_SAMOUSSA_PASSWORD = 'compte21'

#Mail parameters to sync external email in creme
CREME_GET_EMAIL = "" #Creme get email e.g : creme@cremecrm.org
CREME_GET_EMAIL_SERVER = "" #Creme get server e.g : pop.cremecrm.org (only pop supported for now)
CREME_GET_EMAIL_USERNAME = "" #user
CREME_GET_EMAIL_PASSWORD = "" #pass
CREME_GET_EMAIL_PORT = 110
CREME_GET_EMAIL_SSL = False #True or False #Not used for the moment
CREME_GET_EMAIL_SSL_KEYFILE = "" #Not used for the moment
CREME_GET_EMAIL_SSL_CERTFILE = "" #Not used for the moment

try:
    from local_creme_settings import *
except ImportError:
    pass
