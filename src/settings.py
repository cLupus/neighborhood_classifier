# -*- coding: utf-8 -*-
"""
TODO: Description
"""
from ast import literal_eval


with open('/Users/sindrenistad/Dropbox/workspace/geog214a/neighborhood_classifier/src/DATABASE.txt', 'r') as f:
    DATABASE = literal_eval(f.read())

HIDDEN_LAYER = 0.5

