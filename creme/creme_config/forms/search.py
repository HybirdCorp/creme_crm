################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from django.forms import ModelChoiceField
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

import creme.creme_core.forms.header_filter as hf_forms
from creme.creme_core.forms import CremeModelForm
from creme.creme_core.models import SearchConfigItem, UserRole


class SearchRegularFieldsWidget(hf_forms.EntityCellRegularFieldsWidget):
    hide_alone_subfield = False
    only_leaves = True


class SearchRegularFieldsField(hf_forms.EntityCellRegularFieldsField):
    widget = SearchRegularFieldsWidget
    only_leaves = True

    def _regular_fields_enum(self, model):
        # TODO: factorise better with SearchConfigItem
        excluded = tuple(SearchConfigItem.EXCLUDED_FIELDS_TYPES)

        return super()._regular_fields_enum(model=model).exclude(
            lambda model, field, depth:
                isinstance(field, excluded)
                or field.choices
                or (depth == 1 and field.is_relation)
        )


class SearchCustomFieldsField(hf_forms.EntityCellCustomFieldsField):
    def _custom_fields(self):
        excluded = set(SearchConfigItem.EXCLUDED_FIELDS_TYPES)

        for cfield in super()._custom_fields():
            if type(cfield.value_class._meta.get_field('value')) not in excluded:
                yield cfield


class SearchCellsField(hf_forms.EntityCellsField):
    field_classes = {
        SearchRegularFieldsField,
        SearchCustomFieldsField,
    }


class _SearchConfigForm(CremeModelForm):
    cells = SearchCellsField(label=_('Concerned fields'), required=False)

    class Meta:
        model = SearchConfigItem
        exclude: tuple[str, ...] = ('content_type', 'role')

    blocks = CremeModelForm.blocks.new(
        {
            'id': 'cells',
            'label': 'Cells',
            'fields': ['cells'],
        },
    )

    def save(self, *args, **kwargs):
        self.instance.cells = self.cleaned_data['cells']

        return super().save(*args, **kwargs)


class SearchConfigCreationForm(_SearchConfigForm):
    role = ModelChoiceField(
        label=_('Role'), queryset=UserRole.objects.none(),
        empty_label=None, required=False,
    )

    class Meta(_SearchConfigForm.Meta):
        exclude = ('content_type',)  # TODO: editable=False ?

    def __init__(self, ctype, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        instance.content_type = ctype

        fields = self.fields

        # ---
        cells_f = fields['cells']
        cells_f.model = ctype.model_class()

        # --
        role_f = fields['role']
        used_role_ids = {
            *SearchConfigItem.objects
                             .filter(content_type=ctype)
                             .exclude(role__isnull=True, superuser=False)
                             .values_list('role', flat=True),
        }

        try:
            used_role_ids.remove(None)
        except KeyError:
            # NB: browser can ignore <em> tag in <option>...
            role_f.empty_label = '*{}*'.format(gettext('Superuser'))

        role_f.queryset = UserRole.objects.exclude(pk__in=used_role_ids)

    # NB: we could manage the possible/unlikely race condition with 'unique_together'
    # in SearchConfigItem.Meta, but it only leads to IntegrityError, recovered
    # by a refresh (you'll see the 'winning' configuration instead of yours).
    def save(self, *args, **kwargs):
        role = self.cleaned_data.get('role')

        if not role:
            self.instance.superuser = True

        return super().save(*args, **kwargs)


class SearchConfigEditionForm(_SearchConfigForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance = self.instance

        cells_f = self.fields['cells']
        cells = [*instance.cells]
        cells_f.non_hiddable_cells = cells
        cells_f.model = instance.content_type.model_class()
        cells_f.initial = cells
