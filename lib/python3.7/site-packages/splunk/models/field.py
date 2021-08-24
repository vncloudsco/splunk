'''
Splunk model field definitions
'''
from builtins import filter
from builtins import object
import datetime
import re
import time
import logging
logger = logging.getLogger('splunk.models.field')

import splunk.util


class FieldValue(object):
    '''
    Represents a field value object container, used to allow property chaining
    into things like StructuredField()
    '''

    def __init__(self, field):
        self.field = field

        for f in self.field.fields():
            setattr(self, f[0], f[1].get())



class Field(object):
    '''
    Represents a base model field.  Is the base class from which all mappable
    model fields are subclassed.
    '''

    def __init__(self, api_name=None, default_value=None, is_mutable=True):
        self.default_value  = default_value
        self.api_name       = api_name
        self.is_mutable     = is_mutable

    def set(self, val):
        '''
        Assigns a value to the field.
        '''
        self.default_value = val

    def get(self):
        '''
        Returns the field value
        '''
        return self.default_value

    def get_api_name(self, attr_name):
        '''
        Returns the API key name that maps to this model field.
        '''
        return self.api_name or attr_name

    def get_is_mutable(self):
        '''
        Indicates if this field is allowed to be changed if the entity already
        exists.  This has not effect on object create.
        '''
        return self.is_mutable

    def from_apidata(self, api_dict, attrname):
        '''
        Parses data from the API into a model instance.
        '''
        return api_dict.get(self.get_api_name(attrname), self.default_value)

    def to_apidata(self, attrvalue):
        '''
        Returns the field value in a form that is compatible with the API
        '''
        return attrvalue

    def to_api(self, value, attrname, api_dict, fill_value):
        '''
        Updates the api_dict with current model values in a data form that is
        compatible with the API.
        '''
        field = self.get_api_name(attrname)
        value = self.to_apidata(value)

        if value:
            api_dict[field] = value
        elif field in api_dict:
            api_dict[field] = fill_value



class BoolField(Field):
    '''
    Represents a Boolean model field.  On read, this model will attempt to cast
    all known Boolean pairs to a true bool() type.  On write, this model will 
    output either 0 or 1.
    '''

    def from_apidata(self, api_dict, attrname):
        return splunk.util.normalizeBoolean(
            super(BoolField, self).from_apidata(api_dict, attrname)
        )

    def to_apidata(self, attrvalue):
        return splunk.util.normalizeBoolean(attrvalue) and '1' or '0'



class StructuredField(Field):
    '''
    Represents a composite field.  This is generally used to nest property sets
    inside other fields.
    '''

    def fields(self):
        '''
        Returns an interable of all the fields contained in the structure.
        '''
        return list(filter(
            (lambda x: isinstance(x[1], Field)),  
            self.__class__.__dict__.items()
        ))
                
    def get(self):
        return FieldValue(self)

    def from_apidata(self, api_dict, attrname):
        api_name = self.get_api_name(attrname)

        fv = FieldValue(self)
        
        for field in self.fields():
            f = "%s.%s" % (api_name, field[0])
            val = field[1].from_apidata(api_dict, f)
            setattr(fv, field[0], val)

        return fv

    def to_api(self, value, attrname, api_dict, fill_value):
        for field in self.fields():
            attr = "%s.%s" % (attrname, field[0])
            field[1].to_api(
                getattr(value, field[0], None), 
                attr, 
                api_dict, 
                fill_value
            )

    def to_apidata(self, attrvalue):
        return None



class IntField(Field):
    '''
    Represents an integer field
    '''
    
    def from_apidata(self, api_dict, attrname):
        try:
            val = super(IntField, self).from_apidata(api_dict, attrname)
            return int(val)
        except (ValueError, TypeError):
            return None

    def to_apidata(self, attrvalue):
        return str(attrvalue)



class FloatField(Field):
    '''
    Represents a floating point number field
    '''
    
    def from_apidata(self, api_dict, attrname):
        try:
            val = super(FloatField, self).from_apidata(api_dict, attrname)
            return float(val)
        except (ValueError, TypeError):
            return None

    def to_apidata(self, attrvalue):
        return str(attrvalue)



class EpochField(FloatField):
    '''
    Represents a unix epoch timestamp
    '''
    
    def from_apidata(self, api_dict, attrname):
        try:
            val = float(super(EpochField, self).from_apidata(api_dict, attrname))
            if val == 0: return None
            return datetime.datetime.fromtimestamp(val, splunk.util.localTZ)
        except (ValueError, TypeError):
            return None

    def to_apidata(self, attrvalue):
        if attrvalue != None:
            return time.mktime(attrvalue.timetuple())
        else:
            return None



class ListField(Field):
    '''
    Represents a generic list/array structure
    '''
    
    def from_apidata(self, api_dict, attrname):
        val = super(ListField, self).from_apidata(api_dict, attrname)
        if not isinstance(val, list):
            try:
                return list(val)
            except TypeError:
                return []
        return val

    def to_apidata(self, attrvalue):
        if not isinstance(attrvalue, list):
            raise TypeError('ListField must be a list construct')
        return ','.join(attrvalue)



class DictField(Field):
    '''
    Represents a generic dict/hash structure
    '''
    
    def from_apidata(self, api_dict, attrname):
        val = super(DictField, self).from_apidata(api_dict, attrname)
        if not isinstance(val, dict):
            try:
                return dict(val)
            except TypeError:
                return {}
        return val

    def to_apidata(self, attrvalue):
        if not isinstance(attrvalue, dict):
            raise TypeError('DictField must be a dict construct')
        return splunk.util.toUTF8(attrvalue)

#
# composite fields
#


class FloatByteField(Field):
    '''
    Represents a size field that may contain a units suffix.  Valid API values
    include:

        1234
        -1234MB
        1234.5GB

    Units supported range from 'B' to 'YB'.  Unqualified values are assumed
    to be bytes.

    This field is also capable of accepting specific values that do not conform
    to the <float><unit> format, namely:
    
        MAX

    If this Field receives a value of 'MAX' from the API, then it will set
    the 'value_mode' key in the output dictionary to:
        'value_mode': 'MAX',
        'byte_value': 0,
        'relative_value': 0,
        'units': 'B'
    In all other cases, 'value_mode' = 'NORMAL'.

    USAGE:  
    
    Assume that you have defined:

        mod = Foo()
            f1 = Field()
            f2 = FloatByteField()

    Then:

        mod.f2['byte_value']
        >>> 1293942784
        mod.f2['relative_value']
        >>> 1234
        mod.f2['units']
        >>> 'MB'
        mod.f2['value_mode']
        >>> 'NORMAL'
    '''

    # define the typical setting for most byte values
    NORMAL_VALUE_MODE = 'NORMAL'

    # define API-recognized values that are not in the <float><unit> format
    # that hold special meaning
    PRESET_VALUE_MODES = ['MAX']


    def from_apidata(self, api_dict, attrname):
        raw_value = super(FloatByteField, self).from_apidata(api_dict, attrname)

        output = {
            'byte_value': None,
            'relative_value': None,
            'units': None,
            'value_mode': self.NORMAL_VALUE_MODE
        }
        
        if raw_value in self.PRESET_VALUE_MODES:
            output['byte_value'] = 0
            output['relative_value'] = 0
            output['units'] = 'B'
            output['value_mode'] = raw_value
            return output
        
        if raw_value == None:
            return output

        output.update(splunk.util.parseByteSizeString(raw_value))
        
        return output


    def to_apidata(self, attrvalue):
        '''
        Returns the expected value for API write
        '''

        if not isinstance(attrvalue, dict):
            raise TypeError('value is not a dict')

        if attrvalue.get('value_mode') in self.PRESET_VALUE_MODES:
            return attrvalue.get('value_mode')
        elif attrvalue.get('relative_value') in (None, ''):
            return ''
        else:
            return '%s%s' % (attrvalue['relative_value'], attrvalue.get('units') or '')




class IntByteField(FloatByteField):
    '''
    Represents a integer byte value.  See description for FloatByteField for
    full usage information.
    '''

    def from_apidata(self, api_dict, attrname):
        output = super(IntByteField, self).from_apidata(api_dict, attrname)

        try:
            output['byte_value'] = int(output['byte_value'])
            output['relative_value'] = int(output['relative_value'])
        except TypeError:
            pass

        return output


    def to_apidata(self, attrvalue):
        output = super(IntByteField, self).to_apidata(attrvalue)

        if attrvalue.get('value_mode') in self.PRESET_VALUE_MODES:
            return attrvalue.get('value_mode')
        elif attrvalue.get('relative_value') in (None, ''):
            return ''
        else:
            return '%s%s' % (int(float(attrvalue['relative_value'])), attrvalue.get('units') or '')

