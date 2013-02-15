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

from django.forms import ChoiceField, ModelChoiceField, MultipleChoiceField, ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.forms import CremeModelForm, CremeForm
from creme_core.forms.widgets import OrderedMultipleChoiceWidget
from creme_core.registry import creme_registry
#from creme_core.utils.meta import get_flds_with_fk_flds_str
from creme_core.models import SearchConfigItem, SearchField


#EXCLUDED_FIELDS_TYPES = frozenset(['AutoField', 'DateTimeField', 'DateField', 'FileField', 'ImageField', 'OneToOneField'])

class SearchAddForm(CremeModelForm):
    ct_id  = ChoiceField(label=_(u'Related resource'), choices=(), required=True) #TODO: ContentTypeChoiceField
    user   = ModelChoiceField(label=_(u'User'), queryset=User.objects.all(), empty_label=_(u"All users"), required=False)

    class Meta:
        model = SearchConfigItem
        exclude = ('content_type',)

    def __init__(self, *args, **kwargs):
        super(SearchAddForm, self).__init__(*args, **kwargs)

        ct_get_for_model = ContentType.objects.get_for_model
        models = [(ct_get_for_model(model).id, model._meta.verbose_name) for model in creme_registry.iter_entity_models()]
        models.sort(key=lambda k: k[1])
        self.fields['ct_id'].choices = models

    def clean(self):
        cdata = self.cleaned_data

        if SearchConfigItem.objects.filter(content_type=cdata['ct_id'], user=cdata.get('user')).exists():
            raise ValidationError(ugettext(u'The pair search configuration/user(s) already exists !'))

        return cdata

    def save(self, *args, **kwargs):
        self.instance.content_type_id = self.cleaned_data['ct_id']
        return super(SearchAddForm, self).save(*args, **kwargs)


class SearchEditForm(CremeForm):
    fields = MultipleChoiceField(label=_(u'Concerned fields'), required=False,
                                 choices=(), widget=OrderedMultipleChoiceWidget)

    def __init__(self, *args, **kwargs):
        self.search_cfg_itm = search_cfg_itm = kwargs.pop('instance')
        super(SearchEditForm, self).__init__(*args, **kwargs)

        #target_model = search_cfg_itm.content_type.model_class()

        #For the moment the research is only done with icontains so we avoid so field's type
        #model_fields = get_flds_with_fk_flds_str(target_model, 1, exclude_func=lambda f: f.get_internal_type() in EXCLUDED_FIELDS_TYPES)
        #self._model_fields = dict((f_name, f_verbose_name) for f_name, f_verbose_name in model_fields)
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
