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

from django.db.models import CharField, BooleanField, TextField, DateTimeField, ForeignKey, PositiveIntegerField
from django.db.models.signals import pre_delete
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey

from creme.creme_core.models import CremeEntity, CremeModel
from creme.creme_core.models.fields import CremeUserForeignKey, CreationDateTimeField
from creme.creme_core.core.function_field import FunctionField, FunctionFieldResult, FunctionFieldResultsList
from creme.creme_core.signals import pre_merge_related


class ToDo(CremeModel):
    title         = CharField(_(u'Title'), max_length=200)
    is_ok         = BooleanField(_("Done ?"), editable=False)
    has_deadline  = BooleanField(editable=False) #TODO: useful ??? (deadline can be NULL)
    description   = TextField(_(u'Description'), blank=True, null=True)
    creation_date = CreationDateTimeField(_(u'Creation date'), editable=False)
    deadline      = DateTimeField(_(u"Deadline"), blank=True, null=True)
    user          = CremeUserForeignKey(verbose_name=_('Owner user')) #verbose_name=_(u"Assigned to")

    entity_content_type = ForeignKey(ContentType, related_name="todo_entity_set", editable=False)
    entity_id           = PositiveIntegerField(editable=False)
    creme_entity        = GenericForeignKey(ct_field="entity_content_type", fk_field="entity_id")

    class Meta:
        app_label = 'assistants'
        verbose_name = _(u'Todo')
        verbose_name_plural = _(u'Todos')

    def __init__(self, *args, **kwargs):
        super(ToDo, self).__init__(*args, **kwargs)

        if self.pk is None:
            self.is_ok = False #TODO: default=false in field instead ??

        if self.deadline is None:
            self.has_deadline = False

    def __unicode__(self):
        return self.title

    @staticmethod
    def get_todos(entity):
        return ToDo.objects.filter(entity_id=entity.id).select_related('user')

    @staticmethod
    def get_todos_for_home(user):
        return ToDo.objects.filter(user=user).select_related('user')

    @staticmethod
    def get_todos_for_ctypes(ct_ids, user):
        return ToDo.objects.filter(entity_content_type__in=ct_ids, user=user).select_related('user')

    def get_related_entity(self): #for generic views
        return self.creme_entity


#TODO: can delete this with  a WeakForeignKey ??
def _dispose_entity_todos(sender, instance, **kwargs):
    ToDo.objects.filter(entity_id=instance.id).delete()

def _handle_merge(sender, other_entity, **kwargs):
    for todo in ToDo.objects.filter(entity_id=other_entity.id):
        todo.creme_entity = sender
        todo.save()

pre_delete.connect(_dispose_entity_todos, sender=CremeEntity)
pre_merge_related.connect(_handle_merge)


class _GetTodos(FunctionField):
    name         = 'assistants-get_todos'
    verbose_name = _(u"Todos")

    def __call__(self, entity):
        cache = getattr(entity, '_todos_cache', None)

        if cache is None:
            cache = entity._todos_cache = list(ToDo.objects.filter(entity_id=entity.id, is_ok=False) \
                                                           .order_by('-creation_date') \
                                                           .values_list('title', flat=True)
                                              )

        return FunctionFieldResultsList(FunctionFieldResult(title) for title in cache)

    @classmethod
    def populate_entities(cls, entities):
        todos_map = defaultdict(list)

        for title, e_id in ToDo.objects.filter(entity_id__in=[e.id for e in entities], is_ok=False) \
                                       .order_by('-creation_date') \
                                       .values_list('title', 'entity_id'):
            todos_map[e_id].append(title)

        for entity in entities:
            entity._todos_cache = todos_map[entity.id]


CremeEntity.function_fields.add(_GetTodos())
