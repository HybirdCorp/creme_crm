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

import logging

from django.template import Library
from django.template import Node as TemplateNode
from django.template import TemplateSyntaxError

from ..core.entity_cell import EntityCellRegularField
from ..gui.view_tag import ViewTag
from . import KWARG_RE

register = Library()
logger = logging.getLogger(__name__)


class RFieldCellNode(TemplateNode):
    def __init__(self, field_var, asvar_name):
        self.field_var  = field_var
        self.asvar_name = asvar_name

    def _build_model(self, context):
        raise NotImplementedError

    def render(self, context):
        model = self._build_model(context)
        field_name = self.field_var.resolve(context)
        cell = EntityCellRegularField.build(model=model, name=field_name)

        if cell is None:
            # TODO: in EntityCellRegularField.build ??
            raise ValueError(
                r'{% cell_4_regularfield %}: the field seems invalid '
                f'(model={model}, field="{field_name}")'
            )

        asvar_name = self.asvar_name

        if asvar_name is not None:
            context[asvar_name] = cell
            return ''

        return str(cell)


# TODO: merge with InstanceRFieldCellNode ? add some assertions ?
class ModelRFieldCellNode(RFieldCellNode):
    def __init__(self, model_var, **kwargs):
        super().__init__(**kwargs)
        self.model_var = model_var

    def _build_model(self, context):
        return self.model_var.resolve(context).__class__


class CTypeRFieldCellNode(RFieldCellNode):
    def __init__(self, ctype_var, **kwargs):
        super().__init__(**kwargs)
        self.ctype_var = ctype_var

    def _build_model(self, context):
        return self.ctype_var.resolve(context).model_class()


class InstanceRFieldCellNode(RFieldCellNode):
    def __init__(self, instance_var, **kwargs):
        super().__init__(**kwargs)
        self.instance_var = instance_var

    def _build_model(self, context):
        return self.instance_var.resolve(context).__class__


_RFIELD_CELL_NODES: dict[str, tuple[str, type[RFieldCellNode]]] = {
    'model':    ('model_var',    ModelRFieldCellNode),
    'ctype':    ('ctype_var',    CTypeRFieldCellNode),
    'instance': ('instance_var', InstanceRFieldCellNode),
}


@register.tag(name='cell_4_regularfield')
def do_cell_4_regularfield(parser, token):
    """ Get an instance of EntityCellRegularField for a given model & a given field.

    The model can be pass as:
     - a class (model=...).
     - an instance of ContentType (ctype=...).
     - an instance of this model (instance=...).

    The field is a string representing a 'chain' of fields, e.g. 'book__author__name'.

    Examples:
        {% cell_4_regularfield model=contact_cls field="phone" as phone_cell %}
        {% cell_4_regularfield ctype=my_ctype field='first_name' as fname_cell %}
        {% cell_4_regularfield instance=my_contact field="last_name" as lname_cell %}

    You are not obliged to assign a variable ; it's useful to print the verbose name of a field:
        {% cell_4_regularfield instance=my_contact field='first_name' %}
    """
    asvar_name = None
    bits = token.split_contents()
    length = len(bits)

    if length != 3:
        if length != 5:
            raise TemplateSyntaxError(
                f'"{bits[0]}" takes 2 arguments (ctype/instance=... & field=...), '
                f'& then optionally "as my_var".'
            )

        if bits[3] != 'as':
            raise TemplateSyntaxError(
                f'"{bits[0]}" tag expected a keyword "as" here, found "{bits[3]}".'
            )

        asvar_name = bits[4]

    # First argument --------------
    match = KWARG_RE.match(bits[1])
    if not match:
        raise TemplateSyntaxError(
            f'"cell_4_regularfield" tag has a malformed 1rst argument: <{bits[1]}>.'
        )

    fa_name, fa_value = match.groups()
    try:
        first_arg_name, rf_cell_node_cls = _RFIELD_CELL_NODES[fa_name]
    except KeyError as e:
        raise TemplateSyntaxError(
            f'"cell_4_regularfield" tag has an invalid 1rst argument; '
            f'it must be in {[*_RFIELD_CELL_NODES.keys()]}.'
        ) from e

    # Second argument -------------
    match = KWARG_RE.match(bits[2])
    if not match:
        raise TemplateSyntaxError(
            f'"cell_4_regularfield" tag a malformed 2nd argument: <{bits[2]}>.'
        )

    sa_name, sa_value = match.groups()
    if sa_name != 'field':
        raise TemplateSyntaxError(
            '"cell_4_regularfield" tag has an invalid 2nd argument; '
            'it must be "field".'
        )

    return rf_cell_node_cls(
        field_var=parser.compile_filter(sa_value),
        asvar_name=asvar_name,
        **{first_arg_name: parser.compile_filter(fa_value)}
    )


# {% cell_render %} ------------------------------------------------------------
__RENDER_ARGS_MAP = {
    'cell':     'cell_var',
    'instance': 'instance_var',
    'user':     'user_var',
    'tag':      'tag_var',
}


@register.tag(name='cell_render')
def do_render(parser, token):
    """ Render an EntityCell instance.

    A. The cell can be rendered immediately:
        {% cell_render cell=cell instance=helen user=user %}

    or be assigned to a context variable:
        {% cell_render cell=cell instance=helen user=user as cell_content %}
        {{cell_content}}

    B. Mandatory arguments (notice that the arguments must be pass with keyword-notation):
        - cell: an EntityCell instance.
          E.g. it could be generated with {% cell_4_regularfield ... %}
        - instance: an instance of a model.
        - user: an instance of auth.get_user_model().

    D. The optional argument 'tag' controls the type of ViewTag.
       Default value: ViewTag.HTML_DETAIL.
    """
    bits = token.split_contents()
    if len(bits) < 4:
        raise TemplateSyntaxError(
            f'"{bits[0]}" tag takes at least 3 arguments (cell, instance, user)'
        )

    kwargs = {}

    bits = bits[1:]
    if len(bits) >= 2 and bits[-2] == 'as':
        kwargs['asvar_name'] = bits[-1]
        bits = bits[:-2]

    for bit in bits:
        match = KWARG_RE.match(bit)
        if not match:
            raise TemplateSyntaxError(
                f'"cell_render" tag has a malformed arguments: <{bit}>.'
            )

        name, value = match.groups()

        arg_name = __RENDER_ARGS_MAP.get(name)
        if arg_name is None:
            raise TemplateSyntaxError(
                f'"cell_render" tag has an invalid argument name: <{name}>.'
            )

        kwargs[arg_name] = parser.compile_filter(value)

    return CellRenderNode(**kwargs)


class CellRenderNode(TemplateNode):
    def __init__(self, cell_var, instance_var, user_var,
                 tag_var=None, asvar_name=None,
                 ):
        self.cell_var = cell_var
        self.instance_var = instance_var
        self.user_var = user_var
        self.tag_var = tag_var

        self.asvar_name = asvar_name

    def _build_icon(self, context, theme, size_px, label, css_class):
        raise NotImplementedError

    def render(self, context):
        cell = self.cell_var.resolve(context)

        tag_var = self.tag_var
        tag = ViewTag.HTML_DETAIL if tag_var is None else tag_var.resolve(context)

        try:
            render = cell.render(
                entity=self.instance_var.resolve(context),
                user=self.user_var.resolve(context),
                tag=tag,
            )
        except Exception:
            logger.exception('Error in {% cell_render %}')
            render = ''

        if self.asvar_name:
            context[self.asvar_name] = render
            return ''
        else:
            return render


# Other ------------------------------------------------------------------------

@register.filter
def cell_is_sortable(cell, cell_sorter_registry):
    """Can we order_by() a Query from a cell with <creme_core.core.sorter.QuerySorter>.

    @param cell: Instance of EntityCell.
    @param cell_sorter_registry: Instance of <creme_core.core.sorter.CellSorterRegistry>.
    @return: Boolean.
    """
    return bool(cell_sorter_registry.get_field_name(cell))
