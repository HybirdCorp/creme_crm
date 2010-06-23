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

from django.forms import ModelForm, ModelChoiceField
#from django.db.models.query_utils import Q
from django.contrib.auth.models import User

from creme_core.models import CremeProfile, Relation

from persons.models import Contact, Organisation
from persons.constants import REL_OBJ_EMPLOYED_BY, REL_OBJ_MANAGES


class ProfileAddForm(ModelForm):
    user = ModelChoiceField(queryset=User.objects.all())

    def __init__(self, *args, **kwargs):
        super(ProfileAddForm, self).__init__(*args, **kwargs)

        #TODO: can be done is one query only, no ??
        contact_pks = Relation.objects.filter(subject_entity__in=Organisation.get_all_managed_by_creme(), #values_list ??
                                              type__id__in=(REL_OBJ_EMPLOYED_BY, REL_OBJ_MANAGES))\
                                      .values_list('object_entity_id', flat=True)
        users = Contact.objects.filter(pk__in=contact_pks, is_user__isnull=False).distinct().values_list('is_user_id', flat=True)

#        self.fields['user'].queryset = User.objects.filter(Q(id__in=users)&~Q(is_user=None))
        self.fields['user'].queryset = User.objects.filter(id__in=users)

    class Meta:
        model = CremeProfile


class ProfileEditForm(ModelForm):
    class Meta:
        model = CremeProfile
