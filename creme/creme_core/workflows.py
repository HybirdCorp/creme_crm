################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2025  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from .core.workflow import SingleEntitySource, WorkflowAction, WorkflowTrigger
from .models import CremeProperty, CremePropertyType, RelationType


# Triggers ---------------------------------------------------------------------
class EntityCreationTrigger(WorkflowTrigger):
    type_id = 'creme_core-entity_creation'
    verbose_name = _('An entity has been created')

    # TODO: accept Model class too?
    # TODO: docstring
    def __init__(self, model: str, **kwargs):
        super().__init__(**kwargs)
        self._model = ContentType.objects.get_by_natural_key(
            *model.split('-', 1)  # TODO: manage errors
        ).model_class()

    @property
    def description(self):
        return gettext('A «{}» has been created').format(self._model._meta.verbose_name)

    @property
    def model(self):
        return self._model

    def to_dict(self):
        d = super().to_dict()
        meta = self._model._meta
        d['model'] = f'{meta.app_label}-{meta.model_name}'

        return d


# TODO: base model class instead
class EntityEditionTrigger(EntityCreationTrigger):
    type_id = 'creme_core-entity_edition'
    verbose_name = _('An entity has been modified')

    # TODO: factorise?
    @property
    def description(self):
        return gettext('A «{}» has been modified').format(self._model._meta.verbose_name)


class RelationAddingTrigger(WorkflowTrigger):
    type_id = 'creme_core-relation_adding'
    verbose_name = _('A Relationship has been added')

    # TODO: rename arg? accept RelationType?
    def __init__(self, rtype, **kwargs):
        super().__init__(**kwargs)
        self._rtype_id = rtype

    @property
    def description(self):
        return gettext('A relationship «{predicate}» has been added').format(
            predicate=self.relation_type.predicate,
        )

    # TODO: cache
    @property
    def relation_type(self) -> RelationType:
        return RelationType.objects.get(id=self._rtype_id)

    def to_dict(self):
        d = super().to_dict()
        d['rtype'] = self._rtype_id

        return d


# Sources ----------------------------------------------------------------------

class CreatedEntitySource(SingleEntitySource):
    @property
    def label(self):
        return gettext('Created entity ({type})').format(
            type=self._model._meta.verbose_name,
        )


class EditedEntitySource(SingleEntitySource):
    @property
    def label(self):
        return gettext('Modified entity ({type})').format(
            type=self._model._meta.verbose_name,
        )


# Actions ----------------------------------------------------------------------
class PropertyAddingAction(WorkflowAction):
    type_id = 'creme_core-property_adding'
    verbose_name = _('Adding a property')

    # TODO: rename arg? accept CremePropertyType?
    # TODO: docstring
    def __init__(self, ptype, **kwargs):
        super().__init__(**kwargs)
        self._ptype_uuid = ptype

    @property
    def description(self):
        return _('Adding the property «{}»').format(self.property_type.text)

    # TODO: cache
    @property
    def property_type(self) -> CremePropertyType:
        return CremePropertyType.objects.get(uuid=self._ptype_uuid)

    # TODO: in base class
    # TODO: in other classes
    def execute(self, source):
        CremeProperty.objects.safe_create(creme_entity=source, type=self.property_type)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d['ptype'] = self._ptype_uuid

        return d


class RelationAddingAction(WorkflowAction):
    type_id = 'creme_core-relation_adding'
    verbose_name = _('Adding a relationship')

    # TODO: rename arg? accept RelationType?
    def __init__(self, rtype, **kwargs):
        super().__init__(**kwargs)
        self._rtype_id = rtype

    @property
    def description(self):
        return _('Adding the relationship «{}»').format(self.relation_type.predicate)

    # TODO: in base class
    # TODO: in other classes
    def execute(self, source):
        pass
        # CremeProperty.objects.safe_create(creme_entity=source, type=self.property_type)

    @property
    def relation_type(self) -> RelationType:
        return RelationType.objects.get(id=self._rtype_id)

    def to_dict(self):
        d = super().to_dict()
        d['rtype'] = self._rtype_id

        return d
