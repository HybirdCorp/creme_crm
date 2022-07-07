from hashlib import sha1

from django.apps import apps
from django.conf import settings
from django.http import HttpRequest
from django.utils import translation
from django.utils.encoding import smart_str
from django.views.i18n import JavaScriptCatalog  # javascript_catalog

from mediagenerator.generators.bundles.base import Filter

if settings.USE_I18N:
    LANGUAGES = [code for code, _ in settings.LANGUAGES]
else:
    LANGUAGES = (settings.LANGUAGE_CODE,)


class I18N(Filter):
    takes_input = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        assert self.filetype == 'js', (
            f'I18N only supports compilation to js. '
            f'The parent filter expects "{self.filetype}".')

    def get_variations(self):
        return {'language': LANGUAGES}

    def get_output(self, variation):
        language = variation['language']
        yield self._generate(language)

    def get_dev_output(self, name, variation):
        language = variation['language']
        assert language == name

        return self._generate(language)

    def get_dev_output_names(self, variation):
        language = variation['language']
        content = self._generate(language)
        hash = sha1(smart_str(content)).hexdigest()
        yield language, hash

    def _generate(self, language):
        language_bidi = language.split('-')[0] in settings.LANGUAGES_BIDI

        # Hybird FIX - Django1.10 version
        # request = HttpRequest()
        # request.GET['language'] = language

        # Add some JavaScript data
        content = f'var LANGUAGE_CODE = "{language}";\n'
        content += 'var LANGUAGE_BIDI = ' + \
            (language_bidi and 'true' or 'false') + ';\n'

        # content += javascript_catalog(request,
        #     packages=settings.INSTALLED_APPS).content

        # Hybird FIX - Django1.8 version
        # content += javascript_catalog(
        #                 request,
        #                 packages=[app_config.name for app_config in apps.app_configs.values()],
        #             ).content
        # Hybird FIX - Django1.10 version
        translation.activate(language)
        # content += JavaScriptCatalog(
        #     packages=[app_config.name for app_config in apps.app_configs.values()]
        # ).get(HttpRequest()).content
        content += JavaScriptCatalog(
            packages=[app_config.name for app_config in apps.app_configs.values()]
        ).get(HttpRequest()).content.decode()

        # The hgettext() function just calls gettext() internally,
        # but it won't get indexed by makemessages.
        content += '\nwindow.hgettext = function(text) { return gettext(text); };\n'
        # Add a similar hngettext() function
        content += (
            'window.hngettext = function(singular, plural, count) {'
            ' return ngettext(singular, plural, count); '
            '};\n'
        )

        return content
