# -*- coding: utf-8 -*-
"""
    A collection of method that are used in different classes, and files.
"""
__author__ = 'Sindre Nistad'

from re import split as regex_split
from ast import literal_eval

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
    return [float(num) for num in numbers]


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


def get_AVIRIS_wavelengths(unit='micrometer'):
    """
        Returns a list of all the wavelengths of AVIRIS in the specified unit. The default is micrometers.
    :param unit:    The unit of measurement one would like the wavelengths to be in.
    :type unit:     str
    :return:    Returns a list of all the wavelengths of AVIRIS in the specified unit. The default is micrometers.
    :rtype:     list of [float]
    """
    wavelengths = [0.365900, 0.375600, 0.385300, 0.394900, 0.404600, 0.414300, 0.424000, 0.433700, 0.443400, 0.453100,
                   0.462800, 0.472500, 0.482200, 0.491900, 0.501600, 0.511400, 0.521100, 0.530800, 0.540600, 0.550300,
                   0.560000, 0.569800, 0.579600, 0.589300, 0.599100, 0.608900, 0.618600, 0.628400, 0.638200, 0.648000,
                   0.657800, 0.667600, 0.655800, 0.665600, 0.675400, 0.685200, 0.695000, 0.704800, 0.714600, 0.724300,
                   0.734100, 0.743900, 0.753600, 0.763400, 0.773100, 0.782900, 0.792600, 0.802400, 0.812100, 0.821800,
                   0.831500, 0.841200, 0.850900, 0.860600, 0.870300, 0.880000, 0.889700, 0.899400, 0.909100, 0.918800,
                   0.928400, 0.938100, 0.947700, 0.957400, 0.967000, 0.976700, 0.986300, 0.995900, 1.005600, 1.015200,
                   1.024800, 1.034400, 1.044000, 1.053600, 1.063200, 1.072800, 1.082400, 1.092000, 1.101500, 1.111100,
                   1.120700, 1.130200, 1.139800, 1.149300, 1.158900, 1.168400, 1.177900, 1.187400, 1.197000, 1.206500,
                   1.216000, 1.225500, 1.235000, 1.244500, 1.254000, 1.263500, 1.253400, 1.263300, 1.273300, 1.283300,
                   1.293300, 1.303200, 1.313200, 1.323200, 1.333200, 1.343100, 1.353100, 1.363100, 1.373000, 1.383000,
                   1.393000, 1.402900, 1.412900, 1.422900, 1.432800, 1.442800, 1.452800, 1.462700, 1.472700, 1.482700,
                   1.492700, 1.502600, 1.512600, 1.522600, 1.532500, 1.542500, 1.552400, 1.562400, 1.572400, 1.582300,
                   1.592300, 1.602300, 1.612200, 1.622200, 1.632200, 1.642100, 1.652100, 1.662100, 1.672000, 1.682000,
                   1.691900, 1.701900, 1.711900, 1.721800, 1.731800, 1.741800, 1.751700, 1.761700, 1.771600, 1.781600,
                   1.791600, 1.801500, 1.811500, 1.821400, 1.831400, 1.841400, 1.851300, 1.861300, 1.871200, 1.872400,
                   1.866900, 1.876900, 1.887000, 1.897000, 1.907100, 1.917100, 1.927200, 1.937300, 1.947300, 1.957300,
                   1.967400, 1.977400, 1.987500, 1.997500, 2.007500, 2.017500, 2.027600, 2.037600, 2.047600, 2.057600,
                   2.067700, 2.077700, 2.087700, 2.097700, 2.107700, 2.117700, 2.127700, 2.137700, 2.147700, 2.157700,
                   2.167700, 2.177700, 2.187700, 2.197700, 2.207700, 2.217600, 2.227600, 2.237600, 2.247600, 2.257600,
                   2.267500, 2.277500, 2.287500, 2.297400, 2.307400, 2.317300, 2.327300, 2.337300, 2.347200, 2.357200,
                   2.367100, 2.377100, 2.387000, 2.396900, 2.406900, 2.416800, 2.426800, 2.436700, 2.446600, 2.456500,
                   2.466500, 2.476400, 2.486300, 2.496200]

    if unit == 'micrometer' or unit == 'um':
        return wavelengths
    elif unit == 'nanometer' or unit == 'nm':
        return [wavelength * 1000 for wavelength in wavelengths]
    elif unit == 'wavenumber' or wavelengths == 'wave number':
        return [1/(wavelength * 10 ** -6) for wavelength in wavelengths.reverse()]
    else:
        raise AttributeError("The given unit, " + unit + " is invalid, or has not been implemented yet.")


def strip_and_add_space(string):
    """
        Strips the string, and then adds a single space to it, useful for making sure a delimiter is only the character
        followed by a space, as to make it pretty.
    :param string:  The string to be treated
    :type string:   str
    :return:        A striped string with an additional space at the end.
    :rtype:         str
    """
    # To make sure it only have one space after the delimiter character.
    string = string.strip()
    string += " "
    return string


def list_to_string(l, delimiter=','):
    """
        Converts a list of objects to a single string, where the objects are separated by 'delimiter'.
    :param l:           List of objects
    :param delimiter:   The delimiter to divide the data
    :type l:            list of [T]
    :type delimiter:    str
    :return:            Single string of the sting version of the objects, separated by 'delimiter'.
    :rtype:             str
    """
    delimiter = strip_and_add_space(delimiter)
    s = "".join([str(itm) + delimiter for itm in l])
    s = s[:-2]
    return s


def get_one_indexed(i):
    """
        Adds one (1) to the argument, so it is readable when adding one to change indexing system
    :param i:   a 0-index
    :type i:    int
    :return:    i + 1
    :rtype:     int
    """
    return i + 1


def get_zero_index(i):
    """
        Subtracts one (1) to the argument, so it is readable when adding one to change indexing system
    :param i:   a 1-index
    :type i:    int
    :return:    i - 1
    :rtype:     int
    """
    return i - 1


def is_in_name(sub_string, string):
    """
        Checks if the substring is contained in the (long) string. Ignores case.
    :param sub_string:
    :param string:
    :type sub_string:   str
    :type string:       str
    :return:            True if the string contains the substring. False otherwise.
    :rtype:             bool
    """
    return sub_string.lower() in string.lower()


def normalize_min_max(data, minimums, maximums):
    """
        Normalizes the given data in a min-max fashion.
        NB: The length of the different input parameters must be the same length.
    :param data:        The data to be normalized
    :param minimums:    The minimums for each 'band'
    :param maximums:    The maximums for each 'band'
    :type data:         list of [float]
    :type minimums:     list of [float]
    :type maximums:     list of [float]
    :return:            A list of normalized data.
    :rtype:             list of [float]
    """
    assert len(data) == len(minimums) == len(maximums)
    return [(data[i] - minimums[i]) / (maximums[i] - minimums[i]) for i in range(len(data))]


def normalize_gaussian(data, means, standard_deviations):
    """
        Normalizes the given data in a gaussian fashion.
        NB: The length of the different input parameters must be the same length.
    :param data:                The data to be normalized
    :param means:               The mean value for each 'band'
    :param standard_deviations: The standard deviation for each 'band'
    :type data:                 list of [float]
    :type means:                list of [float]
    :type standard_deviations:  list of [float]
    :return:                    A list of normalized data.
    :rtype:                     list of [float]
    """
    assert len(data) == len(means) == len(standard_deviations)
    return [(data[i] - means[i]) / standard_deviations[i] for i in range(len(data))]


def string_to_array(string, floats=True):
    """
        Converts a string literal to a tuple, list or dict safely
    :param string:  The string to be converted
    :param floats:  Toggles whether or not the resulting tuple or list will be of floats, or strings
    :type string:   str
    :type floats:   bool
    :return:        Tuple, list, or dict with the content in the string literal.
    :rtype:         tuple of [str | float] | list of [str | float\ | dict of [str, str]
    """
    # This whole function can be reduced to 'literal_eval'...
    if '(' in string and ')' in string:
        # Tuple
        return tuple(_string_to_list(string, floats))
    elif '[' in string and ']' in string:
        # List
        return _string_to_list(string, floats)
    elif '{' in string and '}' in string and ':' in string:
        # Dict
        return literal_eval(string)
    else:
        raise ValueError("The given string is not a literal tuple, list, or dict!")


def _string_to_list(string, floats=True):
    """
        Helper method to string_to_array. Takes a string, splits it by ',', and removes the beginning and end 'braces'.
    :param string:  String to be divided.
    :param floats:  Toggles whether or not we are to return numbers instead of string literals of what's in 'string'.
    :type string:   str
    :type floats:   bool
    :return:        A list of string literals
    :rtype:         list of [str]
    """
    s = string.split(',')
    first = s[0]
    last = s[-1]
    first = first[1:]  # Removes the first brace
    last = last[:-1]  # Removes the last brace
    s[0] = first
    s[-1] = last
    if floats:
        return [float(o) for o in s]
    else:
        return s


def is_gaussian(string):
    """
        Checks if the given string toggles gaussian
    :param string:  A string for normalization.
    :type string:   str
    :return:        True if the given string can be interpret as 'gaussian'. False otherwise.
    :rtype:         bool
    """
    return string == 'gaussian' or string == 'gauss' or string == 'g'


def is_min_max(string):
    """
        Checks if the given string toggles min-max
    :param string:  A string for normalization.
    :type string:   str
    :return:        True if the given string can be interpret as 'min-max'. False otherwise.
    :rtype:         bool
    """
    return string == 'min-max' or string == 'max-min' or string == 'mm'