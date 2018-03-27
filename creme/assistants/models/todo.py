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

from collections import defaultdict

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import (CharField, BooleanField, TextField, DateTimeField,
        ForeignKey, PositiveIntegerField, CASCADE)
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.core.function_field import (FunctionField,
        FunctionFieldResult, FunctionFieldResultsList)
from creme.creme_core.models import CremeEntity, CremeModel
from creme.creme_core.models.fields import CremeUserForeignKey, CreationDateTimeField


class ToDo(CremeModel):
    title         = CharField(_(u'Title'), max_length=200)
    is_ok         = BooleanField(_(u'Done ?'), editable=False, default=False)
    reminded      = BooleanField(_(u'Notification sent'), editable=False, default=False)  # Needed by creme_core.core.reminder
    description   = TextField(_(u'Description'), blank=True)
    creation_date = CreationDateTimeField(_(u'Creation date'), editable=False)
    deadline      = DateTimeField(_(u"Deadline"), blank=True, null=True)
    user          = CremeUserForeignKey(verbose_name=_(u'Owner user'))

    # TODO: use a True ForeignKey to CremeEntity (do not forget to remove the signal handlers)
    entity_content_type = ForeignKey(ContentType, related_name='todo_entity_set', editable=False, on_delete=CASCADE)
    entity_id           = PositiveIntegerField(editable=False).set_tags(viewable=False)
    creme_entity        = GenericForeignKey(ct_field="entity_content_type", fk_field="entity_id")

    class Meta:
        app_label = 'assistants'
        verbose_name = _(u'Todo')
        verbose_name_plural = _(u'Todos')

    def __unicode__(self):
        return self.title

    def get_edit_absolute_url(self):
        # return '/assistants/todo/edit/%s/' % self.id
        return reverse('assistants__edit_todo', args=(self.id,))

    @staticmethod
    def get_todos(entity):
        return ToDo.objects.filter(entity_id=entity.id).select_related('user')

    @staticmethod
    def get_todos_for_home(user):
        # return ToDo.objects.filter(user=user).select_related('user')
        return ToDo.objects.filter(user__in=[user] + user.teams).select_related('user')

    @staticmethod
    def get_todos_for_ctypes(ct_ids, user):
        # return ToDo.objects.filter(entity_content_type__in=ct_ids, user=user).select_related('user')
        return ToDo.objects.filter(entity_content_type__in=ct_ids,
                                   user__in=[user] + user.teams
                                  ).select_related('user')

    def get_related_entity(self):  # For generic views
        return self.creme_entity

    @property
    def to_be_reminded(self):
        return self.deadline and not self.is_ok and not self.reminded


class _GetTodos(FunctionField):
    name         = 'assistants-get_todos'
    verbose_name = _(u'Todos')
    result_type  = FunctionFieldResultsList

    # def __call__(self, entity):
    def __call__(self, entity, user):
        cache = getattr(entity, '_todos_cache', None)

        if cache is None:
            cache = entity._todos_cache = list(ToDo.objects.filter(entity_id=entity.id, is_ok=False)
                                                           .order_by('-creation_date')
                                                           .values_list('title', flat=True)
                                              )

        return FunctionFieldResultsList(FunctionFieldResult(title) for title in cache)

    @classmethod
    # def populate_entities(cls, entities):
    def populate_entities(cls, entities, user):
        todos_map = defaultdict(list)

        for title, e_id in ToDo.objects.filter(entity_id__in=[e.id for e in entities], is_ok=False) \
                                       .order_by('-creation_date') \
                                       .values_list('title', 'entity_id'):
            todos_map[e_id].append(title)

        for entity in entities:
            entity._todos_cache = todos_map[entity.id]


CremeEntity.function_fields.add(_GetTodos())
