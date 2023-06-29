################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2023  Hybird
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

from django.forms import Field, ValidationError
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms.fields import ChoiceModelIterator
from creme.creme_core.forms.mass_import import (
    BaseExtractorWidget,
    ImportForm4CremeEntity,
)
from creme.creme_core.forms.widgets import PrettySelect

from ..models import Category, SubCategory


class CategoriesExtractor:
    class _FatalError(Exception):
        pass

    def __init__(
            self,
            cat_index,
            subcat_index,
            default_subcat,
            create_if_unfound=False):
        self._cat_index = cat_index
        self._subcat_index = subcat_index
        self._default_cat = default_subcat.category
        self._default_subcat = default_subcat
        self._create = create_if_unfound

    def extract_value(self, line, user):
        error_msg = None
        category = self._default_cat
        sub_category = self._default_subcat
        cat_created = False

        try:
            # Category
            cat_index = self._cat_index

            if cat_index:
                cat_name = line[cat_index - 1]

                if cat_name:
                    category = Category.objects.filter(name=cat_name).first()

                    if category is None:
                        if self._create:
                            # TODO: description=_('Imported') ??
                            category = Category.objects.create(name=cat_name)
                            cat_created = True
                        else:
                            raise self._FatalError(
                                gettext('The category «{}» does not exist').format(cat_name)
                            )

            # Sub-category
            subcat_index = self._subcat_index

            if subcat_index:
                subcat_name = line[subcat_index - 1]

                if subcat_name:
                    if cat_created:  # Small optimisation (do not search if just created)
                        sub_category = None
                    else:
                        sub_category = SubCategory.objects.filter(
                            name=subcat_name, category=category,
                        ).first()

                    if sub_category is None:
                        if self._create:
                            sub_category = SubCategory.objects.create(
                                name=subcat_name, category=category,
                            )
                        else:
                            raise self._FatalError(
                                gettext('The sub-category «{}» does not exist').format(
                                    subcat_name,
                                )
                            )

            # Error checking
            if sub_category.category_id != category.id:
                error_msg = gettext(
                    'The category «{cat}» and the sub-category «{sub_cat}» are not matching.'
                ).format(
                    cat=category,
                    sub_cat=sub_category,
                )
        except self._FatalError as e:
            category = sub_category = None
            error_msg = e.args[0]

        return category, sub_category, error_msg


class CategoriesExtractorWidget(BaseExtractorWidget):
    template_name = 'products/forms/widgets/mass-import/categories-extractor.html'

    def __init__(self, categories=(), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.categories = categories
        self.propose_creation = False

    def get_context(self, name, value, attrs):
        # NB: when a column is selected for the category but not for the
        # sub-category, we do not disable the 0 option in sub-category <select>,
        # because we must force the selection of another option & it causes
        # problems:
        #     - not very visible.
        #     - which option must we choose ? (it's arbitrary/stupid).
        # Displaying a warning/error message causes problems too
        # (e.g. the message can be displayed twice -- python + js sides).

        value = value or {}
        context = super().get_context(name=name, value=value, attrs=attrs)
        widget_cxt = context['widget']
        widget_cxt['propose_creation'] = self.propose_creation
        widget_cxt['create'] = value.get('create', False)

        id_attr = widget_cxt['attrs']['id']

        # Column <select> x 2 -------
        def column_select_context(name_fmt, selected_key):
            try:
                selected_column = int(value.get(selected_key, -1))
            except TypeError:
                selected_column = 0

            return self.column_select.get_context(
                name=name_fmt.format(name),
                value=selected_column,
                attrs={
                    'id':    name_fmt.format(id_attr),
                    'class': 'csv_col_select',
                },
            )['widget']

        widget_cxt['category_colselect'] = column_select_context(
            name_fmt='{}_cat_colselect',
            selected_key='cat_column_index',
        )
        widget_cxt['subcategory_colselect'] = column_select_context(
            name_fmt='{}_subcat_colselect',
            selected_key='subcat_column_index',
        )

        # Default values content -------
        cat_choices = [*self.categories]

        # A mapping between categories & their sub-categories
        # (in order to avoid HTTP requests later)
        sub_cat_map = defaultdict(list)
        if cat_choices:
            for sub_cat in SubCategory.objects.filter(
                category__in=[c[0] for c in cat_choices],
            ):
                sub_cat_map[sub_cat.category_id].append((sub_cat.id, sub_cat.name))

        # NB: we need to work with an int, in order to not mix int & str as keys
        #     for 'sub_cat_map'.
        try:
            selected_cat_id = int(value['default_cat'])
        except (KeyError, ValueError, TypeError):
            selected_cat_id = cat_choices[0][0] if cat_choices else None

        try:
            selected_subcat_id = int(value['default_subcat'])
        except (KeyError, ValueError, TypeError):
            # Notice that get() cannot create a new key
            selected_subcat_choice = sub_cat_map.get(selected_cat_id)
            selected_subcat_id = selected_subcat_choice[0] if selected_subcat_choice else None

        widget_cxt['subcat_js_map'] = sub_cat_map
        widget_cxt['category_defvalselect'] = PrettySelect(
            choices=cat_choices,
        ).get_context(
            name=f'{name}_cat_defval',
            value=selected_cat_id,
            attrs={
                'id': f'{id_attr}_cat_defval',
                'class': 'category-default-value',
            },
        )['widget']
        widget_cxt['subcategory_defvalselect'] = PrettySelect(
            choices=sub_cat_map[selected_cat_id],
        ).get_context(
            name=f'{name}_subcat_defval',
            value=selected_subcat_id,
            attrs={
                'id': f'{id_attr}_subcat_defval',
                'class': 'subcategory-default-value',
            },
        )['widget']

        return context

    def value_from_datadict(self, data, files, name):
        get = data.get
        return {
            'cat_column_index':    get(f'{name}_cat_colselect'),
            'subcat_column_index': get(f'{name}_subcat_colselect'),
            'default_cat':         get(f'{name}_cat_defval'),
            'default_subcat':      get(f'{name}_subcat_defval'),
            'create':              f'{name}_create' in data,
        }


class CategoriesExtractorField(Field):
    widget = CategoriesExtractorWidget
    default_error_messages = {
        'invalid_sub_cat': _('Select a valid sub-category.'),
        'empty_sub_cat': _(
            'Select a column for the sub-category if you select a column for the category.'
        ),
    }

    def __init__(self, *, choices, categories, **kwargs):
        super().__init__(**kwargs)
        self._user = None
        self._can_create = False
        self._allowed_indexes = {c[0] for c in choices}
        self.widget.choices = choices
        self.categories = categories

    @property
    def categories(self):
        return self._categories

    @categories.setter
    def categories(self, categories):
        self._categories = categories
        self.widget.categories = ChoiceModelIterator(categories)

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user
        self.widget.propose_creation = self._can_create = user.has_perm_to_admin('products')

    # TODO: factorise (in ExtractorField) (need _allowed_indexes)
    def _clean_index(self, value, key):
        try:
            index = int(value[key])
        except TypeError as e:
            raise ValidationError(f'Invalid value for index "{key}"') from e

        if index not in self._allowed_indexes:
            raise ValidationError('Invalid index')

        return index

    def clean(self, value):
        try:
            default_subcat = SubCategory.objects.get(id=value['default_subcat'])
        except (ValueError, SubCategory.DoesNotExist) as e:
            raise ValidationError(
                self.error_messages['invalid_sub_cat'],
                code='invalid_sub_cat',
            ) from e

        cat_index    = self._clean_index(value, 'cat_column_index')
        subcat_index = self._clean_index(value, 'subcat_column_index')

        if cat_index and not subcat_index:
            raise ValidationError(
                self.error_messages['empty_sub_cat'],
                code='empty_sub_cat',
            )

        create = value['create']
        if create and not self._can_create:
            raise ValidationError('You cannot create Category or SubCategory')

        return CategoriesExtractor(
            cat_index=cat_index,
            subcat_index=subcat_index,
            default_subcat=default_subcat,
            create_if_unfound=create,
        )


def get_massimport_form_builder(header_dict, choices):
    class ProductMassImportForm(ImportForm4CremeEntity):
        categories = CategoriesExtractorField(
            choices=choices, label=_('Categories'),
            categories=Category.objects.all(),
        )

        class Meta:
            exclude = ('images', 'category', 'sub_category')

        def _pre_instance_save(self, instance, line):
            category, sub_category, error = self.cleaned_data['categories'].extract_value(
                line=line, user=self.user,
            )

            if error:
                self.append_error(error)
            else:
                instance.category = category
                instance.sub_category = sub_category

    return ProductMassImportForm
