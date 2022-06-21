# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

import copy
import logging
import warnings
from datetime import date
from functools import partial
from types import GeneratorType
from typing import Optional

# from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models.query_utils import Q
from django.forms import widgets
from django.urls import reverse
from django.utils.formats import get_format
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy, pgettext, pgettext_lazy

from ..utils.date_range import date_range_registry
from ..utils.queries import QSerializer
from ..utils.url import TemplateURLBuilder

logger = logging.getLogger(__name__)


class WidgetAction:
    def __init__(self, *, name, label, icon=None, enabled=True, **attrs):
        self.name = name
        self.label = label
        self.icon = icon
        self.enabled = enabled
        self.attrs = attrs

    def __eq__(self, other):
        return (
            self.name == other.name
            and self.label == other.label
            and self.icon == other.icon
            and self.enabled == other.enabled
            and self.attrs == other.attrs
        )

    def __repr__(self):
        return (
            f'WidgetAction('
            f'name={self.name!r}, '
            f'label={self.label!r}, '
            f'icon={self.icon!r}, '
            f'enabled={self.enabled}, '
            f'attrs={self.attrs}'
            f')'
        )

    @property
    def enabled(self):
        enabled = self._enabled
        return enabled() if callable(enabled) else (enabled is True)

    @enabled.setter
    def enabled(self, enabled):
        self._enabled = enabled

    @property
    def context(self):
        attrs = {**self.attrs}
        label = self.label

        if not self.enabled:
            attrs['disabled'] = True

        title = attrs.pop('title', label)

        return {
            'name': self.name,
            'label': label,
            'icon': self.icon,
            'attrs': attrs,
            'title': title,
        }


class DatePickerMixin:
    @classmethod
    def get_date_format(cls):
        return get_format('DATE_INPUT_FORMATS')[0]

    # TODO: memoize?
    @classmethod
    def js_date_format(cls, py_date_format=None):
        if py_date_format is None:
            py_date_format = cls.get_date_format()

        return (
            py_date_format.replace('%Y', 'yy')
                          .replace('%y', 'y')
                          .replace('%m', 'mm')
                          .replace('%b', 'M')
                          .replace('%B', 'MM')
                          .replace('%d', 'dd')
        )


# TODO: to be improved....
class DynamicInput(widgets.TextInput):
    def __init__(self, type='text', attrs=None):
        super().__init__(attrs)
        self.input_type = type

    # TODO: factorise ?
    def get_context(self, name, value, attrs):
        widget_type = 'ui-creme-dinput'
        context = super().get_context(name=name, value=value, attrs=attrs)

        final_attrs = context['widget']['attrs']
        base_css = (
            'ui-creme-input ui-creme-widget widget-auto'
            if final_attrs.pop('auto', True) else
            'ui-creme-input ui-creme-widget'
        )
        final_attrs['class'] = (
            f"{base_css} {widget_type} {final_attrs.get('class', '')}"
        ).strip()
        final_attrs['widget'] = widget_type  # TODO: 'data-[creme-]widget'

        return context


# TODO ??? DynamicHiddenInput
# class HiddenInput(Input): #from django
#     input_type = 'hidden'
#     is_hidden = True


class EnhancedSelectOptions:
    option_template_name = 'creme_core/forms/widgets/enhanced-option.html'

    class Choice:
        def __init__(self, value, disabled=False, help='', readonly=False):
            self.value = value
            self.disabled = disabled
            self.readonly = readonly
            self.help = help

        def __str__(self):
            return str(self.value)

    def _set_options(self, options):
        if options is None:
            self.options = ()
        elif isinstance(options, GeneratorType):
            self.options = [*options]
        else:
            self.options = options

    def _get_options(self):
        return [*self.options()] if callable(self.options) else self.options

    @property
    def choices(self):
        return self._get_options()

    @choices.setter
    def choices(self, choices):
        self._set_options(choices)


class DynamicSelect(EnhancedSelectOptions, widgets.Select):
    template_name = 'creme_core/forms/widgets/dyn-select.html'

    def __init__(self, attrs=None, options=None, url='', label=None):
        super().__init__(attrs, ())  # TODO: options or ()
        self.url = url
        self.label = label
        self.from_python = None
        self.choices = options

    def get_context(self, name, value, attrs):
        widget_type = 'ui-creme-dselect'

        # value = self.from_python(value) if self.from_python is not None else value # TODO ?

        context = super().get_context(name=name, value=value, attrs=attrs)
        widget_cxt = context['widget']
        widget_cxt['label'] = self.label

        final_attrs = widget_cxt['attrs']
        base_css = (
            'ui-creme-input ui-creme-widget widget-auto'
            if final_attrs.pop('auto', True) else
            'ui-creme-input ui-creme-widget'
        )
        final_attrs['class'] = (
            f"{base_css} {widget_type} {final_attrs.get('class', '')}"
        ).strip()
        final_attrs['widget'] = widget_type  # TODO: 'data-[creme-]widget'
        final_attrs['url'] = self.url  # TODO 'data-url' + only if value is set?

        return context


class DynamicSelectMultiple(EnhancedSelectOptions, widgets.SelectMultiple):
    template_name = 'creme_core/forms/widgets/dyn-select.html'

    def __init__(self, attrs=None, options=None, url='', label=None):
        super().__init__(attrs=attrs, choices=())  # TODO: options or ()
        self.url = url
        self.label = label
        self.from_python = None
        self.choices = options

    def get_context(self, name, value, attrs):
        widget_type = 'ui-creme-dselect'

        # value = self.from_python(value) if self.from_python is not None else value  # TODO ?

        context = super().get_context(name=name, value=value, attrs=attrs)
        widget_cxt = context['widget']
        widget_cxt['label'] = self.label

        final_attrs = widget_cxt['attrs']
        base_css = (
            'ui-creme-input ui-creme-widget widget-auto'
            if final_attrs.pop('auto', True) else
            'ui-creme-input ui-creme-widget'
        )
        final_attrs['class'] = (
            f"{base_css} {widget_type} {final_attrs.get('class', '')}"
        ).strip()
        final_attrs['widget'] = widget_type  # TODO: 'data-[creme-]widget'
        final_attrs['url'] = self.url  # TODO 'data-url' + only if value is set?

        return context


class ActionButtonList(widgets.Widget):
    template_name = 'creme_core/forms/widgets/action-button-list.html'

    action_class = WidgetAction

    def __init__(self, delegate, attrs=None, actions=()):
        super().__init__(attrs)
        self.delegate = delegate
        self.actions = [*actions]
        self.from_python = None

    def __deepcopy__(self, memo):
        obj = super().__deepcopy__(memo)
        obj.actions = copy.deepcopy(self.actions)
        return obj

    def add_action(self, name, label, enabled=True, icon: Optional[str] = None, **attrs):
        self.actions.append(self.action_class(
            name=name, label=label, icon=icon,
            enabled=enabled,
            **attrs,
        ))
        return self

    def clear_actions(self):
        self.actions.clear()
        return self

    def get_context(self, name, value, attrs):
        widget_type = 'ui-creme-actionbuttonlist'

        value = self.from_python(value) if self.from_python is not None else value

        # TODO: what about attrs passed twice + cannot customise "class" of the wrapping <ul>?
        context = super().get_context(name=name, value=value, attrs=attrs)
        widget_cxt = context['widget']
        widget_cxt['class'] = 'ui-creme-widget widget-auto ' + widget_type
        widget_cxt['widget_type'] = widget_type

        widget_cxt['buttons'] = [action.context for action in self.actions]
        widget_cxt['delegate'] = self.delegate.get_context(
            name=name, value=value, attrs=attrs,
        )['widget']

        return context


class PolymorphicInput(widgets.TextInput):
    template_name = 'creme_core/forms/widgets/polymorphic-input.html'

    def __init__(self, attrs=None, key='', *args):
        super().__init__(attrs)
        self.key = key
        self.inputs = []
        self.default_input = None
        self.set_inputs(*args)
        self.from_python = None  # TODO: remove this hack ?

    def set_inputs(self, *args):
        for input in args:
            self.add_input(input.name, input.widget, input.attrs, **input.kwargs)

    def add_dselect(self, name, options=None, attrs=None, **kwargs):
        if isinstance(options, str):
            self.add_input(name, widget=DynamicSelect, attrs=attrs, url=options, **kwargs)
        else:
            self.add_input(name, widget=DynamicSelect, attrs=attrs, options=options, **kwargs)

    def add_input(self, name, widget, attrs=None, **kwargs):
        self.inputs.append(
            (
                name,
                widget(attrs=attrs, **kwargs) if isinstance(widget, type) else widget
            )
        )

    def set_default_input(self, widget, attrs=None, **kwargs):
        self.default_input = widget(attrs=attrs, **kwargs) if isinstance(widget, type) else widget

    def get_context(self, name, value, attrs):
        widget_type = 'ui-creme-polymorphicselect'

        # value = self.from_python(value) if self.from_python is not None else value # TODO ?
        context = super().get_context(name='', value='', attrs=attrs)
        widget_cxt = context['widget']
        widget_cxt['key'] = self.key

        final_attrs = widget_cxt.pop('attrs')
        base_css = (
            'ui-creme-widget widget-auto'
            if final_attrs.pop('auto', True) else
            'ui-creme-widget'
        )
        widget_cxt['class'] = (
            f"{base_css} {widget_type} {final_attrs.get('class', '')}"
        ).strip()
        widget_cxt['widget_type'] = widget_type

        final_attrs['class'] = 'ui-creme-input ' + widget_type

        widget_cxt['input'] = widgets.HiddenInput().get_context(
            name=name, value=value, attrs=final_attrs,
        )['widget']

        widget_cxt['selectors'] = selectors = [
            (w_name, w_input.get_context(name='', value='', attrs=None)['widget'])
            for w_name, w_input in self.inputs
        ]
        if self.default_input:
            selectors.append(
                ('*', self.default_input.get_context(name='', value='', attrs=None)['widget'])
            )

        return context


# class DateRangeSelect(widgets.Widget):
class DateRangeSelect(DatePickerMixin, widgets.Widget):
    template_name = 'creme_core/forms/widgets/date-range-select.html'
    range_registry = date_range_registry

    def __init__(self, attrs=None, choices=None):
        super().__init__(attrs)
        self.choices = choices

    def range_choices(self):
        return [
            ('', pgettext_lazy('creme_core-date_range', 'Customized')),
            # *date_range_registry.choices(),
            *self.range_registry.choices(),
        ]

    def get_context(self, name, value, attrs):
        widget_type = 'ui-creme-daterange-selector'

        context = super().get_context(name=name, value=value, attrs=attrs)
        widget_cxt = context['widget']

        final_attrs = widget_cxt['attrs']
        base_css = (
            'ui-creme-widget widget-auto'
            if final_attrs.pop('auto', True) else
            'ui-creme-widget'
        )
        widget_cxt['class'] = (
            f"{base_css} {widget_type} {final_attrs.get('class', '')}"
        ).strip()
        widget_cxt['widget_type'] = widget_type
        final_attrs['class'] = 'ui-creme-input ' + widget_type

        widget_cxt['type'] = 'hidden'
        # widget_cxt['date_format'] = settings.DATE_FORMAT_JS.get(settings.DATE_FORMAT)
        widget_cxt['date_format'] = self.js_date_format()
        widget_cxt['choices'] = self.range_choices() if self.choices is None else self.choices

        return context


class NullableDateRangeSelect(DateRangeSelect):
    def range_choices(self):
        choices = [('', pgettext_lazy('creme_core-date_range', 'Customized'))]
        choices.extend(date_range_registry.choices(exclude_empty=False))
        return choices


class ChainedInput(widgets.TextInput):
    template_name = 'creme_core/forms/widgets/chained-inputs.html'

    HORIZONTAL = 'hbox'
    VERTICAL = 'vbox'

    def __init__(self, attrs=None, *args):
        super().__init__(attrs)
        self.inputs = []
        self.set_inputs(*args)
        self.from_python = None  # TODO: remove this hack ?

    def __deepcopy__(self, memo):
        obj = super().__deepcopy__(memo)
        obj.inputs = copy.deepcopy(self.inputs)
        return obj

    def set_inputs(self, *inputs):
        for input in inputs:
            self.add_input(input.name, input.widget, input.attrs, **input.kwargs)

    def add_dselect(self, name, options=None, attrs=None, **kwargs):
        if isinstance(options, str):
            self.add_input(name, widget=DynamicSelect, attrs=attrs, url=options, **kwargs)
        else:
            self.add_input(name, widget=DynamicSelect, attrs=attrs, options=options, **kwargs)

    def add_input(self, name, widget, attrs=None, **kwargs):
        self.inputs.append(
            (
                name,
                widget(attrs=attrs or {}, **kwargs) if callable(widget) else widget
            )
        )

    # TODO ?
    # def clear(self):
    #     self.inputs[:] = ()

    def get_context(self, name, value, attrs):
        widget_type = 'ui-creme-chainedselect'

        value = self.from_python(value) if self.from_python is not None else value
        context = super().get_context(name='', value='', attrs=attrs)
        widget_cxt = context['widget']
        final_attrs = widget_cxt.pop('attrs')

        base_css = (
            'ui-creme-widget widget-auto '
            if final_attrs.pop('auto', True) else
            'ui-creme-widget '
        )
        widget_cxt['class'] = (
            f"{base_css} {widget_type} {final_attrs.get('class', '')}"
        ).strip()
        widget_cxt['widget_type'] = widget_type

        widget_cxt['direction'] = final_attrs.pop('direction', ChainedInput.HORIZONTAL)
        widget_cxt['reset'] = final_attrs.pop('reset', True)

        final_attrs['class'] = 'ui-creme-input ' + widget_type
        widget_cxt['input'] = widgets.HiddenInput().get_context(
            name=name, value=value, attrs=final_attrs,
        )['widget']

        widget_cxt['chained'] = [
            (w_name, w_input.get_context(name='', value='', attrs=None)['widget'])
            for w_name, w_input in self.inputs
        ]

        return context


class SelectorList(widgets.TextInput):
    template_name = 'creme_core/forms/widgets/selector-list.html'
    action_class = WidgetAction

    # def __init__(self, selector, attrs=None, enabled=True):
    def __init__(self, selector, attrs=None, **kwargs):
        super().__init__(attrs)
        self.selector = selector

        # self.enabled = enabled
        self._enabled = True  # DEPRECATED
        if kwargs:
            self.enabled = kwargs.pop('enabled')
            assert not kwargs, 'Invalid attribute'

        self.actions = [self.action_class(name='add', label=gettext_lazy('Add'), icon='add')]
        self.from_python = None  # TODO: remove this hack ?

    @property
    def enabled(self):
        warnings.warn(
            'SelectorList: the attribute <enabled> is deprecated ; '
            'use <attrs={"disabled": True}> to disable instead.',
            DeprecationWarning
        )
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        warnings.warn(
            'SelectorList: the attribute <enabled> is deprecated ; '
            'use <attrs={"disabled": True}> to disable instead.',
            DeprecationWarning
        )
        self._enabled = value

    def add_action(self, name, label, enabled=True, icon: Optional[str] = None, **attrs):
        self.actions.append(self.action_class(
            name=name, label=label, icon=icon, enabled=enabled, **attrs
        ))
        return self

    def clear_actions(self):
        self.actions[:] = ()
        return self

    def get_context(self, name, value, attrs):
        widget_type = 'ui-creme-selectorlist'

        value = self.from_python(value) if self.from_python is not None else value

        # context = super().get_context(name=name, value=value, attrs=None)
        # widget_cxt = context['widget']
        # widget_cxt['class'] = f'ui-creme-widget widget-auto {widget_type}'
        # widget_cxt['widget_type'] = widget_type
        #
        # final_attrs = widget_cxt['attrs']
        # widget_cxt['clonelast'] = final_attrs.pop('clonelast', True)
        # widget_cxt['enabled'] = self.enabled
        context = super().get_context(name=name, value=value, attrs=attrs)
        widget_cxt = context['widget']
        final_attrs = widget_cxt['attrs']

        # DEPRECATED
        if not self._enabled:
            final_attrs['disabled'] = True
        widget_cxt['enabled'] = self._enabled

        widget_cxt['clonelast'] = 'clonelast' in final_attrs  # DEPRECATED

        final_attrs['class'] = (
            f"ui-creme-widget widget-auto {widget_type} "
            f"{final_attrs.get('class', '')} "
            f"{'is-disabled' if 'disabled' in final_attrs else ''}"
        )
        final_attrs['widget'] = widget_type  # TODO: data-widget
        final_attrs.setdefault('clonelast', True)  # TODO: data-clonelast

        widget_cxt['widget_type'] = widget_type  # TODO: deprecate?
        widget_cxt['input'] = widgets.HiddenInput().get_context(
            name=name, value=value,
            # TODO: final_attrs.pop("disabled", False) to get it only here (& rework
            #      the JavaScript component to inspect the input instead of the div)
            attrs={
                'class': f'ui-creme-input {widget_type}',
                **({'disabled': True} if 'disabled' in final_attrs else {})
            },
        )['widget']
        widget_cxt['actions'] = [action.context for action in self.actions]
        widget_cxt['selector'] = self.selector.get_context(
            name='', value='', attrs={'auto': False, 'reset': False},
        )['widget']

        return context


class EntitySelector(widgets.Widget):
    template_name = 'creme_core/forms/widgets/entity-selector.html'

    def __init__(self, content_type=None, attrs=None):
        """ Constructor.
        @param content_type: Template variable which represent the ContentType ID in the URL.
               Default is '${ctype}'.
        @param attrs: see Widget.
        """
        super().__init__(attrs=attrs)
        self.url = self._build_listview_url(content_type)
        self.text_url = self._build_text_url()
        self.from_python = None

    def _build_listview_url(self, content_type):
        return '%s?ct_id=%s&selection=${selection}&q_filter=${qfilter}' % (
            reverse('creme_core__listview_popup'),
            content_type or '${ctype}',
        )

    def _build_text_url(self):
        # TODO: use a GET parameter instead of using a TemplateURLBuilder ?
        return TemplateURLBuilder(
            entity_id=(TemplateURLBuilder.Int, '${id}'),
        ).resolve('creme_core__entity_as_json')

    def get_context(self, name, value, attrs):
        widget_type = 'ui-creme-entityselector'

        # value = self.from_python(value) if self.from_python is not None else value  # TODO ?

        context = super().get_context(name=name, value=value, attrs=attrs)
        widget_cxt = context['widget']
        widget_cxt['url']      = self.url
        widget_cxt['text_url'] = self.text_url

        final_attrs = widget_cxt['attrs']
        base_css = (
            'ui-creme-widget widget-auto'
            if final_attrs.pop('auto', True) else
            'ui-creme-widget'
        )
        widget_cxt['class'] = (
            f"{base_css} {widget_type} {final_attrs.get('class', '')}"
        ).strip()
        widget_cxt['widget_type'] = widget_type

        widget_cxt['selection'] = 'multiple' if final_attrs.pop('multiple', False) else 'single'
        widget_cxt['autoselect'] = final_attrs.pop('autoselect', False)
        widget_cxt['disabled']   = final_attrs.pop('disabled', False)

        qfilter = final_attrs.pop('qfilter', None)
        # TODO: factorise (see CreatorEntityField.q_filter_query() )
        if callable(qfilter):
            qfilter = qfilter()

        if isinstance(qfilter, dict):
            qfilter = Q(**qfilter)

        widget_cxt['qfilter'] = QSerializer().serialize(qfilter) if qfilter else None
        widget_cxt['input'] = widgets.TextInput().get_context(
            name=name, value=value,
            attrs={
                'class': f'ui-creme-input {widget_type}',
                'required': self.is_required,
            },
        )['widget']

        return context


class CTEntitySelector(ChainedInput):
    # template_name = ... TODO in order to override from apps ?

    def __init__(
            self,
            content_types=(),
            attrs=None,
            multiple=False,
            autocomplete=False,
            creator=False):
        super().__init__(attrs=attrs)
        self.content_types = content_types
        self.multiple = multiple
        self.autocomplete = autocomplete
        self.creator = creator

    def get_context(self, name, value, attrs):
        field_attrs = {'auto': False, 'datatype': 'json'}
        if self.autocomplete:
            field_attrs['autocomplete'] = True

        self.add_dselect('ctype', options=self.content_types, attrs=field_attrs)

        multiple = self.multiple
        selector = EntitySelector(
            content_type='${ctype.id}',
            attrs={'auto': False, 'multiple': multiple},
        )
        selector.is_required = self.is_required

        actions = ActionButtonList(delegate=selector)

        if not self.is_required and not multiple:
            clear_label = _('Clear')
            actions.add_action(
                'reset', clear_label,
                icon='delete',
                title=clear_label, action='reset', value='',
            )

        if self.creator:
            actions.add_action(
                name='create', label=_('Add'),
                icon='add',
                popupUrl='${ctype.create}', popupTitle='${ctype.create_label}',
            )

        self.add_input('entity', widget=actions)

        return super().get_context(name=name, value=value, attrs=attrs)


class MultiCTEntitySelector(SelectorList):
    # template_name = ... TODO in order to override from apps ?

    def __init__(self, content_types=(), attrs=None, autocomplete=False, creator=False):
        super().__init__(None, attrs=attrs)
        self.content_types = content_types
        self.autocomplete = autocomplete
        self.creator = creator

    def get_context(self, name, value, attrs):
        self.selector = CTEntitySelector(
            content_types=self.content_types,
            multiple=True,
            autocomplete=self.autocomplete,
            creator=self.creator,
            attrs={'reset': False},
        )

        return super().get_context(name=name, value=value, attrs=attrs)


class RelationSelector(ChainedInput):
    # template_name = ... TODO in order to override from apps ?

    def __init__(self, relation_types=(), content_types=None,  # TODO: rename 'ctypes_url' ?
                 attrs=None, multiple=False, autocomplete=False):
        super().__init__(attrs)
        self.relation_types = relation_types
        self.content_types = content_types
        self.multiple = multiple
        self.autocomplete = autocomplete

    def _build_ctypes_url(self):
        return TemplateURLBuilder(
            rtype_id=(TemplateURLBuilder.Word, '${rtype}'),
        ).resolve('creme_core__ctypes_compatible_with_rtype')

    def get_context(self, name, value, attrs):
        dselect_attrs = {'auto': False, 'autocomplete': True} if self.autocomplete else \
                        {'auto': False}

        self.add_dselect(
            'rtype', options=self.relation_types, attrs=dselect_attrs,
        )
        self.add_dselect(
            'ctype', options=self.content_types or self._build_ctypes_url(), attrs=dselect_attrs,
        )
        self.add_input(
            'entity', widget=EntitySelector, attrs={'auto': False, 'multiple': self.multiple},
        )

        return super().get_context(name=name, value=value, attrs=attrs)


class MultiRelationSelector(SelectorList):
    # template_name = ... TODO in order to override from apps ?

    def __init__(self, relation_types=(), content_types=None,
                 attrs=None, autocomplete=False):
        super().__init__(None, attrs=attrs)
        self.relation_types = relation_types
        self.content_types = content_types
        self.autocomplete = autocomplete

    def get_context(self, name, value, attrs):
        self.selector = RelationSelector(
            relation_types=self.relation_types,
            content_types=self.content_types,
            multiple=True,
            autocomplete=self.autocomplete,
        )

        return super().get_context(name=name, value=value, attrs=attrs)


class EntityCreatorWidget(ActionButtonList):
    # template_name = ... TODO in order to override from apps ?

    def __init__(self, model=None, q_filter=None, attrs=None, creation_url='',
                 creation_allowed=False, creation_label=None):
        super().__init__(delegate=None, attrs=attrs)
        self.model = model
        self.q_filter = q_filter
        self.creation_url = creation_url
        self.creation_allowed = creation_allowed
        self.creation_label = creation_label

    def _is_disabled(self, attrs):
        if attrs is not None:
            return 'disabled' in attrs or 'readonly' in attrs

        return False

    def _build_actions(self, model, attrs):
        is_disabled = self._is_disabled(attrs)

        self.clear_actions()

        if not is_disabled:
            if not self.is_required:
                clear_label = _('Clear')
                self.add_action(
                    'reset', clear_label,
                    title=clear_label, action='reset', value='', icon='delete',
                )

            url = self.creation_url
            if url:
                allowed = self.creation_allowed
                self.add_action(
                    name='create',
                    label=self.creation_label or model.creation_label,
                    icon='add',
                    enabled=allowed,
                    popupUrl=url,
                    title=_('Create') if allowed else _("Can't create"),
                )

    def get_context(self, name, value, attrs):
        model = self.model

        # TODO: creating instance of delegate here is ugly
        #       (use an ActionButtonList & not inherit it ?)
        if model is None:
            self.delegate = Label(empty_label='Model is not set')
        else:
            selector_attrs = {'auto': False, 'disabled': self._is_disabled(attrs)}

            if self.q_filter is not None:
                selector_attrs['qfilter'] = self.q_filter

            self.delegate = EntitySelector(
                str(ContentType.objects.get_for_model(model).id),
                selector_attrs,
            )

            self._build_actions(model, attrs)

        return super().get_context(name=name, value=value, attrs=attrs)


# TODO: unit tests ?
# TODO: factorise with EntityCreatorWidget ?
class MultiEntityCreatorWidget(SelectorList):
    # template_name = ... TODO in order to override from apps ?

    def __init__(self, model=None, q_filter=None, attrs=None, creation_url='',
                 creation_allowed=False, creation_label=None):
        attrs = attrs or {'clonelast': False}
        super().__init__(None, attrs=attrs)
        self.model = model
        self.q_filter = q_filter
        self.creation_url = creation_url
        self.creation_allowed = creation_allowed
        self.creation_label = creation_label

    def get_context(self, name, value, attrs):
        model = self.model
        # TODO: create only if does not exist ?
        self.selector = button_list = ActionButtonList(delegate=None)

        if model is None:
            delegate = Label(empty_label='Model is not set')
        else:
            self.clear_actions()  # TODO: indicate that we do not want actions in __init__
            self.add_action(
                name='add',
                label=getattr(model, 'selection_label', pgettext('creme_core-verb', 'Select')),
            )

            delegate = EntitySelector(
                str(ContentType.objects.get_for_model(model).id),
                {
                    'auto':       False,
                    'qfilter':    self.q_filter,
                    'multiple':   True,
                    'autoselect': True,
                },
            )

            url = self.creation_url
            if url:
                allowed = self.creation_allowed
                action_name = 'create'
                label = self.creation_label or model.creation_label
                icon = 'add'
                button_list.add_action(
                    name=action_name, label=label, icon=icon,
                    enabled=False, hidden=True,
                    title=_('Create') if allowed else _("Can't create"),
                    popupUrl=url,
                )
                self.add_action(name=action_name, label=label, icon=icon, enabled=allowed)

        button_list.delegate = delegate

        return super().get_context(name=name, value=value, attrs=attrs)


class FilteredEntityTypeWidget(ChainedInput):
    # template_name = ... TODO in order to override from apps ?

    def __init__(self, content_types=(), attrs=None, autocomplete=True):
        super().__init__(attrs)
        self.content_types = content_types
        self.autocomplete = autocomplete

    def get_context(self, name, value, attrs):
        add_dselect = partial(
            self.add_dselect,
            attrs={'auto': False, 'autocomplete': self.autocomplete},
        )
        ctype_name = 'ctype'
        add_dselect(ctype_name, options=self.content_types)

        # TODO: allow to omit the 'All' filter ??
        # TODO: do not make a request for ContentType ID == '0'
        add_dselect(
            'efilter',
            options=reverse('creme_core__efilters') + '?ct_id=${%s}&all=true' % ctype_name,
        )

        return super().get_context(name=name, value=value, attrs=attrs)


# class DateTimeWidget(widgets.DateTimeInput):
class DateTimeWidget(DatePickerMixin, widgets.DateTimeInput):
    is_localized = True  # TODO: settings.USE_L10N?
    template_name = 'creme_core/forms/widgets/datetime.html'

    # def __init__(self, attrs=None):
    #     super().__init__(attrs=attrs, format='%d-%m-%Y %H:%M')

    def get_context(self, name, value, attrs):
        context = super().get_context(name=name, value=value, attrs=attrs)

        widget_cxt = context['widget']
        widget_cxt['type'] = 'hidden'
        # widget_cxt['date_format'] = settings.DATE_FORMAT_JS.get(settings.DATE_FORMAT)
        widget_cxt['date_format'] = self.js_date_format()

        return context


class TimeWidget(widgets.TextInput):
    template_name = 'creme_core/forms/widgets/time.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name=name, value=value, attrs=attrs)
        context['widget']['type'] = 'hidden'

        return context

    def value_from_datadict(self, data, files, name):
        value = data.get(name, '')

        if value.strip() == ':':
            value = ''

        return value


# class CalendarWidget(widgets.TextInput):
class CalendarWidget(DatePickerMixin, widgets.TextInput):
    is_localized = True
    template_name = 'creme_core/forms/widgets/date.html'
    # default_help_text = settings.DATE_FORMAT_VERBOSE
    default_help_text = _('Eg: {}')

    def get_default_help_text(self, date_format):
        return self.default_help_text.format(
            date.today().replace(month=12, day=31).strftime(date_format)
        )

    def get_context(self, name, value, attrs):
        date_format = self.get_date_format()
        widget_type = 'ui-creme-datepicker'

        context = super().get_context(name=name, value=value, attrs=attrs)
        widget_cxt = context['widget']
        # widget_cxt['format_help_text'] = self.default_help_text
        widget_cxt['format_help_text'] = self.get_default_help_text(date_format)

        final_attrs = widget_cxt['attrs']

        base_css = (
            'ui-creme-input ui-creme-widget widget-auto'
            if final_attrs.pop('auto', True) else
            'ui-creme-input ui-creme-widget'
        )
        final_attrs['class'] = (
            f"{base_css} {widget_type} {final_attrs.get('class', '')}"
        ).strip()
        final_attrs['widget'] = widget_type  # TODO: data-widget[-type]
        # TODO: data-date-format
        # final_attrs['format'] = settings.DATE_FORMAT_JS.get(settings.DATE_FORMAT)
        final_attrs['format'] = self.js_date_format(date_format)

        return context


class OptionalWidget(widgets.MultiWidget):
    template_name = 'creme_core/forms/widgets/optional.html'

    def __init__(self, sub_widget=widgets.TextInput, attrs=None, sub_label=''):
        super().__init__(
            widgets=(
                widgets.CheckboxInput(
                    # attrs={'onchange': 'creme.forms.optionalWidgetHandler(this)'},
                    attrs={'class': 'optional-widget-trigger'},
                ),
                sub_widget,
            ),
            attrs=attrs,
        )
        self.sub_label = sub_label

    def decompress(self, value):
        return (value[0], value[1]) if value else (None, None)

    def get_context(self, name, value, attrs):
        context = super().get_context(name=name, value=value, attrs=attrs)
        w_context = context['widget']
        w_context['label'] = self.sub_label

        # TODO: factorise
        widget_type = 'ui-creme-optional'
        final_attrs = w_context['attrs']
        disabled = final_attrs.pop('disabled', False)
        base_css = (
            'optional-widget ui-creme-widget widget-auto'
            if final_attrs.pop('auto', True) else
            'optional-widget ui-creme-widget'
        )
        final_attrs['class'] = (
            f"{base_css} {widget_type}"
            f"{' is-disabled' if disabled else ''}"
            f" {final_attrs.get('class', '')}"
        ).strip()
        final_attrs['widget'] = widget_type  # TODO: data-widget

        return context

    @property
    def sub_widget(self):
        return self.widgets[1]


class OptionalSelect(OptionalWidget):
    def __init__(self, choices=(), *args, **kwargs):
        super().__init__(widgets.Select(choices=choices), *args, **kwargs)


class UnionWidget(widgets.Widget):
    template_name = 'creme_core/forms/widgets/union.html'

    def __init__(self, attrs=None, widgets_choices=()):
        super().__init__(attrs)
        self.widgets_choices = widgets_choices

    def get_context(self, name, value, attrs):
        context = super().get_context(name=name, value=value, attrs=attrs)

        widget_type = 'ui-creme-union'
        w_context = context['widget']
        final_attrs = w_context['attrs']
        base_css = (
            'union-widget ui-creme-widget widget-auto'
            if final_attrs.pop('auto', True) else
            'union-widget ui-creme-widget'
        )
        disabled = final_attrs.pop('disabled', False)
        final_attrs['class'] = (
            f"{base_css} {widget_type}"
            f"{' is-disabled' if disabled else ''}"
            f" {final_attrs.get('class', '')}"
        ).strip()
        final_attrs['widget'] = widget_type  # TODO: data-widget

        sub_attrs = {'disabled': True} if disabled else {}
        selected_sub_name, sub_values = ('', {}) if value is None else value
        # TODO: factorise f'{name}_{sub_name}' ?
        w_context['subwidget_choices'] = [
            {
                'name': sub_name,
                'label': sub_label,
                'checked': selected_sub_name == sub_name,
                'widget': sub_widget.get_context(
                    name=f'{name}_{sub_name}', value=sub_values.get(sub_name), attrs=sub_attrs,
                )['widget'],
            } for sub_name, sub_label, sub_widget in self.widgets_choices
        ]
        w_context['disabled'] = disabled

        return context

    def value_from_datadict(self, data, files, name):
        selected = data.get(name)
        sub_values = {
            sub_name: sub_widget.value_from_datadict(data, files, f'{name}_{sub_name}')
            for sub_name, _label, sub_widget in self.widgets_choices
        }

        return selected, sub_values


class TinyMCEEditor(widgets.Textarea):
    def get_context(self, name, value, attrs):
        context = super().get_context(name=name, value=value, attrs=attrs)
        if not attrs.get('disabled'):
            widget_type = 'ui-creme-editor'

            final_attrs = context['widget']['attrs']
            base_css = (
                'ui-creme-input ui-creme-widget widget-auto'
                if final_attrs.pop('auto', True) else
                'ui-creme-input ui-creme-widget'
            )
            final_attrs['class'] = (
                f"{base_css} {widget_type} {final_attrs.get('class', '')}"
            ).strip()
            final_attrs['widget'] = widget_type
            final_attrs['basepath'] = 'tiny_mce'  # See root urls.py

        return context


class ColorPickerWidget(widgets.TextInput):
    template_name = 'creme_core/forms/widgets/color.html'

    def get_context(self, name, value, attrs):
        widget_type = 'ui-creme-jqueryplugin'
        context = super().get_context(name=name, value=value, attrs=attrs)

        final_attrs = context['widget']['attrs']
        base_css = (
            'ui-creme-input ui-creme-widget widget-auto'
            if final_attrs.pop('auto', True) else
            'ui-creme-input ui-creme-widget'
        )
        final_attrs['class'] = (
            f"{base_css} {widget_type} {final_attrs.get('class', '')}"
        ).strip()
        final_attrs['widget'] = widget_type
        final_attrs['plugin'] = 'gccolor'

        return context


class UnorderedMultipleChoiceWidget(EnhancedSelectOptions, widgets.SelectMultiple):
    template_name = 'creme_core/forms/widgets/unordered-multiple.html'

    MODE_SEARCH = 'search'
    MODE_FILTER = 'filter'
    MODES = {MODE_SEARCH, MODE_FILTER}

    MIN_SEARCH_COUNT = 10
    MIN_FILTER_COUNT = 30
    MIN_CHECKALL_COUNT = 3

    def __init__(self, attrs=None, choices=(),
                 columntype='', filtertype=None, viewless=40,  # viewless=20,
                 creation_url='', creation_allowed=False,
                 creation_label=gettext_lazy('Create'),
                 ):
        """Constructor.
        @param attrs: See SelectMultiple.attrs.
        @param choices: See SelectMultiple.choices.
        @param columntype: Extra CSS class of the items container.
        @param filtertype: 'search' to activate search mode (items which do not
               match are translucent) ;
               'filter' to activate filter mode (items which do not
               match are hidden) ;
               Empty to let the widget chose the mode.
        @param viewless: An integer N to hide the items after the Nth item ;
               True to let the widget chose the value of N ;
               False to deactivate this "less" feature.
        @param creation_url: URL to create a new element (in an inner-popup dialog) ;
               ignored if empty.
        @param creation_allowed: False to disable the creation button
               (only used if 'creation_url' is given).
        @param creation_label: Label of the creation button
               (only used if 'creation_url' is given).
        """
        super().__init__(attrs, choices)
        self.columntype = columntype
        self.filtertype = filtertype
        self.viewless = viewless
        self.creation_url = creation_url
        self.creation_allowed = creation_allowed
        self.creation_label = creation_label

    def _choice_count(self):  # TODO: inline ?
        return sum(len(c[1]) if isinstance(c[1], (list, tuple)) else 1 for c in self.choices)

    def _build_filtertype(self, count):
        if self._filtertype:
            return self._filtertype

        if count < self.MIN_SEARCH_COUNT:
            return None
        elif count < self.MIN_FILTER_COUNT:
            return self.MODE_SEARCH
        else:
            return self.MODE_FILTER

    @property
    def filtertype(self):
        return self._filtertype

    @filtertype.setter
    def filtertype(self, filtertype):
        if filtertype and filtertype not in self.MODES:
            raise ValueError(
                f'{self.__class__.__name__}.filtertype: '
                f'the value must be in {self.MODES} (given value: "{filtertype}")'
            )

        self._filtertype = filtertype

    def get_context(self, name, value, attrs):
        widget_type = 'ui-creme-checklistselect'

        if value is not None:
            value = [*value]

        count = self._choice_count()
        context = super().get_context(name=name, value=value, attrs=attrs)
        widget_cxt = context['widget']

        final_attrs = widget_cxt['attrs']
        base_css = (
            'ui-creme-widget widget-auto'
            if final_attrs.pop('auto', True) else
            'ui-creme-widget'
        )
        widget_cxt['class'] = (
            f"{base_css} {widget_type} {final_attrs.get('class', '')}"
        ).strip()
        final_attrs['class'] = 'ui-creme-input'
        widget_cxt['widget_type'] = widget_type

        widget_cxt['column_type'] = self.columntype
        widget_cxt['view_less'] = self.viewless

        widget_cxt['checkall'] = final_attrs.pop('checkall', True)

        widget_cxt['choice_count'] = count
        widget_cxt['filter_type'] = self._build_filtertype(count)

        widget_cxt['MIN_CHECKALL_COUNT'] = self.MIN_CHECKALL_COUNT
        # NB: not used ; set for consistency/extensibility.
        widget_cxt['MIN_SEARCH_COUNT'] = self.MIN_SEARCH_COUNT
        # Idem
        widget_cxt['MIN_FILTER_COUNT'] = self.MIN_FILTER_COUNT

        widget_cxt['creation_allowed'] = self.creation_allowed
        widget_cxt['creation_url']     = self.creation_url
        widget_cxt['creation_label']   = self.creation_label

        return context


class OrderedMultipleChoiceWidget(widgets.SelectMultiple):
    template_name = 'creme_core/forms/widgets/ordered-multiple.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name=name, value=value, attrs=attrs)

        context['widget']['orders'] = {
            opt_value: order + 1
            for order, opt_value in enumerate(value or ())
        }

        return context

    def value_from_datadict(self, data, files, name):
        prefix_check = f'{name}_check_'
        prefix_order = f'{name}_order_'
        prefix_value = f'{name}_value_'

        selected = []
        for key, value in data.items():
            if key.startswith(prefix_check):
                index = key[len(prefix_check):]  # In fact not an int...
                order = int(data.get(prefix_order + index) or 0)
                value = data[prefix_value + index]
                selected.append((order, value))

        selected.sort(key=lambda i: i[0])

        return [val for _order, val in selected]


class Label(widgets.TextInput):
    template_name = 'creme_core/forms/widgets/label.html'
    empty_label = None  # TODO: remove ?

    def __init__(self, attrs=None, empty_label=None):
        super().__init__(attrs=attrs)
        self.empty_label = empty_label

    def get_context(self, name, value, attrs):
        context = super().get_context(name=name, value=value, attrs=attrs)
        context['widget']['content'] = value or self.empty_label

        return context


class ListEditionWidget(widgets.Widget):
    # TODO: 'disabled' state is probably not working as expected...
    template_name = 'creme_core/forms/widgets/list-editor.html'
    content = ()
    only_delete = False

    def get_context(self, name, value, attrs):
        context = super().get_context(name=name, value=value, attrs=attrs)

        items = []
        for i, label in enumerate(self.content):
            checked = True

            if value:
                new_label = value[i]

                if new_label is None:
                    checked = False
                else:
                    label = new_label

            items.append({'checked': checked, 'label': label})

        widget_ctxt = context['widget']
        widget_ctxt['only_delete'] = self.only_delete
        widget_ctxt['items'] = items

        return context

    def value_from_datadict(self, data, files, name):
        prefix_check_fmt = (name + '_check_{}').format
        prefix_value_fmt = (name + '_value_{}').format
        get = data.get

        return [
            get(prefix_value_fmt(i)) if (prefix_check_fmt(i) in data) else None
            for i in range(len(self.content))
        ]


class DatePeriodWidget(widgets.MultiWidget):
    template_name = 'creme_core/forms/widgets/date-period.html'

    def __init__(self, choices=(), attrs=None):
        super().__init__(
            widgets=(
                widgets.Select(choices=choices, attrs={'class': 'dperiod-type'}),
                # widgets.TextInput(attrs={'class': 'dperiod-value'}),
                widgets.NumberInput(attrs={'class': 'dperiod-value', 'min': 1}),
            ),
            attrs=attrs,
        )

    @property
    def choices(self):
        return self.widgets[0].choices

    @choices.setter
    def choices(self, choices):
        self.widgets[0].choices = choices

    def decompress(self, value):
        if value:
            d = value.as_dict()
            return d['type'], d['value']

        return None, None

    def get_context(self, name, value, attrs):
        context = super().get_context(name=name, value=value, attrs=attrs)

        # TODO: do we need a system for localized settings (like python in locale/ ) ?
        try:
            # Translators: this string is used to set the order of the inputs
            # in the widget to choose the relative trigger date of Alerts.
            # Just re-order the format argument, DO NOT ADD other characters (like space...)
            # dateperiod_value: the value of the period ("1" in "1 week)
            # dateperiod_type: the type of the period ("week" in "1 week)
            localized_order = _('{dateperiod_value}{dateperiod_type}').format(
                dateperiod_type='0',
                dateperiod_value='1',
            )
            inverted = localized_order.index('1') < localized_order.index('0')
        except Exception:  # TODO: better exception
            logger.exception('DatePeriodWidget.get_context()')
            inverted = False

        context['widget']['indices'] = (1, 0) if inverted else (0, 1)

        return context


# TODO: factorise with DatePeriodWidget?
class RelativeDatePeriodWidget(widgets.MultiWidget):
    template_name = 'creme_core/forms/widgets/date-period.html'

    def __init__(self, period_choices=(), relative_choices=(), attrs=None):
        super().__init__(
            widgets=(
                widgets.Select(
                    choices=relative_choices,
                    attrs={'class': 'relative_dperiod-direction'},
                ),
                widgets.Select(
                    choices=period_choices,
                    attrs={'class': 'relative_dperiod-type'},
                ),
                widgets.NumberInput(attrs={'class': 'relative_dperiod-value', 'min': 1}),
            ),
            attrs=attrs,
        )

    @property
    def period_choices(self):
        return self.widgets[1].choices

    @period_choices.setter
    def period_choices(self, choices):
        self.widgets[1].choices = choices

    @property
    def relative_choices(self):
        return self.widgets[0].choices

    @relative_choices.setter
    def relative_choices(self, choices):
        self.widgets[0].choices = choices

    def decompress(self, value):
        if value:
            sign, period = value
            d = period.as_dict()
            return sign, d['type'], d['value']

        return None, None, None

    def get_context(self, name, value, attrs):
        context = super().get_context(name=name, value=value, attrs=attrs)

        # TODO: do we need a system for localized settings (like python in locale/ ) ?
        try:
            # Translators: this string is used to set the order of the inputs
            # in the widget to choose the relative trigger date of Alerts.
            # Just re-order the format argument, DO NOT ADD other characters (like space...)
            # dateperiod_value: the value of the period ("1" in "1 week)
            # dateperiod_type: the type of the period ("week" in "1 week)
            # dateperiod_direction: "after" or "before"
            localized_order = _('{dateperiod_value}{dateperiod_type}{dateperiod_direction}').format(  # NOQA
                dateperiod_type='1',
                dateperiod_value='2',
                dateperiod_direction='0',
            )
            indices = [int(i) for i in localized_order]
        except Exception:  # TODO: better exception
            logger.exception('RelativeDatePeriodWidget.get_context()')
            indices = (0, 1, 2)

        context['widget']['indices'] = indices

        return context


class DateRangeWidget(widgets.MultiWidget):
    template_name_format = 'creme_core/forms/widgets/date-range/{}.html'

    def __init__(self, choices=(), attrs=None):
        self.render_as = attrs.pop('render_as', 'table') if attrs else 'table'

        super().__init__(
            widgets=(
                widgets.Select(choices=choices, attrs={'data-daterange-type': True}),
                CalendarWidget(attrs={'data-daterange-field': 'start'}),
                CalendarWidget(attrs={'data-daterange-field': 'end'}),
            ),
            attrs=attrs,
        )

    @property
    def choices(self):
        return self.widgets[0].choices

    @choices.setter
    def choices(self, choices):
        self.widgets[0].choices = choices

    def decompress(self, value):
        if value:
            return value[0], value[1], value[2]
        return None, None, None

    @property
    def template_name(self):
        return self.template_name_format.format(self.render_as)

    def get_context(self, name, value, attrs):
        widget_type = 'ui-creme-daterange'
        context = super().get_context(name=name, value=value, attrs=attrs)

        widget_cxt = context['widget']
        final_attrs = widget_cxt['attrs']
        base_css = (
            'ui-creme-widget widget-auto'
            if final_attrs.pop('auto', True) else
            'ui-creme-widget'
        )
        widget_cxt['class'] = f"{base_css} {widget_type} {final_attrs.get('class', '')}".strip()
        widget_cxt['widget_type'] = widget_type

        return context


class DurationWidget(widgets.MultiWidget):
    template_name = 'creme_core/forms/widgets/duration.html'

    def __init__(self, attrs=None):
        super().__init__(widgets=[widgets.TextInput] * 3, attrs=attrs)

    def decompress(self, value):
        return value.split(':') if value else (None, None, None)


class ChoiceOrCharWidget(widgets.MultiWidget):
    template_name = 'creme_core/forms/widgets/select-or-input.html'

    def __init__(self, attrs=None, choices=()):
        super().__init__(
            widgets=(
                widgets.Select(choices=choices),
                widgets.TextInput(attrs={
                    'placeholder': _('Value not in the choices? Fill it here!'),
                }),
            ),
            attrs=attrs,
        )

    @property
    def choices(self):
        return self.widgets[0].choices

    @choices.setter
    def choices(self, choices):
        self.widgets[0].choices = choices

    def decompress(self, value):
        if value:
            return value[0], value[1]

        return None, None


class CremeRadioSelect(widgets.RadioSelect):
    template_name = 'creme_core/forms/widgets/radio.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name=name, value=value, attrs=attrs)

        final_attrs = context['widget']['attrs']
        # TODO: radio_select => radio-select?
        final_attrs['class'] = f"{final_attrs.get('class', '')} radio_select".strip()

        return context


class CremeTextarea(widgets.Widget):
    template_name = 'django/forms/widgets/textarea.html'

    # Default HTML: 20 x 2
    default_cols = 40
    default_rows = 3
    widget_type = 'ui-creme-autosizedarea'

    # TODO: manage a max ?
    def __init__(self, attrs=None):
        default_attrs = {
            'cols': self.default_cols,
            'rows': self.default_rows,
        }
        if attrs:
            default_attrs.update(attrs)

        super().__init__(default_attrs)

    def get_context(self, name, value, attrs):
        widget_type = self.widget_type

        context = super().get_context(name=name, value=value, attrs=attrs)

        final_attrs = context['widget']['attrs']
        final_attrs['class'] = ' '.join(filter(
            None,
            [
                final_attrs.get('class', ''),
                f'ui-creme-widget widget-auto {widget_type}',
            ],
        ))
        final_attrs['widget'] = widget_type

        return context


class NoPreviewClearableFileInput(widgets.ClearableFileInput):
    clear_checkbox_label = _('Clear the current file')
    template_name = 'creme_core/forms/widgets/clearable-file-input.html'
