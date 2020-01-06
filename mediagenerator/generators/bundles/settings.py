from django.conf import settings

DEFAULT_MEDIA_FILTERS = getattr(settings, 'DEFAULT_MEDIA_FILTERS', {
    'ccss': 'mediagenerator.filters.clever.CleverCSS',
    'css': 'mediagenerator.filters.cssurl.CSSURLFileFilter',
    'html': 'mediagenerator.filters.template.Template',
    'less': 'mediagenerator.filters.less.Less',
})

ROOT_MEDIA_FILTERS = getattr(settings, 'ROOT_MEDIA_FILTERS', {})

# These are applied in addition to ROOT_MEDIA_FILTERS.
# The separation is done because we don't want users to
# always specify the default filters when they merely want
# to configure YUICompressor or Closure.
BASE_ROOT_MEDIA_FILTERS = getattr(settings, 'BASE_ROOT_MEDIA_FILTERS', {
    '*': 'mediagenerator.filters.concat.Concat',
    'css': 'mediagenerator.filters.cssurl.CSSURL',
})

MEDIA_BUNDLES = getattr(settings, 'MEDIA_BUNDLES', ())
