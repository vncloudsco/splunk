from __future__ import print_function
from builtins import object
import inspect, re



def log(msg):
    flog = open("/tmp/recipe.txt", "a")
    flog.write(msg)
    flog.close()

def isTrue(val):
    return len(val) > 0

def get_recipe_list():
    return [o._NAME for o in globals().values() if inspect.isclass(o) and issubclass(o, Recipe) and not o._HIDDEN]

### substVars("elvis was in $location$ but didn't own $4.54 to $person$", {'location':'new york', 'person':'elton'})
### -> "elvis was in new york but didn't own $4.54 to elton"
def substVars(text, variables):
    matches = re.findall("\\$([^$]+)(?=\\$)", text)
    for match in matches:
        try:
            if match in variables:
                text = text.replace("$%s$" % match, variables[match])
        except Exception as e:
            pass
    return text

def get_class(name):
    name = name.lower()
    for o in globals().values():
        if inspect.isclass(o) and issubclass(o, Recipe) and o._NAME.lower() == name:
            return o
    raise Exception("Unknown recipe type: %s" % name)

def tab(depth):
    return " " * (depth*4)


g_last_id = 0
def getID():
    global g_last_id
    g_last_id += 1
    return g_last_id

class Chef(object):
    """operates on recipes. mostly utilies"""

    @classmethod
    def parse(klass, obj):
       recipe = get_class(obj['_class'])()
       rargs = recipe.get_args()
       for k, v in obj.items():
           if k == '_class':
               continue
           if isinstance(v, dict) and '_class' in v:
               v = klass.parse(v)
           if isinstance(v, list):
               v = [klass.parse(s) for s in v]
           rargs[k] = v
       return recipe

    # looks for node with _id = rid, and returns tuple of (node, parentnode)
    @classmethod
    def find(klass, obj, parent, rid):
        myid = obj.get_args().get('_id', None)
        if rid == myid:
            return obj, parent

        for v in obj.get_args().values():
           if isinstance(v, Recipe):
               sobj, sparent = klass.find(v, obj, rid)
               if sobj != None:
                   return sobj, sparent
           if isinstance(v, list):
               for s in v:
                   sobj, sparent = klass.find(s, obj, rid)
                   if sobj != None:
                       return sobj, sparent
        return None, None

    @classmethod
    def delete(klass, obj, rid, newval=None):
        node, parent = klass.find(obj, obj, rid)
        if node == None:
            return False
        # remove child from parent
        args = parent.get_args()
        for k, v in args.items():
            if v == node:
                args.pop(k)
                parent.reset() # reset parent to have default values
                if newval != None:
                    args[k] = newval
                return True
            if isinstance(v, list):
               for i, s in enumerate(v):
                   if s == node:
                       v.remove(s)
                       # old reset loc
                       if newval != None:
                           v.insert(i, newval)
                       parent.reset() # reset parent to have default values
                       return True
        return False

    @classmethod
    def add(klass, obj, rid):
        node, parent = klass.find(obj, obj, rid)
        if node == None:
            return False
        # add child to parent
        args = parent.get_args()
        for v in args.values():
            if isinstance(v, list):
               for i, s in enumerate(v):
                   if s == node:
                       v.insert(i+1, Recipe())
                       return True
            # new
            if isinstance(v, Recipe):
                if klass.add(v, rid):
                    return True

        return False

    @classmethod
    def update(klass, obj, rid, field, val):
        log("UPDATING: %s, %s, %s, %s\n\n" % (obj, rid, val, field))
        log("UPDATYPE: %s, %s, %s, %s\n\n" % (type(obj), type(rid), type( val), type( field)))

        # updating a step.
        if field == 'class':
            node, parent = klass.find(obj, obj, rid)
            if node == None:
                return False
            print("SAME? %s %s" % (node._NAME, val))
            if node._NAME == val:
                print("SAME VALUE!! DO NOTHING!!")
                return False
            log("UPDATING CLASS: %s, %s, %s, %s\n\n" % (obj, rid, val, field))
            # delete old and set new value
            val = get_class(val)()
            log("BEFORE: %s\n\n" % obj.toPY())
            success = klass.delete(obj, rid, val)
            log("AFTER: %s\n\n" % obj.toPY())
            log("GREAT SUCCESS? %s\n\n" % success)
            return success
        else:
            node, parent = klass.find(obj, obj, rid)
            log("XX NODE, PARENT, OBJ, RID: %s, %s, %s, %s\n\n" % (node, parent, obj, rid))
            log("UPDATING FIELD: %s, %s\n\n" % (node, parent))
            if node != None:
                node.get_args()[field] = val
                return True
        return False


class Recipe(object):
    _NAME = "--------"
    _HIDDEN = False

    def __init__(self, **kwargs):
        self.args = {}
        self.args['_id'] = getID()

    def reset(self):
        pass

    def get_args(self):
        return self.args

    def toPrettyText(self, depth=0):
        out = []
        out.append(self._NAME)
        for k, v in self.args.items():
            if isinstance(v, Recipe):
                v = v.toPrettyText(depth+1)
            elif isinstance(v, list):
                v = [s.toPrettyText(depth+1) for s in v]
            out.append("%s=%s" % (k, v))
        return ('\n%s' % tab(depth)).join(out)


    def toPY(self):
        d = { '_class': self._NAME }
        for k, v in self.args.items():
            if isinstance(v, Recipe):
                v = v.toPY()
            elif isinstance(v, list):
                log("TOPY: '%s'\n\n" % v)
                v = [s.toPY() for s in v]
            d[k] = v
        return d


    def run(self, workspace = {}, debug=None):
        raise Exception("not implemented")

class BlockRecipe(Recipe):
    _NAME = "block"
    _HIDDEN = True

    def __init__(self, initchar='[', stopchar=']', **kwargs):
        super(BlockRecipe, self).__init__()
        self.initchar = initchar
        self.stopchar = stopchar
        self.reset()

    def reset(self):
        if 'steps' not in self.args or len(self.args['steps']) == 0:
            self.args['steps'] = [ Recipe() ]

    def run(self, workspace = {}, debug=None):
        for step in self.args['steps']:
            self.run_step(step, workspace, debug)
        self.finalize_steps()
    def run_step(self, step, workspace, debug):
        raise Exception("not implemented")
    def finalize_steps(self):
        pass

class SerialRecipe(BlockRecipe):
    ''' run steps serially'''
    _NAME = "serial"
    _HIDDEN = False

    def __init__(self, **kwargs):
        super(SerialRecipe, self).__init__('[',']', **kwargs)
    def run_step(self, step, workspace = {}, debug=None):
        step.run(workspace, debug)

class ParallelRecipe(BlockRecipe):
    ''' run steps in parallel'''
    _NAME = "parallel"
    _HIDDEN = False

    def __init__(self, **kwargs):
        super(ParallelRecipe, self).__init__('{','}', **kwargs)

    def run_step(self, workspace = {}, debug=None):
        # !!! RUN IN NEW THREAD step.run(workspace, debug)
        pass
    def finalize_steps(self):
        # !!! JOIN UP
        pass

class SearchRecipe(Recipe):
    MAX_DEBUG_RESULTS_PER_STEP = 20
    _NAME = "search"
    _HIDDEN = False

    def __init__(self, **kwargs):
        super(SearchRecipe, self).__init__(**kwargs)
        self.reset()

    def reset(self):
        if 'search' not in self.args:
            self.args['search'] = ''

    def run(self, workspace = {}, debug=None):
        import splunk.search as se

        q = self.args['search']
        q = substVars(q, workspace)
        workspace['_'] = results = se.searchAll(q, **workspace)
        if debug:
            if 'debug' not in workspace:
                workspace['debug'] = []
            workspace['debug'].append(results[:self.MAX_DEBUG_RESULTS_PER_STEP])


class SearchIteratorRecipe(Recipe):
    MAX_DEBUG_RESULTS_PER_STEP = 20
    _NAME = "search_iterator"
    _HIDDEN = False

    def __init__(self, **kwargs):
        super(SearchIteratorRecipe, self).__init__(**kwargs)
        self.reset()

    def reset(self):
        if 'search' not in self.args:
            self.args['search'] = ''

    def run(self, workspace = {}, debug=None):
        import splunk.search as se

        q = self.args['search']
        q = substVars(q, workspace)
        workspace['_'] = se.dispatch(q, **workspace)

class LetRecipe(Recipe):
    MAX_DEBUG_RESULTS_PER_STEP = 20
    _NAME = "let"
    _HIDDEN = False

    def __init__(self, **kwargs):
        super(LetRecipe, self).__init__(**kwargs)
        self.reset()

    def reset(self):
        if 'var' not in self.args:
            self.args['var'] = ''

    def run(self, workspace = {}, debug=None):
        self.args['var'] = workspace['_']


class WhileRecipe(Recipe):
    _NAME = "while"
    _HIDDEN = False

    def __init__(self, **kwargs):
        super(WhileRecipe, self).__init__(**kwargs)
        self.reset()

    def reset(self):
        if 'condition' not in self.args:
            self.args['condition'] = Recipe()
        if 'loop' not in self.args:
            self.args['loop'] = Recipe()

    def run(self, workspace = {}, debug=None):
        while (True):
            self.args['condition'].run(workspace, debug)
            if not isTrue(workspace['_']):
                break
            self.args['loop'].run(workspace, debug)

class PrintRecipe(Recipe):
    _NAME = "print"
    _HIDDEN = False

    def __init__(self, **kwargs):
        super(PrintRecipe, self).__init__(**kwargs)
        self.reset()

    def reset(self):
        if 'statement' not in self.args:
            self.args['statement'] = ""

    def run(self, workspace = {}, debug=None):
        stmt = substVars(self.args["statement"], workspace)
        print(stmt)

## runs generic python
class PythonRecipe(Recipe):
    _NAME = "python"
    _HIDDEN = False

    class PermissionRestricted(object):
        pass

    def __init__(self, **kwargs):
        super(PythonRecipe, self).__init__(**kwargs)
        self.reset()
        # take out some common file ops
        #pr = PythonRecipe.PermissionRestricted()
        #__builtins__.open = pr
        #__builtins__.file = pr
        #__builtins__.execfile = pr

    def reset(self):
        if 'code' not in self.args:
            self.args['code'] = ""

    def run(self, workspace = {}, debug=None):
        exec(self.args['code'])

class SleepRecipe(Recipe):
    _NAME = "sleep"
    _HIDDEN = False

    def __init__(self, **kwargs):
        super(SleepRecipe, self).__init__(**kwargs)
        self.reset()

    def reset(self):
        if 'seconds' not in self.args:
            self.args['seconds'] = 0

    def run(self, workspace = {}, debug=None):
        import time
        time.sleep(self.args["seconds"])


class IfThenElseRecipe(Recipe):
    _NAME = "if-then-else"
    _HIDDEN = False

    def __init__(self, **kwargs):
        super(IfThenElseRecipe, self).__init__(**kwargs)
        self.reset()

    def reset(self):
        if 'if'   not in self.args: self.args['if'  ] = Recipe()
        if 'then' not in self.args: self.args['then'] = Recipe()
        if 'else' not in self.args: self.args['else'] = Recipe()

    def run(self, workspace = {}, debug=None):
        self.args['if'].run(workspace, debug)
        if isTrue(workspace['_']):
            self.args['then'].run(workspace, debug)
        else:
            self.args['else'].run(workspace, debug)


def test2():

    json = { '_class':'while',
             'condition':
                  {
                         '_class': 'search',
                         'search':'search error | head 1'
                  },
                  'loop':
                  {
                         '_class': 'serial',
                         'steps':
                         [
                               {
                                  '_class': 'print',
                                  'statement':'$person$ $_[0]$'
                               },
                               {
                                  '_class': 'sleep',
                                  'seconds': 2
                               },
                               {
                                   '_class': 'python',
                                   'code': 'print "elvis"'
                               }
                        ]

                 }
           }

    json = {'_class': 'while', 'condition': {'search': 'search error | head 1', '_class': 'search', '_id': 5}, 'loop': {'_class': 'serial', 'steps': [{'_class': 'print', 'statement': '$person$ $_[0]$', '_id': 2}, {'seconds': 2, '_class': 'sleep', '_id': 3}, {'code': 'print "elvis"', '_class': 'python', '_id': 4}], '_id': 1}, '_id': 0}

    print("TYPES OF RECIPE STEPS: %s" % get_recipe_list())

    obj = Chef.parse(json)

    print("HUMAN:\n %s" % obj.toPrettyText())
    print("\nPY:   %s" % obj.toPY())


    Chef.add(obj, 4)

    print("\nPY:    %s" % obj.toPY())

    Chef.update(obj, 10, 'class', 'sleep')

    print("\nPY:    %s" % obj.toPY())


    print("FIND: 2 %s" % Chef.find(obj, obj, 2))
    print("FIND: 4 %s" % Chef.find(obj, obj, 4))

    print("UPDATE: 4 DO NOTHING %s" % Chef.update(obj, 4, 'class', 'python'))
    print("PY:    %s" % obj.toPY())

    print("UPDATE: 4 %s" % Chef.update(obj, 4, 'code', 'foobar'))
    print("UPDATE: 4 %s" % Chef.update(obj, 4, 'class', 'parallel'))
    print("PY:    %s" % obj.toPY())
    return


    print("FIND: 5 %s" % Chef.find(obj, obj, 5))

    print("DELETE: 2 %s" % Chef.delete(obj, 2))
    print("PY:    %s" % obj.toPY())
    print("DELETE: 5 %s" % Chef.delete(obj, 5))
    print("PY:   " % obj.toPY())

    #recipe.run({'person':'elvis'}, True)


if __name__ == '__main__':
    import splunk.auth as auth
    auth.getSessionKey('admin', 'changeme')

    import unittest
    class SubstVarsTest(unittest.TestCase):
        def test_substVars(self):
            self.assertEquals(
                substVars("elvis was in $location$ but didn't own $4.54 to $person$", {'location':'new york', 'person':'elton'}),
                "elvis was in new york but didn't own $4.54 to elton"
                )
            self.assertEquals(
                substVars("test is $test$", {'location':'new york'}),
                "test is $test$"
                )

    test2()

    # exec all tests
    loader = unittest.TestLoader()
    suites = []
    suites.append(loader.loadTestsFromTestCase(SubstVarsTest))
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
