# -*- coding: utf-8 -*-
"""
In this file, all the communication between the main program, and the database is handled.
"""

from __future__ import division

import pony.orm as pny
from pony.orm import db_session

from Database.database_definition import db, Color, Dataset, Norm, Point, Region, Spectrum, Wavelengths, bind
from Common.parameters import WAVELENGTHS
from Common.common import get_one_indexed


__author__ = 'Sindre Nistad'


def db_connect():
    """
        Performs Database connection using Database settings from settings.py.
    :return:    A Database engine
    :rtype:     Engine
    """
    # return create_engine(URL(**settings.DATABASE))
    bind()
    return db.get_connection()


def create_tables(overwrite=False, debug=True):
    """
        Creates all the tables necessary for the regions of interest to be in the Database. If 'overwrite' is set to
        True, then, if there is any previous databases with the same name as in settings.py, it will be dropped.
    :return:
    """
    db.create_database(overwrite=overwrite, debug=debug)


@db_session
def roi_to_database(roi, add_wavelengths=False, debug=False):
    """
        Writes the content of a region of interest to the database
    :param roi:             The region of interest to be written to the database
    :param add_wavelengths: Toggle whether or not information about wavelengths is to be added. Default is False,
                            as it takes quite a while, and is not strictly necessary.
    :param debug:           Toggle whether or not debug information is to be written to the console. Default is False
    :type roi:              RegionsOfInterest
    :type add_wavelengths:  bool
    :type debug:            bool
    :return:                None
    :rtype:                 None
    """
    # Splits the path by '/', and then '.', and then extracts the name
    dataset_name = roi.path.split('/')[-1].split('.')[0]
    # :type : str
    if dataset_name in pny.select(d.name for d in Dataset):
        return
    spectral_type = ""
    if add_wavelengths:
        if 'AVIRIS' in dataset_name.upper():
            spectral_type = 'AVIRIS'
        elif 'MASTER' in dataset_name.upper():
            spectral_type = 'MASTER'
    dataset = add_dataset(dataset_name, spectral_type)
    add_normalizing(roi, dataset)
    if debug:
        i = 0
        n = len(roi.get_all())
    for roi in roi.get_all():
        region = add_region(roi, dataset)
        if debug:
            i += 1
            print(region.name + " " + str(i/n * 100) + "% COMPLETE")
        for point in roi.points:
            # :type point: RegionOfInterest.region.Point
            p = add_point(region, point)
            add_spectrum(p, point.bands)
    if add_wavelengths:
        if debug:
            print("Adding wavelength information to all points of the dataset")
        add_wavelength_to_points(spectral_type, dataset)
    if debug:
        print("Committing changes to the database.")
    db.commit()
    if debug:
        print("Commit complete.")


@db_session
def add_region(roi, dataset):
    """
        Adds the given region to the given data set
    :param roi:     The region of interest we would like to add
    :param dataset: The data set (e.g. MASTER r19) we would like to add the region to.
    :type roi:      Region
    :type dataset:  Dataset
    :return:        None
    :rtype:         None
    """
    name = roi.name
    sub_name = roi.sub_name
    region = Region(dataset=dataset, name=name)
    region.sub_name = sub_name
    color = Color(red=roi.rgb[0], green=roi.rgb[1], blue=roi.rgb[2])
    color.regions.add(region)
    region.color = color
    return region


@db_session
def add_point(region, point):
    """
       Adds the specified point to a region (of interest)
    :param region:  The region to which the point is added
    :param point:   The point which will be added
    :type region:   Region
    :type point:    RegionOfInterest.region.Point
    :return:        None
    :rtype:         None
    """
    xy_point = point_to_postgres_point(point.X, point.Y)
    relative_point = point_to_postgres_point(point.map_X, point.map_Y)
    lat_long = point_to_postgres_point(point.latitude, point.longitude)
    p = Point(local_location=xy_point, relative_location=relative_point,
              long_lat=lat_long, region=region)
    return p


@db_session
def add_spectrum(point, bands):
    """
        Adds the given spectrum (the list of bands) to the given point
    :param point:           A point in a region, to which we wish to add a spectral bands
    :param bands:           The spectrum, as discrete bands
    :type point:            Point
    :type bands:            list of [float]
    :return:                None
    :rtype:                 None
    """
    for i in range(len(bands)):
        band = bands[i]
        Spectrum(value=band,
                 point=point,
                 band_nr=get_one_indexed(i))


@db_session
def add_wavelength_to_dataset(dataset, spectral_type):
    """
        Adds information about the spectral bands for the given dataset
    :param dataset:         The dataset to which the info is to be added.
    :param spectral_type:   What kind of spectra is it? (e.g. MASTER, or AVIRIS)
    :type dataset:          Database.database_definition.Dataset
    :type spectral_type:    str
    :return:
    """
    wavelengths = WAVELENGTHS[spectral_type]['wavelengths']
    unit = WAVELENGTHS[spectral_type]['unit']
    for i in range(len(wavelengths)):
        wavelength = wavelengths[i]
        Wavelengths(name=spectral_type,
                    unit=unit,
                    wavelength=wavelength,
                    datasets=dataset,
                    band_nr=get_one_indexed(i))


@db_session
def add_wavelength_to_points(spectral_type, dataset):
    """
        Adds the wavelength
    :type spectral_type: str
    :return:
    """
    wavelengths = pny.select(w for w in Wavelengths if w.name == spectral_type).order_by(Wavelengths.band_nr)
    wavelengths = wavelengths[:]  # Make it into a list
    for spectrum in pny.select(s for s in Spectrum if s.point.region.dataset == dataset):
        spectrum.wavelength = wavelengths[spectrum.band_nr]

@db_session
def add_normalizing(rois, dataset):
    """
        Adds the normalizing data (max, min, mean, std) to the dataset.
    :param rois:    The regions of interest that are contained in the given dataset.
    :param dataset: The dataset to witch we wish to add normalizing data.
    :type rois:     RegionOfInterest.regions_of_interest.RegionsOfInterest
    :type dataset:  Dataset
    :return:
    """
    for i in range(rois.num_bands):
        Norm(dataset=dataset,
             band_nr=get_one_indexed(i),
             maximum=rois.maximums[i],
             minimum=rois.minimums[i],
             mean=rois.means[i],
             std_dev=rois.standard_deviations[i])


@db_session
def add_dataset(name, spectral_type=""):
    """
        Adds the given name to the database of main data sets. If a spectral type is given, e.g. MASTER, or AVIRIS, than
        it also adds the wavelengths of the given ''data type' to the data set.
    :param name:            The (full) name of the dataset that is to be added.
    :param spectral_type:   Specify the type of specter to be used (e.g. MASTER, or AVIRIS)
    :type name:             str
    :type spectral_type:    str
    :return:                The created Dataset object
    :rtype:                 Dataset
    """
    ds = Dataset(name=name)
    if spectral_type:
        add_wavelength_to_dataset(ds, spectral_type)
    return ds


"""
Methods for deleting stuff
"""


def remove_region(name, subname):
    pass
    # db.entities.


"""
Methods for getting stuff from the database
"""
# TODO


def point_to_postgres_point(*args):
    """
        Converts the list of numbers in 'args' to a Postgresql point. This is so that arbitrary
        dimensionality is supported
    :param args:    list of points to be converted
    :type args:     list of [float]
    :return:        A single string representing a point object in Postgres with the given coordinates.
    :rtype:         str
    """
    s = ""
    for elm in args:
        s += str(elm) + ', '
    s = s[:-2]  # Removes the last ", "
    return s

