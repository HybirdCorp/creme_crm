# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.conf import settings
from django.db.models import Model, CharField, ForeignKey, IntegerField, CASCADE
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeModel
from creme.creme_core.models.fields import CTypeForeignKey


class ConfigBillingAlgo(CremeModel):
    organisation = ForeignKey(settings.PERSONS_ORGANISATION_MODEL, verbose_name=_(u'Organisation'), on_delete=CASCADE)
    name_algo    = CharField(_(u"Algo name"), max_length=400)
    ct           = CTypeForeignKey()

    class Meta:
        app_label = 'billing'
        # TODO unique_together = ("organisation", "name_algo", "ct") ??

    def __unicode__(self):
        return u'ConfigBillingAlgo(organisation="{}", name_algo="{}", ct="{}")'.format(
            self.organisation, self.name_algo, self.ct,
        )


class SimpleBillingAlgo(Model):
    organisation = ForeignKey(settings.PERSONS_ORGANISATION_MODEL, verbose_name=_(u'Organisation'), on_delete=CASCADE)
    last_number  = IntegerField()
    prefix       = CharField(_(u'Invoice prefix'), max_length=400)
    ct           = CTypeForeignKey()

    ALGO_NAME = "SIMPLE_ALGO"  # TODO: prefix with app name

    class Meta:
        app_label = 'billing'
        unique_together = ("organisation", "last_number", "ct")

    def __unicode__(self):
        return u'SimpleBillingAlgo(organisation="{}", ct="{}")'.format(self.organisation, self.ct)
