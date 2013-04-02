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

from django.db.models import CharField, ForeignKey, PositiveIntegerField
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from .base import CremeModel


class ButtonMenuItem(CremeModel):
    id           = CharField(primary_key=True, max_length=100) #TODO: pk string still useful ???
    content_type = ForeignKey(ContentType, verbose_name=_(u"Related type"), null=True) #null means: all ContentTypes are accepted.
    button_id    = CharField(_(u"Button ID"), max_length=100, blank=False, null=False)
    order        = PositiveIntegerField(_(u"Priority"))

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Button to display')
        verbose_name_plural = _(u'Buttons to display')

    @staticmethod
    def create_if_needed(pk, model, button, order):
        """Creation helper ; useful for populate.py scripts.
        @param model Can be None for 'all models'
        """
        kwargs = {'content_type': ContentType.objects.get_for_model(model) if model else None,
                  'button_id':    button.id_,
                 }

        try:
            bmi = ButtonMenuItem.objects.get(**kwargs)
        except ButtonMenuItem.DoesNotExist:
            bmi = ButtonMenuItem.objects.create(pk=pk, order=order, **kwargs)

        return bmi
