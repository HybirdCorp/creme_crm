################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

from creme.creme_core.core import cloning, copying


class Spawner(cloning.EntityCloner):
    """A specific subclass of Cloners made to spawn Invoice/Quote/... from a
    TemplateBase instance.
    """
    post_save_copiers = [
        # NB: useless in vanilla code
        copying.ManyToManyFieldsCopier,  # TODO: unit test
        copying.StrongPropertiesCopier,
        copying.StrongRelationsCopier,

        # Does not mean anything to clone that (types are different).
        # CustomFieldsCopier,
    ]

    def _build_instance(self, *, user, source):
        spawn_cls = source.ct.model_class()
        return spawn_cls()


spawner_registry = cloning.EntityClonerRegistry()
