# -*- coding: utf-8 -*-

try:
    from functools import partial
    from time import sleep

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.sessions.models import Session
    from django.utils.formats import date_format
    from django.utils.timezone import localtime
    from django.utils.translation import ugettext as _

    from ..base import CremeTestCase, skipIfNotInstalled
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.gui.field_printers import field_printers_registry
    from creme.creme_core.gui.last_viewed import LastViewedItem
    from creme.creme_core.models import CremeEntity, SetCredentials

    from creme.media_managers.models import Image, MediaCategory

    from creme.persons.models import Contact, Organisation, Position
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class GuiTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def test_last_viewed_items(self):
        settings.MAX_LAST_ITEMS = MAX_LAST_ITEMS = 5
        self.login()

        class FakeRequest(object):
            def __init__(self):
                sessions = Session.objects.all()
                assert 1 == len(sessions)
                self.session = sessions[0].get_decoded()

        def get_items():
            with self.assertNoException():
                return FakeRequest().session['last_viewed_items']

        self.assertEqual(0, len(LastViewedItem.get_all(FakeRequest())))

        create_contact = partial(Contact.objects.create, user=self.user)
        contact01 = create_contact(first_name='Casca',    last_name='Mylove')
        contact02 = create_contact(first_name='Puck',     last_name='Elfman')
        contact03 = create_contact(first_name='Judo',     last_name='Doe')
        contact04 = create_contact(first_name='Griffith', last_name='Femto')

        self.assertGET200(contact01.get_absolute_url())
        self.assertEqual(1, len(LastViewedItem.get_all(FakeRequest())))

        items = get_items()
        self.assertEqual(1, len(items))
        self.assertEqual(contact01.pk, items[0].pk)
        self.assertEqual(MAX_LAST_ITEMS, items.maxlen)

        self.assertGET200(contact02.get_absolute_url())
        self.assertGET200(contact03.get_absolute_url())
        self.assertGET200(contact04.get_absolute_url())
        items = get_items()
        self.assertEqual(4, len(items))
        self.assertEqual([contact04.pk, contact03.pk, contact02.pk, contact01.pk],
                         [i.pk for i in items]
                        )

        sleep(1)
        contact01.last_name = 'ILoveYou'
        contact01.save()
        self.assertGET200(Contact.get_lv_absolute_url())
        old_item = get_items()[-1]
        self.assertEqual(contact01.pk,       old_item.pk)
        self.assertEqual(unicode(contact01), old_item.name)

        self.assertGET200(contact02.get_absolute_url())
        self.assertEqual([contact02.pk, contact04.pk, contact03.pk, contact01.pk],
                         [i.pk for i in get_items()]
                        )

        contact03.delete()
        self.assertFalse(CremeEntity.objects.filter(pk=contact03.id))
        self.assertGET200(Contact.get_lv_absolute_url())
        items = get_items()
        self.assertEqual([contact02.pk, contact04.pk, contact01.pk],
                         [i.pk for i in items]
                        )
        self.assertEqual(MAX_LAST_ITEMS, items.maxlen)

        contact04.trash()
        self.assertGET200(Contact.get_lv_absolute_url())
        self.assertEqual([contact02.pk, contact01.pk],
                         [i.pk for i in get_items()]
                        )

        settings.MAX_LAST_ITEMS = 1
        self.assertGET200(Contact.get_lv_absolute_url())
        self.assertEqual([contact02.pk], [i.pk for i in get_items()])

    def test_field_printers01(self):
        self.login()
        user = self.user
        get_html_val = field_printers_registry.get_html_field_value
        get_csv_val  = field_printers_registry.get_csv_field_value

        create_cat = MediaCategory.objects.create
        cat1 = create_cat(name='Photo of contact')
        cat2 = create_cat(name='Photo of product')

        img = Image.objects.create(name="Casca's face", user=user, description="Casca's selfie")
        img.categories = [cat1, cat2]

        create_contact = partial(Contact.objects.create, user=user)
        casca = create_contact(first_name='Casca', last_name='Mylove',
                               position=Position.objects.create(title='Warrior<script>'),
                               image=img,
                              )

        escaped_title = 'Warrior&lt;script&gt;'

        self.assertEqual(casca.last_name,      get_html_val(casca, 'last_name',       user))
        self.assertEqual(casca.last_name,      get_csv_val(casca,  'last_name',       user))

        self.assertEqual(casca.first_name,     get_html_val(casca, 'first_name',      user))
        self.assertEqual(escaped_title,        get_html_val(casca, 'position',        user))

        self.assertEqual(escaped_title,        get_html_val(casca, 'position__title', user))
        self.assertEqual(casca.position.title, get_csv_val(casca,  'position__title', user))

        self.assertEqual(u'''<a onclick="creme.dialogs.image('%s').open();">%s</a>''' % (
                                casca.image.get_image_url(),
                                casca.image.get_entity_summary(user),
                            ),
                         get_html_val(casca, 'image', user)
                        )
        self.assertEqual(unicode(casca.image),
                         get_csv_val(casca, 'image', user)
                        )

        self.assertEqual('<p>%s</p>' % casca.image.description,
                         get_html_val(casca, 'image__description', user)
                        )
        self.assertEqual(casca.image.description,
                         get_csv_val(casca, 'image__description', user)
                        )

        date_str = date_format(localtime(casca.created), 'DATETIME_FORMAT')
        self.assertEqual(date_str, get_html_val(casca, 'created', user))
        self.assertEqual(date_str, get_csv_val(casca,  'created', user))

        self.assertEqual('<ul><li>%s</li><li>%s</li></ul>' % (cat1.name, cat2.name),
                         get_html_val(casca, 'image__categories', user)
                        )
        self.assertEqual('%s/%s' % (cat1.name, cat2.name),
                         get_csv_val(casca, 'image__categories', user)
                        )
        #TODO: test ImageField

        judo = create_contact(first_name='Judo', last_name='Doe')
        self.assertEqual('', get_html_val(judo, 'position',           user))
        self.assertEqual('', get_html_val(judo, 'position__title',    user))
        self.assertEqual('', get_html_val(judo, 'image',              user))
        self.assertEqual('', get_html_val(judo, 'image__description', user))
        self.assertEqual('', get_html_val(judo, 'image__categories',  user))

        ##todo: move this in login()
        #user.username = 'kirika'
        #user.first_name = 'Kirika'
        #user.last_name = 'Yumura'
        ##user.save()
        #self.assertNotEqual(unicode(user), user.username)

        self.assertEqual(unicode(user), get_html_val(casca, 'image__user', user))           #depth = 2
        self.assertEqual(user.username, get_html_val(casca, 'image__user__username', user)) #depth = 3

    def test_field_printers02(self):
        "ManyToMany (simple model)"
        self.login()
        user = self.user

        create_cat = MediaCategory.objects.create
        cat1 = create_cat(name='Photo of contact')
        cat2 = create_cat(name='Photo of product')

        img = Image.objects.create(user=user, name='Img#1', description='Pretty picture')
        img.categories = [cat1, cat2]

        get_html_val = field_printers_registry.get_html_field_value
        result = '<ul><li>%s</li><li>%s</li></ul>' % (cat1.name, cat2.name)
        self.assertEqual(result, get_html_val(img, 'categories', user))
        self.assertEqual(result, get_html_val(img, 'categories__name', user))

        get_csv_val = field_printers_registry.get_csv_field_value
        result = '%s/%s' % (cat1.name, cat2.name)
        self.assertEqual(result, get_csv_val(img, 'categories', user))
        self.assertEqual(result, get_csv_val(img, 'categories__name', user))

    @skipIfNotInstalled('creme.emails')
    def test_field_printers03(self):
        "ManyToMany (CremeEntity)"
        from creme.emails.models import EmailCampaign, MailingList

        self.login(is_superuser=False, allowed_apps=['creme_core', 'media_managers', 'emails'])
        self.role.exportable_ctypes = [ContentType.objects.get_for_model(EmailCampaign)]
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        user = self.user

        create_camp = partial(EmailCampaign.objects.create, user=user)
        camp1 = create_camp(name='Camp#1')
        camp2 = create_camp(name='Camp#2')
        create_camp(name='Camp#3')

        create_ml = partial(MailingList.objects.create, user=user)
        ml1 = create_ml(name='ML#1')
        ml2 = create_ml(name='ML#2')
        ml3 = create_ml(name='ML#3', user=self.other_user)
        camp1.mailing_lists = [ml1, ml2]
        camp2.mailing_lists = [ml3]

        get_html_val = field_printers_registry.get_html_field_value
        get_csv_val  = field_printers_registry.get_csv_field_value
        self.assertEqual('<ul>'
                            '<li><a target="_blank" href="%s">%s</a></li>'
                            '<li><a target="_blank" href="%s">%s</a></li>'
                         '</ul>' % (
                                ml1.get_absolute_url(), ml1,
                                ml2.get_absolute_url(), ml2,
                            ),
                         get_html_val(camp1, 'mailing_lists', user)
                        )
        self.assertEqual('<ul>'
                            '<li>%s</li>'
                            '<li>%s</li>'
                         '</ul>' % (
                                ml1.name,
                                ml2.name,
                            ),
                         get_html_val(camp1, 'mailing_lists__name', user)
                        )

        csv_value = u'%s/%s' % (ml1, ml2)
        self.assertEqual(csv_value, get_csv_val(camp1, 'mailing_lists', user))
        self.assertEqual(csv_value, get_csv_val(camp1, 'mailing_lists__name', user))

        HIDDEN_VALUE = settings.HIDDEN_VALUE
        html_value = '<ul><li>%s</li></ul>' % HIDDEN_VALUE #_(u'Entity #%s (not viewable)') % ml3.id,
        self.assertEqual(html_value, get_html_val(camp2, 'mailing_lists', user))
        self.assertEqual(html_value, get_html_val(camp2, 'mailing_lists__name', user))

        self.assertEqual(HIDDEN_VALUE, get_csv_val(camp2, 'mailing_lists', user))
        self.assertEqual(HIDDEN_VALUE, get_csv_val(camp2, 'mailing_lists__name', user))

    def test_field_printers04(self):
        "Credentials"
        self.login(is_superuser=False, allowed_apps=['creme_core', 'persons', 'media_managers'])
        self.role.exportable_ctypes = [ContentType.objects.get_for_model(Contact)]
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        user = self.user
        create_img = Image.objects.create
        casca_face = create_img(name='Casca face', user=self.other_user, description="Casca's selfie")
        judo_face  = create_img(name='Judo face',  user=user,            description="Judo's selfie")
        self.assertTrue(user.has_perm_to_view(judo_face))
        self.assertFalse(user.has_perm_to_view(casca_face))

        create_contact = partial(Contact.objects.create, user=user)
        casca = create_contact(first_name='Casca', last_name='Mylove', image=casca_face)
        judo  = create_contact(first_name='Judo',  last_name='Doe',    image=judo_face)

        get_html_val = field_printers_registry.get_html_field_value
        self.assertEqual(u'<a onclick="creme.dialogs.image(\'%s\').open();">%s</a>' % (judo_face.get_image_url(), 
                                                                                       judo_face.get_entity_summary(user)),
                         get_html_val(judo, 'image', user)
                        )
        self.assertEqual('<p>%s</p>' % judo_face.description,
                         get_html_val(judo, 'image__description', user)
                        )

        HIDDEN_VALUE = settings.HIDDEN_VALUE
        self.assertEqual(HIDDEN_VALUE, get_html_val(casca, 'image', user)) #_(u'Entity #%s (not viewable)') % casca_face.id
        self.assertEqual(HIDDEN_VALUE, get_html_val(casca, 'image__description', user))
        self.assertEqual(HIDDEN_VALUE, get_html_val(casca, 'image__categories', user))

        get_csv_val  = field_printers_registry.get_csv_field_value
        self.assertEqual(HIDDEN_VALUE, get_csv_val(casca, 'image', user))
        self.assertEqual(HIDDEN_VALUE, get_csv_val(casca, 'image__description', user))
        self.assertEqual(HIDDEN_VALUE, get_csv_val(casca, 'image__categories', user))

    def test_field_printers06(self):
        "Boolean Field"
        self.login()
        user = self.user

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='God hand', subject_to_vat=False)
        orga2 = create_orga(name='Hawk',     subject_to_vat=True)

        get_html_val = field_printers_registry.get_html_field_value
        self.assertEqual(u'<input type="checkbox" value="False" disabled/>' + _('No'),
                         get_html_val(orga1, 'subject_to_vat', user)
                        )
        self.assertEqual(u'<input type="checkbox" value="True" checked disabled/>' + _('Yes'),
                         get_html_val(orga2, 'subject_to_vat', user)
                        )

        get_csv_val  = field_printers_registry.get_csv_field_value
        self.assertEqual(_('No'),  get_csv_val(orga1, 'subject_to_vat', user))
        self.assertEqual(_('Yes'), get_csv_val(orga2, 'subject_to_vat', user))


from bulk_update import *
from block import *
