# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

#from django.contrib.auth import get_user_model
from django.forms import ModelChoiceField, MultipleChoiceField, ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.forms import CremeModelForm
from creme.creme_core.forms.widgets import OrderedMultipleChoiceWidget
from creme.creme_core.models import SearchConfigItem, UserRole


#CremeUser = get_user_model()


class SearchAddForm(CremeModelForm):
#    user = ModelChoiceField(label=_(u'User'), queryset=CremeUser.objects.none(),
#                            empty_label=None,
#                           )
    role = ModelChoiceField(label=_(u'Role'), queryset=UserRole.objects.none(),
                            empty_label=None, required=False,
                           )

    class Meta:
        model = SearchConfigItem
        exclude = ('content_type', 'field_names')

    def __init__(self, *args, **kwargs):
        super(SearchAddForm, self).__init__(*args, **kwargs)
        self.instance.content_type = ct = self.initial['content_type']

#        used_user_ids = SearchConfigItem.objects.filter(content_type=ct, user__isnull=False)\
#                                                .values_list('user', flat=True)
        role_f = self.fields['role']
        used_role_ids = set(SearchConfigItem.objects.filter(content_type=ct)
                                                .exclude(role__isnull=True, superuser=False)
                                                .values_list('role', flat=True)
                           )

        try:
            used_role_ids.remove(None)
        except KeyError:
            role_f.empty_label = u'*%s*' % ugettext(u'Superuser') # NB: browser can ignore <em> tag in <option>...

#        self.fields['user'].queryset = CremeUser.objects.filter(is_team=False) \
#                                                        .exclude(pk__in=used_user_ids)
        role_f.queryset = UserRole.objects.exclude(pk__in=used_role_ids)

    # NB: we could manage the possible/unlikely race condition with 'unique_together'
    # in SearchConfigItem.Meta, but it only leads to IntegrityError, recovered
    # by a refresh (you'll see the 'winning' configuration instead of yours).
    def save(self, *args, **kwargs):
        role = self.cleaned_data.get('role')

        if not role:
            self.instance.superuser = True

        return super(SearchAddForm, self).save(*args, **kwargs)


class SearchEditForm(CremeModelForm):
    fields = MultipleChoiceField(label=_(u'Concerned fields'), required=False,
                                 choices=(), widget=OrderedMultipleChoiceWidget,
                                )

    class Meta:
        model = SearchConfigItem
#        exclude = ('content_type', 'user', 'field_names')
        exclude = ('content_type', 'role', 'field_names')

    def __init__(self, *args, **kwargs):
        super(SearchEditForm, self).__init__(*args, **kwargs)
        instance = self.instance

        fields_f = self.fields['fields']
        fields_f.choices = instance.get_modelfields_choices()
        fields_f.initial = [sf.name for sf in instance.searchfields]

    def save(self, *args, **kwargs):
        self.instance.searchfields = self.cleaned_data['fields']
        return super(SearchEditForm, self).save(*args, **kwargs)
