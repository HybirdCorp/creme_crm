import os

from django.apps import apps
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.management.base import BaseCommand

from creme.creme_core.staticfiles import (
    I18NCatalog,
    JavaScriptBundle,
    StyleSheetBundle,
)


class Command(BaseCommand):
    help = 'Generate media files'

    BUNDLERS = {
        "javascript": JavaScriptBundle,
        "stylesheet": StyleSheetBundle,
    }

    def create_destination(self):
        os.makedirs(settings.CREME_STATICFILES_TMP_DIRECTORY, exist_ok=True)

    def bundle_i18n(self):
        for language_code, _ in settings.LANGUAGES:
            catalog = I18NCatalog(language_code)
            catalog.save(destination=settings.CREME_STATICFILES_TMP_DIRECTORY)

    def bundle_staticfiles(self):
        for bundle in settings.CREME_STATICFILES_BUNDLES:
            bundler_class = self.BUNDLERS[bundle["type"]]
            bundler = bundler_class(filename=bundle["filename"])
            for app_name, filepaths in bundle["files"].items():
                if apps.is_installed(app_name):
                    for filepath in filepaths:
                        bundler.add(filepath, finders.find(filepath))
            bundler.save(destination=settings.CREME_STATICFILES_TMP_DIRECTORY)

    def handle(self, **options):
        self.create_destination()
        self.bundle_staticfiles()
        self.bundle_i18n()
