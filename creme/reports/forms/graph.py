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

from future_builtins import map

from django.db.models import FieldDoesNotExist, DateTimeField, DateField, ForeignKey
from django.forms.fields import ChoiceField, BooleanField
from django.forms.util import ValidationError, ErrorList
from django.forms.widgets import Select, CheckboxInput
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.forms.base import CremeEntityForm
from creme.creme_core.forms.widgets import DependentSelect
from creme.creme_core.forms.fields import AjaxChoiceField
from creme.creme_core.models import RelationType, CustomField
from creme.creme_core.models.fields import MoneyField
from creme.creme_core.utils.meta import ModelFieldEnumerator
from creme.creme_core.utils.unicode_collation import collator

from ..core.graph import RGRAPH_HANDS_MAP
from ..constants import (RGT_DAY, RGT_MONTH, RGT_YEAR, RGT_RANGE, RGT_FK, RGT_RELATION,
        RGT_CUSTOM_DAY, RGT_CUSTOM_MONTH, RGT_CUSTOM_YEAR, RGT_CUSTOM_RANGE, RGT_CUSTOM_FK)
from ..models.graph import ReportGraph
from ..report_aggregation_registry import field_aggregation_registry


class ReportGraphForm(CremeEntityForm):
    abscissa_field    = ChoiceField(label=_(u'Abscissa field'), choices=(),
                                    widget=DependentSelect(target_id='id_abscissa_group_by'),
                                   ) #TODO: DependentSelect is kept until *Selector widgets accept optgroup
    abscissa_group_by = AjaxChoiceField(label=_(u'Abscissa : Group by'), choices=(),
                                        widget=Select(attrs={'id': 'id_abscissa_group_by'}),
                                       ) #TODO: coerce to int
    aggregate         = ChoiceField(label=_(u'Ordinate aggregate'), required=False,
                                   choices=[(agg.name, agg.title) for agg in field_aggregation_registry.itervalues()],
                                  )
    aggregate_field   = ChoiceField(label=_(u'Ordinate aggregate field'), choices=(), required=False)
    is_count          = BooleanField(label=_(u'Entities count'), required=False,
                                     help_text=_(u'Make a count instead of aggregate ?'),
                                     widget=CheckboxInput(attrs={'onchange': "creme.reports.toggleDisableOthers(this, ['#id_aggregate', '#id_aggregate_field']);"}),
                                    )

    blocks = CremeEntityForm.blocks.new(
                ('abscissa', _(u'Abscissa informations'),  ['abscissa_field', 'abscissa_group_by', 'days']),
                ('ordinate', _(u'Ordinates informations'), ['is_count', 'aggregate', 'aggregate_field']),
            )

    class Meta:
        model = ReportGraph
        exclude = CremeEntityForm.Meta.exclude + ('ordinate', 'abscissa', 'type', 'report')

    def __init__(self, entity, *args, **kwargs):
        super(ReportGraphForm, self).__init__(*args, **kwargs)
        self.report = entity
        report_ct = entity.ct
        model = report_ct.model_class()

        fields = self.fields

        aggregate_field_f = fields['aggregate_field']
        abscissa_field_f  = fields['abscissa_field']
        is_count_f        = fields['is_count']

        sort_key = collator.sort_key
        sort_choices = lambda k: sort_key(k[1])

        #Abscissa -----------------------------------------------------------
        abscissa_model_fields = ModelFieldEnumerator(model, deep=0, only_leafs=False) \
                                    .filter(self._filter_abcissa_field, viewable=True) \
                                    .choices()
        abscissa_model_fields.sort(key=sort_choices)

        self.rtypes = rtypes = dict(RelationType.get_compatible_ones(report_ct, include_internals=True)
                                                .values_list('id', 'predicate')
                                   )
        sort_key = collator.sort_key
        abscissa_predicates = rtypes.items()
        abscissa_predicates.sort(key=sort_choices)

        abscissa_choices = [(_('Fields'),        abscissa_model_fields),
                            (_('Relationships'), abscissa_predicates),
                           ]

        self.abs_cfields = cfields = \
            dict((cf.id, cf) for cf in CustomField.objects.filter(field_type__in=(CustomField.ENUM,
                                                                                  CustomField.DATETIME,
                                                                                 ),
                                                                  content_type=report_ct,
                                                                 )
                )

        if cfields:
            abscissa_choices.append((_('Custom fields'), [(cf.id, cf.name) for cf in cfields.itervalues()])) #TODO: sort ?

        #TODO: we could build the complete map fields/allowed_types, instead of doing AJAX queries...
        abscissa_field_f.choices = abscissa_choices
        abscissa_field_f.widget.target_url = '/reports/graph/get_available_types/%s' % report_ct.id #Bof

        #Ordinate -----------------------------------------------------------
        #aggfield_choices = ModelFieldEnumerator(model, deep=0) \
                                #.filter((lambda f, depth: isinstance(f, field_aggregation_registry.authorized_fields)),
                                        #viewable=True
                                       #) \
                                #.choices()
        aggfields = [field_info[0]
                        for field_info in ModelFieldEnumerator(model, deep=0)
                                            .filter((lambda f, depth: isinstance(f, field_aggregation_registry.authorized_fields)),
                                                    viewable=True
                                                   )
                    ]
        aggfield_choices = [(field.name, field.verbose_name) for field in aggfields]
        aggcustom_choices = list(CustomField.objects.filter(field_type__in=field_aggregation_registry.authorized_customfields,
                                                            content_type=report_ct,
                                                           )
                                                    .values_list('id', 'name')
                                )
        ordinate_choices = aggfield_choices or aggcustom_choices

        if ordinate_choices:
            self.force_count = False

            money_fields = [field for field in aggfields if isinstance(field, MoneyField)]
            if money_fields:
                aggregate_field_f.help_text = ugettext('If you use a field related to money, the entities should use the same '
                                                       'currency or the result will be wrong. Concerned fields are : %s'
                                                      ) % ', '.join(unicode(field.verbose_name) for field in money_fields)


            if aggcustom_choices and aggfield_choices:
                ordinate_choices = [(_('Fields'),        aggfield_choices),
                                    (_('Custom fields'), aggcustom_choices),
                                   ]
        else:
            self.force_count = True
            ordinate_choices = [('', _('No field is usable for aggregation'))]

            disabled_attrs = {'disabled': True}
            aggregate_field_f.widget.attrs = disabled_attrs
            fields['aggregate'].widget.attrs = disabled_attrs

            is_count_f.help_text = _('You must make a count because no field is usable for aggregation')
            is_count_f.initial = True
            is_count_f.widget.attrs = disabled_attrs

        aggregate_field_f.choices = ordinate_choices

        #Initial data --------------------------------------------------------
        data = self.data
        instance = self.instance

        if data:
            get_data = data.get
            widget = abscissa_field_f.widget
            widget.source_val = get_data('abscissa_field')
            widget.target_val = get_data('abscissa_group_by')
        elif instance.pk is not None:
            ordinate, sep, aggregate    = instance.ordinate.rpartition('__')
            fields['aggregate'].initial = aggregate
            aggregate_field_f.initial   = ordinate
            abscissa_field_f.initial    = instance.abscissa

            widget = abscissa_field_f.widget
            widget.source_val = instance.abscissa
            widget.target_val = instance.type

        #TODO: remove this sh*t when is_count is a real widget well initialized (disabling set by JS)
        if is_count_f.initial or instance.is_count or data.get('is_count'):
            disabled_attrs = {'disabled': True}
            aggregate_field_f.widget.attrs = disabled_attrs
            fields['aggregate'].widget.attrs = disabled_attrs

    def _filter_abcissa_field(self, field, depth):
        if isinstance(field, DateField): #TODO: meta.is_date_field ?
            return True

        if isinstance(field, ForeignKey):
            return field.get_tag('enumerable')

        return False

    def clean_abscissa_group_by(self):
        str_val = self.cleaned_data.get('abscissa_group_by')

        if not str_val:
            raise ValidationError(self.fields['abscissa_group_by'].error_messages['required'])

        try:
            graph_type = int(str_val)
        except Exception as e:
            raise ValidationError('Invalid value: %s  [%s]', str_val, e)

        hand = RGRAPH_HANDS_MAP.get(graph_type)

        if hand is None:
            raise ValidationError('Invalid value: %s  not in %s', graph_type,
                                  [h.hand_id for h in RGRAPH_HANDS_MAP]
                                 )

        self.verbose_graph_type = hand.verbose_name

        return graph_type

    def clean_is_count(self):
        return self.cleaned_data.get('is_count', False) or self.force_count

    def _clean_field(self, model, name, field_types, formfield_name='abscissa_field'):
        try:
            field = model._meta.get_field(name)
        except FieldDoesNotExist:
            self.errors[formfield_name] = ErrorList([u'If you choose to group "%s" you have to choose a field.' %
                                                           self.verbose_graph_type
                                                    ]
                                                   )
        else:
            if not isinstance(field, field_types):
                self.errors[formfield_name] = ErrorList([u'"%s" groups are only compatible with {%s}' % (
                                                                self.verbose_graph_type,
                                                                ', '.join(ftype.__name__ for ftype in field_types)
                                                            )
                                                        ]
                                                       )
            else:
                return field

    def _clean_customfield(self, name, cfield_types, formfield_name='abscissa_field'):
        if not name or not name.isdigit():
            self.errors[formfield_name] = ErrorList([u'Unknown or invalid custom field.'])
        else:
            cfield = self.abs_cfields[int(name)]

            if cfield.field_type not in cfield_types:
                self.errors[formfield_name] = ErrorList([u'"%s" groups are only compatible with {%s}' % (
                                                                self.verbose_graph_type,
                                                                ', '.join(map(str, cfield_types)), #TODO: verbose type
                                                            )
                                                        ]
                                                       )
            else:
                return cfield

    def clean(self):
        cleaned_data = self.cleaned_data
        get_data     = cleaned_data.get
        model = self.report.ct.model_class()

        abscissa_name = get_data('abscissa_field')
        abscissa_group_by = cleaned_data['abscissa_group_by']

        #TODO: use a better system to check compatible Field types (use ReportGraphHands)
        if abscissa_group_by == RGT_FK:
            self._clean_field(model, abscissa_name, field_types=(ForeignKey,))
        elif abscissa_group_by == RGT_CUSTOM_FK:
            self._clean_customfield(abscissa_name, cfield_types=(CustomField.ENUM,))
        elif abscissa_group_by == RGT_RELATION:
            if abscissa_name not in self.rtypes:
                self.errors['abscissa_field'] = ErrorList([u'Unknown relationship type.'])
        elif abscissa_group_by in (RGT_DAY, RGT_MONTH, RGT_YEAR):
            self._clean_field(model, abscissa_name, field_types=(DateField, DateTimeField))
        elif abscissa_group_by == RGT_RANGE:
            self._clean_field(model, abscissa_name, field_types=(DateField, DateTimeField))

            if not cleaned_data.get('days'):
                self.errors['days'] = ErrorList([ugettext(u"You have to specify a day range if you use 'by X days'")])
        elif abscissa_group_by in (RGT_CUSTOM_DAY, RGT_CUSTOM_MONTH, RGT_CUSTOM_YEAR):
            self._clean_customfield(abscissa_name, cfield_types=(CustomField.DATETIME,))
        elif abscissa_group_by == RGT_CUSTOM_RANGE:
            self._clean_customfield(abscissa_name, cfield_types=(CustomField.DATETIME,))

            if not cleaned_data.get('days'): #TODO: factorise
                self.errors['days'] = ErrorList([ugettext(u"You have to specify a day range if you use 'by X days'")])
        else:
            raise ValidationError('Unknown graph type')

        if get_data('aggregate_field'):
            if not field_aggregation_registry.get(get_data('aggregate')):
                self.errors['aggregate'] = ErrorList([ugettext(u'This field is required if you choose a field to aggregate.')])
        elif not get_data('is_count'):
            raise ValidationError(ugettext(u"If you don't choose an ordinate field (or none available) "
                                            "you have to check 'Make a count instead of aggregate ?'"
                                          )
                                 )

        return cleaned_data

    def save(self, *args, **kwargs):
        get_data = self.cleaned_data.get
        graph    = self.instance
        graph.report   = self.report
        graph.abscissa = get_data('abscissa_field')
        graph.type = get_data('abscissa_group_by')

        agg_fields = get_data('aggregate_field')
        graph.ordinate = '%s__%s' % (agg_fields, get_data('aggregate')) if agg_fields else u""

        return super(ReportGraphForm, self).save(*args, **kwargs)
