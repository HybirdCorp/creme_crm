# -*- coding: utf-8 -*-

from . import bricks, models


to_register = ((models.Position,  'position'),
               (models.Sector,    'sector'),
               (models.LegalForm, 'legal_form'),
               (models.StaffSize, 'staff_size'),
               (models.Civility,  'civility'),
              )
portalbricks_to_register = (bricks.ManagedOrganisationsBrick,)
