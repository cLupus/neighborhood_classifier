# -*- coding: utf-8 -*-
"""
In this file, all the communication between the main program, and the database is handled.
"""

from __future__ import division

import pony.orm as pny
from pony.orm import db_session

from Database.database_definition import db, Color, Dataset, Norm, Point, Region, Spectrum, Wavelengths, bind
from Common.parameters import WAVELENGTHS
from Common.common import get_one_indexed, is_in_name


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
def roi_to_database(roi, add_wavelengths=False, debug=False, force_load=False, commit_at_end=True):
    """
        Writes the content of a region of interest to the database
    :param roi:             The region of interest to be written to the database
    :param add_wavelengths: Toggle whether or not information about wavelengths is to be added. Default is False,
                            as it takes quite a while, and is not strictly necessary.
    :param debug:           Toggle whether or not debug information is to be written to the console. Default is False
    :param force_load:      Toggle whether or not the actual data in the regions of interest is to be read. Default is
                            False
    :param commit_at_end:   Toggles whether or not all the changes are to be committed at the end. Default is False.
    :type roi:              RegionsOfInterest
    :type add_wavelengths:  bool
    :type debug:            bool
    :type force_load:       bool
    :type commit_at_end:    bool
    :return:                None
    :rtype:                 None
    """
    # Splits the path by '/', and then '.', and then extracts the name
    dataset_name = roi.path.split('/')[-1].split('.')[0]
    # :type : str
    spectral_type = ""
    if add_wavelengths:
        if is_in_name('AVIRIS', roi.path):
            spectral_type = 'AVIRIS'
        elif is_in_name('MASTER', roi.path):
            spectral_type = 'MASTER'
    if dataset_name not in pny.select(d.name for d in Dataset):
        dataset = add_dataset(dataset_name, spectral_type)
        if not roi.is_loaded:
            print("Now loading the dataset located at " + roi.path)
            roi.load_data()
            rois = roi.get_all()
            print("Loading complete. Now exporting to database.")
    else:
        dataset = pny.get(d for d in Dataset if d.name == dataset_name)
        if force_load:
            print("Now loading the dataset located at " + roi.path)
            rois = roi.get_all(force_load=True)
            print("Loading complete. Now exporting to database.")
        else:
            rois = roi.get_all(force_load=False)  # An empty list []
    if debug:
        print("Adding normalizing data.")
    add_normalizing(roi, dataset, debug)
    if debug:
        print("Normalizing data added.")
    if debug:
        i = 0
        n = len(rois)
    for roi in rois:
        if pny.exists(r for r in Region if r.dataset == dataset and r.name == roi.name and r.sub_name == roi.sub_name):
            if debug:
                print("The point " + roi.name + "_" + roi.sub_name + " is already in the database. SKIPPING.")
                i += 1
            continue
        region = add_region(roi, dataset)
        for point in roi.points:
            # :type point: RegionOfInterest.region.Point
            p = add_point(region, point)
            add_spectrum(p, point.bands)
        if debug:
            i += 1
            print(region.name + " " + str(i / n * 100) + "% COMPLETE")
        if not commit_at_end:
            if debug:
                print("Committing point to the database.")
            db.commit()
            if debug:
                print("Commit completed.")
    if not pny.exists(wvl for wvl in Wavelengths if dataset in wvl.datasets):
        # Does the dataset have any wavelengths associated with its spectra?
        if add_wavelengths:
            if debug:
                print("Adding wavelength information to all points of the dataset")
                print("Spectral type is: " + spectral_type)
            # TODO: Check if this part is really necessary...
            add_wavelength_to_points(spectral_type, dataset)
        if debug:
            print("Committing changes to the database.")
    if commit_at_end:
        db.commit()
        if debug:
            print("Commit complete.")
    if debug:
        print("DONE!")


@db_session
def add_region(roi, dataset):
    """
        Adds the given region to the given data set
    :param roi:     The region of interest we would like to add
    :param dataset: The data set (e.g. MASTER r19) we would like to add the region to.
    :type roi:      RegionOfInterest.region.Region
    :type dataset:  Dataset
    :return:        None
    :rtype:         None
    """
    region = Region(dataset=dataset,
                    name=roi.name,
                    sub_name=roi.sub_name,
                    color=Color(red=roi.rgb[0], green=roi.rgb[1], blue=roi.rgb[2]))
    return region


@db_session
def add_point(region, point):
    """
       Adds the specified point to a region (of interest)
    :param region:  The region to which the point is added
    :param point:   The point which will be added
    :type region:   Database.database_definition.Region
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
    wavelengths = pny.select(wvl for wvl in Wavelengths if point.region.dataset.type == wvl.name)[:]
    for i in range(len(bands)):
        band = bands[i]
        Spectrum(value=band,
                 point=point,
                 band_nr=get_one_indexed(i),
                 wavelength=wavelengths[i])


@db_session
def add_wavelength_to_dataset(dataset, spectral_type, debug=False, commit_at_end=False):
    """
        Adds information about the spectral bands for the given dataset
    :param dataset:         The dataset to which the info is to be added.
    :param spectral_type:   What kind of spectra is it? (e.g. MASTER, or AVIRIS)
    :param commit_at_end:   Toggles whether or not all the changes are to be committed at the end. Default is False.
    :type dataset:          Database.database_definition.Dataset
    :type spectral_type:    str
    :type commit_at_end:    bool
    :return:
    """
    if debug:
        print("Adding wavelengths to dataset " + str(dataset) + ", having spectral type " + spectral_type)
    wavelengths = WAVELENGTHS[spectral_type]['wavelengths']
    unit = WAVELENGTHS[spectral_type]['unit']
    if pny.exists(wvl for wvl in Wavelengths if wvl.name == dataset.type):
        if debug:
            print("The wavelengths are already in the database, linking dataset to wavelengths")
        # Wavelengths already exists, so we want to add the dataset to the wavelengths
        for wavelength in pny.select(wvl for wvl in Wavelengths if wvl.name == dataset.name):
            wavelength.datasets.add(dataset)
            # TODO: Does this work at all?
    else:
        if debug:
            print("This is a new dataset for the database, generating wavelength information")
        for i in range(len(wavelengths)):
            wavelength = wavelengths[i]
            Wavelengths(name=spectral_type,
                        unit=unit,
                        wavelength=wavelength,
                        datasets=dataset,
                        band_nr=get_one_indexed(i))
    if not commit_at_end:
        db.commit()


@db_session
def add_wavelength_to_points(spectral_type, dataset, commit_at_end=False):
    """
        Adds the wavelength
    :param spectral_type:   The type of spectral data (MASTER/AVIRIS)
    :param dataset:         The dataset to which the wavelength information is to be added
    :param commit_at_end:   Toggles whether or not all the changes are to be committed at the end. Default is False.
    :type spectral_type:    str
    :type dataset:          Dataset
    :type commit_at_end:    bool
    :return:
    """
    # wavelengths = pny.select(w for w in Wavelengths if w.name == spectral_type).order_by(Wavelengths.band_nr)
    #wavelengths = wavelengths[:]  # Make it into a list
    spectralType = spectral_type
    datasetID = dataset.id
    stuff = db.execute(
        """
        SELECT spectrum.id, spectrum.band_nr, spectrum.value, spectrum.point
        FROM spectrum, point, region, dataset
        WHERE spectrum.point = point.id AND
        point.region = region.id AND
        region.dataset = $datasetID;
        """)
    for (spectrumID, bandNR, value, point) in stuff:
        db.execute(
            """
            UPDATE spectrum SET wavelength = $bandNR
            WHERE id = (SELECT id FROM wavelengths
                        WHERE name = $spectralType AND band_nr = $bandNR)
            """)
    if not commit_at_end:
        db.commit()


@db_session
def add_normalizing(roi, dataset, debug=False):
    """
        Adds the normalizing data (max, min, mean, std) to the dataset.
    :param roi:     The regions of interest that are contained in the given dataset.
    :param dataset: The dataset to witch we wish to add normalizing data.
    :type roi:      RegionOfInterest.regions_of_interest.RegionsOfInterest
    :type dataset:  Dataset
    :return:
    """
    if pny.exists(norm for norm in Norm if dataset == norm.dataset):
        if debug:
            print("The normalization information is already added to this dataset. SKIPPING")
        return
    for i in range(roi.num_bands):
        Norm(dataset=dataset,
             band_nr=get_one_indexed(i),
             maximum=roi.maximums[i],
             minimum=roi.minimums[i],
             mean=roi.means[i],
             std_dev=roi.standard_deviations[i])
    db.commit()


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
    ds = Dataset(name=name, type=spectral_type)
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

