# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from datetime import timedelta #date
import logging

from django.db.models import PositiveIntegerField #ForeignKey
from django.utils.translation import pgettext_lazy
#from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist

from creme.creme_core.models.fields import CTypeForeignKey

from .base import Base


logger = logging.getLogger(__name__)


class TemplateBase(Base):
    #ct        = ForeignKey(ContentType).set_tags(viewable=False)
    ct        = CTypeForeignKey(editable=False).set_tags(viewable=False)
    status_id = PositiveIntegerField(editable=False).set_tags(viewable=False) #TODO: avoid deletion of status

    creation_label = pgettext_lazy('billing', 'Add a template') #XXX: BEWARE Remove context if this item is added in the menu (problem with PreferredMenuItem)

    class Meta:
        app_label = 'billing'
        verbose_name = pgettext_lazy('billing', 'Template')
        verbose_name_plural = pgettext_lazy('billing', 'Templates')

    def get_absolute_url(self):
        return "/billing/template/%s" % self.id

    def get_edit_absolute_url(self):
        return "/billing/template/edit/%s" % self.id

    def get_delete_absolute_url(self):
        return '' #means that TemplateBase can not be deleted directly (because it is closely linked to its RecurrentGenerator)

    @staticmethod
    def get_lv_absolute_url():
        return "/billing/templates"

    def get_generator(self):
        from creme.recurrents.models import RecurrentGenerator
        try:
            return RecurrentGenerator.objects.get(template=self)
        except ObjectDoesNotExist:
            return None

    @property
    def verbose_status(self):
        try: #TODO: cache
            return self.ct.model_class()._meta.get_field('status').rel.to.objects.get(id=self.status_id).name
        except Exception: #TODO: test
            logger.exception('Error in TemplateBase.verbose_status')
            return ''

    # This method is used by the generation job
    def create_entity(self):
        instance_class = self.ct.model_class()
        instance = instance_class()
        instance.build(self)

        # Common rules for the recurrent generation of a "base" object for billing app. See base's child for specific rules
        instance.generate_number()
        instance.expiration_date = instance.issuing_date + timedelta(days=30) #TODO: user configurable rules ???

        instance.additional_info = self.additional_info
        instance.payment_terms   = self.payment_terms

        instance.save()

        return instance

    # This build is in case of convert a template with a ct into another template with a different ct
    def build(self, template, new_ct):
        # Specific generation rules
        self.status_id = 1
        self.ct = new_ct
        return super(TemplateBase, self).build(template)
