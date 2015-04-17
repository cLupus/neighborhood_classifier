# -*- coding: utf-8 -*-
__author__ = 'Sindre Nistad'

from warnings import warn


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
        # This method is unnecessary...
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
