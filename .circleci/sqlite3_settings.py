LANGUAGE_CODE = 'fr'

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.sqlite3',
        'NAME':     'cremecrm.sqlite',
        'TEST': {
            'MIGRATE': False,
        },
    },
}
