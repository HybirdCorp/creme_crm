# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.forms import ModelChoiceField
from django.utils.translation import gettext_lazy as _, gettext

from creme.creme_core.forms import CremeModelForm
from creme.creme_core.forms.validators import validate_linkable_model
from creme.creme_core.models import RelationType, Relation

from creme import persons
from .base import _BasePersonForm

Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()


class ContactNamesForm(CremeModelForm):
    class Meta(CremeModelForm.Meta):
        model = Contact
        fields = ('last_name', 'first_name')


class ContactForm(_BasePersonForm):
    blocks = _BasePersonForm.blocks.new(
        ('details', _('Contact details'), ['skype', 'phone', 'mobile', 'fax', 'email', 'url_site']),
    )

    class Meta(_BasePersonForm.Meta):
        model = Contact

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.is_user_id:
            fields = self.fields
            fields['first_name'].required = True

            email_f = fields.get('email')
            if email_f is not None:
                email_f.required = True


class RelatedContactForm(ContactForm):
    # TODO: move the block "relationships" ? (need to improve the block-manager
    #       in order to avoid duplicating all the list of fields here)
    rtype_for_organisation = ModelChoiceField(
        label='Status in the organisation',  # NB: updated in __init__
        queryset=RelationType.objects.none(),
    )

    def __init__(self, linked_orga, rtype=None, *args, **kwargs):
        if rtype:
            kwargs['forced_relations'] = [
                Relation(type=rtype, object_entity=linked_orga),
            ]

        super().__init__(*args, **kwargs)
        self.linked_orga = linked_orga
        self.relation_type = rtype

        if rtype:
            del self.fields['rtype_for_organisation']
        else:
            rtype_f = self.fields['rtype_for_organisation']
            rtype_f.label = gettext('Status in «{organisation}»').format(
                organisation=linked_orga,
            )
            # TODO: factorise (see User form hooking)
            get_ct = ContentType.objects.get_for_model
            rtype_f.queryset = RelationType.objects.filter(
                subject_ctypes=get_ct(Contact),
                object_ctypes=get_ct(Organisation),
                is_internal=False,
            )

    def clean_user(self):
        return validate_linkable_model(Contact, self.user, owner=self.cleaned_data['user'])

    def _get_relations_to_create(self):
        relations = super()._get_relations_to_create()
        rtype = self.cleaned_data.get('rtype_for_organisation')

        if rtype:
            instance = self.instance
            relations.append(Relation(
                subject_entity=instance,
                type=rtype,
                object_entity=self.linked_orga,
                user=instance.user,
            ))

        return relations
