# -*- coding: utf-8 -*-

try:
    from future_builtins import zip
    from functools import partial

    from django.core.serializers.json import simplejson
    from django.utils.translation import ugettext as _
    from django.utils.encoding import smart_unicode
    from django.contrib.contenttypes.models import ContentType

    from .base import _PollsTestCase
    from ..models import PollType, PollForm, PollFormSection, PollFormLine, PollFormLineCondition
    from ..core import PollLineType
    from ..blocks import pform_lines_block, preplies_block
    from ..utils import SectionTree, NodeStyle
    from ..templatetags.polls_tags import print_node_number, print_node_css, print_line_condition
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('PollFormsTestCase', )

get_ct = ContentType.objects.get_for_model
DELETE_RELATED_URL = '/creme_core/entity/delete_related/%s'


class PollFormsTestCase(_PollsTestCase):
    _CONDSFIELD_STR   = '[{"source": "%(source)s", "choice": "%(choice)s"}]'
    _CONDSFIELD_STR2X = '[{"source": "%(source1)s", "choice": "%(choice1)s"},' \
                        ' {"source": "%(source2)s", "choice": "%(choice2)s"}]'

    def setUp(self):
        self.login()

    def _build_addline_url(self, pform):
        return '/polls/poll_form/%s/add/line' % pform.id

    def _build_addline2section_url(self, section):
        return '/polls/pform_section/%s/add/line' % section.id

    def _build_choices_url(self, line):
        return '/polls/pform_line/%s/choices' % line.id

    #def _build_editline_url(self, line):
        #return '/polls/pform_line/%s/edit' % line.id

    def _build_deleteline_url(self):
        return DELETE_RELATED_URL % get_ct(PollFormLine).id

    def _build_deletesection_url(self):
        return DELETE_RELATED_URL % get_ct(PollFormSection).id

    def _build_disableline_url(self, line):
        return '/polls/pform_line/%s/disable' % line.id

    def _build_editlineconditions_url(self, line):
        return '/polls/pform_line/%s/conditions/edit' % line.id

    def _create_enum_line(self, choices, qtype=PollLineType.ENUM, del_choices=None):
        kwargs = {} if not del_choices else {'del_choices': del_choices}
        create_l = self._get_formline_creator(PollForm.objects.create(user=self.user, name='Form#1'))

        return create_l('What are your favorite colors ?', qtype=qtype, choices=choices, **kwargs)

    def _create_enum_line_from_view(self, choices, qtype=PollLineType.ENUM):
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        response = self.client.post(self._build_addline_url(pform),
                                    data={'question': 'What are the main colors of a swallow ?',
                                          'type':     qtype,
                                          'choices':  u'\r\n'.join(choices),
                                         }
                                   )
        self.assertNoFormError(response)

        line = pform.lines.all()[0]
        self.assertEqual(qtype, line.type)

        return line

    def _create_3_lines_4_conditions(self):
        self.pform = pform = PollForm.objects.create(user=self.user, name='Form#1')
        ENUM = PollLineType.ENUM
        create_l = self._get_formline_creator(pform=pform)
        choices = [[1, 'A little bit'], [2, 'A lot']]

        return (create_l('How do you like swallows ?', qtype=ENUM, choices=choices),
                create_l('How do you like parrots ?',  qtype=ENUM, choices=choices),
                create_l('Do you love all birds ?',    qtype=PollLineType.STRING, conds_use_or=False),
               )

    def _delete_related(self, related, url, ajax=False):
        kwargs = {} if not ajax else {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        return self.client.post(url, data={'id': related.id}, **kwargs)

    def _delete_line(self, line, ajax=False):
        return self._delete_related(line, self._build_deleteline_url(), ajax)

    def _delete_section(self, section, ajax=False):
        return self._delete_related(section, self._build_deletesection_url(), ajax)

    def _disable_line(self, line, ajax=False):
        kwargs = {} if not ajax else {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        return self.client.post(self._build_disableline_url(line),
                                data={'id': line.id}, **kwargs
                               )

    def test_detailview01(self):
        user = self.user
        pform = PollForm.objects.create(user=user, name='Form#1')

        response = self.assertGET200(pform.get_absolute_url())
        self.assertContains(response, 'id="%s"' % pform_lines_block.id_)
        self.assertContains(response, 'id="%s"' % preplies_block.id_)

    def test_createview01(self):
        user = self.user
        self.assertFalse(PollForm.objects.all())

        url = '/polls/poll_form/add'
        self.assertGET200(url)

        name = 'Form#1'
        ptype = PollType.objects.all()[0]
        response = self.client.post(url, follow=True,
                                    data={'user': user.id,
                                          'name': name,
                                          'type': ptype.id,
                                         }
                                   )
        self.assertNoFormError(response)

        pform = self.get_object_or_fail(PollForm, name=name)
        self.assertEqual(user,  pform.user)
        self.assertEqual(ptype, pform.type)

    def test_editview01(self):
        user = self.user
        name = 'form#1'
        pform = PollForm.objects.create(user=user, name=name)

        url = '/polls/poll_form/edit/%s' % pform.id
        self.assertGET200(url)

        name = name.title()
        ptype = PollType.objects.all()[0]
        response = self.client.post(url, follow=True,
                                    data={'user': user.id,
                                          'name': name,
                                          'type': ptype.id,
                                         }
                                   )
        self.assertNoFormError(response)

        pform = self.refresh(pform)
        self.assertEqual(user,  pform.user)
        self.assertEqual(name,  pform.name)
        self.assertEqual(ptype, pform.type)

    def test_listview01(self):
        create_pform = partial(PollForm.objects.create, user=self.user)
        pform1 = create_pform(name='Form#1')
        pform2 = create_pform(name='Form#2')

        response = self.assertGET200('/polls/poll_forms')

        with self.assertNoException():
            pform_page = response.context['entities']

        self.assertEqual(2, pform_page.paginator.count)
        self.assertEqual({pform1, pform2}, set(pform_page.object_list))

    def test_deleteview01(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        url = '/creme_core/entity/delete/%s' % pform.id
        redirection = PollForm.get_lv_absolute_url()
        self.assertRedirects(self.client.post(url), redirection)

        pform = self.assertStillExists(pform)
        self.assertTrue(pform.is_deleted)

        self.assertRedirects(self.client.post(url), redirection)
        self.assertDoesNotExist(pform)

    def test_deleteview02(self):
        line1, line2, line3 = self._create_3_lines_4_conditions()
        pform = self.pform

        create_cond = partial(PollFormLineCondition.objects.create, line=line3,
                              operator=PollFormLineCondition.EQUALS,
                             )
        cond1 = create_cond(source=line1, raw_answer='1')
        cond2 = create_cond(source=line2, raw_answer='2')

        url = '/creme_core/entity/delete/%s' % pform.id
        self.assertPOST200(url, follow=True)
        pform = self.assertStillExists(pform)
        self.assertTrue(pform.is_deleted)
        self.assertStillExists(line1)
        self.assertStillExists(cond1)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(pform)
        self.assertFalse(PollFormLine.objects.filter(id__in=[line1.id, line2.id, line3.id]))
        self.assertFalse(PollFormLineCondition.objects.filter(id__in=[cond1.id, cond2.id]))

    def test_add_section01(self): #TODO: unicity of name ???
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        url = '/polls/poll_form/%s/add/section' % pform.id
        self.assertGET200(url)

        name = 'Name of the Chapter 1'
        body = 'balabla'
        self.assertNoFormError(self.client.post(url, data={'name': name, 'body': body}))

        sections = pform.sections.all()
        self.assertEqual(1, len(sections))

        section = sections[0]
        self.assertIsInstance(section, PollFormSection)
        self.assertEqual(name, section.name)
        self.assertEqual(body, section.body)
        self.assertEqual(1,    section.order)

    def test_add_section02(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        PollFormSection.objects.create(pform=pform, name='Name of the Chapter 1', order=1)

        name = 'Name of the Chapter 2'
        response = self.client.post('/polls/poll_form/%s/add/section' % pform.id,
                                    data={'name': name}
                                   )
        self.assertNoFormError(response)

        section = pform.sections.get(name=name)
        self.assertEqual(2, section.order)

    def test_add_sub_section01(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        create_section = partial(PollFormSection.objects.create, pform=pform)
        section_1 = create_section(name='Name of the Chapter 1', order=1)
        section_2 = create_section(name='Name of the Chapter 2', order=2)
        section_3 = create_section(name='Name of the Chapter 3', order=3)

        url = '/polls/pform_section/%s/add/child' % section_2.id
        self.assertGET200(url)

        name = 'Name of the Chapter 2.1'
        self.assertNoFormError(self.client.post(url, data={'name': name}))

        with self.assertNoException():
            section = pform.sections.get(parent=section_2)

        self.assertEqual(name, section.name)
        self.assertEqual(3,    section.order)

        self.assertEqual(4, self.refresh(section_3).order)

    def test_edit_section(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        name = 'introduction'
        section = PollFormSection.objects.create(pform=pform, name=name, order=1)

        #url = '/polls/pform_section/%s/edit' % section.id
        url = section.get_edit_absolute_url()
        self.assertGET200(url)

        name = name.title()
        body = 'Once upon a time...'
        self.assertNoFormError(self.client.post(url, data={'name': name, 'body': body}))

        section = self.refresh(section)
        self.assertEqual(name, section.name)
        self.assertEqual(body, section.body)

    def test_delete_section01(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        section = PollFormSection.objects.create(pform=pform, name='Introduction', order=1)

        self.assertGET404(self._build_deletesection_url())

        self.assertEqual([False], [node.has_line for node in SectionTree(pform)])

        self.assertEqual(200, self._delete_section(section, ajax=True).status_code)
        self.assertDoesNotExist(section)

    def test_delete_section02(self):
        "Deleted section has a line"
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        section = PollFormSection.objects.create(pform=pform, name='Introduction', order=1)
        line = self._get_formline_creator(pform)('What is the matter ?',
                                                 section=section #<=======
                                                )

        self.assertEqual([True], [node.has_line for node in SectionTree(pform) if node.is_section])

        self.assertEqual(403, self._delete_section(section).status_code)
        self.assertStillExists(line)
        self.assertStillExists(section)

        #TODO: when 404 rendering is improved
        #self.assertIn(_('There is at least one question in this section.'), response.content)

    def test_delete_section03(self):
        "Empty sub sections are deleted"
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        create_section = partial(PollFormSection.objects.create, pform=pform)
        section     = create_section(name='Chapter I',   order=1)
        sub_section = create_section(name='Chapter I.1', order=2, parent=section)

        self.assertEqual([False, False], [node.has_line for node in SectionTree(pform) if node.is_section])

        self.assertRedirects(self._delete_section(section), pform.get_absolute_url())
        self.assertFalse(PollFormSection.objects.filter(pk__in=[section.pk, sub_section.pk]))

    def test_delete_section04(self):
        "Deleted section has a line (indirectly)"
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        create_section = partial(PollFormSection.objects.create, pform=pform)
        section      = create_section(name='Chapter I',   order=1)
        sub_section1 = create_section(name='Chapter I.1', order=2, parent=section)
        sub_section2 = create_section(name='Chapter I.2', order=3, parent=section)

        line = self._get_formline_creator(pform)('What is the matter ?',
                                                 section=sub_section1 #<=======
                                                )

        self.assertEqual([True, True, False],
                         [node.has_line for node in SectionTree(pform) if node.is_section]
                        )

        response = self._delete_section(section, ajax=True)
        self.assertEqual(403, response.status_code)
        self.assertStillExists(section)
        self.assertStillExists(sub_section1)
        self.assertStillExists(sub_section2)
        self.assertStillExists(line)
        self.assertEqual(_(u'There is at least one question in this section.'),
                         smart_unicode(response.content)
                        )

    def test_add_line_string01(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        url = self._build_addline_url(pform)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('index', fields)

        question = 'What is the difference between a swallow ?'
        qtype = PollLineType.STRING
        self.assertNoFormError(self.client.post(url, data={'question': question,
                                                           'type':     qtype,
                                                          }
                                               )
                              )

        lines = pform.lines.all()
        self.assertEqual(1, len(lines))

        line = lines[0]
        self.assertIsInstance(line, PollFormLine)
        self.assertEqual(question, line.question)
        self.assertEqual(1,        line.order)
        self.assertEqual(qtype,    line.type)
        self.assertIsNone(line.section)

        plt = line.poll_line_type
        desc = _(u'String')
        self.assertEqual(desc, plt.verbose_name)
        self.assertEqual(desc, plt.description)

    def test_add_line_text01(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        question = 'What is the difference between a swallow (argue) ?'
        qtype = PollLineType.TEXT
        self.assertNoFormError(self.client.post(self._build_addline_url(pform),
                                                data={'question': question,
                                                      'type':     qtype,
                                                     }
                                               )
                              )

        lines = pform.lines.all()
        self.assertEqual(1, len(lines))

        line = lines[0]
        self.assertIsInstance(line, PollFormLine)
        self.assertEqual(question, line.question)
        self.assertEqual(1,        line.order)
        self.assertEqual(qtype,    line.type)
        self.assertIsNone(line.section)

        plt = line.poll_line_type
        desc = _(u'Text area')
        self.assertEqual(desc, plt.verbose_name)
        self.assertEqual(desc, plt.description)

    def test_add_line_int01(self):
        "Integer type"
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        question = 'What is the size a swallow ? (cm)'
        qtype = PollLineType.INT
        self.assertNoFormError(self.client.post(self._build_addline_url(pform),
                                                data={'question': question,
                                                      'type':     qtype,
                                                      'order':    2,
                                                     }
                                                )
                              )

        line = pform.lines.get(question=question)
        self.assertEqual(1,     line.order)
        self.assertEqual(qtype, line.type)
        self.assertIsNone(line.type_args)

        plt = line.poll_line_type
        desc = _(u'Integer')
        self.assertEqual(desc, plt.verbose_name)
        self.assertEqual(desc, plt.description)

        self.assertIsNone(plt.get_choices())
        self.assertIsNone(plt.get_editable_choices())

    def test_add_line_int02(self):
        "Lower bound"
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        lower_bound = 0
        response = self.client.post(self._build_addline_url(pform),
                                    data={'question':    'What is the size a swallow ? (cm)',
                                          'type':        PollLineType.INT,
                                          'lower_bound': lower_bound,
                                         }
                                   )
        self.assertNoFormError(response)

        line = pform.lines.all()[0]
        self.assertEqual('{"lower_bound": %s}' % lower_bound, line.type_args)
        self.assertEqual(_(u'Integer greater than %(min_value)s') % {'min_value': lower_bound},
                         unicode(line.poll_line_type.description)
                        )

    def test_add_line_int03(self):
        "Upper bound"
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        upper_bound = 10
        response = self.client.post(self._build_addline_url(pform),
                                    data={'question':    'What is the size a swallow ? (cm)',
                                          'type':        PollLineType.INT,
                                          'upper_bound': upper_bound,
                                         }
                                   )
        self.assertNoFormError(response)

        line = pform.lines.all()[0]
        self.assertEqual('{"upper_bound": %s}' % upper_bound, line.type_args)
        self.assertEqual(_(u'Integer lesser than %(max_value)s') % {'max_value': upper_bound},
                         unicode(line.poll_line_type.description)
                        )

    def test_add_line_int04(self):
        "Upper bound & lower bound"
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        lower_bound = 1
        upper_bound = 15
        response = self.client.post(self._build_addline_url(pform),
                                    data={'question':    'What is the size a swallow ? (cm)',
                                          'type':        PollLineType.INT,
                                          'lower_bound': lower_bound,
                                          'upper_bound': upper_bound,
                                         }
                                   )
        self.assertNoFormError(response)

        line = pform.lines.all()[0]
        self.assertEqual('{"lower_bound": %s, "upper_bound": %s}' % (
                            lower_bound, upper_bound),
                        line.type_args
                       )
        self.assertEqual(_(u'Integer between %(min_value)s and %(max_value)s') % {
                                'min_value': lower_bound,
                                'max_value': upper_bound,
                            },
                         unicode(line.poll_line_type.description)
                        )

    def test_add_line_int05(self):
        "Validation error: upper bound > lower bound"
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        def post(lower_bound, upper_bound):
            response = self.assertPOST200(self._build_addline_url(pform),
                                          data={'question':    'What is the size a swallow ? (cm)',
                                                'type':        PollLineType.INT,
                                                'lower_bound': lower_bound,
                                                'upper_bound': upper_bound,
                                               }
                                         )
            self.assertFormError(response, 'form', None,
                                 [_(u'The upper bound must be greater than the lower bound.')]
                                )

        post(10, 3)
        post(4, 4)

    def test_add_line_bool01(self):
        "Boolean type"
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        question = 'Have you ever seen a knight of the Ni ?'
        qtype = PollLineType.BOOL
        self.assertNoFormError(self.client.post(self._build_addline_url(pform),
                                                data={'question': question,
                                                      'type':     qtype,
                                                     }
                                               )
                              )

        line = pform.lines.get(question=question)
        self.assertEqual(qtype, line.type)
        self.assertIsNone(line.type_args)

        plt = line.poll_line_type
        desc = _('Boolean (Yes/No)')
        self.assertEqual(desc, plt.verbose_name)
        self.assertEqual(desc, plt.description)

        self.assertItemsEqual(plt.get_choices(), [(0, _('No')), (1, _('Yes'))])
        self.assertIsNone(plt.get_editable_choices())

        self.assertFalse(hasattr(plt, 'get_deleted_choices'))

    def test_add_line_date01(self):
        "Date type"
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        question = 'When did you see a swallow for the last time ?'
        qtype = PollLineType.DATE
        self.assertNoFormError(self.client.post(self._build_addline_url(pform),
                                                data={'question': question,
                                                      'type':     qtype,
                                                     }
                                               )
                              )

        line = pform.lines.get(question=question)
        self.assertEqual(qtype, line.type)
        self.assertIsNone(line.type_args)

        plt = line.poll_line_type
        desc = _(u'Date')
        self.assertEqual(desc, plt.verbose_name)
        self.assertEqual(desc, plt.description)

        self.assertIsNone(plt.get_choices())
        self.assertIsNone(plt.get_editable_choices())

    def test_add_line_hour01(self):
        "Hour type"
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        question = 'Where did you see a swallow for the last time ?'
        qtype = PollLineType.HOUR
        self.assertNoFormError(self.client.post(self._build_addline_url(pform),
                                                data={'question': question,
                                                      'type':     qtype,
                                                     }
                                               )
                              )

        line = pform.lines.get(question=question)
        self.assertEqual(qtype, line.type)
        self.assertIsNone(line.type_args)

        plt = line.poll_line_type
        desc = _(u'Hour')
        self.assertEqual(desc, plt.verbose_name)
        self.assertEqual(desc, plt.description)

        self.assertIsNone(plt.get_choices())
        self.assertIsNone(plt.get_editable_choices())

    def test_add_line_choices01(self):
        choices = [[1, 'White'], [2, 'Black'], [3, 'Green']]
        line = self._create_enum_line_from_view([c[1] for c in choices],
                                                qtype=PollLineType.ENUM
                                               )
        self.assertEqual({'choices': choices}, simplejson.loads(line.type_args))

        plt = line.poll_line_type
        self.assertEqual(choices, plt.get_choices())
        self.assertEqual(choices, plt.get_editable_choices())
        self.assertEqual(_(u'List of choices'), plt.verbose_name)
        self.assertEqual(_(u'List of choices (%s)') % 'White / Black / Green',
                         plt.description
                        )

    def test_add_line_choices02(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        def post(*choices):
            response = self.assertPOST200(self._build_addline_url(pform),
                                          data={'question': 'What is the main color of a swallow ?',
                                                'type':     PollLineType.ENUM,
                                                'choices':  u'\n'.join(choices),
                                               }
                                         )
            self.assertFormError(response, 'form', None, _(u'Give 2 choices at least.'))

        post()
        post('White')
        post(' ', '  ')

    def test_add_line_multichoices01(self):
        line = self._create_enum_line_from_view(['White', 'Black', 'Green', 'Purple'],
                                                qtype=PollLineType.MULTI_ENUM
                                               )
        plt = line.poll_line_type
        choices = [[1, 'White'], [2, 'Black'], [3, 'Green'], [4, 'Purple']]
        self.assertEqual(choices, plt.get_choices())
        self.assertEqual(choices, plt.get_editable_choices())
        self.assertEqual(_(u'List of multiple choices'), plt.verbose_name)
        self.assertEqual(_(u'List of multiple choices (%s)') % 'White / Black / Green / Purple',
                         plt.description
                        )

    def test_add_line_multichoices02(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        def post(*choices):
            response = self.assertPOST200(self._build_addline_url(pform),
                                          data={'question': 'What are the main colors of a swallow ?',
                                                'type':     PollLineType.MULTI_ENUM,
                                                'choices':  u'\n'.join(choices),
                                               }
                                         )
            self.assertFormError(response, 'form', None, _(u'Give 2 choices at least.'))

        post()
        post('White')
        post(' ', '  ')

    def test_add_line_freechoice01(self):
        line = self._create_enum_line_from_view(['White', 'Black', 'Green', 'Orange'],
                                                qtype=PollLineType.ENUM_OR_STRING
                                               )
        plt = line.poll_line_type
        choices = [[1, 'White'], [2, 'Black'], [3, 'Green'], [4, 'Orange']]
        self.assertEqual([(0, _('Other'))] + choices, plt.get_choices())
        self.assertEqual(choices,                     plt.get_editable_choices())

        self.assertFalse(plt.get_deleted_choices())
        self.assertEqual(_(u'List of choices with free choice'), plt.verbose_name)
        self.assertEqual(_(u'List of choices with free choice (%s)') % 'White / Black / Green / Orange',
                         plt.description
                        )

    def test_add_line_comment01(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        question = 'Your next answers must rhyme'
        qtype = PollLineType.COMMENT
        self.assertNoFormError(self.client.post(self._build_addline_url(pform),
                                                data={'question': question,
                                                      'type':     qtype,
                                                     }
                                               )
                              )

        line = pform.lines.get(question=question)
        self.assertEqual(qtype, line.type)
        self.assertIsNone(line.type_args)

        plt = line.poll_line_type
        desc = _(u'Comment')
        self.assertEqual(desc, plt.verbose_name)
        self.assertEqual(desc, plt.description)

        self.assertIsNone(plt.get_choices())
        self.assertIsNone(plt.get_editable_choices())

    def test_insert_line01(self):
        "End of section"
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        self._get_formline_creator(pform)('What is the matter ?')

        url = self._build_addline_url(pform)
        response = self.client.get(url)

        with self.assertNoException():
            order_field = response.context['form'].fields['index']

        self.assertEqual([(0, _(u'Start of section')),
                          (1, _(u'End of section')),
                         ],
                         order_field.choices
                        )
        self.assertEqual(1, order_field.initial)

        question = 'What is the size a swallow ? (cm)'
        self.assertNoFormError(self.client.post(url, data={'question': question,
                                                           'type':     PollLineType.INT,
                                                           'index':    1,
                                                          }
                                               )
                              )
        self.assertEqual(2, pform.lines.get(question=question).order)

    def test_insert_line02(self):
        "Start of section"
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        line = self._get_formline_creator(pform)('What is the matter ?')

        question = 'What is the size a swallow ? (cm)'
        self.assertNoFormError(self.client.post(self._build_addline_url(pform),
                                                data={'question': question,
                                                      'type':     PollLineType.INT,
                                                      'index':    0,
                                                     }
                                               )
                              )
        self.assertEqual(1, pform.lines.get(question=question).order)
        self.assertEqual(2, self.refresh(line).order)

    def test_add_line_to_section01(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        section = PollFormSection.objects.create(pform=pform, name='Section I')

        url = self._build_addline2section_url(section)
        self.assertGET200(url)

        question = 'What is the size a swallow ? (cm)'
        qtype = PollLineType.INT
        self.assertNoFormError(self.client.post(url, data={'question': question,
                                                           'type':     qtype,
                                                          }
                                               )
                              )

        with self.assertNoException():
            line = pform.lines.get(question=question)

        self.assertEqual(section, line.section)
        self.assertEqual(qtype,   line.type)
        self.assertEqual(1,       line.order)

    def test_add_line_to_section02(self):
        "Orders"
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        create_section = partial(PollFormSection.objects.create, pform=pform)
        section1 = create_section(name='Section I',  order=1)
        section2 = create_section(name='Section II', order=2)

        create_line = self._get_formline_creator(pform)
        line1 = create_line('Question 0',   section=None)
        line2 = create_line('Question 1.1', section=section1)
        line3 = create_line('Question 1.2', section=section1)
        line4 = create_line('Question 2.1', section=section2)
        line5 = create_line('Question 2.2', section=section2)
        line6 = create_line('Question 2.3', section=section2)

        question = 'What is the size a swallow ? (cm)'
        response = self.client.post(self._build_addline2section_url(section1),
                                    data={'question': question,
                                          'type':     PollLineType.INT,
                                          'index':    2, #at the end
                                         }
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            line = pform.lines.get(question=question)

        self.assertEqual(4, line.order)

        self.assertEqual(1, self.refresh(line1).order)
        self.assertEqual(2, self.refresh(line2).order)
        self.assertEqual(3, self.refresh(line3).order)
        self.assertEqual(5, self.refresh(line4).order) # <===== not 4
        self.assertEqual(6, self.refresh(line5).order)
        self.assertEqual(7, self.refresh(line6).order)

    def test_add_line_to_section03(self):
        "Order (empty section, but not first line)"
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        create_section = partial(PollFormSection.objects.create, pform=pform)
        section1   = create_section(name='Section I', order=1)
        section1_1 = create_section(name='Section 1', order=2, parent=section1)
        section1_2 = create_section(name='Section 2', order=3, parent=section1)

        create_line = self._get_formline_creator(pform)
        line1 = create_line('Question 0',     section=None)
        line2 = create_line('Question I.a',   section=section1)
        line3 = create_line('Question I.b',   section=section1)
        line4 = create_line('Question I.2.a', section=section1_2)

        question = 'Question I.1.a'
        response = self.client.post(self._build_addline2section_url(section1_1),
                                    data={'question': question,
                                          'type':     PollLineType.INT,
                                         }
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            line = pform.lines.get(question=question)

        self.assertEqual(4, line.order)

        self.assertEqual(1, self.refresh(line1).order)
        self.assertEqual(2, self.refresh(line2).order)
        self.assertEqual(3, self.refresh(line3).order)
        self.assertEqual(5, self.refresh(line4).order)

    def test_insert_line_to_section01(self):
        "Insert a question between 2 other questions"
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        section = PollFormSection.objects.create(pform=pform, name='Section I')

        create_line = self._get_formline_creator(pform)
        line1 = create_line('Question I.1', section=section)
        line2 = create_line('Question I.2', section=section)
        line3 = create_line('Question I.3', section=section)

        url = self._build_addline2section_url(section)
        response = self.client.get(url)

        with self.assertNoException():
            order_field = response.context['form'].fields['index']

        msg_fmt = _(u'Before: «%(question)s» (#%(number)s)')
        self.assertEqual([(0, _(u'Start of section')),
                          (1,  msg_fmt % {'question': line2.question, 'number': 2}),
                          (2,  msg_fmt % {'question': line3.question, 'number': 3}),
                          (3, _(u'End of section')),
                         ],
                         order_field.choices
                        )
        self.assertEqual(3, order_field.initial)

        question = 'What is the size a swallow ? (cm)'
        self.assertNoFormError(self.client.post(url,
                                                data={'question': question,
                                                      'type':     PollLineType.INT,
                                                      'index':    2,
                                                     }
                                               )
                              )

        self.assertEqual(3, pform.lines.get(question=question).order)
        self.assertEqual(1, self.refresh(line1).order)
        self.assertEqual(2, self.refresh(line2).order)
        self.assertEqual(4, self.refresh(line3).order)

    def test_edit_line01(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        question = 'What is the difference between a swallow'
        qtype1 = PollLineType.STRING
        line = PollFormLine.objects.create(pform=pform, question=question, order=1, type=qtype1)

        #url = self._build_editline_url(line)
        url = line.get_edit_absolute_url()
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('old_choices', fields)
        self.assertNotIn('new_choices', fields)

        question += ' ?'
        qtype2 = PollLineType.INT
        response = self.client.post(url, data={'question': question,
                                               'type':     qtype2, #should not be used
                                               'order':    3, #should not be used
                                              }
                                   )
        self.assertNoFormError(response)

        line = self.refresh(line)
        self.assertEqual(question, line.question)
        self.assertEqual(1,        line.order) #not changed !!
        self.assertEqual(qtype1,   line.type)  #not changed !!

    def test_edit_line02(self): #disabled line --> error
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        line = PollFormLine.objects.create(pform=pform, question='How are you ?', order=1,
                                           type=PollLineType.STRING, disabled=True,
                                          )

        #url = self._build_editline_url(line)
        url = line.get_edit_absolute_url()
        self.assertGET404(url)
        self.assertPOST404(url, data={'question': line.question})

    def test_edit_line03(self):
        "BOOL --> choices are not editable"
        line = PollFormLine.objects.create(pform=PollForm.objects.create(user=self.user, name='Form#1'),
                                           question='Are you ready ?', order=1, type=PollLineType.BOOL,
                                          )
        #response = self.assertGET200(self._build_editline_url(line))
        response = self.assertGET200(line.get_edit_absolute_url())

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('old_choices', fields)
        self.assertNotIn('new_choices', fields)

    def test_edit_line_choices01(self):
        "ENUM"
        line = self._create_enum_line([[1, 'White'], [2, 'black']])
        #url = self._build_editline_url(line)
        url = line.get_edit_absolute_url()
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            old_choices = fields['old_choices'].content
            fields['new_choices']

        self.assertEqual(['White','black'], old_choices)

        response = self.client.post(url, data={'question':     line.question,
                                               'new_choices': '\r\n'.join(['Green', 'Purple']),

                                               'old_choices_check_0': 'on',
                                               'old_choices_value_0': 'White', #not changed

                                               'old_choices_check_1': 'on',
                                               'old_choices_value_1': 'Black ', #s/b/B + ' '
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual({'choices': [[1, 'White'], [2, 'Black'], [3, 'Green'], [4, 'Purple']]},
                         self.refresh(line).poll_line_type._args
                        )

    def test_edit_line_choices02(self):
        "Delete some choices"
        line = self._create_enum_line([[1, 'White'], [2, 'Black'], [3, 'Red']])
        #response = self.client.post(self._build_editline_url(line),
        response = self.client.post(line.get_edit_absolute_url(),
                                    data={'question':    line.question,
                                          'new_choices': 'Cyan',

                                          #'old_choices_check_0': '', #deleted
                                          'old_choices_value_0': 'White',

                                          'old_choices_check_1': 'on', 
                                          'old_choices_value_1': 'Yellow', #changed

                                          #'old_choices_check_2': '', #deleted too
                                          'old_choices_value_2': 'Red',
                                         }
                                   )
        self.assertNoFormError(response)

        plt = self.refresh(line).poll_line_type
        self.assertEqual({'choices':     [[2, 'Yellow'], [4, 'Cyan']],
                          'del_choices': [[1, 'White'], [3, 'Red']],
                         },
                         plt._args
                        )
        self.assertEqual(_(u'List of choices (%(choices)s) (deleted: %(del_choices)s)') % {
                                'choices':     'Yellow / Cyan',
                                'del_choices': 'White / Red',
                            },
                         plt.description
                        )

    def test_edit_line_choices03(self):
        "With removed choices at beginning"
        line = self._create_enum_line([[2, 'Black'], [3, 'Red']],
                                      del_choices=[[1, 'White'], [4, 'Blue']]
                                     )
        #response = self.client.post(self._build_editline_url(line),
        response = self.client.post(line.get_edit_absolute_url(),
                                    data={'question':    line.question,
                                          'new_choices': 'Magenta',

                                          'old_choices_check_0': 'on',
                                          'old_choices_value_0': 'Black', #unchanged

                                          #'old_choices_check_1': '',
                                          'old_choices_value_1': 'Red', #deleted
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual({'choices':     [[2, 'Black'], [5, 'Magenta']],
                          'del_choices': [[1, 'White'], [4, 'Blue'], [3, 'Red']],
                         },
                         self.refresh(line).poll_line_type._args
                        )

    def test_edit_line_choices04(self):
        "Assert choices are not empty"
        line = self._create_enum_line([[1, 'White'], [2, 'Black'], [3, 'Red']])
        #response = self.assertPOST200(self._build_editline_url(line),
        response = self.assertPOST200(line.get_edit_absolute_url(),
                                      data={'question': line.question,

                                            'old_choices_check_0': 'on',
                                            'old_choices_value_0': 'White',

                                            'old_choices_check_1': 'on',
                                            'old_choices_value_1': ' ', #empty  (afer stripping) !!
                                           }
                                     )
        self.assertFormError(response, 'form', 'old_choices',
                             _('Choices can not be empty.')
                            )

    def test_edit_line_choices05(self): #MULTI_ENUM
        line = self._create_enum_line([[1, 'White'], [2, 'black']],
                                      qtype=PollLineType.MULTI_ENUM
                                     )
        #response = self.assertGET200(self._build_editline_url(line))
        response = self.assertGET200(line.get_edit_absolute_url())

        with self.assertNoException():
            fields = response.context['form'].fields
            old_choices = fields['old_choices'].content
            fields['new_choices']

        self.assertEqual(['White', 'black'], old_choices)

    def test_edit_line_choices06(self):
        "ENUM_OR_STRING"
        line = self._create_enum_line([[1, 'White'], [2, 'black']],
                                      qtype=PollLineType.ENUM_OR_STRING
                                     )
        #response = self.assertGET200(self._build_editline_url(line))
        response = self.assertGET200(line.get_edit_absolute_url())

        with self.assertNoException():
            fields = response.context['form'].fields
            old_choices = fields['old_choices'].content
            fields['new_choices']

        self.assertEqual(['White', 'black'], old_choices)

    def test_edit_line_description01(self):
        "MULTI_ENUM"
        line = self._create_enum_line([[2, 'Black'], [3, 'Red']],
                                      del_choices=[[1, 'White'], [4, 'Blue']],
                                      qtype=PollLineType.MULTI_ENUM
                                     )
        self.assertEqual(_(u'List of multiple choices (%(choices)s) (deleted: %(del_choices)s)') % {
                                'choices':     'Black / Red',
                                'del_choices': 'White / Blue',
                            },
                         line.poll_line_type.description
                        )

    def test_edit_line_description02(self):
        "ENUM_OR_STRING"
        line = self._create_enum_line([[2, 'Brown'], [3, 'Red']],
                                      del_choices=[[1, 'Grey'], [4, 'Blue']],
                                      qtype=PollLineType.ENUM_OR_STRING
                                     )
        self.assertEqual(_(u'List of choices with free choice (%(choices)s) (deleted: %(del_choices)s)') % {
                                'choices':     'Brown / Red',
                                'del_choices': 'Grey / Blue',
                            },
                         line.poll_line_type.description
                        )

    def test_edit_line_choices_with_conditions01(self):
        "Delete some choices (NOT used in conditions)"
        line1, line2, line3 = self._create_3_lines_4_conditions()

        PollFormLineCondition.objects.create(line=line3, source=line1, raw_answer='1', #we use choice 'A little bit' for condition
                                             operator=PollFormLineCondition.EQUALS,
                                            )

        #response = self.client.post(self._build_editline_url(line1),
        response = self.client.post(line1.get_edit_absolute_url(),
                                    data={'question':    line1.question,
                                          'new_choices': 'Passionately',

                                          'old_choices_check_0': 'on',
                                          'old_choices_value_0': 'A little bit',

                                          #'old_choices_check_1': '', #we delete 'A lot'
                                          'old_choices_value_1': 'A lot',
                                         }
                                   )
        self.assertNoFormError(response)

        choices = [[1, 'A little bit'], [3, 'Passionately']]
        del_choices = [[2, 'A lot']]
        line1 = self.refresh(line1)
        self.assertEqual({'choices': choices, 'del_choices': del_choices},
                         simplejson.loads(line1.type_args)
                        )

        plt = line1.poll_line_type
        self.assertEqual(choices,     plt.get_choices())
        self.assertEqual(del_choices, plt.get_deleted_choices())

    def test_edit_line_choices_with_conditions02(self):
        "Delete some choices (NOT used in conditions)"
        line1, line2, line3 = self._create_3_lines_4_conditions()

        PollFormLineCondition.objects.create(line=line3, source=line1, raw_answer='1', #we use choice 'A little bit' for condition
                                             operator=PollFormLineCondition.EQUALS,
                                            )

        #response = self.assertPOST200(self._build_editline_url(line1), #todo: factorise ?
        response = self.assertPOST200(line1.get_edit_absolute_url(), #TODO: factorise ?
                                      data={'question':    line1.question,
                                            'new_choices': 'Passionately',

                                           #'old_choices_check_0': '', #we delete 'A little bit'
                                            'old_choices_value_0': 'A little bit',

                                            'old_choices_check_1': 'on', 
                                            'old_choices_value_1': 'A lot',
                                           }
                                     )
        self.assertFormError(response, 'form', 'old_choices',
                             _('You can not delete the choice "%(choice)s" because it is used in a condition by the question "%(question)s".') % {
                                    'choice':   'A little bit',
                                    'question': line3.question,
                               }
                            )

    def test_delete_type(self):
        "Set to null"
        ptype = PollType.objects.create(name='Political poll')
        pform = PollForm.objects.create(user=self.user, name='Form#1', type=ptype)

        self.assertPOST200('/creme_config/polls/poll_type/delete', data={'id': ptype.pk})
        self.assertDoesNotExist(ptype)

        pform = self.assertStillExists(pform)
        self.assertIsNone(pform.type)

    def test_section_tree01(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        with self.assertNumQueries(2): #1 for sections, 1 for lines
            stree = SectionTree(pform)

        with self.assertNumQueries(0):
            nodes = list(stree)

        self.assertEqual([], nodes)

    def test_section_tree02(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        create_section = partial(PollFormSection.objects.create, pform=pform)
        section2  = create_section(name='2',  order=2)
        section1  = create_section(name='1',  order=1)
        section11 = create_section(name='11', order=1, parent=section1)

        create_line = self._get_formline_creator(pform)
        line0    = create_line('What is the difference between a swallow ?')
        line1    = create_line('Beware there are many traps', qtype=PollLineType.COMMENT)
        line1_1  = create_line('What type of swallow ?', section=section1)
        line11_1 = create_line('Do you like swallows ?', section=section11)
        line11_2 = create_line('Do you eat swallows ?',  section=section11)

        with self.assertNumQueries(2): #1 for sections, 1 for lines
            stree = SectionTree(pform)

        with self.assertNumQueries(0):
            nodes = list(stree)

        self.assertEqual([line0, line1, section1, line1_1, section11, line11_1, line11_2, section2],
                         nodes
                        )
        self.assertFalse(nodes[0].is_section)
        self.assertTrue(nodes[2].is_section)
        self.assertEqual([0, 0, 0, 1, 1, 2, 2, 0], [node.deep for node in nodes])
        self.assertEqual([1, None, 1, 2, 1, 3, 4, 2], [node.number for node in nodes])

        #templatetag
        style = NodeStyle()
        self.assertEqual(['1', 'None', 'I', '2', '1', '3', '4', 'II'],
                         [print_node_number(style, node) for node in nodes]
                        )
        self.assertEqual('',                           print_node_css(style, nodes[0]))
        self.assertEqual('background-color: #BDD8E4;', print_node_css(style, nodes[2]))
        self.assertEqual('background-color: #D8E5EB;', print_node_css(style, nodes[4]))

    def test_section_tree03(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        create_section = partial(PollFormSection.objects.create, pform=pform)
        section1  = create_section(name='1',  order=1)
        section11 = create_section(name='11', order=1, parent=section1)
        section2  = create_section(name='2',  order=2)

        create_line = partial(PollFormLine.objects.create, pform=pform, type=PollLineType.STRING)
        line0    = create_line(question='What is the difference between a swallow ?', order=1)
        line1_1  = create_line(question='What type of swallow ?', section=section1,   order=2)
        line11_2 = create_line(question='Do you eat swallows ?',  section=section11,  order=4) #<= order inverted
        line11_1 = create_line(question='Do you like swallows ?', section=section11,  order=3)

        with self.assertNumQueries(2): #1 for sections, 1 for lines
            stree = SectionTree(pform)

        with self.assertNumQueries(0):
            nodes = list(stree)

        self.assertEqual([line0, section1, line1_1, section11, line11_1, line11_2, section2],
                         nodes
                        )
        self.assertFalse(nodes[0].is_section)
        self.assertTrue(nodes[1].is_section)
        self.assertEqual([0, 0, 1, 1, 2, 2, 0], [node.deep for node in nodes])

    def test_section_tree04(self):
        "Section tree: Manage disabled lines"
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        create_line('How do you eat swallows ?')
        create_line('What type of swallow ?', disabled=True)
        create_line('Do you like swallows ?')

        self.assertEqual([1, None, 2], [node.number for node in SectionTree(pform)])

    def test_statsview01(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        self.assertGET200(self._build_stats_url(pform))

    def test_statsview02(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        line1 = create_line('What type of swallow ?')
        line2 = create_line('Do you eat swallows ?')
        line3 = create_line('Do you like swallows ?')

        response = self.assertGET200(self._build_stats_url(pform))
        self.assertContains(response, line1.question)
        self.assertContains(response, line2.question)
        self.assertContains(response, line3.question)

    def test_add_line_conditions_enum01(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        line1 = create_line('What is your favorite meal ?', qtype=PollLineType.ENUM,
                            choices=[[1, 'Spam'], [2, 'Grilled swallow']]
                           )
        line2 = create_line('How can you love spam ?')
        self.assertIsNone(line2.conds_use_or)

        url = self._build_editlineconditions_url(line2)
        self.assertGET200(url)

        #ttype = 1  #TODO: 'display if' 'display except if'
        response = self.client.post(url, data={#'type':      ttype,  #TODO
                                               'use_or':     1,
                                               'conditions': self._CONDSFIELD_STR % {
                                                                    'source': line1.id,
                                                                    'choice': 1,
                                                                },
                                              }
                                   )
        self.assertNoFormError(response)

        line2 = self.refresh(line2)
        self.assertIs(line2.conds_use_or, True)
        #self.assertEqual(ttype, line2.conds_type) #TODO

        conditions = line2.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(line1, condition.source)
        self.assertEqual('1',   condition.raw_answer)

    def test_add_line_conditions_enum02(self):
        "Several conditions"
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        enum_kwargs = {'qtype': PollLineType.ENUM, 'choices': [[1, 'Spam'], [2, 'Grilled swallow']]}
        create_l = self._get_formline_creator(pform)
        line1 = create_l('What is your favorite meal ?',      **enum_kwargs)
        line2 = create_l('What is your real favorite meal ?', **enum_kwargs)
        line3 = create_l('How can you love spam ?')

        response = self.client.post(self._build_editlineconditions_url(line3),
                                    data={'use_or':     0,
                                          'conditions': self._CONDSFIELD_STR2X % {
                                                                'source1': line1.id, 'choice1': 1,
                                                                'source2': line2.id, 'choice2': 1,
                                                            },
                                         }
                                   )
        self.assertNoFormError(response)

        line3 = self.refresh(line3)
        self.assertIs(line3.conds_use_or, False)
        self.assertEqual([line1, line2],
                         [cond.source for cond in line3.conditions.order_by('id')]
                        )

    def test_add_line_conditions_multienum(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        line1 = create_line('What nuts do you like ?', qtype=PollLineType.MULTI_ENUM,
                            choices=[[1, 'Coco nuts'], [2, 'Peanuts']],
                           )
        line2 = create_line('Do you love all types of nuts ?', conds_use_or=False)

        response = self.client.post(self._build_editlineconditions_url(line2),
                                    data={'use_or':     1,
                                          'conditions': self._CONDSFIELD_STR % {
                                                                    'source': line1.id,
                                                                    'choice': 2,
                                                                },
                                         }
                                   )
        self.assertNoFormError(response)

        condition = line2.conditions.get(source=line1)
        self.assertEqual(simplejson.dumps([2]), condition.raw_answer)

    def _aux_test_add_line_conditions_bool(self, choice, raw_answer, error=None):
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        line1 = create_line('Do you love swallows ?', qtype=PollLineType.BOOL)
        line2 = create_line('Describe your love')

        response = self.assertPOST200(self._build_editlineconditions_url(line2),
                                      data={'use_or':     1,
                                            'conditions': self._CONDSFIELD_STR % {
                                                                'source': line1.id,
                                                                'choice': choice,
                                                            },
                                           }
                                     )

        if error:
            self.assertFormError(response, 'form', 'conditions', error)
        else:
            self.assertNoFormError(response)

            conditions = self.refresh(line2).conditions.all()
            self.assertEqual(1, len(conditions))

            condition = conditions[0]
            self.assertEqual(line1,      condition.source)
            self.assertEqual(raw_answer, condition.raw_answer)

    def test_add_line_conditions_bool01(self):
        self._aux_test_add_line_conditions_bool(1, '1')

    def test_add_line_conditions_bool02(self):
        self._aux_test_add_line_conditions_bool(0, '0')

    def test_add_line_conditions_bool03(self):
        self._aux_test_add_line_conditions_bool(2, '2', error=_('This choice is invalid.'))

    def _aux_add_line_conditions_enumorchoice(self, choice, raw_answer):
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        line1 = create_line('How do you like parrots ?', qtype=PollLineType.ENUM_OR_STRING,
                            choices=[[1, 'A little bit'], [2, 'A lot']],
                           )
        line2 = create_line('Do you love all birds ?', conds_use_or=False)

        response = self.client.post(self._build_editlineconditions_url(line2),
                                    data={'use_or':     1,
                                          'conditions': self._CONDSFIELD_STR % {
                                                                    'source': line1.id,
                                                                    'choice': choice,
                                                                },
                                         }
                                   )
        self.assertNoFormError(response)

        condition = line2.conditions.get(source=line1)
        self.assertEqual(raw_answer, condition.raw_answer)

    def test_add_line_conditions_enumorchoice01(self):
        self._aux_add_line_conditions_enumorchoice(1, simplejson.dumps([1]))

    def test_add_line_conditions_enumorchoice02(self):
        "'Other' choice"
        self._aux_add_line_conditions_enumorchoice(0, simplejson.dumps([0]))

    #TODO: def test_add_line_conditionsXX(self): other types of question ?

    def test_add_line_conditions_error01(self):
        "The source can not be after the destination"
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        line1 = create_line('How can you love spam ?')
        line2 = create_line('What is your favorite meal ?', qtype=PollLineType.ENUM,
                            choices=[[1, 'Spam'], [2, 'Grilled swallow']]
                           )

        response = self.assertPOST200(self._build_editlineconditions_url(line1),
                                      data={'use_or':     1,
                                            'conditions': self._CONDSFIELD_STR % {
                                                                'source': line2.id,
                                                                'choice': 1,
                                                            },
                                            }
                                     )
        self.assertFormError(response, 'form', 'conditions', _('This source is invalid.'))

    def test_add_line_conditions_error02(self):
        "Line is disabled --> error"
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        line = PollFormLine.objects.create(pform=pform, question='How can you love spam ?',
                                           order=1, type=PollLineType.STRING, disabled=True
                                          )
        url = self._build_editlineconditions_url(line)
        self.assertGET404(url)
        self.assertPOST404(url)

    def test_edit_line_conditions01(self):
        "Add a condition & change the existing one"
        line1, line2, line3 = self._create_3_lines_4_conditions()

        PollFormLineCondition.objects.create(line=line3, source=line1, raw_answer='1',
                                             operator=PollFormLineCondition.EQUALS
                                            )

        url = self._build_editlineconditions_url(line3)
        self.assertGET200(url)

        response = self.client.post(url, data={'use_or':     1,
                                               'conditions': self._CONDSFIELD_STR2X % {
                                                                'source1': line1.id, 'choice1': 2,
                                                                'source2': line2.id, 'choice2': 1,
                                                            },
                                              }
                                   )
        self.assertNoFormError(response)

        line3 = self.refresh(line3)
        self.assertIs(line3.conds_use_or, True)
        self.assertEqual([(line1, '2'), (line2, '1')],
                         [(cond.source, cond.raw_answer) for cond in line3.conditions.order_by('id')]
                        )

    def test_edit_line_conditions02(self):
        "Change an existing condition & remove one"
        line1, line2, line3 = self._create_3_lines_4_conditions()

        create_cond = partial(PollFormLineCondition.objects.create, line=line3,
                              operator=PollFormLineCondition.EQUALS,
                             )
        create_cond(source=line1, raw_answer='1')
        create_cond(source=line2, raw_answer='2')

        response = self.client.post(self._build_editlineconditions_url(line3),
                                    data={'use_or':     1,
                                          'conditions': self._CONDSFIELD_STR % {
                                                                'source': line1.id,
                                                                'choice': 2,
                                                            },
                                         }
                                   )
        self.assertNoFormError(response)

        conditions = line3.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(line1, condition.source)
        self.assertEqual('2',   condition.raw_answer)

    def test_edit_line_conditions03(self):
        "Remove all conditions"
        line1, line2, line3 = self._create_3_lines_4_conditions()

        create_cond = partial(PollFormLineCondition.objects.create, line=line3,
                              operator=PollFormLineCondition.EQUALS,
                             )
        create_cond(source=line1, raw_answer='1')
        create_cond(source=line2, raw_answer='2')

        self.assertNoFormError(self.client.post(self._build_editlineconditions_url(line3),
                                                data={'use_or':     1,
                                                      'conditions': '[]',
                                                     }
                                               )
                              )
        self.assertFalse(line3.conditions.all())

    #TODO: remove conditions --> update conds_use_or ?? (or remove 'None' feature)

    def test_disable_line01(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        line = PollFormLine.objects.create(pform=pform, type=PollLineType.INT,
                                           order=1, question='How old is this swallow ?'
                                          )
        self.assertFalse(line.disabled)

        url = self._build_disableline_url(line)
        self.assertGET404(url) #only POST
        self.assertRedirects(self._disable_line(line), pform.get_absolute_url())
        self.assertTrue(self.assertStillExists(line).disabled)

    def test_disable_line02(self):
        "Disabled line depends on other lines"
        line1, line2, line3 = self._create_3_lines_4_conditions()

        create_cond = partial(PollFormLineCondition.objects.create, line=line3,
                              operator=PollFormLineCondition.EQUALS,
                             )
        cond1 = create_cond(source=line1, raw_answer='1')
        cond2 = create_cond(source=line2, raw_answer='2')

        self.assertEqual(302, self._disable_line(line3).status_code)
        self.assertTrue(self.assertStillExists(line3).disabled)
        self.assertFalse(PollFormLineCondition.objects.filter(id__in=[cond1.id, cond2.id]).exists())

    def test_disable_line03(self):
        "Disabled line has a line that depends on it"
        #pform = PollForm.objects.create(user=self.user, name='Form#1')
        line2, line3 = self._create_3_lines_4_conditions()[1:]
        cond = PollFormLineCondition.objects.create(line=line3, source=line2, raw_answer='1',
                                                    operator=PollFormLineCondition.EQUALS
                                                   )

        self.assertEqual(403, self._disable_line(line2).status_code)
        self.assertFalse(self.assertStillExists(line2).disabled)
        self.assertStillExists(cond)

        #TODO: when 404 rendering is improved
        #self.assertIn(_('There is at least one other question which depends on this question.'), response.content)

    def test_disable_line04(self):
        "Already disabled"
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        line = PollFormLine.objects.create(pform=pform, type=PollLineType.INT,
                                           order=1, question='How old is this swallow ?',
                                           disabled=True
                                          )
        self.assertEqual(403, self._disable_line(line).status_code)

    def test_disable_line_ajax01(self):
        "Disabled line depends on other lines"
        line1, line2, line3 = self._create_3_lines_4_conditions()

        create_cond = partial(PollFormLineCondition.objects.create, line=line3,
                              operator=PollFormLineCondition.EQUALS,
                             )
        cond1 = create_cond(source=line1, raw_answer='1')
        cond2 = create_cond(source=line2, raw_answer='2')

        self.assertEqual(200, self._disable_line(line3, ajax=True).status_code)
        self.assertTrue(self.assertStillExists(line3).disabled)
        self.assertDoesNotExist(cond1)
        self.assertDoesNotExist(cond2)

    def test_disable_line_ajax02(self):
        "Disabled line has a line that depends on it"
        line2, line3 = self._create_3_lines_4_conditions()[1:]
        cond = PollFormLineCondition.objects.create(line=line3, source=line2, raw_answer='1',
                                                    operator=PollFormLineCondition.EQUALS
                                                   )

        response = self._disable_line(line2, ajax=True)
        self.assertEqual(403, response.status_code)
        self.assertFalse(self.assertStillExists(line2).disabled)
        self.assertStillExists(cond)
        self.assertEqual(_(u'There is at least one other question which depends on this question.'),
                         smart_unicode(response.content)
                        )

    def test_delete_line01(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        line = PollFormLine.objects.create(pform=pform, type=PollLineType.INT,
                                           order=1, question='How old is this swallow ?'
                                          )

        self.assertGET404(self._build_deleteline_url()) #only POST
        self.assertRedirects(self._delete_line(line), pform.get_absolute_url())
        self.assertDoesNotExist(line)

    def test_delete_line02(self):
        "Deleted line depends on other lines"
        line1, line2, line3 = self._create_3_lines_4_conditions()

        create_cond = partial(PollFormLineCondition.objects.create, line=line3, operator=PollFormLineCondition.EQUALS)
        cond1 = create_cond(source=line1, raw_answer='1')
        cond2 = create_cond(source=line2, raw_answer='2')

        self.assertEqual(302, self._delete_line(line3).status_code)
        self.assertDoesNotExist(line3)
        self.assertDoesNotExist(cond1)
        self.assertDoesNotExist(cond2)

    def test_delete_line03(self):
        "Deleted line has a line that depends on it"
        line2, line3 = self._create_3_lines_4_conditions()[1:]
        cond = PollFormLineCondition.objects.create(line=line3, source=line2, raw_answer='1',
                                                    operator=PollFormLineCondition.EQUALS
                                                   )

        response = self._delete_line(line2)
        self.assertEqual(403, response.status_code)
        self.assertStillExists(line2)
        self.assertStillExists(cond)

        #TODO: when 404 rendering is improved
        #self.assertIn(_('There is at least one other question which depends on this question.'), response.content)

    #def test_delete_line04(self): #TODO ??
        #pform = PollForm.objects.create(user=self.user, name='Form#1')
        #line = PollFormLine.objects.create(pform=pform, type=PollLineType.INT,
                                           #order=1, question='How old is this swallow ?',
                                           #deleted=True
                                          #)
        #self.assertEqual(404, self._delete_line(line).status_code)

    def test_delete_line_ajax01(self):
        "Deleted line depends on other lines"
        line1, line2, line3 = self._create_3_lines_4_conditions()

        create_cond = partial(PollFormLineCondition.objects.create, line=line3,
                              operator=PollFormLineCondition.EQUALS,
                             )
        cond1 = create_cond(source=line1, raw_answer='1')
        cond2 = create_cond(source=line2, raw_answer='2')

        self.assertEqual(200, self._delete_line(line3, ajax=True).status_code)
        self.assertDoesNotExist(line3)
        self.assertDoesNotExist(cond1)
        self.assertDoesNotExist(cond2)

    def test_delete_line_ajax02(self):
        "Deleted line has a line that depends on it"
        line2, line3 = self._create_3_lines_4_conditions()[1:]
        cond = PollFormLineCondition.objects.create(line=line3, source=line2, raw_answer='1',
                                                    operator=PollFormLineCondition.EQUALS
                                                   )

        response = self._delete_line(line2, ajax=True)
        self.assertEqual(403, response.status_code)
        self.assertStillExists(line2)
        self.assertStillExists(cond)
        self.assertEqual(_(u'There is at least one other question which depends on this question.'),
                         smart_unicode(response.content)
                        )

    def test_get_choices01(self):
        "ENUM"
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        choices = [[1, 'White'], [2, 'Black'], [3, 'Green']]
        line = self._get_formline_creator(pform)('What is your favorite color ?',
                                                 qtype=PollLineType.ENUM, choices=choices
                                                )

        response = self.assertGET200(self._build_choices_url(line))
        self.assertEqual(choices, simplejson.loads(response.content))

    def test_get_choices02(self):
        "MULTI_ENUM"
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        choices = [[1, 'Red'], [2, 'Green'], [3, 'Blue'], [4, 'Cyan'], [5, 'Magenta'], [6, 'Yellow']]
        line = self._get_formline_creator(pform)('What colors do you like ?',
                                                 qtype=PollLineType.MULTI_ENUM,
                                                 choices=choices,
                                                )
        response = self.assertGET200(self._build_choices_url(line))
        self.assertEqual(choices, simplejson.loads(response.content))

    def test_get_choices03(self):
        "ENUM_OR_STRING"
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        choices = [[1, 'Cat'], [2, 'Dog'], [3, 'Fish']]
        line = self._get_formline_creator(pform)('What is your pet ?',
                                                 qtype=PollLineType.ENUM_OR_STRING,
                                                 choices=choices,
                                                )
        response = self.assertGET200(self._build_choices_url(line))
        self.assertEqual([[0, _('Other')]] + choices, simplejson.loads(response.content))

    def test_get_choices04(self):
        "BOOL"
        line = PollFormLine.objects.create(pform=PollForm.objects.create(user=self.user, name='Form#1'),
                                           question='Do you love swallows ?',
                                           order=1, type=PollLineType.BOOL,
                                          )
        response = self.assertGET200(self._build_choices_url(line))
        self.assertEqual([[0, _('No')], [1, _('Yes')]], simplejson.loads(response.content))

    def test_get_choices_error01(self):
        "Bad type"
        line = PollFormLine.objects.create(pform=PollForm.objects.create(user=self.user, name='Form#1'),
                                           question='What do you like ?',
                                           order=1, type=PollLineType.STRING,
                                          )
        self.assertGET404(self._build_choices_url(line))

    #TODO: use Nullable feature to avoid query
    def test_condition_getters01(self):
        line = PollFormLine.objects.create(pform=PollForm.objects.create(user=self.user, name='Form#1'),
                                           question='Do you love swallows ?',
                                           order=1, type=PollLineType.INT,
                                          )

        with self.assertNumQueries(1): #TODO 0
            conditions = line.get_conditions()
        self.assertEqual([], conditions)

        with self.assertNumQueries(1): #TODO 0
            conditions = line.get_reversed_conditions()
        self.assertEqual([], conditions)

    def test_condition_getters02(self):
        line1, line2, line3 = self._create_3_lines_4_conditions()
        line4 = PollFormLine.objects.create(pform=line1.pform, order=4, type=PollLineType.BOOL,
                                            question='Do you love green swallows ?',
                                           )

        create_cond = partial(PollFormLineCondition.objects.create,
                              operator=PollFormLineCondition.EQUALS,
                             )
        cond1 = create_cond(line=line3, source=line1, raw_answer='2')
        cond2 = create_cond(line=line3, source=line2, raw_answer='2')
        cond3 = create_cond(line=line4, source=line1, raw_answer='2')

        #TODO
        #line3.use_or = True; line3.save()
        #line4.use_or = True; line3.save()

        with self.assertNumQueries(1): #TODO 0
            conditions = line1.get_conditions()
        self.assertEqual([], conditions)

        with self.assertNumQueries(1): #TODO 0
            conditions = line2.get_conditions()
        self.assertEqual([], conditions)

        with self.assertNumQueries(1):
            conditions = line3.get_conditions()
        self.assertEqual([cond1, cond2], conditions)

        with self.assertNumQueries(0):
            line3.get_conditions()

        with self.assertNumQueries(1):
            conditions = line1.get_reversed_conditions()
        self.assertEqual([cond1, cond3], conditions)

        with self.assertNumQueries(0):
            line1.get_reversed_conditions()

    def test_condition_getters03(self):
        "Use populate_conditions()"
        line1, line2, line3 = self._create_3_lines_4_conditions()
        line4 = PollFormLine.objects.create(pform=line1.pform, order=4, type=PollLineType.BOOL,
                                            question='Do you love green swallows ?',
                                           )

        create_cond = partial(PollFormLineCondition.objects.create, operator=PollFormLineCondition.EQUALS)
        cond1 = create_cond(line=line3, source=line1, raw_answer='2')
        cond2 = create_cond(line=line3, source=line2, raw_answer='2')
        cond3 = create_cond(line=line4, source=line1, raw_answer='2')

        #TODO
        #line3.use_or = True; line3.save()
        #line4.use_or = True; line3.save()

        with self.assertNumQueries(1):
            PollFormLine.populate_conditions([line1, line2, line3, line4])

        with self.assertNumQueries(0):
            conditions = line1.get_conditions()
        self.assertEqual([], conditions)

        with self.assertNumQueries(0):
            conditions = line3.get_conditions()
        self.assertEqual([cond1, cond2], conditions)

        with self.assertNumQueries(0):
            conditions = line1.get_reversed_conditions()
        self.assertEqual([cond1, cond3], conditions)

    def test_print_line_condition(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        line1 = create_line('How do you like swallows ?', qtype=PollLineType.ENUM,
                            choices=[[1, 'A little bit'], [2, 'A lot']],
                           )
        line2 = create_line('How do you like parrots ?', qtype=PollLineType.ENUM_OR_STRING,
                            choices=[[1, 'A little bit'], [2, 'A lot']],
                           )
        line3 = create_line('What nuts do you like ?', qtype=PollLineType.MULTI_ENUM,
                            choices=[[1, 'Coco nuts'], [2, 'Peanuts']],
                           )

        line_with_conds = create_line(question='Do you love all birds ?', order=6,
                                      conds_use_or=False, type=PollLineType.STRING
                                     )

        create_cond = partial(PollFormLineCondition.objects.create, operator=PollFormLineCondition.EQUALS)
        dumps = simplejson.dumps
        cond1 = create_cond(line=line_with_conds, source=line1, raw_answer='2')
        cond2 = create_cond(line=line_with_conds, source=line2, raw_answer=dumps([1]))
        cond3 = create_cond(line=line_with_conds, source=line2, raw_answer=dumps([0]))
        cond4 = create_cond(line=line_with_conds, source=line3, raw_answer=dumps([1]))

        nodes = SectionTree(pform)
        msg_fmt1 = _(u'The answer to the question #%(number)s is «%(answer)s».')
        msg_fmt2 = _(u'The answer to the question #%(number)s contains «%(answer)s».')
        self.assertEqual(msg_fmt1 % {'number': 1, 'answer': 'A lot'},
                         print_line_condition(nodes, cond1)
                        )
        self.assertEqual(msg_fmt1 % {'number': 2, 'answer': 'A little bit'},
                         print_line_condition(nodes, cond2)
                        )
        self.assertEqual(msg_fmt1 % {'number': 2, 'answer': _('Other')},
                         print_line_condition(nodes, cond3)
                        )
        self.assertEqual(msg_fmt2 % {'number': 3, 'answer': 'Coco nuts'},
                         print_line_condition(nodes, cond4)
                        )

        self.assertGET200(pform.get_absolute_url())

    def test_clone01(self):
        "Cloning a form with multiple sections, lines and conditions"
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        create_section = partial(PollFormSection.objects.create, pform=pform)
        create_line = self._get_formline_creator(pform)

        section      = create_section(name='Chapter I',   order=1)
        sub_section1 = create_section(name='Chapter I.1', order=2, parent=section)
        sub_section2 = create_section(name='Chapter I.2', order=3, parent=section)

        line1 = create_line('How do you like swallows ?', qtype=PollLineType.ENUM,
                            section=section, choices=[[1, 'A little bit'], [2, 'A lot']],
                           )
        line2 = create_line('How do you like parrots ?', qtype=PollLineType.ENUM_OR_STRING,
                            section=sub_section1, choices=[[1, 'A little bit'], [2, 'A lot']],
                           )
        line3 = create_line('What nuts do you like ?', qtype=PollLineType.MULTI_ENUM,
                            section=sub_section2, choices=[[1, 'Coco nuts'], [2, 'Peanuts']],
                           )
        line_with_conds = create_line(question='Do you love all birds ?', order=6,
                                      conds_use_or=False, type=PollLineType.STRING
                                     )
        create_cond = partial(PollFormLineCondition.objects.create, operator=PollFormLineCondition.EQUALS)
        dumps = simplejson.dumps
        create_cond(line=line_with_conds, source=line1, raw_answer='2')
        create_cond(line=line_with_conds, source=line2, raw_answer=dumps([1]))
        create_cond(line=line_with_conds, source=line2, raw_answer=dumps([0]))
        create_cond(line=line_with_conds, source=line3, raw_answer=dumps([1]))

        count_pforms = PollForm.objects.count()
        count_sections = PollFormSection.objects.count()
        count_lines = PollFormLine.objects.count()
        count_conditions = PollFormLineCondition.objects.count()

        cloned_pform = pform.clone()

        self.assertEqual(pform.name, cloned_pform.name)
        self.assertEqual(pform.type, cloned_pform.type)

        self.assertEqual(count_pforms + 1, PollForm.objects.count())
        self.assertEqual(count_sections + 3, PollFormSection.objects.count())
        self.assertEqual(count_lines + 4, PollFormLine.objects.count())
        self.assertEqual(count_conditions + 4, PollFormLineCondition.objects.count())

        nodes = list(SectionTree(pform))
        cloned_nodes = list(SectionTree(cloned_pform))
        self.assertEqual(len(nodes), len(cloned_nodes))

        line_attrs = ('order', 'type', 'type_args', 'conds_use_or', 'question')
        section_attrs = ('name', 'body', 'order')

        for node, cnode in zip(nodes, cloned_nodes):
            is_section = node.is_section
            self.assertEqual(is_section, cnode.is_section)

            for attr in (section_attrs if is_section else line_attrs):
                self.assertEqual(getattr(node, attr), getattr(cnode, attr))

    def test_clone02(self):
        "Disabled lines excluded when cloning a form"
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        count_pforms = PollForm.objects.count()

        create_line = self._get_formline_creator(pform)
        create_line('How do you like swallows ?', qtype=PollLineType.ENUM,
                    choices=[[1, 'A little bit'], [2, 'A lot']],
                    disabled=True, #<=======
                   )
        create_line('How do you like parrots ?', qtype=PollLineType.ENUM_OR_STRING,
                    choices=[[1, 'A little bit'], [2, 'A lot']],
                   )

        cloned_pform = pform.clone()
        self.assertEqual(pform.name, cloned_pform.name)
        self.assertEqual(pform.type, cloned_pform.type)

        self.assertEqual(count_pforms + 1, PollForm.objects.count())
        self.assertEqual(1, PollFormLine.objects.filter(pform__id=cloned_pform.id).count())
