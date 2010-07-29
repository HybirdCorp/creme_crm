# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from logging import warning, debug
from collections import defaultdict

from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.template.loader import get_template
from django.template import Context
from django.conf import settings
from django.http import HttpResponse
from django.utils.simplejson import JSONEncoder

from creme_core.models import CremeEntity


def list4url(list_):
    """Special url list-to-string function"""
    return ','.join(str(i) for i in list_)

def str2list(string):
    """
    '1,2,3'  -> [1, 2, 3]
    """
    return [int(i) for i in string.split(',') if i.isdigit()]


class _BlockContext(object): #TODO: rename to Context ?? (so Context-> TemplateContext)
    def __repr__(self):
        return '<BlockContext>'

    def update(self, modified, template_context):
        return False


class Block(object):
    """ A block of informations, often related to a model.
    Blocks can be diplayed on a detailview (and so are related to a CremeEntity),
    but they can be optionnally be displayed on portals (related to an app's
    content types) and on the homepage (related to all the apps).

    Reloading after a change (deleting, adding, updating, etc...) in the block
    can be done with ajax if the correct view is set : for this, each block has
    a unique id in a page.

    Optionnal methods (both must exist/not exist in the same time):
    def portal_display(self, context, ct_ids):
        return 'VOID BLOCK FOR PORTAL: %s' % self.verbose_name

    def home_display(self, context):
        return 'VOID BLOCK FOR HOME: %s' % self.verbose_name
    """
    id_           = None               #overload with an unicode object ; use generate_id()
    dependencies  = ()                 #list of the models on which the block depends (ie: generally the block displays these models)
    verbose_name  = 'BLOCK'            #used in the user configuration (see BlockConfigItem)
    template_name = 'OVERLOAD_ME.html' #used to render the block of course
    context_class = _BlockContext      #store the context in the session.
    configurable  = False              #True: the Block can be add/removed to detailview/portal by configuration (see creme_config)

    @staticmethod
    def generate_id(app_name, name): #### _generate_id ????
        return u'block_%s-%s' % (app_name, name)

    def __init__(self):
        self._template = None

    def _render(self, dictionary):
        if settings.DEBUG:
            self._template = get_template(self.template_name)
        else: #use a cache when debug is False
            self._template = self._template or get_template(self.template_name)

        return self._template.render(Context(dictionary))

    def detailview_display(self, context):
        """Overload this method to display a specific block (like Todo etc...) """
        return u'VOID BLOCK FOR DETAILVIEW: %s, %s' % (self.id_, self.verbose_name)

    def __get_context(self, request, base_url, block_name):
        """Retrieve block's context stored in the session.
        In the session (request.session), blocks are stored like this (with "blockcontexts_manager" as key):
            {
                'base_url_for_element_1': {
                    'id_for_block01': _BlockContext<>,
                    'id_for_block02': _BlockContext<>,
                    ...
                },
                'base_url_for_element_2': {...},
                ...
            }
        Base url are opposite to ajax_url.
        Eg: '/tickets/ticke/21' for base url, ajas url couild be '/creme_core/todo/reload/21/'.
        """
        modified = False
        session = request.session

        blockcontexts_manager = session.get('blockcontexts_manager')
        if blockcontexts_manager is None:
            modified = True
            session['blockcontexts_manager'] = blockcontexts_manager = {}

        page_blockcontexts = blockcontexts_manager.get(base_url)
        if page_blockcontexts is None:
            modified = True
            blockcontexts_manager[base_url] = page_blockcontexts = {}

        blockcontext = page_blockcontexts.get(block_name)
        if blockcontext is None:
            modified = True
            page_blockcontexts[block_name] = blockcontext = self.context_class()

        return blockcontext, modified

    def _build_template_context(self, context, block_name, block_context, **extra_kwargs):
        template_context = {
                'block_name': block_name,
                'object':     context.get('object'), #optionnal: only on detailview
                'MEDIA_URL':  settings.MEDIA_URL,
               }
        template_context.update(extra_kwargs)

        return template_context

    def get_block_template_context(self, context, update_url='', depblock_ids=(), **extra_kwargs):
        """ Build the block template context.
        @param context Template context (contains 'request' etc...).
        @param url String containing url to reload this block with ajax.
        """
        request = context['request']
        base_url = request.GET.get('base_url', request.path)
        block_name = self.id_
        block_context, modified = self.__get_context(request, base_url, block_name)

        template_context = self._build_template_context(context, block_name, block_context,
                                                        base_url=base_url,
                                                        update_url=update_url,
                                                        **extra_kwargs)

        #assert BlocksManager.get(context).block_is_registered(self) #!! problem with blocks in inner popups
        if not BlocksManager.get(context).block_is_registered(self):
            debug('Not registered block: %s', self.id_)

        if block_context.update(modified, template_context):
            request.session.modified = True

        return template_context


class _PaginatedBlockContext(_BlockContext):
    __slots__ = ('page',)

    def __init__(self):
        self.page = 1

    def __repr__(self):
        return '<PaginatedBlockContext: page=%s>' % self.page

    def update(self, modified, template_context):
        page = template_context['page'].number

        if self.page != page:
            modified = True
            self.page = page

        return modified


class PaginatedBlock(Block):
    """This king of Block is generally represented by a paginated table.
    Ajax changes management is used to chnage page.
    """
    context_class = _PaginatedBlockContext
    page_size     = settings.BLOCK_SIZE  #number of items in the page

    def _build_template_context(self, context, block_name, block_context, **extra_kwargs):
        request = context['request']
        objects = extra_kwargs.pop('objects')

        page_index = request.GET.get('%s_page' % block_name)
        if page_index is not None:
            try:
                page_index = int(page_index)
            except ValueError, e:
                debug('Invalid page number for block %s: %s', block_name, page_index)
                page_index = 1
        else:
            page_index = block_context.page

        paginator = Paginator(objects, self.page_size)

        try:
            page = paginator.page(page_index)
        except (EmptyPage, InvalidPage):
            page = paginator.page(paginator.num_pages)

        return super(PaginatedBlock, self)._build_template_context(context, block_name, block_context, page=page, **extra_kwargs)

    def get_block_template_context(self, context, objects, update_url='', **extra_kwargs):
        """@param objects Set of objects to display in the block."""
        return Block.get_block_template_context(self, context, update_url=update_url, objects=objects, **extra_kwargs)


class _QuerysetBlockContext(_PaginatedBlockContext):
    __slots__ = ('page', '_order_by')

    def __init__(self):
        super(_QuerysetBlockContext, self).__init__() #*args **kwargs ??
        self._order_by = ''

    def __repr__(self):
        return '<QuerysetBlockContext: page=%s order_by=%s>' % (self.page, self._order_by)

    def get_order_by(self, order_by):
        _order_by = self._order_by

        if _order_by:
            return _order_by

        return order_by

    def update(self, modified, template_context):
        modified = super(_QuerysetBlockContext, self).update(modified, template_context)
        order_by = template_context['order_by']

        if self._order_by != order_by:
            modified = True
            self._order_by = order_by

        return modified


class QuerysetBlock(PaginatedBlock):
    """In this block, displayed objects are stored in a queryset.
    It allows to order objects by one of its columns (which can change): order
    changes are done with ajax of course.
    """
    context_class = _QuerysetBlockContext
    order_by      = '' #default order_by value ; '' means no order_by

    def _build_template_context(self, context, block_name, block_context, **extra_kwargs):
        request = context['request']
        order_by = self.order_by

        if order_by:
            request_order_by = request.GET.get('%s_order' % block_name)

            if request_order_by is not None:
                order_by = request_order_by #TODO: test if order_by is valid (field name) ????
            else:
                order_by = block_context.get_order_by(order_by)

            extra_kwargs['objects'] = extra_kwargs['objects'].order_by(order_by)

        return super(QuerysetBlock, self)._build_template_context(context, block_name, block_context, order_by=order_by, **extra_kwargs)

    def get_block_template_context(self, context, queryset, update_url='', **extra_kwargs):
        """@param queryset Set of objects to display in the block."""
        return PaginatedBlock.get_block_template_context(self, context, objects=queryset, update_url=update_url, **extra_kwargs)


class BlocksManager(object):
    """Using to solve the blocks dependencies problem in a page.
    Blocks can depends on the same model : updating one block involves to update
    the blocks that depends on the same than it.
    """
    var_name = 'blocks_manager'

    class Error(Exception):
        pass

    def __init__(self):
        self._blocks = []
        self._dependencies_map = defaultdict(list)
        self._blocks_groups = defaultdict(list)
        self._dep_solving_mode = False

    def add_group(self, group_name, *blocks):
        if self._dep_solving_mode:
            raise BlocksManager.Error("Can't add block to manager after dependence resolution is done.")

        self._blocks.extend(blocks)

        group = self._blocks_groups[group_name]
        if group:
            raise BlocksManager.Error("This block's group name already exists: %s" % group_name)
        group.extend(blocks)

        dep_map = self._dependencies_map
        for block in blocks:
            for dep in block.dependencies:
                dep_map[dep].append(block.id_)

    def pop_group(self, group_name):
        return self._blocks_groups.pop(group_name)

    def get_remaining_groups(self):
        return self._blocks_groups.keys()

    def _get_dependencies_ids(self, block):
        self._dep_solving_mode = True

        dep_map = self._dependencies_map
        depblocks_ids = set(block_id for dep in block.dependencies for block_id in dep_map[dep])
        depblocks_ids.remove(block.id_)

        return depblocks_ids

    def get_dependencies_map(self):
        get_dep = self._get_dependencies_ids
        return dict((block.id_, get_dep(block)) for block in self._blocks)

    def block_is_registered(self, block):
        block_id = block.id_
        return any(b.id_ == block_id for b in self._blocks)

    @staticmethod
    def get(context):
        return context[BlocksManager.var_name] #will raise exception if not created: OK


class _BlockRegistry(object):
    def __init__(self):
        self._blocks = {}

    def register(self, block):
        blocks = self._blocks
        block_id = block.id_

        if blocks.has_key(block_id):
            warning("Duplicate block's id or block registered twice : %s", block_id) #exception instead ???

        blocks[block_id] = block

    def get_block(self, block_id):
        block = self._blocks.get(block_id)

        if block is None:
            warning('Block seems deprecated: %s', block_id)
            block = Block()

        return block

    def __getitem__(self, block_id):
        return self._blocks[block_id]

    def __iter__(self):
        return self._blocks.iteritems()


block_registry = _BlockRegistry()
