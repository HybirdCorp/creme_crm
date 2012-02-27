# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType
    from django.utils.translation import ugettext as _

    from persons.models import Contact

    from commercial.models import *
    from commercial.tests.base import CommercialBaseTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('ActObjectivePatternTestCase',)


class ActObjectivePatternTestCase(CommercialBaseTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'persons', 'commercial')

    def test_create(self):
        url = '/commercial/objective_pattern/add'
        self.assertEqual(200, self.client.get(url).status_code)

        segment = self._create_segment()
        name = 'ObjPattern#1'
        average_sales = 5000
        response = self.client.post(url, follow=True,
                                    data={'user':          self.user.pk,
                                          'name':          name,
                                          'average_sales': average_sales,
                                          'segment':       segment.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.redirect_chain)
        self.assertEqual(len(response.redirect_chain), 1)

        patterns = ActObjectivePattern.objects.all()
        self.assertEqual(1, len(patterns))

        pattern = patterns[0]
        self.assertEqual(name,          pattern.name)
        self.assertEqual(average_sales, pattern.average_sales)
        self.assertEqual(segment,       pattern.segment)

    def _create_pattern(self, name='ObjPattern', average_sales=1000):
        return ActObjectivePattern.objects.create(user=self.user, name=name,
                                                  average_sales=average_sales,
                                                  segment=self._create_segment(),
                                                 )

    def test_edit(self):
        name = 'ObjPattern'
        average_sales = 1000
        pattern = self._create_pattern(name, average_sales)

        url = '/commercial/objective_pattern/edit/%s' % pattern.id
        self.assertEqual(200, self.client.get(url).status_code)

        name += '_edited'
        average_sales *= 2
        segment = self._create_segment()
        response = self.client.post(url, data={'user':          self.user.pk,
                                               'name':          name,
                                               'average_sales': average_sales,
                                               'segment':       segment.id,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(302, response.status_code)

        pattern = self.refresh(pattern)
        self.assertEqual(name,          pattern.name)
        self.assertEqual(average_sales, pattern.average_sales)
        self.assertEqual(segment,       pattern.segment)

    def test_listview(self):
        create_patterns = ActObjectivePattern.objects.create
        patterns = [create_patterns(user=self.user,
                                    name='ObjPattern#%s' % i,
                                    average_sales=1000 * i,
                                    segment=self._create_segment(),
                                   ) for i in xrange(1, 4)
                   ]

        response = self.client.get('/commercial/objective_patterns')
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            patterns_page = response.context['entities']

        self.assertEqual(1, patterns_page.number)
        self.assertEqual(3, patterns_page.paginator.count)
        self.assertEqual(set(patterns), set(patterns_page.object_list))

    def test_add_root_pattern_component01(self): #no parent component, no counted relation
        pattern  = self._create_pattern()

        url = '/commercial/objective_pattern/%s/add_component' % pattern.id
        self.assertEqual(200, self.client.get(url).status_code)

        name = 'Signed opportunities'
        response = self.client.post(url, data={'name':         name,
                                               'success_rate': 10,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        components = pattern.components.all()
        self.assertEqual(1, len(components))

        component = components[0]
        self.assertEqual(name, component.name)
        self.assertIsNone(component.parent)
        self.assertIsNone(component.ctype)

    def test_add_root_pattern_component02(self): #counted relation (no parent component)
        pattern = self._create_pattern()
        name = 'Called contacts'
        ct = ContentType.objects.get_for_model(Contact)
        response = self.client.post('/commercial/objective_pattern/%s/add_component' % pattern.id,
                                    data={'name':         name,
                                          'ctype':        ct.id,
                                          'success_rate': 15,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        components = pattern.components.all()
        self.assertEqual(1, len(components))

        component = components[0]
        self.assertEqual(name, component.name)
        self.assertEqual(ct,   component.ctype)

    def test_add_child_pattern_component01(self): #parent component
        pattern = self._create_pattern()
        comp01 = ActObjectivePatternComponent.objects.create(name='Signed opportunities',
                                                             pattern=pattern, success_rate=50
                                                            )

        url = '/commercial/objective_pattern/component/%s/add_child' % comp01.id
        self.assertEqual(200, self.client.get(url).status_code)

        name = 'Spread Vcards'
        response = self.client.post(url, data={'name':         name,
                                               'success_rate': 20,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        children = comp01.children.all()
        self.assertEqual(1, len(children))

        comp02 = children[0]
        self.assertEqual(name,   comp02.name)
        self.assertEqual(comp01, comp02.parent)
        self.assertIsNone(comp02.ctype)

        name = 'Called contacts'
        ct   = ContentType.objects.get_for_model(Contact)
        response = self.client.post(url, data={'name':         name,
                                               'ctype':        ct.id,
                                               'success_rate': 60,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertEqual(2,   comp01.children.count())

        with self.assertNoException():
            comp03 = comp01.children.get(name=name)

        self.assertEqual(ct, comp03.ctype)

    def test_add_parent_pattern_component01(self):
        pattern = self._create_pattern()
        comp01 = ActObjectivePatternComponent.objects.create(name='Sent mails',
                                                             pattern=pattern,
                                                             success_rate=5
                                                            )

        url = '/commercial/objective_pattern/component/%s/add_parent' % comp01.id
        self.assertEqual(200, self.client.get(url).status_code)

        name = 'Signed opportunities'
        success_rate = 50
        response = self.client.post(url, data={'name':         name,
                                               'success_rate': success_rate,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        pattern = self.refresh(pattern)
        components = pattern.components.order_by('id')
        self.assertEqual(2, len(components))

        child = components[0]
        self.assertEqual(comp01, child)

        parent = components[1]
        self.assertEqual(name,         parent.name)
        self.assertEqual(success_rate, parent.success_rate)
        self.assertIsNone(parent.parent)
        self.assertEqual(child.parent, parent)

    def test_add_parent_pattern_component02(self):
        pattern = self._create_pattern()

        create_comp = ActObjectivePatternComponent.objects.create
        comp01 = create_comp(name='Signed opportunities', pattern=pattern, success_rate=50)
        comp02 = create_comp(name='Spread Vcards',        pattern=pattern, success_rate=1, parent=comp01)

        name = 'Called contacts'
        ct   = ContentType.objects.get_for_model(Contact)
        response = self.client.post('/commercial/objective_pattern/component/%s/add_parent' % comp02.id,
                                    data={'name':         name,
                                          'ctype':        ct.id,
                                          'success_rate': 20,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        pattern = ActObjectivePattern.objects.get(pk=pattern.id)
        components = pattern.components.order_by('id')
        self.assertEqual(3, len(components))

        grandpa = components[0]
        self.assertEqual(comp01, grandpa)

        child = components[1]
        self.assertEqual(comp02, child)

        parent = components[2]
        self.assertEqual(name, parent.name)
        self.assertEqual(ct,   parent.ctype)

        self.assertEqual(child.parent,  parent)
        self.assertEqual(parent.parent, grandpa)

    def test_add_pattern_component_errors(self):
        pattern = self._create_pattern()

        response = self.client.post('/commercial/objective_pattern/%s/add_component' % pattern.id,
                                    data={'name':         'Signed opportunities',
                                          'success_rate': 0, #minimunm is 1
                                         }
                                   )
        self.assertFormError(response, 'form', 'success_rate',
                             [_(u'Ensure this value is greater than or equal to %(limit_value)s.') % {'limit_value': 1}]
                            )

        response = self.client.post('/commercial/objective_pattern/%s/add_component' % pattern.id,
                                    data={'name':         'Signed opportunities',
                                          'success_rate': 101, #maximum is 100
                                         }
                                   )
        self.assertFormError(response, 'form', 'success_rate',
                             [_(u'Ensure this value is less than or equal to %(limit_value)s.') % {'limit_value': 100}]
                            )

    def test_get_component_tree(self):
        pattern = self._create_pattern()

        create_component = ActObjectivePatternComponent.objects.create
        root01  = create_component(name='Root01',   pattern=pattern,                 success_rate=1)
        root02  = create_component(name='Root02',   pattern=pattern,                 success_rate=1)
        child01 = create_component(name='Child 01', pattern=pattern, parent=root01,  success_rate=1)
        child11 = create_component(name='Child 11', pattern=pattern, parent=child01, success_rate=1)
        child12 = create_component(name='Child 12', pattern=pattern, parent=child01, success_rate=1)
        child13 = create_component(name='Child 13', pattern=pattern, parent=child01, success_rate=1)
        child02 = create_component(name='Child 02', pattern=pattern, parent=root01,  success_rate=1)
        child21 = create_component(name='Child 21', pattern=pattern, parent=child02, success_rate=1)

        comptree = pattern.get_components_tree() #TODO: test that no additionnal queries are done ???
        self.assertIsInstance(comptree, list)
        self.assertEqual(2, len(comptree))

        rootcomp01 = comptree[0]
        self.assertIsInstance(rootcomp01, ActObjectivePatternComponent)
        self.assertEqual(root01, rootcomp01)
        self.assertEqual(root02, comptree[1])

        children = rootcomp01.get_children()
        self.assertEqual(2, len(children))

        compchild01 = children[0]
        self.assertIsInstance(compchild01, ActObjectivePatternComponent)
        self.assertEqual(child01, compchild01)
        self.assertEqual(3, len(compchild01.get_children()))

        self.assertEqual(1, len(children[1].get_children()))

    def test_delete_pattern_component01(self):
        pattern = self._create_pattern()
        comp01 = ActObjectivePatternComponent.objects.create(name='Signed opportunities',
                                                             pattern=pattern, success_rate=20
                                                            )
        ct = ContentType.objects.get_for_model(ActObjectivePatternComponent)

        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id,
                                    data={'id': comp01.id}
                                   )
        self.assertNoFormError(response)
        self.assertEqual(302, response.status_code)
        self.assertEqual(0,   ActObjectivePatternComponent.objects.filter(pk=comp01.id).count())

    def test_delete_pattern_component02(self):
        pattern = self._create_pattern()
        create_comp = ActObjectivePatternComponent.objects.create
        comp00 = create_comp(name='Signed opportunities', pattern=pattern,                success_rate=1) #NB: should not be removed
        comp01 = create_comp(name='DELETE ME',            pattern=pattern,                success_rate=1)
        comp02 = create_comp(name='Will be orphaned01',   pattern=pattern, parent=comp01, success_rate=1)
        comp03 = create_comp(name='Will be orphaned02',   pattern=pattern, parent=comp01, success_rate=1)
        comp04 = create_comp(name='Will be orphaned03',   pattern=pattern, parent=comp02, success_rate=1)
        comp05 = create_comp(name='Smiles done',          pattern=pattern,                success_rate=1) #NB: should not be removed
        comp06 = create_comp(name='Stand by me',          pattern=pattern, parent=comp05, success_rate=1) #NB: should not be removed

        ct = ContentType.objects.get_for_model(ActObjectivePatternComponent)
        response = self.client.post('/creme_core/entity/delete_related/%s' % ct.id, data={'id': comp01.id})
        self.assertNoFormError(response)
        self.assertEqual(302, response.status_code)

        remaining_ids = pattern.components.values_list('id', flat=True)
        self.assertEqual(3, len(remaining_ids))
        self.assertEqual(set([comp00.id, comp05.id, comp06.id]), set(remaining_ids))

    def test_actobjectivepattern_clone01(self):
        pattern  = self._create_pattern()
        create_comp = ActObjectivePatternComponent.objects.create

        comp1   = create_comp(name='1',     pattern=pattern,                success_rate=1)
        comp11  = create_comp(name='1.1',   pattern=pattern, parent=comp1,  success_rate=1)
        comp111 = create_comp(name='1.1.1', pattern=pattern, parent=comp11, success_rate=1)
        comp112 = create_comp(name='1.1.2', pattern=pattern, parent=comp11, success_rate=1)
        comp12  = create_comp(name='1.2',   pattern=pattern, parent=comp1,  success_rate=1)
        comp121 = create_comp(name='1.2.1', pattern=pattern, parent=comp12, success_rate=1)
        comp122 = create_comp(name='1.2.2', pattern=pattern, parent=comp12, success_rate=1)
        comp2   = create_comp(name='2',     pattern=pattern,                success_rate=1)
        comp21  = create_comp(name='2.1',   pattern=pattern, parent=comp2,  success_rate=1)
        comp211 = create_comp(name='2.1.1', pattern=pattern, parent=comp21, success_rate=1)
        comp212 = create_comp(name='2.1.2', pattern=pattern, parent=comp21, success_rate=1)
        comp22  = create_comp(name='2.2',   pattern=pattern, parent=comp2,  success_rate=1)
        comp221 = create_comp(name='2.2.1', pattern=pattern, parent=comp22, success_rate=1)
        comp222 = create_comp(name='2.2.2', pattern=pattern, parent=comp22, success_rate=1)

        cloned_pattern = pattern.clone()

        filter_comp = ActObjectivePatternComponent.objects.filter
        filter_get = ActObjectivePatternComponent.objects.get

        self.assertEqual(14, filter_comp(pattern=cloned_pattern).count())
        self.assertEqual(2,  filter_comp(pattern=cloned_pattern, parent=None).count())
        self.assertEqual(1,  filter_comp(pattern=cloned_pattern, name=comp1.name).count())

        self.assertEqual(set(['1.1', '1.2']),
                         set(filter_get(pattern=cloned_pattern, name=comp1.name).children.values_list('name', flat=True))
                        )
        self.assertEqual(set(['1.1.1', '1.1.2', '1.2.1', '1.2.2']),
                         set(filter_comp(pattern=cloned_pattern, parent__name__in=['1.1', '1.2']) \
                                        .values_list('name', flat=True)
                            )
                        )
        self.assertEqual(1, filter_comp(pattern=cloned_pattern, name=comp2.name).count())
        self.assertEqual(set(['2.1', '2.2']),
                         set(filter_get(pattern=cloned_pattern, name=comp2.name) \
                                       .children.values_list('name', flat=True)
                            )
                        )
        self.assertEqual(set(['2.1.1', '2.1.2', '2.2.1', '2.2.2']),
                         set(filter_comp(pattern=cloned_pattern, parent__name__in=['2.1', '2.2']) \
                                        .values_list('name', flat=True)
                            )
                        )
