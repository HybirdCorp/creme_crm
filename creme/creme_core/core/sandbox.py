# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2021  Hybird
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
from typing import Dict, Optional, Type

from creme.creme_core.models import Sandbox

logger = logging.getLogger(__name__)


class SandboxType:
    id: str = ''  # Override with generate_id()
    verbose_name: str = 'SANDBOX'  # Override or create a property (see below)

    @staticmethod
    def generate_id(app_label: str, name: str) -> str:
        return f'{app_label}-{name}'

    def __init__(self, sandbox: Sandbox):
        self.sandbox: Sandbox = sandbox

    # Example of property to override the class attribute 'verbose_name'
    #  (when the verbose name needs to use the related sandbox's data)
    # @property
    # def verbose_name(self):
    #     return f'Restricted to "{self.sandbox.user}"'


class _SandboxTypeRegistry:
    class Error(Exception):
        pass

    def __init__(self):
        self._sandbox_types: Dict[str, Type[SandboxType]] = {}

    def register(self, sandbox_type: Type[SandboxType]):
        sandbox_id = sandbox_type.id

        if not sandbox_id:
            raise self.Error(f'SandBox class with empty id: {sandbox_type}')

        if self._sandbox_types.setdefault(sandbox_id, sandbox_type) is not sandbox_type:
            raise self.Error(f'Duplicated sandbox type id: {sandbox_id}')

    def get(self, sandbox: Sandbox) -> Optional[SandboxType]:
        try:
            cls = self._sandbox_types[sandbox.type_id]
        except KeyError:
            logger.critical('Unknown SandboxType: %s', sandbox.type_id)
        else:
            return cls(sandbox)

        return None


sandbox_type_registry = _SandboxTypeRegistry()
