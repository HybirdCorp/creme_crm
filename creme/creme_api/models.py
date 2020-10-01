import secrets
import string

from django.db import models
from django.utils.timezone import now, timedelta
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeModel
from creme.creme_core.models.fields import (
    CreationDateTimeField,
    ModificationDateTimeField,
)

SECRET_LENGTH = 32
PASSWORD_ALPHABET = string.digits + string.ascii_letters + string.punctuation
LAST_USE_DELAY = timedelta(seconds=10)


class ApiKey(CremeModel):
    created = CreationDateTimeField(
        _('Creation date'), editable=False
    )
    modified = ModificationDateTimeField(
        _('Last modification'), editable=False
    )

    name = models.CharField(_("Name"), max_length=40, unique=True)
    key = models.CharField(_("Key"), max_length=SECRET_LENGTH, unique=True, editable=False)

    last_use = models.DateTimeField(_("Last use"), null=True, blank=True, editable=False)

    class Meta:
        verbose_name = _("Api key")
        verbose_name_plural = _("Api keys")

    def __str__(self):
        return _("Api key '%s'") % self.name

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    def update_last_use(self):
        _now = now()
        if self.last_use is None or self.last_use < _now - LAST_USE_DELAY:
            self.last_use = _now
            self.save()

    @staticmethod
    def generate_key():
        return ''.join(secrets.choice(PASSWORD_ALPHABET) for i in range(SECRET_LENGTH))
