from functools import partial

from django.forms import URLField
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

LOCATION_MAP_URL = SettingKey(
    id='mobile-location_map_url',
    description=_(
        'URL pattern to map & geolocation services.'
        # "Use {search} placeholder for the address and if geolocation is enabled, "
        # "{lat} & {lng} coordinates can be used too."
    ),
    app_label='mobile',
    type=SettingKey.STRING,
    formfield_class=partial(
        URLField,
        help_text=format_lazy((
            '{explanation}\n'
            ' − https://www.openstreetmap.org/search?query={{search}}\n'
            ' − https://www.openstreetmap.org#map=18/{{lat}}/{{lng}}\n'
            ' − https://www.google.com/maps/?q={{search}}\n'
            ' − https://maps.google.com/maps/place/{{lat}},{{lng}}'
        ), explanation=_(
            'Use {search} placeholder for the address and if geolocation is '
            'enabled, {lat} & {lng} coordinates can be used too.'
        ))
    ),
)
