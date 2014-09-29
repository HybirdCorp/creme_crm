# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType
    from django.utils.timezone import now

    from creme.creme_core.models import CremeEntity

    from ..models import Memo
    from .base import AssistantsTestCase
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('MemoTestCase',)


class MemoTestCase(AssistantsTestCase):
    def _build_add_url(self, entity):
        return '/assistants/memo/add/%s/' % entity.id

    def _create_memo(self, content='Content', on_homepage=True, entity=None):
        entity = entity or self.entity
        response = self.client.post(self._build_add_url(entity),
                                    data={'user':        self.user.pk,
                                          'content':     content,
                                          'on_homepage': on_homepage,
                                         }
                                   )
        self.assertNoFormError(response)

        return self.get_object_or_fail(Memo, content=content)

    def test_create(self):
        self.assertFalse(Memo.objects.exists())

        entity = self.entity
        self.assertGET200(self._build_add_url(entity))

        homepage = True
        content = 'Content'
        memo = self._create_memo(content, homepage)
        self.assertEqual(1, Memo.objects.count())

        self.assertEqual(homepage,  memo.on_homepage)
        self.assertEqual(self.user, memo.user)

        self.assertEqual(entity.id,             memo.entity_id)
        self.assertEqual(entity.entity_type_id, memo.entity_content_type_id)

        self.assertDatetimesAlmostEqual(now(), memo.creation_date)

        self.assertEqual(content, unicode(memo))

    def test_edit(self):
        content  = ' content'
        homepage = True
        memo = self._create_memo(content, homepage)

        #url = '/assistants/memo/edit/%s/' % memo.id
        url = memo.get_edit_absolute_url()
        self.assertGET200(url)

        content += u""": 
I add a long text in order to obtain a content that 
will be truncate by unicode() method"""
        homepage = not homepage
        response = self.client.post(url, data={'user':        self.user.pk,
                                               'content':     content,
                                               'on_homepage': homepage,
                                              }
                                   )
        self.assertNoFormError(response)

        memo = self.refresh(memo)
        self.assertEqual(content,  memo.content)
        self.assertEqual(homepage, memo.on_homepage)

        self.assertEqual(u'content: I add a long te…', unicode(memo))

    def test_delete_related01(self):
        self._create_memo()
        self.assertEqual(1, Memo.objects.count())

        self.entity.delete()
        self.assertEqual(0, Memo.objects.count())

    def test_delete01(self):
        memo = self._create_memo()
        ct = ContentType.objects.get_for_model(Memo)
        self.assertPOST(302, '/creme_core/entity/delete_related/%s' % ct.id, data={'id': memo.id})
        self.assertEqual(0,   Memo.objects.count())

    def test_function_field01(self):
        funf = CremeEntity.function_fields.get('assistants-get_memos')
        self.assertIsNotNone(funf)
        self.assertEqual(u'<ul></ul>', funf(self.entity).for_html())

    def _oldify_memo(self, memo, years_delta=1):
        cdate = memo.creation_date
        memo.creation_date = cdate.replace(year=cdate.year - years_delta)
        memo.save()

    def test_function_field02(self):
        funf = CremeEntity.function_fields.get('assistants-get_memos')

        self._oldify_memo(self._create_memo('Content01'))
        self._create_memo('Content02')

        with self.assertNumQueries(1):
            result = funf(self.entity)

        self.assertEqual(u'<ul><li>Content02</li><li>Content01</li></ul>', result.for_html())

    def test_function_field03(self):
        "Prefetch with 'populate_entities()'"
        self._oldify_memo(self._create_memo('Content01'))
        self._create_memo('Content02')

        entity02 = CremeEntity.objects.create(user=self.user)
        self._oldify_memo(self._create_memo('Content03', entity=entity02))
        self._create_memo('Content04', entity=entity02)

        funf = CremeEntity.function_fields.get('assistants-get_memos')

        with self.assertNumQueries(1):
            funf.populate_entities([self.entity, entity02])

        with self.assertNumQueries(0):
            result1 = funf(self.entity)
            result2 = funf(entity02)

        self.assertEqual(u'<ul><li>Content02</li><li>Content01</li></ul>', result1.for_html())
        self.assertEqual(u'<ul><li>Content04</li><li>Content03</li></ul>', result2.for_html())

    def test_merge(self):
        def creator(contact01, contact02):
            self._create_memo('This guy is strong',           entity=contact01)
            self._create_memo('This guy lost himself easily', entity=contact02)
            self.assertEqual(2, Memo.objects.count())

        def assertor(contact01):
            memos = Memo.objects.all()
            self.assertEqual(2, len(memos))

            for memo in memos:
                self.assertEqual(contact01, memo.creme_entity)

        self.aux_test_merge(creator, assertor)
