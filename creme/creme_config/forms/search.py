# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.forms import ModelChoiceField, MultipleChoiceField
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.forms import CremeModelForm
from creme.creme_core.forms.widgets import OrderedMultipleChoiceWidget
from creme.creme_core.models import SearchConfigItem, UserRole, FieldsConfig
from creme.creme_core.utils.collections import OrderedSet


class _SearchForm(CremeModelForm):
    fields = MultipleChoiceField(label=_(u'Concerned fields'), required=False,
                                 choices=(), widget=OrderedMultipleChoiceWidget,
                                )

    class Meta:
        model = SearchConfigItem
        exclude = ('content_type', 'role', 'field_names')

    def save(self, *args, **kwargs):
        self.instance.searchfields = self.cleaned_data['fields']
        return super(_SearchForm, self).save(*args, **kwargs)


class SearchAddForm(_SearchForm):
    role = ModelChoiceField(label=_(u'Role'), queryset=UserRole.objects.none(),
                            empty_label=None, required=False,
                           )

    class Meta(_SearchForm.Meta):
        exclude = ('content_type', 'field_names')

    def __init__(self, *args, **kwargs):
        super(SearchAddForm, self).__init__(*args, **kwargs)
        instance = self.instance
        instance.content_type = self.initial['content_type']
        self.fields['fields'].choices = instance.get_modelfields_choices()

        role_f = self.fields['role']
        used_role_ids = set(SearchConfigItem.objects
                                            .filter(content_type=instance.content_type)
                                            .exclude(role__isnull=True, superuser=False)
                                            .values_list('role', flat=True)
                           )

        try:
            used_role_ids.remove(None)
        except KeyError:
            role_f.empty_label = u'*{}*'.format(ugettext(u'Superuser'))  # NB: browser can ignore <em> tag in <option>...

        role_f.queryset = UserRole.objects.exclude(pk__in=used_role_ids)

    # NB: we could manage the possible/unlikely race condition with 'unique_together'
    # in SearchConfigItem.Meta, but it only leads to IntegrityError, recovered
    # by a refresh (you'll see the 'winning' configuration instead of yours).
    def save(self, *args, **kwargs):
        role = self.cleaned_data.get('role')

        if not role:
            self.instance.superuser = True

        return super(SearchAddForm, self).save(*args, **kwargs)


class SearchEditForm(_SearchForm):
    def __init__(self, *args, **kwargs):
        super(SearchEditForm, self).__init__(*args, **kwargs)
        instance = self.instance
        selected_fnames = [sf.name for sf in instance.searchfields]
        # TODO: work with Fields instead of Field names + split()...
        not_hiddable_fnames = OrderedSet(fname.split('__', 1)[0] for fname in selected_fnames)
        is_hidden = FieldsConfig.get_4_model(instance.content_type.model_class()).is_fieldname_hidden

        def keep_choice(fname):
            return not is_hidden(c[0].split('__', 1)[0]) or fname in not_hiddable_fnames

        fields_f = self.fields['fields']
        fields_f.choices = [c for c in self.instance.get_modelfields_choices()
                                if keep_choice(c[0].split('__', 1)[0])
                           ]
        fields_f.initial = selected_fnames
