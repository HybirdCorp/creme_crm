# -*- coding: utf-8 -*-

from persons.models import Civility, StaffSize, LegalForm, Sector, PeopleFunction


to_register = ((PeopleFunction, 'people_function'),
               (Sector,         'sector'),
               (LegalForm,      'legal_form'),
               (StaffSize,      'staff_size'),
               (Civility,       'civility'),)
