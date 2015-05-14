# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015  Hybird
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

from django.db.models.signals import pre_delete
from django.dispatch.dispatcher import receiver

from creme.creme_core.models import CremeEntity
from creme.creme_core.signals import pre_merge_related

from .models import Action, Alert, Memo, ToDo, UserMessage


MODELS = (Action, Alert, Memo, ToDo, UserMessage)


@receiver(pre_delete, sender=CremeEntity)
def dispose_instances(sender, instance, **kwargs):
    for model in MODELS:
        model.objects.filter(entity_id=instance.id).delete()

@receiver(pre_merge_related)
def handle_merge(sender, other_entity, **kwargs):
    for model in MODELS:
        for instance in model.objects.filter(entity_id=other_entity.id):
            instance.creme_entity = sender
            instance.save()
