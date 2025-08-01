################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2025  Hybird
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

from decimal import Decimal
from functools import partial

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.formats import number_format
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme import persons
from creme.creme_core.core.snapshot import Snapshot
from creme.creme_core.forms.mass_import import (
    BaseExtractorWidget,
    EntityExtractorField,
    ImportForm4CremeEntity,
)
from creme.creme_core.models import SettingValue, Vat
from creme.creme_core.utils import as_int, update_model_instance

from .. import get_product_line_model
from ..core.number_generation import number_generator_registry
from ..models import NumberGeneratorItem
from ..setting_keys import emitter_edition_key
from ..utils import copy_or_create_address

Contact      = persons.get_contact_model()
Organisation = persons.get_organisation_model()

MODE_NO_TOTAL             = 1
MODE_COMPUTE_TOTAL_VAT    = 2
MODE_COMPUTE_TOTAL_NO_VAT = 3
MODE_COMPUTE_VAT          = 4


def _copy_or_update_address(source, dest, attr_name, addr_name):
    change = True

    source_addr = getattr(source, attr_name, None)
    dest_addr   = getattr(dest,   attr_name, None)

    if dest_addr is None:  # Should not happen
        setattr(dest, attr_name, copy_or_create_address(source_addr, source, addr_name))
    elif source_addr is None:
        # Should we empty the fields of the Address ?
        pass
    else:
        change = update_model_instance(dest_addr, **dict(source_addr.info_fields))

    return change


class _TotalsExtractor:
    # TODO: what if ProductLine is not registered?
    line_model = get_product_line_model()

    def __init__(self, create_vat=False):
        self.create_vat = create_vat
        self._vat_validator = Vat._meta.get_field('value').formfield(localize=True).clean
        self._amount_validator = self.line_model._meta.get_field(
            'unit_price'
        ).formfield(localize=True).clean

    def _extract_total_n_vat(self, line) -> tuple[Decimal, Decimal]:
        """Return total without VAT and VAT.
        @raise ValidationError.
        """
        raise NotImplementedError

    def _clean_total_without_vat(self, value):
        try:
            return self._amount_validator(value)
        except ValidationError as e:
            raise ValidationError(
                gettext('The total without VAT is invalid: {}').format(e.message)
            )

    def _clean_total_with_vat(self, value):
        try:
            return self._amount_validator(value)
        except ValidationError as e:
            raise ValidationError(
                gettext('The total with VAT is invalid: {}').format(e.message)
            )

    def _clean_vat(self, value):
        try:
            cleaned_value = self._vat_validator(value)
        except ValidationError as e:
            raise ValidationError(
                gettext('The VAT value is invalid: {}').format(e.message)
            )

        return self._get_or_create_vat(cleaned_value)

    def _get_or_create_vat(self, value):
        try:
            vat = Vat.objects.get(value=value)
        except Vat.DoesNotExist:
            if not self.create_vat:
                raise ValidationError(
                    gettext(
                        'The VAT with value «{}» does not exist and cannot be created'
                    ).format(number_format(value)),
                )

            vat = Vat.objects.create(value=value)

        return vat

    def extract_value(self, line, user):
        extracted = None
        error_messages = []

        try:
            total_no_vat, vat = self._extract_total_n_vat(line)
        except ValidationError as e:
            error_messages.append(e.message)
        else:
            line_model = self.line_model
            extracted = line_model(
                user=user,
                on_the_fly_item=gettext('N/A (import)'),
                quantity=Decimal('1'),
                discount=Decimal('0'),
                discount_unit=line_model.Discount.PERCENT,
                unit_price=total_no_vat,
                vat_value=vat,
                # unit=...,
                # comment=...,
            )
            # extracted.full_clean() TODO?

        return extracted, error_messages


class TotalWithVatExtractor(_TotalsExtractor):
    def __init__(self, *, total_no_vat_index, vat_index, create_vat=False):
        super().__init__(create_vat=create_vat)
        self._total_no_vat_index = total_no_vat_index - 1
        self._vat_index = vat_index - 1

    def _extract_total_n_vat(self, line):
        vat = self._clean_vat(line[self._vat_index])
        total_no_vat = self._clean_total_without_vat(line[self._total_no_vat_index])

        return total_no_vat, vat


class TotalWithoutVatExtractor(_TotalsExtractor):
    def __init__(self, *, total_vat_index, vat_index, create_vat=False):
        super().__init__(create_vat=create_vat)
        self._total_vat_index = total_vat_index - 1
        self._vat_index = vat_index - 1

    def _extract_total_n_vat(self, line):
        vat = self._clean_vat(line[self._vat_index])
        total_vat = self._clean_total_with_vat(line[self._total_vat_index])

        return (total_vat / (Decimal(1) + vat.value / Decimal(100))), vat


class VatExtractor(_TotalsExtractor):
    def __init__(self, *, total_no_vat_index, total_vat_index, create_vat=False):
        super().__init__(create_vat=create_vat)
        self._total_no_vat_index = total_no_vat_index - 1
        self._total_vat_index = total_vat_index - 1

    def _extract_total_n_vat(self, line):
        total_no_vat = self._clean_total_without_vat(line[self._total_no_vat_index])
        total_vat = self._clean_total_with_vat(line[self._total_vat_index])
        vat_value = (total_vat / total_no_vat - Decimal(1)) * Decimal(100)

        return total_no_vat, self._get_or_create_vat(vat_value)


class TotalsExtractorWidget(BaseExtractorWidget):
    template_name = 'billing/forms/widgets/totals-extractor.html'

    def get_context(self, name, value, attrs):
        value = value or {}
        context = super().get_context(name=name, value=value, attrs=attrs)

        widget_cxt = context['widget']
        widget_cxt['MODE_NO_TOTAL']             = MODE_NO_TOTAL
        widget_cxt['MODE_COMPUTE_TOTAL_VAT']    = MODE_COMPUTE_TOTAL_VAT
        widget_cxt['MODE_COMPUTE_TOTAL_NO_VAT'] = MODE_COMPUTE_TOTAL_NO_VAT
        widget_cxt['MODE_COMPUTE_VAT']          = MODE_COMPUTE_VAT
        widget_cxt['mode'] = value.get('mode', MODE_NO_TOTAL)

        id_attr = widget_cxt['attrs']['id']

        def column_select_context(name_fmt, selected_key):
            return self.column_select.get_context(
                name=name_fmt.format(name),
                value=value.get(selected_key),
                attrs={
                    'id': name_fmt.format(id_attr),
                    'class': 'csv_col_select',
                },
            )['widget']

        widget_cxt['totalnovat_column_select'] = column_select_context(
            name_fmt='{}_total_no_vat_colselect',
            selected_key='total_no_vat_column_index',
        )
        widget_cxt['totalvat_column_select'] = column_select_context(
            name_fmt='{}_total_vat_colselect',
            selected_key='total_vat_column_index',
        )
        widget_cxt['vat_column_select'] = column_select_context(
            name_fmt='{}_vat_colselect',
            selected_key='vat_column_index',
        )

        return context

    def value_from_datadict(self, data, files, name):
        get = data.get

        return {
            'mode': as_int(get(f'{name}_mode'), 1),

            'total_no_vat_column_index': as_int(get(f'{name}_total_no_vat_colselect')),
            'total_vat_column_index':    as_int(get(f'{name}_total_vat_colselect')),
            'vat_column_index':          as_int(get(f'{name}_vat_colselect')),
        }


class TotalsExtractorField(forms.Field):
    default_error_messages = {
        'column_required': _('You have to select a column for «%(field)s».'),
    }
    index_verbose_names = {
        'total_no_vat_column_index': _('Total without VAT'),
        'total_vat_column_index': _('Total with VAT'),
        'vat_column_index': _('VAT'),
    }
    extractors = {
        MODE_NO_TOTAL: (None, {}),  # TODO: EmptyExtractor??
        MODE_COMPUTE_TOTAL_VAT: (
            TotalWithVatExtractor,
            {
                'total_no_vat_index': 'total_no_vat_column_index',
                'vat_index':          'vat_column_index',
            },
        ),
        MODE_COMPUTE_TOTAL_NO_VAT: (
            TotalWithoutVatExtractor,
            {
                'total_vat_index': 'total_vat_column_index',
                'vat_index':       'vat_column_index',
            },
        ),
        MODE_COMPUTE_VAT: (
            VatExtractor,
            {
                'total_vat_index':    'total_vat_column_index',
                'total_no_vat_index': 'total_no_vat_column_index',
            },
        )
    }

    def __init__(self, *, choices, **kwargs):
        super().__init__(widget=TotalsExtractorWidget, **kwargs)
        self._allowed_indexes = {c[0] for c in choices}

        self.user = None
        self.widget.choices = choices

    @property
    def can_create_vat(self):
        user = self._user
        return user is not None and user.has_perm_to_admin('creme_core')

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user
        # NB: probably not great to override help_text, but this field should
        # not be used elsewhere...
        self.help_text = (
            ''
            if self.can_create_vat else
            _('Beware: you are not allowed to create new VAT values')
        )

    def _clean_index(self, value, key):
        try:
            index = int(value[key])
        except KeyError as e:
            raise ValidationError(f'Index "{key}" is required') from e
        except ValueError as e:
            raise ValidationError(f'Index "{key}" should be an integer') from e

        if index not in self._allowed_indexes:
            raise ValidationError('Invalid index')

        if not index:
            raise ValidationError(
                self.error_messages['column_required'],
                code='column_required',
                params={'field': self.index_verbose_names.get(key, '??')},
            )

        return index

    def _clean_mode(self, value):
        try:
            mode = int(value['mode'])
        except KeyError as e:
            if self.required:
                raise ValidationError('Mode is required') from e
            mode = MODE_NO_TOTAL
        except ValueError as e:
            raise ValidationError('Invalid value for mode') from e

        return mode

    def clean(self, value):
        mode = self._clean_mode(value)

        try:
            extractor_cls, args_descriptors = self.extractors[mode]
        except KeyError:
            raise ValidationError('Invalid mode')

        if extractor_cls is None:
            return None

        clean_index = partial(self._clean_index, value)

        return extractor_cls(
            create_vat=self.can_create_vat,
            **{
                arg_name: clean_index(col_name)
                for arg_name, col_name in args_descriptors.items()
            },
        )


def get_import_form_builder(header_dict, choices):
    class BillingMassImportForm(ImportForm4CremeEntity):
        source = EntityExtractorField(
            models_info=[(Organisation, 'name')],
            choices=choices,
            label=pgettext_lazy('billing', 'Source organisation'),
        )
        target = EntityExtractorField(
            models_info=[
                (Organisation, 'name'),
                (Contact, 'last_name'),
            ],
            choices=choices, label=pgettext_lazy('billing', 'Target'),
        )

        totals = TotalsExtractorField(choices=choices, label=_('Totals & VAT'))

        class Meta:
            exclude = ('discount',)  # NB: if uncommented, should be used in totals computing

        blocks = ImportForm4CremeEntity.blocks.new(
            {
                'id': 'organisations_and_addresses',
                'label': _('Organisations'),
                'fields': ['source', 'target'],
            },
            {
                'id': 'totals',
                'label': _('Totals & VAT'),
                'fields': ['totals'],
            },
        )

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['number'].help_text = self._build_number_help_text()

        def _build_number_help_text(self):
            messages = []
            model = self._meta.model

            if model.generate_number_in_create:
                messages.append(
                    gettext(
                        'If you chose an organisation managed by {software} as '
                        'source organisation, a number will be automatically '
                        'generated for created «{models}».'
                    ).format(
                        software=settings.SOFTWARE_LABEL,
                        models=model._meta.verbose_name_plural,
                    )
                )

            allowed = []
            forbidden = []
            for item in NumberGeneratorItem.objects.get_for_model(model):
                if number_generator_registry.get(item):
                    (allowed if item.is_edition_allowed else forbidden).append(item.organisation)

            if allowed:
                messages.append(
                    gettext(
                        'If the source organisation is {}, the file can set a number.'
                    ).format('/'.join(str(orga) for orga in allowed))
                )

            if forbidden:
                messages.append(
                    gettext(
                        'If the source organisation is {}, the file can NOT set a number.'
                    ).format('/'.join(str(orga) for orga in forbidden))
                )

            messages.append(
                gettext(
                    'Hint: to import numbers when the source is managed, '
                    'you can configure temporarily the number generation to allow '
                    'manual edition; you can also edit the counter in order to '
                    'keep a consistent numbering.'
                )
            )

            return '\n'.join(messages)

        def clean_totals(self):
            extractor = self.cleaned_data['totals']

            if extractor is not None and self.cleaned_data.get('key_fields'):
                raise ValidationError(
                    gettext('You cannot compute totals in update mode.')
                )

            return extractor

        def _check_number_edition(self, instance):
            number = instance.number
            snapshot = Snapshot.get_for_instance(instance)
            if snapshot is not None:  # Edition
                if snapshot.get_initial_instance().number  == number:
                    return  # No change
            elif not number:
                return  # Number left empty => filler if needed by signal

            item = NumberGeneratorItem.objects.filter(
                organisation=instance.source,
                numbered_type=instance.entity_type,
            ).first()

            if item and not item.is_edition_allowed:
                raise ValueError(
                    gettext('The number is set as not editable by the configuration.')
                )

        def _pre_instance_save(self, instance, line):
            cdata = self.cleaned_data
            append_error = self.append_error
            user = self.user

            # Emitter ---
            emitter, err_msg1 = cdata['source'].extract_value(line, user)

            snapshot = Snapshot.get_for_instance(instance)
            if (
                snapshot is not None
                and not instance.generate_number_in_create  # Invoice & CreditNote
                and snapshot.get_initial_instance().number
                and instance.source != emitter
                and not SettingValue.objects.get_4_key(emitter_edition_key, default=False).value
            ):
                raise ValueError(
                    gettext('Your configuration forbids you to edit the source Organisation')
                )

            setattr(instance, 'source', emitter)
            append_error(err_msg1)  # Error is only appended if 'err_msg' is not empty

            # Receiver ---
            target, err_msg2 = cdata['target'].extract_value(line, user)
            setattr(instance, 'target', target)
            append_error(err_msg2)

            self._check_number_edition(instance)

        def _post_instance_creation(self, instance, line, updated):
            super()._post_instance_creation(instance, line, updated)
            cdata = self.cleaned_data

            line_extractor = cdata['totals']
            if line_extractor is not None:
                line, errors = line_extractor.extract_value(line, self.user)

                if line:
                    line.related_document = instance
                    line.save()

                for error in errors:
                    self.append_error(error)

    return BillingMassImportForm
