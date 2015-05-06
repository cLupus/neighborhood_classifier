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
from RegionOfInterest.region import Point as ROIPoint


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


def get_points_from_region(region, dataset, k=0):
    # TODO: Implement
    """
        Returns all points, and its k nearest neighbors that are in a given region (can be general (only name),
        or specific (includes sub name). If k is not set explicitly, only the points themselves will be returned. k does
        not include the point itself.
        The dataset is a list, (or a single) data sets the points will be drawn from. If blank, or the list ['MASTER',
        'AVIRIS'], it will return every point which has the given region as name. If one of then, then all points in the
        region which are from the given spectrometer. A specific data set can also be specified, e.g. master_r19... in
        which case, only points in the given data set will be returned. Returns a list of lists of points.
    :param region:  The region points are taken from
    :param dataset: The dataset(s) the points are part of
    :param k:       The number of neighbors that are to be returned with the point. Default is 0; only the point itself.
    :type region:   str
    :type dataset:  list of [str]
    :type k:        int
    :return:        List of list of points, with their neighbors
    :rtype:         list of [list of [RegionOfInterest.region.Point]]
    """
    # Taking care of the names
    name = region.split('_')
    if '_' in region:
        # The region has a sub name, and we want to an extra constraint to the search
        sub_name = name[1]
        name = name[0]
    else:
        # The given name does not contain a sub-name.
        name = name[0]

    if dataset == "":
        # Give all from every dataset/collection
        pass
    elif 'MASTER' in dataset or 'AVIRIS' in dataset:
        # Give all points that are from the MASTER, and/or AVIRIS datasets
        pass
    else:
        # Give the points in the given dataset
        pass
        # TODO: Implement getting list of k-nearest neighbors


def get_nearest_neighbors_to_point(point, k, dataset, ignore_dataset=False, include_point=True, roi_point=True):
    """
        Returns the k-nearest neighbors for the given point. (This method will return k + 1 points in a
        list, as the given point will be included, unless include_point is set to False)
        If the ignore_dataset flag is set to True, we will not care about the points belonging to the same dataset.
    :param point:           The point we are interested in finding nearest neighbors to.
    :param k:               The number of nearest neighbors we want to find.
    :param dataset:         The dataset(s) we want to get the points from. Can be None, as it is not necessary when
                            ignore_dataset is True, but must be specified if ignore_dataset is True.
    :param ignore_dataset:  Toggles whether or not we will consider the dataset a point belongs to, when searching for
                            nearest neighbor, e.g. ignore to which sensor the data came from. Default is False.
    :param include_point:   Toggles whether or not the given point is to be included in the final list or not. Default
                            is True.
    :param roi_point:       Toggles whether or not the list that will be returned is a list of ROIPoints,
                            or Pony Points. Default is ROIPoints.
    :type point:            RegionOfInterest.region.Point | Point
    :type k:                int
    :type dataset:          list of [str] | str
    :type ignore_dataset:   bool
    :type include_point:    bool
    :return:                List of points sorted in ascending order by how close they are to the given point.
    :rtype:                 list of [RegionOfInterest.region.Point | Point]
    """
    if isinstance(point, Point):
        # TODO: Implement getting long, lat
        longitude = point.long_lat[0]
        latitude = point.long_lat[1]
    elif isinstance(point, ROIPoint):
        longitude = point.longitude
        latitude = point.latitude
    else:
        raise TypeError("The type for point is not supported. The type of point is ", type(point))
    select_from_sql = """
                    SELECT id, region, long_lat
                    FROM point"""
    order_by_query = "ORDER BY point.long_lat <-> '(" + str(longitude) + ", " + str(latitude) + ")'::point " \
                                                                                                "LIMIT " + str(k) + ";"
    # FIXME: will return the k first BANDS of the point
    if ignore_dataset:
        sql = select_from_sql + order_by_query
    else:
        if not isinstance(dataset, list):
            dataset = [dataset]
        dataset_sql = " AND ("
        if 'MASTER' in dataset or 'AVIRIS' in dataset:
            for elm in dataset:
                dataset_sql += "dataset.type = '" + elm + "' or "
            dataset_sql = dataset_sql[:-3]  # Removing the last 'or '
            dataset_sql += ")"
        else:
            for elm in dataset:
                dataset_sql += " dataset.name = '" + elm + "' or "
            dataset_sql = dataset_sql[:-3]  # Removing the last 'or '
            dataset_sql += ")"
        sql = select_from_sql + ", dataset WHERE " + dataset_sql + order_by_query
    query = db.execute(sql)
    points = []
    for elm in query:
        if roi_point:
            # TODO: Implement adding points to list
            pass
        pass
        # TODO: Implement adding given point to list


def query_to_point_list(query):
    """
        Takes a query of points (id, region, long_lat
    :param query:
    :return:
    """
    # TODO: Implement
    pass


def get_random_sample(area, number_of_samples, background=False):
    """
        Returns a random sample of number_of_samples points which lies in the given area (which may be regions, or a
        specific region when given a sub-name; e.g. name_sub-name, or just name for the value of area. If background
        is set to True, the resulting collection will be a random sample of anything but the given area.
    :param area:                Name of the region we want the sample to be from (or not from). If the underscore
                                character is in the name, it will be assumed as a sub-region,
                                e.i. sub_name will be given.
    :param number_of_samples:   The number of samples we want.
    :param background:          Toggles whether or not the returned set is from the actual region, or from the
                                'background' of that region, e.i. anything but that region.
    :type area:                 str
    :type number_of_samples:    int
    :type background:           bool
    :return:                    A list of points which constitutes a sample from the given region, or a list of points
                                constitutes a sample from the background of that region.
    :rtype:                     list of [RegionOfInterest.region.Point]
    """
    if '_' in area:
        name = area.split('_')[0]
        sub_name = area.split('_')[1]
    else:
        name = area
        sub_name = ""
    select_sql = "SELECT * FROM spectrum NATURAL JOIN point NATURAL JOIN region "
    # FIXME: Get spectrum later!
    if background:
        equal_operator = " != "
    else:
        equal_operator = " = "
    where_sql = " WHERE region.name" + equal_operator + "'" + name + "'"
    if sub_name != "":
        where_sql += " AND region.sub_name" + equal_operator + "'" + sub_name + "'"
    order_by_sql = " ORDER BY random() LIMIT " + str(number_of_samples) + ";"
    # TODO: Fix the random selection; according to StackOverflow, this is VERY slow (sorts the entire table).
    # There are remedies
    sql = select_sql + where_sql + order_by_sql
    query = db.execute(sql)
    return query_to_point_list(query)
    pass


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


def main():
    """
        The method that will run when the connector module is imported.
        Makes sure that the database is bounded.
    :return:
    """
    bind()