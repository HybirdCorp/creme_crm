# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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
from django.utils.translation import ugettext_lazy as _
from django.utils.simplejson import JSONEncoder
from django.contrib.contenttypes.models import ContentType

from creme_core.models import (CremeEntity, Relation, RelationType,
                               RelationBlockItem, InstanceBlockConfigItem, BlockState)


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
        """Overload me (see _PaginatedBlockContext, _QuerysetBlockContext)"""
        return False


class Block(object):
    """ A block of informations.
    Blocks can be displayed on (see creme_core.templatetags.creme_block):
        - a detailview (and so are related to a CremeEntity),
        - a portal (related to the content types of an app)
        - the homepage - ie the portal of creme_core (related to all the apps).

    A Block can be directly displayed on a page (this is the only solution for
    pages that are not a detailview, a portal or the home). But the better
    solution is to use the configuration system (see creme_core.models.blocks
    & creme_config).

    Reloading after a change (deleting, adding, updating, etc...) in the block
    can be done with ajax if the correct view is set : for this, each block has
    a unique id in a page.

    When you inherit the Block class, you have to define these optionnal methods
    to allow the different possibility of display:

    def detailview_display(self, context):
        return 'VOID BLOCK FOR DETAILVIEW: %s' % self.verbose_name

    def portal_display(self, context, ct_ids):
        return 'VOID BLOCK FOR PORTAL: %s' % self.verbose_name

    def home_display(self, context):
        return 'VOID BLOCK FOR HOME: %s' % self.verbose_name
    """
    id_           = None               #overload with an unicode object ; use generate_id()
    dependencies  = ()                 #list of the models on which the block depends (ie: generally the block displays these models)
    relation_type_deps = ()            #list of id of RelationType objects on which the block depends ; only used for Blocks which have 'Relation' in their dependencies
    verbose_name  = 'BLOCK'            #used in the user configuration (see BlockDetailviewLocation/BlockPortalLocation)
    template_name = 'OVERLOAD_ME.html' #used to render the block of course
    context_class = _BlockContext      #store the context in the session.
    configurable  = True               #True: the Block can be add/removed to detailview/portal by configuration (see creme_config)
    target_ctypes = ()                 #Tuple of CremeEntity classes that can have this type of block. Empty tuple means that all types are ok. eg: (Contact, Organisation)
    target_apps = ()                   #Tuple of name of the Apps that can have this Block on their portal. Empty tuple means that all Apps are ok. eg: ('persons',)

    @staticmethod
    def generate_id(app_name, name): #### _generate_id ????
        return u'block_%s-%s' % (app_name, name)

    def _render(self, template_context):
        return get_template(self.template_name).render(Context(template_context))

    def _simple_detailview_display(self, context):
        """Helper method to build a basic detailview_display() method for classes that inherit Block."""
        return self._render(self.get_block_template_context(context))

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
        Eg: '/tickets/ticket/21' for base url, ajax url could be '/creme_core/todo/reload/21/'.
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
        context['block_name'] = block_name
        context['state']      = BlocksManager.get(context).get_state(self.id_, context['user'])
        context.update(extra_kwargs)

        return context

    def get_block_template_context(self, context, update_url='', **extra_kwargs):
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


class SimpleBlock(Block):
     detailview_display = Block._simple_detailview_display


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


class SpecificRelationsBlock(QuerysetBlock):
    dependencies  = (Relation,) #NB: (Relation, CremeEntity) but useless
    order_by      = 'type'
    verbose_name  = _(u'Relations')
    template_name = 'creme_core/templatetags/block_specific_relations.html'

    def __init__(self, id_, relation_type_id):
        super(SpecificRelationsBlock, self).__init__()
        self.id_ = id_
        self.relation_type_deps = (relation_type_id,)

    @staticmethod
    def generate_id(app_name, name):
        return u'specificblock_%s-%s' % (app_name, name)

    @staticmethod
    def id_is_specific(id_):
        return id_.startswith(u'specificblock_')

    def detailview_display(self, context):
        entity = context['object']
        relation_type = RelationType.objects.get(pk=self.relation_type_deps[0])

        btc = self.get_block_template_context(context,
                                              entity.relations.filter(type=relation_type).select_related('type', 'object_entity'),
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.pk),
                                              relation_type=relation_type,
                                             )

        #NB: DB optimisation
        relations = btc['page'].object_list
        Relation.populate_real_object_entities(relations)
        CremeEntity.populate_credentials([r.object_entity.get_real_entity() for r in relations], context['user'])

        return self._render(btc)


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
        self._used_relationtypes = None
        self._state_cache = None

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
                dep_map[dep].append(block)

    def pop_group(self, group_name):
        return self._blocks_groups.pop(group_name)

    def get_remaining_groups(self):
        return self._blocks_groups.keys()

    def _get_dependencies_ids(self, block):
        self._dep_solving_mode = True

        dep_map = self._dependencies_map
        depblocks_ids = set()
        id_ = block.id_

        for dep in block.dependencies:
            for other_block in dep_map[dep]:
                if other_block.id_ == id_:
                    continue

                if dep == Relation:
                    if not set(block.relation_type_deps) & set(other_block.relation_type_deps):
                        continue

                depblocks_ids.add(other_block.id_)

        return depblocks_ids

    def get_dependencies_map(self):
        get_dep = self._get_dependencies_ids
        return dict((block.id_, get_dep(block)) for block in self._blocks)

    def block_is_registered(self, block):
        block_id = block.id_
        return any(b.id_ == block_id for b in self._blocks)

    def get_used_relationtypes_ids(self):
        if self._used_relationtypes is None:
            self._used_relationtypes = set(rt_id for block in self._dependencies_map[Relation] for rt_id in block.relation_type_deps)

        return self._used_relationtypes

    def set_used_relationtypes_ids(self, relationtypes_ids):
        """@param relation_type_deps Sequence of RelationType objects' ids"""
        self._used_relationtypes = set(relationtypes_ids)

    @staticmethod
    def get(context):
        return context[BlocksManager.var_name] #will raise exception if not created: OK

    def get_state(self, block_id, user):
        """Get the state for a block and fill a cache to avoid multiple requests"""
        _state_cache = self._state_cache
        if not _state_cache:
            _state_cache = self._state_cache = BlockState.get_for_block_ids([block.id_ for block in self._blocks], user)

        state = _state_cache.get(block_id)
        if state is None:
            state = self._state_cache[block_id] = BlockState.get_for_block_id(block_id, user)
            debug("State not set in cache for '%s'" % block_id)

        return state


class _BlockRegistry(object):
    """Use to retrieve a Block by its id.
    All Blocks should be registered in.
    """
    class RegistrationError(Exception):
        pass

    def __init__(self):
        self._blocks = {}
        self._object_blocks = {}

    def register(self, *blocks):
        setdefault = self._blocks.setdefault

        for block in blocks:
            if setdefault(block.id_, block) is not block:
                raise _BlockRegistry.RegistrationError("Duplicate block's id or block registered twice : %s" % block.id_)

    def register_4_model(self, model, block): #TODO: had an 'overload' arg ??
        ct = ContentType.objects.get_for_model(model)
        block.id_ = self._generate_modelblock_id(ct)

        if not block.dependencies:
            block.dependencies  = (model,)

        self._object_blocks[ct.id] = block

    def _generate_modelblock_id(self, ct):
        return u'modelblock_%s-%s' % (ct.app_label, ct.model)

    def _get_block(self, block_id): #TODO: if code with InstanceBlockConfigItem is remove, maybe remove this method too...
        block = self._blocks.get(block_id)

        if block is None:
            if InstanceBlockConfigItem.id_is_specific(block_id): #TODO: this code is duplicated (see get_blocks) + is it useful here ???
                try:
                    ibi = InstanceBlockConfigItem.objects.get(block_id=block_id)
                except InstanceBlockConfigItem.DoesNotExist:
                    return Block()
                path, klass = InstanceBlockConfigItem.get_import_path(block_id)

                try:
                    block_import = __import__(path, globals(), locals(), [klass], -1)
                except ImportError:
                    return Block()

                block_class = getattr(block_import, klass)
                block = block_class(block_id, ibi)
            else:
                warning('Block seems deprecated: %s', block_id)
                block = Block()

        return block

    def __getitem__(self, block_id):
        return self._blocks[block_id]

    def __iter__(self):
        return self._blocks.iteritems()

    def get_blocks(self, block_ids):
        """Blocks type can be SpecificRelationsBlock/InstanceBlockConfigItem: in this case,they are not really
        registered, but created on the fly"""
        specific_ids = filter(SpecificRelationsBlock.id_is_specific, block_ids)
        instance_ids = filter(InstanceBlockConfigItem.id_is_specific, block_ids)
        relation_blocks_items = dict((rbi.block_id, rbi) for rbi in RelationBlockItem.objects.filter(block_id__in=specific_ids)) if specific_ids else {}
        instance_blocks_items = dict((ibi.block_id, ibi) for ibi in InstanceBlockConfigItem.objects.filter(block_id__in=instance_ids)) if instance_ids else {}
        blocks = []

        for id_ in block_ids:
            rbi = relation_blocks_items.get(id_)
            ibi = instance_blocks_items.get(id_) #TODO: do only if needed....

            if rbi:
                #TODO: move in a method of RelationBlockItem
                block = SpecificRelationsBlock(rbi.block_id, rbi.relation_type_id)
            elif ibi:
                #TODO: use a cache ?? a registry like model blocks ??
                #TODO: move in a method of InstanceBlockConfigItem
                path, klass = InstanceBlockConfigItem.get_import_path(id_)

                try:
                    block_import = __import__(path, globals(), locals(), [klass], -1)
                except ImportError:
                    continue

                block_class = getattr(block_import, klass)
                block = block_class(id_, ibi)
            elif id_.startswith('modelblock_'): #TODO: constant ?
                block = self.get_block_4_object(ContentType.objects.get_by_natural_key(*id_[len('modelblock_'):].split('-')))
            else:
                block = self._get_block(id_)

            blocks.append(block)

        return blocks

    def get_block_4_object(self, obj_or_ct):
        """Return the Block that display fields for a CremeEntity"""
        ct = obj_or_ct if isinstance(obj_or_ct, ContentType) else ContentType.objects.get_for_model(obj_or_ct)
        block = self._object_blocks.get(ct.id)

        if not block:
            block = SimpleBlock()
            block.id_ = self._generate_modelblock_id(ct)
            block.dependencies = (ct.model_class(),)
            block.template_name = 'creme_core/templatetags/block_object.html'

            self._object_blocks[ct.id] = block

        return block

    def get_compatible_blocks(self, model=None):
        """Returns the list of registered blocks that are configurable and compatible with the given ContentType.
        @param model Constraint on a CremeEntity class ; means blocks must be compatible with all kind of CremeEntity
        """
        return (block for block in self._blocks.itervalues()
                        if block.configurable and \
                           hasattr(block, 'detailview_display') and \
                           (not block.target_ctypes or model in block.target_ctypes)
               )

    def get_compatible_portal_blocks(self, app_name):
        method_name = 'home_display' if app_name == 'creme_core' else 'portal_display'
        return (block for block in self._blocks.itervalues()
                     if block.configurable and \
                        hasattr(block, method_name) and \
                        (not block.target_apps or app_name in block.target_apps)
               )


block_registry = _BlockRegistry()
