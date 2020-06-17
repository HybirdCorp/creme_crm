# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

# import warnings
import logging
from collections import OrderedDict
from functools import partial
from typing import (
    Any,
    Callable,
    Collection,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)

from django import forms
from django.conf import settings
from django.db.models import Q
from django.forms.boundfield import BoundField
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

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
from . import fields, widgets

__all__ = (
    'FieldBlockManager', 'CremeForm', 'CremeModelForm',
    # 'CremeModelWithUserForm',
    'CremeEntityForm', 'CremeEntityQuickForm',
)

logger = logging.getLogger(__name__)
_CUSTOM_NAME = 'custom_field_{}'


# TODO: add a render method with a template_name attribute ;
#       stores the block ID as an HTML custom attribute.
#      (see Contact/Organisation form)
class _FieldBlock:
    __slots__ = ('name', 'field_names')

    name: str
    field_names: Union[List[str], str]  # TODO: use Litteral for '*' case ?

    def __init__(self, verbose_name: str, field_names: Union[Sequence[str], str]):
        """Constructor.
        @param verbose_name: Name of the block (displayed in the output).
        @param field_names: Sequence of strings (fields names in the form)
               or string '*' (wildcard->all remaining fields).
        """
        self.name = verbose_name

        if isinstance(field_names, str):
            assert field_names == '*'
            self.field_names = field_names
        else:
            self.field_names = [*field_names]

    def __str__(self):  # For debugging
        return f'<_FieldBlock: {self.name} {self.field_names}>'


class FieldBlocksGroup:
    """You should not build them directly ; use FieldBlockManager.build() instead.
    It contains a list of block descriptors. A blocks descriptor is a tuple
    (block_verbose_name, [list of tuples (BoundField, field_is_required)]).
    """
    _blocks_data: Dict[
        str,  # Category name
        Tuple[
            str,  # Block name
            List[
                Tuple[
                    BoundField,
                    bool  # Is field required ?
                ]
            ]
        ]
    ]

    def __init__(self,
                 form: forms.BaseForm,
                 blocks_items: Iterable[Tuple[str, _FieldBlock]]):
        blocks_data = self._blocks_data = OrderedDict()
        wildcard_cat: Optional[str] = None
        field_set: Set[str] = set()

        for cat, block in blocks_items:
            field_names = block.field_names

            if isinstance(field_names, str):  # Wildcard
                assert field_names == '*'

                if wildcard_cat:
                    raise ValueError(f'Only one wildcard is allowed: {type(form)}')

                blocks_data[cat] = (block.name, [])  # We fill the fields info list at the end
                wildcard_cat = cat
            else:
                field_set |= {*field_names}
                block_data = []

                for fn in field_names:
                    try:
                        bound_field = form[fn]
                    except KeyError as e:
                        logger.debug('FieldBlocksGroup: %s', e)
                    else:
                        block_data.append((bound_field, form.fields[fn].required))

                blocks_data[cat] = (block.name, block_data)

        if wildcard_cat is not None:
            blocks_data[wildcard_cat][1].extend(
                (form[name], field.required)
                for name, field in form.fields.items()
                if name not in field_set
            )

    def __getitem__(self, category: str):
        """Beware: it pops the retrieved value (__getitem__ is more comfortable
        to be used in templates than a classical method with an argument).
        @return A block descriptor (see FieldBlocksGroup doc string).
        """
        return self._blocks_data.pop(category)

    def __iter__(self) -> Iterator:
        """Iterates on the non used blocks (see __getitem__).
        @return A sequence of block descriptors (see FieldBlocksGroup doc string).
        """
        return iter(self._blocks_data.values())


class FieldBlockManager:
    __slots__ = ('__blocks',)

    __blocks: Dict[str, _FieldBlock]

    def __init__(self, *blocks: Tuple[str, str, Union[Sequence[str], str]]):
        """Constructor.
        @param blocks: tuples with 3 elements : category(string), verbose_name(i18n string), sequence of field names
               3rd element can be instead a wildcard (the string '*') which mean 'all remaining fields'.
               Only zero or one wildcard is allowed.
        """
        # Beware: use a list comprehension instead of a generator expression with this constructor
        self.__blocks = OrderedDict(
            [(cat, _FieldBlock(name, field_names)) for cat, name, field_names in blocks]
        )

    def new(self, *blocks: Tuple[str, str, Sequence[str]]) -> 'FieldBlockManager':
        """Create a clone of self, updated with new blocks.
        @param blocks: see __init__(). New blocks are merged with self's blocks.
        """
        merged_blocks = OrderedDict([
            (cat, _FieldBlock(block.name, block.field_names))
            for cat, block in self.__blocks.items()
        ])
        to_add = []

        for cat, name, field_names in blocks:
            field_block = merged_blocks.get(cat)

            if field_block is not None:
                field_block.name = name

                if isinstance(field_block.field_names, str):
                    assert field_block.field_names == '*'

                    # TODO: possibility to have ('fieldX', 'fieldY', '*', 'fieldZ') ??
                    raise ValueError(
                        f'You cannot extend a wildcard (see the form-block with category "{cat}")'
                    )
                else:
                    if isinstance(field_names, str):
                        assert field_names == '*'

                        # TODO: idem
                        raise ValueError(
                            f'You cannot extend with a wildcard (see the form-block with category "{cat}")'
                        )
                    else:
                        field_block.field_names.extend(field_names)
            else:
                to_add.append((cat, _FieldBlock(name, field_names)))  # Can't add during iteration

        for cat, field_block in to_add:
            merged_blocks[cat] = field_block

        fbm = FieldBlockManager()
        fbm.__blocks = merged_blocks  # Yerk....

        return fbm

    def build(self, form: forms.BaseForm) -> FieldBlocksGroup:
        """You should not call this directly ; see CremeForm/CremeModelForm
        get_blocks() method.
        @param form: An instance of <django.forms.Form>.
        @return An instance of FieldBlocksGroup.
        """
        return FieldBlocksGroup(form, self.__blocks.items())


_FormCallback = Callable[[forms.Form], None]


# class HookableForm:
class HookableFormMixin:
    # Beware: use related method to manipulate
    _creme_post_clean_callbacks: Sequence[_FormCallback] = ()  # ==> add_post_clean_callback()
    _creme_post_init_callbacks: Sequence[_FormCallback]  = ()  # ==> add_post_init_callback()
    _creme_post_save_callbacks: Sequence[_FormCallback]  = ()  # ==> add_post_save_callback()

    @classmethod
    def __add_callback(cls, attrname: str, callback: _FormCallback) -> Type['HookableFormMixin']:
        setattr(cls, attrname, [*getattr(cls, attrname), callback])
        return cls

    @classmethod
    def add_post_clean_callback(cls, callback: _FormCallback) -> Type['HookableFormMixin']:
        return cls.__add_callback('_creme_post_clean_callbacks', callback)

    @classmethod
    def add_post_init_callback(cls, callback: _FormCallback) -> Type['HookableFormMixin']:
        return cls.__add_callback('_creme_post_init_callbacks', callback)

    @classmethod
    def add_post_save_callback(cls, callback: _FormCallback) -> Type['HookableFormMixin']:
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

    def as_span(self) -> str:  # TODO: in another base class
        """Returns this form rendered as HTML <span>s."""
        assert isinstance(self, forms.BaseForm), \
               f'HookableFormMixin has not been used as Form mixin: {type(self)}.'

        return self._html_output(
            normal_row='<span%(html_class_attr)s>%(label)s %(field)s%(help_text)s</span>',
            error_row='%s',
            row_ender='</span>',
            help_text_html=' <span class="helptext">%s</span>',
            errors_on_separate_row=False,
        )


# class CremeForm(forms.Form, HookableForm):
class CremeForm(HookableFormMixin, forms.Form):
    blocks = FieldBlockManager(('general', _('General information'), '*'))

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

    def get_blocks(self) -> FieldBlocksGroup:
        return self.blocks.build(self)

    def save(self, *args, **kwargs):
        self._creme_post_save()


# class CremeModelForm(forms.ModelForm, HookableForm):
class CremeModelForm(HookableFormMixin, forms.ModelForm):
    blocks = FieldBlockManager(('general', _('General information'), '*'))

    class Meta:
        fields: Union[str, Tuple[str, ...]] = '__all__'

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

        self.fields_configs = fc = FieldsConfig.LocalCache()
        fc.get_4_model(self.instance.__class__).update_form_fields(self.fields)

        self._creme_post_init()

    def clean(self, *args, **kwargs):
        res = super().clean()
        self._creme_post_clean()
        return res

    def get_blocks(self) -> FieldBlocksGroup:
        return self.blocks.build(self)

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        self._creme_post_save()
        return instance


# class CremeModelWithUserForm(CremeModelForm):
#     user = forms.ModelChoiceField(label=_('Owner user'), empty_label=None, queryset=None)
#
#     def __init__(self, user, *args, **kwargs):
#         warnings.warn('CremeModelWithUserForm is deprecated ; '
#                       'use CremeModelForm instead.',
#                       DeprecationWarning
#                      )
#
#         from django.contrib.auth import get_user_model
#
#         super().__init__(user=user, *args, **kwargs)
#         user_f = self.fields['user']
#         user_f.queryset = get_user_model().objects.filter(is_staff=False)
#         user_f.initial = user.id

class CustomFieldsMixin:
    @staticmethod
    def _build_customfield_name(cfield):
        return _CUSTOM_NAME.format(cfield.id)

    def _build_customfields(self, only_required=False) -> None:
        self._customs = self.instance.get_custom_fields_n_values(only_required=only_required)
        fields = self.fields
        user = self.user
        build_name = self._build_customfield_name

        for cfield, cvalue in self._customs:
            fields[build_name(cfield)] = cfield.get_formfield(cvalue, user=user)

    def _save_customfields(self) -> None:
        cfields_n_values = self._customs

        if cfields_n_values:
            cleaned_data = self.cleaned_data
            instance = self.instance
            build_name = self._build_customfield_name

            for cfield, cvalue in cfields_n_values:
                value = cleaned_data[build_name(cfield)]
                CustomFieldValue.save_values_for_entities(cfield, [instance], value)


# class CremeEntityForm(CremeModelForm):
class CremeEntityForm(CustomFieldsMixin, CremeModelForm):
    property_types = fields.EnhancedModelMultipleChoiceField(
        queryset=CremePropertyType.objects.none(),
        label=_('Properties'),
        required=False,
    )

    rtypes_info = forms.CharField(
        label=_('Information on relationships'),
        required=False,
        widget=widgets.Label,
    )
    relation_types = fields.MultiRelationEntityField(
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
        'missing_property_single': _('The property «%(property)s» is mandatory '
                                     'in order to use the relationship «%(predicate)s»'
                                    ),
        'missing_property_multi': _('These properties are mandatory in order to use '
                                    'the relationship «%(predicate)s»: %(properties)s'
                                   ),
        'subject_not_linkable': _('You are not allowed to link the created entity (wrong owner?).'),
    }

    blocks = CremeModelForm.blocks.new(
        ('description',   _('Description'),   ('description',)),
        ('properties',    _('Properties'),    ('property_types',)),
        ('relationships', _('Relationships'), ('rtypes_info', 'relation_types', 'semifixed_rtypes')),
    )

    class Meta:
        exclude: Tuple[str, ...] = ()
        fields = '__all__'

    forced_ptype_ids: List[str]
    forced_relations_info: List[Tuple[RelationType, CremeEntity]]
    _customs: List[Tuple[CustomField, Any]]

    def __init__(self,
                 forced_ptypes: Iterable[Union[CremePropertyType, str]] = (),
                 forced_relations: Iterable[Relation] = (),
                 *args, **kwargs):
        """Constructor.
        @param forced_ptypes: Sequence of CremePropertyType IDs/instances ;
               CremeProperties with these types will be added to the instance.
        @param forced_relations: Sequence of (unsaved) Relations instances ;
               These relations will be added to the instance. Notice that :
                - <instance> will be used as subject (ie: you do not have to
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

    # def _build_customfields(self):
    #     self._customs = self.instance.get_custom_fields_n_values()
    #     fields = self.fields
    #     user = self.user
    #
    #     for i, (cfield, cvalue) in enumerate(self._customs):
    #         fields[_CUSTOM_NAME.format(i)] = cfield.get_formfield(cvalue)

    def _build_properties_field(self, forced_ptype_ids: Iterable[str]) -> None:
        instance = self.instance

        if settings.FORMS_RELATION_FIELDS and not instance.pk:
            ptypes_f = self.fields['property_types']
            ptypes_f.queryset = CremePropertyType.objects.compatible(type(instance))
            ptypes_f.forced_values = forced_ptype_ids
        else:
            del self.fields['property_types']

    def _build_relations_fields(self, forced_relations_info: List[Tuple[RelationType, CremeEntity]]) -> None:
        fields = self.fields
        instance = self.instance
        info: Optional[str] = None

        if settings.FORMS_RELATION_FIELDS and not instance.pk:
            if forced_relations_info:
                if len(forced_relations_info) == 1:
                    rel = forced_relations_info[0]
                    info = _('This relationship will be added: {predicate} «{entity}»').format(
                        predicate=rel[0].predicate,
                        entity=rel[1],
                    )
                else:
                    # TODO: ngettext() ?
                    info = gettext('These relationships will be added: {}').format(
                        format_html(
                            '<ul>{}</ul>',  # TODO:  class="form-help-label" ??
                            format_html_join(
                                '', '<li>{} «{}»</li>',
                                ((rtype.predicate, entity) for rtype, entity in forced_relations_info))
                        )
                    )

            if self.user.has_perm_to_link(type(instance)):
                ctype = instance.entity_type
                fields['relation_types'].allowed_rtypes = \
                    RelationType.objects.compatible(ctype)

                # TODO: factorise ?
                entities = [
                    sfrt.object_entity
                    for sfrt in SemiFixedRelationType.objects
                                                     .select_related('object_entity')
                ]
                sfrt_qs = SemiFixedRelationType.objects.filter(
                    Q(relation_type__subject_ctypes=ctype) |
                    Q(relation_type__subject_ctypes__isnull=True),
                ).filter(
                    object_entity__in=filter(self.user.has_perm_to_link, entities),
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

    # TODO: factorise with _RelationsCreateForm ??
    def _check_properties(self, rtypes: Iterable[RelationType]) -> None:
        need_validation = False
        ptypes_contraints: Dict[str, Tuple[RelationType, Dict[str, str]]] = OrderedDict()

        for rtype in rtypes:
            if rtype.id not in ptypes_contraints:
                properties = dict(rtype.subject_properties.values_list('id', 'text'))
                ptypes_contraints[rtype.id] = (rtype, properties)

                if properties:
                    need_validation = True

        if need_validation:
            subject_prop_ids = {pt.id for pt in self.cleaned_data['property_types']}

            for rtype, needed_properties in ptypes_contraints.values():
                if any(
                    ptype_id not in subject_prop_ids for ptype_id in needed_properties.keys()
                ):
                    if len(needed_properties) == 1:
                        raise forms.ValidationError(
                            self.error_messages['missing_property_single'],
                            params={
                                'property':  next(iter(needed_properties.values())),
                                'predicate': rtype.predicate,
                            },
                            code='missing_property_single',
                        )
                    else:
                        raise forms.ValidationError(
                            self.error_messages['missing_property_multi'],
                            params={
                                'properties': ', '.join(
                                    sorted(map(str, needed_properties.values()))
                                ),
                                'predicate': rtype.predicate,
                            },
                            code='missing_property_multi',
                        )

    def _check_subject_linkable(self, rtypes: Collection[RelationType]) -> None:
        if rtypes and not self.user.has_perm_to_link(type(self.instance),
                                                     owner=self.cleaned_data['user'],
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

    # def _save_customfields(self):
    #     cfields_n_values = self._customs
    #
    #     if cfields_n_values:
    #         cleaned_data = self.cleaned_data
    #         instance = self.instance
    #
    #         for i, (custom_field, custom_value) in enumerate(cfields_n_values):
    #             value = cleaned_data[_CUSTOM_NAME.format(i)]
    #             CustomFieldValue.save_values_for_entities(custom_field, [instance], value)

    def _save_properties(self,
                         properties: Iterable[CremeProperty],
                         check_existing: bool = True) -> None:
        CremeProperty.objects.safe_multi_save(properties, check_existing=check_existing)

    def _save_relations(self,
                        relations: Iterable[Relation],
                        check_existing: bool = True) -> None:
        Relation.objects.safe_multi_save(relations, check_existing=check_existing)

    def save(self, *args, **kwargs):
        created = self.instance.pk is None  # TODO: attribute in CremeModelForm ?
        instance = super().save(*args, **kwargs)
        self._save_customfields()
        self._save_properties(properties=self._get_properties_to_create(),
                              check_existing=not created,
                             )
        self._save_relations(relations=self._get_relations_to_create(),
                             check_existing=not created,
                            )

        return instance


class CremeEntityQuickForm(CustomFieldsMixin, CremeModelForm):
    class Meta:
        fields: Union[str, Tuple[str, ...]] = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert isinstance(self.instance, CremeEntity)

        self._build_customfields(only_required=True)

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        self._save_customfields()

        return instance
