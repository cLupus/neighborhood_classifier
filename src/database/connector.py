# -*- coding: utf-8 -*-
"""
In this file, all the communication between the main program, and the database is handled.
"""

__author__ = 'Sindre Nistad'

from database import db


def db_connect():
    """
        Performs Database connection using Database settings from settings.py.
        Returns sqlalchemy engine instance
    :return:    A Database engine
    :rtype:     Engine
    """
    # return create_engine(URL(**settings.DATABASE))
    return db.get_connection()


def create_tables(overwrite=False, debug=True):
    """
        Creates all the tables necessary for the regions of interest to be in the Database. If 'overwrite' is set to
        True, then, if there is any previous databases with the same name as in settings.py, it will be dropped.
    :return:
    """
    db.create_database(overwrite=overwrite, debug=debug)
