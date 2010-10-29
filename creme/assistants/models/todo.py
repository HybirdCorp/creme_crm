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

from datetime import datetime

from django.db.models import CharField, BooleanField, TextField, DateTimeField, ForeignKey, PositiveIntegerField
from django.db.models.signals import pre_delete
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.auth.models import User

from creme_core.models import CremeEntity, CremeModel


class ToDo(CremeModel):
    title         = CharField(_(u'Title'), max_length=200)
    is_ok         = BooleanField(_("Done ?"), editable=False)
    has_deadline  = BooleanField(editable=False) #useful ??? (deadline can be NULL)
    description   = TextField(_(u'Description'), blank=True, null=True)
    creation_date = DateTimeField(_(u'Creation date'), blank=False, null=False)
    deadline      = DateTimeField(_(u"Deadline"), blank=True, null=True)
    for_user      = ForeignKey(User, verbose_name=_(u'Assigned to'), blank=True, null=True, related_name='user_todo_assigned_set')

    entity_content_type = ForeignKey(ContentType, related_name="todo_entity_set")
    entity_id           = PositiveIntegerField()
    creme_entity        = GenericForeignKey(ct_field="entity_content_type", fk_field="entity_id")


    def __init__(self, *args, **kwargs):
        super(ToDo, self).__init__(*args, **kwargs)

        if self.pk is None:
            self.is_ok = False

        if self.deadline is None:
            self.has_deadline = False 

    @staticmethod
    def get_todos(entity=None):
        queryset = ToDo.objects.select_related('for_user')

        if entity:
            queryset = queryset.filter(entity_id=entity.id)

        return queryset

    @staticmethod
    def get_todos_for_ctypes(ct_ids):
        return ToDo.objects.filter(entity_content_type__in=ct_ids).select_related('for_user')

    class Meta:
        app_label = 'assistants'
        verbose_name = _(u'Todo')
        verbose_name_plural = _(u'Todos')


#TODO: can delete this with  a WeakForeignKey ??
def dispose_entity_todos(sender, instance, **kwargs):
    ToDo.objects.filter(entity_id=instance.id).delete()

pre_delete.connect(dispose_entity_todos, sender=CremeEntity)
