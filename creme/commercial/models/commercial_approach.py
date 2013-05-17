# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

#import logging

from django.db.models import CharField, BooleanField, TextField, DateTimeField, PositiveIntegerField, ForeignKey
from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from creme.creme_core.models import CremeModel, CremeEntity
from creme.creme_core.signals import pre_merge_related

from creme.activities.models import Activity


class CommercialApproach(CremeModel):
    title               = CharField(_(u'Title'), max_length=200)
    ok_or_in_futur      = BooleanField(_("Done ?"), editable=False)#TODO: Future ?
    description         = TextField(_(u'Description'), blank=True, null=True)
    creation_date       = DateTimeField(_(u'Creation date'), blank=False, null=False)

    related_activity    = ForeignKey(Activity, null=True)

    entity_content_type = ForeignKey(ContentType, related_name="comapp_entity_set")
    entity_id           = PositiveIntegerField()
    creme_entity        = GenericForeignKey(ct_field="entity_content_type", fk_field="entity_id")

    class Meta:
        app_label = 'commercial'
        verbose_name = _(u'Commercial approach')
        verbose_name_plural = _(u'Commercial approaches')

    def __unicode__(self):
        return self.title

    @staticmethod
    def get_approaches(entity_pk=None):
        queryset = CommercialApproach.objects.filter(ok_or_in_futur=False).select_related('related_activity')

        if entity_pk:
            queryset = queryset.filter(entity_id=entity_pk)

        return queryset

    @staticmethod
    def get_approaches_for_ctypes(ct_ids):
        return CommercialApproach.objects.filter(entity_content_type__in=ct_ids, ok_or_in_futur=False).select_related('related_activity')


#TODO: with a real ForeignKey can not we remove these handlers ??
@receiver(pre_delete, sender=CremeEntity)
def _dispose_entity_comapps(sender, instance, **kwargs):
    CommercialApproach.objects.filter(entity_id=instance.id).delete()

@receiver(pre_merge_related)
def _handle_merge(sender, other_entity, **kwargs):
    for commapp in CommercialApproach.objects.filter(entity_id=other_entity.id):
        commapp.creme_entity = sender
        commapp.save()

@receiver(post_save) #TODO: sender=Activity (after activities refactoring)
def _sync_with_activity(sender, instance, created, **kwargs):
    #TODO: optimise (only if title has changed - factorise with HistoryLine ??)
    if not created and isinstance(instance, Activity):
        CommercialApproach.objects.filter(related_activity=instance).update(title=instance.title)
