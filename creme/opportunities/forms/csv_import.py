# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from creme.creme_core.forms.list_view_import import ImportForm4CremeEntity, ExtractorWidget, Extractor

from creme.persons.models import Organisation, Contact

from ..models import Opportunity, SalesPhase


# Sales phase management -------------------------------------------------------
#TODO: move 'order' management in SalesPhase.save() ??
class SalesPhaseExtractor(Extractor):
    def __init__(self, column_index, default_value, create_if_unfound):
        self._column_index  = column_index
        self._default_value = default_value
        self._create = create_if_unfound

    def extract_value(self, line, import_errors):
        if not self._column_index: #0 -> not in csv
            return None

        value = line[self._column_index - 1]
        extracted = None

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
                        #TODO: factorise with parent ?
                        import_errors.append((line, _(u'Error while extracting value [%(raw_error)s]: tried to retrieve and then build "%(value)s" on %(model)s') % {
                                                            'raw_error': e,
                                                            'value': value,
                                                            'model': SalesPhase._meta.verbose_name,
                                                        }
                                            ))
                    else:
                        extracted = sales_phase
                else:
                    import_errors.append((line, _(u'Error while extracting value [%(raw_error)s]: tried to retrieve "%(value)s" on %(model)s') % {
                                                        'raw_error': e,
                                                        'value':     value,
                                                        'model':     SalesPhase._meta.verbose_name,
                                                    }
                                        ))
        if not extracted:
            extracted = self._default_value

        return extracted


class SalesPhaseExtractorWidget(ExtractorWidget):
    def __init__(self, *args, **kwargs):
        super(ExtractorWidget, self).__init__(*args, **kwargs)
        self.default_value_widget = None
        #self.propose_creation = False #TODO: use (credentials)

    def render(self, name, value, attrs=None, choices=()):
        value = value or {}
        attrs = self.build_attrs(attrs, name=name)
        output = [u'<table %s><tbody><tr><td>' % flatatt(attrs)]

        out_append = output.append

        try:
            sel_val = int(value.get('selected_column', -1))
        except TypeError:
            sel_val = 0

        out_append(self._render_select("%s_colselect" % name,
                                       choices=chain(self.choices, choices),
                                       sel_val=sel_val,
                                       attrs={'class': 'csv_col_select'}
                                      )
                  )
        out_append(u'</td><td>&nbsp;%s <input type="checkbox" name="%s_create" %s></td>' % (
                        _(u'Create if not found ?'),
                        name,
                        'checked' if value.get('create') else '',
                    ),
                  )
        out_append(u'<td>&nbsp;%s:%s</td></tr></tbody></table>' % (
                        _('Default value'),
                        self.default_value_widget.render("%s_defval" % name, value.get('default_value')),
                    )
                  )

        return mark_safe(u'\n'.join(output))

    def value_from_datadict(self, data, files, name):
        get = data.get
        return {'selected_column':  get("%s_colselect" % name),
                'create':           get("%s_create" % name, False),
                'default_value':    self.default_value_widget.value_from_datadict(data, files, "%s_defval" % name) #TODO
               }


class SalesPhaseExtractorField(Field):
    def __init__(self, choices, modelform_field, *args, **kwargs):
        super(SalesPhaseExtractorField, self).__init__(self, widget=SalesPhaseExtractorWidget, *args, **kwargs)
        #self._can_create = False  #TODO: creds

        widget = self.widget
        widget.default_value_widget = modelform_field.widget
        widget.choices = choices

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
                pass

        if self.required and not col_index:
            if not def_value:
                raise ValidationError(self.error_messages['required'])

        return SalesPhaseExtractor(col_index, def_value, create_if_unfound=value['create'])


# Target management ------------------------------------------------------------
class TargetExtractor(object):
    def __init__(self, orga_column_index, create_orga, contact_column_index, create_contact):
        self._orga_column_index    = orga_column_index
        self._contact_column_index = contact_column_index
        self._create_orga          = create_orga
        self._create_contact       = create_contact

    def _extract_person(self, line, user, model, index, field_name, create):
        #TODO: manage credentials (linkable (& viewable ?) Contact/Organisation)
        if not index: #0 -> not in csv
            return None, None

        value = line[index - 1]
        if not value:
            return None, None

        error_msg = None
        extracted = None
        kwargs = {field_name: value}

        try:
            extracted = model.objects.get(**kwargs)
        except Exception as e:
            if create:
                created = model(user=user, **kwargs)

                try:
                    created.full_clean() #can raise ValidationError
                    created.save() #TODO should we use save points for this line ?
                except Exception as e:
                    error_msg = _(u'Error while extracting value [%(raw_error)s]: tried to retrieve and then build "%(value)s" on %(model)s') % {
                                        'raw_error': e,
                                        'value': value,
                                        'model': model._meta.verbose_name,
                                    }
                else:
                    extracted = created
            else:
                error_msg = _(u'Error while extracting value [%(raw_error)s]: tried to retrieve "%(value)s" on %(model)s') % {
                                    'raw_error': e,
                                    'value':     value,
                                    'model':     model._meta.verbose_name,
                                }

        return error_msg, extracted

    def extract_value(self, line, user, import_errors):
        extract_person = self._extract_person
        error_msg1, extracted = extract_person(line, user, Organisation, self._orga_column_index, 'name', self._create_orga)

        if extracted is None:
            error_msg2, extracted = extract_person(line, user, Contact, self._contact_column_index, 'last_name', self._create_contact)

            if extracted is None:
                import_errors.append((line, u'\n'.join(msg for msg in (error_msg1, error_msg2) if msg)))

        return extracted


#TODO: use ul/li instead of table...
class TargetExtractorWidget(ExtractorWidget):
    def __init__(self, *args, **kwargs):
        super(TargetExtractorWidget, self).__init__(*args, **kwargs)
        #self.propose_orga_creation = False #TODO
        #self.propose_contact_creation = False #TODO

    def _render_column_select(self, name, value, choices, line_name):
        try:
            sel_val = int(value.get('%s_selected_column' % line_name, -1))
        except TypeError:
            sel_val = 0

        return self._render_select("%s_%s_colselect" % (name, line_name),
                                   choices=chain(self.choices, choices),
                                   sel_val=sel_val,
                                   attrs={'class': 'csv_col_select'}
                                  )

    def _render_line(self, output, name, value, choices, line_title, line_name):
        append = output.append
        append(u'<tr><td>%s: </td><td>' % line_title)
        append(self._render_column_select(name, value, choices, line_name))
        append('</td><td>&nbsp;%(label)s <input type="checkbox" name="%(name)s_%(subname)s_create" %(checked)s></td></tr>' % {
                            'label':   _(u'Create if not found ?'),
                            'name':    name,
                            'subname': line_name,
                            'checked': 'checked' if value.get('%s_create' % line_name) else '',
                        }
                     )

    def render(self, name, value, attrs=None, choices=()):
        value = value or {}
        output = [u'<table %s><tbody>' % flatatt(self.build_attrs(attrs, name=name))]

        render_line = self._render_line
        render_line(output, name, value, choices, _('Target organisation'), 'orga')
        render_line(output, name, value, choices, _('Target contact'),      'contact')

        output.append(u'</tbody></table>')

        return mark_safe(u'\n'.join(output))

    def value_from_datadict(self, data, files, name):
        get = data.get
        return {'orga_selected_column':    get("%s_orga_colselect" % name),
                'create_orga':             get("%s_orga_create" % name, False),
                'contact_selected_column': get("%s_contact_colselect" % name),
                'create_contact':          get("%s_contact_create" % name, False),
               }


class TargetExtractorField(Field):
    def __init__(self, choices, *args, **kwargs):
        super(TargetExtractorField, self).__init__(self, widget=TargetExtractorWidget, *args, **kwargs)
        widget = self.widget
        #widget.propose_orga_creation    = self._can_create_orga    = True #TODO user.can_create(...)
        #widget.propose_contact_creation = self._can_create_contact = True #TODO user.can_create(...)

        widget.choices = choices

    def _get_column_index(self, value, index_key):
        try:
            return int(value[index_key])
        except TypeError:
            raise ValidationError(self.error_messages['invalid'])

    def clean(self, value):
        get_column_index = self._get_column_index
        orga_col_index    = get_column_index(value, 'orga_selected_column')
        contact_col_index = get_column_index(value, 'contact_selected_column')

        if self.required and not (orga_col_index or contact_col_index): #TODO: test
            raise ValidationError(self.error_messages['required'])

        #TODO: check that indexes are in self._choices ???

        create_orga = value['create_orga']
        #if not self._can_create_orga and orga_create: #TODO
            #raise ValidationError("You can not create any Organisation.")

        create_contact = value['create_contact']
        #if not self._can_create_orga and orga_create: #TODO
            #raise ValidationError("You can not create any Organisation.")

        return TargetExtractor(orga_col_index, create_orga, contact_col_index, create_contact)


# Main -------------------------------------------------------------------------
def get_csv_form_builder(header_dict, choices):
    class OpportunityCSVImportForm(ImportForm4CremeEntity):
        #TODO: can we improve ExtractorField to use form registered in creme_config when it is possible ?
        sales_phase = SalesPhaseExtractorField(choices, #modelfield
                                                  Opportunity._meta.get_field_by_name('sales_phase')[0].formfield(),
                                                  label=_('Sales phase'),
                                                  #initial={'selected_column': selected_column} #TODO ??
                                                 )
        target      = TargetExtractorField(choices, label=_('Target'))

        #TODO: filter linkable
        emitter = ModelChoiceField(label=_(u"Concerned organisation"), queryset=Organisation.get_all_managed_by_creme(), empty_label=None)

        def _pre_instance_save(self, instance, line):
            cdata = self.cleaned_data
            instance.emitter = cdata['emitter']
            instance.target  = cdata['target'].extract_value(line, self.user, self.import_errors)


    return OpportunityCSVImportForm
