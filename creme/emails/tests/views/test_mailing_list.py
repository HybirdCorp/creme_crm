from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.models import (
    EntityFilter,
    FakeOrganisation,
    FieldsConfig,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.emails import bricks
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from ..base import (
    Contact,
    MailingList,
    Organisation,
    _EmailsTestCase,
    skipIfCustomMailingList,
)


@skipIfCustomMailingList
class MailingListsTestCase(BrickTestCaseMixin, _EmailsTestCase):
    def test_creation(self):
        user = self.login_as_root_and_get()

        url = reverse('emails__create_mlist')
        self.assertGET200(url)

        name = 'my_mailinglist'
        description = 'My friends'
        response2 = self.client.post(
            url, follow=True,
            data={
                'user': user.pk,
                'name': name,
                'description': description,
            },
        )
        self.assertNoFormError(response2)
        ml = self.get_object_or_fail(MailingList, name=name)
        self.assertEqual(description, ml.description)

        # ---
        response3 = self.assertGET200(ml.get_absolute_url())
        self.assertTemplateUsed(response3, 'emails/view_mailing_list.html')

    def test_edition(self):
        user = self.login_as_root_and_get()

        name = 'my_mailinglist'
        mlist = MailingList.objects.create(user=user, name=name)
        url = mlist.get_edit_absolute_url()
        self.assertGET200(url)

        # ---
        name += '_edited'
        response2 = self.client.post(
            url, follow=True,
            data={
                'user': user.pk,
                'name': name,
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(name, self.refresh(mlist).name)

    def test_listview(self):
        self.login_as_root()
        response = self.assertGET200(MailingList.get_lv_absolute_url())

        with self.assertNoException():
            response.context['page_obj']  # NOQA

    def test_tree(self):
        user = self.login_as_root_and_get()
        create_ml = partial(MailingList.objects.create, user=user)
        mlist01 = create_ml(name='ml01')
        mlist02 = create_ml(name='ml02')

        self.assertFalse(mlist01.children.exists())
        self.assertFalse(mlist02.children.exists())

        url = reverse('emails__add_child_mlists', args=(mlist01.id,))
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/link-popup.html')

        context = response1.context
        self.assertEqual(
            _('New child list for «{entity}»').format(entity=mlist01),
            context.get('title'),
        )
        self.assertEqual(_('Link the mailing list'), context.get('submit_label'))

        # --------------------
        self.assertPOST200(url, data={'child': mlist02.id})
        self.assertListEqual([mlist02.id], [ml.id for ml in mlist01.children.all()])
        self.assertFalse(mlist02.children.exists())

        # Children Brick -----------------
        response3 = self.assertGET200(mlist01.get_absolute_url())
        children_brick_node = self.get_brick_node(
            self.get_html_tree(response3.content), brick=bricks.ChildListsBrick,
        )
        self.assertBrickTitleEqual(
            children_brick_node,
            count=1,
            title='{count} Child List',
            plural_title='{count} Child Lists',
        )
        self.assertInstanceLink(children_brick_node, mlist02)

        # Parents Brick -----------------
        response4 = self.assertGET200(mlist02.get_absolute_url())
        parents_brick_node = self.get_brick_node(
            self.get_html_tree(response4.content), brick=bricks.ParentListsBrick,
        )
        self.assertBrickTitleEqual(
            parents_brick_node,
            count=1,
            title='{count} Parent List',
            plural_title='{count} Parent Lists',
        )
        self.assertInstanceLink(parents_brick_node, mlist01)

        # --------------------
        self.assertPOST200(
            reverse('emails__remove_child_mlist', args=(mlist01.id,)),
            data={'id': mlist02.id}, follow=True,
        )
        self.assertFalse(mlist01.children.exists())
        self.assertFalse(mlist02.children.exists())

    def test_tree__errors(self):
        user = self.login_as_root_and_get()
        create_ml = partial(MailingList.objects.create, user=user)
        mlist01 = create_ml(name='ml01')
        mlist02 = create_ml(name='ml02')
        mlist03 = create_ml(name='ml03')

        mlist01.children.add(mlist02)
        mlist02.children.add(mlist03)

        def post(parent, child):
            response = self.client.post(
                reverse('emails__add_child_mlists', args=(parent.id,)),
                data={'child': child.id},
            )
            return self.get_form_or_fail(response)

        children_error = _('List already in the children')
        self.assertFormError(post(mlist01, mlist02), field='child', errors=children_error)
        self.assertFormError(post(mlist01, mlist03), field='child', errors=children_error)

        parents_error = _('List already in the parents')
        self.assertFormError(post(mlist02, mlist01), field='child', errors=parents_error)
        self.assertFormError(post(mlist03, mlist01), field='child', errors=parents_error)
        self.assertFormError(
            post(mlist01, mlist01), field='child', errors=_("A list can't be its own child")
        )

    def test_tree__bad_type(self):
        "Not a MailingList."
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='Dojo')
        self.assertGET404(reverse('emails__add_child_mlists', args=(orga.id,)))


@skipIfCustomContact
@skipIfCustomMailingList
class MailingListContactsTestCase(BrickTestCaseMixin, _EmailsTestCase):
    @staticmethod
    def _build_add_contacts_url(mlist):
        return reverse('emails__add_contacts_to_mlist', args=(mlist.id,))

    @staticmethod
    def _build_add_contacts_from_filter_url(mlist):
        return reverse('emails__add_contacts_to_mlist_from_filter', args=(mlist.id,))

    def test_related_contacts(self):
        user = self.login_as_emails_user(allowed_apps=('persons',))
        self.add_credentials(user.role, all=['VIEW', 'CHANGE', 'LINK'])

        mlist = MailingList.objects.create(user=user, name='ml01')
        url = self._build_add_contacts_url(mlist)

        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/link-popup.html')

        context = response1.context
        self.assertEqual(
            _('New contacts for «{entity}»').format(entity=mlist),
            context.get('title')
        )
        self.assertEqual(_('Link the contacts'), context.get('submit_label'))

        create = partial(Contact.objects.create, user=user)
        recipients = [
            create(first_name='Spike', last_name='Spiegel', email='spike.spiegel@bebop.com'),
            create(first_name='Jet',   last_name='Black',   email='jet.black@bebop.com'),
        ]

        response2 = self.client.post(
            url, data={'recipients': self.formfield_value_multi_creator_entity(*recipients)},
        )
        self.assertNoFormError(response2)
        self.assertCountEqual(recipients, mlist.contacts.all())

        # Brick -----------------
        response3 = self.assertGET200(mlist.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response3.content), brick=bricks.ContactsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=2,
            title='{count} Contact-recipient',
            plural_title='{count} Contact-recipients',
        )

        # --------------------
        contact_to_del = recipients[0]
        self.client.post(
            reverse('emails__remove_contact_from_mlist', args=(mlist.id,)),
            data={'id': contact_to_del.id},
        )

        contacts = {*mlist.contacts.all()}
        self.assertEqual(len(recipients) - 1, len(contacts))
        self.assertNotIn(contact_to_del, contacts)

    def test_add_contacts__hidden_email(self):
        "'email' is hidden."
        user = self.login_as_root_and_get()
        mlist = MailingList.objects.create(user=user, name='ml01')

        FieldsConfig.objects.create(
            content_type=Contact,
            descriptions=[('email', {FieldsConfig.HIDDEN: True})],
        )
        self.assertGET409(self._build_add_contacts_url(mlist))

    def test_add_contacts__bad_type(self):
        "Not a MailingList."
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='Dojo')
        self.assertGET404(self._build_add_contacts_url(orga))

    def test_add_contacts_from_filter__all(self):
        "<All> filter."
        user = self.login_as_root_and_get()
        mlist = MailingList.objects.create(user=user, name='ml01')
        url = self._build_add_contacts_from_filter_url(mlist)

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context = response.context
        self.assertEqual(
            _('New contacts for «{entity}»').format(entity=mlist),
            context.get('title')
        )
        self.assertEqual(_('Link the contacts'), context.get('submit_label'))

        create = partial(Contact.objects.create, user=user)
        create(first_name='Spike', last_name='Spiegel', email='spike.spiegel@bebop.com'),
        create(first_name='Jet', last_name='Black', email='jet.black@bebop.com'),
        create(first_name='Ed', last_name='Wong', email='ed.wong@bebop.com', is_deleted=True),
        self.assertNoFormError(self.client.post(url, data={}))

        contacts = Contact.objects.filter(is_deleted=False)
        self.assertGreaterEqual(len(contacts), 2)
        self.assertCountEqual(contacts, mlist.contacts.all())

    def test_add_contacts_from_filter__efilter(self):
        "With a real EntityFilter."
        user = self.login_as_root_and_get()
        create = partial(Contact.objects.create, user=user)
        recipients = [
            create(first_name='Ranma', last_name='Saotome'),
            create(first_name='Genma', last_name='Saotome'),
            create(first_name='Akane', last_name='Tendô'),
        ]
        expected_ids = {recipients[0].id, recipients[1].id}

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Saotome', Contact, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=Contact,
                    operator=operators.IEQUALS,
                    field_name='last_name', values=['Saotome'],
                ),
            ],
        )
        self.assertSetEqual(expected_ids, {c.id for c in efilter.filter(Contact.objects.all())})

        EntityFilter.objects.smart_update_or_create(
            'test-filter02', 'Useless', Organisation, is_custom=True,
        )  # Should not be a valid choice

        mlist = MailingList.objects.create(user=user, name='ml01')

        url = self._build_add_contacts_from_filter_url(mlist)
        context = self.client.get(url).context

        with self.assertNoException():
            choices = [*context['form'].fields['filters'].choices]

        self.assertListEqual(
            [
                ('', pgettext('creme_core-filter', 'All')),
                *(
                    (ef.id, ef.name)
                    for ef in EntityFilter.objects.filter(
                        entity_type=ContentType.objects.get_for_model(Contact),
                    )
                ),
            ],
            choices
        )

        self.assertNoFormError(self.client.post(url, data={'filters': efilter.id}))
        self.assertSetEqual(expected_ids, {c.id for c in mlist.contacts.all()})

    def test_add_contacts_from_filter__hidden_email(self):
        "'email' is hidden."
        user = self.login_as_root_and_get()
        mlist = MailingList.objects.create(user=user, name='ml01')
        FieldsConfig.objects.create(
            content_type=Contact,
            descriptions=[('email', {FieldsConfig.HIDDEN: True})],
        )
        self.assertGET409(self._build_add_contacts_from_filter_url(mlist))

    def test_add_contacts_from_filter__bad_type(self):
        "Not a MailingList."
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='Dojo')
        self.assertGET404(self._build_add_contacts_from_filter_url(orga))

    def test_forbidden(self):
        "Not allowed to change the list."
        user = self.login_as_emails_user(allowed_apps=('persons',))
        self.add_credentials(user.role, all=['VIEW', 'LINK'])

        contact = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel', email='spike.spiegel@bebop.com',
        )

        mlist = MailingList.objects.create(user=user, name='ml01')
        mlist.contacts.add(contact)

        self.assertPOST403(
            reverse('emails__remove_contact_from_mlist', args=(mlist.id,)),
            data={'id': contact.id}, follow=True,
        )


@skipIfCustomOrganisation
@skipIfCustomMailingList
class MailingListOrganisationsTestCase(BrickTestCaseMixin, _EmailsTestCase):
    @staticmethod
    def _build_add_orgas_url(mlist):
        return reverse('emails__add_orgas_to_mlist', args=(mlist.id,))

    @staticmethod
    def _build_add_orgas_from_filter_url(mlist):
        return reverse('emails__add_orgas_to_mlist_from_filter', args=(mlist.id,))

    def test_related_organisations(self):
        user = self.login_as_root_and_get()
        mlist = MailingList.objects.create(user=user, name='ml01')
        url = self._build_add_orgas_url(mlist)

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context1 = response.context
        self.assertEqual(
            _('New organisations for «{entity}»').format(entity=mlist),
            context1.get('title')
        )
        self.assertEqual(_('Link the organisations'), context1.get('submit_label'))

        # ---
        create = partial(Organisation.objects.create, user=user)
        recipients = [
            create(name='NERV',  email='contact@nerv.jp'),
            create(name='Seele', email='contact@seele.jp'),
        ]
        response2 = self.client.post(
            url,
            data={'recipients': self.formfield_value_multi_creator_entity(*recipients)},
        )
        self.assertNoFormError(response2)
        self.assertCountEqual(recipients, mlist.organisations.all())

        # Brick -----------------
        response3 = self.assertGET200(mlist.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response3.content), brick=bricks.OrganisationsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=2,
            title='{count} Organisation-recipient',
            plural_title='{count} Organisation-recipients',
        )

        # --------------------
        orga_to_del = recipients[0]
        self.client.post(
            reverse('emails__remove_orga_from_mlist', args=(mlist.id,)),
            data={'id': orga_to_del.id}
        )

        orgas = {*mlist.organisations.all()}
        self.assertEqual(len(recipients) - 1, len(orgas))
        self.assertNotIn(orga_to_del, orgas)

    def test_add_organisations__hidden_email(self):
        "'email' is hidden."
        user = self.login_as_root_and_get()
        mlist = MailingList.objects.create(user=user, name='ml01')

        FieldsConfig.objects.create(
            content_type=Organisation,
            descriptions=[('email', {FieldsConfig.HIDDEN: True})],
        )
        self.assertGET409(self._build_add_orgas_url(mlist))

    def test_add_organisations__bad_type(self):
        "Not a MailingList."
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='Dojo')
        self.assertGET404(self._build_add_orgas_url(orga))

    def test_add_organisations_from_filter__all(self):
        "<All> filter."
        user = self.login_as_root_and_get()
        mlist = MailingList.objects.create(user=user, name='ml01')
        url = self._build_add_orgas_from_filter_url(mlist)

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context = response.context
        self.assertEqual(
            _('New organisations for «{entity}»').format(entity=mlist),
            context.get('title')
        )
        self.assertEqual(_('Link the organisations'), context.get('submit_label'))

        create_orga = partial(Organisation.objects.create, user=user)
        create_orga(name='NERV',  email='contact@nerv.jp'),
        create_orga(name='Seele', email='contact@seele.jp')
        self.assertNoFormError(self.client.post(url, data={}))

        orgas = Organisation.objects.all()
        self.assertGreaterEqual(len(orgas), 2)
        self.assertCountEqual(orgas, mlist.organisations.all())

    def test_add_organisations_from_filter__efilter(self):
        "With a real EntityFilter."
        user = self.login_as_root_and_get()
        mlist = MailingList.objects.create(user=user, name='ml01')

        create = partial(Organisation.objects.create, user=user)
        recipients = [
            create(name='NERV',  email='contact@nerv.jp'),
            create(name='Seele', email='contact@seele.jp'),
            create(name='Bebop'),
        ]
        expected_ids = {recipients[0].id, recipients[1].id}

        create_ef = partial(
            EntityFilter.objects.smart_update_or_create,
            name='Has email',
            model=Organisation, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=Organisation,
                    operator=operators.ISEMPTY,
                    field_name='email', values=[False],
                ),
            ],
        )
        priv_efilter = create_ef(pk='test-filter_priv', is_private=True, user=self.create_user())

        efilter = create_ef(pk='test-filter')
        self.assertSetEqual(
            expected_ids,
            {c.id for c in efilter.filter(Organisation.objects.all())},
        )

        url = self._build_add_orgas_from_filter_url(mlist)
        response1 = self.assertPOST200(url, data={'filters': priv_efilter.id})
        self.assertFormError(
            response1.context['form'],
            field='filters',
            errors=_(
                'Select a valid choice. That choice is not one of the available choices.'
            ),
        )

        # ---
        response2 = self.client.post(url, data={'filters': efilter.id})
        self.assertNoFormError(response2)
        self.assertEqual(expected_ids, {c.id for c in mlist.organisations.all()})

    def test_add_organisations_from_filter__hidden_email(self):
        "'email' is hidden."
        user = self.login_as_root_and_get()
        mlist = MailingList.objects.create(user=user, name='ml01')

        FieldsConfig.objects.create(
            content_type=Organisation,
            descriptions=[('email', {FieldsConfig.HIDDEN: True})],
        )
        self.assertGET409(self._build_add_orgas_from_filter_url(mlist))

    def test_add_organisations_from_filter__bad_type(self):
        "Not a MailingList."
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='Dojo')
        self.assertGET404(self._build_add_orgas_from_filter_url(orga))
