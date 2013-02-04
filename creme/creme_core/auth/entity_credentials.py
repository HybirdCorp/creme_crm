# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

VIEW_PERM   = 'creme_core.view_entity'
CHANGE_PERM = 'creme_core.change_entity'
DELETE_PERM = 'creme_core.delete_entity'
LINK_PERM   = 'creme_core.link_entity'
UNLINK_PERM = 'creme_core.unlink_entity'


#TODO: move to auth/
class EntityCredentials(object):
    NONE   =  0
    #ADD    =  1 #0b000001   #useless...
    VIEW   =  2 #0b000010
    CHANGE =  4 #0b000100
    DELETE =  8 #0b001000
    LINK   = 16 #0b010000
    UNLINK = 32 #0b100000

    _ALL_CREDS = 63

    _PERMS_MAP = {VIEW_PERM:   VIEW,
                  CHANGE_PERM: CHANGE,
                  DELETE_PERM: DELETE,
                  LINK_PERM:   LINK,
                  UNLINK_PERM: UNLINK,
                 }

    def __init__(self, user, entity):
        """Constructor.
        @param user django.contrib.auth.models.User instance.
        @param entity CremeEntity instance.
        """
        if user.is_superuser:
            value = EntityCredentials._ALL_CREDS
        else:
            role = user.role
            assert role is not None

            value = role.get_perms(user, entity)

        self._value = value

    def __unicode__(self):
        return u'EntityCredentials(value="%s")' % self.value

    def can_change(self):
        return self.has_perm(CHANGE_PERM)

    def can_delete(self):
        return self.has_perm(DELETE_PERM)

    def can_link(self):
        return self.has_perm(LINK_PERM)

    def can_unlink(self):
        return self.has_perm(UNLINK_PERM)

    def can_view(self):
        return self.has_perm(VIEW_PERM)

    def has_perm(self, string_permission):
        return bool(self._PERMS_MAP.get(string_permission) & self._value)

    @staticmethod
    def filter(user, queryset, perm=VIEW):
        """Filter a Queryset of CremeEntities with their 'view' credentials.
        @param queryset A Queryset on CremeEntity models (better if not yet retrieved).
        @param perm A value in: VIEW, CHANGE, DELETE, LINK, UNLINK [TODO: allow combination]
        @return A new Queryset on CremeEntity, more selective (not retrieved).
        """
        if not user.is_superuser:
            assert user.role is not None
            queryset = user.role.filter(user, queryset, perm)

        return queryset
