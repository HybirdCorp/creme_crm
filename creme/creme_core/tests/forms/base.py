import warnings
from sys import exc_info
from traceback import format_exception

from django.core.exceptions import ValidationError

from ..base import CremeTestCase


def _format_stack():
    warnings.warn('_format_stack() is deprecated.', DeprecationWarning)

    exc_type, exc_value, exc_traceback = exc_info()
    return ''.join(format_exception(exc_type, exc_value, exc_traceback))


class FieldTestCaseMixin(CremeTestCase):  # DEPRECATED
    def assertFieldRaises(self, exception, func, *args, **kwargs):
        warnings.warn(
            'FieldTestCaseMixin.assertFieldRaises() is deprecated ; '
            'use assertRaises() instead.',
            DeprecationWarning,
        )

        try:
            func(*args, **kwargs)
        except exception as e:
            return e, _format_stack()

        exception_name = getattr(exception, '__name__', None) or str(exception)
        self.fail(f'{exception_name} not raised')

    def assertFieldValidationError(self, field, key, func, *args, **kwargs):
        warnings.warn(
            'FieldTestCaseMixin.assertFieldValidationError() is deprecated ; '
            'use _CremeTestCase.assertFormfieldError() instead.',
            DeprecationWarning,
        )

        message_args = kwargs.pop('message_args', {})   # Pop error message args from kwargs
        err, stack = self.assertFieldRaises(ValidationError, func, *args, **kwargs)
        message = str(field().error_messages[key] % message_args)

        if not hasattr(err, 'messages'):
            self.fail(f'unexpected empty message instead of "{message}"\nerror : {stack}')

        if message != err.messages[0]:
            self.fail(
                f'unexpected message "{err.messages[0]}" instead '
                f'of "{message}"\nerror : {stack}'
            )


class FieldTestCase(FieldTestCaseMixin, CremeTestCase):  # DEPRECATED
    pass
