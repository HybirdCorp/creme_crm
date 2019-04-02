# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from collections import defaultdict
import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.db.models import Model
from django.template.loader import get_template
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _, ugettext

from ..constants import MODELBRICK_ID
from ..core.entity_cell import EntityCellRegularField
from ..core.sorter import cell_sorter_registry
from ..models import (Relation, RelationBrickItem, CremeEntity,
        InstanceBrickConfigItem, CustomBrickConfigItem, BrickState)
from ..utils.meta import OrderedField

logger = logging.getLogger(__name__)


class _BrickContext:
    def __repr__(self):
        return '<BrickContext>'

    def as_dict(self):
        return {}

    @classmethod
    def from_dict(cls, data):
        instance = cls()

        for k, v in data.items():
            setattr(instance, k, v)

        return instance

    def update(self, template_context):
        """Overload me (see _PaginatedBrickContext, _QuerysetBrickContext)."""
        return False


class Brick:
    """ A block of information.

    (NB: we use now the term 'brick' internally -- but 'block' in the GUI,
         in order to avoid the confusion with the {% block %} templatetag)

    Bricks can be displayed on (see creme_core.templatetags.creme_bricks):
        - a detail-view (and so are related to a CremeEntity).
        - the homepage - ie the portal of creme_core (related to all the apps).

    A Brick can be directly displayed on a page (this is the only solution for
    pages that are not a detail-view, a portal or the home). But the better
    solution is to use the configuration system (see creme_core.models.bricks
    & creme_config).

    Reloading after a change (deleting, adding, updating, etc...) in the brick
    can be done with ajax if the correct view is set : for this, each brick has
    a unique id in a page.

    When you inherit the Brick class, you have to define these optional methods
    to allow the different possibility of display:

    def detailview_display(self, context):
        return 'VOID BLOCK FOR DETAILVIEW: %s' % self.verbose_name

    def home_display(self, context):
        return 'VOID BLOCK FOR HOME: %s' % self.verbose_name
    """
    # The ID of a brick (string) is used to retrieve the class of a Brick, and build the corresponding instance when:
    #   - the configuration (detail-view/home/portal) is loaded (page creation).
    #   - some bricks are reloaded.
    # For regular brick classes, you just have to override this attribute by using the method generate_id().
    id_ = None

    # List of the models on which the brick depends (ie: generally the brick displays instances of these models) ;
    # it also can be the '*' string, which is a wildcard meaning 'All models used in the page'.
    dependencies = ()

    # List of id of RelationType objects on which the block depends ;
    # only used for Bricks which have the model 'Relation' in their dependencies.
    relation_type_deps = ()

    # 'True' means that the brick will never be used to change the instances of its dependencies models.
    # (ie: the brick is only used to display these instances ; there is no inner-popup to create/edit/delete/...)
    #   ---> so when this brick is reloaded (eg: to change the pagination), it does not causes the dependant bricks
    #  to be reloaded (but it is still reloaded when the dependant bricks are reloaded of course).
    read_only = False

    template_name = 'OVERLOAD_ME.html'  # Used to render the brick of course
    context_class = _BrickContext  # Class of the instance which stores the context in the session.

    # ATTRIBUTES USED BY THE CONFIGURATION GUI FOR THE BRICKS (ie: in creme_config) ------------------------------------
    # True means that the Brick appears in the configuration IHM (ie: it appears on classical detail-views/portals)
    configurable = True

    # Name used in the configuration GUI (so you should override it, excepted if <configurable = False>).
    verbose_name = 'BLOCK'

    # Sequence of classes inheriting CremeEntity which can have this type of brick on their detail-views.
    # An empty sequence means that all types are OK.
    # Example of value: target_ctypes = (Contact, Organisation)  # Available for detail-views of Contact & Organisation
    target_ctypes = ()
    # ATTRIBUTES USED BY THE CONFIGURATION GUI FOR THE BRICKS [END] ----------------------------------------------------

    GENERIC_HAT_BRICK_ID = 'hatbrick'

    def __init__(self):
        self._reloading_info = None

    @property
    def reloading_info(self):
        return self._reloading_info

    @reloading_info.setter
    def reloading_info(self, info):
        """Setter for reloading info.
        @param info: data which will be sent at reload. Must be serializable to JSON.
        """
        self._reloading_info = info

    @staticmethod
    def generate_id(app_name, name):  # TODO: rename _generate_id ?
        return 'block_{}-{}'.format(app_name, name)

    @classmethod
    def _generate_hat_id(cls, app_name, name):
        return '{}-{}-{}'.format(cls.GENERIC_HAT_BRICK_ID, app_name, name)

    def _render(self, template_context):
        return get_template(self.template_name).render(template_context)

    def _simple_detailview_display(self, context):
        """Helper method to build a basic detailview_display() method for classes that inherit Brick."""
        return self._render(self.get_template_context(context))

    def _iter_dependencies_info(self):
        for dep in self.dependencies:
            if isinstance(dep, type) and issubclass(dep, Model):
                if dep == Relation:
                    for rtype_id in self.relation_type_deps:
                        yield 'creme_core.relation.' + rtype_id
                else:
                    meta = dep._meta
                    yield '{}.{}'.format(meta.app_label, meta.model_name)
            else:
                yield str(dep)

    def _build_template_context(self, context, brick_id, brick_context, **extra_kwargs):
        context['brick_id'] = brick_id
        context['state'] = BricksManager.get(context).get_state(self.id_, context['user'])
        context['dependencies'] = list(self._iter_dependencies_info())
        context['reloading_info'] = self._reloading_info
        context['read_only'] = self.read_only

        context.update(extra_kwargs)

        return context

    def get_template_context(self, context, **extra_kwargs):
        """ Build the brick template context.
        @param context: Template context (contains 'request' etc...).
        """
        brick_id = self.id_
        request = context['request']
        base_url = request.GET.get('base_url', request.path)
        session = request.session

        try:
            serialized_context = session['brickcontexts_manager'][base_url][brick_id]
        except KeyError:
            brick_context = self.context_class()
        else:
            brick_context = self.context_class.from_dict(serialized_context)

        template_context = self._build_template_context(context, brick_id, brick_context,
                                                        **extra_kwargs
                                                       )

        # NB:  not 'assert' (it causes problems with bricks in inner popups)
        if not BricksManager.get(context).brick_is_registered(self):
            logger.debug('Not registered brick: %s', self.id_)

        if brick_context.update(template_context):
            session.setdefault('brickcontexts_manager', {}) \
                   .setdefault(base_url, {}) \
                   [brick_id] = brick_context.as_dict()

            request.session.modified = True

        return template_context


class SimpleBrick(Brick):
     detailview_display = Brick._simple_detailview_display


class _PaginatedBrickContext(_BrickContext):
    __slots__ = ('page',)

    def __init__(self):
        self.page = 1

    def __repr__(self):
        return '<PaginatedBrickContext: page={}>'.format(self.page)

    def as_dict(self):
        return {'page': self.page}

    def update(self, template_context):
        page = template_context['page'].number

        if self.page != page:
            modified = True
            self.page = page
        else:
            modified = False

        return modified


class PaginatedBrick(Brick):
    """This king of Brick is generally represented by a paginated table.
    Ajax changes management is used to change page.
    """
    context_class = _PaginatedBrickContext
    page_size     = settings.BLOCK_SIZE  # Number of items in the page

    def _build_template_context(self, context, brick_id, brick_context, **extra_kwargs):
        request = context['request']
        objects = extra_kwargs.pop('objects')

        page_index = request.GET.get('{}_page'.format(brick_id))
        if page_index is not None:
            try:
                page_index = int(page_index)
            except ValueError:
                logger.warning('PaginatedBrick: invalid page number for brick %s: %s', brick_id, page_index)
                page_index = 1
        else:
            page_index = brick_context.page

        paginator = Paginator(objects, self.page_size)

        try:
            page = paginator.page(page_index)
        except (EmptyPage, InvalidPage):
            page = paginator.page(paginator.num_pages)

        return super()._build_template_context(
                context=context, brick_id=brick_id, brick_context=brick_context, page=page,
                **extra_kwargs
        )

    def get_template_context(self, context, objects, **extra_kwargs):
        """@param objects: Sequence of objects to display in the brick."""
        return Brick.get_template_context(self, context, objects=objects, **extra_kwargs)


class _QuerysetBrickContext(_PaginatedBrickContext):
    __slots__ = ('page', '_order_by')

    def __init__(self):
        super().__init__()  # *args **kwargs ??
        self._order_by = ''

    def __repr__(self):
        return '<QuerysetBrickContext: page={} order_by={}>'.format(self.page, self._order_by)

    def as_dict(self):
        d = super().as_dict()
        d['_order_by'] = self._order_by

        return d

    def get_order_by(self, order_by):
        _order_by = self._order_by

        if _order_by:
            return _order_by

        return order_by

    def update(self, template_context):
        modified = super().update(template_context)
        order_by = template_context['order_by']

        if self._order_by != order_by:
            modified = True
            self._order_by = order_by

        return modified


class QuerysetBrick(PaginatedBrick):
    """In this brick, displayed objects are stored in a queryset.
    It allows to order objects by one of its columns (which can change): order
    changes are done with ajax of course.
    """
    context_class = _QuerysetBrickContext

    # Default order_by value (eg: 'name', '-creation_date').
    # '' means that no order_by() command will be added by the brick (but the natural ordering of the model
    # is kept of course).
    # BEWARE: if you want to use columns with the 'sort' feature (see the templatetags lib 'creme_bricks':
    #  {% brick_table_column_for_field %} & {% brick_table_column_for_cell %}), you have to set this attribute.
    order_by = ''
    cell_sorter_registry = cell_sorter_registry

    def _is_order_valid(self, model, order):
        # fname = order[1:] if order.startswith('-') else order
        fname = OrderedField(order).field_name
        cell = EntityCellRegularField.build(model=model, name=fname)

        if cell is None:
            return False

        # if not cell.sortable:
        if not self.cell_sorter_registry.get_field_name(cell):
            logger.warning('QuerysetBrick: the field "{}" is not sortable.'.format(fname))
            return False

        return True

    def _build_template_context(self, context, brick_id, brick_context, **extra_kwargs):
        request = context['request']
        order_by = ''
        objects = extra_kwargs['objects']

        if self.order_by:
            req_order_by = request.GET.get('{}_order'.format(brick_id))
            raw_order_by = brick_context.get_order_by(self.order_by) if req_order_by is None else req_order_by

            if self._is_order_valid(model=objects.model, order=raw_order_by):
                order_by = raw_order_by
                extra_kwargs['objects'] = objects.order_by(order_by)

        return super()._build_template_context(
                context=context, brick_id=brick_id, brick_context=brick_context,
                objects_ctype=ContentType.objects.get_for_model(objects.model),
                order_by=order_by,
                **extra_kwargs
        )

    def get_template_context(self, context, queryset, **extra_kwargs):
        """@param queryset: Set of objects to display in the brick."""
        return PaginatedBrick.get_template_context(self, context, objects=queryset, **extra_kwargs)


class EntityBrick(Brick):
    id_ = MODELBRICK_ID
    verbose_name  = _('Information on the entity (generic)')
    template_name = 'creme_core/bricks/generic/entity.html'

    BASE_FIELDS = {'created', 'modified', 'user'}

    def _get_cells(self, entity, context):
        model = entity.__class__
        BASE_FIELDS = self.BASE_FIELDS
        is_hidden = context['fields_configs'].get_4_model(model).is_field_hidden

        def build_cell(field_name):
            cell = EntityCellRegularField.build(model=model, name=field_name)
            cell.is_base_field = field_name in BASE_FIELDS

            return cell

        return [build_cell(field.name)
                    for field in model._meta.fields
                        if field.get_tag('viewable') and not is_hidden(field)
               ]

    def _get_title(self, entity, context):
        return ugettext('Information «{model}»').format(model=entity.__class__._meta.verbose_name)

    def detailview_display(self, context):
        entity = context['object']

        return self._render(self.get_template_context(
                    context,
                    title=self._get_title(entity, context),
                    cells=self._get_cells(entity, context),
        ))


class SpecificRelationsBrick(QuerysetBrick):
    dependencies  = (Relation,)  # NB: (Relation, CremeEntity) but useless
    order_by      = 'type'
    verbose_name  = _('Relationships')
    template_name = 'creme_core/bricks/specific-relations.html'

    def __init__(self, relationbrick_item):
        "@param relationbrick_item: Instance of RelationBrickItem"
        super().__init__()
        self.id_ = relationbrick_item.brick_id
        self.config_item = relationbrick_item

        rtype = relationbrick_item.relation_type
        self.relation_type_deps = (rtype.id,)
        self.verbose_name = ugettext(
            'Relationship block: «{predicate}»'
        ).format(predicate=rtype.predicate)

    @staticmethod
    def generate_id(app_name, name):
        return 'specificblock_{}-{}'.format(app_name, name)

    @staticmethod
    def id_is_specific(id_):
        return id_.startswith('specificblock_')

    def detailview_display(self, context):
        # TODO: check the constraints (ContentType & CremeProperties) for 'entity'
        #       & display an message in the block (and disable the creation button)
        #       if constraints are broken ? (beware: add CremePropertyType in dependencies)
        #       (problem: it needs additional queries)
        entity = context['object']
        config_item = self.config_item
        relation_type = config_item.relation_type
        btc = self.get_template_context(
                    context,
                    entity.relations.filter(type=relation_type)
                                    .select_related('type', 'object_entity'),
                    config_item=config_item,
                    relation_type=relation_type,
                   )
        relations = btc['page'].object_list
        entities_by_ct = defaultdict(list)

        Relation.populate_real_object_entities(relations)  # DB optimisation

        for relation in relations:
            entity = relation.object_entity.get_real_entity()
            entity.srb_relation_cache = relation
            entities_by_ct[entity.entity_type_id].append(entity)

        groups = []  # List of tuples (entities_with_same_ct, headerfilter_items)
        unconfigured_group = []  # Entities that do not have a customised columns setting
        get_ct = ContentType.objects.get_for_id

        for ct_id, entities in entities_by_ct.items():
            cells = config_item.get_cells(get_ct(ct_id))

            if cells:
                groups.append((entities, cells))
            else:
                unconfigured_group.extend(entities)

        groups.append((unconfigured_group, None))  # 'unconfigured_group' must be at the end

        btc['groups'] = groups

        return self._render(btc)

    @cached_property
    def target_ctypes(self):
        return tuple(
            ct.model_class()
                for ct in self.config_item.relation_type.subject_ctypes.all()
        )


class CustomBrick(Brick):
    """Brick that can be customised by the user to display information of an entity.
    It can display regular, custom & function fields, relationships... (see HeaderFilter & EntityCells)
    """
    template_name = 'creme_core/bricks/custom.html'

    def __init__(self, id_, customblock_conf_item):
        "@param customblock_conf_item: Instance of CustomBlockConfigItem"
        super().__init__()
        self.id_ = id_
        # TODO: related models (by FK/M2M/...) ?
        self.dependencies = deps = [customblock_conf_item.content_type.model_class()]

        rtype_ids = [rtype.id for rtype in filter(None,
                                                  (getattr(cell, 'relation_type', None)
                                                       for cell in customblock_conf_item.cells
                                                  )
                                                 )
                    ]

        if rtype_ids:
            deps.append(Relation)
            self.relation_type_deps = rtype_ids

        self.verbose_name = customblock_conf_item.name
        self.config_item = customblock_conf_item

    def detailview_display(self, context):
        return self._render(self.get_template_context(context, config_item=self.config_item))


class BricksManager:
    """The bricks of a page are registered in order to regroup the query to get their states.

    Documentation for DEPRECATED features:
    Using to solve the blocks dependencies problem in a page.
    Bricks can depends on the same model : updating one brick involves to update
    the bricks which depend on the same than it.
    """
    var_name = 'blocks_manager'  # TODO: rename

    class Error(Exception):
        pass

    def __init__(self):
        self._bricks = []
        self._dependencies_map = None
        self._bricks_groups = defaultdict(list)
        self._used_relationtypes = None
        self._state_cache = None

    def add_group(self, group_name, *bricks):
        if self._dependencies_map is not None:
            raise BricksManager.Error("Can't add brick to manager after dependence resolution is done.")

        group = self._bricks_groups[group_name]
        if group:
            raise BricksManager.Error("This brick's group name already exists: {}".format(group_name))

        self._bricks.extend(bricks)
        group.extend(bricks)

    def brick_is_registered(self, brick):
        brick_id = brick.id_
        return any(b.id_ == brick_id for b in self._bricks)

    def _build_dependencies_map(self):
        dep_map = self._dependencies_map

        if dep_map is None:
            self._dependencies_map = dep_map = defaultdict(list)
            wilcarded_bricks = []

            for brick in self._bricks:
                dependencies = brick.dependencies

                if dependencies == '*':
                    wilcarded_bricks.append(brick)
                else:
                    for dep in dependencies:
                        dep_map[dep].append(brick)

            if wilcarded_bricks:
                for dep_bricks in dep_map.values():
                    dep_bricks.extend(wilcarded_bricks)

        return dep_map

    @staticmethod
    def get(context):
        return context[BricksManager.var_name]  # Will raise exception if not created: OK

    def get_remaining_groups(self):
        return list(self._bricks_groups.keys())

    def get_state(self, brick_id, user):
        "Get the state for a brick and fill a cache to avoid multiple SQL requests"
        _state_cache = self._state_cache
        if not _state_cache:
            _state_cache = self._state_cache = BrickState.get_for_brick_ids([brick.id_ for brick in self._bricks], user)

        state = _state_cache.get(brick_id)
        if state is None:
            state = self._state_cache[brick_id] = BrickState.get_for_brick_id(brick_id, user)
            logger.warning("State not set in cache for '%s'" % brick_id)

        return state

    def pop_group(self, group_name):
        return self._bricks_groups.pop(group_name)

    @property
    def used_relationtypes_ids(self):
        if self._used_relationtypes is None:
            self._used_relationtypes = {rt_id for brick in self._build_dependencies_map()[Relation]
                                            for rt_id in brick.relation_type_deps
                                       }

        return self._used_relationtypes

    @used_relationtypes_ids.setter
    def used_relationtypes_ids(self, relationtypes_ids):
        "@param relation_type_deps: Sequence of RelationType objects' IDs"
        self._used_relationtypes = set(relationtypes_ids)


class _BrickRegistry:
    """Use to retrieve a Brick by its id.
    Many services (like reloading views) need your Bricks to be registered in.
    """
    class RegistrationError(Exception):
        pass

    def __init__(self):
        self._brick_classes = {}
        self._hat_brick_classes = defaultdict(dict)
        self._object_brick_classes = {}
        self._instance_brick_classes = {}
        self._invalid_models = set()

    def register(self, *brick_classes):
        setdefault = self._brick_classes.setdefault

        for brick_cls in brick_classes:
            if setdefault(brick_cls.id_, brick_cls) is not brick_cls:
                raise self.RegistrationError("Duplicated brick's id: {}".format(brick_cls.id_))

    def register_4_instance(self, *brick_classes):  # TODO: factorise
        setdefault = self._instance_brick_classes.setdefault

        for brick_cls in brick_classes:
            if setdefault(brick_cls.id_, brick_cls) is not brick_cls:
                raise self.RegistrationError("Duplicated brick's id: {}".format(brick_cls.id_))

    def register_invalid_models(self, *models):
        """Register some models which cannot have a bricks configuration for
        their detail-views (eg: they have no detail-view, or they are not 'classical' ones).
        @param models: Classes inheriting CremeEntity.
        """
        add = self._invalid_models.add

        for model in models:
            assert issubclass(model, CremeEntity)
            add(model)

    def register_4_model(self, model, brick_cls):  # TODO: had an 'overload' arg ??
        # assert brick_cls.id_ is None
        if brick_cls.id_ != MODELBRICK_ID:
            logger.warning('register_4_model(): <%s> should have an id_== MODELBRICK_ID', brick_cls)
            brick_cls.id_ = MODELBRICK_ID
        # assert brick_cls.id_ == MODELBRICK_ID  TODO

        # NB: the key is the class, not the ContentType.id because it can cause
        # some inconsistencies in DB problem in unit tests (contenttypes cache bug with tests ??)
        self._object_brick_classes[model] = brick_cls

    def register_hat(self, model, main_brick_cls=None, secondary_brick_classes=()):
        brick_classes = self._hat_brick_classes[model]

        if main_brick_cls is not None:
            assert issubclass(main_brick_cls, Brick)

            if main_brick_cls.id_ is not None:
                raise self.RegistrationError('Main hat brick for model={} must be None (currently: {})'.format(
                                                    model, main_brick_cls.id_,
                                                )
                                            )

            brick_classes[''] = main_brick_cls

        for brick_cls in secondary_brick_classes:
            assert issubclass(brick_cls, Brick)

            brick_id = brick_cls.id_

            if not brick_id or not brick_id.startswith(Brick.GENERIC_HAT_BRICK_ID + '-'):
                raise self.RegistrationError('Secondary hat brick for model={} must have an id_ '
                                             'generated by Brick._generate_hat_id() ({})'.format(
                                                    model, brick_cls,
                                                )
                                            )

            if brick_id in brick_classes:
                raise self.RegistrationError("Duplicated hat brick's id_: {}".format(brick_id))

            brick_classes[brick_id] = brick_cls

    # @staticmethod
    # def _generate_modelbrick_id(model):
    #     meta = model._meta
    #     return 'modelblock_{}-{}'.format(meta.app_label, meta.model_name)

    def __getitem__(self, brick_id):
        return self._brick_classes[brick_id]

    def __iter__(self):
        return iter(self._brick_classes.items())

    def get_brick_4_instance(self, ibi, entity=None):
        """Get a Brick instance corresponding to a InstanceBlockConfigItem.
        @param ibi: InstanceBlockConfigItem instance.
        @param entity: CremeEntity instance if your Block has to be displayed on its detailview.
        @return Brick instance.
        """
        brick_id = ibi.brick_id
        brick_class = self._instance_brick_classes.get(InstanceBrickConfigItem.get_base_id(brick_id))

        if brick_class is None:
            logger.warning('Brick class seems deprecated: %s', brick_id)

            brick = Brick()
            brick.verbose_name = '??'
            brick.errors = [_('Unknown type of block (bad uninstall ?)')]
        else:
            brick = brick_class(ibi)
            brick.id_ = brick_id

            if entity:
                # When an InstanceBlock is on a detailview of a entity, the content
                # of this brick depends (generally) of this entity, so we have to
                # complete the dependencies.
                model = entity.__class__
                if model not in brick.dependencies:
                    brick.dependencies += (model,)

        return brick

    def get_bricks(self, brick_ids, entity=None):
        """Bricks type can be SpecificRelationsBlock/InstanceBlockConfigItem:
        in this case, they are not really registered, but created on the fly.
        @param brick_ids: Sequence of id of bricks
        @param entity: if the bricks are displayed of the detail-view of an entity,
                       it should be given.
        """
        specific_ids = list(filter(SpecificRelationsBrick.id_is_specific, brick_ids))
        instance_ids = list(filter(InstanceBrickConfigItem.id_is_specific, brick_ids))
        custom_ids   = list(filter(None, map(CustomBrickConfigItem.id_from_brick_id, brick_ids)))

        relation_bricks_items = {rbi.brick_id: rbi
                                     for rbi in RelationBrickItem.objects.filter(brick_id__in=specific_ids)
                                } if specific_ids else {}
        instance_bricks_items = {ibi.brick_id: ibi
                                     for ibi in InstanceBrickConfigItem.objects.filter(brick_id__in=instance_ids)
                                } if instance_ids else {}
        custom_bricks_items = {cbci.generate_id(): cbci
                                   for cbci in CustomBrickConfigItem.objects.filter(id__in=custom_ids)
                              } if custom_ids else {}

        for id_ in brick_ids:
            rbi = relation_bricks_items.get(id_)
            if rbi:
                yield SpecificRelationsBrick(rbi)
                continue

            ibi = instance_bricks_items.get(id_)
            if ibi:
                yield self.get_brick_4_instance(ibi, entity)
                continue

            cbci = custom_bricks_items.get(id_)
            if cbci:
                yield CustomBrick(id_, cbci)
                continue

            # if id_.startswith('modelblock_'):
            #     yield self.get_brick_4_object(ContentType.objects
            #                                              .get_by_natural_key(*id_[len('modelblock_'):].split('-'))
            #                                  )
            #     continue
            if id_ == MODELBRICK_ID:
                if entity is None:
                    logger.warning('Model brick without entity ?!')
                else:
                    yield self.get_brick_4_object(entity)

                continue

            if id_.startswith(Brick.GENERIC_HAT_BRICK_ID):
                if entity is None:
                    logger.warning('Header brick without entity ?!')
                else:
                    model = entity.__class__

                    if id_ == Brick.GENERIC_HAT_BRICK_ID:
                        yield self.get_generic_hat_brick(model)
                    else:
                        brick_cls = self._hat_brick_classes[model].get(id_)
                        if brick_cls is None:
                            logger.warning('Invalid hat brick ID: %s', id_)
                            yield self.get_generic_hat_brick(model)
                        else:
                            yield brick_cls()

                continue

            brick_cls = self._brick_classes.get(id_)
            if brick_cls is None:
                logger.warning('Brick seems deprecated: %s', id_)
                yield Brick()
            else:
                yield brick_cls()

    def get_brick_4_object(self, obj_or_ct):
        """Return the Brick that displays fields for a CremeEntity instance.
        @param obj_or_ct: Model (class inheriting CremeEntity), or ContentType instance
                          representing this model, or instance of this model.
        """
        model = obj_or_ct.__class__ if isinstance(obj_or_ct, CremeEntity) else \
                obj_or_ct.model_class() if isinstance(obj_or_ct, ContentType) else \
                obj_or_ct
        brick_cls = self._object_brick_classes.get(model)

        if brick_cls is None:
            brick = EntityBrick()
            brick.dependencies = (model,)  # TODO: what about FK, M2M ?
        else:
            brick = brick_cls()

            if not brick.dependencies:
                # TODO: warning ??
                brick.dependencies = (model,)  # TODO: what about FK, M2M ?

            if brick.verbose_name is Brick.verbose_name:
                # TODO: warning ??
                brick.verbose_name = _('Information on the entity')

        # brick.id_ = self._generate_modelbrick_id(model)

        return brick

    def get_generic_hat_brick(self, model):
        brick_cls = self._hat_brick_classes[model].get('')

        if brick_cls is None:
            brick = SimpleBrick()
            brick.dependencies = (model,)  # TODO: what about FK, M2M ?
            brick.template_name = 'creme_core/bricks/generic/hat-bar.html'
        else:
            brick = brick_cls()

            if not brick.dependencies:
                brick.dependencies = (model,)  # TODO: what about FK, M2M ?

        brick.id_ = Brick.GENERIC_HAT_BRICK_ID
        brick.verbose_name = _('Title bar')

        return brick

    def get_compatible_bricks(self, model=None):
        """Returns the list of registered bricks that are configurable and compatible with the given ContentType.
        @param model: Constraint on a CremeEntity class ;
                      None means bricks must be compatible with all kind of CremeEntity.
        """
        for brick_cls in self._brick_classes.values():
            brick = brick_cls()

            if brick.configurable and hasattr(brick, 'detailview_display') \
               and (not brick.target_ctypes or model in brick.target_ctypes):
                yield brick

        # for rbi in RelationBrickItem.objects.all():
        #     yield SpecificRelationsBrick(rbi)
        for rbi in RelationBrickItem.objects.select_related('relation_type'):
            brick = SpecificRelationsBrick(rbi)

            if not brick.target_ctypes or model in brick.target_ctypes:
                yield brick

        for ibi in InstanceBrickConfigItem.objects.all():
            brick = self.get_brick_4_instance(ibi)

            if hasattr(brick, 'detailview_display') \
                    and (not brick.target_ctypes or model in brick.target_ctypes):
                yield brick

        if model:
            yield self.get_brick_4_object(model)

            for cbci in CustomBrickConfigItem.objects.filter(content_type=ContentType.objects.get_for_model(model)):
                yield CustomBrick(cbci.generate_id(), cbci)
        else:
            yield EntityBrick()

    def get_compatible_hat_bricks(self, model):
        yield self.get_generic_hat_brick(model)

        for brick_id, brick_cls in self._hat_brick_classes[model].items():
            if brick_id:  # Only generic hat brick's ID is empty
                yield brick_cls()

    def get_compatible_home_bricks(self):
        method_name = 'home_display'

        for brick_cls in self._brick_classes.values():
            brick = brick_cls()

            if brick.configurable and hasattr(brick, method_name):
                yield brick

        for ibi in InstanceBrickConfigItem.objects.all():
            block = self.get_brick_4_instance(ibi)

            if hasattr(block, method_name):
                yield block

    def is_model_invalid(self, model):
        "See register_invalid_model()"
        return model in self._invalid_models


brick_registry = _BrickRegistry()
