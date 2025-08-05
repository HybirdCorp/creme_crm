################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from __future__ import annotations

# import warnings
from collections.abc import Iterable
from functools import partial
from os.path import splitext
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Field, Manager, Model
from django.template.defaultfilters import filesizeformat, linebreaks
from django.urls import reverse
from django.utils.formats import date_format, get_format, number_format
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
from ..models import CremeEntity, CremeUser, EntityFilter, fields
from ..templatetags.creme_widgets import (
    widget_ctype_hyperlink,
    widget_entity_hyperlink,
    widget_urlize,
)
from ..utils import bool_as_html
from ..utils.collections import ClassKeyedMap
from ..utils.html import render_limited_list
from ..utils.meta import FieldInfo
from .view_tag import ViewTag

if TYPE_CHECKING:
    from typing import Any, Callable, Iterator

    # Only keyword arguments:
    #   - "instance"
    #   - "value" (value of the field for the 'instance' argument)
    #   - "user"
    #   - "field"
    FieldPrinter = Callable[[Model, Any, CremeUser, Field], str]

    # Only keyword arguments: "instance", "user", "field"
    NonePrinter = Callable[[Model, CremeUser, Field], str]

    # Positional arguments
    ReducedPrinter = Callable[[Model, CremeUser], str]

    # Only keyword arguments:
    #   - "instance"
    #   - "manager" (M2M value of the related instance)
    #   - "user"
    #   - "field"
    M2MEnumerator = Callable[[Model, Manager, CremeUser, Field], Iterator[Model]]

    # Only keyword arguments:
    #   - "instance" (the instance to print).
    #   - "related_instance" (the instance with the ManyToManyField -- so
    #     "instance" argument is one of the instances related to it)
    #   - "value" (M2M value of the related instance)
    #   - "user"
    #   - "field"
    M2MInstancePrinter = Callable[[Model, Model, Manager, CremeUser, Field], str]


def simple_print_html(*, instance: Model, value: Any, user, field: Field) -> str:
    return escape(value) if value is not None else ''


def simple_print_text(*, value, **kwargs) -> str:
    return str(value) if value is not None else ''


def print_choice(*, instance: Model, field: Field, **kwargs) -> str:
    choice = getattr(instance, f'get_{field.name}_display')()
    return str(choice) if choice is not None else ''


def print_color_html(*, value, **kwargs) -> str:
    return format_html(
        '''<span style="background:#{color};">{color}</span>''',
        color=value,
    ) if value else ''


class FileFieldPrinterForHTML:
    def __init__(self, registry: FileFieldDownLoadRegistry):
        self.registry = registry

    def __call__(self, *, instance: Model, value, user, field: Field) -> str:
        if value:
            fname = field.name
            registry = self.registry

            try:
                dl_filefield = registry.get(
                    user=user, instance=instance, field_name=fname,
                )
            except registry.InvalidField:
                return simple_print_html(
                    instance=instance, value=value, user=user, field=field,
                )

            ct_id = ContentType.objects.get_for_model(instance).id

            return self._render_download(
                url=reverse('creme_core__download', args=(ct_id, instance.id, fname)),
                dl_filefield=dl_filefield,
                instance=instance,
                user=user,
            )

        return ''

    @staticmethod
    def _render_download(*,
                         url: str,
                         dl_filefield: DownLoadableFileField,
                         instance: Model,
                         user: CremeUser,
                         ) -> str:
        file_name = dl_filefield.base_name
        ext = splitext(file_name)[1]

        if ext:
            ext = ext[1:]  # remove '.'

        if ext.lower() in settings.ALLOWED_IMAGES_EXTENSIONS:
            return format_html(
                """<a class="image-file" onclick="creme.dialogs.image('{url}').open();">"""
                """<img src="{url}" alt="{label}"/>"""
                """</a>""",
                url=url,
                label=_('Download «{file}»').format(file=file_name),
            )
        else:
            return format_html(
                '<a href="{url}">{label}</a>',
                url=url,
                label=_('Download «{file}»').format(file=file_name),
            )


print_file_html = print_image_html = FileFieldPrinterForHTML(registry=filefield_download_registry)


def print_integer_html(*, value, **kwargs) -> str:
    # NB: force grouping instead of <USE_THOUSAND_SEPARATOR = True> in settings
    #     to not impact CSV output, reports etc...
    return number_format(value, force_grouping=True) if value is not None else ''


def print_decimal_html(*, value, **kwargs) -> str:
    return number_format(value, force_grouping=True) if value is not None else ''


def print_decimal_text(*, value, **kwargs) -> str:
    return number_format(value) if value is not None else ''


def print_percent_html(*, value, **kwargs) -> str:
    # NB: force grouping instead of <USE_THOUSAND_SEPARATOR = True> in settings
    #     to not impact CSV output, reports etc...
    return format_html(
        '<span class="percent-value">{value}</span>&nbsp;<span class="percent-marker">%</span>',
        value=number_format(value, force_grouping=True),
    ) if value is not None else ''


def print_file_size_html(*, value, **kwargs) -> str:
    return filesizeformat(value) if value is not None else ''


def print_boolean_html(*, value, **kwargs) -> str:
    return bool_as_html(value) if value is not None else ''


def print_boolean_text(*, value, **kwargs) -> str:
    if value is None:
        return ''

    return _('Yes') if value else _('No')


def print_url_html(*, value, **kwargs) -> str:
    return format_html('<a href="{url}" target="_blank">{url}</a>', url=value) if value else ''


def print_unchecked_url_html(*, value, **kwargs) -> str:
    return format_html(
        '<a href="{href}" target="_blank">{url}</a>',
        url=value,
        href=value if '://' in value else f'//{value}',
    ) if value else ''


def print_datetime_html(*, value, **kwargs) -> str:
    return format_html(
        '<span class="datetime-field" title="{}">{}</span>',
        # No "precise" (with seconds/milliseconds) format in Django's ones; should be enough
        _('Seconds: {}').format(value.second),
        date_format(localtime(value), 'DATETIME_FORMAT'),
    ) if value else ''


def print_datetime_text(*, value, **kwargs) -> str:
    # CSV is often used for import/export of data ;
    # so we choose a format friendly for machines.
    return localtime(value).strftime(get_format('DATETIME_INPUT_FORMATS')[0]) if value else ''


def print_date_html(*, value, **kwargs) -> str:
    return date_format(value, 'DATE_FORMAT') if value else ''


def print_date_text(*, value, **kwargs) -> str:
    return value.strftime(get_format('DATE_INPUT_FORMATS')[0]) if value else ''


class FKPrinter:
    @staticmethod
    def print_fk_null_html(*, instance: Model, user: CremeUser, field: Field):
        null_label = field.get_null_label()
        return format_html('<em>{}</em>', null_label) if null_label else ''

    @staticmethod
    def print_fk_contenttype_html(*, instance: Model, value, user, field: Field) -> str:
        return widget_ctype_hyperlink(ctype=value, user=user)

    @staticmethod
    def print_fk_entity_html(*, instance: Model, value, user, field: Field,
                             target='_self',  # Extra field
                             ) -> str:
        # TODO: assert isinstance(instance, CremeEntity)?
        return widget_entity_hyperlink(value, user, target=target)

    @staticmethod
    def print_fk_entity_text(*, instance: Model, value: Any, user: CremeUser, field: Field) -> str:
        # TODO: assert isinstance(instance, CremeEntity)?
        # TODO: change allowed_str() ??

        return str(value) if user.has_perm_to_view(value) else settings.HIDDEN_VALUE

    @staticmethod
    def print_fk_efilter_html(*, instance: Model, value, user, field: Field) -> str:
        return format_html(
            '<div class="entity_filter-summary">'
            '<a href="{url}">{name}</a>'
            '<ul>{conditions}</ul>'
            '</div>',
            url=value.get_absolute_url(),
            name=value,
            conditions=format_html_join(
                '', '<li>{}</li>',
                ((vc,) for vc in value.get_verbose_conditions(user)),
            ),
        )

    @staticmethod
    def print_fk_colored_html(*, instance: Model, value, user, field: Field) -> str:
        """Printer for models with a 'color' field."""
        return format_html(
            '<div class="ui-creme-colored_status">'
            ' <div class="ui-creme-color_indicator" style="background-color:#{};"></div>'
            ' <span>{}</span>'
            '</div>',
            value.color,
            str(value),
        )

    def __init__(self,
                 none_printer: NonePrinter,
                 default_printer: FieldPrinter,
                 ):
        self.none_printer = none_printer
        self._sub_printers = ClassKeyedMap(default=default_printer)

    def __call__(self, *, instance: Model, value: Any, user: CremeUser, field: Field) -> str:
        if value is None:
            return self.none_printer(instance=instance, user=user, field=field)

        sub_printer = self._sub_printers[value.__class__]
        assert sub_printer is not None  # NB: default_printer is not None

        return sub_printer(instance=instance, value=value, user=user, field=field)

    def register(self, model: type[Model], printer: FieldPrinter) -> FKPrinter:
        self._sub_printers[model] = printer
        return self


class BaseM2MPrinter:
    @staticmethod
    def enumerator_all(*,
                       instance: Model,
                       manager: Manager,
                       user: CremeUser,
                       field: Field,
                       ) -> Iterator[Model]:
        # We use a cache; even if the M2M has not been prefetched,
        # calls after the first one will not perform queries.
        yield from instance.get_m2m_values(field.name)

    @staticmethod
    def enumerator_entity(*,
                          instance: Model,
                          manager: Manager,
                          user: CremeUser,
                          field: Field,
                          ) -> Iterator[Model]:
        # We use the M2M cache as above; we potentially retrieve deleted
        # entities too (not sure if we won't display them in the future anyway).
        entities = instance.get_m2m_values(field.name)
        for entity in entities:
            if not entity.is_deleted:
                yield entity
        # TODO? (OK in HTML, but in CSV?)
        # for entity in entities:
        #     if entity.is_deleted:
        #         yield entity

    def __init__(self,
                 default_printer: M2MInstancePrinter,
                 default_enumerator: M2MEnumerator,
                 ):
        self._sub_printers = ClassKeyedMap(default=(default_printer, default_enumerator))

    def __call__(self, *, instance: Model, value, user: CremeUser, field: Field) -> str:
        raise NotImplementedError

    def register(self,
                 model: type[Model],
                 printer: M2MInstancePrinter,
                 enumerator: M2MEnumerator,
                 ) -> BaseM2MPrinter:
        self._sub_printers[model] = (printer, enumerator)
        return self


class M2MPrinterForHTML(BaseM2MPrinter):
    @staticmethod
    def printer_simple(*, instance: Model, related_instance: Model,
                       value: Manager, user: CremeUser, field: Field,
                       ) -> str:
        return escape(instance)

    @staticmethod
    def printer_entity(*, instance: Model, related_instance: Model,
                       value: Manager, user: CremeUser, field: Field,
                       ) -> str:
        assert isinstance(instance, CremeEntity)

        return format_html(
            '<a target="_blank" href="{url}"{attrs}>{content}</a>',
            url=instance.get_absolute_url(),
            attrs=mark_safe(' class="is_deleted"' if instance.is_deleted else ''),
            content=instance.get_entity_summary(user),
        ) if user.has_perm_to_view(instance) else settings.HIDDEN_VALUE

    def __call__(self, *, instance: Model, value, user: CremeUser, field: Field) -> str:
        assert isinstance(value, Manager)

        print_enum = self._sub_printers[value.model]
        assert print_enum is not None  # NB: default value is not None

        printer, enumerator = print_enum
        common_args = {'user': user, 'field': field}
        return render_limited_list(
            items=[*enumerator(instance=instance, manager=value, **common_args)],
            limit=settings.CELL_SIZE,
            render_item=lambda e: printer(
                instance=e, related_instance=instance, value=value, **common_args,
            ),
        )


class M2MPrinterForText(BaseM2MPrinter):
    @staticmethod
    def printer_simple(*, instance: Model, related_instance: Model,
                       manager: Manager, user: CremeUser, field: Field,
                       ) -> str:
        return str(instance)

    @staticmethod
    def printer_entity(*, instance: Model, related_instance: Model,
                       manager: Manager, user: CremeUser, field: Field,
                       ) -> str:
        assert isinstance(instance, CremeEntity)

        # TODO: summary? [e.get_entity_m2m_summary(user)]
        return str(instance) if user.has_perm_to_view(instance) else settings.HIDDEN_VALUE

    def __call__(self, *, instance: Model, value: Any, user: CremeUser, field: Field) -> str:
        assert isinstance(value, Manager)

        print_enum = self._sub_printers[value.model]
        assert print_enum is not None  # NB: default value is not None

        printer, enumerator = print_enum
        common_args = {'manager': value, 'user': user, 'field': field}

        return '/'.join(
            printer(instance=e, related_instance=instance, **common_args)
            for e in enumerator(instance=instance, **common_args)
        )


def print_duration(*, value, **kwargs) -> str:
    try:
        h, m, s = value.split(':')
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


def print_email_html(*, value, **kwargs) -> str:
    return format_html(
        '<a href="mailto:{email}">{email}</a>',
        email=value,
    ) if value else ''


def print_text_html(*, value, **kwargs) -> str:
    return mark_safe(linebreaks(widget_urlize(value))) if value else ''


def print_unsafehtml_html(*, value, **kwargs) -> str:
    return linebreaks(value, autoescape=True) if value else ''


# TODO: Do more specific fields (i.e: currency field....) ?
class FieldPrinterRegistry:
    class _Printers:
        def __init__(self, printers_for_field_types, default_printer, choice_printer, m2m_joiner):
            self._for_field_types = ClassKeyedMap(
                printers_for_field_types, default=default_printer,
            )
            self._for_fields = {}
            self._for_choice = choice_printer
            self._m2m_joiner = m2m_joiner

        def register_model_field_type(self, type: type[models.Field], printer: FieldPrinter):
            self._for_field_types[type] = printer

        def register_model_field(self, field: models.Field, printer: FieldPrinter):
            self._for_fields[field] = printer

        def register_choice(self, printer: FieldPrinter):
            self._for_choice = printer

        def build_field_printer(self, field_info: FieldInfo) -> ReducedPrinter:
            base_field = field_info[0]
            base_name = base_field.name
            HIDDEN_VALUE = settings.HIDDEN_VALUE

            if len(field_info) > 1:
                base_model = base_field.remote_field.model
                sub_printer = self.build_field_printer(field_info=field_info[1:])

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
                    else:
                        def sub_values(obj, user):
                            for a in getattr(obj, base_name).all():
                                sub_value = sub_printer(a, user)
                                if sub_value:  # NB: avoid empty string
                                    yield sub_value

                    def printer(obj: Model, user):
                        return self._m2m_joiner(sub_values(obj, user))
            else:
                print_func = self._for_fields.get(base_field) or (
                    self._for_choice
                    if base_field.choices else
                    self._for_field_types[base_field.__class__]
                )

                def printer(obj, user):
                    return print_func(
                        instance=obj, value=getattr(obj, base_name), user=user,
                        field=base_field,
                    )

            return printer

    def __init__(self):
        html_printers = [
            (models.IntegerField,       print_integer_html),

            (models.FloatField,         print_decimal_html),
            (models.DecimalField,       print_decimal_html),

            (models.BooleanField,       print_boolean_html),
            (models.NullBooleanField,   print_boolean_html),

            (models.DateField,          print_date_html),
            (models.DateTimeField,      print_datetime_html),

            (models.TextField,          print_text_html),
            (models.EmailField,         print_email_html),
            (models.URLField,           print_url_html),
            (fields.CremeURLField,      print_unchecked_url_html),

            (models.FileField,          print_file_html),
            (models.ImageField,         print_image_html),

            (fields.DurationField,      print_duration),
            (fields.DatePeriodField,    simple_print_html),  # TODO: JSONField ?

            (fields.IntegerPercentField, print_percent_html),
            (fields.DecimalPercentField, print_percent_html),
            (fields.FileSizeField,       print_file_size_html),
            (fields.ColorField,          print_color_html),

            (fields.UnsafeHTMLField,    print_unsafehtml_html),
        ]

        # TODO: make this public?
        def text_joiner(rendered_fields: Iterable[str]):
            return '/'.join(rendered_fields)

        def html_joiner(rendered_fields: Iterable[str]):
            return render_limited_list(items=[*rendered_fields], limit=settings.CELL_SIZE)

        def build_html_fk_printer(target=None):
            return FKPrinter(
                none_printer=FKPrinter.print_fk_null_html,
                default_printer=simple_print_html,
            ).register(
                model=CremeEntity,
                printer=(
                    FKPrinter.print_fk_entity_html
                    if target is None else
                    partial(FKPrinter.print_fk_entity_html, target=target)
                ),
            ).register(
                model=ContentType, printer=FKPrinter.print_fk_contenttype_html,
            ).register(
                model=EntityFilter, printer=FKPrinter.print_fk_efilter_html,
            )

        def build_text_fk_printer():
            return FKPrinter(
                none_printer=lambda *args, **kwargs: '',
                default_printer=simple_print_text,
            ).register(
                model=CremeEntity,
                printer=FKPrinter.print_fk_entity_text,
            )

        def build_html_m2m_printer():
            return M2MPrinterForHTML(
                default_printer=M2MPrinterForHTML.printer_simple,
                default_enumerator=M2MPrinterForHTML.enumerator_all,
            ).register(
                CremeEntity,
                printer=M2MPrinterForHTML.printer_entity,
                enumerator=M2MPrinterForHTML.enumerator_entity,
            )

        self._printers = {
            ViewTag.HTML_DETAIL: self._Printers(
                printers_for_field_types=[
                    *html_printers,
                    (models.ForeignKey,      build_html_fk_printer()),
                    (models.OneToOneField,   build_html_fk_printer()),
                    (models.ManyToManyField, build_html_m2m_printer()),
                ],
                default_printer=simple_print_html,
                choice_printer=print_choice,
                m2m_joiner=html_joiner,
            ),
            ViewTag.HTML_LIST: self._Printers(
                printers_for_field_types=[
                    *html_printers,
                    (models.ForeignKey,      build_html_fk_printer()),
                    (models.OneToOneField,   build_html_fk_printer()),
                    (models.ManyToManyField, build_html_m2m_printer()),
                ],
                default_printer=simple_print_html,
                choice_printer=print_choice,
                m2m_joiner=html_joiner,
            ),
            ViewTag.HTML_FORM: self._Printers(
                printers_for_field_types=[
                    *html_printers,
                    (models.ForeignKey,      build_html_fk_printer(target='_blank')),
                    (models.OneToOneField,   build_html_fk_printer(target='_blank')),
                    (models.ManyToManyField, build_html_m2m_printer()),
                ],
                default_printer=simple_print_html,
                choice_printer=print_choice,
                m2m_joiner=html_joiner,
            ),
            ViewTag.TEXT_PLAIN: self._Printers(
                printers_for_field_types=[
                    (models.FloatField,         print_decimal_text),
                    (models.DecimalField,       print_decimal_text),

                    (models.BooleanField,       print_boolean_text),
                    (models.NullBooleanField,   print_boolean_text),

                    (models.DateField,          print_date_text),
                    (models.DateTimeField,      print_datetime_text),

                    # (models.ImageField,         print_image_text, TODO?

                    (models.ForeignKey,         build_text_fk_printer()),
                    (models.OneToOneField,      build_text_fk_printer()),
                    (
                        models.ManyToManyField,
                        M2MPrinterForText(
                            default_printer=M2MPrinterForText.printer_simple,
                            default_enumerator=M2MPrinterForText.enumerator_all,
                        ).register(
                            CremeEntity,
                            printer=M2MPrinterForText.printer_entity,
                            enumerator=M2MPrinterForText.enumerator_entity,
                        )
                    ),

                    (fields.DurationField,      print_duration),
                ],
                default_printer=simple_print_text,
                choice_printer=print_choice,
                m2m_joiner=text_joiner,
            ),
        }

        # TODO: move these list-view values in another registry dedicated to list-views?
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

    def register_model_field_type(self, *,
                                  type: type[models.Field],
                                  printer: FieldPrinter,
                                  tags: ViewTag | Iterable[ViewTag] | str,
                                  ) -> FieldPrinterRegistry:
        """Register a printer for a class of model-field.
        @param field: A class inheriting <django.models.Field>.
        @param printer: A callable object. See simple_print_html() for arguments/return.
        @param tags: see <ViewTag.smart_generator()> for valid values.
        @return Self to chain calls.
        """
        for tag in ViewTag.smart_generator(tags):
            self._printers[tag].register_model_field_type(type=type, printer=printer)

        return self

    def register_model_field(self, *,
                             model: type[models.Model],
                             field_name: str,
                             printer: FieldPrinter,
                             tags: ViewTag | Iterable[ViewTag] | str,
                             ) -> FieldPrinterRegistry:
        """Register a printer for a specific model-field <MyModel.my_field>.
        @param model: A class inheriting <django.models.Model>.
        @param field_name: The name of a valid field of "model".
        @param printer: A callable object. See simple_print_html() for arguments/return.
        @param tags: see <ViewTag.smart_generator()> for valid values.
        @return Self to chain calls.
        """
        for tag in ViewTag.smart_generator(tags):
            self._printers[tag].register_model_field(
                field=model._meta.get_field(field_name),
                printer=printer,
            )

        return self

    def register_choice_printer(self,
                                printer: FieldPrinter,
                                tags: ViewTag | Iterable[ViewTag] | str,
                                ) -> FieldPrinterRegistry:
        """Register a printer for fields with a "choices" attribute.
        Notice that a field-with-a-choices-attribute which has a registered
        specific printer (see register_model_field()) will be renderer with
        its specific printer and not the choice-printer.
        @param printer: A callable object. See print_choice() for arguments/return.
        @param tags: see <ViewTag.smart_generator()> for valid values.
        @return Self to chain calls.
        """
        for tag in ViewTag.smart_generator(tags):
            self._printers[tag].register_choice(printer)

        return self

    def register_listview_css_class(self,
                                    field: type[models.Field],
                                    css_class: str,
                                    header_css_class: str,
                                    ) -> FieldPrinterRegistry:
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
    def get_listview_css_class_for_field(self, field_class: type[models.Field]) -> str:
        return self._listview_css_printers[field_class]

    def get_header_listview_css_class_for_field(self, field_class: type[models.Field]) -> str:
        return self._header_listview_css_printers[field_class]

    def build_field_printer(self,
                            model: type[models.Model],
                            field_name: str,
                            tag: ViewTag = ViewTag.HTML_DETAIL,
                            ) -> ReducedPrinter:
        return self._printers[tag].build_field_printer(
            field_info=FieldInfo(model, field_name),
        )

    def get_field_value(self, *,
                        instance: models.Model,
                        field_name: str,
                        user: CremeUser,
                        tag: ViewTag = ViewTag.TEXT_PLAIN,
                        ) -> str:
        return self.build_field_printer(
            model=instance.__class__, field_name=field_name, tag=tag,
        )(instance, user)

    def printers_for_field_type(self,
                                type: type[Field],
                                tags: ViewTag | Iterable[ViewTag] | str,
                                ) -> Iterator[FieldPrinter]:
        """Return all the raw printers used for a field type & for some tags
        Hint: most of the printers are immutable functions, so it's mainly
              useful for ForeignKey/ManyToManyField because the related printers
              are sub-registries (see FKPrinter etc...) & you can customize
              the sub-printers (in a method 'register_field_printers()' of your
              apps.py).
        """
        for tag in ViewTag.smart_generator(tags):
            # TODO: method in _Printers?
            yield self._printers[tag]._for_field_types[type]


field_printer_registry = FieldPrinterRegistry()


# def __getattr__(name):
#     if name == '_FieldPrintersRegistry':
#         warnings.warn(
#             '"_FieldPrintersRegistry" is deprecated; use "FieldPrinterRegistry" instead.',
#             DeprecationWarning,
#         )
#         return FieldPrinterRegistry
#
#     if name == 'field_printers_registry':
#         warnings.warn(
#             '"field_printers_registry" is deprecated; use "field_printer_registry" instead.',
#             DeprecationWarning,
#         )
#         return field_printer_registry
#
#     raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
