# -*- coding: utf-8 -*-

try:
    import filecmp
    from os.path import join, exists, split

    from django.core.serializers.json import simplejson
    from django.conf import settings

    from creme_core.tests.base import CremeTestCase

    from media_managers.models import *
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class MediaManagersTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'media_managers')

    def setUp(self):
        self.images = []
        self.login()

    def tearDown(self):
        for img in self.images:
            img.delete()

    def test_populate(self):
        self.assertEqual(3, MediaCategory.objects.count())

    def test_portal(self):
        self.assertEqual(200, self.client.get('/media_managers/').status_code)

    def test_add(self): #TODO: test popup version
        self.assertEqual(0, Image.objects.count())

        url = '/media_managers/image/add'
        self.assertEqual(200, self.client.get(url).status_code)

        path = join(settings.CREME_ROOT, 'static', 'chantilly', 'images', 'creme_22.png')
        self.assertTrue(exists(path))
        image_file = open(path, 'rb')

        name = 'My image'
        description = 'Blabala'
        category = MediaCategory.objects.all()[0]
        response = self.client.post(url, follow=True,
                            data={'user':        self.user.pk,
                                  'name':        name,
                                  'description': description,
                                  'image':       image_file,
                                  'categories':  [category.id],
                                 }
                           )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            image = Image.objects.get(name=name)

        self.assertEqual(self.user,   image.user)
        self.assertEqual(description, image.description)
        self.assertEqual([category],  list(image.categories.all()))

        self.assertTrue(filecmp.cmp(path, image.image.path))

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
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            image = Image.objects.get(name=name)

        self.images.append(image)

        return  image

    def test_edit(self):
        name = 'my beautiful image'
        description = 'Blabala'
        image = self._create_image(name=name, description=description)
        old_path = image.image.path

        url = '/media_managers/image/edit/%s' % image.id
        self.assertEqual(200, self.client.get(url).status_code)

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
        self.assertEqual(200, response.status_code)

        #image = Image.objects.get(pk=image.pk) #refresh
        image = self.refresh(image)
        self.assertEqual(description, image.description)
        self.assertEqual([category],  list(image.categories.all()))
        self.assertEqual(old_path,    image.image.path)

    def test_listview(self):
        image = self._create_image()

        response = self.client.get('/media_managers/images')
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            images_page = response.context['entities']

        self.assertEqual([image], list(images_page.object_list))

    def test_listview_popup(self):
        image = self._create_image()

        response = self.client.get('/media_managers/images/popup')
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            images_page = response.context['entities']

        self.assertEqual([image], list(images_page.object_list))

    def test_popupview(self):
        image = self._create_image()
        response = self.client.get('/media_managers/image/popup/%s' % image.id)
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            entity = response.context['object']

        self.assertEqual(image, entity)

    def test_get_url(self):
        image = self._create_image()

        image_url = image.get_image_url()
        self.assertEqual(split(image.image.path)[1], split(image_url)[1])

        response = self.client.get('/media_managers/images/%s/get_url' % image.id)
        self.assertEqual(200, response.status_code)

        content = simplejson.loads(response.content)
        self.assertIsInstance(content, dict)
        self.assertEqual(1,         len(content))
        self.assertEqual(image_url, content.get('url'))

    def test_select_image_tiny_mce(self):
        image = self._create_image()
        self.assertEqual(200, self.client.get('/media_managers/tiny_mce/image').status_code)

        #TODO: improve this test....
