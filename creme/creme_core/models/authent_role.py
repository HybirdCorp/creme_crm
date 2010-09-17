# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

#TODO : Fonctions unicode a lever / modifier

import logging

from django.db.models.query import QuerySet
from django.db.models import CharField, ForeignKey, ManyToManyField, Model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.auth.models import User
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeModel, CremeTypeDroit, CremeAppDroit, CremeAppTypeDroit, CremeDroitEntityType, CremeTypeEnsembleFiche
from creme_core.models.fields import CreationDateTimeField, ModificationDateTimeField


class CremeRole(CremeModel):
    created            = CreationDateTimeField(_('Creation date'))
    modified           = ModificationDateTimeField(_('Last modification'))
    name               = CharField(_(u"Name"), max_length=100)
    superieur          = ForeignKey('self', verbose_name=_(u"Superior"), blank=True, null=True, related_name='subordonne_set')
    droits_entity_type = ManyToManyField(CremeDroitEntityType, verbose_name=_(u"Credentials on resources"), blank=True, null=True)
    droits_app         = ManyToManyField(CremeAppDroit, verbose_name=_(u"Application credentials"), blank=True , null=True )

    class Meta:
        app_label = 'creme_core'

#    def get_descendants_as_list(self):
#        _descendants = CremeRole.objects.filter(superieur=self)
#        others = []
#        for sub_role in _descendants:
#            others += sub_role.get_descendants()
#        return list(_descendants)+others

    #TODO: rename to children
    def get_descendants(self, include_self=False):
        """
            Return a queryset which contains all sub-roles of a role with self role or not
        """
        if include_self:
            return self._get_descendants() | CremeRole.objects.filter(id=self.id)
        return self._get_descendants()

    def _get_descendants(self):
        """
            Return a queryset which contains all sub-roles of a role
        """
        _descendants = CremeRole.objects.filter(superieur=self)
        for sub_role in _descendants:
            _descendants |= sub_role._get_descendants()
        return _descendants

    #TODO: rename to parents
    def get_ascendants(self, include_self=False):
        """
            Return a queryset which contains all superior-roles of a role with self role or not
        """
        if include_self:
            return self._get_ascendants() | CremeRole.objects.filter(id=self.id)
        return self._get_ascendants()

    def _get_ascendants(self):
        """
            Return a queryset which contains all superior-roles of a role
        """
        if self.superieur is None:
            return CremeRole.objects.none()
        _ascendants = CremeRole.objects.filter(id=self.superieur.id)
        for sup_role in _ascendants:
            _ascendants |= sup_role._get_ascendants()
        return _ascendants

    def __cmp__(self, other):
        if other in self.get_descendants():
            return 1
        elif other in self.get_ascendants():
            return -1
        else:
            return 0

    def __unicode__(self):
#        return '|Name:%s - Superieur:%s - DroitEntityType:%s - DroitsApp:%s|' % (self.name, self.superieur, self.droits_entity_type.all(), self.droits_app.all())
        return force_unicode('%s - %s' % (self.name, self.superieur))

    def get_absolute_url(self):
        return '/creme_config/roles/%s' % self.id

    def get_all_droits_entity_type(self, include_self=False):
        #TODO : Traitement possible en bd avec queryset ?
        return set(credential
                       for role in self.get_descendants(include_self)
                           for credential in role.droits_entity_type.all())

    def get_all_droits_app(self, include_self=False):
        #TODO : Traitement possible en bd avec queryset ?
        return set(credential
                       for role in self.get_descendants(include_self)
                           for credential in role.droits_app.all())

    def delete(self):
        def change_assign(subs, new_sup):
            for sub in subs:
                sub.superieur = new_sup
                sub.save()

        subs = CremeRole.objects.filter(superieur=self)
        if subs:
            if self.superieur is not None:
                change_assign(subs, self.superieur)
            else:
                potential_admins = CremeRole.objects.filter(superieur=None)
                if potential_admins:
                    change_assign(subs, potential_admins[0])
                else:
                    c = CremeRole(name='Temporary admin', superieur=None)
                    c.save()
                    change_assign(subs, c)
        super(CremeRole, self).delete()


class CremeProfile(Model):
    # This is the only required field
    user       = ForeignKey(User, unique=True)
    creme_role = ForeignKey(CremeRole, blank=True, null=True)
    #creme_contact = ForeignKey(Contact, blank=True, null=True )

    class Meta:
        app_label = 'creme_core'

    def __unicode__(self):
        return force_unicode('User : %s - |Role: %s |' % (self.user, self.creme_role))

    def get_absolute_url(self):
        return '/creme_config/profile/%s' % self.id
