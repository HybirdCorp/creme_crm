from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_config.bricks import PropertyTypesBrick
from creme.creme_core.models import CremePropertyType
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_models import FakeContact, FakeOrganisation
from creme.creme_core.tests.views.base import BrickTestCaseMixin


class PropertyTypeTestCase(BrickTestCaseMixin, CremeTestCase):
    ADD_URL = reverse('creme_config__create_ptype')

    @staticmethod
    def _build_edit_url(ptype):
        return reverse('creme_config__edit_ptype', args=(ptype.id,))

    def test_portal(self):
        self.login_as_root()

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='is hairy')
        ptype2 = create_ptype(text='is bearded')

        url = CremePropertyType.get_lv_absolute_url()
        self.assertEqual(reverse('creme_config__ptypes'), url)

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_config/portals/property-type.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url')
        )

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=PropertyTypesBrick,
        )
        self.assertInstanceLink(brick_node, ptype1)
        self.assertInstanceLink(brick_node, ptype2)

    def _find_property_type(self, prop_types, text):
        for prop_type in prop_types:
            if prop_type.text == text:
                return prop_type

        self.fail(f'No property <{text}>')

    def test_create01(self):
        self.login_as_root()

        url = self.ADD_URL
        context = self.assertGET200(url).context
        self.assertEqual(_('New custom type of property'), context.get('title'))
        self.assertEqual(CremePropertyType.save_label,     context.get('submit_label'))

        count = CremePropertyType.objects.count()

        text = 'is beautiful'
        self.assertNoFormError(self.client.post(url, data={'text': text}))

        prop_types = CremePropertyType.objects.all()
        self.assertEqual(count + 1, len(prop_types))

        prop_type = self._find_property_type(prop_types, text)
        self.assertTrue(prop_type.is_custom)
        self.assertEqual('', prop_type.description)
        self.assertFalse(prop_type.subject_ctypes.all())

    def test_create02(self):
        "ContentTypes as constraints + not superuser."
        self.login_as_standard(admin_4_apps=['creme_core'])

        get_ct = ContentType.objects.get_for_model
        models = [FakeContact, FakeOrganisation]
        text = 'is beautiful'
        description = 'causes lots of emotion'
        response = self.client.post(
            self.ADD_URL,
            data={
                'text':           text,
                'description':    description,
                'subject_ctypes': [get_ct(model).id for model in models],
            },
        )
        self.assertNoFormError(response)

        prop_type = self.get_object_or_fail(CremePropertyType, text=text)
        self.assertEqual(description, prop_type.description)
        self.assertCountEqual(models, [*prop_type.subject_models])

    def test_create03(self):
        "Not allowed."
        self.login_as_standard()
        self.assertGET403(self.ADD_URL)

    def test_edit(self):
        "Edit a custom type."
        self.login_as_root()

        pt = CremePropertyType.objects.create(
            text='is beautiful', is_custom=True,
        ).set_subject_ctypes(FakeContact)
        url = self._build_edit_url(pt)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(
            pgettext('creme_config-property', 'Edit the type «{object}»').format(object=pt),
            context.get('title'),
        )
        self.assertEqual(_('Save the modifications'), context.get('submit_label'))

        # ---
        text = 'is very beautiful'
        response = self.client.post(
            url,
            data={
                'text':           text,
                'subject_ctypes': [ContentType.objects.get_for_model(FakeOrganisation).id],
            },
        )
        self.assertNoFormError(response)

        pt = self.refresh(pt)
        self.assertEqual(text, pt.text)
        self.assertTrue(pt.is_custom)
        self.assertListEqual([FakeOrganisation], [*pt.subject_models])

    def test_edit_error01(self):
        "Edit a not custom type."
        self.login_as_root()

        pt = CremePropertyType.objects.create(
            text='is beautiful', is_custom=False,
        ).set_subject_ctypes(FakeContact)
        self.assertGET404(self._build_edit_url(pt))

    def test_edit_error02(self):
        "Edit a disabled type."
        self.login_as_root()

        pt = CremePropertyType.objects.create(
            text='is beautiful', is_custom=True, enabled=False,
        )
        self.assertGET404(self._build_edit_url(pt))

    def test_disable(self):
        self.login_as_root()

        pt = CremePropertyType.objects.create(text='is beautiful', is_custom=True)

        url = reverse('creme_config__disable_ptype', args=(pt.id,))
        self.assertGET405(url)

        self.assertPOST200(url)
        self.assertFalse(self.refresh(pt).enabled)

    def test_enable(self):
        self.login_as_root()

        pt = CremePropertyType.objects.create(
            text='is beautiful', is_custom=True, enabled=False,
        )

        url = reverse('creme_config__enable_ptype', args=(pt.id,))
        self.assertGET405(url)

        self.assertPOST200(url)
        self.assertTrue(self.refresh(pt).enabled)
