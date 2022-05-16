LANGUAGE_CODE = 'en'

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     'cremecrm',
        'USER':     'creme',
        'PASSWORD': 'creme',
        'HOST':     '127.0.0.1',
        'PORT':     '5432',
        'OPTIONS':  {},
        'TEST': {
            'MIGRATE': False,
        },
    },
}
