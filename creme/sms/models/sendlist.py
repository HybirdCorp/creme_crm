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

from django.db.models import CharField, ManyToManyField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity

from persons.models import Contact #, Organisation


class SendList(CremeEntity):
    name          = CharField(_(u'Nom de la liste de diffusion'), max_length=80)
    contacts      = ManyToManyField(Contact, verbose_name=u'Contacts destinataires')
#    organisations = ManyToManyField(Organisation, verbose_name=u'Sociétés destinataires')

    class Meta:
        app_label = "sms"
        verbose_name = _(u'Liste de diffusion')
        verbose_name_plural = _(u'Listes de diffusion')

    def __unicode__(self) :
        return self.name

    def get_absolute_url(self):
        return "/sms/sendlist/%s" % self.id

    def get_edit_absolute_url(self):
        return "/sms/sendlist/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        return "/sms/sendlists"

#    def already_in_parents(self, other_ml_id):
#        parents = self.parents_set.all()
#
#        for parent in parents:
#            if parent.id == other_ml_id:
#                return True
#
#        for parent in parents:
#            if parent.already_in_parents(other_ml_id):
#                return True
#
#        return False
#
#    def already_in_children(self, other_ml_id):
#        children = self.children.all()
#
#        for child in children:
#            if child.id == other_ml_id:
#                return True
#
#        for child in children:
#            if child.already_in_children(other_ml_id):
#                return True
#
#        return False

#    def get_family(self):
#        """Return a dictionary<pk: MailingList> with self and all children, small children etc..."""
#        family = {}
#        self.get_family_aux(family)
#
#        return family
#
#    def get_family_aux(self, dic):
#        dic[self.id] = self
#
#        for child in self.children.all():
#            child.get_family_aux(dic)
