"""
Routable Cherry Controllers

This code let's you combine CherryPy's nice default hierarchial dispatcher
with the ability to setup arbitrary routes to chosen targets.

Routes are attached directly to the method that handles the request rather than
in a separate configuration file

For example:
AccountsController(BaseController):
  @route('/:username/:action')
  def useraction(self, username, action='view'):
      # do some magic
RootControler(BaseController):
  accounts = AccountsController()

All requests to /accounts/username/action then go to the useraction method
additionally, since useraction specifies a default for action, /accounts/username will
go there too.

@route accepts variable, static and greedy components:
@route('/:username') - Any value for username within 1 path segment
@route('/:action=view') - Only requests that begin with /view match - the action keyword argument will always be set to view
@route('/:username/@category/:action') - Adds a keyword argument called category that matches as many path segments as possible

methods can have more than one route attached to them if required

If no routes match then the default method is executed as per usual


You can also construct urls based on route using the path to the controller as the base:
make_route('/accounts', username='auser', action='delete')

you can also add a query string by passing a list of tuples to make_path
make_route('/accounts', username='auser', action='delete', _qs=[ ('return_to', '/') ])
"""
from __future__ import absolute_import


from builtins import range
from splunk.util import cmp
from functools import total_ordering
from builtins import object

import cherrypy
from cherrypy._cpdispatch import test_callable_spec
import sys
import inspect
import logging
import types
import splunk.util

import splunk.appserver.mrsparkle.lib.i18n as i18n
logger = logging.getLogger('splunk.appserver.mrsparkle.lib.routes')

class RequestRefused(cherrypy.HTTPError):
    """
    Used by decorators to reject handling of a request (and thus allow
    routes to try and find an alternate handler)
    Don't raise this in a handler yourself; raise cherrypy.NotFound instead
    """
    pass

class RouteError(Exception):
    """Thrown if route syntax is invalid"""
    pass

def route(route=None, methods=None, leave_exposed=False):
    """
    The @route decorator
    @route('/:vararg/:static=constant/*greedy', methods='POST')
    methods or the route can be ommitted
    methods can be a list of methods
    defaults for route varargs are taken from the method's arguments

    Don't set leave_exposed to true unless you really want your routed method
    to be available at it's method name as well as it's route path
    """
    def decorator(fn):
        if not hasattr(fn, 'routes'):
            fn.routes = []
        fnargs = inspect.getargspec(fn)
        if fnargs[3]:
            defaults = dict( zip(fnargs[0][0-len(fnargs[3]):], fnargs[3]) )
        else:
            defaults = {}
        fn.routes.append(Route(fn, route, defaults, methods))
        if leave_exposed:
            fn.route_exposed = True
        return fn
    return decorator

def make_route(base_path, **kw):
    """
    Return a url path for a route
    make_route('/search/jobs', job_id=1234, action=delete)
    Can also add a query string by passing a list of tuples or a dict as _qs:
    make_route('/search/jobs', job_id=1234, action=delete, _qs=[('q', 'search val to quote')])
    or
    make_route('/search/jobs', job_id=1234, action=delete, _qs=dict(q='search val to quote'))
    """
    qargs = kw.get('_qs', '')
    if qargs:
        del kw['_qs']
        if isinstance(qargs, dict):
            # translate {'v1':'k1', 'v2':['v2-1','v2-2']} to [('v1','k1'), ('v2','v2-1'), ('v2','v2-2')]
            # nexted list comprehensions ftw
            input = qargs
            qargs = []
            [ qargs.extend([(k, e) for e in v]) for k, v in [ (k, v if isinstance(v, (list, tuple)) else (v,) ) for k, v in input.items() ] ]
        qargs = '?'+'&'.join( [ '%s=%s' % (k,splunk.util.safeURLQuote(v)) for k,v in qargs ] )
    if not kw: 
        return i18n.make_i18n_url(base_path + qargs)

    app = cherrypy.request.app
    ctrl = app.root
    base_path = base_path.strip('/').split('/')
    for el in base_path:
        if hasattr(ctrl, el):
            newctrl = getattr(ctrl, el) 
            if not isinstance(newctrl, object):
                break
            ctrl = newctrl
        else:
            break
    # find route that matches kw
    for route in ctrl.routes:
        path = route.build_path(**kw)
        if path:
            base_path.extend(path)
            return i18n.make_i18n_url('/'+'/'.join([str(x) for x in base_path]) + qargs)

@total_ordering
class Route(object):
    """
    An individual route - You don't normally want to instantiate this directly
    Use the @route decorator instead
    """
    DYN = 1
    STATIC = 2
    GREEDY = 3

    def __init__(self, target, route_def, defaults={}, methods=None):
        self.route_str = route_def
        self.target = target
        if isinstance(methods, splunk.util.string_type):
            self.methods = [methods]
        else:
            self.methods = methods
        self.staticcount = 0
        self.greedy = 0
        self.defaults = {}
        self.requires = [] # keys that must be set to build a route dynamically
        self.elnames = []
        nodelist = []
        if route_def and route_def!='/':
            for i, el in enumerate(route_def.strip('/').split('/')):
                if el[0]=='*':
                    el = el[1:]
                    self.elnames.append(el)
                    nodelist.append( (self.GREEDY, el) )
                    self.requires.append(el)
                    self.greedy += 1
                elif el[0]==':':
                    el = el[1:]
                    k = el.split('=', 1)
                    if len(k)==2:
                        nodelist.append( (self.STATIC, k[0], k[1]) )
                        self.staticcount += 1
                        self.elnames.append(k[0])
                        self.requires.append(k[0])
                    else:
                        nodelist.append( (self.DYN, el) )
                        self.elnames.append(el)
                        if el not in defaults:
                            self.requires.append(el)
                        else:
                            self.defaults[el] = defaults[el]
                elif el[0]=='=':
                    nodelist.append( (self.STATIC, None, el[1:]) )
                else:
                    raise RouteError(_('Invalid route definition: %s') % route_def)
        self.nodelist = nodelist
        self.nodelen = len(nodelist)

    def __repr__(self):
        return 'Route<route="%s", methods=%s>' % (self.route_str, self.methods)

    def matchpath(self, path, method=None):
        if method and self.methods and method not in self.methods:
            # this route defines a list of methods it can handle
            # and method isn't one of them
            return False
        if isinstance(path, splunk.util.string_type):
            path = path.strip('/').split('/')
        pathlen = len(path)
        i = 0
        nodenum = 0
        result = {}
        for node in self.nodelist:
            nodename = node[1]
            if node[0] == self.STATIC:
                if i>pathlen-1:
                    return False # no defaults for static elements
                if path[i] != node[2]:
                    return False # must matach
                if node[1]:
                    result[node[1]] = node[2]

            elif node[0] == self.DYN:
                nodename = node[1]
                if i>pathlen-1:
                    if nodename not in self.defaults:
                        return False
                    result[nodename] = self.defaults[nodename]
                else:
                    result[nodename] = path[i]

            elif node[0] == self.GREEDY:
                # match as many nodes as possible, allowing for remaining
                # nodes in the nodelist
                nodesleft = self.nodelen - nodenum - 1
                pathleft = len(path) - i
                suck = pathleft-nodesleft
                if pathleft - nodesleft < 1:
                    # not enough elements left to match the Route
                    return False
                suck = pathleft-nodesleft
                slice = '/'.join(path[i:i+suck])
                result[nodename] = slice
                i += suck-1 # will be increment by one more below

            i += 1
            nodenum += 1
        if i < pathlen:
            return False # If dangling path elements haven't been sucked up by a greedy then we don't match
        return result

    def build_path(self, **args):
        """
        Attempt to build a path from a set of defaults
        Returns None if the defaults don't fit the Route
        Returns a list of path elements otherwise
        """
        for key in self.requires:
            if key not in args:
                return None
        for key in args.keys():
            if key not in self.elnames:
                return None
        result = []
        for node in self.nodelist:
            nodetype, el = node[0], node[1]
            if nodetype == self.STATIC:
                if args[el] != node[2]:
                    return None
                result.append(node[2])

            elif nodetype == self.DYN:
                result.append(args.get(el, self.defaults.get(el, None)))

            elif nodetype == self.GREEDY:
                result.append(args[el])

        return result

    def __eq__(self, other):
        return self._compare_routes(other) == 0
    def __lt__(self, other):
        return self._compare_routes(other) < 0

    def _compare_routes(self, other):
        """
        Compare nodelength and staticlength so arrays of Routes sort correctly based on how specific they are
        Specificity is basead on (in descending priority):
        * The number of static components in the path
        * The number of other components in the path
        * Whether the route is restricted to a specific method or methods
        """
        if self.staticcount == other.staticcount:
            result = self.nodelen - other.nodelen
        else:
            result = self.staticcount - other.staticcount
        if result == 0:
            # all other things being equal, make sure routes that specify a method are returned before routes that accept any
            if self.methods and other.methods:
                return 0 # don't care whether the methods match, just that they both specify some
            if self.methods:
                return 1
            if other.methods:
                return -1
            return 0
        return result


    def collides_with(self, other):
        """
        Unlike a basic comparison, this method determines whether or not two routes will collide when CherryPy resolves them.
        This includes checking whether or not they have any static segments that can be used to distinguish them
        and whether there is any overlap in the HTTP methods they expose.
        """

        if self != other:
            return False

        # initially, we set the flag for whether static segments with resolve the routes if neither route has static segments
        # and their total number of segments is equal
        cant_resolve_with_static = ((self.staticcount == 0 and other.staticcount == 0) and (self.nodelen == other.nodelen))

        # if the flag is not set above, loop through the segments and look for a pair of static segments for resolving
        # if we find a pair, we can return False immediately
        if not cant_resolve_with_static:
            for i in range(len(self.nodelist)):
                self_node, other_node = self.nodelist[i], other.nodelist[i]
                if self_node[0] == self.STATIC and other_node[0] == self.STATIC:
                    if self_node[2] == other_node[2]:
                        cant_resolve_with_static = True
                    else:
                        return False

        # if the static segments can't be used to resolve, check for overlap in the HTTP methods exposed
        if cant_resolve_with_static:
            if self.methods and other.methods:
                for m in self.methods:
                    if m in other.methods:
                        return True
            else:
                return True

        return False




class RoutableType(type):
    """
    Metaclass to route-enable a controller class
    """
    def __new__(m, clsname, bases, dict_obj):
        routes = []
        for attrname, attr in dict_obj.items():
            if isinstance(attr, types.FunctionType):
                if hasattr(attr, 'routes'):
                    routes.extend(attr.routes)
                    if not hasattr(attr, 'route_exposed') and hasattr(attr, 'exposed'):
                        del attr.exposed
        dict_obj['routes'] = routes
        if routes:
            routes.sort(reverse=True) # place most specific routes first

            for i in range(len(routes) - 1):
                if routes[i].collides_with(routes[i + 1]):
                    logger.error('ROUTE COLLISION: a potential collision was found in %s: %s, %s' % (clsname, routes[i], routes[i + 1]))

            def default(self, *path, **kw):
                # attempt to find matching route
                path = list(path)
                for i in range(len(path)):
                    try:
                        if isinstance(path[i], str):
                            if sys.version_info < (3, 0):
                                path[i] = path[i].decode('utf-8')
                            pass
                    except UnicodeDecodeError:
                        pass
                pathlen = len(path)
                method = cherrypy.request.method
                e = None
                for route in self.routes:
                    match = route.matchpath(path, method)
                    if match is False:
                        continue
                    #any methods with routes attached are assumed to be expoed
                    #the method itself should not have the .exposed attribute else
                    # it'll be accessible at an unexpected url
                    kw.update(match) # should probably create a new dict here
                    try:
                        if getattr(route.target, 'lock_session', None):
                            # the default wrapper only acquires a read lock
                            # honour the target's request for a write lock prior to dispatch
                            cherrypy.session.escalate_lock()
                        return route.target(self, **kw)
                    except TypeError as x:
                        test_callable_spec(route.target, [], kw)
                        raise
                    except RequestRefused as e:
                        pass

                if hasattr(default, 'original'):
                    try:
                        return default.original(*path, **kw)
                    except TypeError as x:
                        test_callable_spec(default.original, path, kw)
                        raise
                if e:
                    raise # re-raise the last exception
                raise cherrypy.NotFound
            default.exposed = True

            if 'default' in dict_obj:
                default.original = dict_obj['default']
            dict_obj['default'] = default
        return super(RoutableType, m).__new__(m, clsname, bases, dict_obj)

