# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity
from creme_core.registry import creme_registry
from creme_core.gui.menu import creme_menu
from creme_core.gui.block import block_registry
from creme_core.gui.bulk_update import bulk_update_registry
from creme_core.blocks import relations_block, properties_block, customfields_block


User._meta.ordering = ('username',)

#Those fields haven't to be accessible to users from IHM
#TODO: currently the restriction is applied only in list_view via header filters, so extend to all the app ?
User.header_filter_exclude_fields = ['id', 'pk', 'password', 'is_active', 'is_superuser', 'is_staff', 'last_login', 'date_joined']

ContentType.__unicode__ = lambda self: ugettext(self.name)


creme_registry.register_app('creme_core', _(u'Core'), '/')

creme_menu.register_app('creme_core', '/', _(u'Home'), force_order=0)

block_registry.register(relations_block, properties_block, customfields_block)

bulk_update_registry.register(
    (CremeEntity, ['created', 'modified']),
)
