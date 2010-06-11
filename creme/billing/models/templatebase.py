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

from datetime import date, timedelta

from django.db.models import ForeignKey, PositiveIntegerField
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist

from billing.models import Base


class TemplateBase(Base):
    ct          = ForeignKey(ContentType)
    status_id   = PositiveIntegerField()

    research_fields = Base.research_fields + ['name']
    excluded_fields_in_html_output = Base.excluded_fields_in_html_output + ['base_ptr','ct','status_id','number']

    class Meta:
        app_label = 'billing'
        verbose_name = _(u'Template')
        verbose_name_plural = _(u'Templates')

    def get_absolute_url(self):
        return "/billing/template/%s" % self.id

    def get_edit_absolute_url(self):
        return "/billing/template/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        return "/billing/templates"

    def get_delete_absolute_url(self):
        return "/billing/template/delete/%s" % self.id

    def get_generator(self):
        from recurrents.models import RecurrentGenerator
        try:
            return RecurrentGenerator.objects.get(template = self)
        except ObjectDoesNotExist:
            return None

    # This method is used by the generation job
    def create_entity(self):
        instance_class = self.ct.model_class()
        instance = instance_class()
        instance.build(self)

        # Common rules for the recurrent generation of a "base" object for billing app. See base's child for specific rules
        instance.generate_number()
        instance.issuing_date = date.today()
        instance.expiration_date = date.today() + timedelta(days = 30) # TODO : 30 days after the issuing date, user configurable rules ???

        instance.save()

        return instance

    # This build is in case of convert a template with a ct into another template with a different ct
    def build(self, template, new_ct):
        # Specific generation rules
        self.status_id = 1
        self.ct = new_ct
        return super(TemplateBase, self).build(template)