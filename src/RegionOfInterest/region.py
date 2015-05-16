# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = 'Sindre Nistad'

from warnings import warn
from Common.common import strip_and_add_space, list_to_string


class ROI(object):
    """
    A class to store the information of a single region of interest, along with some handy methods.
    """

    def __init__(self, name, sub_name, rgb, num_points, points=None):
        """
            A object to hold the information on a region of interest.
        :param name:        The full name of the region of interest.
        :param rgb:         The rgb color of the region, as given by the ROI file
        :param num_points:  The number of points that are in the region
        :param points:      A list of the actual points of the region. If no points are given, an empty list is created.

        :type name:         str
        :type rgb:          list of [int]
        :type num_points:   int
        :type points:       list of [Point]

        :return:
        """
        self.name = name
        """ :type : str """
        self.sub_name = sub_name
        """ :type : str """
        self.rgb = rgb
        """ :type : list[int] """
        self.num_points = num_points
        """ :type : int """
        self.sorted_mode = ""
        """ :type: str """
        if points is None:
            self.points = []
            """ :type : list[Point] """
        else:
            self.points = points
            """ :type : list[Point] """

    def sort(self, mode):
        """
            A method to sort the points according to x-y coordinates relative to the (actual) image, or relative to the
            map coordinates, or the points can be sorted according to latitude, and longitude.
            The points are first sorted by x/latitude, and then by y/longitude.
        :param mode:    The mode of sorting. Can be 'map', 'lat-long', or 'x-y'.
        :type mode:     str
        :return:        None
        :rtype:         None
        """
        if mode == 'map':
            expression = lambda p: (p.map_X, p.map_Y)
        elif mode == 'lat-long' or mode == 'latitude-longitude' or mode == 'latlong':
            expression = lambda p: (p.latitude, p.longitude)
        elif mode == 'xy' or mode == 'x-y':
            expression = lambda p: (p.X, p.Y)
        else:
            warn("No valid mode selected")
            return -1
        self.points = sorted(self.points, key=expression)
        self.sorted_mode = mode

    def add_point(self, point):
        """
            Adds the given point to the list of points in the region of interest.
        :param point:   The point we want to add
        :type point:    Point
        :return:        None
        :rtype:         None
        """
        self.points.append(point)
        self.sorted_mode = ""  # Because the points are likely to be in some disorder after adding one or more points.

    def export_to_csv(self, return_val=False, delimiter=",", path=None):
        """
            Creates a 'CSV' file where all the information in the ROI object is stored.
            Format: "NAME, SUB_NAME, (R, G, B), ID, X, Y, MAP_X, MAP_Y, LATITUDE, LONGITUDE, BAND 1, ..., BAND n"
        :param return_val:  Toggles, whether or not the function is return the string, or save it to a file. The
                            default is to save it to a file.
        :param delimiter:   What character the values are separated by. Default is ','
        :param path:        The path to the file in which the values are to be stored. If the path is not given, it
                            will store the file as "NAME_SUB_NAME.csv"
        :type delimiter:    str
        :type path:         str
        :type return_val:   bool
        :return:            If return_val is set to False, the method returns nothing, instead it writes it to a file.
                            If return_val is set to True, it returns a string of what would have been written to file.
        :rtype:             None | str

        """
        delimiter = strip_and_add_space(delimiter)
        if not return_val:
            if path is not None:
                file_name = path
            else:
                file_name = self.name + "_" + self.sub_name + ".csv"
            f = open(file_name, 'w')
        result_string = ""
        pre = self.name + delimiter + self.sub_name + delimiter + str(self.rgb[0]) + delimiter + \
              str(self.rgb[2]) + delimiter + str(self.rgb[2]) + delimiter
        for point in self.points:
            prefix = pre + str(point.identity) + delimiter + str(point.X) + delimiter + str(point.Y) + delimiter + \
                     str(point.map_X) + delimiter + str(point.map_Y) + delimiter + \
                     str(point.latitude) + delimiter + str(point.longitude)

            point_string = prefix + delimiter + point.get_bands_as_string(delimiter) + '\n'
            result_string += point_string
        if return_val:
            return result_string
        else:
            print(result_string, file=f)

    def __len__(self):
        return len(self.points)


def select_params(mode='x-y'):
    """
        Gives the 'x'-parameter, and 'y'-parameter that correspond with the given mode.
    :param mode:
    :return:
    """
    if mode == 'x-y':
        x_param = 'X'
        y_param = 'Y'
    elif mode == 'map':
        x_param = 'map_X'
        y_param = 'map_Y'
    elif mode == 'lat-long':
        x_param = 'latitude'
        y_param = 'longitude'
    else:
        raise Exception("The mode of the bounding box is incorrect. Must be 'x-y', 'map', or 'lat-long'.")
    return x_param, y_param


class BasePoint(object):
    """
    Stores the information (location) of a single point along with the spectral bands. This is a 'simple' point that
    only has id, longitude, and latitude, as well as the spectrum
    """

    def __init__(self, identity, latitude, longitude, bands, region_id=-1, dataset_id=-1):
        """
            A object to hold, and organize the relevant information for a specific point in the data set.
        :param identity:    An id, unique to the ROI polygon at creation in ENVI. Not used
        :param latitude:    The absolute latitude of the point.
        :param longitude:   The absolute longitude of the point.
        :param bands:       A list of the different spectral bands for the point.
        :param region_id:   Optional:   The id for the region the point belongs to. Default is -1, indicating that it
                                        has not been set.
        :param dataset_id:  Optional:   The id for the dataset the point belongs to. Default is -1, indicating that it
                                        has not been set.
        :type identity:     int
        :type latitude:     float
        :type longitude:    float
        :type bands:        list[float]
        :type region_id:    int
        :type dataset_id:   int
        :return:
        """
        self.identity = int(identity)
        """ :type : int """
        self.latitude = latitude
        """ :type : float """
        self.longitude = longitude
        """ :type : float """
        self.bands = bands
        """ :type : list[float] """
        self.region_id = region_id
        """ :type : int """
        self.dataset_id = dataset_id
        """ :type : int """

    def get_bands_as_string(self, delimiter=","):
        """
            Returns a single string of the value of all the bands in this point.
        :param delimiter:   What character the values are separated by.
        :type delimiter:    str
        :return:            String of bands
        :rtype:             str
        """
        return list_to_string(self.bands, delimiter)

    def __len__(self):
        return len(self.bands)


class Point(BasePoint):
    """
    More specific information is stored, such as relative image location and such
    """

    def __init__(self, identity, x, y, map_x, map_y, latitude, longitude, bands, region_id=-1, dataset_id=-1):
        """
            A object to hold, and organize the relevant information for a specific point in the data set.
        :param identity:    An id, unique to the ROI polygon at creation in ENVI. Not used
        :param x:           The (absolute) x location in the original image.
        :param y:           The (absolute) y location in the original image.
        :param map_x:       The x coordinate in the map.
        :param map_y:       The y coordinate in the map.
        :param latitude:    The absolute latitude of the point.
        :param longitude:   The absolute longitude of the point.
        :param bands:       A list of the different spectral bands for the point.
        :param region_id:   Optional:   The id for the region the point belongs to. Default is -1, indicating that it
                                        has not been set.
        :param dataset_id:  Optional:   The id for the dataset the point belongs to. Default is -1, indicating that it
                                        has not been set.
        :type identity:     int
        :type x:            int
        :type y:            int
        :type map_x:        float
        :type map_y:        float
        :type latitude:     float
        :type longitude:    float
        :type bands:        list[float]
        :type region_id:    int
        :type dataset_id:   int
        :return:
        """
        super(Point, self).__init__(identity, latitude, longitude, bands, region_id, dataset_id)
        self.identity = int(identity)
        self.X = int(x)
        """ :type : int """
        self.Y = int(y)
        """ :type : int """
        self.map_X = map_x
        """ :type : float """
        self.map_Y = map_y
        """ :type : float """


