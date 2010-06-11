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

from logging import warning

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


class _BlockContext(object):
    __slots__ = ('page', '_order_by')

    def __init__(self):
        self.page = 1
        self._order_by = ''

    def __repr__(self):
        return '<BlockContext: page=%s>' % self.page

    def get_order_by(self, order_by):
        _order_by = self._order_by

        if _order_by:
            return _order_by

        return order_by

    def set_attrs(self, page, order_by, modified):
        if self.page != page:
            modified = True
            self.page = page

        if self._order_by != order_by:
            modified = True
            self._order_by = order_by

        return modified


class Block(object):
    """ A block of informations, often related to a model.
    Blocks can be diplayed on a detailview (and so are related to a CremeEntity),
    but they can be optionnally be displayed on portals (related to an app's
    content types) and on the homepage (related to all the apps).

    It's represented by a table, paginated, that can be ordered by one of its
    column. Reloading after a change (page, order) can be made with ajax if
    the correct view is set : for this, each block has a unique id in a page.

    Optionnal methods (both must exist/not exist in the same time):
    def portal_display(self, context, ct_ids):
        return 'VOID BLOCK FOR PORTAL: %s' % self.verbose_name

    def home_display(self, context):
        return 'VOID BLOCK FOR HOME: %s' % self.verbose_name
    """
    id_ = None       #overload with an unicode object ; use generate_id()
    order_by = ''         #default order_by value ; '' means no order_by
    page_size = settings.BLOCK_SIZE  #number of items in the page
    verbose_name = 'BLOCK'    #used in the user configuration (see BlockConfigItem)
    template_name = 'OVERLOAD_ME.html' #used to render the block of course

    def __init__(self):
        self._template = None

    @staticmethod
    def generate_id(app_name, name): #### _generate_id ????
        return u'block_%s-%s' % (app_name, name)

    def detailview_display(self, context):
        """Overload this method to display a specific block (like Todo etc...) """
        return u'VOID BLOCK FOR DETAILVIEW: %s, %s' % ( self.id_, self.verbose_name )

    def detailview_ajax(self, request, entity_id=None, **kwargs):
        context = {'request': request}

        if entity_id:
            context['object'] = CremeEntity.objects.get(id=entity_id).get_real_entity()

        context.update(kwargs)

        return HttpResponse(JSONEncoder().encode([(self.id_, self.detailview_display(context))]), mimetype="text/javascript")

    def home_ajax(self, request):
        """Beware: home_display() must be implemented"""
        rendered = [(self.id_, self.home_display({'request': request}))]
        return HttpResponse(JSONEncoder().encode(rendered), mimetype="text/javascript")

    def portal_ajax(self, request, ct_ids):
        """Beware: portal_display() must be implemented"""
        ct_ids = str2list(ct_ids)
        rendered = [(self.id_, self.portal_display({'request': request}, ct_ids))]
        return HttpResponse(JSONEncoder().encode(rendered), mimetype="text/javascript")

    def _get_context(self, request, base_url, block_name):
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
            page_blockcontexts[block_name] = blockcontext = _BlockContext()

        return blockcontext, modified

    def _render(self, dictionary):
        self._template = self._template or get_template(self.template_name)
        return self._template.render(Context(dictionary))

    def get_block_template_context(self, context, queryset, update_url='', **extra_kwargs):
        """ Build the block template context.
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

        @param context Template context (contains 'request' etc...).
        @param queryset Set of objects to display in the block.
        """
        request = context['request']
        base_url = request.GET.get('base_url', request.path)
        block_name = self.id_ #rename ???
        block_context, modified = self._get_context(request, base_url, block_name)

        order_by = self.order_by
        if order_by:
            request_order_by = request.GET.get('%s_order' % block_name)
            if request_order_by is not None:
                order_by = request_order_by #TODO: test if order_by is valid (field name) ????
            else:
                order_by = block_context.get_order_by(order_by)

            queryset = queryset.order_by(order_by)

        page_index = request.GET.get('%s_page' % block_name)
        if page_index is not None:
            try:
                page_index = int(page_index)
            except ValueError, e:
                debug('Invalige page number for block %s: %s', block_name, page_index)
                page_index = 1
        else:
            page_index = block_context.page

        paginator = Paginator(queryset, self.page_size)

        try:
            page = paginator.page(page_index)
        except (EmptyPage, InvalidPage):
            page = paginator.page(paginator.num_pages)

        if block_context.set_attrs(page.number, order_by, modified):
            request.session.modified = True

        template_context = {
                'page':       page,
                'block_name': block_name,
                'order_by':   order_by,
                'base_url':   base_url,
                'object'  :   context.get('object'), #optionnal: only on detailview
                'update_url': update_url,
                'MEDIA_URL':  settings.MEDIA_URL,
               }
        template_context.update(extra_kwargs)

        return template_context


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

    def __iter__(self):
        return self._blocks.iteritems()


block_registry = _BlockRegistry()
