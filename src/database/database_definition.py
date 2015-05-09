# -*- coding: utf-8 -*-
"""
This file contains all the information on how the database is defined, using Pony ORM
"""

__author__ = 'Sindre Nistad'

from pony.orm import *

from settings import DATABASE

db = Database()


class Wavelengths(db.Entity):
    """Where the information about a specific band/or wavelength reside; band number,
    and what wavelength, along with the unit of measurement, e.g. 700 nm."""
    id = PrimaryKey(int, auto=True)
    name = Required(str, 30, sql_type="varchar")
    unit = Required(str, 30, sql_type="varchar")
    wavelength = Required(float)
    datasets = Set("Dataset")
    band_nr = Required(int)
    spectra = Set("Spectrum")
    composite_key(name, band_nr)


class Point(db.Entity):
    """Where the single points reside, along with their spectral response/signature."""
    id = PrimaryKey(int, auto=True)
    local_location = Required(unicode, sql_type="Point")
    relative_location = Required(unicode, sql_type="Point")
    long_lat = Required(unicode, sql_type="Point")
    spectra = Set("Spectrum")
    region = Required("Region")


class Spectrum(db.Entity):
    """Where the actual spectral values reside"""
    id = PrimaryKey(int, auto=True)
    band_nr = Required(int)
    value = Required(float)
    wavelength = Optional(Wavelengths)
    point = Optional(Point)


class Region(db.Entity):
    """Where the regions of interest, and their point collections reside"""
    id = PrimaryKey(int, auto=True)
    dataset = Required("Dataset")
    name = Required(str, 60, sql_type="varchar")
    sub_name = Optional(str, 60, sql_type="varchar")
    color = Optional("Color")
    points = Set(Point)
    composite_key(dataset, name, sub_name)


class Color(db.Entity):
    """The color of a region in rgb values. Not strictly necessary, but might be of use when plotting."""
    id = PrimaryKey(int, auto=True)
    red = Required(float)
    green = Required(float)
    blue = Required(float)
    regions = Set(Region)


class Norm(db.Entity):
    """Normalizing data for the regions of interest"""
    id = PrimaryKey(int, auto=True)
    dataset = Required("Dataset")  # Not Set because the actual normalizing might be different from frame to frame.
    band_nr = Required(int)
    maximum = Required(float)
    minimum = Required(float)
    mean = Required(float)
    std_dev = Required(float)


class Dataset(db.Entity):
    """The data set from which all the regions comes from."""
    id = PrimaryKey(int, auto=True)
    name = Required(str, 200, unique=True, sql_type="varchar")
    type = Required(str, 10, sql_type="varchar")
    regions = Set(Region, cascade_delete=True)
    norms = Set(Norm, cascade_delete=True)
    wavelengths = Set(Wavelengths)


def bind(create_tables=False):
    """
        Binds the database using the standard settings found in the variable DATABASE
    :param create_tables:   Toggles whether or not the tables will be created when binding. Default is False.
                            Useful when debugging
    :type create_tables:    bool
    :return:                None
    :rtype:                 None
    """
    bind_database(create_tables=create_tables, **DATABASE)


def bind_database(check_tables=True, create_tables=False, **kwargs):
    """
        Binds the database to the given information.
    :param check_tables:    Sets the flag 'check_tables' for the generate_mapping method.
    :param create_tables:   Sets the flag 'create_tables' for the generate_mapping method.
    :param kwargs:  Expects the following values: 'drivername', 'host' , 'port', 'username', 'password', and 'database'
    :type check_tables:     bool
    :type create_tables:    bool
    :type kwargs:           dict of [str, str]
    :return:
    """
    driver = kwargs['drivername']
    host = kwargs['host']
    port = kwargs['port']
    user = kwargs['username']
    password = kwargs['password']
    database = kwargs['database']
    if driver == 'postgresql' or driver == 'postgres':
        db.bind('postgres', user=user, password=password, host=host, port=port, database=database)
    else:
        raise NotImplementedError("Only Postgresql back-end has been implemented.")
    db.generate_mapping(check_tables=check_tables, create_tables=create_tables)


def create_database(overwrite=False, debug_sql=True, check_tables=True, create_tables=False):
    """
        Creates a database with the database settings from settings.py
    :param overwrite:       Toggle whether or not the database should be dropped, if it already exists. Default is
                            False.
    :param debug_sql:       Toggle debug_sql mode. Default is True.
    :param check_tables:    Sets the flag 'check_tables' for the generate_mapping method.
    :param create_tables:   Sets the flag 'create_tables' for the generate_mapping method.
    :type overwrite:        bool
    :type debug_sql:        bool
    :type check_tables:     bool
    :type create_tables:    bool
    :return:                The database that has been generated
    :rtype:                 Database
    """
    sql_debug(debug_sql)
    bind_database(check_tables, create_tables, **DATABASE)
    if overwrite:
        drop_tables(True)
    db.create_tables(check_tables=check_tables)
    return db


def drop_tables(are_you_sure=False):
    """
        Drops all the data in the database!
    :param are_you_sure:    Are you really sure you want to drop the database? Added, so that dropping the database
                            does not happen by accident.
    :type are_you_sure:     bool
    """
    if are_you_sure:
        db.drop_all_tables(with_all_data=True)
        db.drop_all_tables()