# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import CharField, BooleanField, TextField, PositiveIntegerField, ForeignKey
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeModel
from creme.creme_core.models.fields import CreationDateTimeField


class CommercialApproach(CremeModel):
    title           = CharField(_(u'Title'), max_length=200)
    ok_or_in_futur  = BooleanField(_("Done ?"), editable=False, default=False)  # TODO: Future ?
    description     = TextField(_(u'Description'), blank=True, null=True)
    creation_date   = CreationDateTimeField(_(u'Creation date'), editable=False)

    related_activity    = ForeignKey(settings.ACTIVITIES_ACTIVITY_MODEL, null=True, editable=False)

    # TODO: use real ForeignKey to CremeEntity ( + remove the signal handlers)
    entity_content_type = ForeignKey(ContentType, related_name="comapp_entity_set", editable=False)
    entity_id           = PositiveIntegerField(editable=False)  # .set_tags(viewable=False) uncomment if it becomes an auxiliary (get_related_entity())
    creme_entity        = GenericForeignKey(ct_field="entity_content_type", fk_field="entity_id")

    class Meta:
        app_label = 'commercial'
        verbose_name = _(u'Commercial approach')
        verbose_name_plural = _(u'Commercial approaches')

    def __unicode__(self):
        return self.title

    @staticmethod
    def get_approaches(entity_pk=None):
        queryset = CommercialApproach.objects.filter(ok_or_in_futur=False) \
                                             .select_related('related_activity')

        if entity_pk:
            queryset = queryset.filter(entity_id=entity_pk)

        return queryset

    @staticmethod
    def get_approaches_for_ctypes(ct_ids):
        return CommercialApproach.objects.filter(entity_content_type__in=ct_ids, ok_or_in_futur=False) \
                                 .select_related('related_activity')
