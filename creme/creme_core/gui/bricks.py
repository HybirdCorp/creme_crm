################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

import logging
# import warnings
from collections import defaultdict
from collections.abc import Iterable, Iterator, Sequence
from typing import DefaultDict, List, Literal, Tuple, Type, Union

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.paginator import EmptyPage, InvalidPage, Paginator
from django.db.models import Model
from django.template.loader import get_template
from django.utils.functional import cached_property
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from ..constants import MODELBRICK_ID
from ..core.entity_cell import EntityCell, EntityCellRegularField
from ..core.exceptions import ConflictError
from ..core.field_tags import FieldTag
from ..core.sorter import cell_sorter_registry
from ..models import (
    BrickState,
    CremeEntity,
    CremeUser,
    CustomBrickConfigItem,
    InstanceBrickConfigItem,
    Relation,
    RelationBrickItem,
)
from ..utils.meta import OrderedField

logger = logging.getLogger(__name__)
BrickDependencies = Union[List[Type[Model]], Tuple[Type[Model], ...], Literal['*']]


class _BrickContext:
    def __repr__(self):
        return '<BrickContext>'

    def as_dict(self) -> dict:
        return {}

    @classmethod
    def from_dict(cls, data: dict):
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
        return f'VOID BLOCK FOR DETAILVIEW: {self.verbose_name}'

    def home_display(self, context):
        return f'VOID BLOCK FOR HOME: {self.verbose_name}'
    """
    # The ID of a brick (string) is used to retrieve the class of a Brick,
    # and build the corresponding instance when:
    #   - the configuration (detail-view/home/portal) is loaded (page creation).
    #   - some bricks are reloaded.
    # For regular brick classes, you just have to override this attribute by using
    # the method generate_id().
    id: str = ''

    # Human-readable name used as default title, or in the configuration GUI.
    # Tips: use gettext_lazy()
    verbose_name: str = 'BLOCK'

    # Description used as tool-tips, and in the configuration GUI.
    # Tips: use gettext_lazy()
    description: str = ''

    # List of the models on which the brick depends (i.e. generally the brick
    # displays instances of these models) ; it also can be the '*' string,
    # which is a wildcard meaning 'All models used in the page'.
    dependencies: BrickDependencies = ()

    # List of IDs of RelationType objects on which the brick depends ;
    # only used for Bricks which have the model 'Relation' in their dependencies.
    relation_type_deps: Sequence[str] = ()

    # 'True' means that the brick will never be used to change the instances
    # of its dependencies models.
    # (i.e. the brick is only used to display these instances ;
    # there is no inner-popup to create/edit/delete/...)
    #   ---> so when this brick is reloaded (e.g. to change the pagination),
    #   it does not cause the dependant bricks to be reloaded
    #   (but it is still reloaded when the dependant bricks are reloaded of course).
    read_only: bool = False

    template_name: str = 'OVERRIDE_ME.html'  # Used to render the brick of course
    context_class = _BrickContext  # Class of the instance which stores the context in the session.

    # True means that the Brick appears in the configuration GUI
    # (i.e. it appears on classical detail-views/portals)
    configurable: bool = True

    # Sequence of classes inheriting CremeEntity which can have this type of
    # brick on their detail-views. An empty sequence means that all types are OK.
    # This attribute notably is used by the reloading views (to only use allowed
    # bricks, & by creme_config to only propose relevant bricks.
    # Example of value:
    #    # Available for detail-views of Contact & Organisation
    #    target_ctypes = (Contact, Organisation)
    target_ctypes: Sequence[type[CremeEntity]] = ()

    # The views (detail-view, home-view, 'creme_core.views.bricks.BricksReloading')
    # check these permissions, and display a <ForbiddenBrick> (see below) when the
    # user should not view a Brick, so :
    #  - the visual difference is clear between a brick related to a forbidden app
    #    and a brick with just some forbidden actions (creation, edition...).
    #  - it avoids information leaking.
    # It can be:
    #  - a classical permission string
    #    Example: <permissions = 'my_app'>
    #  - a sequence of permission strings
    #    Example: <permissions = ['my_app1', 'my_app2.can_admin']>
    # An empty value (like the default empty string) means "No special permission required".
    permissions: str | Sequence[str] = ''

    GENERIC_HAT_BRICK_ID: str = 'hat'

    def __init__(self):
        if self.relation_type_deps and Relation not in self.dependencies:
            raise ValueError(
                f'The Brick <{self.__class__.__name__}> gets RelationTypes '
                f'dependencies but the model Relation is not a dependence.'
            )

        self._reloading_info = None

    def check_permissions(self, user) -> None:
        """@raise PermissionDenied, ConflictError."""
        user.has_perms_or_die(self.permissions)

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
    def generate_id(app_name: str, name: str) -> str:  # TODO: rename _generate_id ?
        return f'regular-{app_name}-{name}'

    @classmethod
    def _generate_hat_id(cls, app_name: str, name: str) -> str:
        return f'{cls.GENERIC_HAT_BRICK_ID}-{app_name}-{name}'

    @property
    def html_id(self):
        return f'brick-{self.id}'

    def _render(self, template_context) -> str:
        # return get_template(self.template_name).render(template_context)
        return get_template(template_context['template_name']).render(template_context)

    def _simple_detailview_display(self, context: dict) -> str:
        """Helper method to build a basic detailview_display() method for
        classes that inherit Brick.
        """
        return self._render(self.get_template_context(context))

    def _iter_dependencies_info(self):
        for dep in self.dependencies:
            if isinstance(dep, type) and issubclass(dep, Model):
                if dep == Relation:
                    for rtype_id in self.relation_type_deps:
                        yield 'creme_core.relation.' + rtype_id
                else:
                    meta = dep._meta
                    yield f'{meta.app_label}.{meta.model_name}'
            else:
                yield str(dep)

    def _build_template_context(self,
                                context: dict,
                                brick_id: str,
                                brick_context: _BrickContext,
                                **extra_kwargs) -> dict:
        context['template_name'] = self.template_name
        context['brick_id'] = brick_id
        context['html_id'] = self.html_id
        context['verbose_name'] = self.verbose_name
        context['description'] = self.description
        context['state'] = BrickManager.get(context).get_state(self.id, context['user'])
        context['dependencies'] = [*self._iter_dependencies_info()]
        context['reloading_info'] = self._reloading_info
        context['read_only'] = self.read_only

        context.update(extra_kwargs)

        return context

    def get_template_context(self, context: dict, **extra_kwargs) -> dict:
        """ Build the brick template context.
        @param context: Template context (contains 'request' etc...).
        """
        brick_id = self.id
        request = context['request']
        base_url = request.GET.get('base_url', request.path)
        session = request.session

        try:
            serialized_context = session['brickcontexts_manager'][base_url][brick_id]
        except KeyError:
            brick_context = self.context_class()
        else:
            brick_context = self.context_class.from_dict(serialized_context)

        template_context = self._build_template_context(
            context=context,
            brick_id=brick_id,
            brick_context=brick_context,
            **extra_kwargs
        )

        # # NB:  not 'assert' (it causes problems with bricks in inner popups)
        # if not BrickManager.get(context).brick_is_registered(self):
        #     logger.debug('Not registered brick: %s', self.id)

        if brick_context.update(template_context):
            session.setdefault(
                'brickcontexts_manager', {},
            ).setdefault(
                base_url, {},
            )[brick_id] = brick_context.as_dict()

            request.session.modified = True

        return template_context


class SimpleBrick(Brick):
    detailview_display = Brick._simple_detailview_display


class ForbiddenBrick(Brick):
    """Used by code which needs to get a content for forbidden brick.
    You should not have to use it.
    """
    template_name = 'creme_core/bricks/generic/forbidden.html'

    def __init__(self, *, id, verbose_name, error=''):
        super().__init__()
        self.id = id
        self.verbose_name = verbose_name
        self.error = error

    def get_template_context(self, context, **extra_kwargs):
        return super().get_template_context(
            context, permissions_error=self.error, **extra_kwargs
        )

    def detailview_display(self, context):
        # return self._render(self.get_template_context(context, permissions_error=self.error))
        return self._render(self.get_template_context(context))

    def home_display(self, context):
        # return self.detailview_display(context=context)
        return self._render(self.get_template_context(context))


class VoidBrick(SimpleBrick):
    """Used by code which needs to get a content for forbidden/invalid/... brick."""
    template_name = 'creme_core/bricks/generic/void.html'

    def __init__(self, *, id):
        super().__init__()
        self.id = id

    home_display = Brick._simple_detailview_display


class _PaginatedBrickContext(_BrickContext):
    __slots__ = ('page',)

    def __init__(self) -> None:
        self.page: int = 1

    def __repr__(self):
        return f'<PaginatedBrickContext: page={self.page}>'

    def as_dict(self):
        return {'page': self.page}

    def update(self, template_context) -> bool:
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
    page_size: int = settings.BLOCK_SIZE  # Number of items in the page

    def _build_template_context(self, context, brick_id, brick_context, **extra_kwargs):
        assert isinstance(brick_context, _PaginatedBrickContext)

        request = context['request']
        objects = extra_kwargs.pop('objects')

        page_index = request.GET.get(f'{brick_id}_page')
        if page_index is not None:
            try:
                page_index = int(page_index)
            except ValueError:
                logger.warning(
                    'PaginatedBrick: invalid page number for brick %s: %s',
                    brick_id, page_index,
                )
                page_index = 1
        else:
            page_index = brick_context.page

        paginator = Paginator(objects, self.page_size)

        try:
            page = paginator.page(page_index)
        except (EmptyPage, InvalidPage):
            page = paginator.page(paginator.num_pages)

        return super()._build_template_context(
            context=context,
            brick_id=brick_id,
            brick_context=brick_context,
            page=page,
            **extra_kwargs
        )

    def get_template_context(self, context, objects, **extra_kwargs):
        """@param objects: Sequence of objects to display in the brick."""
        return Brick.get_template_context(self, context, objects=objects, **extra_kwargs)


class _QuerysetBrickContext(_PaginatedBrickContext):
    __slots__ = ('page', '_order_by')
    _order_by: str

    def __init__(self):
        super().__init__()  # *args **kwargs ??
        self._order_by = ''

    def __repr__(self):
        return f'<QuerysetBrickContext: page={self.page} order_by={self._order_by}>'

    def as_dict(self):
        d = super().as_dict()
        d['_order_by'] = self._order_by

        return d

    def get_order_by(self, order_by: str) -> str:
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
    It allows ordering objects by one of its columns (which can change): order
    changes are done with ajax of course.
    """
    context_class = _QuerysetBrickContext

    # Default order_by value (e.g. 'name', '-creation_date').
    # '' means that no order_by() command will be added by the brick (but the
    # natural ordering of the model is kept of course).
    # BEWARE: if you want to use columns with the 'sort' feature
    # (see the templatetags lib 'creme_bricks': {% brick_table_column_for_field %} &
    # {% brick_table_column_for_cell %}), you have to set this attribute.
    order_by: str = ''
    cell_sorter_registry = cell_sorter_registry

    def _is_order_valid(self, model: type[Model], order: str) -> bool:
        fname = OrderedField(order).field_name
        cell = EntityCellRegularField.build(model=model, name=fname)

        if cell is None:
            return False

        if not self.cell_sorter_registry.get_field_name(cell):
            logger.warning('QuerysetBrick: the field "%s" is not sortable.', fname)
            return False

        return True

    def _build_template_context(self, context, brick_id, brick_context, **extra_kwargs):
        assert isinstance(brick_context, _QuerysetBrickContext)

        request = context['request']
        order_by = ''
        objects = extra_kwargs['objects']

        if self.order_by:
            req_order_by = request.GET.get(f'{brick_id}_order')
            raw_order_by = brick_context.get_order_by(
                self.order_by,
            ) if req_order_by is None else req_order_by

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
        return PaginatedBrick.get_template_context(
            self, context, objects=queryset, **extra_kwargs
        )


# class EntityBrick(Brick):
class EntityBrick(SimpleBrick):
    id = MODELBRICK_ID
    verbose_name = _('Information on the entity (generic)')
    description = _(
        'Displays the values for the fields of the current entity.\n'
        'Hint #1: lots of fields can be hidden in configuration '
        '(so their are hidden everywhere: forms, list-views…).\n'
        'Hint #2: you can create Custom Blocks in configuration to chose '
        'the title of the block, which fields are displayed and their order.'
    )
    template_name = 'creme_core/bricks/generic/entity.html'

    BASE_FIELDS = {'created', 'modified', 'user'}

    def _get_cells(self, entity, context) -> list[EntityCell]:
        model = entity.__class__
        BASE_FIELDS = self.BASE_FIELDS
        is_hidden = context['fields_configs'].get_for_model(model).is_field_hidden

        def build_cell(field_name):
            cell = EntityCellRegularField.build(model=model, name=field_name)
            cell.is_base_field = field_name in BASE_FIELDS

            return cell

        return [
            build_cell(field.name)
            for field in model._meta.fields
            if field.get_tag(FieldTag.VIEWABLE) and not is_hidden(field)
        ]

    def _get_title(self, entity: CremeEntity, context) -> str:
        return gettext('Information «{model}»').format(model=entity.entity_type)

    def get_template_context(self, context, **extra_kwargs):
        entity = context['object']

        return super().get_template_context(
            context,
            title=self._get_title(entity, context),
            cells=self._get_cells(entity, context),
            **extra_kwargs
        )

    # def detailview_display(self, context):
    #     entity = context['object']
    #
    #     return self._render(self.get_template_context(
    #         context,
    #         title=self._get_title(entity, context),
    #         cells=self._get_cells(entity, context),
    #     ))


class SpecificRelationsBrick(QuerysetBrick):
    dependencies = (Relation,)  # NB: (Relation, CremeEntity) but useless
    verbose_name = 'Relationships'  # Overridden by __init__()
    description = _(
        'Displays the entities linked to the current entity with a specific '
        'type of Relationship.\n'
        'Hint #1: this kind of block can be created in the configuration of blocks.\n'
        "Hint #2: you can configure the fields which are displayed (in the blocks' "
        "configuration, or in the block's menu which appears when you click on the "
        "block's icon)."
    )
    # order_by = '...' We use a multi column order manually
    template_name = 'creme_core/bricks/specific-relations.html'

    def __init__(self, relationbrick_item: RelationBrickItem):
        super().__init__()
        self.id = relationbrick_item.brick_id
        self.config_item = relationbrick_item

        rtype = relationbrick_item.relation_type
        self.relation_type_deps = (rtype.id,)
        self.verbose_name = gettext(
            'Relationship block: «{predicate}»'
        ).format(predicate=rtype.predicate)

        self.description = gettext(
            'Displays the linked entities which are the objects of relationships «{predicate}» '
            '(the current entity being the subject of these relationships).\n'
            'Hint #1: this kind of block can be created in the configuration of blocks.\n'
            "Hint #2: you can configure the fields which are displayed (in the blocks' "
            "configuration, or in the block's menu which appears when you click on the "
            "block's icon)."
        ).format(predicate=rtype.predicate)

    def detailview_display(self, context) -> str:
        # TODO: check the constraints (ContentType & CremeProperties) for 'entity'
        #       & display a message in the brick (and disable the creation button)
        #       if constraints are broken ? (beware: add CremePropertyType in dependencies)
        #       (problem: it needs additional queries)
        entity = context['object']
        config_item = self.config_item
        relation_type = config_item.relation_type
        btc = self.get_template_context(
            context,
            # entity.relations
            #       .filter(type=relation_type)
            #       .select_related('type')
            #       .prefetch_related('real_object'),
            # NB: we order by:
            #   - "ctype" to group entities with the same type (sadly types will be ordered
            #     by their ID, not their localized labels -- it would be difficult to do).
            #   - "object_entity" which will be extended to
            #     <object_entity__header_filter_search_field>, for alphabetical ordering.
            #   - "id" to get a consistent ordering of entities between different queries
            #     (it's important for pagination)
            entity.relations
                  .filter(type=relation_type)
                  .select_related('type')
                  .order_by('object_ctype_id', 'object_entity', 'id')
                  .prefetch_related('real_object'),
            config_item=config_item,
            relation_type=relation_type,
        )
        relations = btc['page'].object_list
        entities_by_ct: DefaultDict[int, list[CremeEntity]] = defaultdict(list)

        for relation in relations:
            entity = relation.real_object
            entity.srb_relation_cache = relation
            entities_by_ct[entity.entity_type_id].append(entity)

        # Entities in each list have the same CT
        groups: list[tuple[list[CremeEntity], list[EntityCell] | None]] = []

        # Entities that do not have a customised columns setting
        unconfigured_group: list[CremeEntity] = []

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
        return tuple(self.config_item.relation_type.subject_models)


class InstanceBrick(Brick):
    # Used by creme_config.bricks.InstanceBricksConfigBrick
    errors: list[str] | None = None

    def __init__(self, instance_brick_config_item: InstanceBrickConfigItem):
        super().__init__()
        self.config_item = instance_brick_config_item
        self.id = instance_brick_config_item.brick_id


# class CustomBrick(Brick):
class CustomBrick(SimpleBrick):
    """Brick which can be customised by the user to display information of an entity.
    It can display regular, custom & function fields, relationships...
    (see HeaderFilter & EntityCells)
    """
    description = _(
        'Displays some information concerning the current entity, like:\n'
        '- fields\n'
        '- Custom Fields\n'
        '- related entities\n'
        '- …\n'
        'Hint: this kind of block can be created/modified in the configuration '
        'of blocks («Custom blocks»).'
    )  # TODO: properties to insert dynamically the cells ?
    template_name = 'creme_core/bricks/custom.html'

    # TODO: remove "id_" argument?
    def __init__(self, id_: str, custombrick_conf_item: CustomBrickConfigItem):
        super().__init__()
        self.id = id_
        # TODO: related models (by FK/M2M/...) ?
        self.dependencies = deps = [custombrick_conf_item.content_type.model_class()]

        rtype_ids: list[str] = [
            rtype.id
            for rtype in filter(
                None,
                (
                    getattr(cell, 'relation_type', None)
                    for cell in custombrick_conf_item.cells
                ),
            )
        ]

        if rtype_ids:
            deps.append(Relation)
            self.relation_type_deps = rtype_ids

        self.verbose_name = custombrick_conf_item.name
        self.config_item = custombrick_conf_item

    def get_template_context(self, context, **extra_kwargs):
        config_item = self.config_item

        return super().get_template_context(
            context,
            config_item=config_item,
            cells=[*config_item.filtered_cells],
            **extra_kwargs
        )

    # def detailview_display(self, context) -> str:
    #     config_item = self.config_item
    #     return self._render(self.get_template_context(
    #         context,
    #         config_item=config_item,
    #         cells=[*config_item.filtered_cells],
    #     ))


class BrickManager:
    """The bricks of a page are registered in order to regroup the query to get
    their states.
    """
    var_name: str = 'bricks_manager'

    class Error(Exception):
        pass

    def __init__(self) -> None:
        self._bricks: list[Brick] = []

        self._bricks_groups: DefaultDict[str, list[Brick]] = defaultdict(list)
        self._used_relationtypes: set[str] | None = None
        self._state_cache: dict[str, BrickState] | None = None

    def add_group(self, group_name: str, *bricks: Brick) -> None:
        group = self._bricks_groups[group_name]
        if group:
            raise BrickManager.Error(
                f"This brick's group name already exists: {group_name}"
            )

        self._bricks.extend(bricks)
        group.extend(bricks)

    def brick_is_registered(self, brick: Brick) -> bool:
        brick_id = brick.id
        return any(b.id == brick_id for b in self._bricks)

    @property
    def bricks(self):
        yield from self._bricks

    @staticmethod
    def get(context) -> BrickManager:
        return context[BrickManager.var_name]  # Will raise exception if not created: OK

    # TODO: property
    def get_remaining_groups(self) -> list[str]:
        return [*self._bricks_groups.keys()]

    def get_state(self, brick_id: str, user) -> BrickState:
        "Get the state for a brick and fill a cache to avoid multiple SQL requests."
        _state_cache = self._state_cache
        if not _state_cache:
            _state_cache = self._state_cache = BrickState.objects.get_for_brick_ids(
                brick_ids=[brick.id for brick in self._bricks],
                user=user,
            )

        state = _state_cache.get(brick_id)
        if state is None:
            state = self._state_cache[brick_id] = BrickState.objects.get_for_brick_id(
                brick_id=brick_id, user=user,
            )
            logger.warning("State not set in cache for '%s'", brick_id)

        return state

    def pop_group(self, group_name: str) -> list[Brick]:
        return self._bricks_groups.pop(group_name)


class BrickRegistry:
    """Use to retrieve a Brick by its id.
    Many services (like reloading views) need your Bricks to be registered in.
    """

    class RegistrationError(Exception):
        pass

    class UnRegistrationError(RegistrationError):
        pass

    def __init__(self) -> None:
        self._brick_classes: dict[str, type[Brick]] = {}
        self._hat_brick_classes: \
            DefaultDict[type[CremeEntity], dict[str, type[Brick]]] = defaultdict(dict)
        self._object_brick_classes: dict[type[CremeEntity], type[Brick]] = {}
        self._instance_brick_classes: dict[str, type[InstanceBrick]] = {}
        self._invalid_models: set[type[CremeEntity]] = set()

    def register(self, *brick_classes: type[Brick]) -> BrickRegistry:
        setdefault = self._brick_classes.setdefault

        for brick_cls in brick_classes:
            brick_id = brick_cls.id

            if not brick_id:
                raise self.RegistrationError(f'Brick class with empty ID: {brick_cls}')

            if setdefault(brick_id, brick_cls) is not brick_cls:
                raise self.RegistrationError(f"Duplicated brick's ID: {brick_id}")

            # if hasattr(brick_cls, 'has_perms'):
            #     logger.critical(
            #         'The brick class %s still defines a method "has_perms()"; '
            #         'define the new method "check_permissions()" instead.',
            #         brick_cls,
            #     )

        return self

    # TODO: factorise
    # TODO: def unregister_4_instance()?
    def register_4_instance(self, *brick_classes: type[InstanceBrick]) -> BrickRegistry:
        setdefault = self._instance_brick_classes.setdefault

        for brick_cls in brick_classes:
            if not issubclass(brick_cls, InstanceBrick):
                raise self.RegistrationError(
                    f'Brick class does not inherit InstanceBrick: {brick_cls}'
                )

            brick_id = brick_cls.id

            if not brick_id:
                raise self.RegistrationError(f'Brick class with empty ID: {brick_cls}')

            if setdefault(brick_id, brick_cls) is not brick_cls:
                raise self.RegistrationError(f"Duplicated brick's ID: {brick_id}")

        return self

    def register_invalid_models(self, *models: type[CremeEntity]) -> BrickRegistry:
        """Register some models which cannot have a configuration for Bricks on
        their detail-views (e.g. they have no detail-view, or they are not 'classical' ones).
        @param models: Classes inheriting CremeEntity.
        """
        add = self._invalid_models.add

        for model in models:
            assert issubclass(model, CremeEntity)
            add(model)

        return self

    # TODO: had a boolean argument "override" ??
    def register_4_model(self,
                         model: type[CremeEntity],
                         brick_cls: type[Brick],
                         ) -> BrickRegistry:
        assert brick_cls.id == MODELBRICK_ID

        # NB: the key is the class, not the ContentType.id because it can cause
        # some inconsistencies in DB problem in unit tests (contenttypes cache bug with tests ??)
        self._object_brick_classes[model] = brick_cls

        return self

    def register_hat(self, model: type[CremeEntity],
                     main_brick_cls: type[Brick] | None = None,
                     secondary_brick_classes: Iterable[type[Brick]] = (),
                     ) -> BrickRegistry:
        brick_classes = self._hat_brick_classes[model]

        if main_brick_cls is not None:
            assert issubclass(main_brick_cls, Brick)

            if main_brick_cls.id:
                raise self.RegistrationError(
                    f'Main hat brick for {model=} must be empty '
                    f'(currently: {main_brick_cls.id})'
                )

            brick_classes[''] = main_brick_cls

        for brick_cls in secondary_brick_classes:
            assert issubclass(brick_cls, Brick)

            brick_id = brick_cls.id

            if not brick_id or not brick_id.startswith(Brick.GENERIC_HAT_BRICK_ID + '-'):
                raise self.RegistrationError(
                    f'Secondary hat brick for {model=} must have an ID '
                    f'generated by Brick._generate_hat_id() ({brick_cls})'
                )

            if brick_id in brick_classes:
                raise self.RegistrationError(f"Duplicated hat brick's ID: {brick_id}")

            brick_classes[brick_id] = brick_cls

        return self

    def unregister(self, *brick_classes: type[Brick]) -> BrickRegistry:
        for brick_cls in brick_classes:
            brick_id = brick_cls.id

            if not brick_id:
                raise self.UnRegistrationError(f'Brick class with empty ID: {brick_cls}')

            if self._brick_classes.pop(brick_id, None) is None:
                raise self.UnRegistrationError(
                    f'Brick class with invalid ID (already unregistered?): {brick_cls}',
                )

        return self

    def unregister_4_model(self, model: type[CremeEntity]) -> BrickRegistry:
        if self._object_brick_classes.pop(model, None) is None:
            raise self.UnRegistrationError(
                f"Invalid Brick for model {model} (already unregistered?)"
            )

        return self

    def unregister_hat(self, model: type[CremeEntity],
                       main_brick: bool = False,
                       secondary_brick_classes: Iterable[type[Brick]] = (),
                       ) -> BrickRegistry:
        brick_classes = self._hat_brick_classes[model]

        if main_brick:
            if brick_classes.pop('', None) is None:
                raise self.UnRegistrationError(
                    f"Invalid main hat brick for model {model} (already unregistered?)",
                )

        for brick_cls in secondary_brick_classes:
            assert issubclass(brick_cls, Brick)

            brick_id = brick_cls.id

            if brick_classes.pop(brick_id, None) is None:
                raise self.UnRegistrationError(
                    f'Invalid hat brick for model {model} with id="{brick_id}" '
                    f'(already unregistered?)',
                )

        return self

    def __getitem__(self, brick_id: str) -> type[Brick]:
        return self._brick_classes[brick_id]

    def __iter__(self) -> Iterator[tuple[str, type[Brick]]]:
        return iter(self._brick_classes.items())

    def get_brick_4_instance(self,
                             ibi: InstanceBrickConfigItem,
                             entity: CremeEntity | None = None,
                             ) -> InstanceBrick:
        """Get a Brick instance corresponding to an InstanceBrickConfigItem.
        @param ibi: InstanceBrickConfigItem instance.
        @param entity: CremeEntity instance if your Brick has to be displayed on its detail-view.
        @return Brick instance.
        """
        brick_class_id = ibi.brick_class_id
        brick_class = self._instance_brick_classes.get(brick_class_id)

        if brick_class is None:
            logger.warning('Brick class seems deprecated: %s', brick_class_id)

            brick = InstanceBrick(ibi)
            brick.verbose_name = '??'
            # TODO: add this attribute to the class
            brick.errors = [_('Unknown type of block (bad uninstall?)')]
        else:
            brick = brick_class(ibi)

            if entity:
                # When an InstanceBrick is on a detail-view of an entity, the content
                # of this brick depends (generally) on this entity, so we have to
                # complete the dependencies.
                model = entity.entity_type.model_class()
                if model not in brick.dependencies:
                    assert not isinstance(brick.dependencies, str)  # NB: '*'

                    brick.dependencies += (model,)

        return brick

    def get_bricks(self,
                   brick_ids: Sequence[str],
                   entity: CremeEntity | None = None,
                   *,  # TODO: make all arguments keyword-only
                   user: CremeUser | None = None,
                   ) -> Iterator[Brick]:
        """Bricks type can be SpecificRelationsBrick/InstanceBrickConfigItem:
        in this case, they are not really registered, but created on the fly.
        @param brick_ids: Sequence of bricks' IDs.
        @param entity: if the bricks are displayed of the detail-view of an
               entity, it should be given.
        """
        raw_relation_bricks_items = RelationBrickItem.objects.for_brick_ids(brick_ids)
        RelationBrickItem.prefetch_rtypes(raw_relation_bricks_items)
        relation_bricks_items = {rbi.brick_id: rbi for rbi in raw_relation_bricks_items}

        instance_bricks_items = {
            ibi.brick_id: ibi
            # TODO: CremeEntity.populate_real_entities
            for ibi in InstanceBrickConfigItem.objects
                                              .for_brick_ids(brick_ids)
                                              .prefetch_related('entity')
        }
        custom_bricks_items = {
            cbci.brick_id: cbci
            for cbci in CustomBrickConfigItem.objects.for_brick_ids(brick_ids)
        }

        for id_ in brick_ids:
            rbi = relation_bricks_items.get(id_)
            if rbi:
                if entity is None:
                    logger.warning('Relation brick without entity?!')
                else:
                    yield SpecificRelationsBrick(rbi)

                continue

            ibi = instance_bricks_items.get(id_)
            if ibi:
                yield self.get_brick_4_instance(ibi, entity)
                continue

            cbci = custom_bricks_items.get(id_)
            if cbci:
                if entity is None:
                    logger.warning('Custom brick without entity?!')
                elif entity.entity_type != cbci.content_type:
                    logger.warning(
                        'Custom brick is related to %s, but the entity is an instance of %s',
                        cbci.content_type.model_class(), type(entity),
                    )
                else:
                    yield CustomBrick(id_, cbci)

                continue

            if id_ == MODELBRICK_ID:
                if entity is None:
                    logger.warning('Model brick without entity?!')
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
                brick = brick_cls()

                if user:
                    try:
                        brick.check_permissions(user=user)
                    except (PermissionDenied, ConflictError) as e:
                        brick = ForbiddenBrick(
                            id=brick.id, verbose_name=brick.verbose_name, error=str(e),
                        )

                yield brick

    def get_brick_4_object(self,
                           obj_or_ct: type[CremeEntity] | ContentType | CremeEntity,
                           /,
                           ) -> Brick:
        """Return the Brick that displays fields for a CremeEntity instance.
        @param obj_or_ct: Model (class inheriting CremeEntity), or ContentType
               instance representing this model, or instance of this model.
        """
        model = (
            obj_or_ct.__class__ if isinstance(obj_or_ct, CremeEntity) else
            obj_or_ct.model_class() if isinstance(obj_or_ct, ContentType) else
            obj_or_ct
        )
        brick_cls = self._object_brick_classes.get(model)
        brick: Brick

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

        return brick

    def get_generic_hat_brick(self, model: type[CremeEntity]) -> Brick:
        brick_cls = self._hat_brick_classes[model].get('')
        brick: Brick

        if brick_cls is None:
            brick = SimpleBrick()
            brick.dependencies = (model,)  # TODO: what about FK, M2M ?
            brick.template_name = 'creme_core/bricks/generic/hat-bar.html'
        else:
            brick = brick_cls()

            if not brick.dependencies:
                brick.dependencies = (model,)  # TODO: what about FK, M2M ?

        brick.id = Brick.GENERIC_HAT_BRICK_ID
        brick.verbose_name = _('Title bar')

        return brick

    def get_compatible_bricks(self,
                              model: type[CremeEntity] | None = None,
                              ) -> Iterator[Brick]:
        """Returns the registered bricks that are configurable and
        compatible with the given ContentType.
        @param model: Constraint on a CremeEntity class ;
               <None> means bricks must be compatible with all kind of CremeEntity.
        """
        for brick_cls in self._brick_classes.values():
            brick = brick_cls()

            if (brick.configurable
                    and hasattr(brick, 'detailview_display')
                    and (not brick.target_ctypes or model in brick.target_ctypes)):
                yield brick

        for rbi in RelationBrickItem.objects.select_related('relation_type'):
            brick = SpecificRelationsBrick(rbi)

            if not brick.target_ctypes or model in brick.target_ctypes:
                yield brick

        for ibi in InstanceBrickConfigItem.objects.all():
            brick = self.get_brick_4_instance(ibi)

            if (
                hasattr(brick, 'detailview_display')
                and (not brick.target_ctypes or model in brick.target_ctypes)
            ):
                yield brick

        if model:
            yield self.get_brick_4_object(model)

            for cbci in CustomBrickConfigItem.objects.filter(
                content_type=ContentType.objects.get_for_model(model),
            ):
                yield CustomBrick(cbci.brick_id, cbci)
        else:
            yield EntityBrick()

    def get_compatible_hat_bricks(self, model: type[CremeEntity]) -> Iterator[Brick]:
        yield self.get_generic_hat_brick(model)

        for brick_id, brick_cls in self._hat_brick_classes[model].items():
            if brick_id:  # Only generic hat brick's ID is empty
                yield brick_cls()

    def get_compatible_home_bricks(self) -> Iterator[Brick]:
        method_name = 'home_display'

        for brick_cls in self._brick_classes.values():
            brick = brick_cls()

            if brick.configurable and hasattr(brick, method_name):
                yield brick

        for ibi in InstanceBrickConfigItem.objects.all():
            brick = self.get_brick_4_instance(ibi)

            if hasattr(brick, method_name):
                yield brick

    def is_model_invalid(self, model: type[CremeEntity]) -> bool:
        "See register_invalid_model()."
        return model in self._invalid_models


brick_registry = BrickRegistry()


# def __getattr__(name):
#     if name == '_BrickRegistry':
#         warnings.warn(
#             '"_BrickRegistry" is deprecated; use "BrickRegistry" instead.',
#             DeprecationWarning,
#         )
#         return BrickRegistry
#
#     if name == 'BricksManager':
#         warnings.warn(
#             '"BricksManager" is deprecated; use "BrickManager" instead.',
#             DeprecationWarning,
#         )
#         return BrickManager
#
#     raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
