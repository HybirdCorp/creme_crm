# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from django.db.models import FieldDoesNotExist, DateTimeField, DateField, ForeignKey
from django.db.models.fields.related import RelatedField
from django.forms.fields import ChoiceField, BooleanField
from django.forms.utils import ValidationError
from django.forms.widgets import Select, CheckboxInput
from django.urls import reverse
from django.utils.translation import gettext_lazy as _, gettext

from creme.creme_core.forms.base import CremeEntityForm
from creme.creme_core.forms.fields import AjaxChoiceField
from creme.creme_core.forms.widgets import DependentSelect
from creme.creme_core.models import CremeEntity, RelationType, CustomField, FieldsConfig
from creme.creme_core.models.fields import MoneyField
from creme.creme_core.utils.meta import ModelFieldEnumerator
from creme.creme_core.utils.unicode_collation import collator

from .. import get_rgraph_model
from ..constants import (RGT_DAY, RGT_MONTH, RGT_YEAR, RGT_RANGE, RGT_FK, RGT_RELATION,
        RGT_CUSTOM_DAY, RGT_CUSTOM_MONTH, RGT_CUSTOM_YEAR, RGT_CUSTOM_RANGE, RGT_CUSTOM_FK)
from ..core.graph import RGRAPH_HANDS_MAP
from ..report_aggregation_registry import field_aggregation_registry
from ..report_chart_registry import report_chart_registry


# TODO: TEMPORARY HACK. Toggle fields with an inline onchange script is a bit ugly.
class AbscissaGroupBySelect(Select):
    def get_context(self, name, value, attrs):
        extra_args = {
            'onchange': "creme.reports.toggleDaysField($(this), [{}]);".format(
                            ','.join("'{}'".format(t) for t in (RGT_CUSTOM_RANGE, RGT_RANGE))
                        ),
        }
        if attrs is not None:
            extra_args.update(attrs)

        return super().get_context(name=name, value=value, attrs=extra_args)


class ReportGraphForm(CremeEntityForm):
    chart             = ChoiceField(label=_('Chart type'), choices=report_chart_registry.choices())
    abscissa_field    = ChoiceField(label=_('Field'), choices=(),
                                    widget=DependentSelect(target_id='id_abscissa_group_by'),
                                   )  # TODO: DependentSelect is kept until *Selector widgets accept optgroup
    abscissa_group_by = AjaxChoiceField(label=_('Grouping'), choices=(),
                                        widget=AbscissaGroupBySelect(attrs={'id': 'id_abscissa_group_by'}),
                                       )  # TODO: coerce to int
    aggregate         = ChoiceField(label=_('Aggregate'), required=False,
                                   choices=[(agg.name, agg.title)
                                                for agg in field_aggregation_registry.aggregations
                                           ],
                                  )
    aggregate_field   = ChoiceField(label=_('Field'), choices=(), required=False)
    is_count          = BooleanField(label=_('Entities count'), required=False,
                                     help_text=_('Make a count instead of aggregate ?'),
                                     widget=CheckboxInput(attrs={'onchange': "creme.reports.toggleDisableOthers(this, ['#id_aggregate', '#id_aggregate_field']);"}),
                                    )

    blocks = CremeEntityForm.blocks.new(
                ('abscissa', _('X axis'), ['abscissa_field', 'abscissa_group_by', 'days']),
                ('ordinate', _('Y axis'), ['is_count', 'aggregate', 'aggregate_field']),
            )

    class Meta(CremeEntityForm.Meta):
        model = get_rgraph_model()

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.report = entity
        report_ct = entity.ct
        model = report_ct.model_class()

        instance = self.instance
        fields = self.fields

        aggregate_field_f = fields['aggregate_field']
        abscissa_field_f  = fields['abscissa_field']
        is_count_f        = fields['is_count']

        get_fconf = FieldsConfig.LocalCache().get_4_model
        # TODO: split('__', 1) when 'count' is an aggregate operator
        ordinate_field_name, __, aggregate = instance.ordinate.rpartition('__')

        # Abscissa -------------------------------------------------------------
        def absc_field_excluder(field, deep):
            # TODO: set the ForeignKeys to entities as not enumerable automatically ?
            if isinstance(field, RelatedField) and \
               issubclass(field.remote_field.model, CremeEntity):
                return True

            return get_fconf(field.model).is_field_hidden(field) and \
                   field.name != instance.abscissa

        abscissa_model_fields = ModelFieldEnumerator(model, deep=0, only_leafs=False) \
                                    .filter(self._filter_abcissa_field, viewable=True) \
                                    .exclude(absc_field_excluder) \
                                    .choices()

        self.rtypes = rtypes = dict(RelationType.objects
                                                .compatible(report_ct, include_internals=True)
                                                .values_list('id', 'predicate')
                                   )
        abscissa_predicates = list(rtypes.items())
        sort_key = collator.sort_key
        abscissa_predicates.sort(key=lambda k: sort_key(k[1]))

        abscissa_choices = [(_('Fields'),        abscissa_model_fields),
                            (_('Relationships'), abscissa_predicates),
                           ]

        self.abs_cfields = cfields = {
                cf.id: cf for cf in CustomField.objects.filter(field_type__in=(CustomField.ENUM,
                                                                               CustomField.DATETIME,
                                                                              ),
                                                               content_type=report_ct,
                                                              )
            }

        if cfields:
            # TODO: sort ?
            abscissa_choices.append((_('Custom fields'), [(cf.id, cf.name) for cf in cfields.values()]))

        # TODO: we could build the complete map fields/allowed_types, instead of doing AJAX queries...
        abscissa_field_f.choices = abscissa_choices
        abscissa_field_f.widget.target_url = reverse('reports__graph_types', args=(report_ct.id,))  # Meh

        # Ordinate -------------------------------------------------------------
        def agg_field_excluder(field, deep):
            return get_fconf(field.model).is_field_hidden(field) and \
                   field.name != ordinate_field_name

        aggfields = [field_info[0]
                        for field_info in ModelFieldEnumerator(model, deep=0)
                                            .filter((lambda f, depth: isinstance(f, field_aggregation_registry.authorized_fields)),
                                                    viewable=True
                                                   )
                                            .exclude(agg_field_excluder)
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
                # TODO: lazy lazily-translated-string interpolation
                aggregate_field_f.help_text = gettext(
                        'If you use a field related to money, the entities should use the same '
                        'currency or the result will be wrong. Concerned fields are : {}'
                    ).format(', '.join(str(field.verbose_name) for field in money_fields))


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

        # Initial data ---------------------------------------------------------
        data = self.data

        if data:
            get_data = data.get
            widget = abscissa_field_f.widget
            widget.source_val = get_data('abscissa_field')
            widget.target_val = get_data('abscissa_group_by')
        elif instance.pk is not None:
            fields['aggregate'].initial = aggregate
            aggregate_field_f.initial   = ordinate_field_name
            abscissa_field_f.initial    = instance.abscissa

            widget = abscissa_field_f.widget
            widget.source_val = instance.abscissa
            widget.target_val = instance.type

        # TODO: remove this sh*t when is_count is a real widget well initialized (disabling set by JS)
        if is_count_f.initial or instance.is_count or data.get('is_count'):
            disabled_attrs = {'disabled': True}
            aggregate_field_f.widget.attrs = disabled_attrs
            fields['aggregate'].widget.attrs = disabled_attrs

    def _filter_abcissa_field(self, field, depth):
        if isinstance(field, DateField):  # TODO: meta.is_date_field ?
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
            raise ValidationError('Invalid value: %s  [%s]', str_val, e) from e

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
            self.add_error(formfield_name,
                           'If you choose to group "{}" you have to choose a field.'.format(
                                self.verbose_graph_type
                            )
                          )
        else:
            if not isinstance(field, field_types):
                self.add_error(formfield_name,
                               '"{}" groups are only compatible with [{}]'.format(
                                    self.verbose_graph_type,
                                    ', '.join(ftype.__name__ for ftype in field_types),
                                )
                              )
            else:
                return field

    def _clean_customfield(self, name, cfield_types, formfield_name='abscissa_field'):
        if not name or not name.isdigit():
            self.add_error(formfield_name, 'Unknown or invalid custom field.')
        else:
            cfield = self.abs_cfields[int(name)]

            if cfield.field_type not in cfield_types:
                self.add_error(formfield_name,
                               '"{}" groups are only compatible with [{}]'.format(
                                    self.verbose_graph_type,
                                    ', '.join(map(str, cfield_types)),  # TODO: verbose type
                                )
                              )
            else:
                return cfield

    def clean(self):
        cleaned_data = super().clean()
        get_data     = cleaned_data.get
        model = self.report.ct.model_class()

        abscissa_name = get_data('abscissa_field')
        abscissa_group_by = cleaned_data['abscissa_group_by']

        # TODO: use a better system to check compatible Field types (use ReportGraphHands)
        # TODO: use a self.error_messages
        if abscissa_group_by == RGT_FK:
            self._clean_field(model, abscissa_name, field_types=(ForeignKey,))
        elif abscissa_group_by == RGT_CUSTOM_FK:
            self._clean_customfield(abscissa_name, cfield_types=(CustomField.ENUM,))
        elif abscissa_group_by == RGT_RELATION:
            if abscissa_name not in self.rtypes:
                self.add_error('abscissa_field', 'Unknown relationship type.')
        elif abscissa_group_by in (RGT_DAY, RGT_MONTH, RGT_YEAR):
            self._clean_field(model, abscissa_name, field_types=(DateField, DateTimeField))
        elif abscissa_group_by == RGT_RANGE:
            self._clean_field(model, abscissa_name, field_types=(DateField, DateTimeField))

            if not cleaned_data.get('days'):
                self.add_error('days', _("You have to specify a day range if you use 'by X days'"))
        elif abscissa_group_by in (RGT_CUSTOM_DAY, RGT_CUSTOM_MONTH, RGT_CUSTOM_YEAR):
            self._clean_customfield(abscissa_name, cfield_types=(CustomField.DATETIME,))
        elif abscissa_group_by == RGT_CUSTOM_RANGE:
            self._clean_customfield(abscissa_name, cfield_types=(CustomField.DATETIME,))

            if not cleaned_data.get('days'):  # TODO: factorise
                self.add_error('days', _("You have to specify a day range if you use 'by X days'"))
        else:
            raise ValidationError('Unknown graph type')

        if cleaned_data.get('days') and abscissa_group_by not in (RGT_RANGE, RGT_CUSTOM_RANGE):
            cleaned_data['days'] = None

        if get_data('aggregate_field'):
            if not field_aggregation_registry.get(get_data('aggregate')):
                self.add_error('aggregate', _('This field is required if you choose a field to aggregate.'))
        elif not get_data('is_count'):
            raise ValidationError(gettext("If you don't choose an ordinate field (or none available) "
                                          "you have to check 'Make a count instead of aggregate ?'"
                                         )
                                 )

        return cleaned_data

    def save(self, *args, **kwargs):
        get_data = self.cleaned_data.get
        graph    = self.instance
        graph.linked_report   = self.report
        graph.abscissa = get_data('abscissa_field')
        graph.type = get_data('abscissa_group_by')

        agg_fields = get_data('aggregate_field')
        graph.ordinate = '{}__{}'.format(agg_fields, get_data('aggregate')) if agg_fields else ''

        return super().save(*args, **kwargs)
