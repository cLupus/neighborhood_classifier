# -*- coding: utf-8 -*-
"""
    Interacts with images
"""
__author__ = 'Sindre Nistad'

from warnings import warn

from Classifier.neural_network import ClassificationNet
from Common.common import get_index


def apply_to_image(img, neural_network, normalized_img=False):
    """
        A method to apply the neural network classifier to an entire image.
    :param img:             Image to be classified.
    :param neural_network:  The neural network that does the classification
    :param normalized_img:  A flag to indicate that the image has been normalized. The default is to
                            assume that the image has not been normalized.
    :type img:              list of [list of [list of [float | int]]]
    :type neural_network:   ClassificationNet
    :type normalized_img:   bool
    :return:                A classified image of the same size, as well as a list of targets corresponding to
                            the values of the classification.
    :rtype                  list of [list of [int]], list of [str]
    """
    if not neural_network.is_normalized or not normalized_img:
        warn("The image, and the neural network should be normalized for portability. Continuing.")
    cols = len(img)
    rows = len(img[0])
    bands = len(img[0][0])
    if bands != neural_network.num_bands:
        raise Exception("The number of bands in the image does not match the number of bands in the neural net",
                        (bands, neural_network.num_bands))
    classified_img = [[0 for _ in range(rows)] for _ in range(cols)]  # Creates an empty image for classification.
    buffer_size = int(neural_network.neigborhood_size/2)  # To avoid out of range errors.
    for row in range(buffer_size, rows - buffer_size):
        for col in range(buffer_size, cols - buffer_size):
            neigborhood = get_neigborhood(img, row, col, neural_network.neigborhood_size)
            classified_img[col][row] = neural_network.neural_net.activate()
            # TODO: Implement


def get_neigborhood(img, row, col, neigborhood_size, concatenated=True):
    """
        A method to get all the bands in the neigborhood of a pixel, and concatenate it into a single list of numbers
    :param img:                 The image from which the neigborhood is to be extracted.
    :param row:                 The row of the pixel we are interested in.
    :param col:                 The column of the pixel we are interested in.
    :param neigborhood_size:    The size of the neigborhood of the pixel.
    :param concatenated:        Toggles whether or not we return a single list, or a list per pixel in the neigborhood.
                                The default is to return a single list.
    :type img:                  list of [list of [list of [float | int]]]
    :type row:                  int
    :type col:                  int
    :type neigborhood_size:     int
    :type concatenated:         bool
    :return:                    If the concatenated option is set to True,  we return a single list of numbers.
                                If the concatenated option is set to False, we return a list for each pixel.
    :rtype:                     list of [list of [int | float]] | list of [list of [list of [int | float]]]
    """
    if concatenated:
        neigborhood = [None for _ in range(neigborhood_size ** 2)]
    else:
        neigborhood = [[None for _ in range(neigborhood_size)] for _ in range(neigborhood_size)]
    min_x = row - int(neigborhood_size / 2)
    min_y = col - int(neigborhood_size / 2)
    cols = len(img)
    rows = len(img[0])
    for i in range(neigborhood_size):
        for j in range(neigborhood_size):
            bands = img[col - min_y + j][row - min_x + i]
            if concatenated:
                index = get_index(rows, i, cols, j, neigborhood_size)
                neigborhood[index] = bands
            else:
                neigborhood[i][j] = bands
    return neigborhood


