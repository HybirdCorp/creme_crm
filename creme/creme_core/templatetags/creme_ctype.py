################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2025  Hybird
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
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.template import Library
from django.utils.translation import gettext as _

from .. import get_concrete_model
from ..models import utils
from ..utils.translation import smart_model_verbose_name

register = Library()


# TODO: {% if object|ctype_is:my_ctype %} ?


# @register.simple_tag
# def ctype_for_model(model: type[Model]) -> ContentType:
#     warnings.warn(
#         '{% ctype_for_model %} is deprecated; '
#         'use the filter "|ctype_for_instance" instead.',
#         DeprecationWarning
#     )
#     return ContentType.objects.get_for_model(model)


@register.filter
def ctype_for_instance(instance: Model) -> ContentType:
    """Returns an instance of ContentType for an instance of model.

    @param instance: Instance of <django.db.models.Model>.
    @return: A ContentType instance.

        <h1>Type: {{my_contact|ctype_for_instance}}</h1>

    Notice: remember that if you have a model in your context, the template
            engine of Django will automatically build an instance.
    """
    return ContentType.objects.get_for_model(type(instance))


@register.simple_tag
def ctype_for_naturalkey(app_label: str, model: str) -> ContentType:
    """Returns an instance of ContentType for the natural key of a model.

    @param app_label: String identifying an app.
    @param model: String identifying a model.
    @return: A ContentType instance.

        {% ctype_for_naturalkey app_label='creme_core' model='currency' as currency_ctype %}
        <h1>List of {{ currency_ctype }}</h1>
    """
    return ContentType.objects.get_by_natural_key(app_label=app_label, model=model)


# @register.simple_tag(name='ctype_for_swappable')
# def ctype_for_swappable__deprecated(model_setting: str) -> ContentType:
#     warnings.warn(
#         '{% ctype_for_swappable %} is deprecated; '
#         'use the filter "|ctype_for_swappable" instead.',
#         DeprecationWarning
#     )
#     return ContentType.objects.get_for_model(get_concrete_model(model_setting))


@register.filter
def ctype_for_swappable(model_setting: str) -> ContentType:
    """Returns an instance of ContentType for a swappable model.

    @param model_setting: String identifying a swappable model.
    @return: A ContentType instance.

        <h1>Fields of {{ 'PERSONS_CONTACT_MODEL'|ctype_for_swappable }}</h1>
    """
    return ContentType.objects.get_for_model(get_concrete_model(model_setting))


@register.filter
# def ctype_verbose_name(ctype: ContentType, count: int | None  = None) -> str:
def ctype_verbose_name(ctype: ContentType, count: int) -> str:
    model = ctype.model_class()

    # if count is None:
    #     warnings.warn(
    #         '|ctype_verbose_name without "count" argument is deprecated; '
    #         'you can just print the ContentType instance.',
    #         DeprecationWarning,
    #     )
    #     return utils.model_verbose_name(model)

    return smart_model_verbose_name(model, count)


@register.filter
def ctype_verbose_name_plural(ctype: ContentType) -> str:
    return utils.model_verbose_name_plural(ctype.model_class())


# @register.simple_tag
# def ctype_counted_instances_label(ctype: ContentType, count: int) -> str:
#     warnings.warn(
#         '{% ctype_counted_instances_label %} is deprecated; '
#         'use |ctype_counted_label instead.',
#         DeprecationWarning,
#     )
#
#     return _('{count} {model}').format(
#         count=count,
#         model=smart_model_verbose_name(model=ctype.model_class(), count=count),
#     )


@register.filter
def ctype_counted_label(ctype: ContentType, count: int) -> str:
    """ Return a localized string, in order to display label like '1 Contact' or '3 Organisations'.

    @param ctype: A ContentType instance relation to your model.
    @param count: An Integer representing the number of instances of "model".
    @return: A string.

        <h1>{{ 'PERSONS_CONTACT_MODEL'|ctype_for_swappable|ctype_counted_label:12 }}</h1>
    """
    return _('{count} {model}').format(
        count=count,
        model=smart_model_verbose_name(model=ctype.model_class(), count=count),
    )


@register.filter
def ctype_can_be_merged(ctype: ContentType) -> bool:
    """Indicates if 2 instances of a specific model can be used by the merging view of Creme.

    @param ctype: A ContentType instance corresponding to your model
    @return: A boolean.

        {% if my_entity.entity_type|ctype_can_be_merged %}
            <span>Can be merged !!</span>
        {% endif %}
    """
    from ..gui.merge import merge_form_registry

    return ctype.model_class() in merge_form_registry


# @register.filter
# def ctype_can_be_mass_imported(ctype: ContentType) -> bool:
#     """Indicates if some instances of a specific model can be created from a CSV/XLS/... file.
#
#     @param ctype: A ContentType instance corresponding to your model.
#     @return: A boolean.
#
#         {% if my_entity.entity_type|ctype_can_be_mass_imported %}
#             <span>Can be imported !!</span>
#         {% endif %}
#     """
#     from ..gui.mass_import import import_form_registry
#
#     warnings.warn(
#         'The template filter |ctype_can_be_mass_imported is deprecated',
#         DeprecationWarning,
#     )
#
#     return ctype.model_class() in import_form_registry


@register.filter
def ctype_has_quickform(ctype: ContentType) -> bool:
    from ..gui.quick_forms import quickform_registry
    return quickform_registry.get_form_class(ctype.model_class()) is not None
