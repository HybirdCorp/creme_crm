from django import template

from mediagenerator.generators.bundles.utils import _render_include_media
from mediagenerator import utils

register = template.Library()


class MediaNode(template.Node):
    def __init__(self, bundle, variation):
        self.bundle = bundle
        self.variation = variation

    def render(self, context):
        bundle = template.Variable(self.bundle).resolve(context)
        variation = {}
        for key, value in self.variation.items():
            variation[key] = template.Variable(value).resolve(context)

        return _render_include_media(bundle, variation)


@register.tag
def include_media(parser, token):
    try:
        contents = token.split_contents()
        bundle = contents[1]
        variation_spec = contents[2:]
        variation = {}
        for item in variation_spec:
            key, value = item.split('=')
            variation[key] = value
    except (ValueError, AssertionError, IndexError):
        raise template.TemplateSyntaxError(
            '%r could not parse the arguments: the first argument must be the '
            'the name of a bundle in the MEDIA_BUNDLES setting, and the '
            'following arguments specify the media variation (if you have '
            'any) and must be of the form key="value"' % contents[0])

    return MediaNode(bundle, variation)


@register.simple_tag
def media_url(url):
    return utils.media_url(url)


@register.filter
def media_urls(url):
    return utils.media_urls(url)
