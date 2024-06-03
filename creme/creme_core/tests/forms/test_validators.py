from functools import partial

from django.contrib.auth import get_user
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from creme.creme_core.forms import validators
from creme.creme_core.models import FakeContact

from ..base import CremeTestCase


class CredsValidatorTestCase(CremeTestCase):
    def test_validate_none_user(self):
        with self.assertRaises(ValidationError) as cm:
            validators.validate_authenticated_user(
                None, 'nobody', code='viewnotallowed',
            )

        self.assertValidationError(
            cm.exception, messages='nobody', codes='viewnotallowed',
        )

    def test_validate_anonymous_user(self):
        user = get_user(self.client)
        self.assertTrue(user.is_anonymous)

        with self.assertRaises(ValidationError) as cm:
            validators.validate_authenticated_user(
                None, 'we are legion', code='viewnotallowed',
            )

        self.assertValidationError(
            cm.exception, messages='we are legion', codes='viewnotallowed',
        )

    def test_validate_authenticated_user(self):
        user = self.login_as_standard()
        with self.assertNoException():
            validators.validate_authenticated_user(
                user, 'none or anonymous not allowed', code='viewnotallowed',
            )

    def test_validate_viewable_entity_owner(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, own=['VIEW'])

        a = FakeContact.objects.create(last_name='Doe', first_name='John', user=user)

        with self.assertNoException():
            validators.validate_viewable_entity(a, user)

    def test_validate_viewable_entity_allowed(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, all=['VIEW'])

        a = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=self.get_root_user(),
        )

        with self.assertNoException():
            validators.validate_viewable_entity(a, user)

    def test_validate_viewable_entity_anonymous(self):
        entity = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=self.get_root_user(),
        )

        user = get_user(self.client)
        self.assertTrue(user.is_anonymous)

        with self.assertRaises(ValidationError) as cm:
            validators.validate_viewable_entity(entity, user)

        self.assertValidationError(
            cm.exception,
            messages=_('Not authenticated user is not allowed to view entities'),
            codes='viewnotallowed',
        )

    def test_validate_viewable_entity_notallowed_other(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, own=['VIEW'])

        entity = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=self.get_root_user(),
        )

        with self.assertRaises(ValidationError) as cm:
            validators.validate_viewable_entity(entity, user)

        self.assertValidationError(
            cm.exception,
            messages=_('You are not allowed to view this entity: {}').format(
                _('Entity #{id} (not viewable)').format(id=entity.id)
            ),
            codes='viewnotallowed',
        )

    def test_validate_viewable_entity_notallowed_all(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, all=['CHANGE'])

        entity = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=self.get_root_user(),
        )

        # view permission not set
        with self.assertRaises(ValidationError) as cm:
            validators.validate_viewable_entity(entity, user)

        self.assertValidationError(
            cm.exception,
            messages=_('You are not allowed to view this entity: {}').format(
                _('Entity #{id} (not viewable)').format(id=entity.id)
            ),
            codes='viewnotallowed',
        )

    def test_validate_viewable_entities_owner(self):
        user = self.login_as_standard()
        a = FakeContact.objects.create(last_name='Doe', first_name='A', user=user)
        b = FakeContact.objects.create(last_name='Doe', first_name='B', user=user)

        self.add_credentials(user.role, own=['VIEW'])

        with self.assertNoException():
            validators.validate_viewable_entities([a, b], user)

    def test_validate_viewable_entities_allowed(self):
        user = self.login_as_standard()
        other_user = self.get_root_user()
        a = FakeContact.objects.create(last_name='Doe', first_name='A', user=other_user)
        b = FakeContact.objects.create(last_name='Doe', first_name='B', user=other_user)

        self.add_credentials(user.role, all=['VIEW'])

        with self.assertNoException():
            validators.validate_viewable_entities([a, b], user)

    def test_validate_viewable_entities_anonymous(self):
        other_user = self.get_root_user()
        a = FakeContact.objects.create(last_name='Doe', first_name='John', user=other_user)
        b = FakeContact.objects.create(last_name='Doe', first_name='B', user=other_user)

        user = get_user(self.client)
        self.assertTrue(user.is_anonymous)

        with self.assertRaises(ValidationError) as cm:
            validators.validate_viewable_entities([a, b], user)

        self.assertValidationError(
            cm.exception,
            messages=_('Not authenticated user is not allowed to view entities'),
            codes='viewnotallowed',
        )

    def test_validate_viewable_entities_notallowed_other(self):
        user = self.login_as_standard()

        create_contact = partial(FakeContact.objects.create, user=self.get_root_user())
        a = create_contact(last_name='Doe', first_name='John')
        b = create_contact(last_name='Doe', first_name='B')

        self.add_credentials(user.role, own=['VIEW'])

        with self.assertRaises(ValidationError) as cm:
            validators.validate_viewable_entities([a, b], user)

        e_fmt = _('Entity #{id} (not viewable)').format
        self.assertValidationError(
            cm.exception,
            messages=_('Some entities are not viewable: {}').format(
                f'{e_fmt(id=a.id)}, {e_fmt(id=b.id)}'
            ),
            codes='viewnotallowed',
        )

    def test_validate_viewable_entities_notallowed_all(self):
        user = self.login_as_standard()

        create_contact = partial(FakeContact.objects.create, user=self.get_root_user())
        a = create_contact(last_name='Doe', first_name='John')
        b = create_contact(last_name='Doe', first_name='B')

        self.add_credentials(user.role, all=['CHANGE'])

        with self.assertRaises(ValidationError) as cm:
            validators.validate_viewable_entities([a, b], user)

        e_fmt = _('Entity #{id} (not viewable)').format
        self.assertValidationError(
            cm.exception,
            messages=_('Some entities are not viewable: {}').format(
                f'{e_fmt(id=a.id)}, {e_fmt(id=b.id)}'
            ),
            codes='viewnotallowed',
        )

    def test_validate_editable_entity_owner(self):
        user = self.login_as_standard()
        a = FakeContact.objects.create(last_name='Doe', first_name='John', user=user)

        self.add_credentials(user.role, own=['CHANGE'])

        with self.assertNoException():
            validators.validate_editable_entity(a, user)

    def test_validate_editable_entity_allowed(self):
        user = self.login_as_standard()
        entity = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=self.get_root_user(),
        )

        self.add_credentials(user.role, all=['CHANGE'])

        with self.assertNoException():
            validators.validate_editable_entity(entity, user)

    def test_validate_editable_entity_anonymous(self):
        other_user = self.get_root_user()
        a = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=other_user,
        )

        user = get_user(self.client)
        self.assertTrue(user.is_anonymous)

        with self.assertRaises(ValidationError) as cm:
            validators.validate_editable_entity(a, user)

        self.assertValidationError(
            cm.exception,
            messages=_('Not authenticated user is not allowed to edit entities'),
            codes='changenotallowed',
        )

    def test_validate_editable_entity_notallowed_other(self):
        user = self.login_as_standard()
        entity = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=self.get_root_user(),
        )

        self.add_credentials(user.role, own=['CHANGE'])

        with self.assertRaises(ValidationError) as cm:
            validators.validate_editable_entity(entity, user)

        self.assertValidationError(
            cm.exception,
            messages=_('You are not allowed to edit this entity: {}').format(
                _('Entity #{id} (not viewable)').format(id=entity.id)
            ),
            codes='changenotallowed',
        )

    def test_validate_editable_entity_notallowed_all(self):
        user = self.login_as_standard()
        entity = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=self.get_root_user(),
        )

        self.add_credentials(user.role, all=['VIEW'])

        with self.assertRaises(ValidationError) as cm:
            validators.validate_editable_entity(entity, user)

        self.assertValidationError(
            cm.exception,
            messages=_('You are not allowed to edit this entity: {}').format(entity),
            codes='changenotallowed',
        )

    def test_validate_editable_entities_owner(self):
        user = self.login_as_standard()

        create_contact = partial(FakeContact.objects.create, user=user)
        a = create_contact(last_name='Doe', first_name='A')
        b = create_contact(last_name='Doe', first_name='B')

        self.add_credentials(user.role, own=['CHANGE'])

        with self.assertNoException():
            validators.validate_editable_entities([a, b], user)

    def test_validate_editable_entities_anonymous(self):
        other_user = self.get_root_user()

        create_contact = partial(FakeContact.objects.create, user=other_user)
        a = create_contact(last_name='Doe', first_name='John')
        b = create_contact(last_name='Doe', first_name='B')

        user = get_user(self.client)
        self.assertTrue(user.is_anonymous)

        with self.assertRaises(ValidationError) as cm:
            validators.validate_editable_entities([a, b], user)

        self.assertValidationError(
            cm.exception,
            messages=_('Not authenticated user is not allowed to edit entities'),
            codes='changenotallowed',
        )

    def test_validate_editable_entities_notallowed_other(self):
        user = self.login_as_standard()

        create_contact = partial(FakeContact.objects.create, user=self.get_root_user())
        a = create_contact(last_name='Doe', first_name='John')
        b = create_contact(last_name='Doe', first_name='B')

        self.add_credentials(user.role, own=['CHANGE'])

        with self.assertRaises(ValidationError) as cm:
            validators.validate_editable_entities([a, b], user)

        e_fmt = _('Entity #{id} (not viewable)').format
        self.assertValidationError(
            cm.exception,
            messages=_('Some entities are not editable: {}').format(
                f'{e_fmt(id=a.id)}, {e_fmt(id=b.id)}'
            ),
            codes='changenotallowed',
        )

    def test_validate_editable_entities_notallowed_all(self):
        user = self.login_as_standard()

        create_contact = partial(FakeContact.objects.create, user=self.get_root_user())
        a = create_contact(last_name='Doe', first_name='John')
        b = create_contact(last_name='Doe', first_name='B')

        self.add_credentials(user.role, all=['VIEW'])

        with self.assertRaises(ValidationError) as cm:
            validators.validate_editable_entities([a, b], user)

        self.assertValidationError(
            cm.exception,
            messages=_('Some entities are not editable: {}').format(f'{a}, {b}'),
            codes='changenotallowed',
        )

    def test_validate_linkable_entity_owner(self):
        user = self.login_as_standard()
        a = FakeContact.objects.create(last_name='Doe', first_name='John', user=user)

        self.add_credentials(user.role, own=['LINK'])

        with self.assertNoException():
            validators.validate_linkable_entity(a, user)

    def test_validate_linkable_entity_allowed(self):
        user = self.login_as_standard()
        entity = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=self.get_root_user(),
        )

        self.add_credentials(user.role, all=['LINK'])

        with self.assertNoException():
            validators.validate_linkable_entity(entity, user)

    def test_validate_linkable_entity_anonymous(self):
        other_user = self.get_root_user()
        entity = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=other_user,
        )

        user = get_user(self.client)
        self.assertTrue(user.is_anonymous)

        with self.assertRaises(ValidationError) as cm:
            validators.validate_linkable_entity(entity, user)

        self.assertValidationError(
            cm.exception,
            messages=_('Not authenticated user is not allowed to link entities'),
            codes='linknotallowed',
        )

    def test_validate_linkable_entity_notallowed_other(self):
        user = self.login_as_standard()
        entity = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=self.get_root_user(),
        )

        self.add_credentials(user.role, own=['LINK'])

        with self.assertRaises(ValidationError) as cm:
            validators.validate_linkable_entity(entity, user)

        self.assertValidationError(
            cm.exception,
            messages=_('You are not allowed to link this entity: {}').format(
                _('Entity #{id} (not viewable)').format(id=entity.id)
            ),
            codes='linknotallowed',
        )

    def test_validate_linkable_entity_notallowed_all(self):
        user = self.login_as_standard()
        entity = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=self.get_root_user(),
        )

        self.add_credentials(user.role, all=['VIEW'])

        with self.assertRaises(ValidationError) as cm:
            validators.validate_linkable_entity(entity, user)

        self.assertValidationError(
            cm.exception,
            messages=_('You are not allowed to link this entity: {}').format(entity),
            codes='linknotallowed',
        )

    def test_validate_linkable_entities_owner(self):
        user = self.login_as_standard()

        create_contact = partial(FakeContact.objects.create, user=user)
        a = create_contact(last_name='Doe', first_name='A')
        b = create_contact(last_name='Doe', first_name='B')

        self.add_credentials(user.role, own=['LINK'])

        with self.assertNoException():
            validators.validate_linkable_entities([a, b], user)

    def test_validate_linkable_entities_allowed(self):
        user = self.login_as_standard()

        create_contact = partial(FakeContact.objects.create, user=self.get_root_user())
        a = create_contact(last_name='Doe', first_name='A')
        b = create_contact(last_name='Doe', first_name='B')

        self.add_credentials(user.role, all=['LINK'])

        with self.assertNoException():
            validators.validate_linkable_entities([a, b], user)

    def test_validate_linkable_entities_anonymous(self):
        other_user = self.get_root_user()

        create_contact = partial(FakeContact.objects.create, user=other_user)
        a = create_contact(last_name='Doe', first_name='John')
        b = create_contact(last_name='Doe', first_name='B')

        user = get_user(self.client)
        self.assertTrue(user.is_anonymous)

        with self.assertRaises(ValidationError) as cm:
            validators.validate_linkable_entities([a, b], user)

        self.assertValidationError(
            cm.exception,
            messages=_('Not authenticated user is not allowed to link entities'),
            codes='linknotallowed',
        )

    def test_validate_linkable_entities_notallowed_other(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, own=['LINK'])

        create_contact = partial(FakeContact.objects.create, user=self.get_root_user())
        a = create_contact(last_name='Doe', first_name='John')
        b = create_contact(last_name='Doe', first_name='B')

        with self.assertRaises(ValidationError) as cm:
            validators.validate_linkable_entities([a, b], user)

        e_fmt = _('Entity #{id} (not viewable)').format
        self.assertValidationError(
            cm.exception,
            messages=_('Some entities are not linkable: {}').format(
                f'{e_fmt(id=a.id)}, {e_fmt(id=b.id)}'
            ),
            codes='linknotallowed',
        )

    def test_validate_linkable_entities_notallowed_all(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, all=['VIEW'])

        create_contact = partial(FakeContact.objects.create, user=self.get_root_user())
        a = create_contact(last_name='Doe', first_name='John')
        b = create_contact(last_name='Doe', first_name='B')

        with self.assertRaises(ValidationError) as cm:
            validators.validate_linkable_entities([a, b], user)

        self.assertValidationError(
            cm.exception,
            messages=_('Some entities are not linkable: {}').format(f'{a}, {b}'),
            codes='linknotallowed',
        )

    def test_validate_linkable_model(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, own=['LINK'])

        with self.assertNoException():
            validators.validate_linkable_model(FakeContact, user, user)

    def test_validate_linkable_model_allowed(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, all=['LINK'])

        other_user = self.get_root_user()
        with self.assertNoException():
            validators.validate_linkable_model(FakeContact, user, other_user)

    def test_validate_linkable_model_anonymous(self):
        user = get_user(self.client)
        self.assertTrue(user.is_anonymous)

        with self.assertRaises(ValidationError) as cm:
            validators.validate_linkable_model(FakeContact, user, user)

        self.assertValidationError(
            cm.exception,
            messages=_('Not authenticated user is not allowed to link «{model}»').format(
                model=FakeContact._meta.verbose_name_plural,
            ),
            codes='linknotallowed',
        )

    def test_validate_linkable_model_notallowed_other(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, own=['LINK'])

        other_user = self.get_root_user()
        with self.assertRaises(ValidationError) as cm:
            validators.validate_linkable_model(FakeContact, user, other_user)

        self.assertValidationError(
            cm.exception,
            messages=_(
                'You are not allowed to link with the «{models}» of this user.'
            ).format(models='Test Contacts'),
            codes='linknotallowed',
        )

    def test_validate_linkable_model_notallowed_all(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, all=['VIEW'])

        with self.assertRaises(ValidationError) as cm:
            validators.validate_linkable_model(FakeContact, user, user)

        self.assertValidationError(
            cm.exception,
            messages=_(
                'You are not allowed to link with the «{models}» of this user.'
            ).format(models='Test Contacts'),
            codes='linknotallowed',
        )
