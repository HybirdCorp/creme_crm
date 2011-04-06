# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from datetime import datetime
from itertools import chain

from django.forms.widgets import Widget, Textarea, Select, SelectMultiple, FileInput, TextInput, Input
from django.forms.util import flatatt
from django.utils.html import conditional_escape, escape
from django.utils.translation import ugettext as _
from django.utils.encoding import force_unicode
from django.utils.simplejson.encoder import JSONEncoder
from django.utils.safestring import mark_safe
from django.utils.formats import date_format
from django.conf import settings

from mediagenerator.utils import media_url


def widget_render_input(klass, widget, name, value, context, **kwargs):
    input_attrs = {
                     'class':  ' '.join(['ui-creme-input', context.get('css')]),
                     'widget': context.get('typename'),
                  }
    input_attrs.update(kwargs)

    return klass.render(widget, name, value, input_attrs)

def widget_render_hidden_input(widget, name, value, context):
    input_attrs = {
                    'class': ' '.join(['ui-creme-input', context.get('typename')]),
                    'type':  'hidden',
                   }

    return Input.render(widget, name, value, input_attrs)

def widget_render_context(typename, attrs, css='', **kwargs):
    id   = attrs.get('id')
    auto = attrs.pop('auto', True)
    css = ' '.join((css, 'ui-creme-widget widget-auto' if auto else 'ui-creme-widget', typename))
    context = {
                'style':      '',
                'typename':   typename,
                'css':        css,
                'auto':       auto,
                'id':         id,
             }

    context.update(kwargs)

    return context


class DynamicSelect(Select):
    def __init__(self, attrs=None, options=None, url=''):
        super(DynamicSelect, self).__init__(attrs, options if options else ())
        self.url = url

    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name)
        context = widget_render_context('ui-creme-dselect', attrs)

        return mark_safe(widget_render_input(Select, self, name, value, context, url=self.url))


class ChainedInput(TextInput):
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
        self.inputs.append((name, widget(attrs=attrs, **kwargs)))

    def _render_inputs(self, attrs):
        output = ['<ul class="ui-layout hbox">']

        output.extend('<li chained-name="%s">%s</li>' % (name, input.render('', ''))
                         for name, input in self.inputs
                     )

        if attrs.pop('reset', True):
            output.append("""<li>
                                 <img class="reset" src="%s" alt="%s" title="%s"></img>
                             </li>""" % (media_url('images/delete_22.png'), _(u'Reset'), _(u'Reset')))

        output.append('</ul>')

        return '\n'.join(output)


class SelectorList(TextInput):
    def __init__(self, selector, attrs=None):
        super(SelectorList, self).__init__(attrs)
        self.selector = selector
        self.from_python = None #TODO : wait for django 1.2 and new widget api to remove this hack

    def render(self, name, value, attrs=None):
        value = self.from_python(value) if self.from_python is not None else value # TODO : wait for django 1.2 and new widget api to remove this hack
        attrs = self.build_attrs(attrs, name=name, type='hidden')

        context = widget_render_context('ui-creme-selectorlist', attrs,
                                        add=_(u'Add'),
                                        selector=self.selector.render('', '', {'auto':False,'reset':False}))

        context['input'] = widget_render_hidden_input(self, name, value, context)
        context['img_url'] = media_url('images/add_16.png')

        return mark_safe("""<div class="%(css)s" style="%(style)s" widget="%(typename)s">
                                %(input)s
                                <div class="inner-selector-model" style="display:none;">%(selector)s</div>
                                <ul class="selectors ui-layout"></ul>
                                <div class="add">
                                    <ul class="ui-layout hbox">
                                        <li><img src="%(img_url)s" alt="%(add)s" title="%(add)s"/></li>
                                        <li><span>%(add)s</span></li>
                                    </ul>
                                </div>
                            </div>""" % context)


class EntitySelector(TextInput):
    def __init__(self, content_type=None, attrs=None):
        super(EntitySelector, self).__init__(attrs)
        self.url = '/creme_core/lv_popup/' + content_type if content_type else '/creme_core/lv_popup/${ctype}'
        self.text_url = '/creme_core/relation/entity/${id}/json'

    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name, type='hidden')

        context = widget_render_context('ui-creme-entityselector', attrs,
                                        url=self.url,
                                        text_url=self.text_url,
                                        multiple='1' if attrs.pop('multiple', False) else '0',
                                        style=attrs.pop('style', ''),
                                        label=_(u'Select...'))

        context['input'] = widget_render_hidden_input(self, name, value, context)

        html_output = """
            <span class="%(css)s" style="%(style)s" widget="%(typename)s" url="%(url)s" multiple="%(multiple)s">
                %(input)s
                <button type="button" url="%(text_url)s" label="%(label)s">%(label)s</button>
            </span>
        """ % context;

        return mark_safe(html_output)


class CTEntitySelector(ChainedInput):
    def __init__(self, content_types, attrs=None, multiple=False):
        super(CTEntitySelector, self).__init__(attrs)

        self.add_dselect("ctype", options=content_types, attrs={'auto':False})
        self.add_input("entity", widget=EntitySelector, attrs={'auto':False, 'multiple':multiple})

#    def render(self, name, value, attrs=None):
#        return super(CTEntitySelector, self).render(name, value, attrs)

class RelationSelector(ChainedInput):
    def __init__(self, relation_types, content_types, attrs=None, multiple=False):
        super(RelationSelector, self).__init__(attrs)

        self.add_dselect("rtype", options=relation_types, attrs={'auto':False})
        self.add_dselect("ctype", options=content_types, attrs={'auto':False})
        self.add_input("entity", widget=EntitySelector, attrs={'auto':False, 'multiple':multiple})

#    def render(self, name, value, attrs=None): #TODO: useful ??
#        return super(RelationSelector, self).render(name, value, attrs)

#COMMENTED on 6 april 2011
#class EntitySelectorList(SelectorList):
#    def __init__(self, attrs=None):
#        super(EntitySelectorList, self).__init__(attrs)
#        self.selector = EntitySelector
#
#    def render(self, name, value, attrs=None):
#        attrs = self.build_attrs(attrs, name=name, type='hidden')
#
#        context = widget_render_context('ui-creme-selectorlist', attrs,
#                                        add='Ajouter',
#                                        selector=self.selector.render(name, value, {'auto':False,}))
#
#        context['input'] = widget_render_hidden_input(self, name, value, context)
#        context['img_url'] = media_url('images/add_16.png')
#
#        return mark_safe("""
#            <div id="%(id)s" class="%(css)s" style="%(style)s" widget="%(typename)s">
#                %(input)s
#                <div class="inner-selector-model" style="display:none;">%(selector)s</div>
#                <ul class="selectors ui-layout"></ul>
#                <div class="add">
#                    <img src="%(img_url)s" alt="%(add)s" title="%(add)s"/>
#                    %(add)s
#                </div>
#                %(script)s
#            </div>
#        """ % context)


#COMMENTED on 6 april 2011
#class RelationListWidget(TextInput):
#    def __init__(self, attrs=None, relation_types=()):
#        super(RelationListWidget, self).__init__(attrs)
#        self.relation_types = relation_types
#
#    def render(self, name, value, attrs=None):
#        attrs = self.build_attrs(attrs, name=name, type='hidden')
#
#        self.relation_types = sorted(self.relation_types, key=lambda k: k.predicate)#TODO: Replace with _(k.predicate) when predicate will be traducted
#
#        html_output = """%(input)s
#            <div id="%(id)s_list" class="ui-creme-rel-selector-list" widget-input="%(id)s">
#                %(predicates)s
#                <div class="list"></div>
#                <div onclick="creme.forms.RelationList.appendSelector($('#%(id)s_list'));" class="add">
#                    <img src="%(img_url)s" alt="%(title)s" title="%(title)s"/>
#                    %(title)s
#                </div>
#            </div>
#            <script type="text/javascript">
#                $('.ui-creme-rel-selector-list#%(id)s_list').each(function() {
#                    creme.forms.RelationList.init($(this));
#                });
#            </script>""" % {
#                'img_url':   media_url('images/add_16.png'),
#                'input':      super(RelationListWidget, self).render(name, value, attrs),
#                'title':      _(u'Add'),
#                'id':         attrs['id'],
#                'predicates': self.render_options('predicates'),
#              }
#
#        return mark_safe(html_output)
#
#    def render_options(self, css):
#        output = ['<select style="display:none;" class="%s">' % css]
#        output.extend(u'<option value="%s">%s</option>' % (rt.id, rt.predicate) for rt in self.relation_types)
#        output.append('</select>')
#
#        return u''.join(output)
#
#    def set_predicates(self, predicates):
#        self.predicates = predicates


class DateTimeWidget(TextInput):
    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name, type='hidden')

        return mark_safe("""
            <ul id="%(id)s_datetimepicker" class="ui-creme-datetimepicker" style="list-style:none;margin:0;padding:0;">
                %(input)s
                <li>%(date_label)s&nbsp;</li>
                <li class="date"><input class="ui-corner-all" type="text" maxlength="12"/></li>
                <li>&nbsp;%(time_label)s&nbsp;</li>
                <li class="hour"><input class="ui-corner-all" type="text" maxlength="2"/></li>
                <li>&nbsp;%(hour_label)s&nbsp;</li>
                <li class="minute"><input class="ui-corner-all" type="text" maxlength="2"/></li>
                <li>&nbsp;%(minute_label)s</li>
                <li class="clear"><button type="button">%(clear_label)s</button></li>
                <li class="now last"><button type="button">%(now_label)s</button></li>
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

        return mark_safe("""
            <ul id="%(id)s_timepicker" class="ui-creme-timepicker" style="list-style:none;margin:0;padding:0;">
                %(input)s
                <li class="hour"><input class="ui-corner-all" type="text" maxlength="2"/></li>
                <li>&nbsp;%(hour_label)s&nbsp;</li>
                <li class="minute"><input class="ui-corner-all" type="text" maxlength="2"/></li>
                <li>&nbsp;%(minute_label)s</li>
                <li class="last"><button type="button">%(now_label)s</button></li>
            </ul>
            <script type="text/javascript">
                $('.ui-creme-timepicker#%(id)s_timepicker').each(function() {creme.forms.TimePicker.init($(this));});
            </script>""" % {
                'input':        super(TimeWidget, self).render(name, value, attrs),
                'hour_label':   _(u'h'),
                'minute_label': '',
                'id':           attrs['id'],
                'now_label':    _(u'Now'),
              })


class CalendarWidget(TextInput):
    is_localized = True
    default_help_text = settings.DATE_FORMAT_VERBOSE

    def render(self, name, value, attrs=None):
        #be carefull: JS and python date format should be equal (here: date == "yy-mm-dd")
        if isinstance(value, datetime):
            self.default_help_text = settings.DATETIME_FORMAT_VERBOSE
            value = value.date()

#        value = date_format(value, 'DATE_FORMAT') if value is not None else None
        attrs = self.build_attrs(attrs, name=name)

        date_format_js = settings.DATE_FORMAT_JS.get(settings.DATE_FORMAT)
        dates_js = {
            'dd': 'd.getDate()',
            'mm': '(d.getMonth()+1)',
            'yy': 'd.getFullYear()',
        }

        cmd_js = []
        for f in date_format_js.split(settings.DATE_FORMAT_JS_SEP):
            cmd_js.append(dates_js.get(f))

        #if hasattr(self, 'help_text') and self.help_text not in ('', u'', None):
        help_text = getattr(self, 'help_text', None)
        if help_text:
            help_text = _(help_text)
        else:
            help_text = _(self.default_help_text)

        return mark_safe("""%(help_text)s
            <br/>
            %(input)s
            <button type="button" onclick="d=new Date();$('#%(id)s').val(%(today_js)s);">
                %(today_label)s
            </button>
            <script type="text/javascript">
                $("#%(id)s").datepicker({dateFormat: "%(date_format_js)s", showOn: "button", buttonImage: "%(img_url)s", buttonImageOnly: true });
            </script>""" % {
                    'input':          super(CalendarWidget, self).render(name, value, attrs),
                    'id':             attrs['id'],
                    'today_label':    _(u"Today"),
                    'date_format_js': date_format_js,
                    'today_js':       ("+'%s'+" % settings.DATE_FORMAT_JS_SEP).join(cmd_js),
                    'help_text':      help_text,
                    'img_url':        media_url('images/icon_calendar.gif'),
                  })


#TODO: refactor
class DependentSelect(Select):
    def __init__(self, target_id, target_url, attrs=None, choices=()):
        self.target_id = target_id
        self.target_url = target_url
        super(DependentSelect, self).__init__(attrs, choices)

    def set_target(self, target):
        self.target_val = target

    def set_source(self, source):
        self.source_val = source

    def render(self, name, value, attrs=None, choices=()):
        if attrs is not None :
            if attrs.has_key('id') :
                id = attrs['id']
            else :
                id = "id_%s" % name
                attrs['id'] = id
        else :
            id = "id_%s" % name
            attrs = {"id" : id}
        script = '<script>'
        script += "function change_%s () {" % (id)
        script += "var source = $('#%s');" % id
        script += "if(!source || typeof(source) == 'undefined') return;"
        script += "var target = $('#%s');" % self.target_id
        script += "if(!target || typeof(target) == 'undefined') return;"
        script += "$.post('%s', {record_id : source.val()}, " % (self.target_url)
        script += "      function(data){"
        script += "         target.empty();"
        script += "         var result = data['result'];"
        script += "         for(var option in result)"
        script += "         {"
        if not hasattr(self, "source_val") or not hasattr(self, "target_val"): #TODO: un peu beurk...
            script += "             target.append('<option value='+result[option][\"id\"]+'>'+result[option][\"text\"]+'</option>');"
        else :
            script += "             if(result[option]['id'] == %s){" % self.target_val
            script += "                 target.append('<option selected=\"selected\" value='+result[option][\"id\"]+'>'+result[option][\"text\"]+'</option>');"
            script += "             }"
            script += "             else {"
            script += "                     target.append('<option value='+result[option][\"id\"]+'>'+result[option][\"text\"]+'</option>');"
            script += "             }"
        script += "         "
        script += "         "
        script += "         }"
        script += "      }, 'json');"
        script += '} '
#        if not hasattr(self, "source_val") or not hasattr(self, "target_val"):
        script += "$(document).ready(function(){change_%s ();});" % (id)

#        if hasattr(self, "source_val") and self.source_val is not None :
#            logging.debug("\n\n\nid : %s | source_val : %s\n\n\n" % (id,self.source_val))
#            script += "$(document).ready(function(){"
#            script += "$('#%s').val('%s');" % (id, self.source_val)
#            script += "});"
#        if hasattr(self, "target_val") and self.target_val is not None :
##            script += "console.log('avant2');"
##            script += "console.log('%s');" % self.target_val
#            script += "$(document).ready(function(){"
#            script += "$('#%s').val('%s');" % (self.target_id, self.target_val)
#            script += "});"
##            script += "console.log('apres2');"
#            logging.debug("\n\n\n id : %s | target_val : %s\n\n\n" % (self.target_id,self.target_val))


        script += '</script>'
        attrs['onchange'] = "change_%s ();" % (id)
        select = super(DependentSelect, self).render(name, value, attrs, choices)

        return mark_safe(select + script)


#TODO: refactor (build_attrs() etc...)
class UploadedFileWidget(FileInput):
    def __init__(self, url=None, attrs=None):
        self.url = url or None #???
        super(UploadedFileWidget, self).__init__(attrs)

    def original_render(self, name, value, attrs=None):
        if self.url is not None :
            input = '<a href="/download_file/%s">%s</a>' % (self.url, self.url)
#            input = mark_safe(u'<a href="/download_file/%s">%s</a>' % (self.url, self.url))
#            input = mark_safe(u'<a href="%s">%s</a>' % (url, url))
        else :
            input = super(UploadedFileWidget, self).render(name, value)
        return input

    def render(self, name, value, attrs=None):
        visual=''
        if self.url is not None :
            visual = '<a href="/download_file/%s">' % (self.url)
            visual += '<img src="%s%s" alt="%s"/></a>' % (settings.MEDIA_URL, self.url, self.url)

            if attrs is not None :
                attrs['type'] = 'hidden'
            else :
                attrs = {'type' : 'hidden'}
        input = super(UploadedFileWidget, self).render(name, value, attrs)
        return mark_safe(input + visual)

#TODO: Delete me (delete related js too)
class RTEWidget(Textarea):
    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name)

        return mark_safe("""<script type="text/javascript">
                    $(document).ready(function() { $("#%(id)s").rte(); });
                </script>
                %(textarea)s
                <input type="checkbox" id="%(id)s_is_rte_enabled" name="%(name)s_is_rte_enabled" style="display:none;" checked />
            """ % {
                    'id':       attrs['id'],
                    'name':     attrs['name'],
                    'textarea': super(RTEWidget, self).render(name, value, attrs),
                })


class TinyMCEEditor(Textarea):
    def render(self, name, value, attrs=None):
        rendered = super(TinyMCEEditor, self).render(name, value, attrs)
#        extended_valid_elements : "a[name|href|target|title|onclick]",
#        script_url : '%(MEDIA_URL)stiny_mce/tiny_mce_src.js',
        return mark_safe(u'''%(input)s
                            <script type="text/javascript" src="%(MEDIA_URL)stiny_mce/jquery.tinymce.js"></script>
                            <script type="text/javascript">
                                jQuery('#id_%(name)s').tinymce({
                                    mode : "textareas",
                                    script_url : '%(MEDIA_URL)stiny_mce/tiny_mce.js',
                                    convert_urls : false,
                                    theme : "advanced",
                                    height: 300,
                                    plugins : "spellchecker,pagebreak,style,layer,table,save,advhr,advimage,advlink,emotions,iespell,inlinepopups,insertdatetime,preview,media,searchreplace,print,contextmenu,paste,directionality,fullscreen,noneditable,visualchars,nonbreaking,xhtmlxtras,template, fullpage",
                                    theme_advanced_buttons1 : "save,newdocument,|,bold,italic,underline,strikethrough,|,justifyleft,justifycenter,justifyright,justifyfull,|,styleselect,formatselect,fontselect,fontsizeselect",
                                    theme_advanced_buttons2 : "cut,copy,paste,pastetext,pasteword,|,search,replace,|,bullist,numlist,|,outdent,indent,blockquote,|,undo,redo,|,link,unlink,anchor,image,cleanup,code,|,insertdate,inserttime,preview,|,forecolor,backcolor",
                                    theme_advanced_buttons3 : "tablecontrols,|,hr,removeformat,visualaid,|,sub,sup,|,charmap,emotions,iespell,media,advhr,|,print,|,ltr,rtl,|,fullscreen",
                                    theme_advanced_buttons4 : "insertlayer,moveforward,movebackward,absolute,|,styleprops,spellchecker,|,cite,abbr,acronym,del,ins,attribs,|,visualchars,nonbreaking,blockquote,pagebreak,|,insertfile,insertimage",
                                    theme_advanced_toolbar_location : "top",
                                    theme_advanced_toolbar_align : "left",
                                    theme_advanced_path_location : "bottom",
                                    theme_advanced_resizing : true
                                });
                            </script>''' % {'MEDIA_URL': settings.MEDIA_URL, 'name': name, 'input': rendered})


class ColorPickerWidget(TextInput):
    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name)

        return mark_safe("""<script type="text/javascript">
                    $(document).ready(function() { $("#%(id)s").gccolor(); });
                </script>%(input)s""" % {
                    'id':    attrs['id'],
                    'input': super(ColorPickerWidget, self).render(name, value, attrs),
                })


#TODO: refactor (build_attrs(), model/o2m set by the field etc....)
class ListViewWidget(TextInput):
    """A list view many-to-many widget
    Examples of usage in a form definition :
        mailing_list = fields.CremeEntityField(required=False, model=MailingList, q_filter=None)
        mailing_list = fields.MultiCremeEntityField(required=False, model=MailingList, q_filter=None)
    @param q_filter Has to be a list of dict => {'pk__in':[1,2], 'name__contains':'toto'} or None
    """
    def __init__(self, attrs=None, q_filter=None):
        super(ListViewWidget, self).__init__(attrs)
        self.q_filter = q_filter

    def render(self, name, value, attrs=None):
        #TODO: use build_attrs()
        id_input = self.attrs.get('id')
        if not id_input:
            id_input = 'id_%s' % name
            if not self.attrs:
                self.attrs = {'id' : id_input}
            else:
                self.attrs['id'] = id_input

        encode = JSONEncoder().encode

        #TODO : Improve me
        #TODO: factorise 'if value' ; what happens if 'value' is not string neither integer ??
        #TODO: isinstance(basestring, value) instead
        if(value and (type(value)==type("") or type(value)==type(u""))):#type(value)!=type([])):
            value = [v for v in value.split(',') if v]

        #TODO: isinstance(value, (int, long)) instead
        if(value and (type(value)==type(1) or type(value)==type(1L))):
            value = [value]

        return mark_safe("""%(input)s
                <script type="text/javascript">
                    $(document).ready(function() {
                        creme.lv_widget.init_widget('%(id)s','%(qfilter)s', %(js_attrs)s);
                        creme.lv_widget.handleSelection(%(value)s, '%(id)s');
                    });
                </script>""" % {
                    'input':    super(ListViewWidget, self).render(name, "", self.attrs),
                    'id':       id_input,
                    'qfilter':  encode(self.q_filter),
                    'js_attrs': encode([{'name': k, 'value': v} for k, v in self.attrs.iteritems()]),
                    'value':    encode(value),
                })


class UnorderedMultipleChoiceWidget(SelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        attrs = self.build_attrs(attrs, name=name)

        return mark_safe(u"""%(select)s
                     <script type="text/javascript">
                        $(document).ready(function() {
                            creme.forms.toUnorderedMultiSelect('%(id)s');
                        });
                     </script>""" % {
                        'select': super(UnorderedMultipleChoiceWidget, self).render(name, value, attrs=attrs, choices=choices),
                        'id':     attrs['id'],
                     })


class OrderedMultipleChoiceWidget(SelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = ()
        value_dict = dict((opt_value, order + 1) for order, opt_value in enumerate(value))
        attrs = self.build_attrs(attrs, name=name)

        output = [u'<table %s><tbody>' % flatatt(attrs)]

        for i, (opt_value, opt_label) in enumerate(chain(self.choices, choices)):
            order = value_dict.get(opt_value, '')

            output.append(u"""
                <tr name="oms_row_%(i)s">
                    <td><input class="oms_check" type="checkbox" name="%(name)s_check_%(i)s" %(checked)s/></td>
                    <td class="oms_value">%(label)s<input type="hidden" name="%(name)s_value_%(i)s" value="%(value)s" /></td>
                    <td><input class="oms_order" type="text" name="%(name)s_order_%(i)s" value="%(order)s"/></td>
                </tr>""" % {
                                'i':        i,
                                'label':    opt_label,
                                'name':     name,
                                'value':    opt_value,
                                'checked':  'checked' if order else '',
                                'order':    order,
                            })

        output.append(u"""</tbody></table>
                          <script type="text/javascript">
                              $(document).ready(function() {
                                  creme.forms.toOrderedMultiSelect('%s');
                              });
                          </script>""" % attrs['id'])

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
    def render(self, name, value, attrs=None):
        return mark_safe(u"""%(input)s<span %(attrs)s>%(content)s</span>""" % {
                'input':   super(Label, self).render(name, value, {'style': 'display:none;'}),
                'attrs':   flatatt(self.build_attrs(attrs, name=name)),
                'content': conditional_escape(force_unicode(value)),
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

            output.append(row  % {
                            'i':        i,
                            'name':     name,
                            'label':    label,
                            'checked':  checked,
                        })

        output.append(u"""</tbody></table>""")

        return mark_safe(u'\n'.join(output))

    def value_from_datadict(self, data, files, name):
        prefix_check = name + '_check_%i'
        prefix_value = name + '_value_%i'
        get     = data.get
        has_key = data.has_key

        return [get(prefix_value % i) if has_key(prefix_check % i) else None
                    for i in xrange(len(self.content))]


class DateFilterWidget(Select):
    def render(self, name, value, attrs=None, choices=()):
        rendered = super(DateFilterWidget, self).render(name, value, attrs=None, choices=())
        self_id = self.attrs.get('id')
        if self_id:
            rendered += """<script type="text/javascript">
                $(document).ready(function(){
                    $('#%(self_id)s').change(function(){
                        var $me = $(this);
                        var $selected = $(this).find(':selected');
                        $("#"+$me.attr('start_date_id')).val($selected.attr('begin'));
                        $("#"+$me.attr('end_date_id')).val($selected.attr('end'));
                    });
                });
            </script>""" % {
                'self_id' : self_id,
            }
        return mark_safe(rendered)

    def render_options(self, choices, selected_choices):
        def render_option(report_date_filter): #TODO: protected static method instead
            option_value = force_unicode(report_date_filter.name)
            selected_html = (option_value in selected_choices) and u' selected="selected"' or '' #TODO: conditional experession instead
            return u'<option value="%s"%s begin="%s" end="%s" is_volatile="%s">%s</option>' % ( #TODO: dict instead tuple ??
                escape(option_value), selected_html,
                report_date_filter.get_begin(),
                report_date_filter.get_end(),
                int(report_date_filter.is_volatile),
                conditional_escape(force_unicode(report_date_filter.verbose_name)))

        # Normalize to strings.
        selected_choices = set([force_unicode(v) for v in selected_choices])#TODO: genexpr
        output = []
        for report_date_filter in chain(self.choices, choices):
            output.append(render_option(report_date_filter))

        return u'\n'.join(output) #TODO: genexpr
