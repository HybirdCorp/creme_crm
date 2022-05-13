import secrets
import string
import uuid

from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CremeModel
from creme.creme_core.models.fields import (
    CreationDateTimeField,
    ModificationDateTimeField,
)


def generate_secret(length, chars=(string.ascii_letters + string.digits)):
    return "".join(secrets.choice(chars) for i in range(length))


def default_application_application_secret():
    return generate_secret(40)


class Application(CremeModel):
    # IP restriction capabilities ?
    # Allow to restrict this application to a subset of resources ?

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=255,
        unique=True,
        db_index=True,
    )

    application_id = models.UUIDField(
        verbose_name=_("Application ID"),
        max_length=100,
        unique=True,
        db_index=True,
        default=uuid.uuid4,
        editable=False,
    )
    application_secret = models.CharField(
        verbose_name=_("Application secret"),
        max_length=255,
        blank=True,
    )
    _application_secret = None

    enabled = models.BooleanField(
        verbose_name=_("Enabled"),
        default=True,
    )
    token_duration = models.IntegerField(
        verbose_name=_("Tokens duration"),
        default=3600,
        help_text=_(
            "Number of seconds during which tokens will be valid. "
            "It will only affect newly created tokens."
        ),
    )

    created = CreationDateTimeField(verbose_name=_("Creation date"), editable=False)
    modified = ModificationDateTimeField(
        verbose_name=_("Last modification"), editable=False
    )

    class Meta:
        verbose_name = _("Application")
        verbose_name_plural = _("Applications")
        app_label = "creme_api"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def set_application_secret(self, raw_application_secret):
        self.application_secret = make_password(raw_application_secret)
        self._application_secret = raw_application_secret

    def check_application_secret(self, raw_application_secret):
        def setter(rcs):
            self.set_application_secret(rcs)
            self.save(update_fields=["application_secret"])

        return check_password(raw_application_secret, self.application_secret, setter)

    def save(self, **kwargs):
        if self.pk is None:
            self.set_application_secret(default_application_application_secret())
        return super().save(**kwargs)

    def can_authenticate(self, request=None):
        return self.enabled

    @staticmethod
    def authenticate(application_id, application_secret, request=None):
        try:
            application = Application.objects.get(application_id=application_id)
        except (Application.DoesNotExist, ValidationError):
            Application().set_application_secret(application_secret)
        else:
            if application.check_application_secret(
                application_secret
            ) and application.can_authenticate(request=request):
                return application


def default_token_code():
    return generate_secret(128)


class Token(models.Model):
    # Allow to restrict this token to a subset of resources ?
    # Allow create token with a duration <= application token duration

    application = models.ForeignKey(Application, on_delete=models.CASCADE)

    code = models.CharField(
        max_length=255, unique=True, db_index=True, default=default_token_code
    )
    expires = models.DateTimeField()

    created = CreationDateTimeField(editable=False)
    modified = ModificationDateTimeField(editable=False)

    user = None

    def is_expired(self):
        return timezone.now() >= self.expires

    # def expires_in(self):
    #     if self.is_expired():
    #         return 0
    #     return int((self.expires - timezone.now()).total_seconds())

    def save(self, **kwargs):
        if self.expires is None:
            delta = timezone.timedelta(seconds=self.application.token_duration)
            self.expires = timezone.now() + delta
        return super().save(**kwargs)
