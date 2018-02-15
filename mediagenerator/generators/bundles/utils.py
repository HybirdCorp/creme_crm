import os

from .settings import ROOT_MEDIA_FILTERS, MEDIA_BUNDLES, BASE_ROOT_MEDIA_FILTERS

from mediagenerator.settings import MEDIA_DEV_MODE
from mediagenerator.utils import load_backend, media_urls


_cache = {}


def _load_root_filter(bundle):
    if bundle not in _cache:
        _cache[bundle] = _load_root_filter_uncached(bundle)

    return _cache[bundle]


def _get_root_filters_list(filetype):
    root_filters = ()
    filetypes = (filetype, '*')

    for filters_spec in (BASE_ROOT_MEDIA_FILTERS, ROOT_MEDIA_FILTERS):
        for filetype in filetypes:
            filters = filters_spec.get(filetype, ())

            if not isinstance(filters, (tuple, list)):
                filters = (filters, )

            root_filters += tuple(filters)

    return root_filters


def _load_root_filter_uncached(bundle):
    for items in MEDIA_BUNDLES:
        if items[0] == bundle:
            input = items[1:]
            break
    else:
        raise ValueError('Could not find media bundle "%s"' % bundle)

    filetype = os.path.splitext(bundle)[-1].lstrip('.')
    root_filters = _get_root_filters_list(filetype)
    backend_class = load_backend(root_filters[-1])

    for filter in reversed(root_filters[:-1]):
        input = [{'filter': filter, 'input': input}]

    return backend_class(filter=root_filters[-1],
                         filetype=filetype,
                         bundle=bundle,
                         input=input,
                        )


def _get_key(bundle, variation_map=None):
    if variation_map:
        bundle += '?' + '&'.join('='.join(item) for item in variation_map)

    return bundle


def _render_include_media(bundle, variation):
    variation = variation.copy()
    filetype = os.path.splitext(bundle)[-1].lstrip('.')

    # The "media" variation is special and defines CSS media types
    media_types = None
    if filetype == 'css':
        media_types = variation.pop('media', None)

    if MEDIA_DEV_MODE:
        root = _load_root_filter(bundle)
        variations = root._get_variations_with_input()
        variation_map = [(key, variation.pop(key)) for key in sorted(variations.keys())]

        if variation:
            raise ValueError('Bundle %s does not support the following variation(s): %s'
                             % (bundle, ', '.join(variation.keys())))
    else:
        variation_map = tuple((key, variation[key]) for key in sorted(variation.keys()))

    urls = media_urls(_get_key(bundle, variation_map))

    if filetype == 'css':
        if media_types:
            tag = u'<link rel="stylesheet" type="text/css" href="%%s" media="%s" />' % media_types
        else:
            tag = u'<link rel="stylesheet" type="text/css" href="%s" />'
    elif filetype == 'js':
        tag = u'<script type="text/javascript" src="%s"></script>'
    else:
        raise ValueError("""Don't know how to include file type "%s".""" % filetype)

    return '\n'.join(tag % url for url in urls)
