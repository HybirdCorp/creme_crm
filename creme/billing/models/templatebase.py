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

from datetime import timedelta
import logging
# import warnings

from django.urls import reverse
from django.db.models import PositiveIntegerField
from django.utils.translation import pgettext_lazy

from creme.creme_core.models.fields import CTypeForeignKey

from .base import Base

logger = logging.getLogger(__name__)


class AbstractTemplateBase(Base):
    ct        = CTypeForeignKey(editable=False).set_tags(viewable=False)
    status_id = PositiveIntegerField(editable=False).set_tags(viewable=False)  # TODO: avoid deletion of status

    creation_label = pgettext_lazy('billing', 'Create a template')
    save_label     = pgettext_lazy('billing', 'Save the template')

    _verbose_status_cache = None

    class Meta(Base.Meta):
        abstract = True
        verbose_name = pgettext_lazy('billing', 'Template')
        verbose_name_plural = pgettext_lazy('billing', 'Templates')

    def get_absolute_url(self):
        return reverse('billing__view_template', args=(self.id,))

    @staticmethod
    def get_clone_absolute_url():
        return ''

    def get_edit_absolute_url(self):
        return reverse('billing__edit_template', args=(self.id,))

    def get_delete_absolute_url(self):
        # Means that TemplateBase can not be deleted directly
        # (because it is closely linked to its RecurrentGenerator)
        return '' 

    @staticmethod
    def get_lv_absolute_url():
        return reverse('billing__list_templates')

    # def get_verbose_status(self):
    #     warnings.warn('models.AbstractTemplateBase.get_verbose_status() is deprecated ; '
    #                   'use function_fields.TemplateBaseVerboseStatusField instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     vstatus = self._verbose_status_cache
    #
    #     if vstatus is None or vstatus.id != self.status_id:
    #         status_model = self.ct.model_class()._meta.get_field('status').remote_field.model
    #
    #         try:
    #             vstatus = status_model.objects.get(id=self.status_id)
    #         except status_model.DoesNotExist as e:
    #             logger.warning('Invalid status in TemplateBase(id=%s) [%s]', self.id, e)
    #             vstatus = status_model(id=self.status_id, name='')
    #
    #         self._verbose_status_cache = vstatus
    #
    #     return vstatus.name

    # @property
    # def verbose_status(self):
    #     warnings.warn('AbstractTemplateBase.verbose_status is deprecated '
    #                   '(see get_verbose_status() warning).',
    #                   DeprecationWarning
    #                  )
    #
    #     return self.get_verbose_status()

    def create_entity(self):
        "This method is used by the generation job"
        instance_class = self.ct.model_class()
        instance = instance_class()
        instance.build(self)

        # Common rules for the recurrent generation of a "base" object for billing app.
        # See base's child for specific rules
        instance.generate_number()
        instance.expiration_date = instance.issuing_date + timedelta(days=30)  # TODO: user configurable rules ???

        instance.additional_info = self.additional_info
        instance.payment_terms   = self.payment_terms

        instance.save()

        return instance


class TemplateBase(AbstractTemplateBase):
    class Meta(AbstractTemplateBase.Meta):
        swappable = 'BILLING_TEMPLATE_BASE_MODEL'
