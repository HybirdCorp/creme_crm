# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.forms import ChoiceField, ModelChoiceField, CharField, MultipleChoiceField, ValidationError
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from creme_core.forms import CremeForm
from creme_core.forms.widgets import OrderedMultipleChoiceWidget, Label
from creme_core.registry import creme_registry
from creme_core.utils.meta import get_flds_with_fk_flds_str
from creme_core.models import SearchConfigItem, SearchField

#EXCLUDED_FIELDS_TYPES = frozenset(['AutoField','DateTimeField','DateField', 'FileField', 'ImageField', 'OneToOneField'])
#ManyToManyFields are excluded for the moment waiting for correct research's results display
EXCLUDED_FIELDS_TYPES = frozenset(['AutoField','DateTimeField','DateField', 'FileField', 'ImageField', 'OneToOneField','ManyToManyField'])

class SearchAddForm(CremeForm):
    ct_id  = ChoiceField(label=_(u'Resource associée'), choices=(), required=True)
    user   = ModelChoiceField(label=_(u'Utilisateur'), queryset=User.objects.all(), empty_label=_(u"Tous les utilisateurs"), required=False)

    def __init__(self, *args, **kwargs):
        super(SearchAddForm, self).__init__(*args, **kwargs)
        
        ct_get_for_model = ContentType.objects.get_for_model
        models = [(ct_get_for_model(model).id, model._meta.verbose_name) for model in creme_registry.iter_entity_models()]
        models.sort(key=lambda k: k[1])
        self.fields['ct_id'].choices = models

    def clean(self):
        cleaned_data = self.cleaned_data
        get_data     = cleaned_data.get

        ct_id = get_data('ct_id')
        user  = get_data('user')

        if SearchConfigItem.objects.filter(content_type__id=ct_id, user=user).count() > 0:
            raise ValidationError(_(u'Le couple configuration de recherche/utilisateur(s) existe déjà !'))

        return cleaned_data

    def save(self):
        cleaned_data  = self.cleaned_data
        ct_id = cleaned_data['ct_id']
        user  = cleaned_data['user']
        sfi = SearchConfigItem(content_type_id=ct_id, user=user)
        sfi.save()

class SearchEditForm(CremeForm):
    ct     = CharField(label=_(u"Resource associée"),  widget=Label())
    fields = MultipleChoiceField(label=_(u'Blocs à afficher'), required=False,
                                    choices=(),
                                    widget=OrderedMultipleChoiceWidget)
    user   = ModelChoiceField(label=_(u'Utilisateur'), queryset=User.objects.all(), empty_label=_(u"Tous les utilisateurs"), required=False)

    def __init__(self, search_cfg_itm, *args, **kwargs):
        super(SearchEditForm, self).__init__(*args, **kwargs)

        fields = self.fields
        target_model = search_cfg_itm.content_type.model_class()

        self.search_cfg_itm = search_cfg_itm
        fields['ct'].initial = target_model._meta.verbose_name

        #For the moment the research is only done with icontains so we avoid so field's type
        model_fields = get_flds_with_fk_flds_str(target_model, 1, exclude_func=lambda f: f.get_internal_type() in EXCLUDED_FIELDS_TYPES)

        self._model_fields = dict((f_name, f_verbose_name) for f_name, f_verbose_name in model_fields)


        search_cfg_fields = [f.field for f in search_cfg_itm.get_fields()]

        fields['fields'].choices = model_fields
        fields['fields'].initial = search_cfg_fields

        if search_cfg_itm.user:
            fields['user'].initial = search_cfg_itm.user.pk

    def save(self):
        cleaned_data  = self.cleaned_data
        search_cfg_itm = self.search_cfg_itm
        model_fields = self._model_fields
        SF_filter = SearchField.objects.filter

        fields = cleaned_data['fields']
        user   = cleaned_data['user']

        search_cfg_itm.user = user
        search_cfg_itm.save()
        
        if not fields:
            SF_filter(search_config_item__id=search_cfg_itm.id).delete()
        else:
            old_ids = set(search_cfg_itm.get_fields().values_list('field', flat=True))
            new_ids = set(fields)
            fields_to_del = old_ids - new_ids
            fields_to_add = new_ids - old_ids

            SF_filter(search_config_item__id=search_cfg_itm.id, field__in=fields_to_del).delete()

            for i, field in enumerate(fields):
                if field in fields_to_add:
                    SearchField.objects.create(search_config_item_id=search_cfg_itm.id, field=field, order=i, field_verbose_name=model_fields[field])
                else:
                    sf = SearchField.objects.get(search_config_item__id=search_cfg_itm.id, field=field)

                    if sf.order != i:
                        sf.order = i
                        sf.save()



