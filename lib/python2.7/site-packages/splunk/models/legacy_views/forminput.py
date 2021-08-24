from __future__ import absolute_import
import lxml.etree as et

import splunk.models.legacy_views.base as base
import splunk.util

import logging
logger = logging.getLogger('splunk.models.legacy_views.forminput')


def createInput(name):
    '''
    Factory method for creating an appropriate input object based upon the
    matchTypeName.  Returns an instance of a BaseInput subclass, or throws a
    NotImplementedError if no suitable mapper is found.
    
    This method works by inspecting all objects that subclcass BaseInput and
    attempting to match their matchTagName class attribute.
    '''
    
    # set default as text box
    if name == None:
        return TextInput()
        
    for obj in globals().values():
        try:
            if issubclass(obj, BaseInput) and name == obj.matchTagName:
                return obj()
        except:
            pass
    raise NotImplementedError('Cannot find object mapper for input type: %s' % name)



class BaseInput(base.ViewObject):
    '''
    Represents the base class for all form search input view objects.  These
    objects are used in constructing a search to dispatch to splunkd.  All
    input objects can be set statically, and some input objects can be
    dynamically populated at runtime.
    '''
    
    commonNodeMap = [
        ('label', 'label'),
        ('default', 'defaultValue'),
        ('seed', 'seedValue'),
        ('prefix', 'prefixValue'),
        ('suffix', 'suffixValue'),
        ('searchName', 'searchCommand')
    ]
    
    def __init__(self):

        self.token = None
        self.label = None
        self.defaultValue = None
        self.seedValue = None
        self.prefixValue = None
        self.suffixValue = None
        
        # init standard search configuration params
        self.searchMode = base.SAVED_SEARCH_MODE
        self.searchCommand = None
        
        self.options = {}
        
        
    def fromXml(self, lxmlNode):
        
        self.token = lxmlNode.get('token')
        
        for pair in self.commonNodeMap:
            setattr(self, pair[1], lxmlNode.findtext(pair[0]))
            
        if self.label == None:
            self.label = self.token
            
    
    def toXml(self):
        
        root = et.Element('input')
        root.set('type', self.matchTagName)

        if self.token:
            root.set('token', self.token)
            
        for pair in self.commonNodeMap:
            if getattr(self, pair[1]) != None:
                et.SubElement(root, pair[0]).text = getattr(self, pair[1])
                
        return root
        

            
class TextInput(BaseInput):
    '''
    Represents a single text field input.
    '''
    
    matchTagName = 'text'
    
    def toObject(self):
        
        output = {
            'className': 'ExtendedFieldSearch',
            'params': {
                'field': self.label,
                'intention': {
                    'name': 'stringreplace', 
                    'arg': {
                        self.token: {
                            'default': self.defaultValue,
                            'fillOnEmpty': True,
                            'prefix': self.prefixValue or '',
                            'suffix': self.suffixValue or ''
                        }
                    }
                },
                'replacementMap': {
                    'arg': {
                        self.token: {'value': None}
                    }
                },
                'q': self.seedValue or '',
                'default': self.defaultValue or ''
            },
            'children': []
        }
        
        return output


class InternalSearchInput(BaseInput):

    def __init__(self):
        BaseInput.__init__(self)
        
        self.localCommonNodeMap = [
            ('populatingSearch', 'search'),
            ('populatingSavedSearch', 'savedSearch')
        ]
        
        self.search = None
        self.savedSearch = None
        self.settingToCreate = None
        self.staticFields = []
        self.searchFields = []
        self.searchWhenChanged = False
        self.earliest = None
        self.latest = None

    def fromXml(self, lxmlNode):
        BaseInput.fromXml(self, lxmlNode)

        for item in lxmlNode.findall('choice'):
            value = item.get('value')
            staticField = {
                'label': item.text
            }
            if value: staticField['value'] = value
            self.staticFields.append(staticField)
        
        for pair in self.localCommonNodeMap:
            if pair[0] == 'populatingSearch':
                node = lxmlNode.find(pair[0])
                if node != None:
                    searchField = {
                        'label': node.get('fieldForLabel')
                    }
                    value = node.get('fieldForValue')
                    if value: searchField['value'] = value
                    self.searchFields.append(searchField)
                    
                    self.earliest = node.get('earliest')
                    self.latest = node.get('latest')
                    
                    
            elif pair[0] == 'populatingSavedSearch':
                node = lxmlNode.find(pair[0])
                if node != None:
                    searchField = {
                        'label': node.get('fieldForLabel')
                    }
                    value = node.get('fieldForValue')
                    if value: searchField['value'] = value
                    self.searchFields.append(searchField)

            setattr(self, pair[1], lxmlNode.findtext(pair[0]))
   
        self.settingToCreate = '_'.join([self.token, 'setting'])
        self.searchWhenChanged = splunk.util.normalizeBoolean(lxmlNode.get('searchWhenChanged', False))
    
    def toObject(self, staticName, dynamicName):

        static = {
            'className': staticName,
            'params': {
                'settingToCreate': self.settingToCreate,
                'label': self.label,
                'staticFieldsToDisplay': self.staticFields,
                'searchWhenChanged': self.searchWhenChanged
            }
        }

        dynamic = {
            'className': dynamicName,
            'params': {
                'settingToCreate': self.settingToCreate,
                'label': self.label,
                'searchFieldsToDisplay': self.searchFields,
                'staticFieldsToDisplay': self.staticFields,
                'searchWhenChanged': self.searchWhenChanged
            }
        }
        
        if self.search:
            dynamic['params']['search'] = self.search
            if self.earliest: dynamic['params']['earliest'] = self.earliest
            if self.latest: dynamic['params']['latest'] = self.latest
            
        elif self.savedSearch:
            dynamic['params']['savedSearch'] = self.savedSearch

        children = [
            {
                'className': 'ConvertToIntention',
                'params': {
                    'settingToConvert': self.settingToCreate,
                    'intention': {
                        'name': 'stringreplace',
                        'arg': {
                            self.token: {
                                'value': '$target$',
                                'default': self.defaultValue,
                                'fillOnEmpty': True,
                                'prefix': self.prefixValue or '',
                                'suffix': self.suffixValue or ''
                            }
                        }
                    }
                },
                'children': []
            }
        ]

        output = {}
        if len(self.searchFields) == 0 and len(self.staticFields) > 0 and self.search == None:
            output = static
        else:
            output = dynamic
        output['children'] = children

        return (output, output['children'][0]['children'])


    def toXml(self):
        '''Returns a valid, simplified XML representation of the current object.'''
        root = BaseInput.toXml(self)
        
        for pair in self.localCommonNodeMap:
            if getattr(self, pair[1]) != None:
                attr = et.SubElement(root, pair[0])
                attr.text = str(getattr(self, pair[1]))
                
                if pair[0] == 'populatingSearch':
                    if self.earliest:
                        attr.set('earliest', self.earliest)
                        
                    if self.latest:
                        attr.set('latest', self.latest)

                if pair[0] == 'populatingSearch' or pair[0] == 'populatingSavedSearch':
                    if len(self.searchFields) > 0:
                        for fields in self.searchFields:
                            for key in fields:
                                if key == 'label':
                                    attr.set('fieldForLabel', fields[key])
                                
                                elif key == 'value':
                                    attr.set('fieldForValue', fields[key])
                                    
        for choice in self.staticFields:
            attr = et.SubElement(root, 'choice')
            attr.text = choice['label']
            attr.set('value', choice['value'])
            
        if self.searchWhenChanged:
            root.set('searchWhenChanged', "True")
            
        return root        

 
class DropdownInput(InternalSearchInput):
    '''
    Represents a select dropdown input.  This element can have its options
    populated via a saved search, or other entity list.
    '''
    
    matchTagName = 'dropdown'
    
    def __init__(self):
        InternalSearchInput.__init__(self)
        self.selected = None
        self.localCommonNodeMap.append(('default', 'selected'))

    def toObject(self):
        output, child = InternalSearchInput.toObject(self, 'StaticSelect', 'SearchSelectLister')

        output['params']['selected'] = self.selected

        return (output, child)

        
class RadioInput(InternalSearchInput):
    '''
    Represents a set of one or more radio button inputs.  This element 
    can have its options populated via a saved search, or other entity list.
    '''

    matchTagName = 'radio'

    def __init__(self):
        InternalSearchInput.__init__(self)
        self.name = None
        self.checked = None
        self.localCommonNodeMap.append(('default', 'checked'))

    def fromXml(self, lxmlNode):
        InternalSearchInput.fromXml(self, lxmlNode)
        self.name = '_'.join([self.token, 'name'])
    
    def toObject(self):
        output, child = InternalSearchInput.toObject(self, 'StaticRadio', 'SearchRadioLister')
        
        output['params']['name'] = self.name
        output['params']['checked'] = self.checked
        
        return (output, child)


class CheckboxInput(BaseInput):
    '''
    Represents a single checkbox input.
    '''

    matchTagName = 'checkbox'

    def toObject(self):
        pass
        
        
class TimeInput(BaseInput):
    '''
    Represents a timerange selection input.
    '''

    matchTagName = 'time'
    
    def __init__(self):
        BaseInput.__init__(self)
        self.searchWhenChanged = False
        self.selected = None
        self.label = None
    
    def fromXml(self, lxmlNode):
        BaseInput.fromXml(self, lxmlNode)
        self.searchWhenChanged = splunk.util.normalizeBoolean(lxmlNode.get('searchWhenChanged', False))
        selected = lxmlNode.find('default')
        if selected != None:
            self.selected = selected.text
        label = lxmlNode.find('label')
        if label != None:
            self.label = label.text

    def toObject(self):

        output = {
            'className': 'TimeRangePicker',
            'params': {
                'searchWhenChanged': self.searchWhenChanged
            },
            'children': []
        }
        
        if self.selected != None:
            output['params']['selected'] = self.selected
        if self.label != None:
            output['params']['label'] = self.label
        return output




if __name__ == '__main__':
    import unittest
    from lxml import etree as et
    
    class DropdownInputTests(unittest.TestCase):
        
        def test_serization(self):
            xml = '''<input type="dropdown" token="username" searchWhenChanged="True">
                        <label>Select name</label>
                        <default>Nate</default>
                        <choice value="*">Any</choice>
                        <choice value="nagrin">Nate</choice>
                        <choice value="amrit">Amrit</choice>
                        <populatingSearch earliest="-40m" latest="-10m" fieldForValue="foo" fieldForLabel="bar">search foo bar</populatingSearch>
                    </input>'''
    
            di1 = DropdownInput()
            di1.fromXml(et.fromstring(xml))
            
            xml2 = et.tostring(di1.toXml())
            
            di2 = DropdownInput()
            di2.fromXml(et.fromstring(xml2))
            
            self.assertEqual(di1.search, di2.search)
            self.assertEqual(di1.earliest, di2.earliest)
            self.assertEqual(di1.latest, di2.latest)
            self.assertEqual(di1.searchWhenChanged, di2.searchWhenChanged)
            self.assertEqual(di1.staticFields, di2.staticFields)
            self.assertEqual(di1.searchFields, di2.searchFields)
            self.assertEqual(di1.selected, di2.selected)
            self.assertEqual(di1.savedSearch, di2.savedSearch)
            
    class RadioInputTests(unittest.TestCase):
        
        def test_serialization(self):
            xml = '''<input type="radio" token="username" searchWhenChanged="True">
                        <label>Select name</label>
                        <default>Nate</default>
                        <choice value="*">Any</choice>
                        <choice value="nagrin">Nate</choice>
                        <choice value="amrit">Amrit</choice>
                        <populatingSearch earliest="-40m" latest="-10m" fieldForValue="foo" fieldForLabel="bar">search foo bar</populatingSearch>
                    </input>'''
    
            di1 = RadioInput()
            di1.fromXml(et.fromstring(xml))
            
            xml2 = et.tostring(di1.toXml())
            
            di2 = RadioInput()
            di2.fromXml(et.fromstring(xml2))
            
            self.assertEqual(di1.search, di2.search)
            self.assertEqual(di1.earliest, di2.earliest)
            self.assertEqual(di1.latest, di2.latest)
            self.assertEqual(di1.searchWhenChanged, di2.searchWhenChanged)
            self.assertEqual(di1.staticFields, di2.staticFields)
            self.assertEqual(di1.searchFields, di2.searchFields)
            self.assertEqual(di1.checked, di2.checked)
            self.assertEqual(di1.name, di2.name)
            self.assertEqual(di1.savedSearch, di2.savedSearch)

    # exec all tests
    suites = [
        DropdownInputTests,
        RadioInputTests
    ]
    
    loader = unittest.TestLoader()
    loaded = []
    for suite in suites:
        loaded.append(loader.loadTestsFromTestCase(suite))
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(loaded))
