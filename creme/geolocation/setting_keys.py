# import warnings
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


# def __getattr__(name):
#     if name == 'NEIGHBOURHOOD_DISTANCE':
#         warnings.warn(
#             '"NEIGHBOURHOOD_DISTANCE" is deprecated; '
#             'use geolocation.setting_keys.neighbourhood_distance_key instead.',
#             DeprecationWarning,
#         )
#         return neighbourhood_distance_key
#
#     if name == 'GOOGLE_API_KEY':
#         warnings.warn(
#             '"GOOGLE_API_KEY" is deprecated; '
#             'use geolocation.setting_keys.google_api_key instead.',
#             DeprecationWarning,
#         )
#         return google_api_key
#
#     raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
