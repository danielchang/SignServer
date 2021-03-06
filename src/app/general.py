'''
Created on Dec 13, 2012

@author: nathan

General utilities used by all layers of the app

Copyright 2012, 2013 Nathan G. West

This file is part of SignServer.

SignServer is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

SignServer is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with SignServer.  If not, see <http://www.gnu.org/licenses/>.
'''

import re

import bottle

import alphasign

from sign import sign, read_raw_memory_table
import constants

def validate_label(label, type_name=None, raw_table=None):
    if label not in constants.valid_labels:
        raise bottle.HTTPError(400, 'label %s is invalid' % label)
    if label in constants.counter_labels:
        raise bottle.HTTPError(400, 'label cannot be a counter (1-5)')
    if type_name is not None:
        if raw_table is None:
            raw_table = read_raw_memory_table()
        memory_entry = sign.find_entry(raw_table, label)
        if memory_entry is None:
            raise bottle.HTTPError(400, 'label %s not in memory table' % label)
        if memory_entry['type'] == type_name:
            raise bottle.HTTPError(400, 'label %s is of type %s, not %s' % (label, type_name, memory_entry['type']))

def parse_generic(text, replacer):
    '''This function scans the text for all flags of the form {stuff}, and
    replaces them according to the replacer function. The replacer function
    takes, as an argument, the content inside the flag. If it returns None,
    the flag is untouched.
    '''
    
    match_pattern = '\{([^}]*)\}'
    def _replacer(match):
        replacement = replacer(match.group(1))
        return replacement if replacement is not None else match.group()
    
    return re.sub(match_pattern, _replacer, text)

def parse_colors(text):
    '''This function scans the text for color flags (ie, {RED}) and replaces
    them with their alphasign call-character equivelent
    '''
    def replacer(color):
        color = constants.get_color(color)
        if color != '':
            return color
        return None
        
    return parse_generic(text, replacer)

def parse_labels(text, memory=None):
    '''This function scans the text for label flags (ie, {C}) and replaces
    them with their alphasign call-character equivelents. It depends on the
    current memory table of the sign.
    '''
    
    types = {'STRING': alphasign.String, 'DOTS': alphasign.Dots}
    if memory is None:
        memory = sign.parse_raw_memory_table(read_raw_memory_table())
    memory_types = {entry['label']: types[entry['type']] 
                    for entry in memory if entry['type'] != 'TEXT'}
    
    def replacer(label):
        if label in memory_types:
            return memory_types[label](label=label).call()
        return None
        
    return parse_generic(text, replacer)

def inject_json(func):
    '''Function decorator. Converts takes a function that would expect
    bottle.request to be json, and passes the json dict as the first argument.
    Automatically converts ValueErrors and KeyErrors into HTTPErrors.
    '''
    def wrapper(*args, **kwargs):
        try:
            request = bottle.request.json
            if request is None:
                raise bottle.HTTPError(400, 'Data must be json')
            return func(request, *args, **kwargs)
        except ValueError as e:
            raise bottle.HTTPError(400, 'Error parsing json\n%s' % e.message)
        except KeyError as e:
            raise bottle.HTTPError(400, 'Missing field in json: %s' % e.message)
    return wrapper