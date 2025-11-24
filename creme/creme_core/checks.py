################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2025  Hybird
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

from itertools import chain

from django.apps import apps
from django.conf import settings
from django.core.checks import Error
from django.core.checks import Tags as CoreTags
from django.core.checks import Warning, register
from django.db.utils import DatabaseError


class Tags:
    settings = 'settings'
    api_breaking = 'api_breaking'
    deprecation = 'deprecation'


def check_uninstalled_apps(**kwargs):
    """Check the badly uninstalled apps.
    BEWARE: it crashes if the ContentType table does not exist (first migration).
    """
    warnings = []

    if settings.TESTS_ON:
        return warnings

    try:
        app_labels = [
            *apps.get_model('contenttypes.ContentType')
                 .objects
                 .order_by('app_label')
                 .distinct()
                 .values_list('app_label', flat=True),
        ]
    except DatabaseError:
        pass
    else:
        for app_label in app_labels:
            try:
                apps.get_app_config(app_label)
            except LookupError:
                warnings.append(Warning(
                    'The app seems not been correctly uninstalled.',
                    hint=(
                        "If it's a Creme app, uninstall it with the "
                        'command "creme_uninstall" '
                        '(you must enable this app in your settings before).'
                    ),
                    obj=app_label,
                    id='creme.E003',
                ))

    return warnings


@register(CoreTags.models)
def check_entity_ordering(**kwargs):
    from .models import CremeEntity

    errors = []

    for model in apps.get_models():
        if not issubclass(model, CremeEntity):
            continue

        ordering = model._meta.ordering

        if not ordering or (len(ordering) == 1 and 'id' in ordering[0]):
            errors.append(Error(
                f'<{model.__name__}> should have a Meta.ordering '
                f'different from "id" like all CremeEntities',
                hint='Change the "ordering" attribute in the Meta class of your model.',
                obj=model._meta.app_label,
                id='creme.E005',
            ))

    return errors


# NB: E008
@register(CoreTags.models)
def check_real_entity_foreign_keys(**kwargs):
    from .models.fields import RealEntityForeignKey

    errors = []

    for model in apps.get_models():
        for field in vars(model).values():
            if isinstance(field, RealEntityForeignKey):
                errors.extend(field.check())

    return errors


@register(CoreTags.urls)
def check_swapped_urls(**kwargs):
    from django.urls import NoReverseMatch, reverse

    from creme.creme_core.conf.urls import swap_manager

    errors = []

    for group in swap_manager:
        for swapped in group.swapped():
            name = swapped.pattern.name

            try:
                reverse(viewname=name, args=swapped.check_args)
            except NoReverseMatch:
                errors.append(Error(
                    f'The URL "{name}" (args={swapped.verbose_args}) has been swapped '
                    f'from the app "{group.app_name}" but never defined.',
                    hint='Define this URL in the file "urls.py" of the module '
                         'which defines the concrete model.',
                    obj='creme.creme_core',
                    id='creme.E009',
                ))

    return errors


@register(CoreTags.models)
def check_file_field_maxlength(**kwargs):
    from django.db.models import FileField

    from .models import CremeModel, FileRef

    warnings = []
    max_length = FileRef._meta.get_field('filedata').max_length

    for model in apps.get_models():
        if not issubclass(model, CremeModel):
            continue

        for field in model._meta.get_fields():
            if not isinstance(field, FileField):
                continue

            if field.max_length > max_length:
                warnings.append(Warning(
                    f'The model <{model.__name__}> contains a FileField "{field.name}" '
                    f'with a max_length which is greater than {max_length}. '
                    f'So it is possible that the automatic creation of FileRef '
                    f'(when you delete an instance of <{model.__name__}>) fails.',
                    obj=model._meta.app_label,
                    id='creme.E010',
                ))

    return warnings


# TODO: deploy check instead?
#       https://docs.djangoproject.com/en/5.2/ref/django-admin/#cmdoption-check-deploy
@register(Tags.settings)
def check_site_domain(**kwargs):
    warnings = []
    domain = settings.SITE_DOMAIN

    if domain == 'http://mydomain':
        warnings.append(Warning(
            'The settings SITE_DOMAIN must be defined (you left the example value).',
            obj='settings.py',
            id='creme.E011',
        ))
    else:
        prefixes = ('http://', 'https://')
        if not domain.startswith(prefixes):
            warnings.append(Warning(
                f'The settings SITE_DOMAIN must start with {prefixes}.',
                obj='settings.py',
                id='creme.E011',
            ))

        # ---
        if domain.endswith('/'):
            warnings.append(Warning(
                'The settings SITE_DOMAIN must NOT end with "/".',
                obj='settings.py',
                id='creme.E011',
            ))

    return warnings


# We search for models which are referenced by CremeEntity, through
# ForeignKey/ManyToManyField, directly (depth==0, like <CremeEntity.user>) or
# indirectly (e.g. <CremeEntity.user__role> corresponds to depth==1)
# We use value 1 because currently EntityFilters/HeaderFilters use this depth.
PORTABLE_KEY_MAX_DEPTH = 1


@register(CoreTags.models)
def check_portable_keys(**kwargs):
    from django.db.models import ForeignKey, ManyToManyField

    from .core.field_tags import FieldTag
    from .models import CremeEntity, MinionModel

    warnings = []
    warned_models = set()

    def _check_model(model, depth):
        if not issubclass(model, CremeEntity):
            return

        if model.__name__.startswith('Fake'):  # Avoid messages in unit tests
            return

        for field in chain(model._meta.fields, model._meta.many_to_many):
            if (
                not isinstance(field, (ForeignKey, ManyToManyField))
                or not field.get_tag(FieldTag.VIEWABLE)
                or not field.get_tag(FieldTag.ENUMERABLE)
            ):
                continue

            related_model = field.remote_field.model
            if related_model in warned_models:
                continue

            if not hasattr(related_model, 'portable_key'):
                warnings.append(Warning(
                    f'The model {model} has a viewable ForeignKey to the '
                    f'model {related_model} which has no method "portable_key()" '
                    f'(see docstring of <CremeEntity.portable_key()>).',
                    hint=(
                        f'{related_model} could get a UUIDField, '
                        f'or even inherit <creme_core.models.MinionModel>.'
                    ),
                    obj='creme.creme_core',
                    id='creme.E012',  # TODO: "W" instead?
                ))
                warned_models.add(related_model)
            elif not hasattr(related_model._default_manager, 'get_by_portable_key'):
                warnings.append(Warning(
                    f'The model {related_model} has a property "portable_key" but '
                    f'its default manager has no method "get_by_portable_key()".',
                    obj='creme.creme_core',
                    id='creme.E012',  # TODO: "W" instead?
                    hint=(
                        'Your manager class should inherit <MinionManager>'
                        if issubclass(related_model, MinionModel) else
                        None
                    ),
                ))
                warned_models.add(related_model)

            if depth < PORTABLE_KEY_MAX_DEPTH:
                _check_model(model=related_model, depth=depth + 1)

    for model in apps.get_models():
        _check_model(model=model, depth=0)

    return warnings


@register(Tags.settings)
def check_last_entities(**kwargs):
    errors = []

    try:
        LAST_ENTITIES_SIZE = int(settings.LAST_ENTITIES_SIZE)
        LAST_ENTITIES_MENU_SIZE = int(settings.LAST_ENTITIES_MENU_SIZE)
    except ValueError:
        errors.append(Error(
            'The settings LAST_ENTITIES_SIZE & LAST_ENTITIES_MENU_SIZE must be integers.',
            obj='settings.py',
            id='creme.E013',
        ))
    else:
        if LAST_ENTITIES_MENU_SIZE < 1 or LAST_ENTITIES_SIZE < 1:
            errors.append(Error(
                'The settings LAST_ENTITIES_SIZE & LAST_ENTITIES_MENU_SIZE must be >= 1.',
                obj='settings.py',
                id='creme.E013',
            ))
        elif LAST_ENTITIES_MENU_SIZE > LAST_ENTITIES_SIZE:
            errors.append(Error(
                'The settings LAST_ENTITIES_MENU_SIZE must be small or equal than '
                'LAST_ENTITIES_SIZE.',
                obj='settings.py',
                id='creme.E013',
            ))

    return errors
