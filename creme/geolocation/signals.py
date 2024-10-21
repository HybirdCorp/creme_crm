################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2024  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#
#    GNU Affero General Public License for more details.
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch.dispatcher import receiver

from .models import GeoAddress, Town


@receiver(post_delete, sender=settings.PERSONS_ADDRESS_MODEL, dispatch_uid='geolocation-dispose')
def dispose_geoaddresses(sender, instance, **kwargs):
    try:
        instance.geoaddress.delete()
    except GeoAddress.DoesNotExist:
        pass


@receiver(post_save, sender=settings.PERSONS_ADDRESS_MODEL, dispatch_uid='geolocation-update')
def update_geoaddresses(sender, instance, **kwargs):
    try:
        geoaddress = instance.geoaddress
    except GeoAddress.DoesNotExist:
        geoaddress = GeoAddress(address=instance)

    geoaddress.set_town_position(Town.search(instance))
    geoaddress.save()
