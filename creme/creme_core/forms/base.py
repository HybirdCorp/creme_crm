################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from __future__ import annotations

import logging
from collections import OrderedDict
from copy import copy
from functools import partial
from typing import TYPE_CHECKING, Literal

from django import forms
from django.conf import settings
from django.db.models import Q
from django.forms.boundfield import BoundField
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from ..models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    CustomField,
    CustomFieldValue,
    FieldsConfig,
    Relation,
    RelationType,
    SemiFixedRelationType,
)
from ..utils.collections import FluentList
from . import fields as core_fields
from . import widgets
from .validators import validate_linkable_model

if TYPE_CHECKING:
    from typing import (
        Any,
        Callable,
        Collection,
        Iterable,
        Iterator,
        Sequence,
        Union,
    )

    from ..gui.custom_form import CustomFormExtraSubCell

    # TODO: use Literal for '*' case?
    FieldNamesOrWildcard = Union[Sequence[str], str]
    FormCallback = Callable[[forms.Form], None]

__all__ = (
    'LayoutType',
    'LAYOUT_REGULAR', 'LAYOUT_DUAL_FIRST', 'LAYOUT_DUAL_SECOND', 'LAYOUTS',
    'FieldBlockManager', 'CremeForm', 'CremeModelForm',
    'CremeEntityForm', 'CremeEntityQuickForm',
)

logger = logging.getLogger(__name__)

# NB: we use a '-' to be sure that collision with a regular field is not possible
_CUSTOM_NAME = 'custom_field-{}'

LayoutType = Literal['regular', 'dual_first', 'dual_second']
LAYOUT_REGULAR: LayoutType = 'regular'
LAYOUT_DUAL_FIRST: LayoutType = 'dual_first'
LAYOUT_DUAL_SECOND: LayoutType = 'dual_second'

LAYOUTS = {
    LAYOUT_REGULAR,
    LAYOUT_DUAL_FIRST,
    LAYOUT_DUAL_SECOND,
}


class _FieldBlock:
    __slots__ = (
        'id', 'label', 'field_names',
        'layout', 'template_name', 'template_context',
    )

    default_template_name = 'creme_core/generics/blockform/field-block.html'
    field_names: str | list[str]

    def __init__(self,
                 *,
                 id: str,
                 label: str,
                 field_names: FieldNamesOrWildcard,
                 layout: LayoutType | None = None,
                 template_name: str | None = None,
                 template_context: dict | None = None,
                 ):
        """Constructor.
        @param id: String identifying this block among the group.
        @param label: Title of the block (displayed in the output).
        @param field_names: Sequence of strings (fields names in the form)
               or string '*' (wildcard->all remaining fields).
        @param layout: Layout types (see LAYOUTS) or None ; LAYOUT_REGULAR by default.
        @param template_name: path to the template to use for render, or None ;
               The attribute "default_template_name" is used by default.
       @param template_context: dictionary intended to be used during the
              template rendering, or None.
        """
        self.id = id
        self.label = label
        self.layout: LayoutType = layout or LAYOUT_REGULAR
        self.template_name = template_name or self.default_template_name
        self.template_context = template_context

        if self.layout not in LAYOUTS:
            raise ValueError(f'The layout "{layout}" is invalid.')

        if isinstance(field_names, str):
            assert field_names == '*', f'{field_names!r} != "*"'
            self.field_names = field_names
        else:
            self.field_names = [*field_names]

    def __repr__(self):
        return (
            f'_FieldBlock('
            f'id="{self.id}", '
            f'label="{self.label}", '
            f'layout="{self.layout}", '
            f'template_name="{self.template_name}", '
            f'template_context={self.template_context!r}, '
            f'field_names={self.field_names!r}'
            f')'
        )


class BoundFieldBlocks:
    """A collection to retrieve blocks of <django.form.BoundField> instances.
    Used by templates to get blocks by their ID, or iterate on blocks.
    Hint: you should not build them directly ; use FieldBlockManager.build() instead.
    """
    class BoundFieldBlock:
        __slots__ = (
            'id', 'label', 'bound_fields',
            'layout', 'template_name', 'template_context',
        )

        def __init__(self,
                     *,
                     id: str,
                     label: str,
                     bound_fields: list[BoundField],
                     layout: LayoutType,
                     template_name: str,
                     template_context: dict | None,
                     ):
            self.id = id
            self.label = label
            self.bound_fields = bound_fields
            self.layout = layout
            self.template_name = template_name
            self.template_context = template_context

    _blocks_data: dict[
        str,  # Block ID
        BoundFieldBlock
    ]

    def __init__(self,
                 form: forms.BaseForm,
                 blocks_items: Iterable[tuple[str, _FieldBlock]],
                 ):
        blocks_data = self._blocks_data = OrderedDict()
        wildcard_id: str | None = None
        field_set: set[str] = set()

        BFB = self.BoundFieldBlock

        for block_id, block in blocks_items:
            field_names = block.field_names

            if isinstance(field_names, str):  # Wildcard
                assert field_names == '*'

                if wildcard_id:
                    raise ValueError(f'Only one wildcard is allowed: {type(form)}')

                # We fill the fields info list at the end
                blocks_data[block_id] = BFB(
                    id=block_id,
                    label=block.label,
                    layout=block.layout,
                    bound_fields=[],
                    template_name=block.template_name,
                    template_context=block.template_context,
                )
                wildcard_id = block_id
            else:
                field_set |= {*field_names}
                bound_fields = []

                for fn in field_names:
                    try:
                        bound_field = form[fn]
                    except KeyError as e:
                        logger.debug('BoundFieldBlocks: %s', e)
                    else:
                        bound_fields.append(bound_field)

                blocks_data[block_id] = BFB(
                    id=block_id,
                    label=block.label,
                    bound_fields=bound_fields,
                    layout=block.layout,
                    template_name=block.template_name,
                    template_context=block.template_context,
                )

        if wildcard_id is not None:
            blocks_data[wildcard_id].bound_fields.extend(
                form[name]
                for name in form.fields.keys()
                if name not in field_set
            )

    def __getitem__(self, block_id: str) -> BoundFieldBlock:
        """Beware: it pops the retrieved value (__getitem__ is more comfortable
        to be used in templates than a classical method with an argument).
        @return A BoundFieldBlock instance.
        """
        return self._blocks_data.pop(block_id)

    def __iter__(self) -> Iterator[BoundFieldBlock]:
        """Iterates on the non used blocks (see __getitem__).
        @return A sequence of BoundFieldBlock instances.
        """
        return iter(self._blocks_data.values())


class FieldBlockManager:
    __slots__ = ('__blocks',)

    __blocks: dict[str, _FieldBlock]

    def __init__(self, *blocks: tuple[str, str, FieldNamesOrWildcard] | dict):
        """Constructor.
        @param blocks: Each block info can be either
                - a tuple with 3 elements:
                  (block_ID(string), block_label(i18n string), sequence_of_field_names)
                  3rd element can be instead a wildcard (the string '*') which
                  means 'all remaining fields'.
                - a dictionary which contains:
                  "id": block's string ID.
                  "label": i18n string.
                  "fields": a sequence of field names, or the wildcard.
                  "layout": see LAYOUTS ; optional. Hint: cannot be passed with the tuple format.
                  "template": path to the template to use for render ; optional
                              (default template is
                              "creme_core/generics/blockform/field-block.html").
                              Hint: cannot be passed with the tuple format.
                  "context": dictionary used by the template
                             (see <BoundFieldBlock.template_context>).
                             Hint: cannot be passed with the tuple format.
               Only zero or one wildcard is allowed.
        """
        # Beware: use a list comprehension instead of a generator expression with this constructor

        def block_kwargs():
            for e in blocks:
                if isinstance(e, tuple):
                    block_id, block_label, field_names = e
                    yield block_id, {'label': block_label, 'field_names': field_names}
                elif isinstance(e, dict):
                    if 'order' in e:
                        raise ValueError(
                            'Do not pass <order> information in FieldBlockManager constructor.'
                        )

                    yield (
                        e['id'],
                        {
                            'label': e['label'],
                            'field_names': e['fields'],
                            'layout': e.get('layout'),
                            'template_name': e.get('template'),
                            'template_context': e.get('context'),
                        },
                    )
                else:
                    raise TypeError('Arguments <blocks> must be tuples or dicts.')

        self.__blocks = OrderedDict([
            (block_id, _FieldBlock(id=block_id, **kwargs))
            for block_id, kwargs in block_kwargs()
        ])

    def new(self,
            *blocks: tuple[str, str, FieldNamesOrWildcard] | dict,
            ) -> FieldBlockManager:
        """Create a clone of self, updated with new blocks.
        @param blocks: see __init__(). New blocks are merged with self's blocks.
               If you use the dictionary format, you can use an extra key "order"
               associated to an integer value, which indicates the index where to
               insert the block (only for new blocks for now).
        """
        merged_blocks = OrderedDict([
            (block_id, copy(block))
            for block_id, block in self.__blocks.items()
        ])
        blocks_to_add: list[_FieldBlock] = []
        blocks_to_insert: list[tuple[int, _FieldBlock]] = []

        for e in blocks:
            if isinstance(e, tuple):
                block_id, block_label, block_field_names = e
                block_layout = None
                block_order = None
            elif isinstance(e, dict):
                block_id = e['id']
                block_label = e['label']
                block_field_names = e['fields']
                block_layout = e.get('layout')
                block_order = e.get('order')
                assert (block_order is None) or (isinstance(block_order, int) and block_order >= 0)
            else:
                raise TypeError('Arguments <blocks> must be tuples or dicts')

            field_block = merged_blocks.get(block_id)

            if field_block is not None:
                field_block.label = block_label

                if isinstance(field_block.field_names, str):
                    assert field_block.field_names == '*'

                    # TODO: possibility to have ('fieldX', 'fieldY', '*', 'fieldZ') ??
                    raise ValueError(
                        f'You cannot extend a wildcard '
                        f'(see the form-block with category "{block_id}")'
                    )

                if isinstance(block_field_names, str):
                    assert block_field_names == '*'

                    # TODO: idem
                    raise ValueError(
                        f'You cannot extend with a wildcard '
                        f'(see the form-block with category "{block_id}")'
                    )

                field_block.field_names.extend(block_field_names)
                if block_layout:  # TODO: 'layout' property with checking?
                    field_block.layout = block_layout
            else:
                field_block = _FieldBlock(
                    id=block_id, label=block_label,
                    field_names=block_field_names,
                    layout=block_layout,
                )

                if block_order is None:
                    blocks_to_add.append(field_block)
                else:
                    blocks_to_insert.append((block_order, field_block))

        final_blocks: dict[str, _FieldBlock] = OrderedDict()

        blocks_to_insert.sort(key=lambda t: t[0], reverse=True)

        for merged_block in merged_blocks.values():
            while blocks_to_insert and blocks_to_insert[-1][0] <= len(final_blocks):
                field_block = blocks_to_insert.pop()[1]
                final_blocks[field_block.id] = field_block

            final_blocks[merged_block.id] = merged_block

        for __, field_block in reversed(blocks_to_insert):
            final_blocks[field_block.id] = field_block

        for field_block in blocks_to_add:
            final_blocks[field_block.id] = field_block

        fbm = FieldBlockManager()
        fbm.__blocks = final_blocks  # Yerk....

        return fbm

    def build(self, form: forms.BaseForm) -> BoundFieldBlocks:
        """You should not call this directly ; see CremeForm/CremeModelForm
        get_blocks() method.
        @param form: An instance of <django.forms.Form>.
        @return An instance of BoundFieldBlocks.
        """
        return BoundFieldBlocks(form, self.__blocks.items())


class HookableFormMixin:
    # Beware: use related method to manipulate
    _creme_post_clean_callbacks: Sequence[FormCallback] = ()  # ==> add_post_clean_callback()
    _creme_post_init_callbacks: Sequence[FormCallback]  = ()  # ==> add_post_init_callback()
    _creme_post_save_callbacks: Sequence[FormCallback]  = ()  # ==> add_post_save_callback()

    @classmethod
    def __add_callback(cls, attrname: str, callback: FormCallback) -> type[HookableFormMixin]:
        setattr(cls, attrname, [*getattr(cls, attrname), callback])
        return cls

    @classmethod
    def add_post_clean_callback(cls, callback: FormCallback) -> type[HookableFormMixin]:
        return cls.__add_callback('_creme_post_clean_callbacks', callback)

    @classmethod
    def add_post_init_callback(cls, callback: FormCallback) -> type[HookableFormMixin]:
        return cls.__add_callback('_creme_post_init_callbacks', callback)

    @classmethod
    def add_post_save_callback(cls, callback: FormCallback) -> type[HookableFormMixin]:
        return cls.__add_callback('_creme_post_save_callbacks', callback)

    def _creme_post_clean(self) -> None:
        for callback in self._creme_post_clean_callbacks:
            callback(self)

    def _creme_post_init(self) -> None:
        for callback in self._creme_post_init_callbacks:
            callback(self)

    def _creme_post_save(self) -> None:
        for callback in self._creme_post_save_callbacks:
            callback(self)


# class SpanRenderableFormMixin:
#     template_name_span = 'creme_core/forms/span.html'


class CremeForm(HookableFormMixin, forms.Form):
    blocks = FieldBlockManager({
        'id': 'general', 'label': _('General information'), 'fields': '*',
    })

    def __init__(self, user, *args, **kwargs):
        """Constructor.
        @param user: The user who sends the request (i order to check the permissions)
        @param args: see <django.forms.Form>.
        @param kwargs: see <django.forms.Form>.
        """
        super().__init__(*args, **kwargs)
        self.user = user

        for fn, field in self.fields.items():
            field.user = user  # Used by CreatorModelChoiceField for example

        self._creme_post_init()

    def clean(self, *args, **kwargs):
        res = super().clean()
        self._creme_post_clean()
        return res

    def get_blocks(self) -> BoundFieldBlocks:
        return self.blocks.build(self)

    def save(self, *args, **kwargs):
        self._creme_post_save()


class CremeModelForm(HookableFormMixin, forms.ModelForm):
    blocks = FieldBlockManager({
        'id': 'general', 'label': _('General information'), 'fields': '*',
    })

    class Meta:
        fields: str | tuple[str, ...] = '__all__'

    def __init__(self, user, *args, **kwargs):
        """Constructor.
        @param user: The user who sends the request (in order to check the permissions).
        @param args: see <django.forms.ModelForm>.
        @param kwargs: see <django.forms.ModelForm>.
        """
        super().__init__(*args, **kwargs)
        self.user = user

        for fn, field in self.fields.items():
            field.user = user  # Used by CreatorModelChoiceField for example

        self.fields_configs = FieldsConfig.LocalCache()
        self._build_required_fields()

        self._creme_post_init()

    def _build_required_fields(self):
        # NB: not <type(self.instance)> because it returns an instance of
        #     SimpleLazyObject for User, which causes an error.
        self.fields_configs.get_for_model(self.instance.__class__).update_form_fields(self)

    def clean(self):
        res = super().clean()
        self._creme_post_clean()
        return res

    def get_blocks(self) -> BoundFieldBlocks:
        return self.blocks.build(self)

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        self._creme_post_save()
        return instance


class CustomFieldsMixin:
    @staticmethod
    def _build_customfield_name(cfield):
        return _CUSTOM_NAME.format(cfield.id)

    def _build_customfields(self, only_required=False) -> None:
        self._customs = self._get_customfields_n_values(only_required=only_required)
        fields = self.fields
        user = self.user
        build_name = self._build_customfield_name

        for cfield, cvalue in self._customs:
            fields[build_name(cfield)] = cfield.get_formfield(cvalue, user=user)

    def _get_customfields_n_values(self, only_required):
        return self.instance.get_custom_fields_n_values(only_required=only_required)

    def _save_customfields(self) -> None:
        cfields_n_values = self._customs

        if cfields_n_values:
            cleaned_data = self.cleaned_data
            instance = self.instance
            build_name = self._build_customfield_name

            for cfield, __cvalue in cfields_n_values:
                value = cleaned_data[build_name(cfield)]
                CustomFieldValue.save_values_for_entities(cfield, [instance], value)


class CremeEntityForm(CustomFieldsMixin, CremeModelForm):
    property_types = core_fields.PropertyTypesChoiceField(required=False)

    rtypes_info = forms.CharField(
        label=_('Information on relationships'),
        required=False,
        widget=widgets.Label,
    )
    relation_types = core_fields.MultiRelationEntityField(
        label=_('Relationships to add'),
        required=False,
        autocomplete=True,
    )
    semifixed_rtypes = forms.ModelMultipleChoiceField(
        label=_('Semi-fixed types of relationship'),
        queryset=SemiFixedRelationType.objects.none(),
        required=False,
        # NB: the hook to use this widget automatically is done after...
        widget=widgets.UnorderedMultipleChoiceWidget,
    )

    error_messages = {
        'subject_not_linkable': _(
            'You are not allowed to link the created entity (wrong owner?).'
        ),
    }

    blocks = CremeModelForm.blocks.new(
        {
            'id': 'description',
            'label': _('Description'),
            'fields': ['description'],
        }, {
            'id': 'properties',
            'label': _('Properties'),
            'fields': ['property_types'],
        }, {
            'id': 'relationships',
            'label': _('Relationships'),
            'fields': ['rtypes_info', 'relation_types', 'semifixed_rtypes'],
        },
    )

    class Meta:
        exclude: tuple[str, ...] = ()
        fields = '__all__'

    forced_ptype_ids: list[str]
    forced_relations_info: list[tuple[RelationType, CremeEntity]]
    _customs: list[tuple[CustomField, Any]]

    def __init__(self,
                 forced_ptypes: Iterable[CremePropertyType | str] = (),
                 forced_relations: Iterable[Relation] = (),
                 *args, **kwargs):
        """Constructor.
        @param forced_ptypes: Sequence of CremePropertyType IDs/instances ;
               CremeProperties with these types will be added to the instance.
        @param forced_relations: Sequence of (unsaved) Relations instances ;
               These Relations will be added to the instance. Notice that:
                - <instance> will be used as subject (i.e. you do not have to
                  fill the attribute 'subject_entity').
                - The attribute <user> will be set automatically too.
                - So just fill the attributes <type> & <object_entity>.
        @param args: see CremeModelForm.
        @param kwargs: see CremeModelForm.
        """
        super().__init__(*args, **kwargs)
        assert isinstance(self.instance, CremeEntity)
        self._build_customfields()

        self.forced_ptype_ids = ptypes_ids = [
            pt.id if isinstance(pt, CremePropertyType) else pt
            for pt in forced_ptypes
        ]
        self._build_properties_field(forced_ptype_ids=ptypes_ids)

        self.forced_relations_info = forced_relations_info = [
            (r.type, r.object_entity) for r in forced_relations
        ]
        self._build_relations_fields(forced_relations_info=forced_relations_info)

    def _build_properties_field(self, forced_ptype_ids: Iterable[str]) -> None:
        instance = self.instance

        if self._use_properties_fields() and not instance.pk:
            ptypes_f = self.fields['property_types']
            ptypes_f.queryset = CremePropertyType.objects.compatible(
                type(instance)
            ).filter(enabled=True)
            ptypes_f.forced_values = forced_ptype_ids
        else:
            del self.fields['property_types']

    def _build_relations_fields(
        self,
        forced_relations_info: list[tuple[RelationType, CremeEntity]],
    ) -> None:
        fields = self.fields
        instance = self.instance
        info: str | None = None

        if self._use_relations_fields() and not instance.pk:
            if forced_relations_info:
                if len(forced_relations_info) == 1:
                    rel = forced_relations_info[0]
                    info = _(
                        'This relationship will be added: {predicate} «{entity}»'
                    ).format(predicate=rel[0].predicate, entity=rel[1])
                else:
                    item_msg_fmt = gettext('{predicate} «{entity}»').format
                    info = mark_safe(
                        ngettext(
                            'This relationship will be added: {}',
                            'These relationships will be added: {}',
                            number=len(forced_relations_info),
                        ).format(format_html(
                            '<ul>{}</ul>',  # TODO:  class="form-help-label" ??
                            format_html_join(
                                '', '<li>{}</li>',
                                (
                                    [item_msg_fmt(predicate=rtype.predicate, entity=entity)]
                                    for rtype, entity in forced_relations_info
                                )
                            )
                        ))
                    )

            if self.user.has_perm_to_link(type(instance)):
                ctype = instance.entity_type
                fields['relation_types'].allowed_rtypes = (
                    RelationType.objects
                                .compatible(ctype)
                                .filter(enabled=True)
                )

                # TODO: factorise ?
                entities = [
                    sfrt.object_entity
                    for sfrt in SemiFixedRelationType.objects
                                                     .select_related('object_entity')
                ]
                sfrt_qs = SemiFixedRelationType.objects.filter(
                    Q(relation_type__subject_ctypes=ctype)
                    | Q(relation_type__subject_ctypes__isnull=True),
                ).filter(
                    object_entity__in=filter(self.user.has_perm_to_link, entities),
                    relation_type__enabled=True,
                )

                if sfrt_qs.exists():
                    fields['semifixed_rtypes'].queryset = sfrt_qs
                else:
                    del fields['semifixed_rtypes']
            else:
                info = _('You are not allowed to link this kind of entity.')

                del fields['relation_types']
                del fields['semifixed_rtypes']
        else:
            del fields['relation_types']
            del fields['semifixed_rtypes']

        if info is None:
            del fields['rtypes_info']
        else:
            fields['rtypes_info'].initial = info

    def _check_properties(self, rtypes: Iterable[RelationType]):
        for rtype in rtypes:
            Relation(
                # user=self.user,
                subject_entity=self.instance,
                type=rtype,
                # object_entity=...
            ).clean_subject_entity(
                property_types=self.cleaned_data.get('property_types', ()),
            )

    def _check_subject_linkable(self, rtypes: Collection[RelationType]) -> None:
        if rtypes and not self.user.has_perm_to_link(
            type(self.instance), owner=self.cleaned_data['user'],
        ):
            raise forms.ValidationError(
                self.error_messages['subject_not_linkable'],
                code='subject_not_linkable',
            )

    def clean_relation_types(self):
        rel_desc = self.cleaned_data['relation_types']
        rtypes = [rtype for rtype, e_ in rel_desc]
        self._check_properties(rtypes)
        self._check_subject_linkable(rtypes)

        return rel_desc

    def clean_semifixed_rtypes(self):
        sf_rtypes = self.cleaned_data['semifixed_rtypes']
        rtypes = [sf_rtype.relation_type for sf_rtype in sf_rtypes]
        self._check_properties(rtypes)
        self._check_subject_linkable(rtypes)

        return sf_rtypes

    def clean_user(self):
        owner = self.cleaned_data['user']

        if self.forced_relations_info:
            validate_linkable_model(self._meta.model, self.user, owner=owner)

        return owner

    # TODO: -> FluentList[Relation]
    def _get_relations_to_create(self):
        cdata = self.cleaned_data
        subject = self.instance
        build_relation = partial(Relation, user=subject.user, subject_entity=subject)

        return FluentList(
            build_relation(
                type=rtype,
                object_entity=object_entity,
            ) for rtype, object_entity in cdata.get('relation_types', ())
        ).extend(
            build_relation(
                type=sfrt.relation_type,
                object_entity=sfrt.object_entity,
            ) for sfrt in cdata.get('semifixed_rtypes', ())
        ).extend(
            build_relation(
                type=rtype,
                object_entity=entity,
            ) for rtype, entity in self.forced_relations_info
        )

    # TODO: -> FluentList[CremeProperty]
    def _get_properties_to_create(self):
        instance = self.instance

        try:
            cleaned_ptypes = self.cleaned_data['property_types']
        except KeyError:
            ptype_ids = self.forced_ptype_ids
        else:
            ptype_ids = [ptype.id for ptype in cleaned_ptypes]

        return FluentList(
            CremeProperty(creme_entity=instance, type_id=ptype_id)
            for ptype_id in ptype_ids
        )

    def _save_properties(self,
                         properties: Iterable[CremeProperty],
                         check_existing: bool = True,
                         ) -> None:
        CremeProperty.objects.safe_multi_save(properties, check_existing=check_existing)

    def _save_relations(self,
                        relations: Iterable[Relation],
                        check_existing: bool = True,
                        ) -> None:
        Relation.objects.safe_multi_save(relations, check_existing=check_existing)

    def save(self, *args, **kwargs):
        created = self.instance.pk is None  # TODO: attribute in CremeModelForm ?
        instance = super().save(*args, **kwargs)
        self._save_customfields()
        self._save_properties(
            properties=self._get_properties_to_create(),
            check_existing=not created,
        )
        self._save_relations(
            relations=self._get_relations_to_create(),
            check_existing=not created,
        )

        return instance

    def subcell_key(self, subcell_cls: type[CustomFormExtraSubCell]) -> str:
        "Helper method when writing base class for Custom forms."
        return subcell_cls(model=self._meta.model).into_cell().key

    def _use_properties_fields(self):
        return settings.FORMS_RELATION_FIELDS

    def _use_relations_fields(self):
        return settings.FORMS_RELATION_FIELDS


class CremeEntityQuickForm(CustomFieldsMixin, CremeModelForm):
    class Meta:
        fields: str | tuple[str, ...] = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert isinstance(self.instance, CremeEntity)

        self._build_customfields(only_required=True)

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        self._save_customfields()

        return instance
