# -*- coding: utf-8 -*-

try:
    import filecmp
    from functools import partial
    import json
    from os.path import join, exists, split, basename, splitext
    from tempfile import NamedTemporaryFile

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.gui.field_printers import field_printers_registry

    from creme.persons.tests.base import skipIfCustomContact
    from creme.persons import get_contact_model

    from .models import Image, MediaCategory
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


Contact = get_contact_model()


def create_image(user, ident=1):
    tmpfile = NamedTemporaryFile()
    tmpfile.width = tmpfile.height = 0
    tmpfile._committed = True
    tmpfile.path = 'upload/file_%s.jpg' % ident

    return Image.objects.create(user=user,
                                image=tmpfile,
                                name=u'Image #%s' % ident,
                                description=u"Desc",
                               )


class MediaManagersTestCase(CremeTestCase):
    # @classmethod
    # def setUpClass(cls):
    #     CremeTestCase.setUpClass()
    #     cls.populate('creme_core', 'media_managers')

    # TODO: remove when documents & images have been merged -> use the CremeTestCase.tearDown cleaning.
    def setUp(self):
        self.images = []
#        self.login()

    def tearDown(self):
        for img in self.images:
            img.delete()

    def test_populate(self):
        self.login()
        self.assertEqual(3, MediaCategory.objects.count())

    def test_portal(self):
        self.login()
        self.assertGET200('/media_managers/')

    def test_add01(self):  # TODO: test popup version
        user = self.login()
        self.assertEqual(0, Image.objects.count())

        url = '/media_managers/image/add'
        self.assertGET200(url)

        path = join(settings.CREME_ROOT, 'static', 'chantilly', 'images', 'creme_22.png')
        self.assertTrue(exists(path))
        image_file = open(path, 'rb')

        name = 'My image'
        description = 'Blabala'
        category = MediaCategory.objects.all()[0]
        response = self.client.post(url, follow=True,
                                    data={'user':        user.pk,
                                          'name':        name,
                                          'description': description,
                                          'image':       image_file,
                                          'categories':  [category.id],
                                         }
                                   )
        self.assertNoFormError(response)

        image = self.get_object_or_fail(Image, name=name)
        self.assertEqual(user,        image.user)
        self.assertEqual(description, image.description)
        self.assertEqual([category],  list(image.categories.all()))

        self.assertTrue(filecmp.cmp(path, image.image.path))

        image.delete()

    def test_add02(self):
        "No name"
        user = self.login()

        path = join(settings.CREME_ROOT, 'static', 'chantilly', 'images', 'creme_22.png')
        self.assertTrue(exists(path))
        image_file = open(path, 'rb')

        description = 'This image has no name'
        category = MediaCategory.objects.all()[1]
        response = self.client.post('/media_managers/image/add', follow=True,
                                    data={'user':        user.pk,
                                          # 'name':        name,
                                          'description': description,
                                          'image':       image_file,
                                          'categories':  [category.id],
                                         }
                                   )
        self.assertNoFormError(response)

        image = self.get_object_or_fail(Image, description=description)
        self.assertEqual(user,       image.user)
        self.assertEqual([category], list(image.categories.all()))

        name = image.name
        self.assertTrue(name.startswith('creme_22'), 'This name is not expected: %s' % name)
        self.assertTrue(name.endswith('.png'))

        image.delete()

    def _create_image(self, name='My image', description='Blabala', categories=()):
        path = join(settings.CREME_ROOT, 'static', 'chantilly', 'images', 'creme_22.png')
        self.assertTrue(exists(path))
        image_file = open(path, 'rb')

        response = self.client.post('/media_managers/image/add', follow=True,
                                    data={'user':        self.user.pk,
                                          'name':        name,
                                          'description': description,
                                          'image':       image_file,
                                          'categories':  [c.id for c in categories],
                                         }
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            image = Image.objects.get(name=name)

        self.images.append(image)

        return image

    def test_edit(self):
        self.login()

        name = 'my beautiful image'
        description = 'Blabala'
        image = self._create_image(name=name, description=description)
        old_path = image.image.path

        url = '/media_managers/image/edit/%s' % image.id
        self.assertGET200(url)

        name = name.title()
        description += ' (edited)'
        category = MediaCategory.objects.all()[0]
        response = self.client.post(url, follow=True,
                            data={'user':        self.user.pk,
                                  'name':        name,
                                  'description': description,
                                  'categories':  [category.id],
                                 }
                           )
        self.assertNoFormError(response)

        image = self.refresh(image)
        self.assertEqual(description, image.description)
        self.assertEqual([category],  list(image.categories.all()))
        self.assertEqual(old_path,    image.image.path)

    def test_listview(self):
        self.login()
        image = self._create_image()

        response = self.client.get('/media_managers/images')
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            images_page = response.context['entities']

        self.assertEqual([image], list(images_page.object_list))

    def test_get_url(self):
        self.login()
        image = self._create_image()

        image_url = image.get_image_url()
        self.assertEqual(split(image.image.path)[1], split(image_url)[1])

        response = self.assertGET200('/media_managers/images/%s/get_url' % image.id)

        content = json.loads(response.content)
        self.assertIsInstance(content, dict)
        self.assertEqual(1,         len(content))
        self.assertEqual(image_url, content.get('url'))

    def test_select_image_tiny_mce(self):
        self.login()
        self._create_image()
        self.assertGET200('/media_managers/tiny_mce/image')

        # TODO: improve this test....

    @skipIfCustomContact
    def test_field_printers01(self):
        "Field printer with FK on Image"
        user = self.login()

        image = self._create_image()
        casca = Contact.objects.create(user=user, image=image,
                                       first_name='Casca', last_name='Mylove',
                                      )
        self.assertEqual(u'''<a onclick="creme.dialogs.image('%s').open();">%s</a>''' % (
                                casca.image.get_image_url(),
                                casca.image.get_entity_summary(user),
                            ),
                         field_printers_registry.get_html_field_value(casca, 'image', user)
                        )
        self.assertEqual(unicode(casca.image),
                         field_printers_registry.get_csv_field_value(casca, 'image', user)
                        )

    @skipIfCustomContact
    def test_field_printers02(self):
        "Field printer with FK on Image + credentials"
        from creme.creme_core.auth.entity_credentials import EntityCredentials
        from creme.creme_core.models import SetCredentials

        user = self.login(is_superuser=False, allowed_apps=['creme_core', 'persons', 'media_managers'])
        self.role.exportable_ctypes = [ContentType.objects.get_for_model(Contact)]
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        create_img = Image.objects.create
        casca_face = create_img(name='Casca face', user=self.other_user, description="Casca's selfie")
        judo_face  = create_img(name='Judo face',  user=user,            description="Judo's selfie")
        self.assertTrue(user.has_perm_to_view(judo_face))
        self.assertFalse(user.has_perm_to_view(casca_face))

        create_contact = partial(Contact.objects.create, user=user)
        casca = create_contact(first_name='Casca', last_name='Mylove', image=casca_face)
        judo  = create_contact(first_name='Judo',  last_name='Doe',    image=judo_face)

        get_html_val = field_printers_registry.get_html_field_value
        self.assertEqual(u'<a onclick="creme.dialogs.image(\'%s\').open();">%s</a>' % (
                                judo_face.get_image_url(), 
                                judo_face.get_entity_summary(user)
                            ),
                         get_html_val(judo, 'image', user)
                        )
        self.assertEqual('<p>Judo&#39;s selfie</p>',
                         get_html_val(judo, 'image__description', user)
                        )

        self.assertEqual(settings.HIDDEN_VALUE, get_html_val(casca, 'image', user))
        self.assertEqual(settings.HIDDEN_VALUE, get_html_val(casca, 'image__description', user))


class ImageQuickFormTestCase(CremeTestCase):
    # @classmethod
    # def setUpClass(cls):
    #     CremeTestCase.setUpClass()
    #     cls.populate('creme_core', 'media_managers')

    def setUp(self):
        self.images = []
        self.login()

    def tearDown(self):
        for img in self.images:
            img.delete()

    def _build_filedata(self, content_str, suffix='.txt'):
        tmpfile = NamedTemporaryFile(suffix=suffix, delete=False)
        tmpfile.write(content_str)
        tmpfile.flush()

        # We close and reopen in order to have a file with the right name (so we must specify delete=False)
        tmpfile.close()

        name = tmpfile.name

        return open(name, 'rb'), basename(name)

    def quickform_data(self, count):
        return {'form-INITIAL_FORMS': '0',
                'form-MAX_NUM_FORMS': '',
                'form-TOTAL_FORMS':   '%s' % count,
               }

    def quickform_data_append(self, data, id, user='', image=''):
        return data.update({'form-%d-user' % id:  user,
                            'form-%d-image' % id: image,
                           }
                          )

    def test_add(self):
        self.assertFalse(Image.objects.exists())

        url = '/creme_core/quickforms/%s/%d' % (ContentType.objects.get_for_model(Image).pk, 1)
        self.assertGET200(url)

        with open(join(settings.CREME_ROOT, 'static', 'chantilly', 'images', '500.png'), 'r') as f:
            content = f.read()

        file_obj, file_name = self._build_filedata(content)

        data = self.quickform_data(1)
        self.quickform_data_append(data, 0, user=self.user.pk, image=file_obj)

        self.assertNoFormError(self.client.post(url, follow=True, data=data))

        image = Image.objects.get()

        # self.assertEqual('upload/images/%s_%s' % (image.id, file_name), image.image.name)
        self.assertEqual('upload/images/%s' % file_name, image.image.name)
        self.assertSequenceEqual([], image.categories.all())

        filedata = image.image
        filedata.open()
        self.assertEqual(content, filedata.read())

        name = image.name
        fname_parts = splitext(file_name)
        self.assertTrue(name.startswith(fname_parts[0]), 'This name is not expected: %s' % name)
        self.assertTrue(name.endswith(fname_parts[1]), 'This name is not expected: %s' % name)
