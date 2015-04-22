# -*- coding: utf-8 -*-
__author__ = 'Sindre Nistad'

from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL

import pony.orm as pony

from Database.create_database import create_database


import settings


def db_connect():
    """
        Performs Database connection using Database settings from settings.py.
        Returns sqlalchemy engine instance
    :return:    A Database engine
    :rtype:     Engine
    """
    return create_engine(URL(**settings.DATABASE))


def create_tables(overwrite=False, debug=True):
    """
        Creates all the tables necessary for the regions of interest to be in the Database. If 'overwrite' is set to
        True, then, if there is any previous databases with the same name as in settings.py, it will be dropped.
    :return:
    """
    create_database(overwrite=overwrite, debug=debug)