# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2021  Hybird
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

from django.apps import apps

if apps.is_installed('creme.activities'):
    from django.contrib.contenttypes.models import ContentType
    from django.db.models.signals import post_save  # pre_delete
    from django.dispatch import receiver

    from creme.activities import get_activity_model
    from creme.activities.constants import REL_OBJ_ACTIVITY_SUBJECT
    from creme.creme_core.models import Relation
    from creme.opportunities import get_opportunity_model

    from . import get_act_model
    from .constants import REL_SUB_COMPLETE_GOAL
    from .models import CommercialApproach

    # Catching the save of the relation between an activity and an opportunity as a subject
    @receiver(post_save, sender=Relation)
    def post_save_relation_opp_subject_activity(sender, instance, **kwargs):
        if instance.type_id == REL_OBJ_ACTIVITY_SUBJECT:
            object_entity = instance.object_entity
            get_ct = ContentType.objects.get_for_model

            if object_entity.entity_type == get_ct(get_opportunity_model()):
                activity = instance.subject_entity
                user = instance.user

                Relation.objects.safe_multi_save(
                    Relation(
                        subject_entity=activity,
                        type_id=REL_SUB_COMPLETE_GOAL,
                        object_entity=relation.object_entity,
                        user=user,
                    ) for relation in Relation.objects.filter(
                        subject_entity_id=object_entity.id,
                        type=REL_SUB_COMPLETE_GOAL,
                        object_entity__entity_type=get_ct(get_act_model()),
                    )
                )

    @receiver(post_save, sender=get_activity_model())
    def sync_with_activity(sender, instance, created, **kwargs):
        # TODO: optimise (only if title has changed - factorise with HistoryLine ??)
        if not created:
            CommercialApproach.objects.filter(
                related_activity=instance,
            ).update(title=instance.title)
