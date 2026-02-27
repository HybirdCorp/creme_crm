from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

neighbourhood_distance_key = SettingKey(
    id='geolocation-neighbourhood_distance',
    description=_('Maximum distance to find neighbours in meters'),
    app_label='geolocation',
    type=SettingKey.INT,
)

# NB: yes "key" is here for SettingKey naming convention AND it works for "API key" too. lol
google_api_key = SettingKey(
    id='geolocation-google_api_key',
    description=_('Google Maps ® API key (optional)'),
    app_label='geolocation',
    type=SettingKey.STRING,
    blank=True,
)

use_entity_icon_key = SettingKey(
    id='geolocation-use_entity_icon_key',
    description=_('Show customizable marker icon of address related entity'),
    app_label='geolocation',
    type=SettingKey.BOOL,
)
