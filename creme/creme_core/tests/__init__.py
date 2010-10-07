# -*- coding: utf-8 -*-

from unittest import TestLoader, TestSuite

import utils
import models
import views


def suite():
    loadtests = TestLoader().loadTestsFromModule

    return TestSuite([loadtests(module) for module in (utils, models, views)])
