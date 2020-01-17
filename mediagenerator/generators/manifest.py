from django.conf import settings
from django.template.loader import render_to_string

from mediagenerator.base import Generator
from mediagenerator.utils import get_media_mapping, prepare_patterns

OFFLINE_MANIFEST = getattr(settings, 'OFFLINE_MANIFEST', {})
if isinstance(OFFLINE_MANIFEST, str):
    OFFLINE_MANIFEST = {OFFLINE_MANIFEST: '.*'}


def get_tuple(data, name, default=()):
    result = data.get(name, default)

    return (result,) if isinstance(result, str) else result


class Manifest(Generator):
    def generate_version(self, key, url, content):
        return None

    def get_dev_output(self, name):
        config = OFFLINE_MANIFEST[name]
        if isinstance(config, (tuple, list)):
            config = {'cache': config}
        elif isinstance(config, str):
            config = {'cache': (config,)}

        cache_pattern = prepare_patterns(get_tuple(config, 'cache', '.*'),
                                         f'OFFLINE_MANIFEST[{name}]',
                                        )
        exclude = prepare_patterns(get_tuple(config, 'exclude'),
                                   f"OFFLINE_MANIFEST[{name}]['exclude']",
                                  )
        cache = set()
        for item in get_media_mapping().keys():
            if cache_pattern.match(item) and not exclude.match(item):
                cache.add(item)
        cache -= set(OFFLINE_MANIFEST.keys())

        network = get_tuple(config, 'network', ('*',))
        fallback = get_tuple(config, 'fallback')

        template = get_tuple(config, 'template') + (
            'mediagenerator/manifest/' + name,
            'mediagenerator/manifest/base.manifest'
        )

        content = render_to_string(template, {
            'cache': cache, 'network': network, 'fallback': fallback,
        })
        return content, 'text/cache-manifest'

    def get_dev_output_names(self):
        for name in OFFLINE_MANIFEST:
            yield name, name, None
