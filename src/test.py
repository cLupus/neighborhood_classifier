# -*- coding: utf-8 -*-
__author__ = 'Sindre Nistad'

from regions_of_interest import RegionsOfInterest
from neural_network import ClassificationNet


folder = '../ASCII roi/'
normalized = 'normalizing/'
targets = ['master_r19_7_5_emissivity_sub', 'sb_r19_sub_sub_corrected', 'sb_r20_2011_rfl_sub',
           'sb_r21_sub_sub_corrected', 'sb_r22_sub_sub_corrected_colored']
extension = '.txt'


def run():
    # AVIRIS wavelengths in micrometer
    # wavelengths = [0.365900, 0.375600, 0.385300, 0.394900, 0.404600, 0.414300, 0.424000, 0.433700, 0.443400, 0.453100,
    #                0.462800, 0.472500, 0.482200, 0.491900, 0.501600, 0.511400, 0.521100, 0.530800, 0.540600, 0.550300,
    #                0.560000, 0.569800, 0.579600, 0.589300, 0.599100, 0.608900, 0.618600, 0.628400, 0.638200, 0.648000,
    #                0.657800, 0.667600, 0.655800, 0.665600, 0.675400, 0.685200, 0.695000, 0.704800, 0.714600, 0.724300,
    #                0.734100, 0.743900, 0.753600, 0.763400, 0.773100, 0.782900, 0.792600, 0.802400, 0.812100, 0.821800,
    #                0.831500, 0.841200, 0.850900, 0.860600, 0.870300, 0.880000, 0.889700, 0.899400, 0.909100, 0.918800,
    #                0.928400, 0.938100, 0.947700, 0.957400, 0.967000, 0.976700, 0.986300, 0.995900, 1.005600, 1.015200,
    #                1.024800, 1.034400, 1.044000, 1.053600, 1.063200, 1.072800, 1.082400, 1.092000, 1.101500, 1.111100,
    #                1.120700, 1.130200, 1.139800, 1.149300, 1.158900, 1.168400, 1.177900, 1.187400, 1.197000, 1.206500,
    #                1.216000, 1.225500, 1.235000, 1.244500, 1.254000, 1.263500, 1.253400, 1.263300, 1.273300, 1.283300,
    #                1.293300, 1.303200, 1.313200, 1.323200, 1.333200, 1.343100, 1.353100, 1.363100, 1.373000, 1.383000,
    #                1.393000, 1.402900, 1.412900, 1.422900, 1.432800, 1.442800, 1.452800, 1.462700, 1.472700, 1.482700,
    #                1.492700, 1.502600, 1.512600, 1.522600, 1.532500, 1.542500, 1.552400, 1.562400, 1.572400, 1.582300,
    #                1.592300, 1.602300, 1.612200, 1.622200, 1.632200, 1.642100, 1.652100, 1.662100, 1.672000, 1.682000,
    #                1.691900, 1.701900, 1.711900, 1.721800, 1.731800, 1.741800, 1.751700, 1.761700, 1.771600, 1.781600,
    #                1.791600, 1.801500, 1.811500, 1.821400, 1.831400, 1.841400, 1.851300, 1.861300, 1.871200, 1.872400,
    #                1.866900, 1.876900, 1.887000, 1.897000, 1.907100, 1.917100, 1.927200, 1.937300, 1.947300, 1.957300,
    #                1.967400, 1.977400, 1.987500, 1.997500, 2.007500, 2.017500, 2.027600, 2.037600, 2.047600, 2.057600,
    #                2.067700, 2.077700, 2.087700, 2.097700, 2.107700, 2.117700, 2.127700, 2.137700, 2.147700, 2.157700,
    #                2.167700, 2.177700, 2.187700, 2.197700, 2.207700, 2.217600, 2.227600, 2.237600, 2.247600, 2.257600,
    #                2.267500, 2.277500, 2.287500, 2.297400, 2.307400, 2.317300, 2.327300, 2.337300, 2.347200, 2.357200,
    #                2.367100, 2.377100, 2.387000, 2.396900, 2.406900, 2.416800, 2.426800, 2.436700, 2.446600, 2.456500,
    #                2.466500, 2.476400, 2.486300, 2.496200]





    # soil = net.data_set.data.

    # #print(net)
    # best = hidden_layer_to_input_output_layers(0, ['soil'], [0.8, 1], 0.02, 3)
    # best.save('../best.nn')
    pass


def run_neural_network(i, mode='guass', target=None, neigborhood_size=3,
                       targets_background_ration=None, hidden_ratio=0.98,
                       learning_rate=0.2, verbose=True, momentum=0.1, weight_decay=0.,
                       max_epochs=10):
    """
        Aggregate method for reading all the data, and then creating a neural network, training it, and saving it.
    :param i:                           The index of which file is to be loaded
    :param mode:                        How is the data going to be normalized? max-min or gaussian.
                                        The latter is default
    :param target:                      What do we consider to be the target of interest? Everything else will be
                                        considered background.
    :param neigborhood_size:            The size of the neighborhood. Default is 3.
    :param targets_background_ration:   The ratios of targets to background. Default is 1:1.
    :param hidden_ratio:                The ratio of hidden nodes to input plus output nodes.
    :param learning_rate:               The learning rate for the back-propagation algorithm.
    :param verbose:                     Toggles verbose mode on or off. Default is on.
    :param momentum:                    The momentum (previous round) of the learning algorithm to use. Default is 0.1.
    :param weight_decay:                How fast the weighs are decaying. Default is 0.
    :param max_epochs:                  The maximum number of epochs the algorithm will run. Default is 10.

    :type i:                            int
    :type mode:                         str
    :type target:                       list of [str] | str
    :type neigborhood_size:             int
    :type targets_background_ration:    list of [float]
    :type hidden_ratio:                 float
    :type learning_rate:                float
    :type verbose:                      bool
    :type momentum:                     float
    :type weight_decay:                 float
    :type max_epochs:                   int
    :return:                            None
    :rtype:                             None
    """
    # Defaults
    if target is None:
        target = ['soil']
    if targets_background_ration is None:
        targets_background_ration = [1., 1.]

    target_data_set = targets[i]
    path = folder + target_data_set + extension
    normalized_path = folder + normalized + target_data_set + extension
    roi = RegionsOfInterest(path, normalizing_path=normalized_path, mode=mode)
    roi.set_aggregate(True)
    net = ClassificationNet(roi, target, neigborhood_size=neigborhood_size,
                            targets_background_ration=targets_background_ration, hidden_ratio=hidden_ratio)
    net.neural_net.randomize()

    net.set_trainer(learning_rate=learning_rate, verbose=verbose, momentum=momentum, weight_decay=weight_decay)
    net.train_network(max_epochs=max_epochs, verbose=verbose)
    name = target[0] + '.nn'
    net.save('../' + name)


run()