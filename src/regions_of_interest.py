# -*- coding: utf-8 -*-
"""
Classes and methods for reading, and interpreting the data from a ASCII ROI file.
"""
__author__ = 'Sindre Nistad'
from warnings import warn
import sys

from common import get_histogram, extract_name
from data_management import read_data_from_file, read_normalizing_data


if sys.version_info.major == 2:
    from cPickle import dump, load, HIGHEST_PROTOCOL
elif sys.version_info.major == 3:
    from pickle import dump, load, HIGHEST_PROTOCOL


class RegionsOfInterest(object):
    """
        A holder/structure for the ROI file, as given by ENVI (in ASCII format)
    """
    def __init__(self, path, read_data=True, use_aggregate=True,
                 normalizing_path=None, mode='min-max', is_normalized=False):
        """
            Creates a RegionsOfInterest object, which is a collection of region on interest, each having a
            number of points in it. The default is to read the data at creation, and to use the aggregate
            name of the regions, e.g. 'rock' instead of 'rock_23'.
        :param path:            The path to either the ROI text file, or an already pickled RegionsOfInterest object.
        :param read_data:       Decides whether or not the data is to be read when the new RegionsOfInterest object
                                is created. The default is to read at creation.
        :param use_aggregate:   Decides whether or not you can refer to a region by its general name, e.g. 'rock', or
                                if you have to specify the entire name of the region e.g. 'rock_r43'. The default is
                                to use the aggregate.
        :param is_normalized:   Specify whether or not the input data is normalized or not. The default is not.
        :type path:             str
        :type read_data:        bool
        :type use_aggregate:    bool
        :type is_normalized:    bool
        """
        self.path = path
        """ :type : str """
        self.rois = {}
        """ :type : dict of [str, dict of [str, ROI]] """
        self.number_of_rois = 0
        """ :type : int """
        self.meta = ""
        """ :type : str """
        self.img_dim = []
        """ :type : list[int] """
        self.band_info = ""
        """ :type : list[str] """
        self.num_bands = 0
        """ :type : int"""
        self.histogram = None
        """ :type: dict of [str, int] """
        self.use_aggregate = use_aggregate
        """ :type : bool """
        self.is_normalized = is_normalized
        """ :type : bool """
        self.maximums = []
        """ :type : list[float] """
        self.minimums = []
        """ :type : list[float] """
        self.means = []
        """ :type : list[float] """
        self.standard_deviations = []
        """ :type : list[float] """

        if read_data:
            ending = self.path.split('.')[-1]
            if ending == 'pkl' or ending == 'pickle':
                self.load_roi_object(self.path)
            else:
                data = read_data_from_file(self.path)
                self.rois = data['rois']
                self.number_of_rois = data['number_of_rois']
                self.meta = data['meta']
                self.img_dim = data['img_dim']
                self.band_info = data['band_info']
                self.num_bands = data['num_bands']
        if normalizing_path is not None:
            data = read_normalizing_data(normalizing_path)
            self.maximums = data['maximums']
            self.minimums = data['minimums']
            self.means = data['means']
            self.standard_deviations = data['standard_deviations']
            self.normalize(mode)

    def load_roi_object(self, path):
        """
            Loads a pickled rois object into this one.
        :param path:    The path to the file you want to load.
        :return:        None
        """
        roi = load(open(path, 'rb'))
        assert isinstance(roi, RegionsOfInterest)
        self.path = roi.path
        self.rois = roi.rois
        self.number_of_rois = roi.number_of_rois
        self.meta = roi.meta
        self.img_dim = roi.img_dim
        self.band_info = roi.band_info
        self.num_bands = roi.num_bands
        self.use_aggregate = roi.use_aggregate
        self.is_normalized = roi.is_normalized

    def set_aggregate(self, val):
        """
            Sets the 'use_aggregate' filed to True, or False
        :param val:
        :type val: bool
        :return: None
        """
        assert isinstance(val, bool)
        self.use_aggregate = val

    def sort(self, mode):
        """
            Sorts all the regions of interest according to the give mode, which may be 'x-y', 'map', or 'lat-long'.
        :param mode:    What parameters do we sort on?
        :type mode:     str
        :return:        None
        :rtype:         None
        """
        for roi in self.rois:
            roi.sort(mode)

    def get_histogram(self):
        """
            Returns a dictionary of regions of interest, and how many points there is in each.
        :return:    Dictionary where the region of interest is the key, and the number of points
                    in that region is the value.
        :rtype:     dict of [str, int]
        """
        if self.histogram is None:
            targets = self.rois.keys()
            self.histogram = get_histogram(self.get_all(), targets)
        return self.histogram

    def save_to_file(self, filename):
        """
            Pickles the entire object to the specified file.
        :param filename:    The full name of the path/file name of the desired output file.
        :type filename:     str
        :return:            None
        :rtype:             None
        """
        with open(filename, 'wb') as output:
            dump(self, output, HIGHEST_PROTOCOL)

    def normalize(self, mode='min-max'):
        """
            Normalizes the data. Makes it simpler than the original normalize function, which takes a subtraction, and
            and a division parameter.
            The mode can be 'min-max', or gaussian.
        :param mode:    Specify the way the data can be normalized. At the moment, only min-max,
                        and gaussian normalization is supported.
        :type mode:     str
        :return:        None
        :rtype:         None
        """
        if mode is 'min-max' or 'max-min':
            assert self.minimums is not None
            assert self.maximums is not None
            self._normalize_min_max(self.minimums, self.maximums)
        elif mode is 'gaussian' or 'gauss':
            assert self.means is not None
            assert self.standard_deviations is not None
            self._normalize_gaussian(self.means, self.standard_deviations)

    def _normalize_gaussian(self, mean_param, std_dev_param):
        """
            A method to normalize the rois, as to make it more portable between images.
            The parameters must be per band
            Per now, the modes of normalizing is globally, and only min-max, and gaussian.
        :param mean_param:      The mean value of the data set
        :param std_dev_param:   The standard deviation of the data set.
        :type mean_param:       list[float]
        :type std_dev_param:    list[float]
        :return: None
        :rtype: None
        """
        if not len(mean_param) == self.num_bands and len(std_dev_param) == self.num_bands:
            raise Exception("The input parameters does not match the bands in the ROIs")
        for roi in self.get_all():
            for point in roi.points:
                for i in range(self.num_bands):
                    point.bands[i] = (point.bands[i] - mean_param[i]) / std_dev_param[i]
        self.is_normalized = True

    def _normalize_min_max(self, min_param, max_param):
        """
            A method to normalize the rois, as to make it more portable between images.
            The parameters must be per band
            Per now, the modes of normalizing is globally, and only min-max, and gaussian.
        :param min_param:   The minimum value of the data set.
        :param max_param:   The maximum value of the data set.
        :type min_param:    list[float]
        :type max_param:    list[float]
        :return: None
        :rtype: None
        """
        if not len(min_param) == self.num_bands and len(max_param) == self.num_bands:
            raise Exception("The input parameters does not match the bands in the ROIs")
        for roi in self.get_all():
            for point in roi.points:
                for i in range(self.num_bands):
                    point.bands[i] = (point.bands[i] - min_param[i]) / (max_param[i] - min_param[i])
        self.is_normalized = True

    def absolutize(self, sub_param, div_param, mode='min-max'):
        """
            Reverts what have been done when normalizing the data.
        :param sub_param:   The parameter that was subtracted when the data was normalized, e.g. minimum, or mean
        :param div_param:   The parameter that was used to divide the data, when it was normalized, e.g. maximum,
                            or std.dev.
        :param mode:        How the reversion should be done.
        :type sub_param:    list[float]
        :type div_param:    list[float]
        :type mode:         str
        :return:            None
        :rtype:             None
        """
        if not self.is_normalized:
            raise Exception("The data has to be normalized, if you want to revert the normalization!")
        for roi in self.rois:
            for point in roi.points:
                for i in range(self.num_bands):
                    point.bands[i] = point.bands[i] * div_param[i] + sub_param[i]

    def get_all(self):
        """
            A method to get all regions of interest as a list of regions
            :return:    A list of the regions of interest that are stored in this object.
            :rtype:     List of [ROI]
        """
        roi_list = []
        for key in self.rois.keys():
            for sub_key in self.rois[key]:
                roi_list.append(self.rois[key][sub_key])
        return roi_list

    def __getitem__(self, item):
        if self.use_aggregate:
            rois = self.rois[item]
            points = []
            for key in rois.keys():
                roi = rois[key]
                color = roi.rgb
                points += roi.points
            return ROI(item, "", color, len(points), points)
        else:
            name, sub_name = extract_name(item)
            return self.rois[name][sub_name]

    def __len__(self):
        return len(self.rois)


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
        self.sub_name = sub_name
        self.rgb = rgb
        self.num_points = num_points
        self.sorted_mode = ""
        """ :type: str """
        if points is None:
            self.points = []
        else:
            self.points = points

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

    def get_bounding_box(self, mode='x-y'):
        """
            Returns a bounding box (list of the extreme x/y values) for this region of interest.
            The list has the following format:
            [x_max, x_min, y_max, y_min]
        :param mode:    The mode of operation.
                        Can be:
                            'x-y'
                                for the bounding box relative to the image
                            'map'
                               for the bounding box where the coordinates are global
                            'lat-long'
                                for the bounding boc of the latitude and longitude.
        :return:        A bounding box for the region of interest polygon
        :rtype:         list of [int | float]
        """
        y_max = -float('Inf')
        y_min = float('Inf')
        x_max = -float('Inf')
        x_min = float('Inf')
        x_param, y_param = select_params(mode)
        for point in self.points:
            point_x = point.get_value(x_param)
            point_y = point.get_value(y_param)
            if point_x < x_min:
                x_min = point_x
            if point_x > x_max:
                x_max = point_x
            if point_y < y_min:
                y_min = point_y
            if point_y > y_max:
                y_max = point_y
        return [x_max, x_min, y_max, y_min]

    def find_point(self, x, y, mode='x-y', closest=False):
        """
            Finds the (closest) point to a given coordinate in this region of interest. The method uses binary search
            if the points are sorted according to the mode.
        :param x:           The desired 'x'-coordinate.
        :param y:           The desired 'y'-coordinate.
        :param mode:        The mode in which we wish to search the coordinates: local X-Y, global X-Y,
                            or latitude, and longitude. The default is local X-Y.
        :param closest:     Toggles whether or not you want the closest point to be returned
                            if no exact match was found.
        :return:            The point (closest) to the given coordinates.
        :rtype:             Point
        """
        if self.sorted_mode == mode:
            return self._binary_search(x, y, mode, closest)
        else:
            return self._linear_search(x, y, mode, closest)

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

    def __len__(self):
        return len(self.points)

    def _binary_search(self, x, y, mode='x-y', closest=False):
        i = 0
        j = len(self.points)
        x_param, y_param = select_params(mode)
        point = None
        while i != j:
            search_index = int((i + j) / 2)
            point = self.points[search_index]
            if point.get_value(x_param) == x:
                if point.get_value(y_param) == y:
                    return point
                elif point.get_value(y_param) > y:
                    i = search_index
                else:
                    j = search_index
                # TODO: Search for y
            elif point.get_value(x_param) > x:
                i = search_index
            else:
                j = search_index
        if closest:
            return point
        else:
            return None

    def _linear_search(self, x, y, mode='x-y', closest=False):
        x_param, y_param = select_params(mode)
        closest_point = None
        if closest:
            radius_squared = float('Inf')
        for point in self.points:
            point_x = point.get_value(x_param)
            point_y = point.get_value(y_param)
            if point_x == x and point_y == y:
                return point
            if closest and (point_x - x) ** 2 + (point_y - y) ** 2 < radius_squared:
                radius_squared = (point_x - x) ** 2 + (point_y - y) ** 2
                closest_point = point
        return closest_point


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


class Point(object):
    """
    Stores the information (location) of a single point along with the spectral bands.
    """
    def __init__(self, identity, x, y, map_x, map_y, latitude, longitude, bands):
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
        :type identity:     int
        :type x:            int
        :type y:            int
        :type map_x:        float
        :type map_y:        float
        :type latitude:     float
        :type longitude:    float
        :type bands:        list[float]
        :return:
        """
        self.identity = int(identity)
        self.X = int(x)
        self.Y = int(y)
        self.map_X = map_x
        self.map_Y = map_y
        self.latitude = latitude
        self.longitude = longitude
        self.bands = bands

    def get_value(self, val):
        """
            A get method for the region of interest
        :param val:     The parameter one want from the ROI object. Can be 'id', 'X', 'Y', 'map_X', 'map_Y', 'latitude',
                        'longitude', or 'bands'.
        :return:
        """
        if val == 'id' or val == 'identity':
            return self.identity
        elif val == 'X':
            return self.X
        elif val == 'Y':
            return self.Y
        elif val == 'map_X':
            return self.map_X
        elif val == 'map_Y':
            return self.map_Y
        elif val == 'latitude':
            return self.latitude
        elif val == 'longitude':
            return self.longitude
        elif val == 'bands':
            return self.bands

    def __len__(self):
        return len(self.bands)
