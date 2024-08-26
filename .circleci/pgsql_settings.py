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

BILLING_EXPORTERS = [
    'creme.billing.exporters.xls.XLSExportEngine',
    # 'creme.billing.exporters.xhtml2pdf.Xhtml2pdfExportEngine',
    'creme.billing.exporters.weasyprint.WeasyprintExportEngine',
]
