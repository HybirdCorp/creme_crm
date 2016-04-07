# -*- coding: utf-8 -*-

try:
    from django.contrib.auth import get_user_model
    from django.db import models
    from django.utils import translation
    from django.utils.translation import ugettext as _

    from ..base import CremeTestCase
    from ..fake_models import (FakeContact as Contact,
            FakeOrganisation as Organisation, FakeImage as Image,
            FakeEmailCampaign as EmailCampaign, FakeActivity)
    from creme.creme_core.models import CremePropertyType, CremeProperty, CremeEntity, Language
    from creme.creme_core.utils import meta
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class MetaTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        cls._lang = translation.get_language()
        cls._translation_deactivated = False

    def tearDown(self):
        super(MetaTestCase, self).tearDown()

        if self._translation_deactivated:
            translation.activate(self._lang)
            self._translation_deactivated = False

    def _deactivate_translation(self):  # TODO: decorator ?? in CremeTestCase ?
        translation.deactivate_all()
        self._translation_deactivated = True

    def test_get_instance_field_info01(self):
        get_info = meta.get_instance_field_info
        text = 'TEXT'

        user   = get_user_model().objects.create(username='name')
        ptype  = CremePropertyType.objects.create(text=text, is_custom=True)
        entity = CremeEntity.objects.create(user=user)
        prop   = CremeProperty(type=ptype, creme_entity=entity)

        self.assertEqual((models.CharField,    text), get_info(prop, 'type__text'))
        self.assertEqual((models.BooleanField, True), get_info(prop, 'type__is_custom'))

        self.assertEqual((None, ''), get_info(prop, 'foobar__is_custom'))
        self.assertEqual((None, ''), get_info(prop, 'type__foobar'))

        self.assertEqual(models.CharField, get_info(prop, 'creme_entity__entity_type__model')[0])

    def test_get_instance_field_info02(self):
        "ManyToMany"
        get_info = meta.get_instance_field_info
        user = get_user_model().objects.create(username='name')
        contact = Contact.objects.create(user=user, first_name='Alphonse', last_name='Elric')
        self.assertEqual((models.CharField, contact.first_name), get_info(contact, 'first_name'))

        # -----------
        m2m_info = get_info(contact, 'languages')
        self.assertEqual(models.ManyToManyField, m2m_info[0])

        values = m2m_info[1]
        self.assertEqual(Language, values.model)
        self.assertEqual([], list(values))

        # -------------
        create_language = Language.objects.create
        l1 = create_language(name='English',  code='EN')
        l2 = create_language(name='French',   code='FRA')
        l3 = create_language(name='Japanese', code='JP')

        contact.languages = [l1, l3]
        self.assertEqual({l1, l3}, set(get_info(contact, 'languages')[1]))

        # -------------
        # TODO: fix it ??
        self.assertEqual((None, ''), get_info(contact, 'languages__code'))

    def test_field_info01(self):
        "Simple field"
        fi = meta.FieldInfo(Contact, 'first_name')

        self.assertEqual(1, len(fi))

        with self.assertNoException():
            base_field = fi[0]

        self.assertEqual(Contact._meta.get_field('first_name'), base_field)

        self.assertEqual(Organisation._meta.get_field('name'),
                         meta.FieldInfo(Organisation, 'name')[0]
                        )

        # FK
        self.assertEqual(Contact._meta.get_field('image'),
                         meta.FieldInfo(Contact, 'image')[0]
                        )

    def test_field_info02(self):
        "depth > 1"
        fi = meta.FieldInfo(Contact, 'image__name')

        self.assertEqual(2, len(fi))
        self.assertEqual(Contact._meta.get_field('image'), fi[0])
        self.assertEqual(Image._meta.get_field('name'),    fi[1])

        self.assertEqual(_('Photograph') + ' - ' + _('Name'), fi.verbose_name)

        with self.assertNoException():
            fi_as_list = list(meta.FieldInfo(Contact, 'image__user__username'))

        self.assertEqual([Contact._meta.get_field('image'),
                          Image._meta.get_field('user'),
                          get_user_model()._meta.get_field('username'),
                         ],
                         fi_as_list
                        )

    def test_field_info03(self):
        "Invalid fields"
        FieldDoesNotExist = models.FieldDoesNotExist

        with self.assertRaises(FieldDoesNotExist):
            meta.FieldInfo(Contact, 'invalid')

        with self.assertRaises(FieldDoesNotExist):
            meta.FieldInfo(Contact, 'image__invalid')

        with self.assertRaises(FieldDoesNotExist):
            meta.FieldInfo(Contact, 'invalid__invalidtoo')

    def test_field_info04(self):
        "Slice"
        fi = meta.FieldInfo(Contact, 'image__user__username')

        with self.assertNoException():
            sub_fi = fi[1:]

        self.assertIsInstance(sub_fi, meta.FieldInfo)
        self.assertEqual(2, len(sub_fi))
        self.assertEqual(Image._meta.get_field('user'),    sub_fi[0])
        self.assertEqual(get_user_model()._meta.get_field('username'), sub_fi[1])

    def test_field_info_get_value01(self):
        FieldInfo = meta.FieldInfo

        user = get_user_model().objects.create(username='alphonse')
        al = Contact.objects.create(user=user, first_name='Alphonse', last_name='Elric')

        self.assertEqual(al.first_name,
                         FieldInfo(Contact, 'first_name').value_from(al)
                        )
        self.assertEqual(user,
                         FieldInfo(Contact, 'user').value_from(al)
                        )
        self.assertEqual(user.username,
                         FieldInfo(Contact, 'user__username').value_from(al)
                        )

        # Other model
        ptype = CremePropertyType.objects.create(text='Is the hero', is_custom=True)
        prop = CremeProperty(type=ptype, creme_entity=al)
        self.assertEqual(ptype.text,
                         FieldInfo(CremeProperty, 'type__text').value_from(prop)
                        )
        self.assertEqual(al.entity_type.model,
                         FieldInfo(CremeProperty, 'creme_entity__entity_type__model').value_from(prop)
                        )

        with self.assertRaises(ValueError):
            FieldInfo(CremeProperty, 'type__text').value_from(al)  # 'al' is not a CremeProperty

        self.assertIsNone(FieldInfo(Contact, 'sector').value_from(al))
        self.assertIsNone(FieldInfo(Contact, 'sector__title').value_from(al))

    def test_field_info_get_value02(self):
        "ManyToManyField"
        FieldInfo = meta.FieldInfo

        user = get_user_model().objects.create(username='alphonse')
        al = Contact.objects.create(user=user, first_name='Alphonse', last_name='Elric')

        self.assertEqual([], FieldInfo(Contact, 'languages').value_from(al))
        self.assertEqual([], FieldInfo(Contact, 'languages__code').value_from(al))

        # ----
        create_language = Language.objects.create
        l1 = create_language(name='English',  code='EN')
        l2 = create_language(name='French',   code='FRA')
        l3 = create_language(name='Japanese', code='JP')

        al.languages = [l1, l3]
        self.assertEqual([l1, l3], FieldInfo(Contact, 'languages').value_from(al))
        self.assertEqual([l1.name, l3.name], FieldInfo(Contact, 'languages__name').value_from(al))

    # TODO: test mtom1__mtom2

    # def test_get_date_fields(self):
    #     datefields = meta.get_date_fields(CremeEntity())
    #     self.assertEqual(2, len(datefields))
    #     self.assertEqual({'created', 'modified'}, {f.name for f in datefields})

    def test_is_date_field(self):
        entity = CremeEntity()
        get_field = entity._meta.get_field
        self.assertTrue(meta.is_date_field(get_field('created')))
        self.assertFalse(meta.is_date_field(get_field('user')))

    def test_field_enumerator01(self):
        self._deactivate_translation()

        expected = [('created',                    _('Creation date')),
                    ('header_filter_search_field', 'header filter search field'),
                    ('id',                         'ID'),
                    ('is_actived',                 'is actived'),
                    ('is_deleted',                 'is deleted'),
                    ('modified',                   _('Last modification')),
                   ]
        choices = meta.ModelFieldEnumerator(CremeEntity).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(CremeEntity, only_leafs=True).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(CremeEntity, only_leafs=False).choices()
        self.assertEqual([('created',                    _('Creation date')),
                          ('entity_type',                'entity type'),
                          ('header_filter_search_field', 'header filter search field'),
                          ('id',                         'ID'),
                          ('is_actived',                 'is actived'),
                          ('is_deleted',                 'is deleted'),
                          ('modified',                   _('Last modification')),
                          ('user',                       _('Owner user')),
                         ],
                         choices, choices
                        )

    def test_field_enumerator02(self):
        "Filter, exclude (simple)"
        self._deactivate_translation()

        expected = [('created',  _('Creation date')),
                    ('modified', _('Last modification')),
                   ]
        choices = meta.ModelFieldEnumerator(CremeEntity).filter(viewable=True).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(CremeEntity).exclude(viewable=False).choices()
        self.assertEqual(expected, choices, choices)

        expected = [('created',  _('Creation date')),
                    ('modified', _('Last modification')),
                    ('user',     _('Owner user'))
                   ]
        choices = meta.ModelFieldEnumerator(CremeEntity, only_leafs=False).filter(viewable=True).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(CremeEntity, only_leafs=False).exclude(viewable=False).choices()
        self.assertEqual(expected, choices, choices)

    def test_field_enumerator03(self):
        "deep = 1"
        self._deactivate_translation()

        fs = u'[%s] - %%s' % _('Owner user')
        expected = [('created',         _('Creation date')),
                    ('modified',        _('Last modification')),

                    ('user__email',     fs % _('Email address')),
                    ('user__last_name', fs % _('Last name')),
                    ('user__username',  fs % _('Username')),
                   ]
        self.assertEqual(expected,
                         meta.ModelFieldEnumerator(CremeEntity, deep=1)
                             .filter(viewable=True).choices()
                        )
        self.assertEqual(expected,
                         meta.ModelFieldEnumerator(CremeEntity, deep=1, only_leafs=True)
                             .filter(viewable=True).choices()
                        )
        self.assertEqual([('created',         _('Creation date')),
                          ('modified',        _('Last modification')),
                          ('user',            _('Owner user')),  # <===

                          ('user__email',     fs % _('Email address')),
                          ('user__last_name', fs % _('Last name')),
                          ('user__username',  fs % _('Username')),
                         ],
                         meta.ModelFieldEnumerator(CremeEntity, deep=1, only_leafs=False)
                             .filter(viewable=True).choices()
                        )

    def test_field_enumerator04(self):
        "Filter with function, exclude"
        self._deactivate_translation()

        self.assertEqual([('modified', _('Last modification'))],
                         meta.ModelFieldEnumerator(CremeEntity, deep=1)
                             .filter(lambda f, depth: f.name.endswith('ied'), viewable=True)
                             .choices()
                        )
        self.assertEqual([('created', _('Creation date'))],
                         meta.ModelFieldEnumerator(CremeEntity, deep=0)
                             .exclude(lambda f, depth: f.name.endswith('ied'), viewable=False)
                             .choices()
                        )

    def test_field_enumerator05(self):
        "Other ct"
        self._deactivate_translation()

        expected = [('created',     _('Creation date')),
                    ('modified',    _('Last modification')),
                    ('name',        _('Name of the campaign')),
                   ]
        choices = meta.ModelFieldEnumerator(EmailCampaign).filter(viewable=True).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(EmailCampaign, only_leafs=False) \
                      .filter((lambda f, depth: f.get_internal_type() != 'ForeignKey'),
                              viewable=True,
                             ) \
                      .choices()
        expected.append(('mailing_lists', _('Related mailing lists')))
        self.assertEqual(expected, choices, choices)

    def test_field_enumerator06(self):
        "Filter/exclude : multiple conditions + field true attributes"
        self._deactivate_translation()

        expected = [('birthday',    _('Birthday')),
                    ('civility',    _('Civility')),
                    ('description', _('Description')),
                    ('email',       _('Email address')),
                    ('first_name',  _('First name')),
                    ('is_a_nerd',   _(u'Is a Nerd')),
                    ('last_name',   _('Last name')),
                    ('sector',      _('Line of business')),
                    ('mobile',      _('Mobile')),
                    ('user',        _('Owner user')),
                    ('phone',       _('Phone number')),
                    ('image',       _('Photograph')),
                    ('position',    _('Position')),
                    ('languages',   _(u'Spoken language(s)')),
                    ('url_site',    _('Web Site')),
                   ]
        choices = meta.ModelFieldEnumerator(Contact, only_leafs=False) \
                      .filter(editable=True, viewable=True).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(Contact, only_leafs=False) \
                      .exclude(editable=False, viewable=False).choices()
        self.assertEqual(expected, choices, choices)

    def test_field_enumerator07(self):
        "Ordering of FKs"
        self._deactivate_translation()

        choices = meta.ModelFieldEnumerator(FakeActivity, deep=1, only_leafs=False) \
                      .filter(viewable=True).choices()
        fs = u'[%s] - %s'
        type_lbl = _(u'Activity type')
        user_lbl = _('Owner user')
        self.assertEqual([('type',            type_lbl),
                          ('created',         _('Creation date')),
                          ('end',             _(u'End')),
                          ('modified',        _('Last modification')),
                          ('user',            user_lbl),
                          ('start',           _(u'Start')),
                          ('title',           _(u'Title')),

                          ('type__name',      fs % (type_lbl, _('Name'))),

                          ('user__email',     fs % (user_lbl, _('Email address'))),
                          ('user__last_name', fs % (user_lbl, _('Last name'))),
                          ('user__username',  fs % (user_lbl, _('Username'))),
                         ],
                         choices, choices
                        )

    def test_field_enumerator08(self):
        "'depth' argument"
        self._deactivate_translation()

        choices = meta.ModelFieldEnumerator(FakeActivity, deep=1, only_leafs=False) \
                      .filter((lambda f, depth: not depth or f.name == 'name'), viewable=True) \
                      .choices()

        fs = u'[%s] - %s'
        type_lbl = _(u'Activity type')
        self.assertEqual([('type',       type_lbl),
                          ('created',    _('Creation date')),
                          ('end',        _(u'End')),
                          ('modified',   _('Last modification')),
                          ('user',       _('Owner user')),
                          ('start',      _(u'Start')),
                          ('title',      _(u'Title')),

                          ('type__name', fs % (type_lbl, _('Name')))
                         ],
                         choices, choices
                        )

    def test_field_enumerator09(self):
        "Translation activated"
        choices = set(meta.ModelFieldEnumerator(FakeActivity, deep=1, only_leafs=False)
                          .filter(viewable=True).choices()
                     )
        fs = u'[%s] - %s'
        type_lbl = _(u'Activity type')
        user_lbl = _('Owner user')
        self.assertEqual({('type',            type_lbl),
                          ('created',         _('Creation date')),
                          ('end',             _(u'End')),
                          ('modified',        _('Last modification')),
                          ('user',            user_lbl),
                          ('start',           _(u'Start')),
                          ('title',           _(u'Title')),

                          ('type__name',      fs % (type_lbl, _('Name'))),

                          ('user__email',     fs % (user_lbl, _('Email address'))),
                          ('user__last_name', fs % (user_lbl, _('Last name'))),
                          ('user__username',  fs % (user_lbl, _('Username'))),
                         },
                         choices, choices
                        )
