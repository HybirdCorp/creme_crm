# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

# import warnings
from os.path import splitext
from typing import Any, Callable, Iterator, Type

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Field, Manager, Model
from django.template.defaultfilters import linebreaks
from django.urls import reverse
from django.utils.formats import date_format, number_format
from django.utils.html import escape, format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.timezone import localtime
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from ..core.download import (
    DownLoadableFileField,
    FileFieldDownLoadRegistry,
    filefield_download_registry,
)
from ..models import CremeEntity, EntityFilter, fields
from ..templatetags.creme_widgets import widget_entity_hyperlink, widget_urlize
from ..utils import bool_as_html
from ..utils.collections import ClassKeyedMap
from ..utils.meta import FieldInfo

# TODO: in settings
MAX_HEIGHT: int = 200
MAX_WIDTH: int = 200

# NB: 2nd argument is "user".
#     3rd argument is "value" (value of the field for the instance -- ie 1rst argument).
FieldPrinter = Callable[[Model, Any, Any, Field], str]
# NB: 2nd argument is "user".
NonePrinter = Callable[[Model, Any, Field], str]
# NB: 2nd argument is "user".
ReducedPrinter = Callable[[Model, Any], str]
# NB: 2nd argument is M2M value of the related instance.
#     3rd argument is "user".
M2MEnumerator = Callable[[Model, Manager, Any, Field], Iterator[Model]]
# NB: 1st argument is the instance to print
#     2nd argument is the related instance, the one with the ManyToManyField
#                  (so 1st argument is one the instance related to it)
#     3rd argument M2M value of the related instance.
#     4th argument is "user".
M2MInstancePrinter = Callable[[Model, Model, Manager, Any, Field], str]


def image_size(image, max_h: int = MAX_HEIGHT, max_w: int = MAX_WIDTH) -> str:
    if hasattr(image, 'height'):
        h = image.height
    elif hasattr(image, 'height_field'):
        h = image.height_field
    else:
        h = max_h
    if hasattr(image, 'width'):
        w = image.width
    elif hasattr(image, 'width_field'):
        w = image.width_field
    else:
        w = max_w

    h = float(h)
    w = float(w)

    ratio = max(h / max_h, w / max_w)

    if ratio >= 1.0:
        h /= ratio
        w /= ratio

    return format_html('height="{}" width="{}"', h, w)


def simple_print_html(entity: Model, fval, user, field: Field) -> str:
    return escape(fval) if fval is not None else ''


def simple_print_csv(entity: Model, fval, user, field: Field) -> str:
    return str(fval) if fval is not None else ''


def print_choice(entity: Model, fval, user, field: Field) -> str:
    choice = getattr(entity, f'get_{field.name}_display')()
    return str(choice) if choice is not None else ''


def print_color_html(entity: Model, fval, user, field: Field) -> str:
    return format_html(
        '''<span style="background:#{color};">{color}</span>''',
        color=fval,
    ) if fval else ''


class FileFieldPrinterForHTML:
    def __init__(self, registry: FileFieldDownLoadRegistry):
        self.registry = registry

    def __call__(self, entity: Model, fval, user, field: Field) -> str:
        if fval:
            fname = field.name
            registry = self.registry

            try:
                dl_filefield = registry.get(
                    user=user,
                    instance=entity,
                    field_name=fname,
                )
            except registry.InvalidField:
                return simple_print_html(entity, fval, user, field)

            ct_id = ContentType.objects.get_for_model(entity).id

            return self._render_download(
                url=reverse('creme_core__download', args=(ct_id, entity.id, fname)),
                dl_filefield=dl_filefield,
                entity=entity,
                user=user,
            )

        return ''

    @staticmethod
    def _render_download(*,
                         url: str,
                         dl_filefield: DownLoadableFileField,
                         entity: Model,
                         user) -> str:
        file_name = dl_filefield.base_name
        ext = splitext(file_name)[1]

        if ext:
            ext = ext[1:]  # remove '.'

        if ext in settings.ALLOWED_IMAGES_EXTENSIONS:
            return format_html(
                """<a onclick="creme.dialogs.image('{url}').open();">"""
                """<img src="{url}" {size} alt="{label}"/>"""
                """</a>""",
                url=url,
                label=_('Download «{file}»').format(file=file_name),
                size=image_size(dl_filefield.file),   # TODO: fix to use the file
            )
        else:
            return format_html(
                '<a href="{url}" alt="{label}">{label}</a>',
                url=url,
                label=_('Download «{file}»').format(file=file_name),
            )


print_file_html = print_image_html = FileFieldPrinterForHTML(registry=filefield_download_registry)


# def print_integer(entity: Model, fval, user, field: Field) -> str:
#     warnings.warn(
#         'The function creme_core.gui.field_printers.print_integer() is deprecated.',
#         DeprecationWarning
#     )
#
#     if field.choices:
#         fval = getattr(entity, f'get_{field.name}_display')()
#
#     return str(fval) if fval is not None else ''


def print_integer_html(entity: Model, fval, user, field: Field) -> str:
    # TODO remove 'use_l10n' when settings.USE_L10N == True
    # NB: force grouping instead of <USE_THOUSAND_SEPARATOR = True> in settings
    #     to not impact CSV output, reports etc...
    return number_format(fval, use_l10n=True, force_grouping=True) if fval is not None else ''


# def print_decimal(entity: Model, fval, user, field: Field) -> str:
#     warnings.warn(
#         'The function creme_core.gui.field_printers.print_decimal() is deprecated.',
#         DeprecationWarning
#     )
#
#     return number_format(fval, use_l10n=True) if fval is not None else ''


def print_decimal_html(entity: Model, fval, user, field: Field) -> str:
    # TODO remove 'use_l10n' when settings.USE_L10N == True
    return number_format(fval, use_l10n=True, force_grouping=True) if fval is not None else ''


def print_decimal_csv(entity: Model, fval, user, field: Field) -> str:
    # TODO remove 'use_l10n' when settings.USE_L10N == True
    return number_format(fval, use_l10n=True) if fval is not None else ''


def print_boolean_html(entity: Model, fval, user, field: Field) -> str:
    return bool_as_html(fval) if fval is not None else ''


def print_boolean_csv(entity: Model, fval, user, field: Field) -> str:
    if fval is None:
        return ''

    return _('Yes') if fval else _('No')


def print_url_html(entity: Model, fval, user, field: Field) -> str:
    return format_html('<a href="{url}" target="_blank">{url}</a>', url=fval) if fval else ''


def print_datetime(entity: Model, fval, user, field: Field) -> str:
    return date_format(localtime(fval), 'DATETIME_FORMAT') if fval else ''


def print_date(entity: Model, fval, user, field: Field) -> str:
    return date_format(fval, 'DATE_FORMAT') if fval else ''


class FKPrinter:
    @staticmethod
    def print_fk_null_html(entity: Model, user, field: Field):
        null_label = field.get_null_label()
        return format_html('<em>{}</em>', null_label) if null_label else ''

    @staticmethod
    def print_fk_entity_html(entity: Model, fval, user, field: Field) -> str:
        return widget_entity_hyperlink(fval, user)

    @staticmethod
    def print_fk_entity_csv(entity: Model, fval, user, field: Field) -> str:
        # TODO: change allowed_str() ??
        return str(fval) if user.has_perm_to_view(fval) else settings.HIDDEN_VALUE

    @staticmethod
    def print_fk_efilter_html(entity: Model, fval, user, field: Field) -> str:
        return format_html(
            '<div class="entity_filter-summary">{}<ul>{}</ul></div>',
            fval.name,
            format_html_join(
                '', '<li>{}</li>',
                ((vc,) for vc in fval.get_verbose_conditions(user)),
            )
        )

    def __init__(self,
                 none_printer: NonePrinter,
                 default_printer: FieldPrinter):
        self.none_printer = none_printer
        self._sub_printers = ClassKeyedMap(default=default_printer)

    def __call__(self, entity: Model, fval, user, field: Field):
        if fval is None:
            return self.none_printer(entity, user, field)

        sub_printer = self._sub_printers[fval.__class__]
        assert sub_printer is not None  # NB: default_printer is not None

        return sub_printer(entity, fval, user, field)

    def register(self, model: Type[Model], printer: FieldPrinter) -> 'FKPrinter':
        self._sub_printers[model] = printer
        return self


print_foreignkey_html = FKPrinter(
    none_printer=FKPrinter.print_fk_null_html,
    default_printer=simple_print_html,
).register(
    model=CremeEntity,  printer=FKPrinter.print_fk_entity_html,
).register(
    model=EntityFilter, printer=FKPrinter.print_fk_efilter_html,
)


print_foreignkey_csv = FKPrinter(
    none_printer=lambda *args, **kwargs: '',
    default_printer=simple_print_html,
).register(
    model=CremeEntity, printer=FKPrinter.print_fk_entity_csv,
)


class BaseM2MPrinter:
    @staticmethod
    def enumerator_all(
            entity: Model,
            fval: Manager,
            user,
            field: Field) -> Iterator[Model]:
        return fval.all()

    @staticmethod
    def enumerator_entity(
            entity: Model,
            fval: Manager,
            user,
            field: Field) -> Iterator[Model]:
        return fval.filter(is_deleted=False)

    def __init__(
            self,
            default_printer: M2MInstancePrinter,
            default_enumerator: M2MEnumerator):
        self._sub_printers = ClassKeyedMap(default=(default_printer, default_enumerator))

    def __call__(self, entity: Model, fval, user, field: Field) -> str:
        raise NotImplementedError

    def register(self,
                 model: Type[Model],
                 printer: M2MInstancePrinter,
                 enumerator: M2MEnumerator) -> 'BaseM2MPrinter':
        self._sub_printers[model] = (printer, enumerator)
        return self


class M2MPrinterForHTML(BaseM2MPrinter):
    @staticmethod
    def printer_html(
            instance: Model,
            related_entity: Model,
            fval: Manager,
            user,
            field: Field) -> str:
        return escape(instance)

    @staticmethod
    def printer_entity_html(
            instance: Model,
            related_entity: Model,
            fval: Manager,
            user,
            field: Field) -> str:
        assert isinstance(instance, CremeEntity)

        return format_html(
            '<a target="_blank" href="{url}"{attrs}>{content}</a>',
            url=instance.get_absolute_url(),
            attrs=mark_safe(' class="is_deleted"' if instance.is_deleted else ''),
            content=instance.get_entity_summary(user),
        ) if user.has_perm_to_view(instance) else settings.HIDDEN_VALUE

    def __call__(self, entity: Model, fval, user, field: Field) -> str:
        assert isinstance(fval, Manager)

        print_enum = self._sub_printers[fval.model]
        assert print_enum is not None  # NB: default value is not None

        printer, enumerator = print_enum
        li_tags = format_html_join(
            '', '<li>{}</li>',
            (
                (printer(e, entity, fval, user, field),)
                for e in enumerator(entity, fval, user, field)
            )
        )

        return format_html('<ul>{}</ul>', li_tags) if li_tags else ''


# class M2MPrinter(M2MPrinterForHTML):
#     def __init__(self, *args, **kwargs):
#         warnings.warn(
#             'The class creme_core.gui.field_printers.M2MPrinter is deprecated ; '
#             'use M2MPrinterForHTML instead.',
#             DeprecationWarning
#         )
#         super().__init__(*args, **kwargs)


print_many2many_html = M2MPrinterForHTML(
    default_printer=M2MPrinterForHTML.printer_html,
    default_enumerator=M2MPrinterForHTML.enumerator_all,
).register(
    CremeEntity,
    printer=M2MPrinterForHTML.printer_entity_html,
    enumerator=M2MPrinterForHTML.enumerator_entity,
)


class M2MPrinterForCSV(BaseM2MPrinter):
    @staticmethod
    def printer_csv(
            instance: Model,
            related_entity: Model,
            fval: Manager,
            user,
            field: Field) -> str:
        return str(instance)

    @staticmethod
    def printer_entity_csv(
            instance: Model,
            related_entity: Model,
            fval: Manager,
            user,
            field: Field) -> str:
        assert isinstance(instance, CremeEntity)

        # TODO: CSV summary ?? [e.get_entity_m2m_summary(user)]
        return str(instance) if user.has_perm_to_view(instance) else settings.HIDDEN_VALUE

    def __call__(self, entity: Model, fval, user, field: Field) -> str:
        assert isinstance(fval, Manager)

        print_enum = self._sub_printers[fval.model]
        assert print_enum is not None  # NB: default value is not None

        printer, enumerator = print_enum

        return '/'.join(
            printer(e, entity, fval, user, field)
            for e in enumerator(entity, fval, user, field)
        )


print_many2many_csv = M2MPrinterForCSV(
    default_printer=M2MPrinterForCSV.printer_csv,
    default_enumerator=M2MPrinterForCSV.enumerator_all,
).register(
    CremeEntity,
    printer=M2MPrinterForCSV.printer_entity_csv,
    enumerator=M2MPrinterForCSV.enumerator_entity,
)


def print_duration(entity: Model, fval, user, field: Field) -> str:
    try:
        h, m, s = fval.split(':')
    except (ValueError, AttributeError):
        return ''

    h = int(h)
    m = int(m)
    s = int(s)

    return '{hour} {hour_label} {minute} {minute_label} {second} {second_label}'.format(
        hour=h,
        hour_label=ngettext('hour', 'hours', h),
        minute=m,
        minute_label=ngettext('minute', 'minutes', m),
        second=s,
        second_label=ngettext('second', 'seconds', s)
    )


def print_email_html(entity: Model, fval, user, field: Field) -> str:
    return format_html(
        '<a href="mailto:{email}">{email}</a>',
        email=fval,
    ) if fval else ''


def print_text_html(entity: Model, fval, user, field: Field) -> str:
    return mark_safe(linebreaks(widget_urlize(fval, autoescape=True))) if fval else ''


def print_unsafehtml_html(entity: Model, fval, user, field: Field) -> str:
    return linebreaks(fval, autoescape=True) if fval else ''


# TODO: Do more specific fields (i.e: currency field....) ?
class _FieldPrintersRegistry:
    def __init__(self):
        self._html_printers = ClassKeyedMap(
            [
                (models.IntegerField,       print_integer_html),

                (models.FloatField,         print_decimal_html),
                (models.DecimalField,       print_decimal_html),

                (models.BooleanField,       print_boolean_html),
                (models.NullBooleanField,   print_boolean_html),

                (models.DateField,          print_date),
                (models.DateTimeField,      print_datetime),

                (models.TextField,          print_text_html),
                (models.EmailField,         print_email_html),
                (models.URLField,           print_url_html),

                (models.FileField,          print_file_html),
                (models.ImageField,         print_image_html),

                (models.ForeignKey,         print_foreignkey_html),
                (models.ManyToManyField,    print_many2many_html),
                (models.OneToOneField,      print_foreignkey_html),

                (fields.DurationField,      print_duration),
                (fields.DatePeriodField,    simple_print_html),  # TODO: JSONField ?

                (fields.ColorField,         print_color_html),

                (fields.UnsafeHTMLField,    print_unsafehtml_html),
            ],
            default=simple_print_html,
        )

        self._csv_printers = ClassKeyedMap(
            [
                (models.FloatField,         print_decimal_csv),
                (models.DecimalField,       print_decimal_csv),

                (models.BooleanField,       print_boolean_csv),
                (models.NullBooleanField,   print_boolean_csv),

                (models.DateField,          print_date),
                (models.DateTimeField,      print_datetime),
                # (models.ImageField,         print_image_csv, TODO ??

                (models.ForeignKey,         print_foreignkey_csv),
                (models.ManyToManyField,    print_many2many_csv),
                (models.OneToOneField,      print_foreignkey_csv),

                (fields.DurationField,      print_duration),
            ],
            default=simple_print_csv,
        )

        self._printers_maps = {
            'html': self._html_printers,
            'csv':  self._csv_printers,
        }
        self._choice_printers = {
            'html': print_choice,
            'csv':  print_choice,
        }

        css_default        = getattr(settings, 'CSS_DEFAULT_LISTVIEW')
        css_default_header = getattr(settings, 'CSS_DEFAULT_HEADER_LISTVIEW')

        css_number_lv      = getattr(settings, 'CSS_NUMBER_LISTVIEW',      css_default)
        css_textarea_lv    = getattr(settings, 'CSS_TEXTAREA_LISTVIEW',    css_default)
        css_date_lv_header = getattr(settings, 'CSS_DATE_HEADER_LISTVIEW', css_default_header)

        self._listview_css_printers = ClassKeyedMap(
            [
                (models.IntegerField,               css_number_lv),
                (models.CommaSeparatedIntegerField, css_number_lv),
                (models.DecimalField,               css_number_lv),
                (models.FloatField,                 css_number_lv),

                (models.TextField,                  css_textarea_lv),
            ],
            default=css_default,
        )

        self._header_listview_css_printers = ClassKeyedMap(
            [
                (models.DateField,      css_date_lv_header),
                (models.DateTimeField,  css_date_lv_header),
            ],
            default=css_default_header,
        )

    # TODO: rename register_printer
    def register(
            self,
            field: Type[models.Field],
            printer: FieldPrinter,
            output: str = 'html') -> '_FieldPrintersRegistry':
        """Register a field printer.
        @param field: A class inheriting <django.models.Field>.
        @param printer: A callable object. See simple_print_html() for arguments/return.
        @param output: string in {'html', 'csv'}.
        @return Self to chain calls.
        """
        self._printers_maps[output][field] = printer
        return self

    def register_choice_printer(
            self,
            printer: FieldPrinter,
            output: str = 'html') -> '_FieldPrintersRegistry':
        """Register a printer for fields with a "choices" attribute.
        @param printer: A callable object. See print_choice() for arguments/return.
        @param output: string in {'html', 'csv'}.
        @return Self to chain calls.
        """
        self._choice_printers[output] = printer
        return self

    def register_listview_css_class(
            self,
            field: Type[models.Field],
            css_class: str,
            header_css_class: str) -> '_FieldPrintersRegistry':
        """Register CSS classes used in list-views to display field's value and column header.
        @param field: A class inheriting <django.models.Field>.
        @param css_class: CSS class for table cell.
        @param header_css_class: CSS class for table header.
        @return Self to chain calls.
        """
        self._listview_css_printers[field] = css_class
        self._header_listview_css_printers[field] = header_css_class

        return self

    # NB: see EntityCell._get_listview_css_class()
    def get_listview_css_class_for_field(self, field_class: Type[models.Field]) -> str:
        return self._listview_css_printers[field_class]

    def get_header_listview_css_class_for_field(self, field_class: Type[models.Field]) -> str:
        return self._header_listview_css_printers[field_class]

    def _build_field_printer(
            self,
            field_info: FieldInfo,
            output: str = 'html') -> ReducedPrinter:
        base_field = field_info[0]
        base_name = base_field.name
        HIDDEN_VALUE = settings.HIDDEN_VALUE

        if len(field_info) > 1:
            base_model = base_field.remote_field.model
            sub_printer = self._build_field_printer(field_info[1:], output)

            if isinstance(base_field, models.ForeignKey):
                if issubclass(base_model, CremeEntity):
                    def printer(obj: Model, user):
                        base_value = getattr(obj, base_name)

                        if base_value is None:
                            return ''

                        if not user.has_perm_to_view(base_value):
                            return HIDDEN_VALUE

                        return sub_printer(base_value, user)
                else:
                    def printer(obj: Model, user):
                        base_value = getattr(obj, base_name)

                        if base_value is None:
                            return ''

                        return sub_printer(base_value, user)
            else:
                assert isinstance(base_field, models.ManyToManyField)

                if issubclass(base_model, CremeEntity):
                    def sub_values(obj, user):
                        has_perm = user.has_perm_to_view

                        for e in getattr(obj, base_name).filter(is_deleted=False):
                            if not has_perm(e):
                                yield HIDDEN_VALUE
                            else:
                                sub_value = sub_printer(e, user)
                                if sub_value:  # NB: avoid empty string
                                    yield sub_value

                    if output == 'csv':
                        def printer(obj: Model, user):
                            return '/'.join(sub_values(obj, user))
                    else:
                        def printer(obj: Model, user):
                            li_tags = format_html_join(
                                '', '<li>{}</li>', ((v,) for v in sub_values(obj, user))
                            )

                            return format_html('<ul>{}</ul>', li_tags) if li_tags else ''
                else:
                    def sub_values(obj, user):
                        for a in getattr(obj, base_name).all():
                            sub_value = sub_printer(a, user)
                            if sub_value:  # NB: avoid empty string
                                yield sub_value

                    if output == 'csv':
                        def printer(obj: Model, user):
                            return '/'.join(sub_values(obj, user))
                    else:
                        def printer(obj: Model, user):
                            li_tags = format_html_join(
                                '', '<li>{}</li>', ((v,) for v in sub_values(obj, user))
                            )

                            return format_html('<ul>{}</ul>', li_tags) if li_tags else ''
        else:
            print_func = (
                self._choice_printers[output]
                if base_field.choices else
                self._printers_maps[output][base_field.__class__]
            )

            def printer(obj, user):
                return print_func(obj, getattr(obj, base_name), user, base_field)

        return printer

    def build_field_printer(
            self,
            model: Type[models.Model],
            field_name: str,
            output: str = 'html') -> ReducedPrinter:
        return self._build_field_printer(FieldInfo(model, field_name), output=output)

    def get_html_field_value(
            self,
            obj: models.Model,
            field_name: str,
            user) -> str:
        return self.build_field_printer(obj.__class__, field_name)(obj, user)

    def get_csv_field_value(
            self,
            obj: models.Model,
            field_name: str,
            user) -> str:
        return self.build_field_printer(obj.__class__, field_name, output='csv')(obj, user)


field_printers_registry = _FieldPrintersRegistry()
