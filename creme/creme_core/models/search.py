# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import TextField, ForeignKey, BooleanField, Q, FieldDoesNotExist, CASCADE
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext_lazy

from ..utils import find_first
from ..utils.meta import FieldInfo, ModelFieldEnumerator
from .auth import UserRole
from .base import CremeModel
from .fields import EntityCTypeForeignKey, DatePeriodField


logger = logging.getLogger(__name__)


# TODO: store FieldInfo too/instead (see Searcher + creme_config form)
class SearchField(object):
    __slots__ = ('__name', '__verbose_name')

    def __init__(self, field_name, field_verbose_name): 
        self.__name = field_name
        self.__verbose_name = field_verbose_name

    def __unicode__(self):
        return self.__verbose_name

    @property
    def name(self):
        return self.__name

    @property
    def verbose_name(self):
        return self.__verbose_name


class SearchConfigItem(CremeModel):
    content_type = EntityCTypeForeignKey(verbose_name=_(u'Related resource'))
    role         = ForeignKey(UserRole, verbose_name=_(u'Related role'), null=True, default=None, on_delete=CASCADE)
    # TODO: a UserRole for superusers instead ??
    superuser    = BooleanField(u'related to superusers', default=False, editable=False)
    disabled     = BooleanField(pgettext_lazy('creme_core-search_conf', u'Disabled?'), default=False)
    field_names  = TextField(null=True)  # Do not this field directly; use 'searchfields' property

    creation_label = _(u'Create a search configuration')
    save_label     = _(u'Save the configuration')

    _searchfields = None
    EXCLUDED_FIELDS_TYPES = [models.DateTimeField, models.DateField,
                             models.FileField, models.ImageField,
                             BooleanField, models.NullBooleanField,
                             DatePeriodField,  # TODO: JSONField ?
                            ]

    class Meta:
        app_label = 'creme_core'
        unique_together = ('content_type', 'role', 'superuser')

    def __unicode__(self):
        if self.superuser:
            return ugettext(u'Search configuration of super-users for «{model}»').format(model=self.content_type)

        role = self.role

        if role is None:
            return ugettext(u'Default search configuration for «{model}»').format(model=self.content_type)

        return ugettext(u'Search configuration of «{role}» for «{model}»').format(
                    role=role,
                    model=self.content_type,
        )

    @property
    def all_fields(self):
        "@return True means that all fields are used."
        self.searchfields  # Computes self._all_fields
        return self._all_fields

    @property
    def is_default(self):
        "Is default configuration ?"
        return self.role_id is None and not self.superuser

    @staticmethod
    def _get_modelfields_choices(model):
        excluded = tuple(SearchConfigItem.EXCLUDED_FIELDS_TYPES)
        return ModelFieldEnumerator(model, deep=1) \
                .filter(viewable=True) \
                .exclude(lambda f, depth: isinstance(f, excluded) or f.choices) \
                .choices()

    def _build_searchfields(self, model, fields, save=True):
        sfields = []
        old_field_names = self.field_names

        for field_name in fields:
            try:
                field_info = FieldInfo(model, field_name)
            except FieldDoesNotExist as e:
                logger.warn('%s => SearchField removed', e)
            else:
                sfields.append(SearchField(field_name=field_name, field_verbose_name=field_info.verbose_name))

        self.field_names = ','.join(sf.name for sf in sfields) or None

        if not sfields:  # field_names is empty => use all compatible fields
            sfields.extend(SearchField(field_name=field_name, field_verbose_name=verbose_name)
                                for field_name, verbose_name in self._get_modelfields_choices(model)
                          )
            self._all_fields = True
        else:
            self._all_fields = False

        # We can pass the reference to this immutable collections (and SearchFields are hardly mutable).
        self._searchfields = tuple(sfields)

        if save and old_field_names != self.field_names:
            self.save()

    @property
    def searchfields(self):
        if self._searchfields is None:
            names = self.field_names
            self._build_searchfields(self.content_type.model_class(), names.split(',') if names else ())

        return self._searchfields

    @searchfields.setter
    def searchfields(self, fields):
        "@param fields Sequence of strings representing field names"
        self._build_searchfields(self.content_type.model_class(), fields, save=False)

    def get_modelfields_choices(self):
        """Return a list of tuples (useful for Select.choices) representing
        Fields that can be chosen by the user.
        """
        return self._get_modelfields_choices(self.content_type.model_class())

    @staticmethod
    def create_if_needed(model, fields, role=None, disabled=False):
        """Create a config item & its fields if one does not already exists.
        SearchConfigItem.create_if_needed(SomeDjangoModel, ['YourEntity_field1', 'YourEntity_field2', ..])
        @param fields Sequence of strings representing field names.
        @param role UserRole instance; or 'superuser'; or None, for default configuration.
        @param disabled Boolean
        """
        ct = ContentType.objects.get_for_model(model)
        superuser = False

        if role == 'superuser':
            superuser = True
            role = None
        elif role is not None:
            assert isinstance(role, UserRole)

        sci, created = SearchConfigItem.objects.get_or_create(content_type=ct,
                                                              role=role,
                                                              superuser=superuser,
                                                              defaults={'disabled': disabled},
                                                             )

        if created:
            sci._build_searchfields(model, fields)

        return sci

    @staticmethod
    def get_4_models(models, user):
        "Get the SearchConfigItem instances corresponding to the given models (generator)."
        get_ct = ContentType.objects.get_for_model
        ctypes = [get_ct(model) for model in models]

        role_query = Q(role__isnull=True)
        if user.is_superuser:
            role_query |= Q(superuser=True)
            filter_func = lambda sci: sci.superuser
        else:
            role = user.role
            role_query |= Q(role=role)
            filter_func = lambda sci: sci.role == role

# TODO: use a similar way if superuser is a role
#       (PG does not return a cool result if we do a ".order_by('role', 'superuser')")
#        sc_items = {sci.content_type: sci
#                        for sci in SearchConfigItem.objects
#                                                   .filter(content_type__in=ctypes)
#                                                   .filter(Q(user=user) | Q(user__isnull=True))
#                                                   .order_by('user') # Config of the user has higher priority than the default one
#                   }
#
#        for ctype in ctypes:
#            yield sc_items.get(ctype) or SearchConfigItem(content_type=ctype)
        sc_items_per_ctid = defaultdict(list)
        for sci in SearchConfigItem.objects.filter(content_type__in=ctypes).filter(role_query):
            sc_items_per_ctid[sci.content_type_id].append(sci)

        for ctype in ctypes:
            sc_items = sc_items_per_ctid.get(ctype.id)

            if sc_items:
                try:
                    yield find_first(sc_items, filter_func)
                except IndexError:
                    yield sc_items[0]
            else:
                yield SearchConfigItem(content_type=ctype)

    def save(self, *args, **kwargs):
        if self.superuser and self.role_id:
            raise ValueError('"role" must be NULL if "superuser" is True')

        super(SearchConfigItem, self).save(*args, **kwargs)
