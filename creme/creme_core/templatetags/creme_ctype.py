# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2018  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.template import Library
from django.utils.translation import ugettext as _

from .. import get_concrete_model
from ..utils.translation import get_model_verbose_name

register = Library()


# TODO: {% ctype_for_model %} ?
# TODO: {% ctype_for_instance %} ?


# NB: not used, but here for API completeness
# @register.assignment_tag
@register.simple_tag
def ctype_for_naturalkey(app_label, model):
    """Returns a instance of ContentType for the natural key of a model.

    @param app_label: String identifying an app.
    @param model: String identifying a model.
    @return: A ContentType instance.

        {% ctype_for_naturalkey app_label='creme_core' model='currency' as currency_ctype %}
        <h1>List of {{currency_ctype}}</h1>
    """
    return ContentType.objects.get_by_natural_key(app_label=app_label, model=model)


# @register.assignment_tag
@register.simple_tag
def ctype_for_swappable(model_setting):
    """Returns a instance of ContentType for a swappable model.

    @param model_setting: String identifying a swappable model.
    @return: A ContentType instance.

        {% ctype_for_swappable 'PERSONS_CONTACT_MODEL' as contact_ctype %}
        <h1>List of {{contact_ctype}}</h1>
    """
    return ContentType.objects.get_for_model(get_concrete_model(model_setting))


# TODO: ?
# @register.assignment_tag(name='get_model_verbose_name')
# def get_model_vname(model, count):
#     return get_model_verbose_name(model, count)


# @register.assignment_tag
@register.simple_tag
def ctype_counted_instances_label(ctype, count):
    """ Return a localized string, in order to display label like '1 Contact' or '3 Organisations'.

    @param ctype: A ContentType instance relation to your model.
    @param count: An Integer representing the number of instances of "model".
    @return: A string.

        {% ctype_for_swappable 'PERSONS_CONTACT_MODEL' as contact_ctype %}
        {% ctype_counted_instances_label  ctype=contact_ctype count=12 as my_label %}
        <h1>{{my_label}}</h1>
    """
    return _(u'%(count)s %(model)s') % {
        'count': count,
        'model': get_model_verbose_name(model=ctype.model_class(), count=count),
    }


@register.filter
def ctype_can_be_merged(ctype):
    """Indicates if 2 instances of a specific model can be used by the merging view of Creme.

    @param ctype: A ContentType instance corresponding to your model
    @return: A boolean.

        {% if my_entity.entity_type|ctype_can_be_merged %}
            <span>Can be merged !!</span>
        {% endif %}
    """
    from ..gui.merge import merge_form_registry
    return merge_form_registry.get(ctype.model_class()) is not None


@register.filter
def ctype_can_be_mass_imported(ctype):
    """Indicates if some instances of a specific model can be created from a CSV/XLS/... file.

    @param ctype: A ContentType instance corresponding to your model
    @return: A boolean.

        {% if my_entity.entity_type|ctype_can_be_mass_imported %}
            <span>Can be imported !!</span>
        {% endif %}
    """
    from ..gui.mass_import import import_form_registry
    return import_form_registry.is_registered(ctype)
