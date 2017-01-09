# -*- coding: utf-8 -*-

from . import blocks, models


to_register = ((models.Position,  'position'),
               (models.Sector,    'sector'),
               (models.LegalForm, 'legal_form'),
               (models.StaffSize, 'staff_size'),
               (models.Civility,  'civility'),
              )
portalblocks_to_register = (blocks.managed_orgas_block, )
