# -*- coding: utf-8 -*-
"""
    A collection of method that are used in different classes, and files.
"""
__author__ = 'Sindre Nistad'

from re import split as regex_split

import matplotlib.pylab as plt
from matplotlib import figure


def get_indices(max_x, x, max_y, y, num_neighbors):
    """
        Returns the indices for placement of points in the local neigborhood of that point having size
        'num_neigborhood' * 'num_neigborhood'.
    :param max_x:           The x size of the entire image (The number of rows in the image)
    :param x:               The row in which the pixel is located
    :param max_y:           The y size of the entire image (The number of columns in the image)
    :param y:               The column in which the pixel is located
    :param num_neighbors:   The size of the neigborhood.
    :type max_x:            int
    :type x:                int
    :type max_y:            int
    :type y:                int
    :type num_neighbors:    int
    :return:                The x, and y index for the local neigborhood.
    :rtype:                 int, int
    """
    return num_neighbors - (max_x - x) - 1, num_neighbors - (max_y - y) - 1


def get_index(max_x, x, max_y, y, num_neighbors):
    """
        Gets the linear index for the local neigborhood.
    :param max_x:           The x size of the entire image (The number of rows in the image)
    :param x:               The row in which the pixel is located
    :param max_y:           The y size of the entire image (The number of columns in the image)
    :param y:               The column in which the pixel is located
    :param num_neighbors:   The size of the neigborhood.
    :type max_x:            int
    :type x:                int
    :type max_y:            int
    :type y:                int
    :type num_neighbors:    int
    :return:                The linear index for the local neigborhood.
    :rtype:                 int
    """
    index_x, index_y = get_indices(max_x, x, max_y, y, num_neighbors)
    return index_y * num_neighbors + index_x


def split_numbers(numbers):
    """
        A subroutine to extract the numbers from the list of strings
    :param numbers:
    :type numbers:  list of [string]
    :return :       List of numbers
    :rtype:         list of [float]
    """

    res = []
    for elm in numbers:
        res.append(int(filter(str.isdigit, elm)))
    return res


def get_histogram(roi_list, targets,  count_points=True):
    """
        A helper method to count the distribution of the targets.
    :param roi_list:            A list of region of interest objects.
    :param targets:             A list of targets, including the 'background' target.
    :param count_points:        Toggles whether or not to count each point, or each ROI as a unit of the count mode.
    :return:                    If count is set to False, the function returns the data set.
                                If count is set to True, the function returns a dictionary of targets (including
                                'background') that has the frequency of each target.

    :type roi_list:             list[ROI]
    :type targets:              list[str]
    :type count_points:         bool
    :rtype:                     dict of [str, int] | ClassificationDataSet
    """
    # Initializing the histogram/distribution for the data.
    histogram = {}
    for target in targets:
        histogram[target] = 0

    for roi in roi_list:
        if roi.name is 'background' or roi.name not in targets:
            if count_points:
                histogram['background'] += roi.num_points
            else:
                histogram['background'] += 1
        else:  # The ROI is a target
            if count_points:
                histogram[roi.name] += roi.num_points
            else:
                histogram['background'] += 1
    return histogram


def plot_data(data):
    """
        Creates a 2D plot of the input data.
    :param data:    The data to be plotted
    :type data:     list of [float | int]
    :return:
    """
    x = plt.linspace(0, 1, len(data))
    y = data
    figure()
    plt.plot(x, y, 'r')


def extract_name(name_string):
    """
        A helper method to extract the name of the ROI, and separate it into main name, and part name
    :param name_string: The full string of the line with the name
    :type name_string: str | list of [str]
    :return: the first name of the region, and the sub name of the region
    """
    if isinstance(name_string, str):
        name_string = name_string.split()
    full_name = name_string[-1]
    full_name = full_name.split('_')
    if len(full_name) > 1:  # e.i. the name is in the form name_region
        roi_name = full_name[0]
        sub_name = full_name[1]
    else:
        full_name = regex_split('(\d+)', full_name[0])
        roi_name = full_name[0]
        sub_name = full_name[1]
    return roi_name, sub_name


def get_neighbors(point, point_list, num_neighbors, use_list=False):
    """
        A method that gets the n neighbors of a point (and the point itself) in a matrix
    :param point:           The ROI Point of interest
    :param point_list:      A list of all the points of the region of interest
    :param num_neighbors:   The diameter of the neighborhood
    :param use_list:        Toggles whether or not the function is to return a list instead of a matrix

    :type point:            Point
    :type point_list:       list of [Point]
    :type num_neighbors:    int
    :rtype:                 list[list[Point]] or list[Point]
    :return:                Matrix of Points corresponding to the neighborhood. Some of the points ma
    """
    if not use_list:
        points = [[None for _ in range(num_neighbors)] for _ in range(num_neighbors)]
    else:
        points = [None for _ in range(num_neighbors ** 2)]

    x = point.X
    y = point.Y
    max_x = x + int(num_neighbors / 2)
    min_x = x - int(num_neighbors / 2)
    max_y = y + int(num_neighbors / 2)
    min_y = y - int(num_neighbors / 2)
    for p in point_list:
        if min_x <= p.X <= max_x and min_y <= p.Y <= max_y:
            index_x, index_y = get_indices(max_x, p.X, max_y, p.Y, num_neighbors)
            if not use_list:
                points[index_y][index_x] = p
            else:
                points[index_y * num_neighbors + index_x] = p
    return points


class ROI(object):
    def __init__(self, name, sub_name, rgb, num_points, points=None):
        """
            A object to hold the information on a region of interest.
        :param name:
        :param rgb:
        :param num_points:
        :param points:

        :type name: str
        :type rgb: list[int]
        :type num_points: int
        :type points: list[Point]

        :return:
        """
        self.name = name
        self.sub_name = sub_name
        self.rgb = rgb
        self.num_points = num_points
        if points is None:
            self.points = []
        else:
            self.points = points

    def add_point(self, point):
        self.points.append(point)

    def __len__(self):
        return len(self.points)


class Point(object):
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

    def __len__(self):
        return len(self.bands)
