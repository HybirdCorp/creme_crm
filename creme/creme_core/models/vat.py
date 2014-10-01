# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2014  Hybird
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

from django.db.models import BooleanField, DecimalField
from django.db.transaction import commit_on_success
from django.utils.translation import ugettext_lazy as _

from .base import CremeModel
from ..constants import DEFAULT_VAT


class Vat(CremeModel):
    value      = DecimalField(_(u'VAT'), max_digits=4, decimal_places=2, default=DEFAULT_VAT)
    is_default = BooleanField(_(u'Is default?'), default=False)
    is_custom  = BooleanField(default=True).set_tags(viewable=False) #used by creme_config

    def __unicode__(self):
        return unicode(self.value)

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'VAT')
        verbose_name_plural = _(u'VAT')
        ordering = ('value',)

    @commit_on_success
    def save(self, *args, **kwargs):
        if self.is_default:
            Vat.objects.update(is_default=False)
        elif not Vat.objects.filter(is_default=True).exclude(pk=self.id).exists():
            self.is_default = True

        super(Vat, self).save(*args, **kwargs)

    @commit_on_success
    def delete(self, *args, **kwargs):
        if self.is_default:
            existing_vat = Vat.objects.exclude(id=self.id)[:1]

            if existing_vat:
                first_vat = existing_vat[0]
                first_vat.is_default = True
                first_vat.save()

        super(Vat, self).delete(*args, **kwargs)

    @staticmethod
    def get_default_vat():
        return Vat.objects.filter(is_default=True)[0]
