# -*- coding: utf-8 -*-

from django.utils.translation import gettext as _

from creme.creme_core.core.setting_key import SettingKey

LOCATION_MAP_URL = SettingKey(
    id='mobile-location_map_url',
    description='\n'.join((
        _("Url pattern to map & geolocation services.\n"
          "Use {search} placeholder for the address and if geolocation is enabled, "
          "{lat} & {lng} coordinates can be used too."
         ),
        ' − https://www.openstreetmap.org/search?query={search}',
        ' − https://www.openstreetmap.org#map=18/{lat}/{lng}',
        ' − https://www.google.com/maps/?q={search}',
        ' − https://maps.google.com/maps/place/{lat},{lng}',
    )),
    app_label='mobile',
    type=SettingKey.STRING,
)
