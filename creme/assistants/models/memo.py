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

from collections import defaultdict

from django.db.models import TextField, BooleanField, DateTimeField, ForeignKey, PositiveIntegerField
from django.db.models.signals import pre_delete
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey

from creme.creme_core.models import CremeModel, CremeEntity
from creme.creme_core.models.fields import CremeUserForeignKey
from creme.creme_core.core.function_field import FunctionField, FunctionFieldResult, FunctionFieldResultsList
from creme.creme_core.signals import pre_merge_related
from creme.creme_core.utils import ellipsis


class Memo(CremeModel):
    content       = TextField(_(u'Content'), blank=True, null=True)
    on_homepage   = BooleanField(_(u"Displayed on homepage"), blank=True, default=False)
    creation_date = DateTimeField(_(u'Creation date'), editable=False)
    user          = CremeUserForeignKey(verbose_name=_(u"Assigned to"))

    entity_content_type = ForeignKey(ContentType, related_name="memo_entity_set", editable=False)
    entity_id           = PositiveIntegerField(editable=False)
    creme_entity        = GenericForeignKey(ct_field="entity_content_type", fk_field="entity_id")

    class Meta:
        app_label = 'assistants'
        verbose_name = _(u'Memo')
        verbose_name_plural = _(u'Memos')

    def __unicode__(self):
        #NB: translate for unicode can not take 2 arguments...
        return ellipsis(self.content.strip().replace('\n', ''), 25)

    @staticmethod
    def get_memos(entity):
        return Memo.objects.filter(entity_id=entity.id).select_related('user')

    @staticmethod
    def get_memos_for_home(user):
        return Memo.objects.filter(on_homepage=True, user=user).select_related('user')

    @staticmethod
    def get_memos_for_ctypes(ct_ids, user):
        return Memo.objects.filter(entity_content_type__in=ct_ids, user=user).select_related('user')

    def get_related_entity(self): #for generic views
        return self.creme_entity


#TODO: can delete this with  a WeakForeignKey ??
def _dispose_entity_memos(sender, instance, **kwargs):
    Memo.objects.filter(entity_id=instance.id).delete()

def _handle_merge(sender, other_entity, **kwargs):
    for memo in Memo.objects.filter(entity_id=other_entity.id):
        memo.creme_entity = sender
        memo.save()

pre_delete.connect(_dispose_entity_memos, sender=CremeEntity)
pre_merge_related.connect(_handle_merge)


class _GetMemos(FunctionField):
    name         = 'assistants-get_memos'
    verbose_name = _(u"Memos")

    def __call__(self, entity):
        cache = getattr(entity, '_memos_cache', None)

        if cache is None:
            cache = entity._memos_cache = list(Memo.objects.filter(entity_id=entity.id) \
                                                           .order_by('-creation_date') \
                                                           .values_list('content', flat=True)
                                              )

        return FunctionFieldResultsList(FunctionFieldResult(content) for content in cache)

    @classmethod
    def populate_entities(cls, entities):
        memos_map = defaultdict(list)

        for content, e_id in Memo.objects.filter(entity_id__in=[e.id for e in entities]) \
                                         .order_by('-creation_date') \
                                         .values_list('content', 'entity_id'):
            memos_map[e_id].append(content)

        for entity in entities:
            entity._memos_cache = memos_map[entity.id]


CremeEntity.function_fields.add(_GetMemos())
