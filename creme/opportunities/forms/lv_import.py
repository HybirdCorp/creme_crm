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

from itertools import chain

from django.db.models import Max
from django.forms import Field, ModelChoiceField, ValidationError
from django.forms.util import flatatt
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from creme.creme_core.forms.list_view_import import (ImportForm4CremeEntity,
        ExtractorWidget, Extractor, EntityExtractorField)

from creme.persons.models import Organisation, Contact

from ..models import Opportunity, SalesPhase


# Sales phase management -------------------------------------------------------
#TODO: move 'order' management in SalesPhase.save() ??
class SalesPhaseExtractor(Extractor):
    def __init__(self, column_index, default_value, create_if_unfound):
        self._column_index  = column_index
        self._default_value = default_value
        self._create = create_if_unfound

    def extract_value(self, line):
        extracted = err_msg = None

        if self._column_index: #0 -> not in csv
            value = line[self._column_index - 1]

            if value:
                try:
                    extracted = SalesPhase.objects.get(name=value)
                except SalesPhase.DoesNotExist as e:
                    if self._create:
                        aggr = SalesPhase.objects.aggregate(Max('order'))
                        sales_phase = SalesPhase(name=value,
                                                 order=(aggr['order__max'] or 0) + 1,
                                                )
                        try:
                            sales_phase.full_clean()
                            sales_phase.save()
                        except Exception as e:
                            err_msg = _(u'Error while extracting value [%(raw_error)s]: '
                                         'tried to retrieve and then build "%(value)s" on %(model)s') % {
                                                'raw_error': e,
                                                'value':     value,
                                                'model':     SalesPhase._meta.verbose_name,
                                            }
                        else:
                            extracted = sales_phase
                    else:
                        err_msg = _(u'Error while extracting value [%(raw_error)s]: '
                                     'tried to retrieve "%(value)s" on %(model)s') % {
                                            'raw_error': e,
                                            'value':     value,
                                            'model':     SalesPhase._meta.verbose_name,
                                        }

            if not extracted:
                extracted = self._default_value

        return extracted, err_msg


class SalesPhaseExtractorWidget(ExtractorWidget):
    def __init__(self, *args, **kwargs):
        super(ExtractorWidget, self).__init__(*args, **kwargs)
        self.default_value_widget = None
        self.propose_creation = False

    def render(self, name, value, attrs=None, choices=()):
        value = value or {}
        attrs = self.build_attrs(attrs, name=name)

        try:
            sel_val = int(value.get('selected_column', -1))
        except TypeError:
            sel_val = 0

        if self.propose_creation:
            tag_class = disabled = ''
        else:
            tag_class = 'class=forbidden'
            disabled = 'disabled'

        return mark_safe('<table %(attrs)s>'
                            '<tbody>'
                                '<tr>'
                                    '<td>%(colselect)s</td>'
                                    '<td %(td_class)s>&nbsp;%(chk_label)s <input type="checkbox" name="%(name)s_create" %(checked)s %(chk_disabled)s></td>'
                                    '<td>&nbsp;%(defval_label)s:%(defval_widget)s</td>'
                                '</tr>'
                            '</tbody>'
                         '</table>' % {
            'name':          name,
            'attrs':         flatatt(self.build_attrs(attrs, name=name)),
            'colselect':     self._render_select("%s_colselect" % name,
                                                 choices=chain(self.choices, choices),
                                                 sel_val=sel_val,
                                                 attrs={'class': 'csv_col_select'},
                                                ),
            'td_class':       tag_class,
            'chk_label':     _(u'Create if not found ?'),
            'checked':       'checked' if value.get('create') else '',
            'chk_disabled':  disabled,
            'defval_label':  _('Default value'),
            'defval_widget': self.default_value_widget
                                 .render("%s_defval" % name, value.get('default_value')),
           })

    def value_from_datadict(self, data, files, name):
        get = data.get
        return {'selected_column':  get("%s_colselect" % name),
                'create':           get("%s_create" % name, False),
                'default_value':    self.default_value_widget.value_from_datadict(data, files, "%s_defval" % name) #TODO
               }


class SalesPhaseExtractorField(Field):
    def __init__(self, choices, modelform_field, *args, **kwargs):
        super(SalesPhaseExtractorField, self).__init__(widget=SalesPhaseExtractorWidget, *args, **kwargs)
        self._user = None
        self._can_create = False

        widget = self.widget
        widget.default_value_widget = modelform_field.widget
        widget.choices = choices

    @property
    def user(self, user):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user
        self.widget.propose_creation = self._can_create = user.has_perm_to_admin('opportunities')

    def clean(self, value):
        #TODO: factorise
        try:
            #TODO: check that col_index is in self._choices ???
            col_index = int(value['selected_column'])
        except TypeError:
            raise ValidationError(self.error_messages['invalid'])

        def_pk = value['default_value']
        def_value = None
        if def_pk:
            try:
                def_value = SalesPhase.objects.get(pk=def_pk)
            except Exception:
                pass #TODO: ValidationError

        if self.required and not col_index:
            if not def_value:
                raise ValidationError(self.error_messages['required'])

        want_create = value['create']

        if want_create and not self._can_create:
            raise ValidationError(u'You are not allowed to create "Sales phase"')

        return SalesPhaseExtractor(col_index, def_value, create_if_unfound=want_create)


# Main -------------------------------------------------------------------------
def get_csv_form_builder(header_dict, choices):
    class OpportunityCSVImportForm(ImportForm4CremeEntity):
        #TODO: can we improve ExtractorField to use form registered in creme_config when it is possible ?
        sales_phase = SalesPhaseExtractorField(choices, #modelfield
                                               Opportunity._meta.get_field_by_name('sales_phase')[0].formfield(),
                                               label=_('Sales phase'),
                                               #initial={'selected_column': selected_column} #TODO ??
                                              )
        target = EntityExtractorField([(Organisation, 'name'), (Contact, 'last_name')],
                                      choices, label=_('Target')
                                     )
        emitter = ModelChoiceField(label=_(u"Concerned organisation"), empty_label=None,
                                   queryset=Organisation.get_all_managed_by_creme(),
                                  )

        def _pre_instance_save(self, instance, line):
            cdata = self.cleaned_data

            if not instance.pk: #creation
                instance.emitter = cdata['emitter']

            target, err_msg = cdata['target'].extract_value(line, self.user)
            instance.target = target
            self.append_error(line, err_msg, instance) #error is really appenede if 'err_msg' is not empty


    return OpportunityCSVImportForm
