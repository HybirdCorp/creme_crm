# -*- coding: utf-8 -*-

import os
import re
import pywbxml
from optparse import make_option, OptionParser

from django.core.management.base import BaseCommand

from activesync.wbxml.converters import WBXMLToXML


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-f", "--wbxmlfile", action="store", dest="filename"),
        make_option("-d", "--directory", action="store", dest="directory"),
    )

    def handle(self, *args, **options):
        filename  = options.get('filename')
        directory = options.get('directory')
        
        if filename is not None:
            try:
                source = open(filename, 'rb')
                target_filename = "%s.xml" % filename
                target_path = os.path.join(filename.rpartition(os.sep)[0], target_filename)
                dest   = open(target_path, 'w')

                dest.write(str(WBXMLToXML(source.read())))

            except Exception, e:
                print e
            else:
                source.close()
                dest.close()

        elif directory is not None:
            for f in os.listdir(directory):
#                if re.match(r'^\w*\.bin$', f):
                try:
                    source = open(os.path.join(directory, f), 'rb')
                    target_filename = "%s.xml" % f
                    target_path = os.path.join(directory, target_filename)
                    dest   = open(target_path, 'w')
                    dest.write(str(WBXMLToXML(source.read())))

                except Exception, e:
                    print "Invalid :", target_path
                    os.remove(target_path)
                else:
                    source.close()
                    dest.close()






