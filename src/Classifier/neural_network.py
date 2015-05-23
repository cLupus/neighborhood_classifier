# -*- coding: utf-8 -*-
"""
The class, and associated sub-classes, and methods for creating, training, and testing an artificial neural network
classifier.
"""

import neurolab as nl
from neurolab.trans import TanSig, HardLim, Competitive, HardLims, LogSig, PureLin, SatLin, SoftMax, SatLins, SatLinPrm
from numpy import array

from Common.parameters import NUMBER_OF_USED_BANDS, HIDDEN_INPUT_RATIO


class ClassificationNet(object):
    """
    A classification neural network.
    """

    def __init__(self, minimum, maximum, points, hidden_layer=-1, transfer_functions=TanSig):
        """
        Initializes a classification network, which will be trained to classify the remote sensed data.
        :param minimum:             The minimum value of what the input will be.
        :param maximum:             The maximum value of what the input will be.
        :param points:              The points which will be used to train the network.
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
        if isinstance(points[0], list):
            self.k = len(points[0])
        else:
            self.k = 0  # e.i. no neighbors
        # Plus 1 because k does not include the point itself
        self.num_input_nodes = NUMBER_OF_USED_BANDS['AVIRIS'] * (self.k + 1)
        if isinstance(hidden_layer, int) and hidden_layer > 0:
            self.num_hidden_nodes = hidden_layer
        elif isinstance(hidden_layer, float) and hidden_layer > 0:
            self.num_hidden_nodes = self.num_input_nodes * hidden_layer
        else:
            self.num_hidden_nodes = self.num_input_nodes * HIDDEN_INPUT_RATIO
        minmax = [minimum, maximum] * self.num_input_nodes
        size = [self.num_hidden_nodes, 1]
        self.net = nl.net.newff(minmax=minmax, size=size, transf=transfer_functions)


    pass
