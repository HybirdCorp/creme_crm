################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2026  Hybird
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

from typing import override

from django.db import models

from creme.creme_core import models as core_models
from creme.creme_core import workflows
from creme.creme_core.core.entity_filter import (
    EF_CREDENTIALS,
    condition_handler,
)
from creme.creme_core.core.soft_reference import SoftReferenceCollector


# References contained by RelationTypes ----------------------------------------
class RelationTypeConstraintPTypeRefCollector(SoftReferenceCollector):
    """Collect the RelationTypes which reference a CremePropertyType through their
    constraints to allowed & forbidden Property types.

    Notice that these references are stored in ManyToManyFields, & this type of
    fields has no attribute 'on_delete' like ForeignKeys.
    """
    id = 'creme_core-rtype_constraints-ptype'
    model = core_models.CremePropertyType

    @override
    def collect(self, instance):
        assert isinstance(instance, self.model)

        yield from instance.relationtype_subjects_set.all()
        yield from instance.relationtype_forbidden_set.all()


# References contained by EntityFilters ----------------------------------------
class EFilterConditionCFieldRefCollector(SoftReferenceCollector):
    """Collect the EntityFilters which reference CustomFields in their conditions."""
    id = 'creme_core-efilter_condition_cfield-cfield'
    model = core_models.CustomField

    @override
    def collect(self, instance):
        assert isinstance(instance, self.model)

        cond_type_ids = (
            condition_handler.CustomFieldConditionHandler.type_id,
            condition_handler.DateCustomFieldConditionHandler.type_id,
        )
        yield from core_models.EntityFilter.objects.filter(
            conditions__type__in=cond_type_ids, conditions__name=instance.uuid,
        )


class EFilterConditionCFieldEnumValueRefCollector(SoftReferenceCollector):
    """Collect the EntityFilters which reference CustomFieldEnumValues in their
    conditions.

    Currently, only credentials filters are considered as deletion blockers.
    """
    id = 'creme_core-efilter_condition_cfield-evalue'
    model = core_models.CustomFieldEnumValue

    @override
    def collect(self, instance):
        assert isinstance(instance, self.model)

        yield from core_models.EntityFilter.objects.filter(
            filter_type=EF_CREDENTIALS,  # TODO: not only system filters?
        ).filter(models.Exists(core_models.EntityFilterCondition.objects.filter(
            filter=models.OuterRef('pk'),
            type=condition_handler.CustomFieldConditionHandler.type_id,
            name=str(instance.custom_field.uuid),
            value__values__regex=f'"{instance.uuid}"',
        )))


class EFilterConditionPTypeRefCollector(SoftReferenceCollector):
    """Collect the EntityFilters which reference CremePropertyTypes in their
    conditions on properties ("has"/"has not" property with type ...).
    """
    id = 'creme_core-efilter_condition_ptype-ptype'
    model = core_models.CremePropertyType

    @override
    def collect(self, instance):
        assert isinstance(instance, self.model)

        yield from core_models.EntityFilter.objects.filter(
            conditions__type=condition_handler.PropertyConditionHandler.type_id,
            conditions__name=instance.uuid,
        )


class EFilterConditionRTypeRefCollector(SoftReferenceCollector):
    """Collect the EntityFilters which reference RelationTypes in their conditions
    on relationships ("has"/"has not" & related to sub-filters ...).
    """
    id = 'creme_core-efilter_condition_rtypes-rtype'
    model = core_models.RelationType

    @override
    def collect(self, instance):
        assert isinstance(instance, self.model)

        yield from core_models.EntityFilter.objects.filter(
            conditions__type__in=(
                condition_handler.RelationConditionHandler.type_id,
                condition_handler.RelationSubFilterConditionHandler.type_id,
            ),
            conditions__name__in=(instance.id, instance.symmetric_type_id),
        )


class EFilterConditionPortableKeyedRefCollector(SoftReferenceCollector):
    """Collect the EntityFilters which reference instances with a portable key
    (like MinionModel) in their conditions on regular fields.
    """
    id = 'creme_core-efilter_condition_rfield-portable_keyed'
    # model = models.Model

    @override
    def collect(self, instance):
        get_key = getattr(instance, 'portable_key', None)
        if get_key is None:
            return

        key = get_key()
        yielded_ids = set()
        model = type(instance)

        for cond in core_models.EntityFilterCondition.objects.filter(
            # filter__filter_type=EF_CREDENTIALS,
            type=condition_handler.RegularFieldConditionHandler.type_id,
            value__values__regex=f'"{key}"',
        ).order_by(models.F('filter__name')).prefetch_related('filter'):
            if cond.filter_id not in yielded_ids:
                last_field = cond.handler.field_info[-1]
                if last_field.is_relation and issubclass(last_field.related_model, model):
                    yield cond.filter

                    yielded_ids.add(cond.filter_id)


class EFilterConditionEntityRefCollector(SoftReferenceCollector):
    """Collect the EntityFilters which reference CremeEntities in their
    conditions on Relations.
    """
    id = 'creme_core-efilter_condition_rtype-entity'
    model = core_models.CremeEntity

    @override
    def collect(self, instance):
        assert isinstance(instance, self.model)

        yield from core_models.EntityFilter.objects.filter(
            conditions__type=condition_handler.RelationConditionHandler.type_id,
            conditions__value__entity__regex=f'{instance.uuid}',
        )


# References contained by Workflows (Triggers) ---------------------------------
class PropertyAddingTriggerPTypeRefCollector(SoftReferenceCollector):
    """Collect the Workflows which reference CremePropertyTypes through their
    trigger.
    """
    id = 'creme_core-workflow_prop_added-ptype'
    model = core_models.CremePropertyType

    @override
    def collect(self, instance):
        assert isinstance(instance, self.model)

        trigger_cls = workflows.PropertyAddingTrigger

        for workflow in core_models.Workflow.objects.all_workflows():
            if (
                isinstance(workflow.trigger, trigger_cls)
                and workflow.trigger.property_type == instance
            ):
                yield workflow


class RelationAddingTriggerRTypeRefCollector(SoftReferenceCollector):
    """Collect the Workflows which reference RelationTypes through their
    trigger.
    """
    id = 'creme_core-workflow_relation_added-rtype'
    model = core_models.RelationType

    @override
    def collect(self, instance):
        assert isinstance(instance, self.model)

        trigger_cls = workflows.RelationAddingTrigger

        for workflow in core_models.Workflow.objects.all_workflows():
            if (
                isinstance(workflow.trigger, trigger_cls)
                and workflow.trigger.relation_type in (instance, instance.symmetric_type)
            ):
                yield workflow


# References contained by Workflows (Conditionss) ------------------------------
# TODO: uncomment when conditions on properties are managed by Workflow + register;
#       idem with RelationTypes
# class WorkflowConditionPTypeRefCollector(SoftReferenceCollector):
#     id = 'creme_core-workflow_prop_cond-ptype'
#     model = core_models.CremePropertyType
#
#     @override
#     def collect(self, instance):
#         assert isinstance(instance, self.model)
#
#         for workflow in core_models.Workflow.objects.all_workflows():
#             # todo: add an API for '_conditions_per_source'
#             for source_conditions in workflow.conditions._conditions_per_source:
#                 for condition in source_conditions['conditions']:
#                     if (
#                         condition.type == PropertyConditionHandler.type_id
#                         and condition.name == ptype_uuid
#                     ):
#                         yield workflow

class WorkflowConditionCFieldRefCollector(SoftReferenceCollector):
    """Collect the Workflows which reference CustomFields through their
    conditions.
    """
    id = 'creme_core-workflow_condition_cfield-cfield'
    model = core_models.CustomField

    @override
    def collect(self, instance):
        assert isinstance(instance, self.model)

        cfield_uuid = str(instance.uuid)
        cond_type_ids = (
            condition_handler.CustomFieldConditionHandler.type_id,
            condition_handler.DateCustomFieldConditionHandler.type_id,
        )

        for workflow in core_models.Workflow.objects.all_workflows():
            # TODO: add an API for '_conditions_per_source'
            for source_conditions in workflow.conditions._conditions_per_source:
                for condition in source_conditions['conditions']:
                    if condition.type in cond_type_ids and condition.name == cfield_uuid:
                        yield workflow


class WorkflowConditionCFieldEnumValueRefCollector(SoftReferenceCollector):
    """Collect the Workflows which reference CustomFieldEnumValues through their
    conditions.
    """
    id = 'creme_core-workflow_condition_cfield-evalue'
    model = core_models.CustomFieldEnumValue

    @override
    def collect(self, instance):
        assert isinstance(instance, self.model)

        key = str(instance.uuid)
        cond_type_id = condition_handler.CustomFieldConditionHandler.type_id
        cf_uuid = instance.custom_field.uuid

        for wf in core_models.Workflow.objects.all_workflows():
            # TODO: public API for '_conditions_per_source' ?
            for source_conditions in wf.conditions._conditions_per_source:
                for cond in source_conditions['conditions']:
                    if (
                        cond.type == cond_type_id
                        and cond.handler._custom_field_uuid == cf_uuid
                        and key in cond.value['values']
                    ):
                        yield wf


class WorkflowConditionPortableKeyedRefCollector(SoftReferenceCollector):
    """Collect the Workflows which reference instances with a portable key
    (like MinionModel) in their conditions on regular fields.
    """
    id = 'creme_core-workflow_condition_rfield-portable_keyed'
    # model = models.Model

    @override
    def collect(self, instance):
        get_key = getattr(instance, 'portable_key', None)
        if get_key is None:
            return

        key = get_key()
        model = type(instance)
        cond_type_id = condition_handler.RegularFieldConditionHandler.type_id

        for wf in core_models.Workflow.objects.all_workflows():
            # TODO: public API for '_conditions_per_source' ?
            for source_conditions in wf.conditions._conditions_per_source:
                for cond in source_conditions['conditions']:
                    if cond.type == cond_type_id:
                        last_field = cond.handler.field_info[-1]
                        if (
                            last_field.is_relation
                            and issubclass(last_field.related_model, model)
                            and key in cond.value['values']
                        ):
                            yield wf


# References contained by Workflows (Actions) ----------------------------------
class WorkflowActionModelRefCollector(SoftReferenceCollector):
    """Collect the Workflows which collect references contained in their actions."""
    id = 'creme_core-workflow_action-model'

    @override
    def collect(self, instance):
        assert isinstance(instance, self.model)

        model = type(instance)

        for wf in core_models.Workflow.objects.all_workflows():
            if any(
                instance == ref
                for action in wf.actions
                for ref in action.soft_references(model=model)
            ):
                yield wf
