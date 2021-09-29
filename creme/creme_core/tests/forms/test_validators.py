# -*- coding: utf-8 -*-

from functools import partial

from django.contrib.auth import get_user
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.forms import validators
from creme.creme_core.models import CremeUser, FakeContact
from creme.creme_core.models.auth import SetCredentials

from ..base import CremeTestCase


class CredsValidatorTestCase(CremeTestCase):
    @staticmethod
    def _set_user_credentials(user, credentials, coverage):
        SetCredentials.objects.create(
            role=user.role, value=credentials, set_type=coverage,
        )

    def test_validate_none_user(self):
        with self.assertRaises(ValidationError) as e:
            validators.validate_authenticated_user(
                None, 'nobody', code='viewnotallowed',
            )

        self.assertEqual(e.exception.message, 'nobody')
        self.assertEqual(e.exception.code, 'viewnotallowed')

    def test_validate_anonymous_user(self):
        user = get_user(self.client)
        self.assertTrue(user.is_anonymous)

        with self.assertRaises(ValidationError) as e:
            validators.validate_authenticated_user(
                None, 'we are legion', code='viewnotallowed',
            )

        self.assertEqual(e.exception.message, 'we are legion')
        self.assertEqual(e.exception.code, 'viewnotallowed')

    def test_validate_authenticated_user(self):
        user = self.login(is_superuser=False)
        with self.assertNoException():
            validators.validate_authenticated_user(
                user, 'none or anonymous not allowed', code='viewnotallowed',
            )

    def test_validate_viewable_entity_owner(self):
        user = self.login(is_superuser=False)
        a = FakeContact.objects.create(last_name='Doe', first_name='John', user=user)

        # view permission set for owned entities
        self._set_user_credentials(user, EntityCredentials.VIEW, SetCredentials.ESET_OWN)

        with self.assertNoException():
            validators.validate_viewable_entity(a, user)

    def test_validate_viewable_entity_allowed(self):
        user = self.login(is_superuser=False)
        a = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=self.other_user,
        )

        # view permission set for all entities
        self._set_user_credentials(user, EntityCredentials.VIEW, SetCredentials.ESET_ALL)

        with self.assertNoException():
            validators.validate_viewable_entity(a, user)

    def test_validate_viewable_entity_anonymous(self):
        other_user = CremeUser.objects.create(username='other')
        a = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=other_user,
        )

        user = get_user(self.client)
        self.assertTrue(user.is_anonymous)

        with self.assertRaises(ValidationError) as e:
            validators.validate_viewable_entity(a, user)

        self.assertEqual(
            e.exception.message,
            _('Not authenticated user is not allowed to view entities'),
        )
        self.assertEqual(e.exception.code, 'viewnotallowed')

    def test_validate_viewable_entity_notallowed_other(self):
        user = self.login(is_superuser=False)
        a = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=self.other_user,
        )

        self._set_user_credentials(user, EntityCredentials.VIEW, SetCredentials.ESET_OWN)

        # view permission set for owned entities
        with self.assertRaises(ValidationError) as e:
            validators.validate_viewable_entity(a, user)

        self.assertEqual(e.exception.code, 'viewnotallowed')

    def test_validate_viewable_entity_notallowed_all(self):
        user = self.login(is_superuser=False)
        a = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=self.other_user,
        )

        self._set_user_credentials(user, EntityCredentials.CHANGE, SetCredentials.ESET_ALL)

        # view permission not set
        with self.assertRaises(ValidationError) as e:
            validators.validate_viewable_entity(a, user)

        self.assertEqual(e.exception.code, 'viewnotallowed')

    def test_validate_viewable_entities_owner(self):
        user = self.login(is_superuser=False)
        a = FakeContact.objects.create(last_name='Doe', first_name='A', user=user)
        b = FakeContact.objects.create(last_name='Doe', first_name='B', user=user)

        self._set_user_credentials(user, EntityCredentials.VIEW,  SetCredentials.ESET_OWN)

        with self.assertNoException():
            validators.validate_viewable_entities([a, b], user)

    def test_validate_viewable_entities_allowed(self):
        user = self.login(is_superuser=False)
        a = FakeContact.objects.create(last_name='Doe', first_name='A', user=self.other_user)
        b = FakeContact.objects.create(last_name='Doe', first_name='B', user=self.other_user)

        self._set_user_credentials(user, EntityCredentials.VIEW,  SetCredentials.ESET_ALL)

        with self.assertNoException():
            validators.validate_viewable_entities([a, b], user)

    def test_validate_viewable_entities_anonymous(self):
        other_user = CremeUser.objects.create(username='other')
        a = FakeContact.objects.create(last_name='Doe', first_name='John', user=other_user)
        b = FakeContact.objects.create(last_name='Doe', first_name='B', user=other_user)

        user = get_user(self.client)
        self.assertTrue(user.is_anonymous)

        with self.assertRaises(ValidationError) as e:
            validators.validate_viewable_entities([a, b], user)

        self.assertEqual(e.exception.code, 'viewnotallowed')

    def test_validate_viewable_entities_notallowed_other(self):
        user = self.login(is_superuser=False)

        create_contact = partial(FakeContact.objects.create, user=self.other_user)
        a = create_contact(last_name='Doe', first_name='John')
        b = create_contact(last_name='Doe', first_name='B')

        self._set_user_credentials(user, EntityCredentials.VIEW,  SetCredentials.ESET_OWN)

        with self.assertRaises(ValidationError) as e:
            validators.validate_viewable_entities([a, b], user)

        self.assertEqual(e.exception.code, 'viewnotallowed')

    def test_validate_viewable_entities_notallowed_all(self):
        user = self.login(is_superuser=False)

        create_contact = partial(FakeContact.objects.create, user=self.other_user)
        a = create_contact(last_name='Doe', first_name='John')
        b = create_contact(last_name='Doe', first_name='B')

        self._set_user_credentials(user, EntityCredentials.CHANGE,  SetCredentials.ESET_ALL)

        with self.assertRaises(ValidationError) as e:
            validators.validate_viewable_entities([a, b], user)

        self.assertEqual(e.exception.code, 'viewnotallowed')

    def test_validate_editable_entity_owner(self):
        user = self.login(is_superuser=False)
        a = FakeContact.objects.create(last_name='Doe', first_name='John', user=user)

        self._set_user_credentials(
            user, EntityCredentials.CHANGE, SetCredentials.ESET_OWN,
        )

        with self.assertNoException():
            validators.validate_editable_entity(a, user)

    def test_validate_editable_entity_allowed(self):
        user = self.login(is_superuser=False)
        a = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=self.other_user,
        )

        self._set_user_credentials(
            user, EntityCredentials.CHANGE, SetCredentials.ESET_ALL,
        )

        with self.assertNoException():
            validators.validate_editable_entity(a, user)

    def test_validate_editable_entity_anonymous(self):
        other_user = CremeUser.objects.create(username='other')
        a = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=other_user,
        )

        user = get_user(self.client)
        self.assertTrue(user.is_anonymous)

        with self.assertRaises(ValidationError) as e:
            validators.validate_editable_entity(a, user)

        self.assertEqual(
            e.exception.message,
            _('Not authenticated user is not allowed to edit entities')
        )
        self.assertEqual(e.exception.code, 'changenotallowed')

    def test_validate_editable_entity_notallowed_other(self):
        user = self.login(is_superuser=False)
        a = FakeContact.objects.create(last_name='Doe', first_name='John', user=self.other_user)

        self._set_user_credentials(user, EntityCredentials.CHANGE, SetCredentials.ESET_OWN)

        with self.assertRaises(ValidationError) as e:
            validators.validate_editable_entity(a, user)

        self.assertEqual(e.exception.code, 'changenotallowed')

    def test_validate_editable_entity_notallowed_all(self):
        user = self.login(is_superuser=False)
        a = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=self.other_user,
        )

        self._set_user_credentials(
            user, EntityCredentials.VIEW, SetCredentials.ESET_ALL,
        )

        with self.assertRaises(ValidationError) as e:
            validators.validate_editable_entity(a, user)

        self.assertEqual(e.exception.code, 'changenotallowed')

    def test_validate_editable_entities_owner(self):
        user = self.login(is_superuser=False)

        create_contact = partial(FakeContact.objects.create, user=user)
        a = create_contact(last_name='Doe', first_name='A')
        b = create_contact(last_name='Doe', first_name='B')

        self._set_user_credentials(
            user, EntityCredentials.CHANGE, SetCredentials.ESET_OWN,
        )

        with self.assertNoException():
            validators.validate_editable_entities([a, b], user)

    def test_validate_editable_entities_anonymous(self):
        other_user = CremeUser.objects.create(username='other')

        create_contact = partial(FakeContact.objects.create, user=other_user)
        a = create_contact(last_name='Doe', first_name='John')
        b = create_contact(last_name='Doe', first_name='B')

        user = get_user(self.client)
        self.assertTrue(user.is_anonymous)

        with self.assertRaises(ValidationError) as e:
            validators.validate_editable_entities([a, b], user)

        self.assertEqual(e.exception.code, 'changenotallowed')

    def test_validate_editable_entities_notallowed_other(self):
        user = self.login(is_superuser=False)

        create_contact = partial(FakeContact.objects.create, user=self.other_user)
        a = create_contact(last_name='Doe', first_name='John')
        b = create_contact(last_name='Doe', first_name='B')

        self._set_user_credentials(user, EntityCredentials.CHANGE, SetCredentials.ESET_OWN)

        with self.assertRaises(ValidationError) as e:
            validators.validate_editable_entities([a, b], user)

        self.assertEqual(e.exception.code, 'changenotallowed')

    def test_validate_editable_entities_notallowed_all(self):
        user = self.login(is_superuser=False)

        create_contact = partial(FakeContact.objects.create, user=self.other_user)
        a = create_contact(last_name='Doe', first_name='John')
        b = create_contact(last_name='Doe', first_name='B')

        self._set_user_credentials(user, EntityCredentials.VIEW, SetCredentials.ESET_ALL)

        with self.assertRaises(ValidationError) as e:
            validators.validate_editable_entities([a, b], user)

        self.assertEqual(e.exception.code, 'changenotallowed')

    def test_validate_linkable_entity_owner(self):
        user = self.login(is_superuser=False)
        a = FakeContact.objects.create(last_name='Doe', first_name='John', user=user)

        self._set_user_credentials(
            user, EntityCredentials.LINK, SetCredentials.ESET_OWN,
        )

        with self.assertNoException():
            validators.validate_linkable_entity(a, user)

    def test_validate_linkable_entity_allowed(self):
        user = self.login(is_superuser=False)
        a = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=self.other_user,
        )

        self._set_user_credentials(
            user, EntityCredentials.LINK, SetCredentials.ESET_ALL,
        )

        with self.assertNoException():
            validators.validate_linkable_entity(a, user)

    def test_validate_linkable_entity_anonymous(self):
        other_user = CremeUser.objects.create(username='other')
        a = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=other_user,
        )

        user = get_user(self.client)
        self.assertTrue(user.is_anonymous)

        with self.assertRaises(ValidationError) as e:
            validators.validate_linkable_entity(a, user)

        self.assertEqual(
            e.exception.message,
            _('Not authenticated user is not allowed to link entities'),
        )
        self.assertEqual(e.exception.code, 'linknotallowed')

    def test_validate_linkable_entity_notallowed_other(self):
        user = self.login(is_superuser=False)
        a = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=self.other_user,
        )

        self._set_user_credentials(
            user, EntityCredentials.LINK, SetCredentials.ESET_OWN,
        )

        with self.assertRaises(ValidationError) as e:
            validators.validate_linkable_entity(a, user)

        self.assertEqual(e.exception.code, 'linknotallowed')

    def test_validate_linkable_entity_notallowed_all(self):
        user = self.login(is_superuser=False)
        a = FakeContact.objects.create(
            last_name='Doe', first_name='John', user=self.other_user,
        )

        self._set_user_credentials(
            user, EntityCredentials.VIEW, SetCredentials.ESET_ALL,
        )

        with self.assertRaises(ValidationError) as e:
            validators.validate_linkable_entity(a, user)

        self.assertEqual(e.exception.code, 'linknotallowed')

    def test_validate_linkable_entities_owner(self):
        user = self.login(is_superuser=False)

        create_contact = partial(FakeContact.objects.create, user=user)
        a = create_contact(last_name='Doe', first_name='A')
        b = create_contact(last_name='Doe', first_name='B')

        self._set_user_credentials(
            user, EntityCredentials.LINK, SetCredentials.ESET_OWN,
        )

        with self.assertNoException():
            validators.validate_linkable_entities([a, b], user)

    def test_validate_linkable_entities_allowed(self):
        user = self.login(is_superuser=False)

        create_contact = partial(FakeContact.objects.create, user=self.other_user)
        a = create_contact(last_name='Doe', first_name='A')
        b = create_contact(last_name='Doe', first_name='B')

        self._set_user_credentials(
            user, EntityCredentials.LINK, SetCredentials.ESET_ALL,
        )

        with self.assertNoException():
            validators.validate_linkable_entities([a, b], user)

    def test_validate_linkable_entities_anonymous(self):
        other_user = CremeUser.objects.create(username='other')

        create_contact = partial(FakeContact.objects.create, user=other_user)
        a = create_contact(last_name='Doe', first_name='John')
        b = create_contact(last_name='Doe', first_name='B')

        user = get_user(self.client)
        self.assertTrue(user.is_anonymous)

        with self.assertRaises(ValidationError) as e:
            validators.validate_linkable_entities([a, b], user)

        self.assertEqual(
            e.exception.message,
            _('Not authenticated user is not allowed to link entities'),
        )
        self.assertEqual(e.exception.code, 'linknotallowed')

    def test_validate_linkable_entities_notallowed_other(self):
        user = self.login(is_superuser=False)

        create_contact = partial(FakeContact.objects.create, user=self.other_user)
        a = create_contact(last_name='Doe', first_name='John')
        b = create_contact(last_name='Doe', first_name='B')

        self._set_user_credentials(
            user, EntityCredentials.LINK, SetCredentials.ESET_OWN,
        )

        with self.assertRaises(ValidationError) as e:
            validators.validate_linkable_entities([a, b], user)

        self.assertEqual(e.exception.code, 'linknotallowed')

    def test_validate_linkable_entities_notallowed_all(self):
        user = self.login(is_superuser=False)

        create_contact = partial(FakeContact.objects.create, user=self.other_user)
        a = create_contact(last_name='Doe', first_name='John')
        b = create_contact(last_name='Doe', first_name='B')

        self._set_user_credentials(
            user, EntityCredentials.VIEW, SetCredentials.ESET_ALL,
        )

        with self.assertRaises(ValidationError) as e:
            validators.validate_linkable_entities([a, b], user)

        self.assertEqual(e.exception.code, 'linknotallowed')

    def test_validate_linkable_model(self):
        user = self.login(is_superuser=False)
        self._set_user_credentials(
            user, EntityCredentials.LINK, SetCredentials.ESET_OWN,
        )

        with self.assertNoException():
            validators.validate_linkable_model(FakeContact, user, user)

    def test_validate_linkable_model_allowed(self):
        user = self.login(is_superuser=False)
        self._set_user_credentials(
            user, EntityCredentials.LINK, SetCredentials.ESET_ALL,
        )

        with self.assertNoException():
            validators.validate_linkable_model(FakeContact, user, self.other_user)

    def test_validate_linkable_model_anonymous(self):
        user = get_user(self.client)
        self.assertTrue(user.is_anonymous)

        with self.assertRaises(ValidationError) as e:
            validators.validate_linkable_model(FakeContact, user, user)

        self.assertEqual(
            e.exception.message,
            _('Not authenticated user is not allowed to link «{model}»').format(
                model=FakeContact._meta.verbose_name_plural,
            )
        )

        self.assertEqual(e.exception.code, 'linknotallowed')

    def test_validate_linkable_model_notallowed_other(self):
        user = self.login(is_superuser=False)
        self._set_user_credentials(
            user, EntityCredentials.LINK, SetCredentials.ESET_OWN,
        )

        with self.assertRaises(ValidationError) as e:
            validators.validate_linkable_model(FakeContact, user, self.other_user)

        self.assertEqual(e.exception.code, 'linknotallowed')

    def test_validate_linkable_model_notallowed_all(self):
        user = self.login(is_superuser=False)
        self._set_user_credentials(
            user, EntityCredentials.VIEW, SetCredentials.ESET_ALL,
        )

        with self.assertRaises(ValidationError) as e:
            validators.validate_linkable_model(FakeContact, user, user)

        self.assertEqual(e.exception.code, 'linknotallowed')
