# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme_core.views.generic import app_portal

from creme_config.utils.url_generator import generate_portal_url

from events.models import Event


def portal(request):
    stats = (
                (_('Number of events'), Event.objects.count()),
            )

    return app_portal(request, 'events', 'events/portal.html', Event, stats,
                      config_url=generate_portal_url('events'))
