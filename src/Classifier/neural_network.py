# -*- coding: utf-8 -*-
"""
The class, and associated sub-classes, and methods for creating, training, and testing an artificial neural network
classifier.
"""

import neurolab as nl
from neurolab.trans import TanSig
from numpy.random import random_sample

from Common.parameters import NUMBER_OF_USED_BANDS, HIDDEN_INPUT_RATIO


class ClassificationNet(object):
    """
    A classification neural network.
    """

    def __init__(self, minimum, maximum, points, target, hidden_layer=-1, transfer_functions=TanSig):
        """
        Initializes a classification network, which will be trained to classify the remote sensed data.
        :param minimum:             The minimum value of what the input will be.
        :param maximum:             The maximum value of what the input will be.
        :param points:              The points which will be used to train the network.
        :param target:              The
        :param hidden_layer:        The number of hidden nodes in the hidden layer.
                                    If it is an integer, it will be interpreted as the number of hidden nodes.
                                    If it is a float, it will be interpreted as the ratio of nodes in the hidden layer
                                     nodes to the number of nodes in the input layer, e.i.
                                        hidden_layer < 1.0 -> there will be more input nodes than hidden nodes.
                                        hidden_layer = 1.0 -> there will be as many hidden nodes as there are input
                                        nodes.
                                        hidden_layer > 1.0 -> there will be more hidden nodes than input nodes.
                                    If the number is less than or equal to 0, a default ration will be assigned
                                    HIDDEN_INPUT_RATION form parameters (0.5)
        :param transfer_functions:  The function(s) that will be used as in the input layer, the hidden layer,
                                    and the output layer. If only one function is given, it will be applied to all the
                                    layers. If a list of 2 is given, the function(s) will be applied to the input layer
                                    and the hidden layer (transfer_function[0] -> input, transfer_function[1] -> hidden)
                                    If a list of 3 elements is given, the first will be given to the input layer, the
                                    second to the hidden layer, and the third to the output layer.
        :type minimum:              float
        :type maximum:              float
        :type points:               array
        :type hidden_layer:         int | float
        :type transfer_functions:   Competitive | HardLim | HardLims | LogSig | PureLin | SatLin | SatLinPrm | SatLins
                                    | SoftMax | TanSig | list of [Competitive | HardLim | HardLims | LogSig | PureLin
                                    | SatLin | SatLinPrm | SatLins | SoftMax | TanSig]
        :return:
        """
        self.dataset = points
        """ :type array """
        self.training_data = None
        """ :type array """
        self.validation_data = None
        """ :type array """
        self.test_data = None
        """ :type array """
        if isinstance(points[0], list):
            self.k = len(points[0])
            """ :type int """
        else:
            self.k = 0  # e.i. no neighbors
            """ :type int """
        # Plus 1 because k does not include the point itself
        self.num_input_nodes = NUMBER_OF_USED_BANDS['AVIRIS'] * (self.k + 1)
        """ :type int """
        if isinstance(hidden_layer, int) and hidden_layer > 0:
            self.num_hidden_nodes = hidden_layer
            """ :type int """
        elif isinstance(hidden_layer, float) and hidden_layer > 0:
            self.num_hidden_nodes = self.num_input_nodes * hidden_layer
            """ :type int """
        else:
            self.num_hidden_nodes = self.num_input_nodes * HIDDEN_INPUT_RATIO
            """ :type int """
        minmax = [minimum, maximum] * self.num_input_nodes
        size = [self.num_hidden_nodes, 1]
        self.net = nl.net.newff(minmax=minmax, size=size, transf=transfer_functions)

    def divide_dataset(self, test_fraction, validation_fraction=0):
        """
        Divides the dataset into a test set, and a training set. In the training set, if validation_fraction is set
        to more than 0, then the training data will be subdivided into a training set, and a validation set.
        :param test_fraction:           The fraction of the dataset that will be set aside for testing the model
        :param validation_fraction:     The fraction of the training set that will be set aside for (cross) validation.
        :type test_fraction:            float
        :type validation_fraction:      float
        :return:                        None
        :rtype:                         None
        """
        assert 0 < test_fraction < 1 and 0 <= validation_fraction < 1
        indices = random_sample(len(self.dataset) * test_fraction) * len(self.dataset)
        indices = indices.astype(int)
        self.test_data = self.dataset[indices]
        self.training_data = self.dataset - self.test_data

        indices = random_sample(len(self.training_data) * validation_fraction) * len(self.training_data)
        indices = indices.astype(int)
        self.validation_data = self.training_data[indices]

    def train(self):
        self.net.train()
