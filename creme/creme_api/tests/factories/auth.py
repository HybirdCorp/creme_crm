import factory
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from factory.django import DjangoModelFactory

from creme import persons
from creme.creme_core.models import SetCredentials, UserRole


class RoleFactory(DjangoModelFactory):
    class Meta:
        model = UserRole

    name = "Basic"
    allowed_apps = ["creme_core", "creme_api", "persons"]
    admin_4_apps = ["creme_core", "creme_api"]

    @factory.post_generation
    def creatable_ctypes(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted is None:
            contact_ct = ContentType.objects.get_for_model(persons.get_contact_model())
            orga_ct = ContentType.objects.get_for_model(
                persons.get_organisation_model()
            )
            extracted = [contact_ct.id, orga_ct.id]
        self.creatable_ctypes.set(extracted)

    @factory.post_generation
    def exportable_ctypes(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted is None:
            contact_ct = ContentType.objects.get_for_model(persons.get_contact_model())
            extracted = [contact_ct.id]
        self.exportable_ctypes.set(extracted)


def build_username(user):
    return "%s.%s" % (user.first_name.lower(), user.last_name.lower())


def build_email(user):
    return "%s@provider.com" % build_username(user)


class UserFactory(DjangoModelFactory):
    class Meta:
        model = get_user_model()
        django_get_or_create = ["username"]

    first_name = "John"
    last_name = "Doe"
    username = factory.lazy_attribute(build_username)
    email = factory.lazy_attribute(build_email)
    is_active = True
    is_superuser = True
    role = factory.Maybe(
        "is_superuser",
        yes_declaration=None,
        no_declaration=factory.SubFactory(RoleFactory),
    )


class TeamFactory(DjangoModelFactory):
    is_team = True
    username = factory.lazy_attribute(lambda t: t.name)

    class Meta:
        model = get_user_model()

    class Params:
        name = "Team #1"

    @factory.post_generation
    def teammates(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.teammates = extracted


class CredentialFactory(DjangoModelFactory):
    role = factory.SubFactory(RoleFactory)
    set_type = SetCredentials.ESET_OWN
    forbidden = False
    efilter = None
    ctype = factory.Iterator(ContentType.objects.all())

    can_view = True
    can_change = True
    can_delete = True
    can_link = True
    can_unlink = True

    _permissions = {"can_view", "can_change", "can_delete", "can_link", "can_unlink"}

    class Meta:
        model = SetCredentials

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Create an instance of the model, and save it to the database."""
        permission = {p: kwargs.pop(p) for p in cls._permissions}
        instance = model_class(**kwargs)
        instance.set_value(**permission)
        instance.save()
        return instance
