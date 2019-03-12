# -*- coding: utf-8 -*-

# from django.db.models.query_utils import Q

from ..core.function_field import FunctionField, FunctionFieldResult, FunctionFieldResultsList

# from .fake_constants import FAKE_PERCENT_UNIT, FAKE_AMOUNT_UNIT


class FakeTodosField(FunctionField):
    name = 'tests-fake_todos'
    verbose_name = 'Fake Todos'
    # # has_filter   = False #==> cannot search
    result_type = FunctionFieldResultsList

    def __call__(self, entity, user):
        return FunctionFieldResultsList(
                FunctionFieldResult('Todo {} #{}'.format(entity, i))
                    for i in range(1, 3)
        )


# class GreatDiscountField(FunctionField):
#     name = 'tests-great_discount'
#     verbose_name = 'Great discount'
#     has_filter = True
#     choices = [
#         (1, 'Bad'),
#         (2, 'Not bad'),
#         (3, 'Great'),
#     ]
#
#     @classmethod
#     def filter_in_result(cls, search_string):
#         if search_string == '1':
#             return Q(discount_unit=FAKE_AMOUNT_UNIT) | \
#                    Q(discount_unit=FAKE_PERCENT_UNIT, discount__lt='3.0')
#
#         if search_string == '2':
#             return Q(discount_unit=FAKE_PERCENT_UNIT, discount__gte='3.0') & \
#                    Q(discount_unit=FAKE_PERCENT_UNIT, discount__lt='5.0')
#
#         if search_string == '3':
#             return Q(discount_unit=FAKE_PERCENT_UNIT, discount__gte='5.0')
#
#         return Q()
#
#     def __call__(self, entity, user):
#         return self.result_type('Bad')
