################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from __future__ import annotations

from uuid import uuid4

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.models import CremeModel
from creme.documents.models.fields import ImageEntityManyToManyField


class EmailSignatureManager(models.Manager):
    def get_by_portable_key(self, key) -> EmailSignature:
        return self.get(uuid=key)


class EmailSignature(CremeModel):  # TODO: MinionModel?
    uuid = models.UUIDField(
        unique=True, editable=False, default=uuid4,
    ).set_tags(viewable=False)
    name = models.CharField(
        _('Name'),
        max_length=100,
        help_text=_(
            "The name is only used to select the signature you want to use (in "
            "an email or an email template), it is not display in the email's "
            "body."
        ),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_('User'), on_delete=models.CASCADE,
    )
    body = models.TextField(_('Body'))
    images = ImageEntityManyToManyField(
        verbose_name=_('Images'), blank=True,
        help_text=_(
            'Images embedded in emails (but not as attached).\n'
            'Hint: try to keep your images light (less than 2MB).\n'
            'Hint: try to keep your images less than 500px wide to get a good render on mobile.'
        ),
    )

    objects = EmailSignatureManager()

    creation_label = pgettext_lazy('emails', 'Create a signature')
    save_label     = pgettext_lazy('emails', 'Save the signature')

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'emails'
        verbose_name = _('Email signature')
        verbose_name_plural = _('Email signatures')
        ordering = ('name',)

    def can_change_or_delete(self, user):
        return self.user_id == user.id or user.is_superuser

    def get_edit_absolute_url(self):
        return reverse('emails__edit_signature', args=(self.id,))

    def portable_key(self) -> str:
        return str(self.uuid)
