# -*- coding: utf-8 -*-

from persons.models import Civility, StaffSize, LegalForm, Sector, Position


to_register = ((Position,  'position'),
               (Sector,    'sector'),
               (LegalForm, 'legal_form'),
               (StaffSize, 'staff_size'),
               (Civility,  'civility'),
              )
