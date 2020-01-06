# -*- coding: utf-8 -*-

from ..core.function_field import FunctionField, FunctionFieldResult, FunctionFieldResultsList


class FakeTodosField(FunctionField):
    name = 'tests-fake_todos'
    verbose_name = 'Fake Todos'
    result_type = FunctionFieldResultsList

    def __call__(self, entity, user):
        return FunctionFieldResultsList(
                FunctionFieldResult('Todo {} #{}'.format(entity, i))
                    for i in range(1, 3)
        )
