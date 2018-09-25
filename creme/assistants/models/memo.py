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

# from collections import defaultdict
import warnings

# from django.contrib.contenttypes.fields import GenericForeignKey
# from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

# from creme.creme_core.core.function_field import FunctionField, FunctionFieldResult, FunctionFieldResultsList
from creme.creme_core import models as creme_models
from creme.creme_core.models import fields as creme_fields
from creme.creme_core.utils import ellipsis


class MemoManager(models.Manager):
    def filter_by_user(self, user):
        return self.filter(user__in=[user] + user.teams)


class Memo(creme_models.CremeModel):
    content       = models.TextField(_('Content'))
    on_homepage   = models.BooleanField(_('Displayed on homepage'), blank=True, default=False)
    creation_date = creme_fields.CreationDateTimeField(_('Creation date'), editable=False)
    user          = creme_fields.CremeUserForeignKey(verbose_name=_('Owner user'))

    # entity_content_type = models.ForeignKey(ContentType, related_name='memo_entity_set', editable=False, on_delete=models.CASCADE)
    # entity_id           = models.PositiveIntegerField(editable=False).set_tags(viewable=False)
    # creme_entity        = GenericForeignKey(ct_field='entity_content_type', fk_field='entity_id')
    entity_content_type = creme_fields.EntityCTypeForeignKey(related_name='+', editable=False)
    entity              = models.ForeignKey(creme_models.CremeEntity,  related_name='assistants_memos',
                                            editable=False, on_delete=models.CASCADE,
                                           ).set_tags(viewable=False)
    creme_entity        = creme_fields.RealEntityForeignKey(ct_field='entity_content_type', fk_field='entity')

    objects = MemoManager()

    creation_label = _('Create a memo')
    save_label     = _('Save the memo')

    class Meta:
        app_label = 'assistants'
        verbose_name = _('Memo')
        verbose_name_plural = _('Memos')

    def __str__(self):
        # NB: translate for unicode can not take 2 arguments...
        return ellipsis(self.content.strip().replace('\n', ''), 25)

    def get_edit_absolute_url(self):
        return reverse('assistants__edit_memo', args=(self.id,))

    @staticmethod
    def get_memos(entity):
        warnings.warn('Memo.get_memos() is deprecated.', DeprecationWarning)
        return Memo.objects.filter(entity_id=entity.id).select_related('user')

    @staticmethod
    def get_memos_for_home(user):
        warnings.warn('Memo.get_memos_for_home() is deprecated.', DeprecationWarning)
        return Memo.objects.filter(on_homepage=True,
                                   user__in=[user] + user.teams,
                                   # entity__is_deleted=False,
                                  ) \
                          .select_related('user')

    @staticmethod
    def get_memos_for_ctypes(ct_ids, user):
        warnings.warn('Memo.get_memos_for_ctypes() is deprecated.', DeprecationWarning)
        return Memo.objects.filter(entity_content_type__in=ct_ids, user__in=[user] + user.teams) \
                           .select_related('user')

    def get_related_entity(self):  # For generic views
        return self.creme_entity


# class _GetMemos(FunctionField):
#     name         = 'assistants-get_memos'
#     verbose_name = _(u'Memos')
#     result_type  = FunctionFieldResultsList
#
#     def __call__(self, entity, user):
#         cache = getattr(entity, '_memos_cache', None)
#
#         if cache is None:
#             cache = entity._memos_cache = list(Memo.objects.filter(entity_id=entity.id)
#                                                            .order_by('-creation_date')
#                                                            .values_list('content', flat=True)
#                                               )
#
#         return FunctionFieldResultsList(FunctionFieldResult(content) for content in cache)
#
#     @classmethod
#     def populate_entities(cls, entities, user):
#         memos_map = defaultdict(list)
#
#         for content, e_id in Memo.objects.filter(entity_id__in=[e.id for e in entities]) \
#                                          .order_by('-creation_date') \
#                                          .values_list('content', 'entity_id'):
#             memos_map[e_id].append(content)
#
#         for entity in entities:
#             entity._memos_cache = memos_map[entity.id]
#
#
# CremeEntity.function_fields.add(_GetMemos())
