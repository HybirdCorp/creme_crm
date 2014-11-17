# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

#from datetime import datetime
from itertools import chain
#import warnings

#from django.contrib.contenttypes.models import ContentType
from django.forms.widgets import (Widget, Textarea, Select, SelectMultiple,
        TextInput, Input, MultiWidget, RadioSelect, RadioFieldRenderer) #FileInput
from django.forms.util import flatatt
from django.utils.html import conditional_escape, escape
from django.utils.translation import ugettext as _
from django.utils.encoding import force_unicode
from django.utils.simplejson.encoder import JSONEncoder
from django.utils.safestring import mark_safe
#from django.utils.formats import date_format
#from django.core.validators import EMPTY_VALUES
from django.conf import settings

from ..utils.media import creme_media_themed_url as media_url
from ..utils.date_range import date_range_registry


def widget_render_input(renderer, widget, name, value, context, **kwargs):
    input_attrs = {'class':  ' '.join(['ui-creme-input', context.get('css', '')]),
                   'widget': context.get('typename', None),
                  }
    input_attrs.update(kwargs)

    return renderer(widget, name, value, input_attrs)

def widget_render_hidden_input(widget, name, value, context):
    input_attrs = {'class': ' '.join(['ui-creme-input', context.get('typename')]),
                   'type':  'hidden',
                  }

    return Input.render(widget, name, value, input_attrs)

def widget_render_context(typename, attrs, css='', **kwargs):
    id   = attrs.get('id')
    auto = attrs.pop('auto', True)
    css = ' '.join((css, 'ui-creme-widget widget-auto' if auto else 'ui-creme-widget', typename)).strip()
    context = {'style':      '',
               'typename':   typename,
               'css':        css,
               'auto':       auto,
               'id':         id,
              }

    context.update(kwargs)

    return context

#TODO: to be improved....
class DynamicInput(TextInput):
    def __init__(self, type='text', attrs=None):
        super(DynamicInput, self).__init__(attrs)
        #self.type = type
        self.input_type = type

    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name)
        #context = widget_render_context('ui-creme-dinput', attrs, type=self.type)
        context = widget_render_context('ui-creme-dinput', attrs)

        return mark_safe(widget_render_input(TextInput.render, self, name, value, context)) #, url=self.url

#TODO ??? DynamicHiddenInput
#class HiddenInput(Input): #from django
    #input_type = 'hidden'
    #is_hidden = True


class DynamicSelect(Select):
    def __init__(self, attrs=None, options=None, url='', label=None):
        super(DynamicSelect, self).__init__(attrs, ()) #TODO: options or ()
        self.url = url
        self.label = label
        self.from_python = None

        if not options:
            self.options = ()
        elif callable(options):
            self.options = options
        else:
            self.options = list(options)

    def _get_options(self):
        return list(self.options()) if callable(self.options) else self.options

    @property
    def choices(self):
        return self._get_options()

    @choices.setter
    def choices(self, choices):
        self.options = choices

    def render(self, name, value, attrs=None, choices=()):
        attrs = self.build_attrs(attrs, name=name)
        context = widget_render_context('ui-creme-dselect', attrs)

        value = self.from_python(value) if self.from_python is not None else value
        output = widget_render_input(Select.render, self, name, value, context, url=self.url)

        if not self.label:
            return mark_safe(output)

        return mark_safe(u"""<span class="ui-creme-dselectlabel">%s</span>%s""" % (self.label, output))


class ActionButtonList(Widget):
    def __init__(self, delegate, attrs=None, actions=None):
        super(ActionButtonList, self).__init__(attrs)
        self.delegate = delegate
        self.actions = actions or []

    def add_action(self, name, label, enabled=True, **kwargs):
        self.actions.append((name, label, enabled, kwargs))
        return self

    def clear_actions(self):
        self.actions = []
        return self

    def render(self, name, value, attrs=None):
        context = widget_render_context('ui-creme-actionbuttonlist', attrs)
        context['delegate'] = self.delegate.render(name, value, attrs)
        context['buttons'] = self._render_actions()

        return mark_safe("""<ul class="ui-layout hbox %(css)s" style="%(style)s" widget="%(typename)s">
                                <li class="delegate">%(delegate)s</li>
                                %(buttons)s
                            </ul>""" % context)

    def _render_actions(self):
        #output = []
        #output.extend(self._render_action(name, label, enabled, **attrs) for name, label, enabled, attrs in self.actions)

        #return '\n'.join(output)
        return '\n'.join(self._render_action(name, label, enabled, **attrs) for name, label, enabled, attrs in self.actions)

    def _render_action(self, name, label, enabled, **kwargs):
        if enabled is not None:
            if enabled is False or (callable(enabled) and not enabled()):
                kwargs['disabled'] = u''

        title = kwargs.pop('title', label)
        context = {'name':  name,
                   'attr':  flatatt(kwargs),
                   'label': label,
                   'title': title,
                  }

        return u"""<li><button class="ui-creme-actionbutton" name="%(name)s" title="%(title)s" alt="%(title)s" type="button" %(attr)s>
                       %(label)s
                   </button></li>""" % context


class PolymorphicInput(TextInput):
    class Model(object):
        def __init__(self, name='', widget=DynamicInput, attrs=None, **kwargs):
            self.name = name
            self.kwargs = kwargs
            self.attrs = attrs
            self.widget = widget

    def __init__(self, attrs=None, key='', *args):
        super(PolymorphicInput, self).__init__(attrs)
        self.key = key
        self.inputs = []
        self.default_input = None
        self.set_inputs(*args)
        self.from_python = None #TODO : wait for django 1.2 and new widget api to remove this hack

    def render(self, name, value, attrs=None):
        value = self.from_python(value) if self.from_python is not None else value #TODO : wait for django 1.2 and new widget api to remove this hack
        attrs = self.build_attrs(attrs, name=name, type='hidden')

        context = widget_render_context('ui-creme-polymorphicselect', attrs,
                                        style=attrs.pop('style', ''),
                                        selectors=self._render_inputs(attrs),
                                        key=self.key,
                                       )
        context['input'] = widget_render_hidden_input(self, name, value, context)

        return mark_safe("""<span class="%(css)s" style="%(style)s" widget="%(typename)s" key="%(key)s">
                                %(input)s
                                %(selectors)s
                            </span>""" % context)

    def set_inputs(self, *args):
        for input in args:
            self.add_input(input.name, input.widget, input.attrs, **input.kwargs)

    def add_dselect(self, name, options=None, attrs=None, **kwargs):
        if isinstance(options, basestring):
            self.add_input(name, widget=DynamicSelect, attrs=attrs, url=options, **kwargs)
        else:
            self.add_input(name, widget=DynamicSelect, attrs=attrs, options=options, **kwargs)

    def add_input(self, name, widget, attrs=None, **kwargs):
        self.inputs.append((name, widget(attrs=attrs, **kwargs) if isinstance(widget, type) else widget))

    def set_default_input(self, widget, attrs=None, **kwargs):
        self.default_input = widget(attrs=attrs, **kwargs) if isinstance(widget, type) else widget

    def _render_inputs(self, attrs):
        output = ['<script selector-key="%s" type="text/template">%s</script>' % (name, input.render('', ''))
                      for name, input in self.inputs
                 ]

        if self.default_input:
            output.append('<script selector-key="*" type="text/template">%s</script>' % (self.default_input.render('', '')))

        return '\n'.join(output)


class DateRangeSelect(TextInput):
    def __init__(self, attrs=None):
        super(DateRangeSelect, self).__init__(attrs)

        choices = [('', _("Customized"))]
        choices.extend(date_range_registry.choices())
        self.choices = choices

    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name, type='hidden')
        context = widget_render_context('ui-creme-daterange-selector', attrs)

        date_range = ['<select class="daterange-input range-type">']
        date_range.extend(u'<option value="%s">%s</option>' % (name, verb_name) for name, verb_name in self.choices)
        date_range.append('</select>')

        context['input'] = widget_render_hidden_input(self, name, value, context)
        context['select'] = '\n'.join(date_range)
        context['start'] = '<input type="text" class="daterange-input date-start"></input>'
        context['end']   = '<input type="text" class="daterange-input date-end"></input>'
        context['from']  = _(u'From')
        context['to']    = _(u'To')
        context['date_format'] = settings.DATE_FORMAT_JS.get(settings.DATE_FORMAT)

        return mark_safe("""<span class="%(css)s" style="%(style)s" widget="%(typename)s" date_format="%(date_format)s">
                                %(input)s
                                %(select)s
                               <span class="daterange-inputs"> %(from)s%(start)s&nbsp;%(to)s%(end)s</span>
                            </span>""" % context
                        )


class ChainedInput(TextInput):
    HORIZONTAL = 'hbox'
    VERTICAL = 'vbox'

    class Model(object):
        def __init__(self, name='', widget=DynamicSelect, attrs=None, **kwargs):
            self.name = name
            self.kwargs = kwargs
            self.attrs = attrs
            self.widget = widget

    def __init__(self, attrs=None, *args):
        super(ChainedInput, self).__init__(attrs)
        self.inputs = []
        self.set_inputs(*args)
        self.from_python = None #TODO : wait for django 1.2 and new widget api to remove this hack

    def render(self, name, value, attrs=None):
        value = self.from_python(value) if self.from_python is not None else value # TODO : wait for django 1.2 and new widget api to remove this hack
        attrs = self.build_attrs(attrs, name=name, type='hidden')

        context = widget_render_context('ui-creme-chainedselect', attrs,
                                        style=attrs.pop('style', ''),
                                        selects=self._render_inputs(attrs))

        context['input'] = widget_render_hidden_input(self, name, value, context)

        return mark_safe("""<div class="%(css)s" style="%(style)s" widget="%(typename)s">
                                %(input)s
                                %(selects)s
                            </div>""" % context)

    def set_inputs(self, *args):
        for input in args:
            self.add_input(input.name, input.widget, input.attrs, **input.kwargs)

    def add_dselect(self, name, options=None, attrs=None, **kwargs):
        if isinstance(options, basestring):
            self.add_input(name, widget=DynamicSelect, attrs=attrs, url=options, **kwargs)
        else:
            self.add_input(name, widget=DynamicSelect, attrs=attrs, options=options, **kwargs)

    def add_input(self, name, widget, attrs=None, **kwargs):
        self.inputs.append((name, widget(attrs=attrs or {}, **kwargs) if callable(widget) else widget))

    def _render_inputs(self, attrs):
        direction = attrs.get('direction', ChainedInput.HORIZONTAL)
        output = ['<ul class="ui-layout %s">' % direction]

        output.extend('<li chained-name="%s" class="ui-creme-chainedselect-item">%s</li>' % (name, input.render('', ''))
                         for name, input in self.inputs
                     )

        if attrs.pop('reset', True):
            output.append("""<li>
                                 <img class="reset" src="%s" alt="%s" title="%s"></img>
                             </li>""" % (media_url('images/delete_22.png'), _(u'Reset'), _(u'Reset'))) #TODO: call '_()' once...

        output.append('</ul>')

        return '\n'.join(output)


class SelectorList(TextInput):
    class Action(object):
        def __init__(self, name, label, enabled=True, **kwargs):
            self.name = name
            self.label = label
            self.enabled = enabled
            self.attrs = kwargs or {}

        @property
        def enabled(self):
            return self._enabled if callable(self._enabled) else self._enabled is True

        @enabled.setter
        def enabled(self, enabled):
            self._enabled = enabled

    def __init__(self, selector, attrs=None, enabled=True):
        super(SelectorList, self).__init__(attrs)
        self.selector = selector
        self.enabled = enabled
        self.actions = [self.Action('add', _(u'Add'))]
        self.from_python = None #TODO : wait for django 1.2 and new widget api to remove this hack

    def add_action(self, name, label, enabled=True, **kwargs):
        self.actions.append(self.Action(name, label, enabled, **kwargs))
        return self

    def clear_actions(self):
        self.actions = []
        return self

    def _render_actions(self):
        #output = []
        #output.extend(self._render_action(name, label, enabled, **attrs) for name, label, enabled, attrs in self.actions)

        #return '\n'.join(output)
        return '\n'.join(self._render_action(action) for action in self.actions)

    def _render_action(self, action):
        attrs = dict(action.attrs)

        if not action.enabled:
            attrs['disabled'] = u''

        title = attrs.pop('title', action.label)
        context = {'name':  action.name,
                   'attr':  flatatt(attrs),
                   'label': action.label,
                   'title': title,
                  }

        return u'<li><button class="ui-creme-actionbutton selectorlist-%(name)s" title="%(title)s" alt="%(title)s" type="button" %(attr)s>'\
                '    %(label)s'\
                '</button></li>' % context

    def render(self, name, value, attrs=None):
        value = self.from_python(value) if self.from_python is not None else value # TODO : wait for django 1.2 and new widget api to remove this hack
        attrs = self.build_attrs(attrs, name=name, type='hidden')
        clonelast = 'cloneLast' if attrs.pop('clonelast', True) else ''
        disabled = 'disabled' if not self.enabled else ''

        context = widget_render_context('ui-creme-selectorlist', attrs,
                                        add=_(u'Add'),
                                        clonelast=clonelast,
                                        disabled=disabled,
                                        selector=self.selector.render('', '', {'auto': False,'reset': False}))

        context['input'] = widget_render_hidden_input(self, name, value, context)
        context['img_url'] = media_url('images/add_16.png')
        context['actions'] = self._render_actions()

        return mark_safe('<div class="%(css)s" style="%(style)s" widget="%(typename)s" %(clonelast)s %(disabled)s>'\
                         '       %(input)s'\
                         '      <div class="inner-selector-model" style="display:none;">%(selector)s</div>'\
                         '       <ul class="selectors ui-layout"></ul>'\
                         '       <ul class="ui-layout hbox">%(actions)s</ul>'\
                         '</div>' % context)


class EntitySelector(TextInput):
    def __init__(self, content_type=None, attrs=None):
        super(EntitySelector, self).__init__(attrs)
        self.url = '/creme_core/list_view/popup/' + content_type + '/${selection}?q_filter=${qfilter}' if content_type else \
                   '/creme_core/list_view/popup/${ctype}/${selection}?q_filter=${qfilter}'
        self.text_url = '/creme_core/relation/entity/${id}/json'

    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name, type='hidden')
        selection_mode = '0' if attrs.pop('multiple', False) else '1'
        autoselect_mode = 'popupAuto' if attrs.pop('autoselect', False) else ''

        context = widget_render_context('ui-creme-entityselector', attrs,
                                        url=self.url,
                                        text_url=self.text_url,
                                        selection=selection_mode,
                                        autoselect=autoselect_mode,
                                        style=attrs.pop('style', ''),
                                        label=_(u'Select...'),
                                       )

        context['input'] = widget_render_hidden_input(self, name, value, context)

        qfilter = attrs.pop('qfilter', None)
        context['qfilter'] = escape(JSONEncoder().encode(qfilter)) if qfilter else ''

        html_output = """
            <span class="%(css)s" style="%(style)s" widget="%(typename)s" 
                  labelURL="%(text_url)s" label="%(label)s"
                  popupURL="%(url)s" popupSelection="%(selection)s" %(autoselect)s
                  qfilter="%(qfilter)s">
                %(input)s
                <button type="button">%(label)s</button>
            </span>
        """ % context

        return mark_safe(html_output)


class CTEntitySelector(ChainedInput):
    def __init__(self, content_types, attrs=None, multiple=False, autocomplete=False):
        super(CTEntitySelector, self).__init__(attrs)

        self.add_dselect("ctype", options=content_types, attrs={'auto': False, 'autocomplete': True} if autocomplete else {'auto': False})
        self.add_input("entity", widget=EntitySelector, attrs={'auto': False, 'multiple':multiple})


class RelationSelector(ChainedInput):
    def __init__(self, relation_types, content_types, attrs=None, multiple=False, autocomplete=False):
        super(RelationSelector, self).__init__(attrs)

        dselect_attrs = {'auto': False, 'autocomplete': True} if autocomplete else {'auto': False}

        self.add_dselect("rtype", options=relation_types, attrs=dselect_attrs)
        self.add_dselect("ctype", options=content_types, attrs=dselect_attrs)
        self.add_input("entity", widget=EntitySelector, attrs={'auto': False, 'multiple': multiple})


class FilteredEntityTypeWidget(ChainedInput):
    def __init__(self, content_types, attrs=None, autocomplete=False):
        super(FilteredEntityTypeWidget, self).__init__(attrs)

        add_dselect = self.add_dselect
        attrs = {'auto': False, 'autocomplete': True} if autocomplete else {'auto': False}
        ctype_name = 'ctype'
        add_dselect(ctype_name, options=content_types, attrs=attrs)

        #TODO: 'all' as GET parameter ??
        #TODO: allow to omit the 'All' filter ??
        add_dselect('efilter', options='/creme_core/entity_filter/get_for_ctype/${%s}/all' % ctype_name, attrs=attrs)


class DateTimeWidget(TextInput):
    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name, type='hidden')

        return mark_safe("""
            <ul id="%(id)s_datetimepicker" class="ui-creme-datetimepicker">
                %(input)s
                <li>%(date_label)s</li>
                <li class="date"><input class="ui-corner-all" type="text" maxlength="12"/></li>
                <li>%(time_label)s</li>
                <li class="hour"><input class="ui-corner-all" type="text" maxlength="2"/></li>
                <li>%(hour_label)s</li>
                <li class="minute"><input class="ui-corner-all" type="text" maxlength="2"/></li>
                <li>%(minute_label)s</li>
                <li class="clear"><button type="button">%(clear_label)s</button></li>
                <li class="now"><button type="button">%(now_label)s</button></li>
            </ul>
            <script type="text/javascript">
                $('.ui-creme-datetimepicker#%(id)s_datetimepicker').each(function() {creme.forms.DateTimePicker.init($(this));});
            </script>""" % {
                'input':        super(DateTimeWidget, self).render(name, value, attrs),
                'date_label':   _(u'On'),
                'time_label':   _(u'at'),
                'hour_label':   _(u'h'), #TODO: improve i18n
                'minute_label': '',      #TODO: improve i18n
                'id':           attrs['id'],
                'clear_label':  _(u'Clean'),
                'now_label':    _(u'Now'),
              })


class TimeWidget(TextInput):
    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name, type='hidden')

        return mark_safe(
"""<ul id="%(id)s_timepicker" class="ui-creme-timepicker">
    %(input)s
    <li class="hour"><input class="ui-corner-all" type="text" maxlength="2"/></li>
    <li>%(hour_label)s</li>
    <li class="minute"><input class="ui-corner-all" type="text" maxlength="2"/></li>
    <li>%(minute_label)s</li>
    <li><button type="button">%(now_label)s</button></li>
</ul>
<script type="text/javascript">
    $('.ui-creme-timepicker#%(id)s_timepicker').each(function() {creme.forms.TimePicker.init($(this));});
</script>""" % {'input':        super(TimeWidget, self).render(name, value, attrs),
                'hour_label':   _(u'h'),
                'minute_label': '',
                'id':           attrs['id'],
                'now_label':    _(u'Now'),
              })

    def value_from_datadict(self, data, files, name):
        value = data.get(name, '')

        if value.strip() == ':':
            value = ''

        return value


class CalendarWidget(TextInput):
    is_localized = True
    default_help_text = settings.DATE_FORMAT_VERBOSE

    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name)
        context = widget_render_context('ui-creme-datepicker', attrs)
        dateformat = settings.DATE_FORMAT_JS.get(settings.DATE_FORMAT)

        return mark_safe(u"""<div>%(help_text)s</div>%(input)s""" % {
                                  'help_text': self.default_help_text,
                                  'input': widget_render_input(TextInput.render, self, name, value, context,
                                                               format=dateformat),
                              })

        #be carefull: JS and python date format should be equal (here: date == "yy-mm-dd")
#        if isinstance(value, datetime):
#            # TODO cremedatetimefield is not working properly for the moment
#            self.default_help_text = settings.DATE_FORMAT_VERBOSE
#            value = value.date()
#
##        value = date_format(value, 'DATE_FORMAT') if value is not None else None
#        attrs = self.build_attrs(attrs, name=name)
#
#        date_format_js = settings.DATE_FORMAT_JS.get(settings.DATE_FORMAT)
#        dates_js = {
#            'dd': 'd.getDate()',
#            'mm': '(d.getMonth()+1)',
#            'yy': 'd.getFullYear()',
#        }
#
#        cmd_js = []
#        for f in date_format_js.split(settings.DATE_FORMAT_JS_SEP):
#            cmd_js.append(dates_js.get(f))
#
#        return mark_safe(u"""<div class="ui-creme-calendarpicker">
#                %(help_text)s
#                <br/>
#                <ul class="ui-layout hbox">
#                    <li>%(input)s</li>
#                    <li>
#                        <button type="button" onclick="d=new Date();$('#%(id)s').val(%(today_js)s);">
#                            %(today_label)s
#                        </button>
#                    </li>
#                </ul>
#            </div>
#            <script type="text/javascript">
#                $("#%(id)s").datepicker({dateFormat: "%(date_format_js)s", 
#                                         showOn: "button", 
#                                         buttonText: "%(img_text)s",
#                                         buttonImage: "%(img_url)s", 
#                                         buttonImageOnly: true });
#            </script>""" % {
#                    'input':           super(CalendarWidget, self).render(name, value, attrs),
#                    'id':              attrs['id'],
#                    'today_label':     _(u"Today"),
#                    'date_format_js':  date_format_js,
#                    'today_js':        ("+'%s'+" % settings.DATE_FORMAT_JS_SEP).join(cmd_js),
#                    'help_text':       self.default_help_text,
#                    'img_url':         media_url('images/icon_calendar.gif'),
#                    'img_text':        _(u'Calendar')
#                  })

#TODO: Only used in reports for now. Kept until *Selector widgets accept optgroup
class DependentSelect(Select):
    def __init__(self, target_id, attrs=None, choices=()):
        self.target_id   = target_id
        self.target_url  = None
        self._source_val = self._target_val = None
        super(DependentSelect, self).__init__(attrs, choices)

    def _set_target(self, target):
        self._target_val = target
    target_val = property(lambda self: self._target_val, _set_target); del _set_target

    def _set_source(self, source):
        self._source_val = source
    source_val = property(lambda self: self._source_val, _set_source); del _set_source

    def render(self, name, value, attrs=None, choices=()):
        attrs = self.build_attrs(attrs, name=name)
        id = attrs['id']
        script = """(function(){
                        var source = $('#%(id)s');
                        if(!source || typeof(source) == 'undefined') return;
                        var target = $('#%(target_id)s');
                        if(!target || typeof(target) == 'undefined') return;
                        $.post('%(target_url)s',
                               {record_id : source.val()},
                               function(data){
                                var data = creme.forms.Select.optionsFromData(data.result, 'text', 'id');
                                creme.forms.Select.fill(target, data, '%(target_val)s');
                               } , 'json');
        }());""" % {
            'id': id,
            'target_id': self.target_id,
            'target_url': self.target_url,
            'target_val': self.target_val

        }
        attrs['onchange'] = script

        return mark_safe("""
            <script type="text/javascript">
                $("#%(id)s").change();
            </script>
            %(input)s
        """ % {'input':super(DependentSelect, self).render(name, value, attrs, choices), 'id': id})


#class UploadedFileWidget(FileInput):
    #def __init__(self, attrs=None):
        #super(UploadedFileWidget, self).__init__(attrs)

    #def render(self, name, value, attrs=None):
        #visual=''
        #attrs = self.build_attrs(attrs, name=name)

        #if value not in EMPTY_VALUES:
            #visual = """
            #<a href="/download_file/%(url)s">
                #<img src="%(media_url)s%(url)s" alt="%(url)s"/>
            #</a>""" % {
                    #'url': value,
                    #'media_url': settings.MEDIA_URL
                #}
            #attrs['type'] = 'hidden'

        #input = super(UploadedFileWidget, self).render(name, value, attrs)
        #return mark_safe(input + visual)


class TinyMCEEditor(Textarea):
    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name)
        context = widget_render_context('ui-creme-jqueryplugin', attrs)

        plugin_options = JSONEncoder().encode({
            "mode": "textareas",
            "script_url": '%stiny_mce/tiny_mce.js' % settings.MEDIA_URL,
            "convert_urls": False,
            "theme": "advanced",
            "height": 300,
            "plugins": "spellchecker,pagebreak,style,layer,table,save,advhr,advimage,advlink,emotions,iespell,inlinepopups,insertdatetime,preview,media,searchreplace,print,contextmenu,paste,directionality,fullscreen,noneditable,visualchars,nonbreaking,xhtmlxtras,template, fullpage",
            "theme_advanced_buttons1": "save,newdocument,|,bold,italic,underline,strikethrough,|,justifyleft,justifycenter,justifyright,justifyfull,|,styleselect,formatselect,fontselect,fontsizeselect",
            "theme_advanced_buttons2": "cut,copy,paste,pastetext,pasteword,|,search,replace,|,bullist,numlist,|,outdent,indent,blockquote,|,undo,redo,|,link,unlink,anchor,image,cleanup,code,|,insertdate,inserttime,preview,|,forecolor,backcolor",
            "theme_advanced_buttons3": "tablecontrols,|,hr,removeformat,visualaid,|,sub,sup,|,charmap,emotions,iespell,media,advhr,|,print,|,ltr,rtl,|,fullscreen",
            "theme_advanced_buttons4": "insertlayer,moveforward,movebackward,absolute,|,styleprops,spellchecker,|,cite,abbr,acronym,del,ins,attribs,|,visualchars,nonbreaking,blockquote,pagebreak,|,insertfile,insertimage",
            "theme_advanced_toolbar_location": "top",
            "theme_advanced_toolbar_align": "left",
            "theme_advanced_path_location": "bottom",
            "theme_advanced_resizing": True,
        })

        return mark_safe(widget_render_input(Textarea.render, self, name, value, context, 
                                             plugin='tinymce', 
                                             plugin_options=plugin_options))

#        rendered = super(TinyMCEEditor, self).render(name, value, attrs)
##        extended_valid_elements : "a[name|href|target|title|onclick]",
##        script_url : '%(MEDIA_URL)stiny_mce/tiny_mce_src.js',
#        return mark_safe(u'''%(input)s
#                            <script type="text/javascript" src="%(MEDIA_URL)stiny_mce/jquery.tinymce.js"></script>
#                            <script type="text/javascript">
#                                jQuery('#id_%(name)s').tinymce({
#                                    mode : "textareas",
#                                    script_url : '%(MEDIA_URL)stiny_mce/tiny_mce.js',
#                                    convert_urls : false,
#                                    theme : "advanced",
#                                    height: 300,
#                                    plugins : "spellchecker,pagebreak,style,layer,table,save,advhr,advimage,advlink,emotions,iespell,inlinepopups,insertdatetime,preview,media,searchreplace,print,contextmenu,paste,directionality,fullscreen,noneditable,visualchars,nonbreaking,xhtmlxtras,template, fullpage",
#                                    theme_advanced_buttons1 : "save,newdocument,|,bold,italic,underline,strikethrough,|,justifyleft,justifycenter,justifyright,justifyfull,|,styleselect,formatselect,fontselect,fontsizeselect",
#                                    theme_advanced_buttons2 : "cut,copy,paste,pastetext,pasteword,|,search,replace,|,bullist,numlist,|,outdent,indent,blockquote,|,undo,redo,|,link,unlink,anchor,image,cleanup,code,|,insertdate,inserttime,preview,|,forecolor,backcolor",
#                                    theme_advanced_buttons3 : "tablecontrols,|,hr,removeformat,visualaid,|,sub,sup,|,charmap,emotions,iespell,media,advhr,|,print,|,ltr,rtl,|,fullscreen",
#                                    theme_advanced_buttons4 : "insertlayer,moveforward,movebackward,absolute,|,styleprops,spellchecker,|,cite,abbr,acronym,del,ins,attribs,|,visualchars,nonbreaking,blockquote,pagebreak,|,insertfile,insertimage",
#                                    theme_advanced_toolbar_location : "top",
#                                    theme_advanced_toolbar_align : "left",
#                                    theme_advanced_path_location : "bottom",
#                                    theme_advanced_resizing : true
#                                });
#                            </script>''' % {'MEDIA_URL': settings.MEDIA_URL, 'name': name, 'input': rendered})


class ColorPickerWidget(TextInput):
    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name)
        context = widget_render_context('ui-creme-jqueryplugin', attrs)

        return mark_safe(widget_render_input(TextInput.render, self, name, value, context, plugin='gccolor'))
#
#        return mark_safe("""<script type="text/javascript">
#                    $(document).ready(function() { $("#%(id)s").gccolor()});
#                </script>%(input)s""" % {
#                    'id':    attrs['id'],
#                    'input': super(ColorPickerWidget, self).render(name, value, attrs),
#                })


#class ListViewWidget(TextInput):
    #"""A list view many-to-many widget
    #Examples of usage in a form definition :
        #mailing_list = fields.CremeEntityField(required=False, model=MailingList, q_filter=None)
        #mailing_list = fields.MultiCremeEntityField(required=False, model=MailingList, q_filter=None)
    #@param q_filter Has to be a list of dict => {'pk__in':[1,2], 'name__contains':'toto'} or None
    #"""
    #def __init__(self, attrs=None, q_filter=None, model=None, separator=','):
        #warnings.warn("ListViewWidget class is deprecated.", DeprecationWarning)
        #super(ListViewWidget, self).__init__(attrs)
        #self.q_filter  = q_filter
        #self._o2m      = 1
        #self._model    = model
        #self._ct_id    = None if model is None else ContentType.objects.get_for_model(model).id
        #self.separator = separator

    #@property
    #def o2m(self):
        #return self._o2m

    #@o2m.setter
    #def o2m(self, o2m):
        #self._o2m = o2m

    #@property
    #def model(self):
        #return self._model

    #@model.setter
    #def model(self, model):
        #self._model = model
        #if model is not None:
            #self._ct_id = ContentType.objects.get_for_model(model).id

    #def render(self, name, value, attrs=None):
        #attrs = self.build_attrs(attrs, name=name)
        #attrs['o2m']   = self.o2m
        #attrs['ct_id'] = self._ct_id

        #id_input = attrs.get('id')

        #encode = JSONEncoder().encode

        #return mark_safe("""%(input)s
                #<script type="text/javascript">
                    #$(document).ready(function() {
                        #creme.lv_widget.init_widget('%(id)s','%(qfilter)s', %(js_attrs)s);
                        #creme.lv_widget.handleSelection(%(value)s, '%(id)s');
                    #});
                #</script>""" % {
                    #'input':    super(ListViewWidget, self).render(name, "", attrs),
                    #'id':       id_input,
                    #'qfilter':  encode(self.q_filter),
                    #'js_attrs': encode([{'name': k, 'value': v} for k, v in self.attrs.iteritems()]),
                    #'value':    encode(value),
                #})

    #def value_from_datadict(self, data, files, name):
        #value = data.get(name, None)

        #if value:
            #if self.separator in value:
                #return [v for v in data[name].split(self.separator) if v]

            #return [value]

        #return None


class UnorderedMultipleChoiceWidget(SelectMultiple):
    class Choice(object):
        def __init__(self, value, disabled=False, help=u''):
            self.value = value
            self.disabled = disabled
            self.help = help

    def __init__(self, attrs=None, choices=(), columntype='', filtertype=None):
        super(UnorderedMultipleChoiceWidget, self).__init__(attrs, choices)
        self.columntype = columntype
        self.filtertype = filtertype

    def render_unordered_choice(self, selected_choices, choice, option_label):
        # This code is part of method django.forms.widgets.Select.render_option()
        # ==========================
        option_value = force_unicode(choice.value)

        if option_value in selected_choices:
            selected_html = u' selected="selected"'
            if not self.allow_multiple_selected:
                # Only allow for a single selection.
                selected_choices.remove(option_value)
        else:
            selected_html = ''
        # ==========================

        disabled_html = u' disabled' if choice.disabled else u''
        help_html = u' help="%s"' % escape(choice.help) if choice.help else u''

        return u'<option value="%s"%s%s%s>%s</option>' % (escape(option_value),
                                                          selected_html,
                                                          disabled_html,
                                                          help_html,
                                                          conditional_escape(force_unicode(option_label)))

    def render_option(self, selected_choices, option_value, option_label):
        if isinstance(option_value, self.Choice):
            return self.render_unordered_choice(selected_choices, option_value, option_label)

        return super(UnorderedMultipleChoiceWidget, self).render_option(selected_choices, option_value, option_label)


    def render(self, name, value, attrs=None, choices=()):
        if not self.choices:
            return _('No choice available.')

        count = len(self.choices)
        attrs = self.build_attrs(attrs, name=name)
        filtertype = self._build_filtertype(count)
        input = SelectMultiple.render(self, name, value, {'class': 'ui-creme-input'}, choices);

        context = widget_render_context('ui-creme-checklistselect', attrs,
                                        body=self._render_body(attrs, filtertype),
                                        header=self._render_header(attrs, filtertype, count),
                                        counter=self._render_counter(attrs, filtertype),
                                        input=input)

        return mark_safe(
u"""<div class="%(css)s" style="%(style)s" widget="%(typename)s">
    %(input)s
    %(counter)s
    %(header)s
    %(body)s
</div>""" % context)

    def _build_filtertype(self, count):
        if self.filtertype:
            return self.filtertype

        if count < 10:
            return None

        if 10 < count < 30:
            return 'search'

        return 'filter'

    def _render_counter(self, attrs, filtertype):
        return '<span class="checklist-counter"></span>' if filtertype == "filter" else ''

    def _render_header(self, attrs, filtertype, count):
        has_checkall = attrs.get('checkall', True) and count > 2

        if not has_checkall and not filtertype:
            return ''

        filter = checkall = ''

        if filtertype:
            filtername = _('Filter') if filtertype == 'filter' else _('Search')
            filter = '<input type="search" class="checklist-filter" placeholder="%s">' % filtername.upper()

        if has_checkall:
            checkall = '<a type="button" class="checklist-check-all">%s</a>'\
                       ' | <a type="button" class="checklist-check-none">%s</a>' % (_(u'Check all'), _(u'Check none'))

        return '<div class="checklist-header">%(checkall)s%(filter)s</div>' % {
                   'filter': filter, 
                   'checkall': checkall,
               }

    def _render_body(self, attrs, filtertype):
        return '<ul class="checklist-content %s %s"></ul>' % (filtertype or '', self.columntype)

# TODO : remove it !
# class UnorderedMultipleChoiceWidget(SelectMultiple):
#     def render(self, name, value, attrs=None, choices=()):
#         attrs = self.build_attrs(attrs, name=name)
# 
#         reduced = attrs.get('reduced', 'false')
#         assert reduced in ('true', 'false')
# 
#         return mark_safe(u"""%(select)s
#                      <script type="text/javascript">
#                         $(document).ready(function() {
#                             creme.forms.toUnorderedMultiSelect('%(id)s', %(reduced)s);
#                         });
#                      </script>""" % {
#                         'select':  super(UnorderedMultipleChoiceWidget, self).render(name, value, attrs=attrs, choices=choices),
#                         'id':      attrs['id'],
#                         'reduced': reduced,
#                      })


class OrderedMultipleChoiceWidget(SelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = ()
        value_dict = {opt_value: order + 1 for order, opt_value in enumerate(value)}
        attrs = self.build_attrs(attrs, name=name)

        reduced = attrs.get('reduced', 'false')
        assert reduced in ('true', 'false')

        output = [u'<table %s><tbody>' % flatatt(attrs)]

        for i, (opt_value, opt_label) in enumerate(chain(self.choices, choices)):
            order = value_dict.get(opt_value, '')

            output.append(
u"""<tr name="oms_row_%(i)s">
    <td><input class="oms_check" type="checkbox" name="%(name)s_check_%(i)s" %(checked)s/></td>
    <td class="oms_value">%(label)s<input type="hidden" name="%(name)s_value_%(i)s" value="%(value)s" /></td>
    <td><input class="oms_order" type="text" name="%(name)s_order_%(i)s" value="%(order)s"/></td>
</tr>""" % {'i':        i,
            'label':    escape(opt_label),
            'name':     name,
            'value':    opt_value,
            'checked':  'checked' if order else '',
            'order':    order,
            })

        output.append(
u"""</tbody></table>
<script type="text/javascript">
    $(document).ready(function() {
        creme.forms.toOrderedMultiSelect('%(id)s', %(reduced)s);
    });
</script>""" % {'id':      attrs['id'],
                'reduced': reduced,
               })

        return mark_safe(u'\n'.join(output))

    def value_from_datadict(self, data, files, name):
        prefix_check = '%s_check_' % name
        prefix_order = '%s_order_' % name
        prefix_value = '%s_value_' % name

        selected = []
        for key, value in data.iteritems():
            if key.startswith(prefix_check):
                index = key[len(prefix_check):] #in fact not an int...
                order = int(data.get(prefix_order + index) or 0)
                value = data[prefix_value + index]
                selected.append((order, value))

        selected.sort(key=lambda i: i[0])

        return [val for order, val in selected]


class Label(TextInput):
    empty_label = None

    def __init__(self, attrs=None, empty_label=None):
        TextInput.__init__(self, attrs=attrs)
        self.empty_label = empty_label

    def render(self, name, value, attrs=None):
        return mark_safe(u'%(input)s<span %(attrs)s>%(content)s</span>' % {
                'input':   super(Label, self).render(name, value, {'style': 'display:none;'}),
                'attrs':   flatatt(self.build_attrs(attrs, name=name)),
                'content': conditional_escape(force_unicode(value if value is not None else self.empty_label)),
            })


class ListEditionWidget(Widget):
    content = ()
    only_delete = False

    def render(self, name, value, attrs=None, choices=()):
        output = [u'<table %s><tbody>' % flatatt(self.build_attrs(attrs, name=name))]
        row = u"""<tr>
                    <td><input type="checkbox" name="%(name)s_check_%(i)s" %(checked)s/></td>
                    <td><input type="text" name="%(name)s_value_%(i)s" value="%(label)s" style="display:none;"/><span>%(label)s</span></td>
                  </tr>""" if self.only_delete \
            else u"""<tr>
                        <td><input type="checkbox" name="%(name)s_check_%(i)s" %(checked)s/></td>
                        <td><input type="text" name="%(name)s_value_%(i)s" value="%(label)s"/></td>
                     </tr>"""

        for i, label in enumerate(self.content):
            checked = 'checked'

            if value:
                new_label = value[i]

                if new_label is None:
                    checked = ''
                else:
                    label = new_label

            output.append(row  % {'i':        i,
                                  'name':     name,
                                  'label':    escape(label),
                                  'checked':  checked,
                                 }
                         )

        output.append(u'</tbody></table>')

        return mark_safe(u'\n'.join(output))

    def value_from_datadict(self, data, files, name):
        prefix_check = name + '_check_%i'
        prefix_value = name + '_value_%i'
        get     = data.get
        has_key = data.has_key

        return [get(prefix_value % i) if has_key(prefix_check % i) else None
                    for i in xrange(len(self.content))
               ]


class AdaptiveWidget(Select):
    def __init__(self, ct_id, object_id="", attrs=None, choices=()):
        super(AdaptiveWidget, self).__init__(attrs, choices)
        self.ct_id = ct_id
        self.object_id = object_id
        self.url = "/creme_core/entity/get_widget/%s" % ct_id

    def render(self, name, value, attrs=None, choices=()):
        attrs = self.build_attrs(attrs, name=name)
        context = widget_render_context('ui-creme-adaptive-widget', attrs,
                                        url=self.url,
                                        object_id=self.object_id,
                                        style=attrs.pop('style', ''),
                                       )
        context['input'] = super(AdaptiveWidget, self).render(name, value, attrs, choices)

        return mark_safe('<span class="%(css)s" style="%(style)s" widget="%(typename)s" '
                               'url="%(url)s" object_id="%(object_id)s">'
                            '%(input)s'
                         '</span>' % context
                        )


class DatePeriodWidget(MultiWidget):
    def __init__(self, choices=(), attrs=None):
        widgets = (Select(choices=choices, attrs={'class': 'dperiod-type'}),
                   TextInput(attrs={'class': 'dperiod-value'}), #TODO: min_value
                  )
        super(DatePeriodWidget, self).__init__(widgets, attrs)

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

    def format_output(self, rendered_widgets):
        return u'<ul class="ui-layout hbox">%s</ul>' % (
                    _('%(dateperiod_value)s%(dateperiod_type)s') % {
                            'dateperiod_type':  u'<li>%s</li>' % rendered_widgets[0],
                            'dateperiod_value': u'<li>%s</li>' % rendered_widgets[1],
                        }
                )


class DateRangeWidget(MultiWidget):
    def __init__(self, attrs=None):
        self.render_as = attrs.pop('render_as', 'table') if attrs else 'table'

        widgets = (Select(choices=chain([(u'', _(u'Customized'))], date_range_registry.choices()), attrs={'class': 'range-type'}),
                   CalendarWidget(attrs={'class': 'date-start'}),
                   CalendarWidget(attrs={'class': 'date-end'}),
                  )
        super(DateRangeWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return value[0], value[1], value[2]
        return None, None, None

    def format_output(self, rendered_widgets):
        _css_class = "ui-creme-daterange" #TODO: inline ?
        context = widget_render_context('ui-creme-daterange', {})

        if self.render_as == 'table':
            return u"".join([u'<table class="%(css)s" style="%(style)s" widget="%(typename)s"><tbody><tr>' % context,
                             u''.join(u'<td>%s</td>' % w for w in rendered_widgets),
                             u'</tr></tbody></table>'
                            ])
        elif self.render_as == 'ul':
            return u"".join([u'<ul class="%(css)s" style="%(style)s" widget="%(typename)s">' % context,
                             u''.join(u'<li>%s</li>' % w for w in rendered_widgets),
                             u'</ul>'
                            ])

        return u'<div class="%s">%s</div>' % (_css_class, u''.join(u'<div>%s</div>' % w for w in rendered_widgets))


class DurationWidget(MultiWidget):
    def __init__(self, attrs=None):
        widgets = (TextInput(),
                   TextInput(),
                   TextInput()
                  )
        super(DurationWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return value.split(':')
        return None, None, None

    def format_output(self, rendered_widgets):
        hours_widget, minutes_widget, seconds_widget = rendered_widgets
        return u"""<span>%(hours)s&nbsp;%(hours_label)s&nbsp;
                         %(minutes)s&nbsp;%(minutes_label)s&nbsp;
                         %(seconds)s&nbsp;%(seconds_label)s&nbsp;</span>
                """ % {'hours':   hours_widget,   'hours_label':   _(u'Hour(s)'),
                       'minutes': minutes_widget, 'minutes_label': _(u'Minute(s)'),
                       'seconds': seconds_widget, 'seconds_label': _(u'Second(s)'),
                      }


class ChoiceOrCharWidget(MultiWidget):
    def __init__(self, attrs=None, choices=()):
        self.select_widget = select = Select(choices=choices)
        super(ChoiceOrCharWidget, self).__init__((select, TextInput()), attrs)

    @property
    def choices(self):
        return self.select_widget.choices

    @choices.setter
    def choices(self, choices):
        self.select_widget.choices = choices

    def decompress(self, value):
        if value:
            return value[0], value[1]

        return None, None

    #def format_output(self, rendered_widgets):
        #return u'<div>%s</div>' % (u''.join(u'<div>%s</div>' % w for w in rendered_widgets))


class CremeRadioFieldRenderer(RadioFieldRenderer):
    def render(self):
        return mark_safe(u'<ul class="radio_select">\n%s\n</ul>' %
                            u'\n'.join(u'<li>%s</li>' % force_unicode(w) for w in self)
                        )


class CremeRadioSelect(RadioSelect):
    renderer = CremeRadioFieldRenderer
