# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019-2021  Hybird
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

import decimal
import logging
import unicodedata
from collections import OrderedDict  # defaultdict
from functools import partial
from re import compile as compile_re
from typing import Type

from django.conf import settings
from django.db.models.query_utils import Q
from django.forms import Field, Widget
from django.utils.formats import get_format
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.core import enumerable
from creme.creme_core.forms.base import CremeForm
from creme.creme_core.models import Relation
from creme.creme_core.utils.date_range import CustomRange
from creme.creme_core.utils.dates import dt_from_str

logger = logging.getLogger(__name__)
NULL = 'NULL'


# Widgets ----------------------------------------------------------------------

class ListViewSearchWidget(Widget):
    """Base class for the list-view search-widget (displayed in the column
    headers of the list-views to operate "quick" search.
    """
    template_name = 'creme_core/listview/search-widgets/void.html'


class TextLVSWidget(ListViewSearchWidget):
    """Search-widget to enter a string."""
    # input_type = 'text'  # TODO ? (see 'django/forms/widgets/input.html')
    template_name = 'creme_core/listview/search-widgets/text.html'


class IntegerLVSWidget(TextLVSWidget):
    tooltip = _('''You can use these operators: <, <=, >, >=
Eg: < 100

You can combine several expressions with the separator «;»
Eg: > -100 ; <= 2000
''')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.attrs['title'] = self.tooltip


class PositiveIntegerLVSWidget(IntegerLVSWidget):
    tooltip = _('''You can use these operators: <, <=, >, >=
Eg: < 100

You can combine several expressions with the separator «;»
Eg: > 100 ; <= 2000
''')


class DecimalLVSWidget(IntegerLVSWidget):
    tooltip = _('''You can use these operators: <, <=, >, >=
Eg: < 100

You can combine several expressions with the separator «;»
Eg: > 10 ; <= 10.5
''')


class FloatLVSWidget(IntegerLVSWidget):
    tooltip = _('''You must use these operators: <, <=, >, >=
Eg: < 100

You can combine several expressions with the separator «;»
Eg: > 10 ; <= 10.5
''')


# TODO: inherit SelectLVSWidget ?
class BooleanLVSWidget(ListViewSearchWidget):
    """Search-widget to enter a boolean value."""
    template_name = 'creme_core/listview/search-widgets/boolean.html'

    def __init__(self, *, null=False, **kwargs):
        super().__init__(**kwargs)
        self.null = null

    def format_value(self, value):
        return '' if value is None else NULL if value == NULL else int(value)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        w_ctxt = context['widget']
        w_ctxt['null'] = self.null
        w_ctxt['NULL_FK'] = NULL

        return context

    def value_from_datadict(self, data, files, name):
        try:
            str_value = data[name]
        except KeyError:
            pass
        else:
            if str_value == '1':
                return True

            if str_value == '0':
                return False

            if str_value == NULL and self.null:
                return NULL


# TODO: extends ChoiceWidget ?
class SelectLVSWidget(ListViewSearchWidget):
    """Search-widget to enter a choice among valid choices."""
    template_name = 'creme_core/listview/search-widgets/select.html'

    def __init__(self, *, choices=(), **kwargs):
        super().__init__(**kwargs)
        self.choices = choices

    def _build_groups(self, choices, selected_value):
        # groups = defaultdict(list)  # TODO: when order is kept (py3.7) ?
        #
        # for choice in choices:
        #     value = str(choice['value'])
        #     groups[choice.get('group')].append(
        #         {'value': value,
        #          'text': choice['label'],
        #          'selected': selected_value == value,
        #         }
        #     )
        groups = OrderedDict()

        for choice in choices:
            value = str(choice['value'])
            group_name = choice.get('group')
            group_choices = groups.get(group_name)
            if group_choices is None:
                groups[group_name] = group_choices = []

            group_choices.append(
                # TODO: use "help" ? (need to display entirely our widget, not a regular <select>)
                {
                    'value': value,
                    'text': choice['label'],
                    'selected': selected_value == value,
                }
            )

        return [*groups.items()]

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)

        w_ctxt = context['widget']
        w_ctxt['choices'] = self._build_groups(
            choices=self.choices, selected_value=w_ctxt['value'],
        )
        w_ctxt['NULL_FK'] = NULL

        return context

    def value_from_datadict(self, data, files, name):
        return data.get(name)


# TODO: extends MultiWidget & remove/improve get_context() ?
class DateRangeLVSWidget(ListViewSearchWidget):
    """Search-widget to enter a couple of dates."""
    template_name = 'creme_core/listview/search-widgets/date-range.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name=name, value=value, attrs=attrs)

        w_ctxt = context['widget']
        w_ctxt['date_format'] = settings.DATE_FORMAT_JS.get(settings.DATE_FORMAT)
        w_ctxt['value_start'] = value[0]
        w_ctxt['value_end']   = value[1]

        id_ = w_ctxt['attrs'].pop('id', None)
        if id_:
            w_ctxt['id_start'] = f'{id_}-start'
            w_ctxt['id_end']   = f'{id_}-end'

        return context

    def value_from_datadict(self, data, files, name):
        get = data.get
        return [
            get(f'{name}-start', ''),
            get(f'{name}-end', ''),
        ]


# Fields -----------------------------------------------------------------------

class ListViewSearchField(Field):
    """Base class for the list-view search-field.
     These fields return Q instances used to filter the entities displayed by a list-view.

    This a specialization of <django.forms.Field> with the following differences:
     - the widget class generally inherits <ListViewSearch>.
     - the method "to_python()" returns an instance of <django.db.models.query_utils.Q>.
    """
    widget: Type[ListViewSearchWidget] = ListViewSearchWidget

    def __init__(self, *, cell, user, **kwargs):
        super().__init__(**kwargs)
        self.cell = cell
        self.user = user

    def to_python(self, value):
        return Q()


class BaseIntegerField(ListViewSearchField):
    """ Base class for list-view search-fields which filter with 'operations'.
    Here 'operation' means a string containing an operator and a value.

    Eg: "< 12"
    """
    widget = IntegerLVSWidget

    OPERATIONS_SEPARATOR = ';'  # Separates operations. Eg: >100 ; <= 200
    OPERATION_RE = compile_re(r'^(.*?)(\-?[0-9]+)$')  # Regex for one operation.
    # Available operators
    #  Key: operation string in the user input.
    #  Value: filter to use in the QuerySet.
    OPERATORS = {
        '':   'exact',
        '=':  'exact',
        '>':  'gt',
        '>=': 'gte',
        '<':  'lt',
        '<=': 'lte',
    }

    def _get_q_for_operations(self, operations):
        """Return a Q from operations.

        @param operations: List of tuples (queryset-filter, number-value)
        @return: <django.db.models.query_utils.Q> instance.
        """
        raise NotImplementedError

    def _str_to_number(self, number_str):
        """Convert a string number, found in the user input, to a real number.
        Default implementation returns an integer.

        @param number_str: String.
        @return: A number, or None if the conversion is not possible.
        """
        try:
            return int(number_str)
        except ValueError:
            return None

    def to_python(self, value):
        if value:
            expressions = []

            for part in value.replace(' ', '').split(self.OPERATIONS_SEPARATOR):
                match = self.OPERATION_RE.search(part)

                if match:
                    op_str, number_str = match.groups()
                    query_op = self.OPERATORS.get(op_str)

                    if query_op:
                        number = self._str_to_number(number_str)

                        if number is not None:
                            expressions.append((query_op, number))

            if expressions:
                return self._get_q_for_operations(expressions)

        return super().to_python(value)


class BaseDecimalField(BaseIntegerField):
    widget = DecimalLVSWidget

    # NB: we assume that decimal separator is "." or ",".
    #     Another design would be better for other separator
    #     (without colliding with operators), but it should be OK in many cases...
    OPERATION_RE = compile_re(r'^(.*?)(\-?[0-9]*[\.,]?[0-9]*)$')

    # NB: copy of <django.utils.formats.sanitize_separators()> which forces <use_l10n=True>
    # TODO: remove when 'settings.USE_L10N = True' is set by default
    @staticmethod
    def _sanitize_separators(value):
        # if isinstance(value, str):
        parts = []
        decimal_separator = get_format(
            'DECIMAL_SEPARATOR',
            use_l10n=True,  # <=========
        )
        if decimal_separator in value:
            value, decimals = value.split(decimal_separator, 1)
            parts.append(decimals)

        if settings.USE_THOUSAND_SEPARATOR:
            thousand_sep = get_format('THOUSAND_SEPARATOR')
            if thousand_sep == '.' and value.count('.') == 1 and len(value.split('.')[-1]) != 3:
                pass
            else:
                for replacement in {
                    thousand_sep,
                    unicodedata.normalize('NFKD', thousand_sep)
                }:
                    value = value.replace(replacement, '')
        parts.append(value)

        return '.'.join(reversed(parts))

    def _str_to_number(self, number_str):
        sanitized_number_str = self._sanitize_separators(number_str)

        try:
            number = decimal.Decimal(sanitized_number_str)
        except decimal.InvalidOperation:
            number = None

        return number


class BaseChoiceField(ListViewSearchField):
    widget = SelectLVSWidget

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.choices = self.widget.choices = self._build_choices()

    def _build_choices(self, null_label=None):
        choices = [
            {'value': '', 'label': pgettext_lazy('creme_core-filter', 'All')},
        ]

        if null_label is not None:
            choices.append({'value': NULL, 'label': null_label})

        return choices

    def _get_q_for_choice(self, choice_value):
        raise NotImplementedError

    def _get_q_for_null_choice(self):
        raise NotImplementedError

    def to_python(self, value):
        if value:
            for choice in self.choices:
                choice_value = choice['value']

                if value == str(choice_value):
                    return (
                        self._get_q_for_null_choice() if choice_value == NULL else
                        self._get_q_for_choice(choice_value)
                    )

            # TODO: raise error instead ?
            logger.warning('BaseChoiceField: invalid choice: %s', value)

        return super().to_python(value=value)


# For regular model-fields
# ------------------------

class RegularCharField(ListViewSearchField):
    widget = TextLVSWidget

    def to_python(self, value):
        return Q(**{f'{self.cell.value}__icontains': value}) if value else Q()


class RegularBooleanField(ListViewSearchField):
    widget = BooleanLVSWidget

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.null = self.widget.null = self.cell.field_info[-1].null

    def to_python(self, value):
        if value is None:
            return Q()

        if value == NULL:
            if not self.null:
                # TODO: error ?!
                return Q()

            final_value = None
        else:
            final_value = value

        return Q(**{self.cell.value: final_value})


class RegularOperationsFieldMixin:
    def _build_q_from_operations(self, operations):
        return Q(**{
            f'{self.cell.value}__{op}': number
            for op, number in operations
        })


class RegularIntegerField(RegularOperationsFieldMixin, BaseIntegerField):
    def _get_q_for_operations(self, operations):
        return self._build_q_from_operations(operations)


class RegularPositiveIntegerField(RegularIntegerField):
    widget = PositiveIntegerLVSWidget
    OPERATION_RE = compile_re(r'^(.*?)([0-9]+)$')


class RegularDecimalField(RegularOperationsFieldMixin, BaseDecimalField):
    def _get_q_for_operations(self, operations):
        return self._build_q_from_operations(operations)


class RegularFloatField(RegularDecimalField):
    widget = FloatLVSWidget

    # No equal operator on float because of round problem
    # (you should probably only use DecimalField any way...)
    OPERATORS = {
        '>':  'gt',
        '>=': 'gte',
        '<':  'lt',
        '<=': 'lte',
    }


class RegularChoiceField(BaseChoiceField):
    def _build_choices(self, null_label=_('* is empty *')):
        field = self.cell.field_info[-1]
        choices = super()._build_choices(null_label=null_label if field.null else None)

        choices.extend(
            enumerable.Enumerator.convert_choices(field.get_choices(include_blank=False))
        )

        return choices

    def _get_q_for_choice(self, choice_value):
        return Q(**{self.cell.value: choice_value})

    def _get_q_for_null_choice(self):
        return Q(**{f'{self.cell.value}__isnull': True})


class RegularDateField(ListViewSearchField):
    widget = DateRangeLVSWidget

    # TODO: remove/rework (leave errors)
    def _get_date(self, date_str):
        if date_str:
            try:
                return dt_from_str(date_str).date()
            except AttributeError:
                logger.warning('RegularDateField => invalid date: %s', date_str)

    # TODO: datetime validation
    def to_python(self, value):
        start_str, end_str = value

        if start_str or end_str:
            get_date = self._get_date
            start = get_date(start_str)
            end = get_date(end_str)

            if start or end:
                return Q(**CustomRange(start=start, end=end).get_q_dict(self.cell.value, now()))

        return super().to_python(value=value)


class RegularRelatedField(ListViewSearchField):
    widget = SelectLVSWidget
    enumerable_registry = enumerable.enumerable_registry
    default_null_label = _('* is empty *')

    def __init__(self, enumerable_registry=None, **kwargs):
        super().__init__(**kwargs)

        if enumerable_registry is None:
            enumerable_registry = self.enumerable_registry

        self.choices = self.widget.choices = choices = [
            {'value': '', 'label': pgettext_lazy('creme_core-filter', 'All')},
        ]

        field = self.cell.field_info[-1]
        if field.null or field.many_to_many:
            choices.append({
                'value': NULL,
                'label': self._get_field_null_label(field),
            })

        try:
            enumerator = enumerable_registry.enumerator_by_field(field)
        except ValueError as e:
            logger.warning('RegularRelatedField => %s', e)
        else:
            choices.extend(enumerator.choices(user=self.user))

    def _get_field_null_label(self, field):
        try:
            null_label = field.get_null_label()
        except AttributeError:
            null_label = ''

        return f'* {null_label} *' if null_label else self.default_null_label

    def to_python(self, value):
        if value:
            for choice in self.choices:
                pk = choice['value']

                if value == str(pk):
                    return (
                        Q(**{f'{self.cell.value}__isnull': True})
                        if value == NULL else
                        Q(**{self.cell.value: pk})
                    )

            logger.warning('ForeignKeyField => invalid ID: %s', value)

        return super().to_python(value=value)


class EntityRelatedField(ListViewSearchField):
    widget = TextLVSWidget  # TODO: widget to get NULL ForeignKeys too

    def to_python(self, value):
        return (
            Q(**{f'{self.cell.value}__header_filter_search_field__icontains': value})
            if value else
            super().to_python(value=value)
        )


# For custom fields
# -----------------

class CustomCharField(ListViewSearchField):
    widget = TextLVSWidget

    def to_python(self, value):
        if value:
            cfield = self.cell.custom_field

            # TODO: optimized version if only one CustomField
            #       related_name = cfield.value_class.get_related_name()
            #       return Q(**{'{}__value__icontains'.format(related_name): value,
            #                   '{}__custom_field'.format(related_name): cfield.id,
            #                  }
            #               )
            return Q(
                pk__in=cfield.value_class
                             .objects
                             .filter(custom_field=cfield, value__icontains=value)
                             .values_list('entity_id', flat=True)
            )

        return super().to_python(value=value)


class CustomOperationsFieldMixin:
    def _build_q_from_operations(self, operations):
        cfield = self.cell.custom_field

        return Q(
            pk__in=cfield.value_class.objects.filter(
                custom_field=cfield,
                **{f'value__{op}': number for op, number in operations}
            ).values_list('entity_id', flat=True)
        )


class CustomIntegerField(CustomOperationsFieldMixin, BaseIntegerField):
    def _get_q_for_operations(self, operations):
        return self._build_q_from_operations(operations)


class CustomDecimalField(CustomOperationsFieldMixin, BaseDecimalField):
    def _get_q_for_operations(self, operations):
        return self._build_q_from_operations(operations)


# TODO: factorise
class CustomBooleanField(ListViewSearchField):
    widget = BooleanLVSWidget

    def to_python(self, value):
        if value is not None:
            cfield = self.cell.custom_field

            # TODO: optimized version if only one CustomField
            #       related_name = cfield.value_class.get_related_name()
            #       return Q(**{'{}__value'.format(related_name): value,
            #                   '{}__custom_field'.format(related_name): cfield.id,
            #                  }
            #               )
            return Q(
                pk__in=cfield.value_class
                             .objects
                             .filter(custom_field=cfield, value=value)
                             .values_list('entity_id', flat=True)
            )

        return super().to_python(value=value)


# TODO: factorise ?
class CustomDatetimeField(ListViewSearchField):
    widget = DateRangeLVSWidget

    # TODO: factorise
    # TODO: remove/rework (leave errors)
    def _get_date(self, date_str):
        if date_str:
            try:
                return dt_from_str(date_str).date()
            except AttributeError:
                logger.warning('CustomDatetimeField => invalid date: %s', date_str)

    # TODO: datetime validation
    def to_python(self, value):
        start_str, end_str = value

        if start_str or end_str:
            get_date = self._get_date
            start = get_date(start_str)
            end = get_date(end_str)

            if start or end:
                cfield = self.cell.custom_field

                return Q(
                    pk__in=cfield.value_class.objects.filter(
                        custom_field=cfield,
                        **CustomRange(start=start, end=end).get_q_dict('value', now()),
                    ).values_list('entity_id', flat=True)
                )

        return super().to_python(value=value)


class CustomChoiceField(BaseChoiceField):
    def _build_choices(self, null_label=_('* is empty *')):
        choices = super()._build_choices(null_label=null_label)
        choices.extend(
            {'value': cfid, 'label': cfvalue}
            for cfid, cfvalue in self.cell.custom_field
                                          .customfieldenumvalue_set
                                          .values_list('id', 'value')
        )

        return choices

    def _get_q_for_choice(self, choice_value):
        cfield = self.cell.custom_field

        # TODO: optimized version if only one CustomField
        #       related_name = cfield.value_class.get_related_name()
        #       Q(**{'{}__value'.format(related_name): value,
        #            '{}__custom_field'.format(related_name): cfield.id,
        #           }
        #        )
        return Q(
            pk__in=cfield.value_class
                         .objects
                         .filter(custom_field=cfield, value=choice_value)
                         .values_list('entity_id', flat=True),
        )

    def _get_q_for_null_choice(self):
        cfield = self.cell.custom_field

        # TODO: optimized version if only one CustomField
        #       related_name = cfield.value_class.get_related_name()
        #       Q(**{'{}__isnull'.format(related_name): True})
        return ~Q(
            pk__in=cfield.value_class
                         .objects
                         .filter(custom_field=cfield)
                         .values_list('entity_id', flat=True)
        )


# For Relations
# -------------

class RelationField(ListViewSearchField):
    widget = TextLVSWidget

    def to_python(self, value):
        if value:
            # TODO: optimized version if only one Relation
            #       Q(relations__type=self.cell.relation_type,
            #         relations__object_entity__header_filter_search_field__icontains=value,
            #        )
            return Q(
                pk__in=Relation.objects.filter(
                    type=self.cell.relation_type,
                    object_entity__header_filter_search_field__icontains=value,
                ).values_list('subject_entity', flat=True),
            )

        return super().to_python(value=value)


# Form -------------------------------------------------------------------------

class ListViewSearchForm(CremeForm):
    """Class for forms using ListViewSearchFields for fields & returning a global
     Q instance from them.
    """
    prefix = 'search'

    def __init__(self, *, field_registry, cells, **kwargs):
        """Constructor.

        It generates automatically the fields from a search-field registry &
        a sequence of EntityCells (generally these sequence corresponds to
        a HeaderFilter).

        @param field_registry: Instance of
               <creme_core.gui.listview.search.AbstractListViewSearchFieldRegistry>.
        @param cells: Sequence of <creme_core.core.entity_cell.EntityCell>.
        """
        super().__init__(**kwargs)
        # self._registry = field_registry TODO ?
        self._cells = cells

        fields = self.fields
        get_field = partial(field_registry.get_field, user=self.user, required=False)
        for cell in cells:
            fields[cell.key] = get_field(cell=cell)

    @cached_property
    def filtered_data(self):
        """Get a dictionary containing only the items from the data given in the
        constructor (ie GET/POST data) which are used by the search-fields.

        @return: A dictionary.
        """
        base_prefix = self.prefix
        prefix = f'{base_prefix}-' if base_prefix else ''

        # NB: we could filter in a better way, but it's probably not a real issue
        #     that users can store crappy data in their session...
        # IDEA: a "spying" dictionary with monitors which keys have been accessed.
        return {
            k: v
            for k, v in self.data.items()
            if k.startswith(prefix)
        }

    @cached_property
    def search_q(self):
        """Total search corresponding to all searches done in the fields.

        @return: An instance of <django.db.models.query_utils.Q>.
        """
        q = Q()
        cdata = self.cleaned_data

        for cell in self._cells:
            try:
                q &= cdata[cell.key]
            except KeyError:
                pass

        return q
