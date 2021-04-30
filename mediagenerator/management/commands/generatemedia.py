from django.core.management.base import BaseCommand

from ...api import generate_media


class Command(BaseCommand):
    help = 'Combines and compresses your media files and saves them in _generated_media.'
    leave_locale_alone = True
    # requires_system_checks = False
    requires_system_checks = []

    def handle(self, **options):
        generate_media()
