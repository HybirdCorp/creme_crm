from functools import partial

from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import ngettext

from creme.creme_core.models import FakeContact, FakeOrganisation, PinnedEntity

from ..base import CremeTestCase


@override_settings(PINNED_ENTITIES_SIZE=9)
class PinnedEntityViewsTestCase(CremeTestCase):
    def _build_pin_url(self, entity):
        return reverse('creme_core__pin_entity', args=(entity.id,))

    def test_ok(self):
        user = self.login_as_standard()
        self.add_credentials(role=user.role, own=['VIEW'])

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Sherlock', last_name='Holmes')
        contact2 = create_contact(first_name='John', last_name='Watson')

        pin_url = self._build_pin_url(contact1)
        self.assertGET405(pin_url)

        self.assertPOST200(pin_url)
        pinned1 = self.get_object_or_fail(PinnedEntity, user=user, entity=contact1)

        # ---
        unpin_url = reverse('creme_core__unpin_entity', args=(contact1.id,))
        create_pinned = PinnedEntity.objects.create
        pinned2 = create_pinned(real_entity=contact2, user=user)
        pinned3 = create_pinned(real_entity=contact1, user=self.get_root_user())

        self.assertGET405(unpin_url)

        self.assertPOST200(unpin_url)
        self.assertDoesNotExist(pinned1)
        self.assertStillExists(pinned2)
        self.assertStillExists(pinned3)

    def test_forbidden(self):
        user = self.login_as_standard()
        # self.add_credentials(role=user.role, own=['VIEW'])  # <==

        contact1 = FakeContact.objects.create(
            user=user, first_name='Sherlock', last_name='Holmes',
        )
        self.assertPOST403(reverse('creme_core__pin_entity', args=(contact1.id,)))

    def test_check_max(self):
        user = self.login_as_root_and_get()

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Sherlock', last_name='Holmes')
        contact2 = create_contact(first_name='John', last_name='Watson')
        contact3 = create_contact(first_name='Mycroft', last_name='Holmes')

        self.assertPOST200(self._build_pin_url(contact1))

        url2 = self._build_pin_url(contact2)
        with override_settings(PINNED_ENTITIES_SIZE=1):
            response2 = self.client.post(url2)
        self.assertContains(
            response2,
            status_code=409,
            text=ngettext(
                'You cannot have more than {count} pinned entity',
                'You cannot have more than {count} pinned entities',
                1,
            ).format(count=1),
            html=True,
        )

        with override_settings(PINNED_ENTITIES_SIZE=2):
            self.assertPOST200(url2)

        url3 = self._build_pin_url(contact3)
        with override_settings(PINNED_ENTITIES_SIZE=2):
            response3 = self.client.post(url3)
        self.assertContains(
            response3,
            status_code=409,
            text=ngettext(
                'You cannot have more than {count} pinned entity',
                'You cannot have more than {count} pinned entities',
                2,
            ).format(count=2),
            html=True,
        )

        PinnedEntity.objects.create(
            real_entity=FakeOrganisation.objects.create(user=user, name='Moriarty'),
            user=self.create_user(),
        )  # ignored (other user)
        with override_settings(PINNED_ENTITIES_SIZE=3):
            self.assertPOST200(url3)
