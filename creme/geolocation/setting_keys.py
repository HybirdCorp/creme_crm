# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey


NEIGHBOURHOOD_DISTANCE = SettingKey(id='geolocation-neighbourhood_distance',
                                    description=_(u'Maximum distance to find neighbours in meters'),
                                    app_label='geolocation',
                                    type=SettingKey.INT,
                                   )

GOOGLE_API_KEY = SettingKey(id='geolocation-google_api_key',
                            description=_(u'Google Maps ® API key (optional)'),
                            app_label='geolocation',
                            type=SettingKey.STRING,
                            blank=True,
                           )
