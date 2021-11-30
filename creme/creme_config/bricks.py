# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
from collections import defaultdict

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core import setting_key
from creme.creme_core.core.entity_filter import EF_USER
from creme.creme_core.forms import base as base_forms
from creme.creme_core.gui.bricks import (
    Brick,
    BricksManager,
    PaginatedBrick,
    QuerysetBrick,
    brick_registry,
)
from creme.creme_core.gui.button_menu import button_registry
from creme.creme_core.gui.custom_form import (
    FieldGroupList,
    customform_descriptor_registry,
)
from creme.creme_core.gui.fields_config import fields_config_registry
from creme.creme_core.gui.menu import ContainerEntry, menu_registry
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    BrickMypageLocation,
    ButtonMenuItem,
    CremeEntity,
    CremeModel,
    CremePropertyType,
    CustomBrickConfigItem,
    CustomField,
    CustomFieldEnumValue,
    CustomFormConfigItem,
    EntityFilter,
    FieldsConfig,
    HeaderFilter,
    HistoryConfigItem,
    InstanceBrickConfigItem,
    MenuConfigItem,
    RelationBrickItem,
    RelationType,
    SearchConfigItem,
    SemiFixedRelationType,
    SettingValue,
    UserRole,
)
from creme.creme_core.registry import creme_registry
from creme.creme_core.utils.content_type import entity_ctypes
from creme.creme_core.utils.unicode_collation import collator

from . import constants

# _PAGE_SIZE = 20
_PAGE_SIZE = 50
User = get_user_model()
logger = logging.getLogger(__name__)


class ExportButtonBrick(Brick):
    id_ = Brick.generate_id('creme_config', 'transfer_buttons')
    verbose_name = _('Export & import configuration')
    template_name = 'creme_config/bricks/transfer-buttons.html'
    configurable = False

    def detailview_display(self, context):
        return self._render(self.get_template_context(context))


class GenericModelBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('creme_config', 'model_config')
    verbose_name = 'Model configuration'
    dependencies = (CremeModel,)
    page_size = _PAGE_SIZE
    template_name = 'creme_config/bricks/configurable-model.html'
    configurable = False

    # NB: credentials are OK : we are sure to use the custom reloading view
    #     because of the specific constructor.
    def __init__(self, app_name, model_config):
        super().__init__()
        self.app_name = app_name
        self.model_config = model_config

    def detailview_display(self, context):
        model_config = self.model_config
        model = model_config.model
        meta = model._meta

        # TODO: (must declare in the template what fields can be used to sort)
        # ordering = meta.ordering
        # if ordering:
        #     self.order_by = ordering[0]

        displayable_fields = []
        is_reorderable = False

        for field in meta.fields:
            fieldname = field.name.lower()

            if fieldname == 'is_custom':
                continue
            elif fieldname == 'order':
                is_reorderable = True
            else:
                displayable_fields.append(field)

        displayable_fields.extend(meta.many_to_many)

        return self._render(self.get_template_context(
            context,
            model.objects.all(),

            model=model,
            meta=meta,

            app_name=self.app_name,
            model_config=model_config,

            model_is_reorderable=is_reorderable,
            displayable_fields=displayable_fields,
        ))


class SettingsBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('creme_config', 'settings')
    verbose_name = 'App settings'
    dependencies = (SettingValue,)
    page_size = _PAGE_SIZE
    template_name = 'creme_config/bricks/setting-values.html'
    configurable = False
    order_by = 'id'

    setting_key_registry = setting_key.setting_key_registry

    def detailview_display(self, context):
        app_name = context['app_name']
        skeys_ids = [
            skey.id
            for skey in self.setting_key_registry
            if skey.app_label == app_name and not skey.hidden
        ]

        return self._render(self.get_template_context(
            context,
            SettingValue.objects.filter(key_id__in=skeys_ids),
            app_name=app_name,
        ))


class _ConfigAdminBrick(QuerysetBrick):
    page_size = _PAGE_SIZE
    # The portals can be viewed by all users => reloading can be done by all users too.
    # permission = ''
    configurable = False


class PropertyTypesBrick(_ConfigAdminBrick):
    id_ = _ConfigAdminBrick.generate_id('creme_config', 'property_types')
    verbose_name = _('Types of property')
    dependencies = (CremePropertyType,)
    order_by = 'text'
    template_name = 'creme_config/bricks/property-types.html'

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            CremePropertyType.objects.annotate(stats=Count('cremeproperty')),
        ))


class RelationTypesBrick(_ConfigAdminBrick):
    id_ = _ConfigAdminBrick.generate_id('creme_config', 'relation_types')
    verbose_name = _('Standard types of relation')
    dependencies = (RelationType,)
    template_name = 'creme_config/bricks/relation-types.html'

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            RelationType.objects.filter(
                is_custom=False,
                pk__contains='-subject_',
            ),
            custom=False,
        ))


class CustomRelationTypesBrick(_ConfigAdminBrick):
    id_ = _ConfigAdminBrick.generate_id('creme_config', 'custom_relation_types')
    verbose_name = _('Custom types of relation')
    dependencies = (RelationType,)
    template_name = 'creme_config/bricks/relation-types.html'

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            RelationType.objects.filter(
                is_custom=True,
                pk__contains='-subject_',
            ),
            custom=True,
        ))


class SemiFixedRelationTypesBrick(_ConfigAdminBrick):
    id_ = _ConfigAdminBrick.generate_id('creme_config', 'semifixed_relation_types')
    verbose_name = _('Semi-fixed types of relationship')
    dependencies = (RelationType, SemiFixedRelationType,)
    template_name = 'creme_config/bricks/semi-fixed-relation-types.html'

    def detailview_display(self, context):
        btc = self.get_template_context(
            context, SemiFixedRelationType.objects.all(),
        )

        CremeEntity.populate_real_entities(
            [sfrt.object_entity for sfrt in btc['page'].object_list]
        )

        return self._render(btc)


class FieldsConfigsBrick(PaginatedBrick):
    id_ = PaginatedBrick.generate_id('creme_config', 'fields_configs')
    verbose_name = 'Fields configuration'
    dependencies = (FieldsConfig,)
    page_size = _PAGE_SIZE
    template_name = 'creme_config/bricks/fields-configs.html'
    # permission = None  # NB: used by the view creme_core.views.bricks.reload_basic()
    configurable = False

    fields_config_registry = fields_config_registry

    def detailview_display(self, context):
        # TODO: exclude CTs that user cannot see ?
        #       (should probably be done everywhere in creme_config...)
        fconfigs = [*FieldsConfig.objects.all()]
        sort_key = collator.sort_key
        fconfigs.sort(key=lambda fconf: sort_key(str(fconf.content_type)))

        used_models = {fconf.content_type.model_class() for fconf in fconfigs}
        is_model_valid = FieldsConfig.objects.has_configurable_fields
        registry = self.fields_config_registry
        btc = self.get_template_context(
            context, fconfigs,
            display_add_button=any(
                model not in used_models
                # for model in filter(FieldsConfig.objects.is_model_valid, apps.get_models())
                for model in filter(is_model_valid, registry.models)
            ),
        )

        for fconf in btc['page'].object_list:
            # vnames = [str(f.verbose_name) for f in fconf.hidden_fields]
            # vnames.sort(key=sort_key)
            #
            # fconf.fields_vnames = vnames
            hidden_vnames = [str(f.verbose_name) for f in fconf.hidden_fields]
            hidden_vnames.sort(key=sort_key)
            fconf.hidden_fields_vnames = hidden_vnames

            required_vnames = [str(f.verbose_name) for f in fconf.required_fields]
            required_vnames.sort(key=sort_key)
            fconf.required_fields_vnames = required_vnames

            # TODO: method ?
            model = fconf.content_type.model_class()
            fconf.is_valid = registry.is_model_registered(model) and is_model_valid(model)

        return self._render(btc)


class CustomFieldsBrick(Brick):
    id_ = Brick.generate_id('creme_config', 'custom_fields')
    verbose_name = 'Configuration of custom fields'
    dependencies = (CustomField,)
    template_name = 'creme_config/bricks/custom-fields.html'
    # permission = None  # NB: used by the view creme_core.views.bricks.reload_basic
    configurable = False

    def detailview_display(self, context):
        # NB: we wrap the ContentType instances instead of store extra data in
        #     them because the instances are stored in a global cache, so we do
        #     not want to mutate them.
        class _ContentTypeWrapper:
            __slots__ = ('ctype', 'cfields')

            def __init__(self, ctype, cfields):
                self.ctype = ctype
                self.cfields = cfields

        cfields = CustomField.objects.order_by('id').annotate(
            enum_count=Count('customfieldenumvalue_set'),
        )

        hide_deleted = BricksManager.get(context).get_state(
            brick_id=self.id_,
            user=context['user'],
        ).get_extra_data(constants.BRICK_STATE_HIDE_DELETED_CFIELDS)
        if hide_deleted:
            cfields = cfields.exclude(is_deleted=True)

        enums_types = {CustomField.ENUM, CustomField.MULTI_ENUM}
        for cfield in cfields:
            cfield.is_enum = (cfield.field_type in enums_types)   # TODO: templatetag instead ?

        # ------
        cfields_per_ct_id = defaultdict(list)
        for cfield in cfields:
            cfields_per_ct_id[cfield.content_type_id].append(cfield)

        get_ct = ContentType.objects.get_for_id
        ctypes = [
            _ContentTypeWrapper(get_ct(ct_id), ct_cfields)
            for ct_id, ct_cfields in cfields_per_ct_id.items()
        ]

        return self._render(self.get_template_context(
            context,
            ctypes=ctypes,
            hide_deleted=hide_deleted,
        ))


class CustomEnumsBrick(_ConfigAdminBrick):
    id_ = _ConfigAdminBrick.generate_id('creme_config', 'custom_enums')
    verbose_name = 'Custom-field choices'
    dependencies = (CustomFieldEnumValue,)
    order_by = 'id'  # TODO: 'value' ? a new field 'order' ?
    template_name = 'creme_config/bricks/custom-enums.html'

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            CustomFieldEnumValue.objects.filter(custom_field=context['custom_field']),
        ))


class CustomFormsBrick(PaginatedBrick):
    id_ = _ConfigAdminBrick.generate_id('creme_config', 'custom_forms')
    verbose_name = 'Custom forms'
    dependencies = (CustomFormConfigItem,)
    template_name = 'creme_config/bricks/custom-forms.html'
    page_size = _PAGE_SIZE
    configurable = False

    registry = customform_descriptor_registry

    error_field_blocks = {
        FieldGroupList.BLOCK_ID_MISSING_FIELD:        _('Missing required field: {}'),
        FieldGroupList.BLOCK_ID_MISSING_CUSTOM_FIELD: _('Missing required custom field: {}'),
        FieldGroupList.BLOCK_ID_MISSING_EXTRA_FIELD:  _('Missing required special field: {}'),
    }

    def get_ctype_descriptors(self, user, expanded_ctype_id):
        get_ct = ContentType.objects.get_for_model

        # class _ExtendedDescriptor:
        class _ExtendedConfigItem:
            # def __init__(this, descriptor, item):
            def __init__(this, *, item, descriptor):
                this._descriptor = descriptor
                this._item = item
                this.groups = descriptor.groups(item)
                # this.id = descriptor.id
                this.id = item.id

                # this.verbose_name = descriptor.verbose_name
                # TODO: factorise with CustomFormConfigItemChoiceField
                if item.superuser:
                    this.verbose_name = _('Form for super-user')
                elif item.role:
                    this.verbose_name = gettext('Form for role «{role}»').format(role=item.role)
                else:
                    this.verbose_name = _('Default form')

            @property
            def can_be_deleted(self):
                item = self._item

                return item.superuser or item.role_id

            @property
            def has_extra_groups(this):
                # TODO: descriptor.method ?
                return bool(next(this._descriptor.extra_group_classes, None))

            @property
            def errors(this):
                errors = []
                form_cls = this._descriptor.build_form_class(this._item)

                try:
                    blocks = form_cls(user=user).get_blocks()
                except Exception:
                    logger.exception(
                        'Error while building the form for "%s" '
                        '(in order to retrieve erroneous fields)',
                        form_cls,
                    )
                else:
                    for block_id, error_msg in self.error_field_blocks.items():
                        try:
                            errors_block = blocks[block_id]
                        except KeyError:
                            pass
                        else:
                            errors.extend(
                                error_msg.format(field.label)
                                for field in errors_block.bound_fields
                            )

                return errors

        class _ExtendedDescriptor:
            def __init__(this, *, descriptor, items):
                this.id = descriptor.id
                this.verbose_name = descriptor.verbose_name
                this.items = sorted(
                    (
                        _ExtendedConfigItem(item=item, descriptor=descriptor)
                        for item in items
                    ),
                    key=this._item_sort_key,
                )

            @staticmethod
            def _item_sort_key(ext_item):
                item = ext_item._item

                if item.superuser:
                    return 1, ''

                if item.role:
                    return 2, item.role.name

                return 0, ''

        desc_per_model = defaultdict(list)
        for desc in self.registry:
            desc_per_model[desc.model].append(desc)

        # items = CustomFormConfigItem.objects.in_bulk(
        #     descriptor.id
        #     for descriptors in desc_per_model.values()
        #     for descriptor in descriptors
        # )
        items_per_desc = defaultdict(list)
        for cfci in CustomFormConfigItem.objects.filter(
            descriptor_id__in=[
                descriptor.id
                for descriptors in desc_per_model.values()
                for descriptor in descriptors
            ],
        ).select_related('role'):
            items_per_desc[cfci.descriptor_id].append(cfci)

        class _ContentTypeWrapper:
            __slots__ = ('ctype', 'descriptors', 'collapsed')

            def __init__(this, model, descriptors):
                this.ctype = ctype = get_ct(model)
                # TODO: manage default item not created?
                # this.descriptors = [
                #     _ExtendedDescriptor(descriptor=desc, item=items[desc.id])
                #     for desc in descriptors
                # ]
                this.descriptors = [
                    _ExtendedDescriptor(
                        descriptor=descriptor, items=items_per_desc[descriptor.id],
                    ) for descriptor in descriptors
                ]
                this.collapsed = (expanded_ctype_id != ctype.id)

        wrappers = [
            _ContentTypeWrapper(model=model, descriptors=descriptors)
            for model, descriptors in desc_per_model.items()
        ]
        sort_key = collator.sort_key
        wrappers.sort(key=lambda wrp: sort_key(str(wrp.ctype)))

        return wrappers

    def detailview_display(self, context):
        user = context['user']

        expanded_ctype_id = BricksManager.get(context).get_state(
            brick_id=self.id_, user=user,
        ).get_extra_data(constants.BRICK_STATE_SHOW_CFORMS_DETAILS)

        return self._render(self.get_template_context(
            context,
            self.get_ctype_descriptors(user=user, expanded_ctype_id=expanded_ctype_id),
            LAYOUT_REGULAR=base_forms.LAYOUT_REGULAR,
            LAYOUT_DUAL_FIRST=base_forms.LAYOUT_DUAL_FIRST,
            LAYOUT_DUAL_SECOND=base_forms.LAYOUT_DUAL_SECOND,

            # NB: '+ 2' is for default config + super-users config.
            max_conf_count=UserRole.objects.count() + 2,
        ))


class UsersBrick(_ConfigAdminBrick):
    id_ = _ConfigAdminBrick.generate_id('creme_config', 'users')
    verbose_name = _('Users')
    dependencies = (User,)
    order_by = 'username'
    template_name = 'creme_config/bricks/users.html'

    def detailview_display(self, context):
        users = User.objects.filter(is_team=False)

        if not context['user'].is_staff:
            users = users.exclude(is_staff=True)

        hide_inactive = BricksManager.get(context).get_state(
            brick_id=self.id_,
            user=context['user'],
        ).get_extra_data(constants.BRICK_STATE_HIDE_INACTIVE_USERS)
        if hide_inactive:
            users = users.exclude(is_active=False)

        btc = self.get_template_context(context, users, hide_inactive=hide_inactive)
        page = btc['page']
        page_users = page.object_list
        TIME_ZONE = settings.TIME_ZONE
        btc['display_tz'] = (
            any(user.time_zone != TIME_ZONE for user in page_users)
            # All users are displayed if our page
            if page.paginator.count == len(page_users) else
            User.objects.exclude(time_zone=TIME_ZONE).exists()
        )

        return self._render(btc)


class TeamsBrick(_ConfigAdminBrick):
    id_ = _ConfigAdminBrick.generate_id('creme_config', 'teams')
    verbose_name = _('Teams')
    dependencies = (User,)
    order_by = 'username'
    template_name = 'creme_config/bricks/teams.html'

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context, User.objects.filter(is_team=True),
        ))


class BrickDetailviewLocationsBrick(PaginatedBrick):
    id_ = PaginatedBrick.generate_id('creme_config', 'blocks_dv_locations')
    verbose_name = 'Blocks locations on detailed views'
    dependencies = (BrickDetailviewLocation,)
    # '-1' because there is always the line for default config on each page
    page_size = _PAGE_SIZE - 1
    template_name = 'creme_config/bricks/bricklocations-detailviews.html'
    # permission = None  # NB: used by the view creme_core.views.blocks.reload_basic
    configurable = False

    brick_registry = brick_registry

    def detailview_display(self, context):
        # NB: we wrap the ContentType instances instead of store extra data in
        #     them because the instances are stored in a global cache, so we do
        #     not want to mutate them.
        class _ContentTypeWrapper:  # TODO: move from here ?
            __slots__ = ('ctype', 'locations_info', 'default_count')

            def __init__(this, ctype):
                this.ctype = ctype
                this.default_count = 0
                # List of tuples (role_arg, role_label, brick_count)
                # with <role_arg == role.id> or 'superuser'
                this.locations_info = ()

        # TODO: factorise with SearchConfigBrick ?
        # TODO: factorise with CustomBrickConfigItemCreateForm, add a method in brick_registry ?
        get_ct = ContentType.objects.get_for_model
        is_invalid = self.brick_registry.is_model_invalid
        ctypes = [
            _ContentTypeWrapper(get_ct(model))
            for model in creme_registry.iter_entity_models()
            if not is_invalid(model)
        ]

        sort_key = collator.sort_key
        ctypes.sort(key=lambda ctw: sort_key(str(ctw.ctype)))

        btc = self.get_template_context(
            context, ctypes,
            max_conf_count=UserRole.objects.count() + 1,  # NB: '+ 1' is for super-users config.
        )

        ctypes_wrappers = btc['page'].object_list

        # brick_counts[content_type.id][(role_id, superuser)] -> count
        brick_counts = defaultdict(lambda: defaultdict(int))
        role_ids = set()

        for bdl in BrickDetailviewLocation.objects.filter(
            content_type__in=[ctw.ctype for ctw in ctypes_wrappers],
        ).exclude(zone=BrickDetailviewLocation.HAT):
            # Do not count the 'place-holder'
            # (empty block IDs which mean "no-block for this zone")
            if bdl.brick_id:
                role_id = bdl.role_id
                brick_counts[bdl.content_type_id][(role_id, bdl.superuser)] += 1
                role_ids.add(role_id)

        role_names = dict(UserRole.objects.filter(id__in=role_ids).values_list('id', 'name'))
        superusers_label = gettext('Superuser')  # TODO: cached_lazy_gettext

        for ctw in ctypes_wrappers:
            count_per_role = brick_counts[ctw.ctype.id]
            ctw.default_count = count_per_role.pop((None, False), 0)

            ctw.locations_info = locations_info = []
            for (role_id, superuser), block_count in count_per_role.items():
                if superuser:
                    role_arg = 'superuser'
                    role_label = superusers_label
                else:
                    role_arg = role_id
                    role_label = role_names[role_id]

                locations_info.append((role_arg, role_label, block_count))

            locations_info.sort(key=lambda t: sort_key(t[1]))  # Sort by role label

        btc['default_count'] = BrickDetailviewLocation.objects.filter(
            content_type=None,
            role=None, superuser=False,
        ).count()

        return self._render(btc)


class BrickHomeLocationsBrick(_ConfigAdminBrick):
    id_ = _ConfigAdminBrick.generate_id('creme_config', 'blocks_home_locations')
    verbose_name = _('Blocks on home')
    dependencies = (BrickHomeLocation,)
    template_name = 'creme_config/bricks/bricklocations-home.html'

    def detailview_display(self, context):
        superuser_count = BrickHomeLocation.objects.filter(superuser=True).count()

        btc = self.get_template_context(
            context,
            UserRole.objects.exclude(brickhomelocation=None)
                            .order_by('name')
                            .annotate(bricks_count=Count('brickhomelocation')),
            superuser_count=superuser_count,
            empty_configs={
                'superuser' if superuser else (role or 'default')
                for role, superuser in BrickHomeLocation.objects
                                                        .filter(brick_id='')
                                                        .values_list('role', 'superuser')
            },
        )

        # NB: lambda => lazy
        btc['get_default_count'] = lambda: BrickHomeLocation.objects.filter(
            role=None, superuser=False,
        ).count()

        paginator = btc['page'].paginator
        btc['show_add_button'] = (
            (UserRole.objects.count() > paginator.count)
            or (superuser_count == 0)
        )

        # NB: the UserRole queryset count does not use the default & superuser configuration
        paginator.count += 1 + min(superuser_count, 1)

        return self._render(btc)


class BrickDefaultMypageLocationsBrick(_ConfigAdminBrick):
    id_ = _ConfigAdminBrick.generate_id('creme_config', 'blocks_default_mypage_locations')
    verbose_name = _('Blocks on default «My page»')
    dependencies = (BrickMypageLocation,)
    template_name = 'creme_config/bricks/bricklocations-mypage-default.html'

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            BrickMypageLocation.objects.filter(user=None),
        ))


class BrickMypageLocationsBrick(_ConfigAdminBrick):
    id_ = _ConfigAdminBrick.generate_id('creme_config', 'blocks_mypage_locations')
    verbose_name = _('Blocks on «My page»')
    dependencies = (BrickMypageLocation,)
    template_name = 'creme_config/bricks/bricklocations-mypage-user.html'

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            BrickMypageLocation.objects.filter(user=context['user']),
        ))


class RelationBricksConfigBrick(_ConfigAdminBrick):
    id_ = _ConfigAdminBrick.generate_id('creme_config', 'relation_blocks_config')
    verbose_name = 'Relation blocks configuration'
    dependencies = (RelationBrickItem, BrickDetailviewLocation)
    template_name = 'creme_config/bricks/relationbricks-configs.html'
    order_by = 'relation_type__predicate'

    def detailview_display(self, context):
        # TODO: prefetch symmetric types
        return self._render(self.get_template_context(
            context, RelationBrickItem.objects.prefetch_related('relation_type'),
        ))


class InstanceBricksConfigBrick(_ConfigAdminBrick):
    id_ = _ConfigAdminBrick.generate_id('creme_config', 'instance_blocks_config')
    verbose_name = _("Instances' blocks")
    dependencies = (InstanceBrickConfigItem,)
    template_name = 'creme_config/bricks/instancebricks-configs.html'

    def detailview_display(self, context):
        btc = self.get_template_context(
            context,
            InstanceBrickConfigItem.objects.prefetch_related('entity'),
        )

        CremeEntity.populate_real_entities(
            [ibci.entity for ibci in btc['page'].object_list]
        )

        return self._render(btc)


class CustomBricksConfigBrick(PaginatedBrick):
    id_ = _ConfigAdminBrick.generate_id('creme_config', 'custom_blocks_config')
    verbose_name = _('Custom blocks')
    dependencies = (CustomBrickConfigItem,)
    template_name = 'creme_config/bricks/custombricks-configs.html'
    page_size = _PAGE_SIZE
    # The portals can be viewed by all users => reloading can be done by all users too.
    # permission = ''
    configurable = False

    def detailview_display(self, context):
        # NB: we wrap the ContentType instances instead of store extra data in
        #     them because teh instances are stored in a global cache, so we do
        #     not want to mutate them.
        class _ContentTypeWrapper:  # TODO: move from here ?
            __slots__ = ('ctype', 'items')

            def __init__(this, ctype, items):
                this.ctype = ctype
                this.items = items

        cbi_per_ctid = defaultdict(list)

        for cb_item in CustomBrickConfigItem.objects.order_by('name'):
            cbi_per_ctid[cb_item.content_type_id].append(cb_item)

        get_ct = ContentType.objects.get_for_id
        ctypes = [
            _ContentTypeWrapper(get_ct(ct_id), cb_items)
            for ct_id, cb_items in cbi_per_ctid.items()
        ]

        sort_key = collator.sort_key
        ctypes.sort(key=lambda ctw: sort_key(str(ctw.ctype)))

        btc = self.get_template_context(context, ctypes)
        # TODO: better way to pre-populate FieldsConfig, CustomFields, RelationTypes...
        #       when we get several groups un de-serialized EntityCells
        FieldsConfig.objects.get_for_models(
            [ctype_wrapper.ctype.model_class() for ctype_wrapper in btc['page'].object_list],
        )  # NB: regroup/prefetch queries on FieldsConfig (we bet that regular fields will be used)

        return self._render(btc)


class MenuBrick(Brick):
    id_ = Brick.generate_id('creme_config', 'menu')
    verbose_name = _('Menu configuration')
    dependencies = (MenuConfigItem,)
    template_name = 'creme_config/bricks/menu-config.html'
    configurable = False

    menu_registry = menu_registry

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            entries=self.menu_registry.get_entries(MenuConfigItem.objects.all()),
            container_id=ContainerEntry.id,
        ))


class ButtonMenuBrick(Brick):
    id_ = Brick.generate_id('creme_config', 'button_menu')
    verbose_name = 'Button menu configuration'
    dependencies = (ButtonMenuItem,)
    template_name = 'creme_config/bricks/button-menu.html'
    configurable = False

    button_registry = button_registry

    def get_buttons(self):
        default_buttons = []
        buttons_map = defaultdict(list)

        get_button = self.button_registry.get_button

        for bmi in ButtonMenuItem.objects.order_by('order'):
            if bmi.content_type is not None:
                _button_list = buttons_map[bmi.content_type]
            else:
                _button_list = default_buttons

            button = get_button(bmi.button_id)
            if button is not None:
                _button_list.append({
                    'label': str(bmi),
                    'description': str(button.description)
                })

        sort_key = collator.sort_key
        buttons = sorted(buttons_map.items(), key=lambda t: sort_key(str(t[0])))

        return default_buttons, buttons

    def detailview_display(self, context):
        default_buttons, buttons = self.get_buttons()

        return self._render(self.get_template_context(
            context,
            default_buttons=default_buttons,
            buttons=buttons,
        ))


class SearchConfigBrick(PaginatedBrick):
    id_ = PaginatedBrick.generate_id('creme_config', 'searchconfig')
    verbose_name = 'Search configuration'
    dependencies = (SearchConfigItem,)
    template_name = 'creme_config/bricks/search-config.html'
    order_by = 'content_type'
    page_size = _PAGE_SIZE * 2  # Only one brick
    configurable = False

    def detailview_display(self, context):
        # NB: we wrap the ContentType instances instead of store extra data in
        #     them because teh instances are stored in a global cache, so we do
        #     not want to mutate them.
        class _ContentTypeWrapper:  # TODO: move from here ?
            __slots__ = ('ctype', 'sc_items')

            def __init__(this, ctype):
                this.ctype = ctype
                this.sc_items = ()

        ctypes = [_ContentTypeWrapper(ctype) for ctype in entity_ctypes()]
        sort_key = collator.sort_key
        ctypes.sort(key=lambda ctw: sort_key(str(ctw.ctype)))

        btc = self.get_template_context(
            context, ctypes,
            # NB: '+ 2' is for default config + super-users config.
            max_conf_count=UserRole.objects.count() + 2,
        )

        ctypes_wrappers = btc['page'].object_list

        sci_map = defaultdict(list)
        for sci in SearchConfigItem.objects.filter(
            content_type__in=[ctw.ctype for ctw in ctypes_wrappers],
        ).select_related('role'):
            sci_map[sci.content_type_id].append(sci)

        superusers_label = gettext('Superuser')

        for ctw in ctypes_wrappers:
            ctype = ctw.ctype
            ctw.sc_items = sc_items = sci_map.get(ctype.id) or []
            sc_items.sort(
                key=lambda sci: sort_key(
                    str(sci.role) if sci.role
                    else superusers_label if sci.superuser
                    else ''
                ),
            )

            if not sc_items or not sc_items[0].is_default:  # No default config -> we build it
                SearchConfigItem.objects.create(content_type=ctype)

        return self._render(btc)


class HistoryConfigBrick(_ConfigAdminBrick):
    id_ = _ConfigAdminBrick.generate_id('creme_config', 'historyconfig')
    verbose_name = 'History configuration'
    dependencies = (HistoryConfigItem,)
    template_name = 'creme_config/bricks/history-config.html'
    order_by = 'relation_type__predicate'

    def detailview_display(self, context):
        return self._render(self.get_template_context(context, HistoryConfigItem.objects.all()))


class UserRolesBrick(_ConfigAdminBrick):
    id_ = _ConfigAdminBrick.generate_id('creme_config', 'user_roles')
    verbose_name = _('Roles')
    dependencies = (UserRole,)
    order_by = 'name'
    template_name = 'creme_config/bricks/user-roles.html'

    def detailview_display(self, context):
        return self._render(self.get_template_context(context, UserRole.objects.all()))


class UserSettingValuesBrick(Brick):
    id_ = QuerysetBrick.generate_id('creme_config', 'user_setting_values')
    verbose_name = _('Setting values')
    # dependencies  = (User,) ??
    template_name = 'creme_config/bricks/user-setting-values.html'
    configurable = False

    user_setting_key_registry = setting_key.user_setting_key_registry

    def detailview_display(self, context):
        # NB: credentials OK: user can only view his own settings
        u_settings = context['user'].settings
        sv_info_per_app = defaultdict(list)
        get_app_config = apps.get_app_config
        count = 0

        for skey in self.user_setting_key_registry:
            if skey.hidden:
                continue

            info = {
                'description': skey.description_html,
                'key_id':      skey.id,
            }

            try:
                info['value'] = u_settings.as_html(skey)
            except KeyError:
                info['not_set'] = True

            sv_info_per_app[skey.app_label].append(info)
            count += 1

        return self._render(self.get_template_context(
            context,
            values_per_app=[
                (get_app_config(app_label).verbose_name, svalues)
                for app_label, svalues in sv_info_per_app.items()
            ],
            count=count,
        ))


class EntityFiltersBrick(PaginatedBrick):
    id_ = PaginatedBrick.generate_id('creme_config', 'entity_filters')
    verbose_name = 'All entity filters'
    dependencies = (EntityFilter,)
    page_size = _PAGE_SIZE
    template_name = 'creme_config/bricks/entity-filters.html'
    configurable = False

    def detailview_display(self, context):
        # NB: we wrap the ContentType instances instead of store extra data in
        #     them because the instances are stored in a global cache, so we do
        #     not want to mutate them.
        class _ContentTypeWrapper:
            __slots__ = ('ctype', 'all_users_filters', 'owned_filters')

            def __init__(this, ctype):
                this.ctype = ctype
                this.all_users_filters = ()
                this.owned_filters = ()

        # TODO: factorise with SearchConfigBrick ?
        get_ct = ContentType.objects.get_for_model
        user = context['user']
        has_perm = user.has_perm_to_access
        ctypes = [
            _ContentTypeWrapper(get_ct(model))
            for model in creme_registry.iter_entity_models()
            if has_perm(model._meta.app_label)
        ]

        sort_key = collator.sort_key
        ctypes.sort(key=lambda ctw: sort_key(str(ctw.ctype)))

        btc = self.get_template_context(context, ctypes)

        ctypes_wrappers = btc['page'].object_list

        # NB: efilters[content_type.id][user.id] -> List[EntityFilter]
        efilters = defaultdict(lambda: defaultdict(list))
        user_ids = set()

        for efilter in EntityFilter.objects.filter(
            filter_type=EF_USER,
            entity_type__in=[ctw.ctype for ctw in ctypes_wrappers],
        ):
            # TODO: templatetags instead ?
            efilter.edition_perm = efilter.can_edit(user)[0]
            efilter.deletion_perm = efilter.can_delete(user)[0]

            user_id = efilter.user_id
            efilters[efilter.entity_type_id][user_id].append(efilter)
            user_ids.add(user_id)

        users = get_user_model().objects.in_bulk(user_ids)

        def efilter_key(efilter):
            return sort_key(efilter.name)

        for ctw in ctypes_wrappers:
            ctype_efilters_per_users = efilters[ctw.ctype.id]

            all_users_filters = ctype_efilters_per_users.pop(None, None) or []
            all_users_filters.sort(key=efilter_key)

            ctw.all_users_filters = all_users_filters

            ctw.owned_filters = [
                (
                    str(users[user_id]),
                    sorted(user_efilters, key=efilter_key),
                ) for user_id, user_efilters in ctype_efilters_per_users.items()
            ]

        return self._render(btc)


# TODO: factorise
class HeaderFiltersBrick(PaginatedBrick):
    id_ = PaginatedBrick.generate_id('creme_config', 'header_filters')
    verbose_name = 'All views of list'
    dependencies = (HeaderFilter,)
    page_size = _PAGE_SIZE
    template_name = 'creme_config/bricks/header-filters.html'
    configurable = False

    def detailview_display(self, context):
        # NB: we wrap the ContentType instances instead of store extra data in
        #     them because the instances are stored in a global cache, so we do
        #     not want to mutate them.
        class _ContentTypeWrapper:
            __slots__ = ('ctype', 'all_users_hfilters', 'owned_hfilters')

            def __init__(this, ctype):
                this.ctype = ctype
                this.all_users_hfilters = ()
                this.owned_hfilters = ()

        # # TODO: factorise with SearchConfigBrick ?
        get_ct = ContentType.objects.get_for_model
        user = context['user']
        has_perm = user.has_perm_to_access
        ctypes = [
            _ContentTypeWrapper(get_ct(model))
            for model in creme_registry.iter_entity_models()
            if has_perm(model._meta.app_label)
        ]

        sort_key = collator.sort_key
        ctypes.sort(key=lambda ctw: sort_key(str(ctw.ctype)))

        btc = self.get_template_context(context, ctypes)

        ctypes_wrappers = btc['page'].object_list

        # NB: hfilters[content_type.id][user.id] -> List[HeaderFilter]
        hfilters = defaultdict(lambda: defaultdict(list))
        user_ids = set()

        for hfilter in HeaderFilter.objects.filter(
            # filter_type=EF_USER,
            entity_type__in=[ctw.ctype for ctw in ctypes_wrappers],
        ):
            # TODO: templatetags instead ?
            hfilter.edition_perm = hfilter.can_edit(user)[0]
            hfilter.deletion_perm = hfilter.can_delete(user)[0]

            user_id = hfilter.user_id
            hfilters[hfilter.entity_type_id][user_id].append(hfilter)
            user_ids.add(user_id)

        users = get_user_model().objects.in_bulk(user_ids)

        def hfilter_key(efilter):
            return sort_key(efilter.name)

        for ctw in ctypes_wrappers:
            ctype_hfilters_per_users = hfilters[ctw.ctype.id]

            all_users_filters = ctype_hfilters_per_users.pop(None, None) or []
            all_users_filters.sort(key=hfilter_key)

            ctw.all_users_hfilters = all_users_filters

            ctw.owned_hfilters = [
                (
                    str(users[user_id]),
                    sorted(user_hfilters, key=hfilter_key),
                ) for user_id, user_hfilters in ctype_hfilters_per_users.items()
            ]

        return self._render(btc)
