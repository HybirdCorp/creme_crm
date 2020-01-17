from hashlib import sha1
from json import dumps

from django.utils.encoding import smart_str

from mediagenerator.generators.bundles.base import Filter
from mediagenerator.utils import get_media_url_mapping

_CODE = """
_$MEDIA_URLS = %s;

media_urls = function(key) {
  var urls = _$MEDIA_URLS[key];
  if (!urls)
    throw 'Could not resolve media url ' + key;
  return urls;
};

media_url = function(key) {
  var urls = media_urls(key);
  if (urls.length == 1)
    return urls[0];
  throw 'media_url() only works with keys that point to a single entry (e.g. an image), but not bundles. Use media_urls() instead.';
};
""".lstrip()


class MediaURL(Filter):
    takes_input = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        assert self.filetype == 'js', (
            f'MediaURL only supports JS output. '
            f'The parent filter expects "{self.filetype}".')

    def get_output(self, variation):
        yield self._compile()

    def get_dev_output(self, name, variation):
        assert name == '.media_url.js'
        return self._compile()

    def get_dev_output_names(self, variation):
        content = self._compile()
        hash = sha1(smart_str(content)).hexdigest()
        yield '.media_url.js', hash

    def _compile(self):
        return _CODE % dumps(get_media_url_mapping())
