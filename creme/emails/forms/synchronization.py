################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2022  Hybird
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

from django import forms
from django.core.exceptions import ValidationError
from django.db.transaction import atomic
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme import persons
from creme.creme_core import forms as core_forms

from ..models import EmailSyncConfigItem, EmailToSync, EmailToSyncPerson


class _EmailSyncConfigItemForm(core_forms.CremeModelForm):
    password = forms.CharField(
        label=_('Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    class Meta:
        model = EmailSyncConfigItem
        exclude = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['default_user'].empty_label = _('*No default user*')

    def save(self, *args, **kwargs):
        password = self.cleaned_data['password']
        if password:
            self.instance.password = password
        return super().save(*args, **kwargs)


class EmailSyncConfigItemCreationForm(_EmailSyncConfigItemForm):
    pass


class EmailSyncConfigItemEditionForm(_EmailSyncConfigItemForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        password_f = self.fields['password']
        password_f.required = False
        password_f.help_text = _('Leave empty to keep the recorded password')


class EmailToSyncPersonForm(core_forms.CremeModelForm):
    person = core_forms.GenericEntityField(
        label=_('Contact or Organisation'),
        help_text=_(
            'The email address of the Contact/Organisation will be automatically updated.'
        ),
        models=[
            persons.get_organisation_model(),
            persons.get_contact_model()
        ],
    )

    class Meta:
        model = EmailToSyncPerson
        exclude = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['person'].initial = self.instance.person

    def clean_person(self):
        person = self.cleaned_data['person']

        if (
            person.email != self.instance.email
            and not self.user.has_perm_to_change(person)
        ):
            raise ValidationError(
                gettext(
                    'You are not allowed to edit «{}», so the email address cannot be updated'
                ).format(person)
            )

        return person

    @atomic
    def save(self, *args, **kwargs):
        instance = self.instance
        instance.person = person = self.cleaned_data['person']

        if person.email != instance.email:
            person.email = instance.email
            person.save()

        return super().save(*args, **kwargs)


class EmailToSyncCorrectionForm(core_forms.CremeModelForm):
    sender = core_forms.GenericEntityField(
        label=_('Sender'),
        models=[persons.get_organisation_model(), persons.get_contact_model()],
    )
    recipient = core_forms.GenericEntityField(
        label=_('Recipient'),
        models=[persons.get_organisation_model(), persons.get_contact_model()],
    )

    class Meta:
        model = EmailToSync
        fields = ('subject',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        related_persons = [*self.instance.related_persons.all()]
        assert len(related_persons) == 1
        assert related_persons[0].type == EmailToSyncPerson.Type.SENDER

        self.sender_cache = related = related_persons[0]
        self.fields['recipient'].initial = related.person

    def _clean_person(self, field_name):
        person = self.cleaned_data[field_name]

        if not person.email:
            raise ValidationError(
                gettext('This entity has no email address.')
            )

        return person

    def clean_recipient(self):
        return self._clean_person('recipient')

    def clean_sender(self):
        return self._clean_person('sender')

    @atomic
    def save(self, *args, **kwargs):
        cdata = self.cleaned_data

        sender = cdata['sender']
        sender_cache = self.sender_cache
        sender_cache.email = sender.email
        sender_cache.person = sender
        sender_cache.save()

        recipient = cdata['recipient']
        EmailToSyncPerson.objects.create(
            email_to_sync=self.instance,
            type=EmailToSyncPerson.Type.RECIPIENT,
            email=recipient.email,
            person=recipient,
        )

        return super().save(*args, **kwargs)
