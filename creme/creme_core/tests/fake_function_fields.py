# -*- coding: utf-8 -*-

from ..core.function_field import (
    FunctionField,
    FunctionFieldResult,
    FunctionFieldResultsList,
)
from ..models import FakeTodo


# NB: we could had a search feature of course, but we need a FunctionField which has not.
#     see creme.creme_core.tests.views.test_listview.ListViewTestCase.test_search_functionfield02()
class FakeTodosField(FunctionField):
    name = 'tests-fake_todos'
    verbose_name = 'Fake Todos'
    result_type = FunctionFieldResultsList

    def __call__(self, entity, user):
        return FunctionFieldResultsList(
            # FunctionFieldResult('Todo {} #{}'.format(entity, i))
            #     for i in range(1, 3)
            FunctionFieldResult(str(todo))
            for todo in FakeTodo.objects.filter(entity=entity)
        )
