# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017  Hybird
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

from django.template import Library, TemplateSyntaxError, Node as TemplateNode
from django.utils.safestring import mark_safe

from ..core.entity_cell import EntityCellRegularField
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
            raise ValueError("{{% cell_4_regularfield %}}: the field seems invalid "
                             "(model={model}, field={field})".format(model=model, field=field_name)
                            )

        context[self.asvar_name] = cell
        return ''


class CTypeRFieldCellNode(RFieldCellNode):
    def __init__(self, ctype_var, **kwargs):
        super(CTypeRFieldCellNode, self).__init__(**kwargs)
        self.ctype_var = ctype_var

    def _build_model(self, context):
        return self.ctype_var.resolve(context).model_class()


class InstanceRFieldCellNode(RFieldCellNode):
    def __init__(self, instance_var, **kwargs):
        super(InstanceRFieldCellNode, self).__init__(**kwargs)
        self.instance_var = instance_var

    def _build_model(self, context):
        return self.instance_var.resolve(context).__class__


_RFIELD_CELL_NODES = {
    'ctype':    ('ctype_var',    CTypeRFieldCellNode),
    'instance': ('instance_var', InstanceRFieldCellNode),
}


@register.tag(name='cell_4_regularfield')
def do_cell_4_regularfield(parser, token):
    """ Get an instance of EntityCellRegularField for a given model & a given field.

    The model can be pass as:
     - an instance of ContentType (ctype=...).
     - an instance of this model (instance=...).

    The field is a string representing a 'chain' of fields; eg: 'book__author__name'.

    Examples:
        {% cell_4_regularfield ctype=my_ctype field='first_name' as fname_cell %}
        {% cell_4_regularfield instance=my_contact field="last_name" as lname_cell %}
    """
    bits = token.split_contents()
    if len(bits) != 5:
        raise TemplateSyntaxError("'%s' takes 2 arguments (ctype/instance=... & field=...), then 'as my_var'." % bits[0])

    if bits[3] != 'as':
        raise TemplateSyntaxError('Keyword "as" of "cell_4_regularfield" tag is missing.')

    # First argument --------------
    match = KWARG_RE.match(bits[1])
    if not match:
        raise TemplateSyntaxError('Malformed 1rst argument to "cell_4_regularfield" tag.')

    fa_name, fa_value = match.groups()
    try:
        first_arg_name, rf_cell_node_cls = _RFIELD_CELL_NODES[fa_name]
    except KeyError:
        raise TemplateSyntaxError('Invalid 1rst argument of "cell_4_regularfield" tag ; '
                                  'it must be in %s.' % _RFIELD_CELL_NODES.keys()
                                 )

    # Second argument -------------
    match = KWARG_RE.match(bits[2])
    if not match:
        raise TemplateSyntaxError('Malformed 2nd argument to "cell_4_regularfield" tag.')

    sa_name, sa_value = match.groups()
    if sa_name != 'field':
        raise TemplateSyntaxError('Invalid second argument of "cell_4_regularfield" tag ; it must be "field".')

    return rf_cell_node_cls(field_var=parser.compile_filter(sa_value),
                            asvar_name=bits[4],
                            **{first_arg_name: parser.compile_filter(fa_value)}
                           )


# {% cell_render %} ----------------------------------------------------------------------------------------------------
__RENDER_ARGS_MAP = {
    'cell':     'cell_var',
    'instance': 'instance_var',
    'user':     'user_var',
    'output':   'output_var',
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
        - cell: an EntityCell instance. Eg: it could be generated with {% cell_4_regularfield ... %}
        - instance: an instance of a model.
        - user: an instance of auth.get_user_model().

    C. The optional argument 'output' controls the type of output.
       Possible values: "html", "csv".
       Default value: "html".
    """
    bits = token.split_contents()
    if len(bits) < 4:
        raise TemplateSyntaxError("'%s' takes at least 3 arguments (cell, instance, user)" % bits[0])

    kwargs = {}

    bits = bits[1:]
    if len(bits) >= 2 and bits[-2] == 'as':
        kwargs['asvar_name'] = bits[-1]
        bits = bits[:-2]

    for bit in bits:
        match = KWARG_RE.match(bit)
        if not match:
            raise TemplateSyntaxError('Malformed arguments for "cell_render" tag: %s' % bit)

        name, value = match.groups()

        arg_name = __RENDER_ARGS_MAP.get(name)
        if arg_name is None:
            raise TemplateSyntaxError('Invalid argument name for "cell_render" tag: %s' % name)

        kwargs[arg_name] = parser.compile_filter(value)

    return CellRenderNode(**kwargs)


class CellRenderNode(TemplateNode):
    RENDER_METHODS = {
        'html': 'render_html',
        'csv':  'render_csv',
    }

    def __init__(self, cell_var, instance_var, user_var, output_var=None, asvar_name=None):
        self.cell_var = cell_var
        self.instance_var = instance_var
        self.user_var = user_var
        self.output_var = output_var

        self.asvar_name = asvar_name

    def _build_icon(self, context, theme, size_px, label, css_class):
        raise NotImplementedError

    def render(self, context):
        cell = self.cell_var.resolve(context)

        output_var = self.output_var
        output = 'html' if output_var is None else output_var.resolve(context)

        method_name = self.RENDER_METHODS.get(output)
        if method_name is None:
            raise ValueError('{%% cell_render %%}: invalid output "%s" (must be in ["html", "csv"])' % output)

        try:
            render = getattr(cell, method_name)(entity=self.instance_var.resolve(context),
                                                user=self.user_var.resolve(context),
                                               )
        except Exception:
            logger.exception('Error in {% cell_render %}')
            render = ''

        if self.asvar_name:
            context[self.asvar_name] = mark_safe(render)
            return ''
        else:
            return render
