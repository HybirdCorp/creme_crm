from __future__ import annotations

from json import dumps as json_dump

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.models import FakeContact
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from ..core import RegularFieldExtractor
from ..models import FetcherConfigItem, MachineConfigItem
from .base import CrudityTestCase


class CrudityViewsTestCase(BrickTestCaseMixin, CrudityTestCase):
    def test_machine_item_creation_view01(self):
        self.login_as_standard(admin_4_apps=['crudity'])
        url = reverse('crudity__create_machine_item')

        # Step 1 (GET)
        response1 = self.assertGET200(url)
        get_ctxt1 = response1.context.get
        self.assertEqual(
            pgettext('crudity', 'Create a machine'), get_ctxt1('title'),
        )
        self.assertEqual(_('Next step'), get_ctxt1('submit_label'))

        # Step 1 (POST)
        step_key = 'machine_config_item_creation_wizard-current_step'
        fetcher_item = FetcherConfigItem.objects.create(
            class_id='crudity-filesystem',
            options={'path': '/home/creme/crud_import/ini/'},
        )
        action_type = MachineConfigItem.CRUDAction.CREATE
        contact_ct = ContentType.objects.get_for_model(FakeContact)
        response1_2 = self.client.post(
            url,
            data={
                step_key: '0',

                '0-content_type': contact_ct.id,
                '0-action_type': action_type,
                '0-fetcher_item': fetcher_item.id,
            },
        )
        self.assertNoFormError(response1_2)

        # Step 2 (GET)
        context1_2 = response1_2.context
        self.assertEqual(
            pgettext('crudity', 'Save the machine'),
            context1_2.get('submit_label')
        )

        with self.assertNoException():
            extractors_f = context1_2['form'].fields['extractors']

        self.assertEqual(FakeContact, extractors_f.model)

        # Step 2 (POST)
        response2_2 = self.client.post(
            url,
            data={
                step_key: '1',

                '1-extractors': json_dump([
                    {
                        'key': 'regular_field-last_name',
                        'extractor_type': 'basic',  # TODO: use
                        # 'extractor_data': {},
                    }, {
                        'key': 'regular_field-sector',
                        'extractor_type': 'search',  # TODO: use
                        'extractor_data': {'field': 'title'},   # TODO: use
                    },
                ]),
            },
        )
        self.assertNoFormError(response2_2)

        item = self.get_object_or_fail(
            MachineConfigItem,
            content_type=contact_ct,
            action_type=action_type,
            fetcher_item=fetcher_item,
        )
        self.assertListEqual(
            [
                RegularFieldExtractor(model=FakeContact, value='last_name'),
                RegularFieldExtractor(model=FakeContact, value='sector'),
            ],
            item.extractors,
        )

    # TODO: creation of machine with fixed ctype?
    # TODO: edition
    #  - fetcher
    #  - machine
    # TODO: deletion
    #  - fetcher (beware if used in a machine)
    #  - machine (beware if used in an action??)
