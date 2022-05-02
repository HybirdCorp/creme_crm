# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

import logging
import uuid
from collections import defaultdict
from typing import TYPE_CHECKING, Any, DefaultDict, Dict, List, Sequence, Tuple

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.query_utils import Q
from django.db.transaction import atomic
from django.urls import reverse
from django.utils.html import escape
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from ..core.field_tags import FieldTag
from .base import CremeModel
from .fields import (
    CreationDateTimeField,
    CremeUserForeignKey,
    CTypeForeignKey,
    ModificationDateTimeField,
)
from .manager import CremeEntityManager

if TYPE_CHECKING:
    from . import CremeProperty, CustomField, Relation


logger = logging.getLogger(__name__)
_SEARCH_FIELD_MAX_LENGTH = 200


class CremeEntity(CremeModel):
    created = CreationDateTimeField(
        _('Creation date'), editable=False
    ).set_tags(clonable=False)
    modified = ModificationDateTimeField(
        _('Last modification'), editable=False
    ).set_tags(clonable=False)

    entity_type = CTypeForeignKey(editable=False).set_tags(viewable=False)

    header_filter_search_field = models.CharField(
        max_length=_SEARCH_FIELD_MAX_LENGTH, editable=False,
    ).set_tags(viewable=False)

    is_deleted = models.BooleanField(default=False, editable=False).set_tags(viewable=False)

    user = CremeUserForeignKey(verbose_name=_('Owner user'))

    description = models.TextField(_('Description'), blank=True).set_tags(optional=True)

    uuid = models.UUIDField(
        unique=True, editable=False, default=uuid.uuid4,
    ).set_tags(viewable=False)

    sandbox = models.ForeignKey(
        'creme_core.Sandbox',
        null=True, on_delete=models.PROTECT,
        editable=False,
    ).set_tags(viewable=False)

    objects = CremeEntityManager()

    _real_entity = None  # TODO: Union[None, 'CremeEntity', Literal[True]]

    # Currently used in reports (can be used elsewhere ?) to allow reporting
    # on those related fields
    # TODO: use tag instead.
    allowed_related: set = set()

    creation_label = _('Create an entity')
    save_label     = _('Save the entity')
    # multi_creation_label = _('Add entities')  TODO ??
    # multi_save_label = _('Save the entities')  TODO ??

    # Score in the light search ; entity with the highest score is display as 'Best result'
    # Add a 'search_score' @property to a model in order to have a per-instance scoring.
    search_score: int = 0

    class Meta:
        app_label = 'creme_core'
        verbose_name = 'Entity'
        verbose_name_plural = 'Entities'
        ordering = ('header_filter_search_field',)  # NB: order by id on a FK can cause a crashes
        index_together = [
            ['entity_type', 'is_deleted'],  # Optimise the basic COUNT in list-views
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.pk is None:
            if 'entity_type' not in kwargs and 'entity_type_id' not in kwargs:
                self.entity_type = ContentType.objects.get_for_model(self)

        self._relations_map = {}
        self._properties = None
        self._cvalues_map = {}

    @atomic
    def delete(self, using=None, keep_parents=False):
        from .history import _get_deleted_entity_ids

        # Pre-delete signal is sent to auxiliary _before_, then sent to the entity
        # so it causes problem with aux_deletion line that reference the entity
        # (e.g.:this problem appears when deleting an EmailCampaign with Sendings)
        _get_deleted_entity_ids().add(self.id)

        for relation in self.relations.exclude(type__is_internal=True):
            relation.delete(using=using)

        for prop in self.properties.all():
            prop.delete(using=using)

        super()._delete_without_transaction(using=using, keep_parents=keep_parents)

    def __str__(self):
        real_entity = self.get_real_entity()

        if self is real_entity:
            return f'Creme entity: {self.id}'

        return str(real_entity)

    def allowed_str(self, user) -> str:
        return (
            str(self) if user.has_perm_to_view(self) else
            gettext('Entity #{id} (not viewable)').format(id=self.id)
        )

    def get_real_entity(self) -> 'CremeEntity':
        entity = self._real_entity

        if entity is True:
            return self

        if entity is None:
            ct = self.entity_type
            get_ct = ContentType.objects.get_for_model

            if ct == get_ct(CremeEntity) or ct == get_ct(self.__class__):
                self._real_entity = True  # Avoid reference to 'self' (cyclic reference)
                entity = self
            else:
                entity = self._real_entity = ct.get_object_for_this_type(id=self.id)

        return entity

    def get_absolute_url(self) -> str:
        real_entity = self.get_real_entity()

        if self is real_entity:
            return ''

        return real_entity.get_absolute_url()

    @staticmethod
    def get_clone_absolute_url() -> str:
        """Returns the url of the clone view of this entity type.
        This URL should only accept POST method, and take an 'id' POST parameter.
        If '' (void string) is returned, the type can not be cloned.
        """
        return reverse('creme_core__clone_entity')

    @staticmethod
    def get_create_absolute_url() -> str:
        """Returns the url of the creation view of this entity type.
        If '' (void string) is returned, the type can not be created directly.
        eg: return "/my_app/my_model/add"
        """
        return ''

    def get_edit_absolute_url(self) -> str:
        """Returns the url of the edition view for this instance.
        If '' (void string) is returned, the model can not be edited directly.
        eg: return "/my_app/my_model/edit/%s" % self.id
        """
        return ''

    def get_delete_absolute_url(self) -> str:
        """Returns the url of the deletion view (should use POST method) for this instance.
        If '' (void string) is returned, the model can not be deleted directly.
        """
        return reverse('creme_core__delete_entity', args=(self.id,))

    def get_html_attrs(self, context) -> Dict[str, str]:
        """Extra HTMl attributes for this entity.
        @param context: Context of the template (useful to stores re-usable values).
        @return A dictionary.

        Examples of overloading:
            return {'style': 'background-color: red;'}

            # Better, but needs additional CSS (see 'tickets' app).
            return {'data-color': 'my_entity-important'}
        """
        return {}

    def get_related_entities(self,
                             relation_type_id: str,
                             real_entities: bool = True,
                             ) -> List['CremeEntity']:
        return [
            relation.object_entity.get_real_entity()
            for relation in self.get_relations(relation_type_id, real_entities)
        ]

    def get_relations(self,
                      relation_type_id: str,
                      real_obj_entities: bool = False,
                      ) -> List['Relation']:
        from . import Relation

        relations = self._relations_map.get(relation_type_id)

        if relations is None:
            logger.debug(
                'CremeEntity.get_relations(): Cache MISS for id=%s type=%s',
                self.id, relation_type_id,
            )
            relations = self.relations.filter(type=relation_type_id).order_by('id')

            if real_obj_entities:
                relations = [*relations.select_related('object_entity')]
                Relation.populate_real_object_entities(relations)

            self._relations_map[relation_type_id] = relations
        else:
            logger.debug(
                'CremeEntity.get_relations(): Cache HIT for id=%s type=%s',
                self.id, relation_type_id,
            )

        return relations

    @staticmethod
    def populate_real_entities(entities: Sequence['CremeEntity']) -> None:
        """Faster than calling get_real_entity() of each CremeEntity object,
        because it groups queries by ContentType.
        @param entities: Sequence of CremeEntity instances.
               Beware it can be iterated twice (ie: can't be a generator).
        """
        entities_by_ct: DefaultDict[int, list] = defaultdict(list)

        for entity in entities:
            entities_by_ct[entity.entity_type_id].append(entity.id)

        entities_map: Dict[int, CremeModel] = {}
        get_ct = ContentType.objects.get_for_id

        for ct_id, entity_ids in entities_by_ct.items():
            entities_map.update(get_ct(ct_id).model_class().objects.in_bulk(entity_ids))

        for entity in entities:
            entity._real_entity = entities_map[entity.id]

    @staticmethod
    def populate_relations(entities: Sequence['CremeEntity'],
                           relation_type_ids: Sequence[str],
                           ) -> None:
        from . import Relation

        relations = Relation.objects.filter(
            subject_entity__in=[e.id for e in entities],
            type__in=relation_type_ids,
        ).select_related('object_entity')
        Relation.populate_real_object_entities(relations)

        # { Subject_Entity -> { RelationType ->[Relation list] } }
        relations_map: DefaultDict[int, DefaultDict[str, list]] = \
            defaultdict(lambda: defaultdict(list))
        for relation in relations:
            relations_map[relation.subject_entity_id][relation.type_id].append(relation)

        for entity in entities:
            for relation_type_id in relation_type_ids:
                entity._relations_map[relation_type_id] = \
                    relations_map[entity.id][relation_type_id]
                logger.debug('Fill relations cache id=%s type=%s', entity.id, relation_type_id)

    def get_custom_value(self, custom_field: 'CustomField'):
        cvalue = None

        try:
            cvalue = self._cvalues_map[custom_field.id]
        except KeyError:
            self.populate_custom_values([self], [custom_field])
            cvalue = self._cvalues_map.get(custom_field.id)

        return cvalue

    @staticmethod
    def populate_custom_values(entities: Sequence['CremeEntity'],
                               custom_fields: Sequence['CustomField'],
                               ) -> None:
        from . import CustomField

        cvalues_map = CustomField.get_custom_values_map(entities, custom_fields)

        for entity in entities:
            entity_id = entity.id
            for custom_field in custom_fields:
                cf_id = custom_field.id
                entity._cvalues_map[cf_id] = cvalues_map[entity_id].get(cf_id)

    def get_entity_summary(self, user) -> str:
        return escape(self.allowed_str(user))

    def get_custom_fields_n_values(self,
                                   only_required: bool = False,
                                   ) -> List[Tuple['CustomField', Any]]:
        from . import CustomField

        # NB: we do not use <CustomField.objects.get_for_model()> because this method
        #     seems mostly used in forms,  not detail-views (bigger query, cache probably useless).
        cfields = CustomField.objects.filter(
            content_type=self.entity_type_id,
            is_deleted=False,
        )

        if only_required:
            cfields = cfields.filter(is_required=True)

        CremeEntity.populate_custom_values([self], cfields)

        return [(cfield, self.get_custom_value(cfield)) for cfield in cfields]

    def get_properties(self) -> List['CremeProperty']:
        if self._properties is None:
            logger.debug('CremeEntity.get_properties(): Cache MISS for id=%s', self.id)
            self._properties = [*self.properties.all().select_related('type')]
        else:
            logger.debug('CremeEntity.get_properties(): Cache HIT for id=%s', self.id)

        return self._properties

    @staticmethod
    def populate_properties(entities: Sequence['CremeEntity']) -> None:
        from . import CremeProperty

        properties_map: DefaultDict[int, list] = defaultdict(list)

        # NB1: listify entities in order to avoid subquery
        #      (that is not supported by some DB backends)
        # NB2: list of id in order to avoid strange queries that retrieve
        #      base CremeEntities (ORM problem ?)
        entities_ids = [entity.id for entity in entities]

        for prop in CremeProperty.objects.filter(
            creme_entity__in=entities_ids,
        ).select_related('type'):
            properties_map[prop.creme_entity_id].append(prop)

        for entity in entities:
            entity_id = entity.id
            logger.debug('Fill properties cache entity_id=%s', entity_id)
            entity._properties = properties_map[entity_id]

    def save(self, *args, **kwargs):
        self.header_filter_search_field = self._search_field_value()[:_SEARCH_FIELD_MAX_LENGTH]

        super().save(*args, **kwargs)
        logger.debug('CremeEntity.save(%s, %s)', args, kwargs)

    def _search_field_value(self):
        """Overload this method if you want to customise the value to search
        on your CremeEntity type.
        """
        return str(self)

    def _clone_custom_values(self, source):
        from . import CustomField, CustomFieldValue

        for custom_field in CustomField.objects.get_for_model(source.entity_type).values():
            custom_value_klass = custom_field.value_class
            try:
                value = custom_value_klass.objects.get(
                    custom_field=custom_field,
                    entity=source.id,
                ).value
            except custom_value_klass.DoesNotExist:
                continue
            else:
                if hasattr(value, 'id'):
                    value = value.id
                elif hasattr(value, 'all'):
                    value = [*value.all()]
                CustomFieldValue.save_values_for_entities(custom_field, [self], value)

    def _pre_save_clone(self, source):
        """Called just before saving the entity which is already populated
        with source attributes (except m2m).
        """
        pass

    def _post_save_clone(self, source):
        """Called just after saving the entity (m2m and custom fields are
         not already cloned & saved).
        """
        pass

    def _post_clone(self, source):
        """Called after all clone operations (object cloned with all his
         M2M, custom values, properties and relations).
        """
        pass

    def _clone_m2m(self, source: 'CremeEntity') -> None:
        """Handle the clone of all many to many fields."""
        for field in source._meta.many_to_many:
            field_name = field.name
            getattr(self, field_name).set(getattr(source, field_name).all())

    def _clone_object(self):
        """Clone and returns a new saved instance of self.
        NB: Clones also customs values.
        """
        fields_kv = {}

        for field in self._meta.fields:
            # if field.get_tag('clonable'):
            if field.get_tag(FieldTag.CLONABLE):
                fname = field.name
                fields_kv[fname] = getattr(self, fname)

        new_entity = self.__class__(uuid=uuid.uuid4(), **fields_kv)
        new_entity._pre_save_clone(self)
        new_entity.save()
        new_entity._post_save_clone(self)

        new_entity._clone_m2m(self)

        new_entity._clone_custom_values(self)

        return new_entity

    def _copy_properties(self, source: 'CremeEntity') -> None:
        from . import CremeProperty

        creme_property_create = CremeProperty.objects.safe_create

        for type_id in source.properties.filter(
                type__is_copiable=True,
        ).values_list('type', flat=True):
            creme_property_create(type_id=type_id, creme_entity=self)

    def _copy_relations(self,
                        source: 'CremeEntity',
                        allowed_internal: Sequence[str] = (),
                        ) -> None:
        """@param allowed_internal: Sequence of RelationTypes PK with <is_internal=True>.
                  Relationships with these types will be cloned anyway.
        """
        from . import Relation, RelationType

        relation_create = Relation.objects.safe_create
        query = Q(
            type__in=RelationType.objects.compatible(
                self.entity_type,
            ).filter(Q(is_copiable=True)),
        )

        if allowed_internal:
            query |= Q(type__in=allowed_internal)

        for relation in source.relations.filter(query):
            relation_create(
                user_id=relation.user_id,
                subject_entity=self,
                type=relation.type,
                object_entity_id=relation.object_entity_id,
            )

    @atomic
    def clone(self) -> 'CremeEntity':
        """Take an entity and makes it copy.
        @returns : A new entity (with a different pk) with sames values
        """
        real_self = self.get_real_entity()
        new_entity = real_self._clone_object()

        new_entity._copy_properties(real_self)
        new_entity._copy_relations(real_self)

        new_entity._post_clone(real_self)

        return new_entity

    def restore(self) -> None:
        self.is_deleted = False
        self.save()

    def trash(self) -> None:
        self.is_deleted = True
        self.save()
