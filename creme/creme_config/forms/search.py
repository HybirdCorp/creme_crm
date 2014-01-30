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

from django.forms import ModelChoiceField, MultipleChoiceField, ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.auth.models import User

from creme.creme_core.forms import CremeModelForm, CremeForm
from creme.creme_core.forms.widgets import OrderedMultipleChoiceWidget
from creme.creme_core.models import SearchConfigItem, SearchField


class SearchAddForm(CremeModelForm):
    user = ModelChoiceField(label=_(u'User'), queryset=User.objects.all(),
                            empty_label=_(u"All users"), required=False,
                           )

    class Meta:
        model = SearchConfigItem

    def clean(self):
        cdata = super(SearchAddForm, self).clean()

        if not self._errors and \
           SearchConfigItem.objects.filter(content_type=cdata['content_type'],
                                           user=cdata.get('user')
                                          ).exists():
            raise ValidationError(ugettext(u'The pair search configuration/user(s) already exists !'))

        return cdata


class SearchEditForm(CremeForm):
    fields = MultipleChoiceField(label=_(u'Concerned fields'), required=False,
                                 choices=(), widget=OrderedMultipleChoiceWidget)

    def __init__(self, *args, **kwargs):
        self.search_cfg_itm = search_cfg_itm = kwargs.pop('instance')
        super(SearchEditForm, self).__init__(*args, **kwargs)

        model_fields = search_cfg_itm.get_modelfields_choices()
        self._model_fields = dict(model_fields)

        fields_f = self.fields['fields']
        fields_f.choices = model_fields
        fields_f.initial = [f.field for f in search_cfg_itm.searchfields]

    def save(self):
        search_cfg_itm = self.search_cfg_itm
        model_fields = self._model_fields
        fields = self.cleaned_data['fields']

        if not fields:
            SearchField.objects.filter(search_config_item=search_cfg_itm).delete()
        else:
            old_ids = set(sci.field for sci in search_cfg_itm.searchfields)
            new_ids = set(fields)
            fields_to_del = old_ids - new_ids
            fields_to_add = new_ids - old_ids

            SearchField.objects.filter(search_config_item=search_cfg_itm, field__in=fields_to_del).delete()

            for i, field in enumerate(fields):
                if field in fields_to_add:
                    SearchField.objects.create(search_config_item=search_cfg_itm, field=field, order=i, field_verbose_name=model_fields[field])
                else:
                    sf = SearchField.objects.get(search_config_item=search_cfg_itm, field=field) #TODO: queries could be regrouped...

                    if sf.order != i:
                        sf.order = i
                        sf.save()
