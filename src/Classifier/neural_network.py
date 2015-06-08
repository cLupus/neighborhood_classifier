# -*- coding: utf-8 -*-
"""
The class, and associated sub-classes, and methods for creating, training, and testing an artificial neural network
classifier.
"""

# import neurolab as nl
from neurolab.net import newff
from neurolab.trans import TanSig
from neurolab.train import train_gd
from numpy.random import random_sample, shuffle
from numpy import setdiff1d, arange, zeros, array

from Common.parameters import NUMBER_OF_USED_BANDS, HIDDEN_INPUT_RATIO, DEFAULT_TRANSFER_FUNCTION


class ClassificationNet(object):
    """
    A classification neural network.
    """

    def __init__(self, minimum, maximum, points, k, target, hidden_layer=-1, transfer_functions=TanSig(),
                 training_function=train_gd):
        """
        Initializes a classification network, which will be trained to classify the remote sensed data.
        :param minimum:             The minimum value of what the input will be.
        :param maximum:             The maximum value of what the input will be.
        :param points:              The points which will be used to train the network.
        :param k:                   The number of neighbors to each point.
                                    If the point is by it self, it has k = 0 neighbors.
        :param target:              The target for this neural network
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
        :param training_function:   The function to be used when the network is trained. Default is Gradient Decent.
        :type minimum:              float
        :type maximum:              float
        :type points:               numpy.array
        :type k:                    int
        :type target:               str
        :type hidden_layer:         int | float
        :type transfer_functions:   Competitive | HardLim | HardLims | LogSig | PureLin | SatLin | SatLinPrm | SatLins
                                    | SoftMax | TanSig | list of [Competitive | HardLim | HardLims | LogSig | PureLin
                                    | SatLin | SatLinPrm | SatLins | SoftMax | TanSig]
        :type training_function:    neurolab.train.spo | neurolab.train.wta
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
        self.target = target
        """ :type str """
        self.k = k
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
            self.num_hidden_nodes = int(self.num_input_nodes * HIDDEN_INPUT_RATIO)
            """ :type int """
        minmax = [[minimum, maximum]] * self.num_input_nodes
        size = [self.num_hidden_nodes, 1]

        if not isinstance(transfer_functions, list) and not None:
            # A single function is given
            transfer_functions = [transfer_functions] * 2
        elif len(transfer_functions) == 1:
            transfer_functions.extend([DEFAULT_TRANSFER_FUNCTION])
        elif len(transfer_functions) == 2:
            pass
        else:
            raise TypeError("Too many transfer functions")

        self.net = newff(minmax, size)  # , transf=transfer_functions)
        self.net.trainf = training_function

    def divide_dataset(self, test_fraction, validation_fraction=0, shuffle_dataset=True):
        """
        Divides the dataset into a test set, and a training set. In the training set, if validation_fraction is set
        to more than 0, then the training data will be subdivided into a training set, and a validation set.
        :param test_fraction:           The fraction of the dataset that will be set aside for testing the model
        :param validation_fraction:     The fraction of the training set that will be set aside for (cross) validation.
        :param shuffle_dataset:                 Toggles whether or not the dataset is to be shuffled before divided.
                                        Default is True.
        :type test_fraction:            float
        :type validation_fraction:      float
        :type shuffle_dataset:                  bool
        :return:                        None
        :rtype:                         None
        """
        assert 0 < test_fraction < 1 and 0 <= validation_fraction < 1
        if shuffle_dataset:
            shuffle(self.dataset)

        n = len(self.dataset)
        dataset_indices = arange(n)

        test_indices = random_sample(n * test_fraction) * n
        test_indices = test_indices.astype(int)

        train_indices = setdiff1d(dataset_indices, test_indices)
        self.test_data = self.dataset[test_indices]
        self.training_data = self.dataset[train_indices]
        n_train = len(self.test_data)

        indices = random_sample(n_train * validation_fraction) * n_train
        indices = indices.astype(int)

        self.validation_data = self.training_data[indices]

    def train(self, epoch, goal):
        inp, tar = separate_dataset(self.training_data)
        self.net.train(inp, tar, epochs=epoch, goal=goal, show=100, lr=0.01)

    def simulate(self, inp):
        out = self.net.sim(inp)
        # Converts it so that lows are 0, and highs are 1
        # TODO: What is there are values in between?
        out = (out - out.min()) / (out.max() - out.min())
        return out.astype(int)

    def test(self):
        inp, tar = separate_dataset(self.test_data)
        out = self.simulate(inp)
        err = out - tar
        return err


def separate_dataset(dataset):
    """
    Divides the given dataset into two sets; one with the bands, and one with the targets
    :param dataset: The dataset we want to split.
    :type dataset:  numpy.array
    :return:        inp, tar: inp consists of all the band-lengths in the dataset, while tar is the flag that indicates
                    whether or not this is a background
    :rtype:         numpy.array, numpy.array
    """
    n = len(dataset)
    m = len(dataset[0])
    tar = zeros(n).reshape(n, 1)
    inp = [None] * n
    for i in range(n):
        tar[i] = dataset[i][0]
        inp[i] = dataset[i][1:]
    inp = array(inp)
    tar = tar.astype(int)
    return inp, tar
