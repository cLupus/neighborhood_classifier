# -*- coding: utf-8 -*-
"""
The export from Pony ORM to create a PostgreSQL Database
"""

__author__ = 'Sindre Nistad'

from pony.orm import db_session

from Database.database_definition import Point, Color, Dataset, db, Norm, Region, Spectrum

@db_session
def roi_to_database(rois):
    """
        Writes the content of a region of interest to the database
    :param rois:    The region of interest to be written to the database
    :type rois:     RegionsOfInterest
    :return:        None
    :rtype:         None
    """
    # Splits the path by '/', and then '.', and then extracts the name
    dataset_name = rois.path.split('/')[-1].split('.')[0]
    dataset = add_dataset(dataset_name)
    add_normalizing(rois, dataset)
    for roi in rois.get_all():
        region = add_region(roi, dataset)
        for point in roi.points:
            # :type point: RegionOfInterest.region.Point
            p = add_point(region, point)
            # TODO: Implement wavelengths
            add_spectrum(p, point.bands)
    db.commit()


@db_session
def add_region(roi, dataset):
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
    #region.points.
    #region.points.add(p)
    return p


@db_session
def add_spectrum(point, bands):
    """
        Adds the given spectrum (the list of bands) to the given point
    :param point:   A point in a region, to which we wish to add a spectral bands
    :param bands:   The spectrum, as discrete bands
    :type point:    Point
    :type bands:    list of [float]
    :return:        None
    :rtype:         None
    """
    for i in range(len(bands)):
        band = bands[i]
        #point.add(Spectrum(value=band, point=point))
        Spectrum(value=band, point=point, band_nr=i)


@db_session
def add_wavelength(point):
    # TODO: Implement
    """

    :param point:
    """
    pass


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
             band_nr=i,
             maximum=rois.maximums[i],
             minimum=rois.minimums[i],
             mean=rois.means[i],
             std_dev=rois.standard_deviations[i])


@db_session
def add_dataset(name):
    return db.Dataset(name=name)


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