# -*- coding: utf-8 -*-
"""
TODO: File description
"""
from __future__ import division

__author__ = 'Sindre Nistad'

"""
The different names of classes in each dataset
"""
CLASSES = {
    'master_r19': [
        'BAPI',
        'soil',
        'ARCA-SALE',
        'CISP',
        'ARGL',
        'MAFG',
        'QUDO',
        'pisa',
        'CESP',
        'UMCA',
        'ARCASALE',
        'agsoil',
        'QUAG',
        'magf',
        'cecu',
        'PLRA',
        'qudo',
        'agres',
        'PISA',
        'erfa',
        'rock',
        'ADFA'
    ],
    'aviris_r19': [
        'BAPI',
        'soil',
        'ARCA-SALE',
        'CISP',
        'ARGL',
        'MAFG',
        'QUDO',
        'pisa',
        'CESP',
        'UMCA',
        'ARCASALE',
        'agsoil',
        'QUAG',
        'magf',
        'cecu',
        'PLRA',
        'qudo',
        'agres',
        'PISA',
        'erfa',
        'rock',
        'ADFA'
    ],
    'aviris_r20': [
        'RDP',
        'golfcourse',
        'EUSP',
        'BRNI',
        'BAPI',
        'MARSH',
        'bapi',
        'soil',
    ],
    'aviris_r21': [
        'BAPI',
        'BRNI',
        'CISP',
        'DTR',
        'EUSP',
        'MARSH',
        'PEAM',
        'PLRA',
        'RDP',
        'agsoil',
        'bapi',
        'golfcourse',
        'soil',
        'urban',
    ],
    'aviris_r22': [
        'BRNI',
        'CEME',
        'CESP',
        'CISP',
        'DTR',
        'DTRN',
        'EUSP',
        'PEAM',
        'PLRA',
        'RDP',
        'grassland',
        'plra',
        'rock',
        'soil',
    ]
}

WAVELENGTHS = {
    'AVIRIS': {
        'wavelengths': [
            0.365900, 0.375600, 0.385300, 0.394900, 0.404600, 0.414300, 0.424000, 0.433700, 0.443400, 0.453100,
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
            2.466500, 2.476400, 2.486300, 2.496200
        ],
        'unit': 'micrometer',
    },
    'MASTER': {  # In this case, we only use 5 bands...
        'wavelengths': [
            0.458, 0.496, 0.538, 0.58, 0.652, 0.71, 0.75, 0.8, 0.866, 0.906, 0.946, 1.608, 1.666, 1.718, 1.774,
            1.826, 1.874, 1.924, 1.98, 2.08, 2.16, 2.212, 2.258, 2.32, 2.388, 3.142, 3.292, 3.452, 3.607, 3.757,
            3.912, 4.067, 4.224, 4.374, 4.522, 4.667, 4.822, 4.962, 5.117, 5.272, 7.815, 8.185, 8.665, 9.104,
            9.706, 10.115, 10.554, 11.365, 12.097, 12.876
        ],
        'unit': 'micrometer',
    }
}

NUMBER_OF_USED_BANDS = {
    'AVIRIS': 178,
    "MASTER": 5,

}

"""
Adds wave numbers to the datasets
"""

WAVELENGTHS['AVIRIS']['wave number'] = [
    1 / wvl * 10 ** 6 for wvl in reversed(WAVELENGTHS['AVIRIS']['wavelengths'])
]
WAVELENGTHS['MASTER']['wave number'] = [
    1 / wvl * 10 ** 6 for wvl in reversed(WAVELENGTHS['MASTER']['wavelengths'])
]

UNITS = {
    'meter': 1,
    'decimeter': 10 ** -1,
    'centimeter': 10 ** -2,
    'millimeter': 10 ** -3,
    'micrometer': 10 ** -6,
    'nanometer': 10 ** -9,
}

HIDDEN_INPUT_RATIO = 0.5

"""
Methods for changing the unit of measurement of the wavelengths.
"""


def set_unit(unit, dataset=""):
    """
        Changes the units of the dataset (AVISIR/MASTER), or both if left blank to the given units.
    :param unit:    The unit we want the dataset(s) to be in, e.g. micrometers, nanometers, etc.
    :param dataset: The dataset the units are to be changed. If none is specified, it will change the units for all
                    datasets. The options for datasets is MASTER, and AVIRIS.
    :type unit:     str
    :type dataset:  str
    """
    dataset = dataset.upper()
    if dataset is 'AVIRIS':
        _set_unit(unit, 'AVIRIS')
    elif dataset is 'MASTER':
        _set_unit(unit, 'MASTER')
    else:
        _set_unit(unit, 'AVIRIS')
        _set_unit(unit, 'MASTER')


def _set_unit(unit, dataset):
    """
        Helper method for set_unit. Does the actual conversion between different units
    :param unit:
    :param dataset:
    :type unit:
    :type dataset:
    """
    current_unit = WAVELENGTHS[dataset]['unit']
    conversion_factor = UNITS[unit] / UNITS[current_unit]
    WAVELENGTHS[dataset]['wavelengths'] = [
        wvl * conversion_factor
        for wvl in WAVELENGTHS[dataset]['wavelengths']
    ]
    WAVELENGTHS[dataset]['unit'] = unit
