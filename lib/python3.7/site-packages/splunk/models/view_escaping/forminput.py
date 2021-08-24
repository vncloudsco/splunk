from __future__ import absolute_import
from builtins import object

import csv
import logging
import inspect
import sys
if sys.version_info >= (3, 0):
    from io import StringIO
else:
    from StringIO import StringIO

from splunk.appserver.mrsparkle.lib import times
from splunk.models.view_escaping.base import STRING_SEARCH_MODE, SAVED_SEARCH_MODE
from splunk.models.view_escaping.drilldown import parseEventHandler
from splunk.models.view_escaping.search import Search, createSearchFromSearchXml
from splunk.models.view_escaping.tokendeps import parseTokenDeps
import splunk.util



logger = logging.getLogger('splunk.models.legacy_views.forminput')


def createInput(name, defaults):
    '''
    Factory method for creating an appropriate input object based upon the
    matchTypeName.  Returns an instance of a BaseInput subclass, or throws a
    NotImplementedError if no suitable mapper is found.

    This method works by inspecting all objects that subclcass BaseInput and
    attempting to match their matchTagName class attribute.
    '''

    # set default as text box
    if name is None:
        return TextInput(defaults)

    for key, obj in list(globals().items()):
        if inspect.isclass(obj) and issubclass(obj, BaseInput) and key[-5:] == 'Input':
            if hasattr(obj, 'matchTagName') and name == obj.matchTagName:
                return obj(defaults)
    raise NotImplementedError(
        'Cannot find object mapper for input type: %s' % name)


class BaseInput(object):
    '''
    Represents the base class for all form search input view objects.  These
    objects are used in constructing a search to dispatch to splunkd.  All
    input objects can be set statically, and some input objects can be
    dynamically populated at runtime.
    '''


    def __init__(self, defaults={}):

        self.token = None
        self.label = None
        self.defaultValue = None
        self.initialValue = None
        self.prefixValue = None
        self.suffixValue = None
        self.commonNodeMap = [
            ('label', 'label'),
            ('default', 'defaultValue'),
            ('initialValue', 'initialValue'),
            ('prefix', 'prefixValue'),
            ('suffix', 'suffixValue'),
            ('searchName', 'searchCommand')
        ]

        # init standard search configuration params

        self.searchWhenChanged = defaults['searchWhenChanged'] if 'searchWhenChanged' in defaults else None

        self.options = {}
        self.id = None
        self.tokenDeps = None

        # Conditions/actions for input change events
        self.inputChange = []

    def fromXml(self, inputNode, sourceApp):

        self.token = inputNode.get('token')
        self.id = inputNode.get('id')

        for pair in self.commonNodeMap:
            setattr(self, pair[1], inputNode.findtext(pair[0]))

        if getattr(self, 'initialValue', None) is None:
            setattr(self, 'initialValue', inputNode.findtext('seed'))

        if self.label is None:
            self.label = self.token

        self.searchWhenChanged = splunk.util.normalizeBoolean(
            inputNode.get('searchWhenChanged', self.searchWhenChanged))

        self.tokenDeps = parseTokenDeps(inputNode)

        inputChangeHandler = inputNode.find('change')
        if inputChangeHandler is not None:
            self.inputChange = parseEventHandler(inputChangeHandler, ('value', 'label'))


class TextInput(BaseInput):
    '''
    Represents a single text field input.
    '''
    matchTagName = 'text'


class InternalSearchInput(BaseInput):

    def __init__(self, defaults):
        BaseInput.__init__(self, defaults)

        self.search = None
        self.settingToCreate = None
        self.staticFields = []
        self.searchFields = []
        self.selectFirstChoice = False

    def fromXml(self, lxmlNode, sourceApp):
        BaseInput.fromXml(self, lxmlNode, sourceApp)

        for item in lxmlNode.findall('choice'):
            value = item.get('value')
            staticField = {
                'label': item.text
            }
            if value != None:
                staticField['value'] = value
            else:
                staticField['value'] = item.text
            self.staticFields.append(staticField)

        searchNode = lxmlNode.find('search')
        search = createSearchFromSearchXml(searchNode) if searchNode is not None else None
        if search:
            self.search = search
            self.extractSearchFields(lxmlNode)
        else:
            node = lxmlNode.find('populatingSearch')
            if node is not None:
                self.extractLegacySearchFields(node)

                opts = {}
                opts['earliestTime'] = node.get('earliest')
                opts['latestTime'] = node.get('latest')
                opts['searchCommand'] = node.text.strip()
                opts['searchMode'] = STRING_SEARCH_MODE
                self.search = Search(**opts)
            else:
                node = lxmlNode.find('populatingSavedSearch')
                if node is not None:
                    self.extractLegacySearchFields(node)

                    opts = {}
                    opts['searchCommand'] = node.text.strip()
                    opts['searchMode'] = SAVED_SEARCH_MODE
                    self.search = Search(**opts)

        # SPL-64605 Normalize the default selection - prefers value over label
        if not self.search and self.defaultValue:
            found_default = False
            for choice in self.staticFields:
                if choice['value'] == self.defaultValue:
                    found_default = True
                    break
            if not found_default:
                for choice in self.staticFields:
                    if choice['label'] == self.defaultValue:
                        # Translate the label to its corresponding value
                        self.defaultValue = choice['value']
                        break

        # SPL-79171 allow the user to specify whether the first choice is selected by default
        selectFirstChoiceNode = lxmlNode.find('selectFirstChoice')
        if selectFirstChoiceNode is not None:
            try:
                self.selectFirstChoice = splunk.util.normalizeBoolean(selectFirstChoiceNode.text, enableStrictMode=True)
            except ValueError:
                logger.warn('Invalid boolean "%s" for selectFirstChoice', self.selectFirstChoice)
                self.selectFirstChoice = False

    def extractLegacySearchFields(self, node):
        searchField = {
            'label': node.get('fieldForLabel')
        }
        value = node.get('fieldForValue')
        if value:
            searchField['value'] = value
        self.searchFields.append(searchField)

    def extractSearchFields(self, node):
        searchField = {
            'label': node.findtext('fieldForLabel')
        }
        value = node.findtext('fieldForValue')
        if value:
            searchField['value'] = value
        self.searchFields.append(searchField)


class DropdownInput(InternalSearchInput):
    '''
    Represents a select dropdown input.  This element can have its options
    populated via a saved search, or other entity list.
    '''

    matchTagName = 'dropdown'

    def __init__(self, defaults):
        InternalSearchInput.__init__(self, defaults)
        self.commonNodeMap.append(('allowCustomValues', 'allowCustomValues'))
        self.selected = None
        self.showClearButton = True

    def fromXml(self, lxmlNode, sourceApp):
        InternalSearchInput.fromXml(self, lxmlNode, sourceApp)
        if hasattr(self, 'allowCustomValues'):
            self.allowCustomValues = splunk.util.normalizeBoolean(self.allowCustomValues)
        showClearButton = lxmlNode.findtext('showClearButton')
        if showClearButton:
            self.showClearButton = splunk.util.normalizeBoolean(showClearButton)


class RadioInput(InternalSearchInput):
    '''
    Represents a set of one or more radio button inputs.  This element
    can have its options populated via a saved search, or other entity list.
    '''
    matchTagName = 'radio'

    def __init__(self, defaults):
        InternalSearchInput.__init__(self, defaults)
        self.name = None
        self.checked = None

    def fromXml(self, lxmlNode, sourceApp):
        InternalSearchInput.fromXml(self, lxmlNode, sourceApp)
        self.name = '_'.join([self.token, 'name'])


class LinkInput(InternalSearchInput):
    '''
    Represents a set of one or more links.  This element
    can have its options populated via a saved search, or other entity list.
    '''
    matchTagName = 'link'

    def __init__(self, defaults):
        InternalSearchInput.__init__(self, defaults)
        self.name = None
        self.checked = None

    def fromXml(self, lxmlNode, sourceApp):
        InternalSearchInput.fromXml(self, lxmlNode, sourceApp)
        self.name = '_'.join([self.token, 'name'])


class TimeInput(BaseInput):
    '''
    Represents a timerange selection input.
    '''
    matchTagName = 'time'

    def __init__(self, defaults):
        BaseInput.__init__(self, defaults)
        self.selected = None
        self.label = None

    def fromXml(self, lxmlNode, sourceApp):
        BaseInput.fromXml(self, lxmlNode, sourceApp)
        self.searchWhenChanged = splunk.util.normalizeBoolean(lxmlNode.get('searchWhenChanged', self.searchWhenChanged))
        selected = lxmlNode.find('default')
        if selected is not None:
            et, lt = selected.find('earliestTime'), selected.find('latestTime')
            earliest, latest = selected.find('earliest'), selected.find('latest')
            if earliest is not None or latest is not None:
                self.selected = dict(
                    earliestTime=earliest.text if earliest is not None else None,
                    latestTime=latest.text if latest is not None else None
                )
            elif et is not None or lt is not None:
                self.selected = dict(
                    earliestTime=et.text if et is not None else None,
                    latestTime=lt.text if lt is not None else None
                )
            elif selected.text:
                self.selected = selected.text.strip()
                appTimes = times.getTimeRanges(sourceApp)
                for time in appTimes:
                    if time['label'].strip() == self.selected:
                        self.selected = dict(
                            earliestTime=time.get('earliest_time', None),
                            latestTime=time.get('latest_time', None)
                        )
                        break
                else:
                    self.selected = dict(
                        earliestTime=0,
                        latestTime=None
                    )
            else:
                self.selected = dict(
                    earliestTime=0,
                    latestTime=None
                )
        label = lxmlNode.find('label')
        if label is not None:
            self.label = label.text


class MultiValueSearchInput(InternalSearchInput):
    """
    Represents a search input that will have an array as a value.
    <input type="multiselect" token="my_multiselect">
        <label> Choose Sourcetype:</label>
        <choice value="*">All</choice>
        <option name="prefix">q=[</option>
        <option name="suffix">]</option>
        <option name="value_prefix">sourcetype="</option>
        <option name="value_suffix">"</option>
        <option name="delimiter"> </option>
        <option name="minCount">1</option>
        <option name="showSelectAll">true</option>    <!-- Enable users to have quick select and deselect all links -->
        <option name="showDeselectAll">true</option>
        <option name="width">5</option>   <!-- width; allow users to configure width based on length of values and #  -->
        <populatingSearch fieldForLabel="sourcetype" fieldForValue="sourcetype" earliest="-24h" latest="now">index=_internal | stats count by sourcetype
        </populatingSearch>
        <default>NULL</default>            <!-- if default set to NULL, then submit token should be null -->
    </input>
    """

    def __init__(self, defaults):
        InternalSearchInput.__init__(self, defaults)
        self.selected = None
        self.label = None
        self.valuePrefix = ""
        self.valueSuffix = ""
        self.delimiter = " "
        self.minCount = None
        self.showSelectAl = False
        self.showDeselectAll = False
        self.width = None
        self.commonNodeMap.append(('default', 'selected'))
        self.commonNodeMap.append(('valuePrefix', 'valuePrefix'))
        self.commonNodeMap.append(('valueSuffix', 'valueSuffix'))
        self.commonNodeMap.append(('delimiter', 'delimiter'))
        self.commonNodeMap.append(('minCount', 'minCount'))
        self.commonNodeMap.append(('showSelectAll', 'showSelectAll'))
        self.commonNodeMap.append(('showDeselectAll', 'showDeselectAll'))
        self.commonNodeMap.append(('width', 'width'))
        self.commonNodeMap.append(('allowCustomValues', 'allowCustomValues'))

    def fromXml(self, lxmlNode, sourceApp):
        InternalSearchInput.fromXml(self, lxmlNode, sourceApp)
        for k in ['defaultValue', 'initialValue']:
            value = getattr(self, k, None)
            if value is not None:
                reader = csv.reader(StringIO(value.strip()), delimiter=',')
                values = [item.strip() for row in reader for item in row]
                if len(values):
                    setattr(self, k, values)


class MultiSelectInput(MultiValueSearchInput):
    """
    Represents a multiple selection input.
    """
    matchTagName = 'multiselect'

    def fromXml(self, lxmlNode, sourceApp):
        MultiValueSearchInput.fromXml(self, lxmlNode, sourceApp)
        if hasattr(self, 'allowCustomValues'):
            self.allowCustomValues = splunk.util.normalizeBoolean(self.allowCustomValues)


class CheckboxGroupInput(MultiValueSearchInput):
    """
    Represents a group of checkbox input.
    """
    matchTagName = 'checkbox'


if __name__ == '__main__':
    import unittest
    import lxml.etree as et

    nodeMap = [
        ('label', 'label'),
        ('default', 'defaultValue'),
        ('initialValue', 'initialValue'),
        ('prefix', 'prefixValue'),
        ('suffix', 'suffixValue'),
        ('searchName', 'searchCommand'),
        ('default', 'selected'),
        ('valuePrefix', 'valuePrefix'),
        ('valueSuffix', 'valueSuffix'),
        ('delimiter', 'delimiter'),
        ('minCount', 'minCount'),
        ('showSelectAll', 'showSelectAll'),
        ('showDeselectAll', 'showDeselectAll'),
        ('width', 'width'),
        ('allowCustomValues', 'allowCustomValues')
    ]

    class MultiValueInputTests(unittest.TestCase):

        def testMultiSelectInput(self):
            multiSelectInput = MultiSelectInput(dict())
            self.assertItemsEqual(nodeMap, multiSelectInput.commonNodeMap)
            self.assertEqual("multiselect", multiSelectInput.matchTagName)

    class CheckboxInputTests(unittest.TestCase):

        def testCheckboxInput(self):
            checkboxGroupInput = CheckboxGroupInput(dict())
            self.assertItemsEqual(nodeMap, checkboxGroupInput.commonNodeMap)
            self.assertEqual("checkbox", checkboxGroupInput.matchTagName)

    class SelectFirstChoiceTests(unittest.TestCase):
        def testParseSelectFirstChoice(self):
            node = et.fromstring('<input type="dropdown" token="foo" />')
            item = createInput(node.attrib.get('type'), defaults=dict())
            item.fromXml(node, 'fake')
            self.assertFalse(item.selectFirstChoice) # pylint: disable=E1103

            node = et.fromstring('<input type="dropdown" token="foo">'
                                 '<selectFirstChoice>true</selectFirstChoice>'
                                 '</input>')
            item = createInput(node.attrib.get('type'), defaults=dict())
            item.fromXml(node, 'fake')
            self.assertTrue(item.selectFirstChoice) # pylint: disable=E1103

            node = et.fromstring('<input type="dropdown" token="foo">'
                                 '<selectFirstChoice>1</selectFirstChoice>'
                                 '</input>')
            item = createInput(node.attrib.get('type'), defaults=dict())
            item.fromXml(node, 'fake')
            self.assertTrue(item.selectFirstChoice) # pylint: disable=E1103

            node = et.fromstring('<input type="dropdown" token="foo">'
                                 '<selectFirstChoice>0</selectFirstChoice>'
                                 '</input>')
            item = createInput(node.attrib.get('type'), defaults=dict())
            item.fromXml(node, 'fake')
            self.assertFalse(item.selectFirstChoice) # pylint: disable=E1103

            node = et.fromstring('<input type="dropdown" token="foo">'
                                 '<selectFirstChoice>foobar</selectFirstChoice>'
                                 '</input>')
            item = createInput(node.attrib.get('type'), defaults=dict())
            item.fromXml(node, 'fake')
            self.assertFalse(item.selectFirstChoice) # pylint: disable=E1103

            # first occurrence of <selectFirstChoice> takes precedence
            node = et.fromstring('<input type="dropdown" token="foo">'
                                 '<selectFirstChoice>foobar</selectFirstChoice>'
                                 '<selectFirstChoice>true</selectFirstChoice>'
                                 '</input>')
            item = createInput(node.attrib.get('type'), defaults=dict())
            item.fromXml(node, 'fake')
            self.assertFalse(item.selectFirstChoice) # pylint: disable=E1103

            node = et.fromstring('<input type="dropdown" token="foo">'
                                 '<selectFirstChoice></selectFirstChoice>'
                                 '</input>')
            item = createInput(node.attrib.get('type'), defaults=dict())
            item.fromXml(node, 'fake')
            self.assertFalse(item.selectFirstChoice) # pylint: disable=E1103

            node = et.fromstring('<input type="dropdown" token="foo">'
                                 '<selectFirstChoice />'
                                 '</input>')
            item = createInput(node.attrib.get('type'), defaults=dict())
            item.fromXml(node, 'fake')
            self.assertFalse(item.selectFirstChoice) # pylint: disable=E1103

    class InputChangeEventHandlerTests(unittest.TestCase):
        def testParseSimpleChangeAction(self):
            result = createInput('text', defaults=dict())
            result.fromXml(et.fromstring(
                '<input type="text" token="foo">'
                    '<change>'
                        '<set token="foo">bar</set>'
                    '</change>'
                  '</input>'
            ), sourceApp="fake")
            self.assertEqual(result.token, 'foo')
            self.assertEqual(len(result.inputChange), 1)
            self.assertEqual(result.inputChange[0].value, '*')
            self.assertEqual(result.inputChange[0].attr, 'value')

        def testParseConditionalChangeActions(self):
            result = createInput('text', defaults=dict())
            result.fromXml(et.fromstring(
                '<input type="text" token="foo">'
                    '<change>'
                        '<condition value="val1">'
                            '<set token="bar">ding</set>'
                        '</condition>'
                        '<condition value="val2">'
                            '<set token="bar">ding</set>'
                        '</condition>'
                        '<condition label="LABEL1">'
                            '<set token="bar">ding</set>'
                        '</condition>'
                    '</change>'
                  '</input>'
            ), sourceApp="fake")
            self.assertEqual(result.token, 'foo')
            self.assertEqual(len(result.inputChange), 3)
            self.assertEqual(result.inputChange[0].attr, 'value')
            self.assertEqual(result.inputChange[0].value, 'val1')
            self.assertEqual(len(result.inputChange[0].actions), 1)
            self.assertEqual(result.inputChange[0].actions[0].type, 'settoken')
            self.assertEqual(result.inputChange[0].actions[0].name, 'bar')
            self.assertEqual(result.inputChange[0].actions[0].template, 'ding')
            self.assertEqual(result.inputChange[1].attr, 'value')
            self.assertEqual(result.inputChange[1].value, 'val2')
            self.assertEqual(len(result.inputChange[1].actions), 1)
            self.assertEqual(result.inputChange[1].actions[0].type, 'settoken')
            self.assertEqual(result.inputChange[2].attr, 'label')
            self.assertEqual(result.inputChange[2].value, 'LABEL1')
            self.assertEqual(len(result.inputChange[2].actions), 1)
            self.assertEqual(result.inputChange[2].actions[0].type, 'settoken')

    class TokenDepsTests(unittest.TestCase):
        def testTokenDeps(self):
            input = createInput('text', defaults=dict())
            input.fromXml(et.fromstring(
                '<input type="text" token="foo" depends="$bar$">'
                '</input>'
            ), sourceApp="fake")

            self.assertIsNotNone(input.tokenDeps)
            self.assertEquals(input.tokenDeps.depends, '$bar$')
            self.assertEquals(input.tokenDeps.rejects, '')

    class TimeInputTests(unittest.TestCase):
        def testTokenDeps(self):
            input = createInput('time', defaults=dict())
            input.fromXml(et.fromstring(
                '<input type="time" token="foo">'
                '<default>'
                '<earliest>-15m</earliest>'
                '</default>'
                '</input>'
            ), sourceApp="fake")

            self.assertEqual(input.selected['earliestTime'], '-15m')
            self.assertEqual(input.selected['latestTime'], None)

            input = createInput('time', defaults=dict())
            input.fromXml(et.fromstring(
                '<input type="time" token="foo">'
                '<default>'
                '<latest>-15m</latest>'
                '</default>'
                '</input>'
            ), sourceApp="fake")

            self.assertEqual(input.selected['latestTime'], '-15m')
            self.assertEqual(input.selected['earliestTime'], None)

            input = createInput('time', defaults=dict())
            input.fromXml(et.fromstring(
                '<input type="time" token="foo">'
                '<default>'
                '<earliest>-15m</earliest>'
                '<latest>-15m</latest>'
                '</default>'
                '</input>'
            ), sourceApp="fake")

            self.assertEqual(input.selected['latestTime'], '-15m')
            self.assertEqual(input.selected['earliestTime'], '-15m')

            input = createInput('time', defaults=dict())
            input.fromXml(et.fromstring(
                '<input type="time" token="foo">'
                '<default>'
                '<earliestTime>-15m</earliestTime>'
                '</default>'
                '</input>'
            ), sourceApp="fake")

            self.assertEqual(input.selected['earliestTime'], '-15m')
            self.assertEqual(input.selected['latestTime'], None)

            input = createInput('time', defaults=dict())
            input.fromXml(et.fromstring(
                '<input type="time" token="foo">'
                '<default>'
                '<latestTime>-15m</latestTime>'
                '</default>'
                '</input>'
            ), sourceApp="fake")

            self.assertEqual(input.selected['latestTime'], '-15m')
            self.assertEqual(input.selected['earliestTime'], None)

            input = createInput('time', defaults=dict())
            input.fromXml(et.fromstring(
                '<input type="time" token="foo">'
                '<default>'
                '<latestTime>-15m</latestTime>'
                '<earliestTime>-15m</earliestTime>'
                '</default>'
                '</input>'
            ), sourceApp="fake")

            self.assertEqual(input.selected['latestTime'], '-15m')
            self.assertEqual(input.selected['earliestTime'], '-15m')

            input = createInput('time', defaults=dict())
            input.fromXml(et.fromstring(
                '<input type="time" token="foo">'
                '<default>'
                '<latestTime>-15m</latestTime>'
                '<earliestTime>-15m</earliestTime>'
                '<latest>-24h</latest>'
                '<earliest>-24h</earliest>'
                '</default>'
                '</input>'
            ), sourceApp="fake")

            self.assertEqual(input.selected['latestTime'], '-24h')
            self.assertEqual(input.selected['earliestTime'], '-24h')




    loader = unittest.TestLoader()
    suites = [loader.loadTestsFromTestCase(test) for test in (
        MultiValueInputTests, CheckboxInputTests, SelectFirstChoiceTests, InputChangeEventHandlerTests, TokenDepsTests, TimeInputTests
    )]
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
