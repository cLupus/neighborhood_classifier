__author__ = 'Sindre Nistad'


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

