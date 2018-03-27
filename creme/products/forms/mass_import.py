# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2018  Hybird
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
# from itertools import chain
from json import dumps as json_dump

from django.forms import Field, ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext

from creme.creme_core.forms.fields import ChoiceModelIterator
from creme.creme_core.forms.mass_import import ImportForm4CremeEntity, ExtractorWidget

from ..models import Category, SubCategory


class CategoriesExtractor(object):
    class _FatalError(Exception):
        pass

    def __init__(self, cat_index, subcat_index, default_subcat, create_if_unfound=False):
        self._cat_index = cat_index
        self._subcat_index = subcat_index
        self._default_cat = default_subcat.category
        self._default_subcat = default_subcat
        self._create = create_if_unfound

    def extract_value(self, line):
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
                            raise self._FatalError(ugettext(u'The category «%s» does not exist') % cat_name)

            # Sub-category
            subcat_index = self._subcat_index

            if subcat_index:
                subcat_name = line[subcat_index - 1]

                if subcat_name:
                    if cat_created:  # Small optimisation (do not search if just created)
                        sub_category = None
                    else:
                        sub_category = SubCategory.objects.filter(name=subcat_name, category=category).first()

                    if sub_category is None:
                        if self._create:
                            sub_category = SubCategory.objects.create(name=subcat_name, category=category)
                        else:
                            raise self._FatalError(ugettext(u'The sub-category «%s» does not exist') % subcat_name)

            # Error checking
            if sub_category.category_id != category.id:
                error_msg = ugettext(u'The category «%(cat)s» and the sub-category «%(sub_cat)s are not matching.') % {
                    'cat':     category,
                    'sub_cat': sub_category,
                }
        except self._FatalError as e:
            category = sub_category = None
            error_msg = e.args[0]

        return category, sub_category, error_msg


class CategoriesExtractorWidget(ExtractorWidget):
    def __init__(self, categories=(), *args, **kwargs):
        super(CategoriesExtractorWidget, self).__init__(*args, **kwargs)
        self.categories = categories

    # def render(self, name, value, attrs=None, choices=()):
    def render(self, name, value, attrs=None):
        value = value or {}
        get_value = value.get

        # Default values content -------
        cat_choices = list(self.categories)

        # A mapping between categories & their sub-categories (in order to avoid HTTP requests later)
        sub_cat_map = defaultdict(list)
        if cat_choices:
            for sub_cat in SubCategory.objects.filter(category__in=[c[0] for c in cat_choices]):
                sub_cat_map[sub_cat.category_id].append((sub_cat.id, sub_cat.name))

        # NB: we need to work with an int, in order to not mix int & str as keys for 'sub_cat_map'.
        try:
            selected_cat_id = int(value['default_cat'])
        except (KeyError, ValueError, TypeError):
            selected_cat_id = cat_choices[0][0] if cat_choices else None

        try:
            selected_subcat_id = int(value['default_subcat'])
        except (KeyError, ValueError, TypeError):
            selected_subcat_choice = sub_cat_map.get(selected_cat_id)  # Notice that get() cannot create a new key
            selected_subcat_id = selected_subcat_choice[0] if selected_subcat_choice else None

        # Rendering -------
        cat_colselect_id    = '%s_cat_colselect' % name
        cat_defvalselect_id = '%s_cat_defval' % name

        subcat_colselect_id    = '%s_subcat_colselect' % name
        subcat_defvalselect_id = '%s_subcat_defval' % name

        render_sel = self._render_select
        # col_choices = list(chain(self.choices, choices))
        col_choices = list(self.choices)

        def render_colsel(name, sel_val):
            return render_sel(name, choices=col_choices, sel_val=sel_val,
                              attrs={'id': name, 'class': 'csv_col_select'},
                             )

        def get_selected_column(datadict_key):
            try:
                return int(get_value(datadict_key, -1))
            except TypeError:
                return 0

        # NB: when a column is selected for the category but non for the sub-category, we do not disable
        #     the 0 option (in sub-category <select>, because we must force the selection of
        #     another option & it causes problems:
        #        - not very visible.
        #        - which option must we choose ? (it's arbitrary/stupid).
        #     Displaying a warning/error message causes problems too (eg: the message can be displayed
        #     twice -- python + js sides).
        return mark_safe(
u"""%(create_check)s
<ul class="multi-select">
    <li>
        <label for="%(cat_colselect_id)s">%(cat_label)s:%(cat_colselect)s</label>
        <label for="%(cat_defvalselect_id)s">%(cat_defval_label)s:%(cat_defvalselect)s</label>
    </li>
    <li>
        <label for="%(subcat_colselect_id)s">%(subcat_label)s:%(subcat_colselect)s</label>
        <label for="%(subcat_defvalselect_id)s">%(subcat_defval_label)s:%(subcat_defvalselect)s</label>
    </li>
    <script type='text/javascript'>
        $(document).ready(function() {
            var subCatMap = %(subcat_js_map)s;

            $('#%(cat_defvalselect_id)s').on('change', function(e) {
                creme.forms.Select.fill($('#%(subcat_defvalselect_id)s'), subCatMap[$(this).val()]);
            });
        });
    </script>
</ul>
""" % {'create_check': '' if not self.propose_creation else
                       u'<label for="%(id)s"><input id="%(id)s" type="checkbox" name="%(id)s" %(checked)s />%(label)s</label>' % {
                           'id': '%s_create' % name,
                           'checked': 'checked' if get_value('create') else '',
                           'label': _(u'Create the Categories/Sub-Categories which are not found?'),
                       },

       'cat_label':        pgettext('products-category', u'Category'),
       'cat_colselect_id': cat_colselect_id,
       'cat_colselect':    render_colsel(cat_colselect_id, get_selected_column('cat_column_index')),

       'cat_defval_label':    pgettext('products-category', u'Default category'),
       'cat_defvalselect_id': cat_defvalselect_id,
       'cat_defvalselect':    render_sel(cat_defvalselect_id,
                                         choices=cat_choices,
                                         sel_val=selected_cat_id,
                                         attrs={'id': cat_defvalselect_id},
                                        ),

       'subcat_label':        pgettext('products-sub_category', u'Sub-category'),
       'subcat_colselect_id': subcat_colselect_id,
       'subcat_colselect':    render_colsel(subcat_colselect_id, get_selected_column('subcat_column_index')),

       'subcat_defval_label':    pgettext('products-sub_category', u'Default sub-category'),
       'subcat_defvalselect_id': subcat_defvalselect_id,
       'subcat_defvalselect':    render_sel(subcat_defvalselect_id,
                                            choices=sub_cat_map[selected_cat_id],
                                            sel_val=selected_subcat_id,
                                            attrs={'id': subcat_defvalselect_id},
                                           ),

       'subcat_js_map': json_dump(sub_cat_map),
      })

    def value_from_datadict(self, data, files, name):
        get = data.get
        return {
            'cat_column_index':    get('%s_cat_colselect' % name),
            'subcat_column_index': get('%s_subcat_colselect' % name),
            'default_cat':         get('%s_cat_defval' % name),
            'default_subcat':      get('%s_subcat_defval' % name),
            'create':              ('%s_create' % name) in data,
        }


class CategoriesExtractorField(Field):
    widget = CategoriesExtractorWidget
    default_error_messages = {
        'invalid_sub_cat': _('Select a valid sub-category.'),
        'empty_sub_cat':   _('Select a column for the sub-category if you select a column for the category.'),
    }

    def __init__(self, choices, categories, *args, **kwargs):
        super(CategoriesExtractorField, self).__init__(*args, **kwargs)
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
        except TypeError:
            raise ValidationError('Invalid value for index "%s"' % key)

        if index not in self._allowed_indexes:
            raise ValidationError('Invalid index')

        return index

    def clean(self, value):
        try:
            default_subcat = SubCategory.objects.get(id=value['default_subcat'])
        except (ValueError, SubCategory.DoesNotExist):
            raise ValidationError(self.error_messages['invalid_sub_cat'], code='invalid_sub_cat')

        cat_index    = self._clean_index(value, 'cat_column_index')
        subcat_index = self._clean_index(value, 'subcat_column_index')

        if cat_index and not subcat_index:
            raise ValidationError(self.error_messages['empty_sub_cat'], code='empty_sub_cat')

        create = value['create']
        if create and not self._can_create:
             raise ValidationError('You cannot create Category or SubCategory')

        return CategoriesExtractor(cat_index=cat_index,
                                   subcat_index=subcat_index,
                                   default_subcat=default_subcat,
                                   create_if_unfound=create,
                                  )


def get_massimport_form_builder(header_dict, choices):
    class ProductMassImportForm(ImportForm4CremeEntity):
        categories = CategoriesExtractorField(choices=choices, label=_('Categories'),
                                              categories=Category.objects.all(),
                                             )

        class Meta:
            exclude = ('images', 'category', 'sub_category')

        def _pre_instance_save(self, instance, line):
            category, sub_category, error = self.cleaned_data['categories'].extract_value(line)

            if error:
                # self.append_error(line, error, instance)
                self.append_error(error)
            else:
                instance.category = category
                instance.sub_category = sub_category

    return ProductMassImportForm
