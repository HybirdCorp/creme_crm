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
import warnings
from collections import defaultdict
from typing import Iterable, Tuple, Type, Union

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, models
from django.db.models.query_utils import Q
from django.db.transaction import atomic
from django.dispatch import receiver
from django.http import Http404
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from ..signals import pre_merge_related
from ..utils.content_type import as_ctype
from . import fields as creme_fields
from .base import CremeModel
from .creme_property import CremePropertyType
from .entity import CremeEntity

logger = logging.getLogger(__name__)


class RelationTypeManager(models.Manager):
    def compatible(self,
                   ct_or_model: Union[ContentType, Type[CremeEntity]],
                   include_internals: bool = False,
                   ) -> models.QuerySet:
        types = self.filter(
            Q(subject_ctypes=as_ctype(ct_or_model))
            | Q(subject_ctypes__isnull=True)
        )

        if not include_internals:
            types = types.filter(Q(is_internal=False))

        return types

    @atomic
    def smart_update_or_create(
        self,
        subject_desc: tuple,
        object_desc: tuple,
        *,
        generate_pk: bool = False,
        is_custom: bool = False,
        is_internal: bool = False,
        is_copiable: Union[bool, Tuple[bool, bool]] = (True, True),
        minimal_display: Tuple[bool, bool] = (False, False),
    ) -> Tuple['RelationType', 'RelationType']:
        """Create or update 2 symmetric RelationTypes, with their constraints.
        @param subject_desc: Tuple describing the subject RelationType instance
               (
                string_pk, predicate_string
                [, sequence_of_cremeEntityClasses [, sequence_of_propertyTypes]]
               )
               'string_pk' is used as ID value (or it's prefix -- see generate_pk).
               'predicate_string' is used as <RelationType.predicate>.
               'sequence_of_cremeEntityClasses' is used to fill <RelationType.subject_ctypes>.
               'sequence_of_propertyTypes' is used to fill <RelationType.subject_properties>.
        @param object_desc: Tuple describing the object RelationType instance ;
               see 'subject_desc'.
        @param generate_pk: If True, 'string_pk' args are used as prefix to
               generate the Primary Keys.
        @param is_custom: Value of <RelationType.is_custom> in the created
               instances (same value for the both).
        @param is_internal: Value of <RelationType.is_internal> in the created
               instances (same value for the both).
        @param is_copiable: Values of <RelationType.is_copiable> in the created
               instances.
        @param minimal_display: Values of <RelationType.minimal_display> in the
               created instances.
        """
        # In case sequence_of_cremeEntityClasses or sequence_of_propertyType not given.
        padding = ((), ())

        subject_desc += padding
        object_desc  += padding

        if isinstance(is_copiable, bool):
            is_copiable = (is_copiable, is_copiable)

        pk_subject   = subject_desc[0]
        pk_object    = object_desc[0]
        pred_subject = subject_desc[1]
        pred_object  = object_desc[1]

        if not generate_pk:
            update_or_create = self.update_or_create
            defaults = {'is_custom': is_custom, 'is_internal': is_internal}
            sub_relation_type = update_or_create(
                id=pk_subject,
                defaults={
                    **defaults,
                    'predicate': pred_subject,
                    'is_copiable': is_copiable[0],
                    'minimal_display': minimal_display[0],
                },
            )[0]
            obj_relation_type = update_or_create(
                id=pk_object,
                defaults={
                    **defaults,
                    'predicate': pred_object,
                    'is_copiable': is_copiable[1],
                    'minimal_display': minimal_display[1],
                },
            )[0]
        else:
            from creme.creme_core.utils.id_generator import (
                generate_string_id_and_save,
            )

            model = self.model
            sub_relation_type = model(
                predicate=pred_subject, is_custom=is_custom, is_internal=is_internal,
                is_copiable=is_copiable[0], minimal_display=minimal_display[0],
            )
            obj_relation_type = model(
                predicate=pred_object,  is_custom=is_custom, is_internal=is_internal,
                is_copiable=is_copiable[1], minimal_display=minimal_display[1],
            )

            generate_string_id_and_save(model, [sub_relation_type], pk_subject)
            generate_string_id_and_save(model, [obj_relation_type], pk_object)

        sub_relation_type.symmetric_type = obj_relation_type
        obj_relation_type.symmetric_type = sub_relation_type

        # Delete old m2m (TODO: just remove useless ones ???)
        for rt in (sub_relation_type, obj_relation_type):
            rt.subject_ctypes.clear()
            rt.subject_properties.clear()

        get_ct = ContentType.objects.get_for_model

        for subject_ctype in subject_desc[2]:
            sub_relation_type.subject_ctypes.add(get_ct(subject_ctype))

        for object_ctype in object_desc[2]:
            obj_relation_type.subject_ctypes.add(get_ct(object_ctype))

        for subject_prop in subject_desc[3]:
            sub_relation_type.subject_properties.add(subject_prop)

        for object_prop in object_desc[3]:
            obj_relation_type.subject_properties.add(object_prop)

        sub_relation_type.save()
        obj_relation_type.save()

        return sub_relation_type, obj_relation_type


class RelationManager(models.Manager):
    def safe_create(self, **kwargs) -> None:
        """Create a Relation in DB by taking care of the UNIQUE constraint
        of Relation.
        Notice that, unlike 'create()' it always return None (to avoid a
        query in case of IntegrityError) ; use 'safe_get_or_create()' if
        you need the Relation instance.
        @param kwargs: same as 'create()'.
        """
        try:
            self.create(**kwargs)
        except IntegrityError:
            logger.exception('Avoid a Relation duplicate: %s ?!', kwargs)

    def safe_get_or_create(self, **kwargs) -> 'Relation':
        """Kind of safe version of 'get_or_create'.
        Safe means the UNIQUE constraint of Relation is respected, &
        this method will never raise an IntegrityError.

        Notice that the signature of this method is the same as 'create()'
        & not the same as 'get_or_create()' : the argument "defaults" does
        not exist. Pass directly the argument "user" ; it won't be used to
        retrieve the Relation, only for the Relation creation (if it's needed
        of course).

        @param kwargs: same as 'create()'.
        return: A Relation instance.
        """
        user = kwargs.pop('user', None)
        user_id = kwargs.pop('user_id') if user is None else user.id

        for _i in range(10):
            try:
                relation = self.get(**kwargs)
            except self.model.DoesNotExist:
                try:
                    # NB: Relation.save is already @atomic'd
                    relation = self.create(**kwargs, user_id=user_id)
                except IntegrityError:
                    logger.exception('Avoid a Relation duplicate: %s ?!', kwargs)
                    continue

            break
        else:
            raise RuntimeError(
                f'It seems the Relation <{kwargs}> keeps being created & deleted.'
            )

        return relation

    def safe_multi_save(self,
                        relations: Iterable['Relation'],
                        check_existing: bool = True,
                        ) -> int:
        """Save several instances of Relation by taking care of the UNIQUE
        constraint on ('type', 'subject_entity', 'object_entity').

        Notice that you should not rely on the instances which you gave ;
        they can be saved (so get a fresh ID), or not be saved because they are
        a duplicate (& so their ID remains 'None').

        Compared to use N x 'safe_get_or_create()', this method will only
        perform 1 query to retrieve the existing Relations.

        @param relations: An iterable of Relations (not save yet).
        @param check_existing: Perform a query to check existing Relations.
               You can pass False for newly created instances in order to avoid a query.
        @return: Number of Relations inserted in base.
                 NB: the symmetrical instances are not counted.
        """
        count = 0

        # Group the relations by their unique "signature" (type, subject, object)
        unique_relations = {}

        for relation in relations:
            # NB: we could use a string '{type_is}#{sub_id}#{obj_id}' => what is the best ?
            unique_relations[(
                relation.type_id,
                relation.subject_entity_id,
                relation.object_entity_id,
            )] = relation

        if unique_relations:
            if check_existing:
                # Remove all existing relations in the list of relation to be created.
                existing_q = Q()
                for relation in unique_relations.values():
                    existing_q |= Q(
                        type_id=relation.type_id,
                        subject_entity_id=relation.subject_entity_id,
                        object_entity_id=relation.object_entity_id,
                    )

                for rel_sig in self.filter(existing_q).values_list(
                    'type', 'subject_entity', 'object_entity',
                ):
                    unique_relations.pop(rel_sig, None)

            # Creation (we take the first of each group to guaranty uniqueness)
            for relation in unique_relations.values():
                try:
                    # NB: Relation.save is already @atomic'd
                    relation.save()
                except IntegrityError:
                    logger.exception('Avoid a Relation duplicate: %s ?!', relation)
                else:
                    count += 1

        return count


class RelationType(CremeModel):
    """Type of Relations.

    When you want to link (see Relation) to 2 kinds of CremeEntities
    (eg: Contact & Organisation) you define a type of relation with the
    following information :
      - The <predicate>, a string which describes the relation between the
        "subject" & the "object".
         Eg: "employs", "is a customer of"
      - List of ContentTypes which are allowed for the subjects & for the objects
        (attributes <subject_ctypes> & <object_ctypes>).
        Eg: the type "employs" accepts Organisations as subject, but not Invoice.
      - List of CremePropertyTypes which are mandatory for the subjects & for the objects
        (attributes <subject_properties> & <object_properties>).

    If *_ctypes = null --> all ContentTypes are valid.
    If *_properties = null --> all CremeProperties are valid.
    """
    # NB: convention: 'app_name-foobar'
    # BEWARE: 'id' MUST only contain alphanumeric '-' and '_'
    # TODO: validator ?
    id = models.CharField(primary_key=True, max_length=100)

    subject_ctypes = models.ManyToManyField(
        ContentType, blank=True, related_name='relationtype_subjects_set',
    )
    subject_properties = models.ManyToManyField(
        CremePropertyType, blank=True, related_name='relationtype_subjects_set',
    )

    # If True, the relations with this type cannot be created/deleted directly by the users.
    is_internal = models.BooleanField(default=False)

    # If True, the RelationType can ot be deleted (in creme_config).
    is_custom = models.BooleanField(default=False)

    # If True, the relations with this type can be copied
    #  (ie when cloning or converting an entity)
    is_copiable = models.BooleanField(default=True)

    # Try to display the relationships of this type only once in the detail-views ?
    # ie: does not display them in the general relationships bricks when another
    #     brick manages this type.
    minimal_display = models.BooleanField(default=False)

    predicate = models.CharField(_('Predicate'), max_length=100)
    symmetric_type = models.ForeignKey(
        'self', blank=True, null=True, on_delete=models.CASCADE,
    )

    objects = RelationTypeManager()

    creation_label = _('Create a type of relationship')
    save_label     = _('Save the type')

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('Type of relationship')
        verbose_name_plural = _('Types of relationship')
        ordering = ('predicate',)

    def __str__(self):
        sym_type = self.symmetric_type
        symmetric_pred = (
            gettext('No relationship')
            if sym_type is None else
            sym_type.predicate
        )

        return f'{self.predicate} — {symmetric_pred}'  # NB: — == "\xE2\x80\x94" == &mdash;

    def add_subject_ctypes(self, *models: Type[CremeEntity]) -> None:
        get_ct = ContentType.objects.get_for_model
        cts = [get_ct(model) for model in models]
        self.subject_ctypes.add(*cts)

    def delete(self, using=None, keep_parents=False):
        sym_type = self.symmetric_type

        super(RelationType, sym_type).delete(using=using)
        super().delete(using=using, keep_parents=keep_parents)

    @classmethod
    @atomic
    def create(
            cls,
            subject_desc: tuple,
            object_desc: tuple,
            is_custom: bool = False,
            generate_pk: bool = False,
            is_internal: bool = False,
            is_copiable: Union[bool, Tuple[bool, bool]] = (True, True),
            minimal_display: Tuple[bool, bool] = (False, False),
    ) -> Tuple['RelationType', 'RelationType']:
        warnings.warn(
            'RelationType.create() is deprecated; '
            'use RelationType.objects.smart_update_or_create() instead.',
            DeprecationWarning,
        )
        return cls.objects.smart_update_or_create(
            subject_desc=subject_desc,
            object_desc=object_desc,
            is_custom=is_custom,
            generate_pk=generate_pk,
            is_internal=is_internal,
            is_copiable=is_copiable,
            minimal_display=minimal_display,
        )

    # TODO: use the '/' (positional-only argument) in Python 3.8
    def is_compatible(self, *args) -> bool:
        """Can an instance of a given model be the subject of a Relation with this type.

        @param args: A single argument, the model, which can be:
               - A instance of ContentType.
               - An ID of ContentType.
               - A model class (inheriting CremeEntity).
               - A CremeEntity instance (its model is used).
        @return: Boolean. <True> means "yes it is compatible".
        """
        assert len(args) == 1

        # TODO: check if self.subject_ctypes.all() is already retrieved (prefetch_related)? cache ?
        subject_ctype_ids = frozenset(self.subject_ctypes.values_list('id', flat=True))

        arg = args[0]
        if isinstance(arg, ContentType):
            ctype_id = arg.id
        elif isinstance(arg, type):
            assert issubclass(arg, CremeEntity)

            ctype_id = ContentType.objects.get_for_model(arg).id
        elif isinstance(arg, CremeEntity):
            ctype_id = arg.entity_type_id
        else:
            ctype_id = int(arg)

        return not subject_ctype_ids or ctype_id in subject_ctype_ids

    def is_not_internal_or_die(self) -> None:
        if self.is_internal:
            # TODO: 409 ?
            raise Http404(gettext(
                "You can't add/delete the relationships with this type (internal type)"
            ))

    @property
    def object_ctypes(self):
        return self.symmetric_type.subject_ctypes

    @property
    def object_properties(self):
        return self.symmetric_type.subject_properties


class Relation(CremeModel):
    """2 instances of creme_core.models.CremeEntity can be linked by Relations.
    The first instance is called "object", the second one "object".

    A relation has a type (see RelationType).
     Eg: a Contact & an Organisation could be linked by a RelationType with
         <predicate="is employed by">

    Each instance of Relation has a symmetrical instance, which has the
    symmetrical RelationType.
     Eg: considering the previous example, we got a Relation instance between
         our Contact & an Organisation with a RelationType which could be like
         <predicate="employs">
    """
    created = creme_fields.CreationDateTimeField(_('Creation date')).set_tags(clonable=False)

    user = creme_fields.CremeUserForeignKey(verbose_name=_('Owner user'))

    type = models.ForeignKey(RelationType, on_delete=models.CASCADE)
    symmetric_relation = models.ForeignKey('self', null=True, on_delete=models.CASCADE)

    subject_entity = models.ForeignKey(
        CremeEntity, related_name='relations', on_delete=models.PROTECT,
    )
    object_entity = models.ForeignKey(
        CremeEntity, related_name='relations_where_is_object', on_delete=models.PROTECT,
    )

    objects = RelationManager()

    class Meta:
        app_label = 'creme_core'
        verbose_name = _('Relationship')
        verbose_name_plural = _('Relationships')
        unique_together = ('type', 'subject_entity', 'object_entity')

    def __str__(self):
        return f'«{self.subject_entity}» {self.type} «{self.object_entity}»'

    # def _build_symmetric_relation(self, update: bool):
    #     warnings.warn(
    #         'Relation._build_symmetric_relation() is deprecated.',
    #         DeprecationWarning
    #     )
    #
    #     if update:
    #         sym_relation = self.symmetric_relation
    #         assert sym_relation
    #     else:
    #         sym_relation = Relation(
    #             user=self.user,
    #             type=self.type.symmetric_type,
    #             symmetric_relation=self,
    #             subject_entity=self.object_entity,
    #             object_entity=self.subject_entity,
    #         )
    #
    #     return sym_relation

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """See django.db.models.Model.save().
        Notice that Relation instances should only be created, not updated.

        @param force_update: Not used.
        @param update_fields: Not used.
        """
        if self.pk is not None:
            logger.warning(
                'Relation.save(): try to update instance pk=%s (should only be created).',
                self.pk
            )
            return

        with atomic():
            super().save(using=using, force_insert=force_insert)

            cls = type(self)
            sym_relation = cls(
                user=self.user,
                type=self.type.symmetric_type,
                symmetric_relation=self,
                subject_entity=self.object_entity,
                object_entity=self.subject_entity,
            )
            super(cls, sym_relation).save(using=using, force_insert=force_insert)

            self.symmetric_relation = sym_relation
            super().save(
                using=using, force_insert=False,
                update_fields=['symmetric_relation'],
            )

    @staticmethod
    def populate_real_object_entities(relations: Iterable['Relation']) -> None:
        """Faster than call get_real_entity() on each relation.object_entity.
        @param relations: Iterable of Relation objects.

        Tips: better if object_entity attribute is already populated
        -> (eg: use select_related('object_entity') on the queryset)
        """
        CremeEntity.populate_real_entities([
            relation.object_entity for relation in relations
        ])


class SemiFixedRelationType(CremeModel):
    predicate = models.CharField(_('Predicate'), max_length=100, unique=True)
    relation_type = models.ForeignKey(RelationType, on_delete=models.CASCADE)
    object_entity = models.ForeignKey(CremeEntity, on_delete=models.CASCADE)

    creation_label = _('Create a semi-fixed type of relationship')
    save_label     = _('Save the type')

    class Meta:
        app_label = 'creme_core'
        unique_together = ('relation_type', 'object_entity')
        verbose_name = _('Semi-fixed type of relationship')
        verbose_name_plural = _('Semi-fixed types of relationship')
        ordering = ('predicate',)

    def __str__(self):
        return self.predicate


@receiver(pre_merge_related)
def _handle_merge(sender, other_entity, **kwargs):
    """The generic creme_core.utils.replace_related_object() cannot correctly
    handle the Relation model :
      - we have to keep the uniqueness of (subject, type, object)
      - replacing the remaining entity as subject/object in the Relations of
        'other_entity' should not create multiple HistoryLines.
        (because with the symmetric relationships feature, its tricky).

    So this handler does the job i the right way:
      - it deletes the 'duplicated' Relations (ie: exist in the removed entity
        & the remaining entity), without creating HistoryLines at all.
      - it updates the relationships which reference the removed entity to
        reference the remaining entity (History is managed by hand).
    """
    from .history import HistoryLine, _HLTRelation

    # Deletion of duplicates ---------------------------------------------------
    # Key#1 => relation-type ID
    # Key#2 => object_entity ID (linked to at least one of the merged entities)
    # Value => set of merged entities IDs (so 1 or 2 IDs between [sender.id, other_entity.id])
    entities_per_rtype_ids = defaultdict(lambda: defaultdict(set))

    for merged_id, rtype_id, object_id in RelationType.objects.filter(
        relation__subject_entity__in=(sender.id, other_entity.id)
    ).values_list(
        'relation__subject_entity_id', 'id', 'relation__object_entity_id',
    ):
        entities_per_rtype_ids[rtype_id][object_id].add(merged_id)

    duplicates_q = Q()
    for rtype_id, entities_dict in entities_per_rtype_ids.items():
        for object_id, subject_ids in entities_dict.items():
            if len(subject_ids) > 1:
                duplicates_q |= Q(type=rtype_id, object_entity=object_id)

    del entities_per_rtype_ids  # free memory

    if duplicates_q:
        for relation in other_entity.relations.filter(duplicates_q) \
                                    .select_related('symmetric_relation'):
            # NB: HistoryLine.disable() work only on the '-subject_' side of the Relation
            if '-subject_' not in relation.type_id:
                relation = relation.symmetric_relation

            HistoryLine.disable(relation)
            relation.delete()

    # Replacement of ForeignKeys -----------------------------------------------

    for relation in other_entity.relations.select_related('symmetric_relation'):
        relation.subject_entity = sender
        relation.symmetric_relation.object_entity = sender
        # NB: <created=False> because the function create lines only at edition
        #     (to ensure the 2 linked Relation instances are created).
        _HLTRelation.create_lines(relation, created=False)

    other_entity.relations.update(subject_entity=sender)
    other_entity.relations_where_is_object.update(object_entity=sender)
