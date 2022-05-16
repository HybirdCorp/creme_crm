LANGUAGE_CODE = 'fr'

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.mysql',
        'NAME':     'cremecrm',
        'USER':     'root',
        'PASSWORD': 'creme',
        'HOST':     '127.0.0.1',
        'PORT':     '3306',
        'OPTIONS':  {},
        'TEST': {
            'MIGRATE': False,
        },
    },
}
