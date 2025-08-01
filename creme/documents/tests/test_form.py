from json import dumps as json_dump

from django.db.models.query_utils import Q
from django.forms import Field
from django.urls import reverse
from django.utils.translation import gettext as _

from ..forms.fields import ImageEntityField, MultiImageEntityField
from .base import Document, _DocumentsTestCase


class ImageEntityFieldTestCase(_DocumentsTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.login_as_root_and_get()

    def test_init01(self):
        "Not required."
        with self.assertNumQueries(0):
            field = ImageEntityField(required=False)

        self.assertFalse(field.required)
        self.assertEqual(Document, field.model)
        self.assertEqual(Document, field.widget.model)
        self.assertTrue(field.force_creation)
        self.assertQEqual(Q(mime_type__name__startswith='image/'), field.q_filter)

        url = reverse('documents__create_image_popup')
        self.assertEqual(url, field.create_action_url)
        self.assertFalse(field.widget.creation_url)
        self.assertFalse(field.widget.creation_allowed)

        field.user = self.user
        self.assertEqual(url, field.widget.creation_url)
        self.assertTrue(field.widget.creation_allowed)

    def test_clean01(self):
        "Not required."
        field = ImageEntityField(required=False)
        field.user = self.user
        self.assertIsNone(field.clean(''))

        img = self._create_image(user=self.user)
        self.assertEqual(img, field.clean(str(img.id)))

        doc = self._create_doc('foobar.txt', user=self.user)
        self.assertIsNone(field.clean(''))
        self.assertFormfieldError(
            field=field, value=str(doc.id),
            codes='isexcluded',
            messages=_('«%(entity)s» violates the constraints.') % {'entity': str(doc)},
        )

    def test_clean02(self):
        "Required."
        field = ImageEntityField(user=self.user)
        self.assertTrue(field.required)
        self.assertFormfieldError(
            field=field, value='',
            codes='required', messages=Field.default_error_messages['required'],
        )

        doc = self._create_doc('foobar.txt', user=self.user)
        self.assertFormfieldError(
            field=field, value=str(doc.id),
            messages=_('«%(entity)s» violates the constraints.') % {'entity': str(doc)},
            codes='isexcluded',
        )

    def test_qfilter_init01(self):
        "Dict."
        field = ImageEntityField(user=self.user, q_filter={'title__icontains': 'show'})

        final_qfilter = Q(mime_type__name__startswith='image/') & Q(title__icontains='show')
        self.assertQEqual(final_qfilter, field.q_filter)
        self.assertFalse(field.force_creation)

        # Widget
        self.assertQEqual(final_qfilter, field.widget.q_filter)
        self.assertFalse(field.widget.creation_url)
        self.assertTrue(field.widget.creation_allowed)

        # Clean
        img1 = self._create_image(title='Icon#1', ident=1, user=self.user)
        self.assertFormfieldError(
            field=field, value=str(img1.id),
            messages=_('«%(entity)s» violates the constraints.')  % {'entity': str(img1)},
            codes='isexcluded',
        )

        img2 = self._create_image(title='Python Show 2018', ident=2, user=self.user)
        self.assertEqual(img2, field.clean(str(img2.id)))

    def test_qfilter_init02(self):
        "Q"
        field = ImageEntityField(user=self.user, q_filter=Q(title__icontains='show'))

        final_qfilter = Q(mime_type__name__startswith='image/') & Q(title__icontains='show')
        self.assertQEqual(final_qfilter, field.q_filter)
        self.assertFalse(field.force_creation)

        # Widget
        self.assertQEqual(final_qfilter, field.widget.q_filter)
        self.assertFalse(field.widget.creation_url)
        self.assertTrue(field.widget.creation_allowed)

        # Clean
        img1 = self._create_image(title='Icon#1', ident=1, user=self.user)
        self.assertFormfieldError(
            field=field, value=str(img1.id),
            codes='isexcluded',
            messages=_('«%(entity)s» violates the constraints.') % {'entity': str(img1)},
        )

        img2 = self._create_image(title='Python Show 2018', ident=2, user=self.user)
        self.assertEqual(img2, field.clean(str(img2.id)))

    def test_qfilter_property01(self):
        "Dict."
        field = ImageEntityField(user=self.user)
        field.q_filter = {'title__contains': 'show'}

        final_qfilter = Q(mime_type__name__startswith='image/') & Q(title__contains='show')
        self.assertQEqual(final_qfilter, field.q_filter)
        self.assertFalse(field.force_creation)

        # Widget
        self.assertQEqual(final_qfilter, field.widget.q_filter)
        self.assertFalse(field.widget.creation_url)
        self.assertTrue(field.widget.creation_allowed)

        # Clean
        img1 = self._create_image(title='Icon#1', user=self.user)
        self.assertFormfieldError(
            field=field, value=str(img1.id),
            codes='isexcluded',
            messages=_('«%(entity)s» violates the constraints.') % {'entity': str(img1)},
        )

        img2 = self._create_image(title='Python show 2018', user=self.user)
        self.assertEqual(img2, field.clean(str(img2.id)))

    def test_qfilter_property02(self):
        "Q."
        field = ImageEntityField(user=self.user)
        field.q_filter = Q(title__contains='show')

        final_qfilter = Q(mime_type__name__startswith='image/') & Q(title__contains='show')
        self.assertQEqual(final_qfilter, field.q_filter)
        self.assertFalse(field.force_creation)

        # Widget
        self.assertQEqual(final_qfilter, field.widget.q_filter)
        self.assertFalse(field.widget.creation_url)
        self.assertTrue(field.widget.creation_allowed)

        # Clean
        img1 = self._create_image(title='Icon#1', user=self.user)
        self.assertFormfieldError(
            field=field, value=str(img1.id),
            codes='isexcluded',
            messages=_('«%(entity)s» violates the constraints.') % {'entity': str(img1)},
        )

        img2 = self._create_image(title='Python show 2018', user=self.user)
        self.assertEqual(img2, field.clean(str(img2.id)))

    def test_force_creation(self):
        field = ImageEntityField(user=self.user)
        self.assertTrue(field.force_creation)

        url = reverse('documents__create_image_popup')
        self.assertEqual(url, field.widget.creation_url)
        self.assertTrue(field.widget.creation_allowed)

        field.force_creation = False
        self.assertFalse(field.widget.creation_url)

        field.force_creation = True
        self.assertEqual(url, field.widget.creation_url)

    def test_creation_url_init(self):
        creation_url = '/documents/create_image_v2/'

        field = ImageEntityField(create_action_url=creation_url)
        self.assertEqual(creation_url, field.create_action_url)
        self.assertFalse(field.widget.creation_url)
        self.assertTrue(field.force_creation)

        field.user = self.user
        self.assertEqual(creation_url, field.widget.creation_url)

    def test_creation_url_property(self):
        creation_url = '/documents/create_image_v2/'

        field = ImageEntityField()
        field.create_action_url = creation_url
        self.assertEqual(creation_url, field.create_action_url)
        self.assertFalse(field.widget.creation_url)
        self.assertTrue(field.force_creation)

        field.user = self.user
        self.assertEqual(creation_url, field.widget.creation_url)
        self.assertTrue(field.widget.creation_allowed)
        self.assertEqual(_('Create an image'), field.widget.creation_label)


class MultiImageEntityFieldTestCase(_DocumentsTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.login_as_root_and_get()

    @staticmethod
    def _build_value(*docs):
        return json_dump([doc.id for doc in docs])

    def test_init01(self):
        "Not required."
        with self.assertNumQueries(0):
            field = MultiImageEntityField(required=False)

        self.assertFalse(field.required)
        self.assertEqual(Document, field.model)
        self.assertEqual(Document, field.widget.model)
        self.assertTrue(field.force_creation)
        self.assertQEqual(Q(mime_type__name__startswith='image/'), field.q_filter)

        url = reverse('documents__create_image_popup')
        self.assertEqual(url, field.create_action_url)
        self.assertFalse(field.widget.creation_url)
        self.assertFalse(field.widget.creation_allowed)

        field.user = self.user
        self.assertEqual(url, field.widget.creation_url)
        self.assertTrue(field.widget.creation_allowed)

    def test_clean01(self):
        "Not required."
        field = MultiImageEntityField(required=False)
        field.user = self.user
        self.assertListEqual([], field.clean('[]'))

        img = self._create_image(user=self.user)
        self.assertListEqual([img], field.clean(self._build_value(img)))

        doc = self._create_doc('foobar.txt', user=self.user)
        # self.assertEqual([], field.clean(json_dump([doc.id]))) TODO ?
        self.assertFormfieldError(
            field=field, value=self._build_value(doc),
            codes='isexcluded',
            messages=_('«%(entity)s» violates the constraints.') % {'entity': str(doc)},
        )

    def test_clean02(self):
        "Required."
        field = MultiImageEntityField(user=self.user)

        self.assertTrue(field.required)
        self.assertFormfieldError(
            field=field, value='[]',
            codes='required', messages=_('This field is required.'),
        )

        doc = self._create_doc('foobar.txt', user=self.user)
        self.assertFormfieldError(
            field=field, value=self._build_value(doc),
            codes='isexcluded',
            messages=_('«%(entity)s» violates the constraints.') % {'entity': str(doc)},
        )

    def test_qfilter_init(self):
        field = MultiImageEntityField(user=self.user, q_filter={'title__contains': 'show'})

        final_qfilter = Q(mime_type__name__startswith='image/') & Q(title__contains='show')
        self.assertQEqual(final_qfilter, field.q_filter)
        self.assertFalse(field.force_creation)

        # Widget
        self.assertQEqual(final_qfilter, field.widget.q_filter)
        self.assertFalse(field.widget.creation_url)
        self.assertTrue(field.widget.creation_allowed)

        # Clean
        img1 = self._create_image(title='Icon#1', user=self.user)
        self.assertFormfieldError(
            field=field, value=self._build_value(img1),
            codes='isexcluded',
            messages=_('«%(entity)s» violates the constraints.') % {'entity': str(img1)},
        )

        img2 = self._create_image(title='Python show 2018', user=self.user)
        img3 = self._create_image(title='Python show 2019', user=self.user)
        self.assertEqual([img2, img3], field.clean(self._build_value(img2, img3)))

    def test_qfilter_property01(self):
        "Dict."
        field = MultiImageEntityField(user=self.user)
        field.q_filter = {'title__icontains': 'show'}

        final_qfilter = Q(mime_type__name__startswith='image/') & Q(title__icontains='show')
        self.assertQEqual(final_qfilter, field.q_filter)
        self.assertFalse(field.force_creation)

        # Widget
        self.assertQEqual(final_qfilter, field.widget.q_filter)
        self.assertFalse(field.widget.creation_url)
        self.assertTrue(field.widget.creation_allowed)

        # Clean
        img1 = self._create_image(title='Icon#1', user=self.user)
        self.assertFormfieldError(
            field=field, value=self._build_value(img1),
            codes='isexcluded',
            messages=_('«%(entity)s» violates the constraints.') % {'entity': str(img1)},
        )

        img2 = self._create_image(title='Python Show 2018', user=self.user)
        self.assertListEqual([img2], field.clean(self._build_value(img2)))

    def test_qfilter_property02(self):
        "Q."
        field = MultiImageEntityField(user=self.user)
        field.q_filter = Q(title__icontains='show')

        final_qfilter = Q(mime_type__name__startswith='image/') & Q(title__icontains='show')
        self.assertQEqual(final_qfilter, field.q_filter)
        self.assertFalse(field.force_creation)

        # Widget
        self.assertQEqual(final_qfilter, field.widget.q_filter)
        self.assertFalse(field.widget.creation_url)
        self.assertTrue(field.widget.creation_allowed)

        # Clean
        img1 = self._create_image(title='Icon#1', user=self.user)
        self.assertFormfieldError(
            field=field, value=self._build_value(img1),
            codes='isexcluded',
            messages=_('«%(entity)s» violates the constraints.') % {'entity': str(img1)},
        )

        img2 = self._create_image(title='Python Show 2018', user=self.user)
        self.assertEqual([img2], field.clean(self._build_value(img2)))

    def test_force_creation(self):
        field = MultiImageEntityField(user=self.user)
        self.assertTrue(field.force_creation)

        url = reverse('documents__create_image_popup')
        self.assertEqual(url, field.widget.creation_url)
        self.assertTrue(field.widget.creation_allowed)

        field.force_creation = False
        self.assertFalse(field.widget.creation_url)

        field.force_creation = True
        self.assertEqual(url, field.widget.creation_url)

    def test_creation_url_init(self):
        creation_url = '/documents/create_image_v2/'

        field = MultiImageEntityField(create_action_url=creation_url)
        self.assertEqual(creation_url, field.create_action_url)
        self.assertFalse(field.widget.creation_url)
        self.assertTrue(field.force_creation)

        field.user = self.user
        self.assertEqual(creation_url, field.widget.creation_url)

    def test_creation_url_property(self):
        creation_url = '/documents/create_image_v2/'

        field = MultiImageEntityField()
        field.create_action_url = creation_url
        self.assertEqual(creation_url, field.create_action_url)
        self.assertFalse(field.widget.creation_url)
        self.assertTrue(field.force_creation)

        field.user = self.user
        self.assertEqual(creation_url, field.widget.creation_url)
        self.assertTrue(field.widget.creation_allowed)
        self.assertEqual(_('Create an image'), field.widget.creation_label)
