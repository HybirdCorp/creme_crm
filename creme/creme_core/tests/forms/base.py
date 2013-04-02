# -*- coding: utf-8 -*-

from sys import exc_info
from traceback import format_exception

from django.core.exceptions import ValidationError

from ..base import CremeTestCase


def _format_stack(): #TODO: in utils ??
    exc_type, exc_value, exc_traceback = exc_info()
    return ''.join(format_exception(exc_type, exc_value, exc_traceback))

#def format_function(func):
    #return func.__module__ + '.' + func.__name__.lstrip('<').rstrip('>') + '()' if func else 'None'


class FieldTestCase(CremeTestCase):
    def assertFieldRaises(self, exception, func, *args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            return (e, _format_stack())

        exception_name = getattr(exception, '__name__', None) or str(exception)
        self.fail("%s not raised" % exception_name)

    def assertFieldValidationError(self, field, key, func, *args, **kwargs):
        message_args = kwargs.pop('message_args', {})   # pop error message args from kwargs
        err, stack = self.assertFieldRaises(ValidationError, func, *args, **kwargs)
        message = unicode(field().error_messages[key] % message_args)

        if not hasattr(err, 'messages'):
            self.fail('unexpected empty message instead of "%s"\nerror : %s' % (message, stack))

        if message != err.messages[0]:
            self.fail('unexpected message "%s" instead of "%s"\nerror : %s' % (err.messages[0], message, stack))
