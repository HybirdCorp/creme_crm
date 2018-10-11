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

import warnings

from django.conf import settings
# from django.contrib.contenttypes.fields import GenericForeignKey
# from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy as _

from creme.creme_core import models as creme_models
from creme.creme_core.models import fields as creme_fields


class CommercialApproach(creme_models.CremeModel):
    title          = models.CharField(_('Title'), max_length=200)
    # ok_or_in_futur = models.BooleanField(_('Done?'), editable=False, default=False)
    description    = models.TextField(_('Description'), blank=True)
    creation_date  = creme_fields.CreationDateTimeField(_('Creation date'), editable=False)

    related_activity = models.ForeignKey(settings.ACTIVITIES_ACTIVITY_MODEL, null=True,
                                         editable=False, on_delete=models.CASCADE,
                                        )

    # entity_content_type = models.ForeignKey(ContentType, related_name="comapp_entity_set", editable=False, on_delete=models.CASCADE)
    # entity_id           = models.PositiveIntegerField(editable=False)  # .set_tags(viewable=False) uncomment if it becomes an auxiliary (get_related_entity())
    # creme_entity        = GenericForeignKey(ct_field="entity_content_type", fk_field="entity_id")
    entity_content_type = creme_fields.EntityCTypeForeignKey(related_name='+', editable=False)
    entity              = models.ForeignKey(creme_models.CremeEntity, related_name='commercial_approaches',
                                            editable=False, on_delete=models.CASCADE,
                                           )  # .set_tags(viewable=False) uncomment if it becomes an auxiliary (get_related_entity())
    creme_entity        = creme_fields.RealEntityForeignKey(ct_field='entity_content_type', fk_field='entity')

    creation_label = _('Create a commercial approach')
    save_label     = _('Save the commercial approach')

    class Meta:
        app_label = 'commercial'
        verbose_name = _('Commercial approach')
        verbose_name_plural = _('Commercial approaches')

    def __str__(self):
        return self.title

    @staticmethod
    def get_approaches(entity_pk=None):
        # queryset = CommercialApproach.objects.filter(ok_or_in_futur=False) \
        #                                      .select_related('related_activity')
        queryset = CommercialApproach.objects.select_related('related_activity')

        return queryset.filter(entity_id=entity_pk) if entity_pk else \
               queryset.exclude(entity__is_deleted=True)

    @staticmethod
    def get_approaches_for_ctypes(ct_ids):
        warnings.warn('CommercialApproach.get_approaches_for_ctypes() is deprecated.', DeprecationWarning)
        # return CommercialApproach.objects.filter(entity_content_type__in=ct_ids, ok_or_in_futur=False) \
        return CommercialApproach.objects.filter(entity_content_type__in=ct_ids) \
                                 .select_related('related_activity')
