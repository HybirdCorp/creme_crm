################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2024  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.template import Library
from django.utils.translation import gettext as _

from .. import get_concrete_model
from ..utils.translation import get_model_verbose_name

register = Library()


# TODO: {% ctype_for_instance %} ? (ctype_for_model already works for instances...)
# TODO: {% if object|ctype_is:my_ctype %} ?


@register.simple_tag
def ctype_for_model(model: type[Model]) -> ContentType:
    """Returns an instance of ContentType for a model.

    @param model: Class 'inheriting django.db.models.Model'.
    @return: A ContentType instance.

        {% ctype_for_model currency_model as currency_ctype %}
        <h1>List of {{currency_ctype}}</h1>
    """
    return ContentType.objects.get_for_model(model)


@register.simple_tag
def ctype_for_naturalkey(app_label: str, model: str) -> ContentType:
    """Returns an instance of ContentType for the natural key of a model.

    @param app_label: String identifying an app.
    @param model: String identifying a model.
    @return: A ContentType instance.

        {% ctype_for_naturalkey app_label='creme_core' model='currency' as currency_ctype %}
        <h1>List of {{currency_ctype}}</h1>
    """
    return ContentType.objects.get_by_natural_key(app_label=app_label, model=model)


@register.simple_tag
def ctype_for_swappable(model_setting: str) -> ContentType:
    """Returns an instance of ContentType for a swappable model.

    @param model_setting: String identifying a swappable model.
    @return: A ContentType instance.

        {% ctype_for_swappable 'PERSONS_CONTACT_MODEL' as contact_ctype %}
        <h1>List of {{contact_ctype}}</h1>
    """
    return ContentType.objects.get_for_model(get_concrete_model(model_setting))


# TODO: replace 'get_meta_value' (only used to retrieve verbose_name?)?
@register.filter
def ctype_verbose_name(ctype: ContentType, count: int | None  = None) -> str:
    model = ctype.model_class()
    return model._meta.verbose_name if count is None else get_model_verbose_name(model, count)


@register.simple_tag
def ctype_counted_instances_label(ctype: ContentType, count: int) -> str:
    """ Return a localized string, in order to display label like '1 Contact' or '3 Organisations'.

    @param ctype: A ContentType instance relation to your model.
    @param count: An Integer representing the number of instances of "model".
    @return: A string.

        {% ctype_for_swappable 'PERSONS_CONTACT_MODEL' as contact_ctype %}
        {% ctype_counted_instances_label ctype=contact_ctype count=12 as my_label %}
        <h1>{{my_label}}</h1>
    """
    return _('{count} {model}').format(
        count=count,
        model=get_model_verbose_name(model=ctype.model_class(), count=count),
    )


# TODO: what about the global registry ? take it from the context ?
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

    # return merge_form_registry.get(ctype.model_class()) is not None
    return ctype.model_class() in merge_form_registry


# TODO: what about the global registry ? take it from the context ?
@register.filter
def ctype_can_be_mass_imported(ctype: ContentType) -> bool:
    """Indicates if some instances of a specific model can be created from a CSV/XLS/... file.

    @param ctype: A ContentType instance corresponding to your model.
    @return: A boolean.

        {% if my_entity.entity_type|ctype_can_be_mass_imported %}
            <span>Can be imported !!</span>
        {% endif %}
    """
    from ..gui.mass_import import import_form_registry

    # return import_form_registry.is_registered(ctype)
    return ctype.model_class() in import_form_registry


# TODO: what about the global registry ? take it from the context ?
@register.filter
def ctype_has_quickform(ctype: ContentType) -> bool:
    from ..gui.quick_forms import quickforms_registry
    return quickforms_registry.get_form_class(ctype.model_class()) is not None
