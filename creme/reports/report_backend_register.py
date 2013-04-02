# -*- coding: utf-8 -*-

from .backends import HtmlReportBackend, CsvReportBackend

to_register = (('HTML', HtmlReportBackend), 
               ('CSV', CsvReportBackend),
              )
