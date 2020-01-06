# -*- coding: utf-8 -*-

# import warnings
#
# from django import template
# from django.template.defaultfilters import truncatewords
#
# register = template.Library()
#
#
# @register.filter(name='truncate')
# def truncate(word, truncate_at):
#     warnings.warn('The filter "|truncate" (crudity_tags) is deprecated ;'
#                   'use "|truncatewords" and "|truncatewords" instead.',
#                   DeprecationWarning
#                  )
#
#     words = truncatewords(word, truncate_at)
#     word = str(word)
#     truncated = word[:truncate_at]
#
#     if len(words.split()) == 1 and not len(truncated) == len(word):
#         words = '{}...'.format(truncated)
#
#     return words
