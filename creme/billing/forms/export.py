# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020  Hybird
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

from collections import defaultdict
from json import dumps as json_dump

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeModelForm
from creme.creme_core.forms.fields import JSONField
from creme.creme_core.forms.widgets import ChainedInput, CremeRadioSelect
from creme.creme_core.utils.l10n import countries
from creme.creme_core.utils.unicode_collation import collator

from ..exporters.base import AGNOSTIC, BillingExportEngineManager
from ..models import Base, ExporterConfigItem


class ExporterLocalisationWidget(ChainedInput):
    country_data_name = 'country'
    country_code_data_name = 'country_code'
    languages_data_name = 'languages'
    language_data_name = 'language'
    language_code_data_name = 'language_code'

    def __init__(self, engine_manager=None, model=Base, attrs=None):
        super().__init__(attrs=attrs)
        self.engine_manager = engine_manager or BillingExportEngineManager([])
        self.model = model

    def get_context(self, name, value, attrs):
        field_attrs = {'auto': False, 'datatype': 'json'}
        country_data_name = self.country_data_name

        countries_n_lang = defaultdict(set)
        for cls in self.engine_manager.engine_classes:
            for flavour in cls(self.model).flavours:
                countries_n_lang[flavour.country].add(flavour.language)

        country_code_dname = self.country_code_data_name
        languages_dname = self.languages_data_name
        language_code_dname = self.language_code_data_name

        ext_countries = {
            AGNOSTIC: _('Agnostic (raw data)'),
            **countries,
        }

        self.add_dselect(
            country_data_name,
            # TODO: sort by country verbose name + agnostic first
            options=[
                (
                    json_dump({
                        country_code_dname: country_code,
                        # NB: sorted() to guaranty the initial value given by
                        #     field is consistent.
                        languages_dname: sorted(languages),
                    }),
                    ext_countries.get(country_code, country_code),
                )
                for country_code, languages in countries_n_lang.items()
            ],
            # TODO: when there are a lot of countries
            # attrs={
            #     **field_attrs,
            #     'autocomplete': True,
            # },
            attrs=field_attrs,
        )
        self.add_dselect(
            self.language_data_name,
            options=[
                (
                    json_dump({
                        language_code_dname: lang,
                    }),
                    lang
                )
                for lang in set(
                    lang
                    for languages in countries_n_lang.values()
                    for lang in languages
                )
            ],
            attrs={
                **field_attrs,
                # TODO: is it the smarter to filter, when the country item
                #       already contains the languages list ?
                'filter': (
                    f'context.{country_data_name} && item.value ? '
                    f'context.{country_data_name}.{languages_dname}.indexOf('
                    f'item.value.{language_code_dname}'
                    f') !== -1 : '
                    f'true'
                ),
                'dependencies': country_data_name,
            },
        )

        return super().get_context(name=name, value=value, attrs=attrs)


class ExporterLocalisationField(JSONField):
    default_error_messages = {
        'countryrequired': 'The country is required.',
        'languagerequired': 'The language is required.',
        'invalidlocalisation': 'The couple country/language is invalid',
    }

    value_type = dict
    widget = ExporterLocalisationWidget

    country_data_name       = ExporterLocalisationWidget.country_data_name
    country_code_data_name  = ExporterLocalisationWidget.country_code_data_name
    languages_data_name     = ExporterLocalisationWidget.languages_data_name
    language_data_name      = ExporterLocalisationWidget.language_data_name
    language_code_data_name = ExporterLocalisationWidget.language_code_data_name

    def __init__(self, engine_manager=None, model=Base, **kwargs):
        super().__init__(**kwargs)
        self.engine_manager = engine_manager
        self.model = model

    @property
    def engine_manager(self):
        return self._engine_manager

    @engine_manager.setter
    def engine_manager(self, mngr):
        self._engine_manager = self.widget.engine_manager = \
            mngr or BillingExportEngineManager([])

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, model):
        self._model = self.widget.model = model

    def _clean_country_code(self, data):
        clean_value = self.clean_value

        country_info = clean_value(
            data, self.country_data_name, dict,
            required=True, required_error_key='countryrequired',
        )
        country_code = clean_value(
            country_info, self.country_code_data_name, str,
            required=True, required_error_key='countryrequired',
        )

        if not country_code:
            if self.required:
                raise ValidationError(
                    self.error_messages['countryrequired'],
                    code='countryrequired',
                )

            return None

        return country_code

    def _clean_country_n_language(self, country, language):
        for cls in self.engine_manager.engine_classes:
            engine = cls(self.model)
            for flavour in engine.flavours:
                if flavour.country == country and language == flavour.language:
                    return country, language

        raise ValidationError(
            self.error_messages['invalidlocalisation'],
            code='invalidlocalisation',
        )

    def _clean_language(self, data):
        clean_value = self.clean_value

        language_info = clean_value(
            data, self.language_data_name, dict,
            required=True, required_error_key='languagerequired',
        )

        return clean_value(
            language_info, self.language_code_data_name, str,
            required=True,
            required_error_key='languagerequired',
        )

    def _value_from_unjsonfied(self, data):
        country_code = self._clean_country_code(data)
        if country_code:
            return self._clean_country_n_language(
                country_code,
                language=self._clean_language(data),
            )

        return None

    def _value_to_jsonifiable(self, value):
        country_code, language_code = value

        languages = {
            flavour.language
            for cls in self.engine_manager.engine_classes
            for flavour in cls(self.model).flavours
            if flavour.country == country_code
        }

        return {
            self.country_data_name: {
                self.country_code_data_name: country_code,
                # NB: would be cool to avoid giving this for the JS to
                #     initialize correctly.
                self.languages_data_name: sorted(languages),
            },
            self.language_data_name: {
                self.language_code_data_name: language_code,
            },
        }


class ExporterLocalisationStep(CremeModelForm):
    localisation = ExporterLocalisationField(
        label=_('Localisation'),
        help_text=_(
            'You have to choose the country, because of the legal notices '
            'printed of the output document.'
        )
    )

    class Meta(CremeModelForm.Meta):
        model = ExporterConfigItem
        fields = ()

    def __init__(self, engine_manager, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        localisation_f = self.fields['localisation']
        localisation_f.engine_manager = engine_manager
        localisation_f.model = model

        instance = self.instance
        if instance.engine_id:
            exporter = engine_manager.exporter(
                engine_id=instance.engine_id,
                flavour_id=instance.flavour_id,
                model=model,
            )

            if exporter:
                flavour = exporter.flavour
                localisation_f.initial = (flavour.country, flavour.language)

    # def save(self, *args, **kwargs):


# TODO: make true creme_core widget/field (EnhancedChoiceField ?) ?
class _ExporterSelect(CremeRadioSelect):
    option_template_name = 'billing/forms/widgets/exporter-option.html'

    def __init__(self, thumbnail_width='200px', thumbnail_height='200px', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.setdefault('class', 'billing-exporter-select')

        self.thumbnail_width = thumbnail_width
        self.thumbnail_height = thumbnail_height

    class Choice:
        def __init__(self, value, images=()):
            self.value = value
            self.images = [*images]

        def __str__(self):
            return str(self.value)

    def create_option(self, *args, **kwargs):
        context = super().create_option(*args, **kwargs)
        context['thumbnail_width'] = self.thumbnail_width
        context['thumbnail_height'] = self.thumbnail_height

        return context


class _ExporterChoiceField(forms.ChoiceField):
    widget = _ExporterSelect

    def __init__(self,
                 exporters=(),
                 required=True, widget=None, label=None, initial=None, help_text=''):
        super().__init__(
            required=required, widget=widget, label=label, initial=initial,
            help_text=help_text,
        )
        self.exporters = exporters

    # TODO:
    # def __deepcopy__(self, memo):
    #     result = super().__deepcopy__(memo)
    #     result._exporters = deepcopy(self._exporters, memo)
    #     return result

    @property
    def exporters(self):
        return self._exporters

    @exporters.setter
    def exporters(self, exporters):
        self._exporters = exporters = [*exporters]

        Choice = self.widget.Choice
        choices = [
            (Choice(exporter.id, images=exporter.screenshots), exporter.verbose_name)
            for exporter in exporters
        ]
        sort_key = collator.sort_key
        choices.sort(key=lambda k: sort_key(k[1]))
        self.choices = choices

    def to_python(self, value):
        if value in self.empty_values:
            return None

        for exporter in self._exporters:
            if value == exporter.id:
                return exporter

        # TODO: unit test
        raise ValidationError(
            self.error_messages['invalid_choice'],
            code='invalid_choice',
            params={'value': value},
        )

    def validate(self, value):
        return forms.Field.validate(self, value)


class ExporterThemeStep(CremeModelForm):
    exporter = _ExporterChoiceField(label=_('Theme'))

    # TODO: factorise
    class Meta(CremeModelForm.Meta):
        model = ExporterConfigItem
        fields = ()

    def __init__(self, localisation, engine_manager, model, *args, **kwargs):
        super().__init__(*args, **kwargs)

        country, language = localisation
        exporters = []

        for cls in engine_manager.engine_classes:
            engine = cls(model)

            exporters.extend(
                engine.exporter(flavour)
                for flavour in engine.flavours
                if flavour.country == country and language == flavour.language
            )

        exporter_f = self.fields['exporter']
        exporter_f.exporters = exporters

        instance = self.instance
        if instance.engine_id:
            # TODO: only if the engine is the same ?
            exporter_f.initial = engine_manager.exporter(
                engine_id=instance.engine_id,
                flavour_id=instance.flavour_id,
                model=model,
            ).id

    def save(self, *args, **kwargs):
        instance = self.instance
        exporter = self.cleaned_data['exporter']
        instance.engine_id = exporter.engine.id
        instance.flavour_id = exporter.flavour.as_id()

        return super().save(*args, **kwargs)
