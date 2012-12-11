'''
Created on Dec 5, 2012

@author: nathan
'''

import re

import alphasign
import labels

class SignDirectException(Exception):
    def __init__(self, *args):
        super(SignDirectException, self).__init__(*args)

class LabelInvalidException(SignDirectException):
    def __init__(self, label, message, *args):
        self.label = label
        super(LabelInvalidException, self).__init__(message, label, *args)
        
################################################################################
        
class SignDirect(object):
    '''Class to handle all the sign-direct methods
    '''        

    def __init__(self, sign):
        '''The handler holds a reference to the sign
        '''
        self.sign = sign

    def _validate_label(self, label, type_name):
        if label not in labels.valid_labels:
            raise LabelInvalidException(label, 'Not a valid label')
        if label in labels.counter_labels:
            raise LabelInvalidException(label, 'Must not use counter label')
        memory_entry = self.sign.read_memory_table(label=label)
        if memory_entry is None:
            raise LabelInvalidException(label, 'Label not in memory table')
        if memory_entry['type'] == type_name:
            raise LabelInvalidException(label, 'label is wrong type in memory table')
        
    def clear_table(self):
        self.sign.clear_memory()
        
    def store_table(self, table):
        '''This function parses and allocates a table specified by table. It
        returns a list of rejected entries, rejected entry is a tuple in the
        form (index of entry, exception that caused rejection). If a label is
        reused, only the first use is accepted, and the rest are rejected.
        '''
        table = table['table']
        rejected_entries = []
        allocation_objects = []
        used_labels = []
        for index, entry in enumerate(table):
            try:
                label = entry['label']
                object_type = entry['type']
                
                self._validate_label(label)
                if label in used_labels:
                    raise LabelInvalidException(label, 'Already used label')
                
                #TODO: check sizes
                if object_type == 'TEXT':
                    obj = alphasign.Text(label=label, size=entry['size'])
                elif object_type == 'STRING':
                    obj = alphasign.String(label=label, size=entry['size'])
                elif object_type == 'DOTS':
                    obj = alphasign.Dots(entry['rows'], entry['columns'], label=label)
                allocation_objects.append(obj)
                used_labels.append(label)
            
            except (SignDirectException, KeyError) as e:
                rejected_entries.append((index, e))
                
        self.sign.allocate(allocation_objects)
        return rejected_entries
    
    def get_table(self):
        return {'table': self.sign.read_memory_table()}
    
    def show_text(self, label):
        if label not in labels.valid_labels:
            raise LabelInvalidException(label, 'label is not valid')
        self.sign.set_run_sequence([alphasign.Text(label=label)])
        
    @staticmethod
    def _parse_generic(text, replacer):
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
    
    def _parse_colors(self, text):
        '''This function scans the text for color flags (ie, {RED}) and replaces
        them with their alphasign call-character equivelent
        '''
        def replacer(color):
            if color in alphasign.colors.colors:
                return alphasign.colors.colors[color]
            
        return self._parse_generic(text, replacer)

    def _parse_labels(self, text):
        '''This function scans the text for label flags (ie, {C}) and replaces
        them with their alphasign call-character equivelents. It depends on the
        current memory table of the sign.
        '''
        
        types = {'STRING': alphasign.String, 'DOTS': alphasign.Dots}
        memory_types = {entry['label']: types[entry['type']] 
                        for entry in self.sign.read_memory_table()
                        if entry['type'] != 'TEXT'}
        
        def replacer(label):
            if label in memory_types:
                return memory_types[label](label=label).call()
            
        return self._parse_generic(text, replacer)
        
    #TODO: refactor identical code in these two functions
    #TODO: additional parameter validation. size, type, etc.
    def insert_text(self, text_object):
        label = text_object['label']
        self._validate_label(label)
        data = text_object['text']
        
        #prepend color if present
        if 'color' in text_object and text_object['color'] in alphasign.colors.colors:
            data = alphasign.colors.colors[text_object['color']] + data
            
        data = self._parse_colors(data)
        data = self._parse_labels(data)
        
        text = alphasign.Text(data,
                              label=label,
                              mode=text_object.get('mode', alphasign.modes.HOLD))
        self.sign.write(text)
        
    def insert_string(self, string_object):
        label = string_object['label']
        self._validate_label(label)
        data = string_object['text']
        
        #prepend color if present
        if 'color' in string_object and string_object['color'] in alphasign.colors.colors:
            data = alphasign.colors.colors[string_object['color']] + data
            
        data = self._parse_colors(data)
        
        string = alphasign.String(data,
                                  label=label)   
        self.sign.write(string)
        
    def insert_dots(self, dots_object):
        label = dots_object['label']
        self._validate_label(label)
        
        dots = alphasign.Dots(dots_object['rows'], dots_object['columns'], label=label)
        
        for i, row in enumerate(dots_object['data']):
            dots.set_row(i, row)
        self.sign.write(dots)
        