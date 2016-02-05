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

from django.contrib.contenttypes.models import ContentType
from django.forms import CharField, ModelChoiceField
from django.forms.widgets import TextInput
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.forms import CreatorEntityField
from creme.creme_core.forms.validators import validate_linkable_model
from creme.creme_core.forms.widgets import Label
from creme.creme_core.models import RelationType, Relation

from creme.media_managers.models import Image

from .. import get_contact_model, get_organisation_model
from .base import _BasePersonForm


Contact = get_contact_model()
Organisation = get_organisation_model()


class ContactForm(_BasePersonForm):
#     birthday = CremeDateTimeField(label=_('Birthday'), required=False)
    image    = CreatorEntityField(label=_('Image'), required=False, model=Image)

    blocks = _BasePersonForm.blocks.new(
                ('details', _(u'Contact details'), ['skype', 'phone', 'mobile', 'fax', 'email', 'url_site']),
            )

    class Meta(_BasePersonForm.Meta):
        model = Contact

    def __init__(self, *args, **kwargs):
        super(ContactForm, self).__init__(*args, **kwargs)

        if self.instance.is_user_id:
            fields = self.fields
            fields['first_name'].required = True

            email_f = fields.get('email')
            if email_f is not None:
                email_f.required = True


class RelatedContactForm(ContactForm):
    orga_overview = CharField(label=_(u'Concerned organisation'), widget=Label, initial=_('No one'))

    def __init__(self, *args, **kwargs):
        super(RelatedContactForm, self).__init__(*args, **kwargs)
        self.linked_orga = self.initial.get('linked_orga')

        if not self.linked_orga:
            return

        fields = self.fields
        fields['orga_overview'].initial = self.linked_orga
        self.relation_type = self.initial.get('relation_type')

        if self.relation_type:
            relation_field = CharField(label=ugettext(u'Relation type'),
                                       widget=TextInput(attrs={'readonly': 'readonly'}),
                                       initial=self.relation_type,  # TODO: required=False ??
                                      )
        else:
            get_ct = ContentType.objects.get_for_model
            relation_field = ModelChoiceField(label=ugettext(u"Status in the organisation"),
                                              # TODO: factorise (see User form hooking)
                                              queryset=RelationType.objects.filter(subject_ctypes=get_ct(Contact),
                                                                                   object_ctypes=get_ct(Organisation),
                                                                                   is_internal=False,
                                                                                  ),
                                             )

        fields['relation'] = relation_field

    def clean_user(self):
        return validate_linkable_model(Contact, self.user, owner=self.cleaned_data['user'])

    def save(self, *args, **kwargs):
        instance = super(RelatedContactForm, self).save(*args, **kwargs)

        if self.linked_orga:
            Relation.objects.create(subject_entity=instance,
                                    type=self.relation_type or self.cleaned_data.get('relation'),
                                    object_entity=self.linked_orga,
                                    user=instance.user,
                                   )

        return instance
