################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2021-2025  Hybird
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
from functools import partial
from typing import Iterable, Iterator, Sequence

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.core.validators import EMPTY_VALUES
from django.db import models
from django.db.models import Field
from django.template.loader import get_template
from django.utils.encoding import force_str
from django.utils.formats import date_format, number_format
from django.utils.hashable import make_hashable
from django.utils.html import escape, format_html, linebreaks
from django.utils.safestring import mark_safe
from django.utils.timezone import localtime
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy

from creme.creme_core.models import (
    CremeEntity,
    CremePropertyType,
    CustomField,
    CustomFieldEnumValue,
    HistoryLine,
    RelationType,
    history,
)
from creme.creme_core.templatetags.creme_widgets import widget_entity_hyperlink
from creme.creme_core.utils.collections import ClassKeyedMap
from creme.creme_core.utils.dates import date_from_ISO8601, dt_from_ISO8601
from creme.creme_core.utils.db import PreFetcher

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
class FieldChangeExplainer:
    """Render a string which explains a modification on a field stored in an
    history line (edition, related edition, auxiliary object's edition).

    The main method is 'render()' ; other methods are made to be overridden by
    child classes.
    """
    no_value_sentence = _('{field} set')
    new_value_sentence = _('{field} set to {value}')
    emptied_value_sentence = _('{field} emptied (it was {oldvalue})')
    two_values_sentence = _('{field} changed from {oldvalue} to {value}')

    field_decorator = _('“{field}”')
    old_value_decorator = new_value_decorator = _('“{value}”')

    def __init__(self, *,
                 field: Field | CustomField,
                 values: Sequence,
                 prefetcher: PreFetcher,
                 ):
        """Build a string explain a modification about an instance's field.
        @param field: The field the modification is about.
        @param values: Sequence representing changes (generally stored in HistoryLine).
               0 element => the field changed.
               1 element => the field received a new value.
               2 elements => (old value, new value) generally
                             (ManyToManyFields interprets (PKs removed, PK added).
        """
        self._field = field
        self._values = values
        self._prefetcher = prefetcher

    def decorate_field(self, field: Field | CustomField) -> str:
        return self.field_decorator.format(field=self.render_field(field=field))

    def decorate_new_value(self, value: str) -> str:
        return self.new_value_decorator.format(value=value)

    def decorate_old_value(self, value: str) -> str:
        return self.old_value_decorator.format(value=value)

    @staticmethod
    def is_empty_value(value) -> bool:
        return value in EMPTY_VALUES

    def render_choice(self, *, user, value):
        # NB: django way for '_get_FIELD_display()' methods
        #       => would a linear search be faster ?
        return force_str(
            dict(make_hashable(self._field.flatchoices)).get(make_hashable(value), value),
            strings_only=True,
        )

    def render_field(self, field: Field | CustomField) -> str:
        return field if isinstance(field, CustomField) else field.verbose_name

    def render_value(self, *, user, value) -> str:
        return str(value)

    def render(self, user) -> str:
        """Build a string explain a modification about an instance's field.
        @param user: Instance of auth.get_user_model() ; used for VIEW credentials.
        @return: a description string.
        """
        field = self._field
        values = self._values
        decorated_field = self.decorate_field(field)

        match len(values):
            case 0:
                sentence = self.no_value_sentence.format(field=decorated_field)
            case 1:
                render_value = (
                    self.render_choice
                    if isinstance(field, Field) and field.choices else
                    self.render_value
                )  # TODO: factorise
                sentence = self.new_value_sentence.format(
                    field=decorated_field,
                    value=self.decorate_new_value(
                        render_value(user=user, value=values[0])
                    ),
                )
            case _:  # length == 2
                render_value = (
                    self.render_choice
                    if isinstance(field, Field) and field.choices else
                    self.render_value
                )
                new_value = values[1]
                old_rendered_value = self.decorate_old_value(
                    render_value(user=user, value=values[0])
                )

                if self.is_empty_value(new_value):
                    sentence = self.emptied_value_sentence.format(
                        field=decorated_field,
                        oldvalue=old_rendered_value,
                    )
                else:
                    sentence = self.two_values_sentence.format(
                        field=decorated_field,
                        oldvalue=old_rendered_value,
                        value=self.decorate_new_value(
                            render_value(user=user, value=new_value)
                        ),
                    )

        return sentence


class HTMLFieldChangeExplainer(FieldChangeExplainer):
    """Specialization of FieldChangeExplainer which produce HTML descriptions.
    Used by the History brick for example.
    """
    field_decorator = '<span class="field-change-field_name">{field}</span>'
    old_value_decorator = '<span class="field-change-old_value">{value}</span>'
    new_value_decorator = '<span class="field-change-new_value">{value}</span>'

    def render(self, user):
        return mark_safe(super().render(user=user))

    def render_field(self, field: Field | CustomField) -> str:
        return (
            escape(field) if isinstance(field, CustomField) else field.verbose_name
        )

    def render_value(self, *, user, value) -> str:
        return escape(value)


class HTMLBooleanFieldChangeExplainer(HTMLFieldChangeExplainer):
    @staticmethod
    def is_empty_value(value):
        return False

    def render_value(self, *, user, value):
        return (
            gettext('Yes') if value else
            gettext('No') if value is False else
            gettext('N/A')
        )


class HTMLDateFieldChangeExplainer(HTMLFieldChangeExplainer):
    def render_value(self, *, user, value):
        return date_format(date_from_ISO8601(value), 'DATE_FORMAT')


class HTMLDateTimeFieldChangeExplainer(HTMLFieldChangeExplainer):
    def render_value(self, *, user, value):
        return date_format(localtime(dt_from_ISO8601(value)), 'DATETIME_FORMAT')


class HTMLNumberFieldChangeExplainer(HTMLFieldChangeExplainer):
    def render_value(self, *, user, value):
        return number_format(value, force_grouping=True)


class HTMLTextFieldChangeExplainer(HTMLFieldChangeExplainer):
    emptied_value_sentence = _('{field} emptied {details_link}')
    changed_value_sentence = _('{field} set {details_link}')

    def render(self, user):
        decorated_field = self.decorate_field(self._field)
        values = self._values
        length = len(values)

        if not length:  # NB: old HistoryLine
            sentence = self.no_value_sentence.format(field=decorated_field)
        else:
            if length == 1:
                old_value = ''
                new_value = values[0]
            else:  # length == 2
                old_value = values[0]
                new_value = values[1]

            sentence_format = (
                self.emptied_value_sentence
                if self.is_empty_value(new_value)
                else self.changed_value_sentence
            )
            sentence = sentence_format.format(
                field=decorated_field,
                details_link=format_html(
                    '<a class="field-change-text_details" data-action="popover">'
                    ' {label}'
                    ' <summary>{summary}</summary>'
                    ' <details>'
                    '  <div class="history-line-field-change-text-old_value">'
                    '   <h4>{old_title}</h4>{old}'
                    '  </div>'
                    '  <div class="history-line-field-change-text-new_value">'
                    '   <h4>{new_title}</h4>{new}'
                    '  </div>'
                    ' </details>'
                    '</a>',
                    label=gettext('(see details)'),
                    summary=gettext('Details of modifications'),

                    old_title=gettext('Old value'),
                    old=mark_safe(
                        linebreaks(old_value, autoescape=True)
                        if old_value else
                        '<p class="empty-field">—</p>'
                    ),

                    new_title=gettext('New value'),
                    new=mark_safe(
                        linebreaks(new_value, autoescape=True)
                        if new_value else
                        '<p class="empty-field">—</p>'
                    ),
                ),
            )

        return mark_safe(sentence)


class ForeignKeyExplainerMixin:
    deleted_value = _('{pk} (deleted)')

    def __init__(self, *,
                 field: Field | CustomField,
                 values,
                 prefetcher: PreFetcher,
                 ):
        self._model = model = (
            field.remote_field.model if isinstance(field, Field) else CustomFieldEnumValue
        )
        prefetcher.order(model=model, pks=values)

    def render_instance(self, instance, user):
        if isinstance(instance, CremeEntity):
            return instance.allowed_str(user)  # TODO: test

        return str(instance)

    def render_fk(self, *, user, value):
        instance = self._prefetcher.get(model=self._model, pk=value)

        return (
            self.deleted_value.format(pk=value)
            if instance is None else
            self.render_instance(instance=instance, user=user)
        )


class HTMLForeignKeyFieldChangeExplainer(ForeignKeyExplainerMixin,
                                         HTMLFieldChangeExplainer):
    def __init__(self, **kwargs):
        ForeignKeyExplainerMixin.__init__(self, **kwargs)
        HTMLFieldChangeExplainer.__init__(self, **kwargs)

    def render_instance(self, instance, user):
        if isinstance(instance, CremeEntity):
            return widget_entity_hyperlink(entity=instance, user=user)

        return escape(instance)

    def render_value(self, *, user, value):
        return self.render_fk(user=user, value=value)


# TODO: prefetcher.order(model=model, pks=values)
class ManyToManyFieldChangeExplainer(FieldChangeExplainer):
    sentence = _('{field} changed: {changes}')
    added_part   = ngettext_lazy('{} was added',   '[{}] were added')
    removed_part = ngettext_lazy('{} was removed', '[{}] were removed')

    added_value_decorator = removed_value_decorator = '{value}'

    def decorate_added_value(self, value: str) -> str:
        return self.added_value_decorator.format(value=value)

    def decorate_removed_value(self, value: str) -> str:
        return self.removed_value_decorator.format(value=value)

    # TODO: test
    def render_instance(self, instance, user):
        if isinstance(instance, CremeEntity):
            return instance.allowed_str(user)

        return str(instance)

    def render(self, user) -> str:
        # NB: [PKs removed, PKs added].
        values = self._values
        assert len(values) == 2

        field = self._field

        removed_pks = set(values[0])
        added_pks = set(values[1])

        # TODO: factorise
        # NB: not in_bulk() to preserve natural ordering
        linked_model = (
            field.remote_field.model if isinstance(field, Field) else CustomFieldEnumValue
        )
        linked_instances = linked_model._default_manager.filter(pk__in=removed_pks | added_pks)

        render = partial(self.render_instance, user=user)
        decorate_added = self.decorate_added_value
        decorate_removed = self.decorate_removed_value
        added_instances = [
            decorate_added(render(o))
            for o in linked_instances if o.pk in added_pks
        ]
        removed_instances = [
            decorate_removed(render(o))
            for o in linked_instances if o.pk in removed_pks
        ]

        # TODO: what about deleted instances ??
        # TODO: decorate_instances() for better enumerations ?
        changes = []
        if added_instances:
            changes.append(
                (self.added_part % len(added_instances)).format(
                    ', '.join(added_instances)
                )
            )
        if removed_instances:
            changes.append(
                (self.removed_part % len(removed_instances)).format(
                    ', '.join(removed_instances)
                )
            )

        return self.sentence.format(
            field=self.decorate_field(field),
            changes=', '.join(changes)
        )


class HTMLManyToManyFieldChangeExplainer(ManyToManyFieldChangeExplainer):
    field_decorator = '<span class="field-change-field_name">{field}</span>'
    added_part   = ngettext_lazy('{} was added',   '{} were added')
    removed_part = ngettext_lazy('{} was removed', '{} were removed')

    added_value_decorator   = '<span class="field-change-m2m_added">{value}</span>'
    removed_value_decorator = '<span class="field-change-m2m_removed">{value}</span>'

    def render(self, user):
        return mark_safe(super().render(user=user))

    def render_instance(self, instance, user):
        if isinstance(instance, CremeEntity):
            return widget_entity_hyperlink(entity=instance, user=user)

        return escape(instance)


# ------------------------------------------------------------------------------
class HistoryLineExplainer:
    """Render a string which explains a history line.
    Used by the history brick to render all the lines of the current page.

    The main method is 'render()' ; other methods are made to be overridden by
    child classes.
    """
    type_id: str = ''  # Used in CSS class for example
    template_name: str = 'OVERRIDE_ME'

    def __init__(self, *,
                 hline: HistoryLine,
                 user,
                 field_explainers: ClassKeyedMap,
                 prefetcher: PreFetcher,
                 ):
        self.hline = hline
        self.user = user
        self._field_explainers = field_explainers
        self._prefetcher = prefetcher

    def get_context(self) -> dict:
        """Builds the context of the template."""
        return {
            'type_id': self.type_id,
            'hline': self.hline,
            'user': self.user,
        }

    def _explainers_for_custom_fields(self,
                                      model_class: type[models.Model],
                                      modifications: list[tuple],
                                      ) -> Iterator[FieldChangeExplainer]:
        get_cfield = CustomField.objects.get_for_model(model_class).get

        field_explainers = self._field_explainers

        class InvalidCustomFieldChangeExplainer(FieldChangeExplainer):
            def __init__(this, cfield_id):
                this._cfield_id = cfield_id

            def render(this, user):
                return gettext(
                    'Deleted field (with id={id}) set'
                ).format(id=this._cfield_id)

        for modif in modifications:
            cfield_id = modif[0]
            cfield = get_cfield(cfield_id)

            if cfield is None:
                explainer = InvalidCustomFieldChangeExplainer(cfield_id=cfield_id)
            else:
                value_field = cfield.value_class._meta.get_field('value')
                explainer = field_explainers[type(value_field)](
                    field=cfield,
                    values=modif[1:],
                    prefetcher=self._prefetcher,
                )

            yield explainer

    def _explainers_for_fields(self,
                               model_class: type[models.Model],
                               modifications: list[tuple],
                               ) -> Iterator[FieldChangeExplainer]:
        get_field = model_class._meta.get_field
        field_explainers = self._field_explainers

        class InvalidFieldChangeExplainer(FieldChangeExplainer):
            def __init__(this, field_name):
                this._field_name = field_name

            def render(this, user):
                return gettext('“{field}” set').format(field=this._field_name)

        for modif in modifications:
            field_name = modif[0]
            try:
                field: Field = get_field(field_name)
            except FieldDoesNotExist:
                explainer = InvalidFieldChangeExplainer(field_name=field_name)
            else:
                explainer = field_explainers[type(field)](
                    field=field,
                    values=modif[1:],
                    prefetcher=self._prefetcher,
                )

            yield explainer

    @staticmethod
    def _render_field_explainers(field_explainers: Iterable[FieldChangeExplainer],
                                 user,
                                 ) -> Iterator[str]:
        for explainer in field_explainers:
            try:
                yield explainer.render(user)
            except Exception:
                logger.exception('Error when render history for field')
                yield '??'

    def render(self) -> str:
        return get_template(self.template_name).render(self.get_context())


class HTMLCreationExplainer(HistoryLineExplainer):
    type_id = 'creation'
    template_name = 'creme_core/history/html/creation.html'


class _EditionExplainer(HistoryLineExplainer):
    def __init__(self, *, hline, **kwargs):
        super().__init__(hline=hline, **kwargs)
        self._field_explainers = [
            *self._explainers_for_fields(
                model_class=hline.entity_ctype.model_class(),
                modifications=hline.modifications,
            ),
        ]

    def get_context(self):
        context = super().get_context()
        context['modifications'] = [
            *self._render_field_explainers(self._field_explainers, self.user),
        ]

        return context


class HTMLEditionExplainer(_EditionExplainer):
    type_id = 'edition'
    template_name = 'creme_core/history/html/edition.html'


class HTMLCustomEditionExplainer(HistoryLineExplainer):
    type_id = 'custom_edition'
    template_name = 'creme_core/history/html/custom-edition.html'

    def __init__(self, *, hline, **kwargs):
        super().__init__(hline=hline, **kwargs)
        self._field_explainers = [
            *self._explainers_for_custom_fields(
                model_class=hline.entity_ctype.model_class(),
                modifications=hline.modifications,
            ),
        ]

    def get_context(self):
        context = super().get_context()
        context['modifications'] = [
            *self._render_field_explainers(self._field_explainers, self.user),
        ]

        return context


class HTMLDeletionExplainer(HistoryLineExplainer):
    type_id = 'deletion'
    template_name = 'creme_core/history/html/deletion.html'


class HTMLRelatedEditionExplainer(HistoryLineExplainer):
    type_id = 'related_edition'
    template_name = 'creme_core/history/html/related-edition.html'

    def __init__(self, *, hline, **kwargs):
        super().__init__(hline=hline, **kwargs)
        related_line = self.hline.related_line
        self._field_explainers = [
            *self._explainers_for_fields(
                model_class=related_line.entity_ctype.model_class(),
                modifications=related_line.modifications,
            ),
        ]

    def get_context(self):
        context = super().get_context()

        # TODO: render related line in template ?
        context['modifications'] = [
            *self._render_field_explainers(self._field_explainers, self.user),
        ]

        return context


class _PropertyExplainer(HistoryLineExplainer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ptype_id = ptype_id = self.hline.modifications[0]
        self._prefetcher.order(CremePropertyType, [ptype_id])

    def get_context(self):
        context = super().get_context()

        ptype_id = self._ptype_id
        ptype = self._prefetcher.get(CremePropertyType, ptype_id)
        context['property_text'] = ptype_id if ptype is None else ptype.text

        return context


class HTMLPropertyAdditionExplainer(_PropertyExplainer):
    type_id = 'property_addition'
    template_name = 'creme_core/history/html/property-addition.html'


class HTMLPropertyDeletionExplainer(_PropertyExplainer):
    type_id = 'property_deletion'
    template_name = 'creme_core/history/html/property-deletion.html'


class _RelationExplainer(HistoryLineExplainer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rtype_id = rtype_id = self.hline.modifications[0]
        self._prefetcher.order(RelationType, [rtype_id])

    def get_context(self):
        context = super().get_context()

        rtype_id = self._rtype_id
        rtype = self._prefetcher.get(RelationType, rtype_id)
        context['predicate'] = rtype_id if rtype is None else rtype.predicate

        return context


class HTMLRelationAdditionExplainer(_RelationExplainer):
    type_id = 'relationship_addition'
    template_name = 'creme_core/history/html/relation-addition.html'


class HTMLRelationDeletionExplainer(_RelationExplainer):
    type_id = 'relationship_deletion'
    template_name = 'creme_core/history/html/relation-deletion.html'


class HTMLAuxCreationExplainer(HistoryLineExplainer):
    type_id = 'auxiliary_creation'
    template_name = 'creme_core/history/html/auxiliary-creation.html'

    def get_context(self):
        context = super().get_context()

        # TODO: use aux_id to display an up-to-date value ??
        ct_id, aux_id, str_obj = self.hline.modifications
        try:
            ctype = ContentType.objects.get_for_id(ct_id)
        except ContentType.DoesNotExist:
            ctype = None

        context['auxiliary_ctype'] = ctype
        context['auxiliary_value'] = str_obj

        return context


class _AuxiliaryEditionExplainer(HistoryLineExplainer):
    def __init__(self, *, hline, **kwargs):
        super().__init__(hline=hline, **kwargs)

        modifications = hline.modifications

        # TODO: use aux_id to display an up-to-date value ??
        ct_id, __aux_id, str_obj = modifications[0]
        try:
            ctype = ContentType.objects.get_for_id(ct_id)
        except ContentType.DoesNotExist:
            ctype = None

        self._aux_ctype = ctype
        self._aux_value = str_obj
        self._field_explainers = [
            *self._explainers_for_fields(
                model_class=ctype.model_class(),
                modifications=modifications[1:],
            ),
        ] if ctype else []

    def get_context(self):
        context = super().get_context()

        context['auxiliary_ctype'] = self._aux_ctype
        context['auxiliary_value'] = self._aux_value
        context['modifications'] = [
            *self._render_field_explainers(self._field_explainers, self.user),
        ]

        return context


class HTMLAuxiliaryEditionExplainer(_AuxiliaryEditionExplainer):
    type_id = 'auxiliary_edition'
    template_name = 'creme_core/history/html/auxiliary-edition.html'


class HTMLAuxDeletionExplainer(HistoryLineExplainer):
    type_id = 'auxiliary_deletion'
    template_name = 'creme_core/history/html/auxiliary-deletion.html'

    def get_context(self):
        context = super().get_context()

        ct_id, str_obj = self.hline.modifications

        try:
            ctype = ContentType.objects.get_for_id(ct_id)
        except ContentType.DoesNotExist:
            ctype = None

        context['auxiliary_ctype'] = ctype
        context['auxiliary_value'] = str_obj

        return context


class HTMLTrashExplainer(HistoryLineExplainer):
    type_id = 'trash'
    template_name = 'creme_core/history/html/trash.html'


class HTMLMassExportExplainer(HistoryLineExplainer):
    type_id = 'mass_export'
    template_name = 'creme_core/history/html/mass-export.html'


# ------------------------------------------------------------------------------
class HistoryRegistry:
    """Registry for HistoryLineExplainers & FieldChangeExplainers.
    Each registry should be dedicated to one format (e.g. HTML for the brick).
    """
    def __init__(self, default_field_explainer_class=FieldChangeExplainer):
        self._line_explainer_classes = {}
        self._field_explainer_classes = ClassKeyedMap(default=default_field_explainer_class)

    def register_line_explainer(self,
                                htype: int,
                                explainer_class: type[HistoryLineExplainer],
                                ) -> HistoryRegistry:
        self._line_explainer_classes[htype] = explainer_class

        return self

    # TODO: unit test
    def register_field_explainers(
        self,
        *explainer_classes: tuple[type[Field], type[FieldChangeExplainer]],
    ):
        existing_classes = self._field_explainer_classes
        for field_cls, explainer_cls in explainer_classes:
            existing_classes[field_cls] = explainer_cls

        return self

    def line_explainers(self,
                        hlines: Iterable[HistoryLine],
                        user,
                        ) -> list[HistoryLineExplainer]:
        """Get the explainers corresponding to a sequence of HistoryLines
        Notice that the order is kept (i.e. you can zip()).
        """
        class EmptyExplainer(HistoryLineExplainer):
            def render(this):
                return '??'

        get_cls = self._line_explainer_classes.get
        field_explainers = self._field_explainer_classes
        fetcher = PreFetcher()
        explainers = [
            get_cls(hline.type, EmptyExplainer)(
                hline=hline, user=user,
                field_explainers=field_explainers,
                prefetcher=fetcher,
            ) for hline in hlines
        ]

        fetcher.proceed()
        # TODO: populate real entities in 'fetcher'

        return explainers


html_history_registry = HistoryRegistry(
    default_field_explainer_class=HTMLFieldChangeExplainer,
).register_field_explainers(
    (models.BooleanField, HTMLBooleanFieldChangeExplainer),

    (models.ForeignKey, HTMLForeignKeyFieldChangeExplainer),

    (models.ManyToManyField, HTMLManyToManyFieldChangeExplainer),

    (models.DateField,     HTMLDateFieldChangeExplainer),
    (models.DateTimeField, HTMLDateTimeFieldChangeExplainer),

    (models.IntegerField, HTMLNumberFieldChangeExplainer),
    (models.DecimalField, HTMLNumberFieldChangeExplainer),
    (models.FloatField,   HTMLNumberFieldChangeExplainer),  # TODO: test

    (models.TextField, HTMLTextFieldChangeExplainer),
).register_line_explainer(
    htype=history.TYPE_CREATION,
    explainer_class=HTMLCreationExplainer,
).register_line_explainer(
    htype=history.TYPE_EDITION,
    explainer_class=HTMLEditionExplainer,
).register_line_explainer(
    htype=history.TYPE_CUSTOM_EDITION,
    explainer_class=HTMLCustomEditionExplainer,
).register_line_explainer(
    htype=history.TYPE_DELETION,
    explainer_class=HTMLDeletionExplainer,
).register_line_explainer(
    htype=history.TYPE_RELATED,
    explainer_class=HTMLRelatedEditionExplainer,
).register_line_explainer(
    htype=history.TYPE_PROP_ADD,
    explainer_class=HTMLPropertyAdditionExplainer,
).register_line_explainer(
    htype=history.TYPE_PROP_DEL,
    explainer_class=HTMLPropertyDeletionExplainer,
).register_line_explainer(
    htype=history.TYPE_RELATION,
    explainer_class=HTMLRelationAdditionExplainer,
).register_line_explainer(
    htype=history.TYPE_SYM_RELATION,
    explainer_class=HTMLRelationAdditionExplainer,
).register_line_explainer(
    htype=history.TYPE_RELATION_DEL,
    explainer_class=HTMLRelationDeletionExplainer,
).register_line_explainer(
    htype=history.TYPE_SYM_REL_DEL,
    explainer_class=HTMLRelationDeletionExplainer,
).register_line_explainer(
    htype=history.TYPE_AUX_CREATION,
    explainer_class=HTMLAuxCreationExplainer,
).register_line_explainer(
    htype=history.TYPE_AUX_EDITION,
    explainer_class=HTMLAuxiliaryEditionExplainer,
).register_line_explainer(
    htype=history.TYPE_AUX_DELETION,
    explainer_class=HTMLAuxDeletionExplainer,
).register_line_explainer(
    htype=history.TYPE_TRASH,
    explainer_class=HTMLTrashExplainer,
).register_line_explainer(
    htype=history.TYPE_EXPORT,
    explainer_class=HTMLMassExportExplainer,
)
