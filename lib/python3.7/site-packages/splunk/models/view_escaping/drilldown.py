from __future__ import absolute_import

from builtins import object
import logging
import lxml.etree as et


logger = logging.getLogger('splunk.models.view_escaping.drilldown')

EXPLICT_CONDITION = True
IMPLICIT_CONDITION = False


def parseDrilldownAction(node, defaultLinkTarget=None):
    if node.tag == 'set':
        name = node.attrib.get('token', '').strip()
        if not name:
            logger.warn('Ignoring token action without token name %s', et.tostring(node))
            return
        if node.text is None:
            logger.warn('Missing text template for token action node %s', et.tostring(node))
            return
        return SetToken(
            name=name,
            template=node.text.strip(),
            delimiter=node.attrib.get('delimiter', None),
            prefix=node.attrib.get('prefix', None),
            suffix=node.attrib.get('suffix', None)
        )

    elif node.tag == 'unset':
        name = node.attrib.get('token', '').strip()
        if not name:
            logger.warn('Ignoring token action without token name %s', et.tostring(node))
            return
        return UnsetToken(name=name)

    elif node.tag == 'link':
        if node.text is None:
            logger.warn('Missing text template for link action node %s', et.tostring(node))
            return
        return Link(
            link=node.text.strip().replace("\n", " "),
            target=node.attrib.get(
                'target') if 'target' in node.attrib else defaultLinkTarget
        )
    elif node.tag == 'eval':
        if node.text is None:
            logger.warn('Missing eval expression template %s', et.tostring(node))
            return
        return EvalToken(name=node.attrib.get('token'), expr=node.text.strip())
    else:
        logger.warn('Ignoring unrecognized drilldown action %s', et.tostring(node))


def checkAttrValue(attr, value, fieldMap, node):
    values = fieldMap.get(attr, None)
    if values is None:
        values = dict()
        fieldMap[attr] = values
    if value in values:
        logger.warn('Duplicate condition for %s="%s" found for drilldown. Overriding previous conditions '
                    'with %s. (line %d)', attr, value, et.tostring(node).strip().replace('\n', ' '), node.sourceline)
    else:
        values[value] = True


def parseDrilldown(drilldownNode):
    defaultTarget = drilldownNode.get('target') if (drilldownNode is not None) else None
    return parseEventHandler(drilldownNode, ('field', 'series'), defaultTarget=defaultTarget, allowLinkConditions=True)

def getConditionAttrAndValue(condNode, validAttributes, default=(None, None)):
    match = condNode.get('match', None)
    if match is not None:
        return 'match', match
    for attr in validAttributes:
        val = condNode.get(attr, None)
        if val is not None:
            return attr, val
    return default

def parseEventHandler(evtHandlerNode, validAttributes, defaultTarget=None, allowLinkConditions=False):
    results = list()
    fieldMap = dict()
    conditionsType = None
    implicitCondition = None
    defaultAttr = validAttributes[0]

    if evtHandlerNode is not None:
        for child in [node for node in evtHandlerNode if et.iselement(node) and isinstance(node.tag, str)]:
            nodeName = child.tag.lower()
            if nodeName == 'link':
                if conditionsType is None:
                    conditionsType = IMPLICIT_CONDITION
                elif conditionsType is EXPLICT_CONDITION:
                    raise AttributeError('Cannot mix <%s> with explicit <condition>s (line %d)' %
                                         (nodeName, child.sourceline))
                action = parseDrilldownAction(child, defaultLinkTarget=defaultTarget)
                if allowLinkConditions:
                    field = child.attrib.get('field')
                    series = child.attrib.get('series')
                    if not field and series:
                        field = series
                    if not field:
                        field = '*'
                    if child.text and len(child.text) == 0:
                        continue
                    if action is not None:
                        checkAttrValue(defaultAttr, field, fieldMap, child)
                        if field == '*':
                            if implicitCondition is None:
                                implicitCondition = Condition(value='*', attr=defaultAttr)
                                results.append(implicitCondition)
                            implicitCondition.add(action)
                        else:
                            results.append(Condition(value=field, attr=defaultAttr, action=action))
                else:
                    if implicitCondition is None:
                        implicitCondition = Condition(value='*', attr=defaultAttr)
                        results.append(implicitCondition)
                    implicitCondition.add(action)
                    
            elif nodeName in ('set', 'unset', 'eval'):
                if conditionsType is None:
                    conditionsType = IMPLICIT_CONDITION
                elif conditionsType is EXPLICT_CONDITION:
                    raise AttributeError('Cannot mix <%s> with explicit <condition>s' % nodeName)
                for attr in validAttributes:
                    if attr in child.attrib:
                        logger.warn('Ignoring field attribute for top-level <%s> action, assuming field="*" (line %d)',
                                                                             nodeName, child.sourceline)
                action = parseDrilldownAction(child, defaultLinkTarget=defaultTarget)
                if action is not None:
                    checkAttrValue(defaultAttr, '*', fieldMap, child)
                    if implicitCondition is None:
                        implicitCondition = Condition(value='*', attr=defaultAttr)
                        results.append(implicitCondition)
                    implicitCondition.add(action)
            elif nodeName == 'condition':
                if conditionsType is None:
                    conditionsType = EXPLICT_CONDITION
                elif conditionsType is IMPLICIT_CONDITION:
                    raise AttributeError('Cannot mix <%s> with implicit conditions (line %d)' %
                                         (nodeName, child.sourceline))
                attr, val = getConditionAttrAndValue(child, validAttributes, default=('any', '*'))
                checkAttrValue(attr, val, fieldMap, child)
                condition = Condition(val, attr=attr)
                for node in [node for node in child if et.iselement(node) and isinstance(node.tag, str)]:
                    action = parseDrilldownAction(node, defaultLinkTarget=defaultTarget)
                    if action is not None:
                        condition.add(action)

                results.append(condition)
            else:
                logger.warn('Ignoring unrecognized drilldown node "%s" (line %d)', nodeName, child.sourceline)

    return results


class Condition(object):
    def __init__(self, value, attr="field", action=None):
        self.attr = attr
        self.value = self.field = value
        self.wildcard = value == '*'
        self.actions = []
        if action is not None:
            self.add(action)

    def add(self, item):
        self.actions.append(item)


class Action(object):
    def __init__(self, drilldownType):
        self.type = drilldownType


class Link(Action):
    def __init__(self, link, target):
        Action.__init__(self, 'link')
        self.link = link
        self.target = target


class SetToken(Action):
    def __init__(self, name, template, delimiter=None, prefix="", suffix=""):
        Action.__init__(self, 'settoken')
        self.name = name
        self.template = template
        self.delimiter = delimiter
        self.prefix = prefix
        self.suffix = suffix


class UnsetToken(Action):
    def __init__(self, name):
        Action.__init__(self, 'unsettoken')
        self.name = name


class EvalToken(Action):
    def __init__(self, name, expr):
        Action.__init__(self, 'eval')
        self.name = name
        self.expr = expr


if __name__ == '__main__':
    import unittest

    class DrilldownParserTests(unittest.TestCase):
        def testParseEmptyDrilldownNode(self):
            result = parseDrilldown(et.fromstring('''<drilldown></drilldown>'''))
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 0)
            result = parseDrilldown(et.fromstring('''<drilldown />'''))
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 0)
            self.assertTrue(isinstance(result, list))
            result = parseDrilldown(et.fromstring('''<foo></foo>'''))
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 0)
            self.assertTrue(isinstance(result, list))
            result = parseDrilldown(None)
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 0)
            self.assertTrue(isinstance(result, list))

        def testParseEmptyCondition(self):
            result = parseDrilldown(et.fromstring('''
                    <drilldown>
                        <condition field="foo"></condition>
                    </drilldown>
                '''))
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 1)
            cond = result[0]
            self.assertEqual(cond.field, 'foo')
            self.assertEqual(len(cond.actions), 0)

        def testParseSimpleLinkNodes(self):
            result = parseDrilldown(et.fromstring('''
            
                <drilldown>
                    <link field="foo">/foo/bar</link>
                    <link field="bar" target="_blank">/foo/bar</link>
                </drilldown>
            '''))
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 2)
            cond = result[0]
            self.assertEqual(cond.field, 'foo')
            self.assertEqual(len(cond.actions), 1)
            self.assertTrue(isinstance(cond.actions[0], Link))
            self.assertEqual(cond.actions[0].link, '/foo/bar')
            self.assertEqual(cond.actions[0].target, None)
            cond = result[1]
            self.assertEqual(cond.field, 'bar')
            self.assertEqual(len(cond.actions), 1)
            self.assertEqual(cond.actions[0].type, 'link')
            self.assertEqual(cond.actions[0].link, '/foo/bar')
            self.assertEqual(cond.actions[0].target, '_blank')

        def testParseLinkInCondition(self):
            result = parseDrilldown(et.fromstring('''
            
                <drilldown>
                    <condition field="foo">
                        <link>/foo/bar</link>
                    </condition>
                    <condition field="bar">
                        <link target="_blank">/foo/bar</link>
                    </condition>
                </drilldown>
            '''))
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 2)
            cond = result[0]
            self.assertEqual(cond.field, 'foo')
            self.assertEqual(len(cond.actions), 1)
            self.assertTrue(isinstance(cond.actions[0], Link))
            self.assertEqual(cond.actions[0].link, '/foo/bar')
            self.assertEqual(cond.actions[0].target, None)
            cond = result[1]
            self.assertEqual(cond.field, 'bar')
            self.assertEqual(len(cond.actions), 1)
            self.assertEqual(cond.actions[0].type, 'link')
            self.assertEqual(cond.actions[0].link, '/foo/bar')
            self.assertEqual(cond.actions[0].target, '_blank')

        def testParseTokenInCondition(self):
            result = parseDrilldown(et.fromstring('''
                <drilldown>
                    <condition field="*">
                        <set token="foo">$click.value$</set>
                        <set token="foobar">
                            $click.value$
                        </set>
                        <unset token="bar" />
                    </condition>
                </drilldown>
            '''))
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 1)
            cond = result[0]
            self.assertEqual(len(cond.actions), 3)
            action = cond.actions[0]
            self.assertEqual(action.type, 'settoken')
            self.assertEqual(action.name, 'foo')
            self.assertEqual(action.template, '$click.value$')
            action = cond.actions[1]
            self.assertEqual(action.type, 'settoken')
            self.assertEqual(action.name, 'foobar')
            self.assertEqual(action.template, '$click.value$')
            action = cond.actions[2]
            self.assertEqual(action.type, 'unsettoken')
            self.assertEqual(action.name, 'bar')

        def testParseImplicitLinkAction(self):
            result = parseDrilldown(et.fromstring('''
                <drilldown>
                    <link>/foo/bar</link>
                </drilldown>
            '''))
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 1)
            cond = result[0]
            self.assertEqual(cond.field, '*')
            self.assertEqual(len(cond.actions), 1)
            action = cond.actions[0]
            self.assertEqual(action.type, 'link')

        def testParseImplicitSetTokenAction(self):
            result = parseDrilldown(et.fromstring('''
                <drilldown>
                    <set token="foo">$click.value$</set>
                </drilldown>
            '''))
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 1)
            cond = result[0]
            self.assertEqual(cond.field, '*')
            self.assertEqual(len(cond.actions), 1)
            action = cond.actions[0]
            self.assertEqual(action.type, 'settoken')
            self.assertEqual(action.name, 'foo')
            self.assertEqual(action.template, '$click.value$')

        def testParseImplicitSetTokenActions(self):
            result = parseDrilldown(et.fromstring('''
                <drilldown>
                    <set token="foo">$click.value$</set>
                    <set token="bar">$click.value2$</set>
                    <unset token="foobar" />
                </drilldown>
            '''))
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 1)
            cond = result[0]
            self.assertEqual(cond.field, '*')
            self.assertEqual(len(cond.actions), 3)
            action = cond.actions[0]
            self.assertEqual(action.type, 'settoken')
            self.assertEqual(action.name, 'foo')
            self.assertEqual(action.template, '$click.value$')
            action = cond.actions[1]
            self.assertEqual(action.type, 'settoken')
            self.assertEqual(action.name, 'bar')
            self.assertEqual(action.template, '$click.value2$')
            action = cond.actions[2]
            self.assertEqual(action.type, 'unsettoken')
            self.assertEqual(action.name, 'foobar')

        def testParserDoesNotFailWithComments(self):
            result = parseDrilldown(et.fromstring('''
                <drilldown>
                    <!-- this is a comment -->
                    <condition field="foo">
                        <set token="blah">$click.value$</set>
                        <!-- another comment -->
                        <set token="buh"><!-- some comment--></set>
                        <link><!-- comment comment --></link>
                    </condition>
                </drilldown>
            '''))
            self.assertIsNotNone(result)

        def testParsePrefixAndSuffixForSet(self):
            result = parseDrilldown(et.fromstring('''
                <drilldown>
                    <set token="foo" prefix="sourcetype=&quot;" suffix="&quot;">$click.value$</set>
                </drilldown>
            '''))
            action = result[0].actions[0]
            self.assertEquals(action.name, 'foo')
            self.assertEquals(action.prefix, 'sourcetype="')
            self.assertEquals(action.suffix, '"')

            result = parseDrilldown(et.fromstring('''
                <drilldown>
                    <set token="foo">$click.value|s$</set>
                </drilldown>
            '''))
            action = result[0].actions[0]
            self.assertEquals(action.name, 'foo')
            self.assertIsNone(action.prefix)
            self.assertIsNone(action.suffix)

        def testMixedConditionsRaisesError(self):

            with self.assertRaises(AttributeError):
                parseDrilldown(et.fromstring('''
                    <drilldown>
                        <set token="foo">...</set>
                        <condition field="foobar">
                            <set token="bar">...</set>
                        </condition>
                    </drilldown>
                '''))

            with self.assertRaises(AttributeError):
                parseDrilldown(et.fromstring('''
                    <drilldown>
                        <condition field="foobar">
                            <set token="bar">...</set>
                        </condition>
                        <set token="foo">...</set>
                    </drilldown>
                '''))

            with self.assertRaises(AttributeError):
                parseDrilldown(et.fromstring('''
                    <drilldown>
                        <set token="foo">...</set>
                        <condition field="foobar">
                            <set token="bar">...</set>
                        </condition>
                        <unset token="foo" />
                    </drilldown>
                '''))
                
        def testParseEmptyCondition(self):
            drilldown = parseDrilldown(et.fromstring('''
                <drilldown>
                    <condition>
                        <link>foo</link>
                    </condition>
                </drilldown>
            '''))
            self.assertEqual(drilldown[0].attr, 'any')
            self.assertEqual(drilldown[0].value, '*')

    logger.setLevel(logging.ERROR)
    loader = unittest.TestLoader()
    suite = [loader.loadTestsFromTestCase(case) for case in (DrilldownParserTests,)]
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suite))