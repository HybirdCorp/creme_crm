# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015  Hybird
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
#from django.db import transaction
#from django.db.transaction import atomic

from django.db.models.signals import post_save, post_delete
from django.dispatch.dispatcher import receiver

#from creme.persons.models import Address

from .models import GeoAddress, Town


#@receiver(post_delete, sender=Address)
@receiver(post_delete, sender=settings.PERSONS_ADDRESS_MODEL)
def dispose_geoaddresses(sender, instance, **kwargs):
#    sid = transaction.savepoint()
#
#    try:
#        instance.geoaddress.delete()
#    except GeoAddress.DoesNotExist:
#        transaction.savepoint_rollback(sid)
#    else:
#        transaction.savepoint_commit(sid)
    try:
        #with atomic(): #NB: seems useless (it seems DoesNotExist do not corrupt the current transaction even with PostGreSQL)
        instance.geoaddress.delete()
    except GeoAddress.DoesNotExist:
        pass

#@receiver(post_save, sender=Address)
@receiver(post_save, sender=settings.PERSONS_ADDRESS_MODEL)
def update_geoaddresses(sender, instance, **kwargs):
#    sid = transaction.savepoint()
#
#    try:
#        geoaddress = instance.geoaddress
#    except GeoAddress.DoesNotExist:
#        transaction.savepoint_rollback(sid)
#        #instance.geoaddress = # NB: not useful with django1.5+
#        geoaddress = GeoAddress(address=instance)
#        sid = transaction.savepoint()
#
#    town = Town.search(instance)
#
#    geoaddress.set_town_position(town)
#    geoaddress.save()
#
#    transaction.savepoint_commit(sid)
    try:
        #with atomic(): #NB: see above
        geoaddress = instance.geoaddress
    except GeoAddress.DoesNotExist:
        #instance.geoaddress = # NB: not useful with django1.5+
        geoaddress = GeoAddress(address=instance)

    geoaddress.set_town_position(Town.search(instance))
    geoaddress.save()
