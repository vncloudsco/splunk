from __future__ import division
#
# Much of this file is heavily influenced by the Django web framework.
# www.djangoproject.com
#

from past.utils import old_div
from builtins import range
from builtins import object

import logging
from future.moves.urllib import parse as urllib_parse
import re
import sys

import splunk.entity
import splunk.rest
from splunk.models.field import Field, BoolField
import splunk.util

logger = logging.getLogger('splunk.models.base')

# define Atom entity <link> rel values
LINK_REMOVE_KEY = 'remove'
LINK_LIST_KEY = 'list'

def object_is_integer_type(obj):
    if isinstance(obj, int):
        return True
    if sys.version_info < (3, 0) and isinstance(obj, long):
        return True
    return False

class SplunkQuerySet(object):
    '''
    A simple query set for splunkd model objects.

    Supports iterating, slicing, searching, and ordering.
    '''

    def __init__(self, manager, count_per_req=50, host_path=None, sessionKey=None):
        self.manager            = manager
        self._host_path         = host_path
        self._sessionKey        = sessionKey
        self._count_per_req     = count_per_req
        self._results_cache     = None
        self._iter              = None
        self._count             = 0
        self._offset            = 0
        self._total             = None
        self._sort_key          = None
        self._sort_dir          = None
        self._search_string     = None
        self._search_count      = None
        self._additional_getargs = None

        self._uri               = None
        self._namespace         = None
        self._owner             = None

    def get_total(self):
        '''Get the total. If total has not yet been defined, request it from splunkd.'''

        if self._total == None:
            try:
                self._total = int(self.get_entities(count=1, offset=0,
                                                    search=self._search_string,
                                                    hostPath=self._host_path,
                                                    sessionKey=self._sessionKey).totalResults)
            except splunk.AuthenticationFailed:
                raise
            except Exception as e:
                self._total = 0
                logger.warn('Could not retrieve entities for the given resource with the following error %s' % e)
        return self._total

    def set_total(self, val):
        '''Setter for the total'''

        self._total = int(val)

    total = property(get_total, set_total)

    def __len__(self):
        '''
        Return the len of the query.

        Note that if this query is the result of a slice, the len is calculated
        as the len of the slice, not the total number of entities available for
        the given resource. If a slice is requested that extends beyond the
        total number of actual entities, the subset of entities will be returned.

        Example:
        (assume total number of jobs is 50)

        >>> len(Job.all()) == 50
        >>> True

        >>> len(Job.all()[:10]) == 10
        >>> True

        >>> len(Job.all()[48:60]) == 2
        >>> True
        '''

        # Coercing an uncached queryset obj to a list calls __len__ before
        # paging through the generator.  This is a bit of a hack but prevents
        # an extra request to splunkd when doing something like list(Job.all())
        if sys.version_info < (3, 0) and self._iter and self._total == None:
            raise
        if not self._count:
            if self._search_string:
                if self._search_count == None:
                    self._search_count = 0
                    self._search_count = len(list(self))
                return self._search_count
            return self.total
        elif self._count + self._offset <= self.total:
            return self._count
        elif self._count + self._offset > self.total:
            return self.total - self._offset

    def __iter__(self):
        '''Iterate over the cached result set, or generate a new iterator.'''

        if self._results_cache is None:
            self._results_cache = []
            self._iter = self.iterator()
        if self._iter:
            return self._result_iter()
        return iter(self._results_cache)

    def _result_iter(self):
        '''
        Used only when we have an internal _iter available. Will iterate over
        the cache first then fall back to the stored iterator.
        '''
        pos = 0
        while True:
            upper = len(self._results_cache)
            if sys.version_info >= (3, 0):
                 while pos < upper:
                    try:
                        yield self._results_cache[pos]
                    except StopIteration:
                        return
                    pos = pos + 1
                 if not self._iter:
                    return
            else:
                while pos < upper:
                    yield self._results_cache[pos]
                    pos = pos + 1
                if not self._iter:
                    raise StopIteration
            if len(self._results_cache) <= pos:
                self._fill_cache()

    def _fill_cache(self, num=None):
        '''Fills in the cache by chunk size or by num. Copied from Django.'''
        if self._iter:
            try:
                for i in range(num or self._count_per_req):
                    self._results_cache.append(next(self._iter))
            except StopIteration:
                self._iter = None

    def __bool__(self):
        '''Used in if statements. Copied verbatim from Django.'''
        if self._results_cache is not None:
            return bool(self._results_cache)
        try:
            next(iter(self))
        except StopIteration:
            return False
        return True

    def __contains__(self, val):
        '''Used in "in" statements. Copied verbatim from Django.'''
        pos = 0
        if self._results_cache is not None:
            if val in self._results_cache:
                return True
            elif self._iter is None:
                return False
            pos = len(self._results_cache)

        while True:
            if len(self._results_cache) <= pos:
                self._fill_cache(num=1)
            if self._iter is None:
                return False
            if self._results_cache[pos] == val:
                return True
            pos += 1

    def __getitem__(self, key):
        '''
        Retrieve a single item or slice of items from the cache or by returning
        a cloned queryset object bound to a given count and offset.

        Parts of this function are taken from the equivalent method in the
        Django web framework.
        '''

        if not (isinstance(key, slice) or object_is_integer_type(key)):
            raise TypeError

        assert ((not isinstance(key, slice) and (key >= 0))
            or (isinstance(key, slice) and (key.start is None or key.start >= 0)
            and (key.stop is None or key.stop >= 0))), \
            "Negative indexing is not supported."

        if self._results_cache is not None:
            # This just optimizes against requesting
            # a single item out of bounds and fetching
            # everything in the entire set to check for it.
            # We can do this b/c we know the total len
            # for the set early on.
            if object_is_integer_type(key):
                if key >= len(self) :
                    raise IndexError

            if self._iter is not None:
                if isinstance(key, slice):
                    if key.stop is not None:
                        bound = int(key.stop)
                    else:
                        bound = None
                else:
                    bound = key + 1
                if len(self._results_cache) < bound:
                    self._fill_cache(bound - len(self._results_cache))
            return self._results_cache[key]

        # Otherwise, this is an unloaded queryset and we're going to clone it...
        else:
            if isinstance(key, slice):
                start = int(key.start) if key.start is not None else 0
                stop = int(key.stop) if key.stop is not None else 0
                clone = self._clone()
                clone._count = (stop - start)
                clone._offset = start
                return key.step and list(clone)[::key.step] or clone

            # Handle just an int
            clone = self._clone()
            clone._count = 1
            clone._offset = self._offset + key
            return list(clone)[0]

    def iterator(self):
        '''
        The actual iterator itself.  Will retrieve the entities for a given
        resource in pages based on the internal count_per_req.
        '''

        # Set the count to the lesser of the count_per_req or the internal
        # count. This remains constant until the very last req.
        iter_count = self._count_per_req if (self._count > self._count_per_req or self._count == 0) else self._count

        # The initial iterator offset is the same as the queryset's.
        iter_offset = self._offset

        # Get the initial set of entities so we can start somewhere and have
        # access to the total # of entities.
        try:
            entities = self.get_entities(count=iter_count, offset=iter_offset, search=self._search_string, sort_key=self._sort_key, sort_dir=self._sort_dir, hostPath=self._host_path, sessionKey=self._sessionKey)
        except splunk.AuthenticationFailed:
            raise
        except splunk.LicenseRestriction:
            raise splunk.LicenseRestriction
        except Exception as e:
            logger.warn('Could not retrieve entities for the given resource with the following error %s' % e)
            self.total = 0
            return

        results = [self.manager._from_entity(self.manager._fix_entity(entities[entity])) for entity in entities]

        # Get the actual total, even though this may be a slice
        self.total = int(entities.totalResults)
        max_num_iters = self.total // iter_count

        # Now determine the final offset so we can setup a while loop
        # over the offset (essentially page)
        # self._count being greater than 0 indicates this is a slice
        num_iters = (old_div(self._count, iter_count) if self._count else (old_div(self.total, iter_count))) - 1
        remainder =  self._count % iter_count if self._count else (self.total % iter_count)

        # ensure that requesting a count greater than total number of results
        # doesn't produce excess requests
        num_iters = min(max_num_iters, num_iters)

        if remainder: num_iters += 1

        # Yield the initial set of models
        for model in results:
            yield model

        while num_iters > 0:
            num_iters -=1

            iter_offset = iter_count + iter_offset
            if num_iters == 0:
                # only change iter_count if page size is non-default
                iter_count = remainder or iter_count

            entities = self.get_entities(count=iter_count, offset=iter_offset, search=self._search_string, sort_key=self._sort_key, sort_dir=self._sort_dir, hostPath=self._host_path, sessionKey=self._sessionKey)
            results = [self.manager._from_entity(self.manager._fix_entity(entities[entity])) for entity in entities]

            for model in results:
                yield model

    def get_entities(self, **kwargs):
        '''Simple wrapper around the getEntities method.'''

        if self._additional_getargs is not None:
            for arg in self._additional_getargs:
                kwargs[arg] = self._additional_getargs[arg]

        return splunk.entity.getEntities(self.manager.model.resource, unique_key='id', uri=self._uri, namespace=self._namespace, owner=self._owner, **kwargs)

    def all(self, *args, **kwargs):
        return self

    def order_by(self, key, sort_dir='desc', *args, **kwargs):
        '''Returns a clone of the current query set, providing an ordering.'''
        clone = self._clone()
        clone._sort_key = key
        clone._sort_dir = sort_dir
        return clone

    def filter_by_app(self, app, *args, **kwargs):
        '''Returns a clone of the current query set, providing app based filtering'''
        clone            = self._clone()
        # objects in question must be visible from the app which we're requested to filter by
        clone._namespace = '-' if app == None or len(app) == 0 else app
        return clone.search('eai:acl.app="' + ('*' if app == None or len(app) == 0 or app == '-' else app) + '"')


    def filter_by_user(self, user, *args, **kwargs):
        '''Returns a clone of the current query set, providing user based filtering'''
        clone            = self._clone()
        # the objects in question must be visible to the user which we're requested to filter by
        clone._owner     = '-' if user == None or len(user) == 0 else user
        return clone.search('eai:acl.owner="' + ('*' if user == None or len(user) == 0 or user == '-' else user) + '"')


    def search(self, search_string, *args, **kwargs):
        '''Returns a clone of the current query set, allowing for post process searching.'''
        clone = self._clone()
        # setting the search
        if self._search_string == None or len(self._search_string) == 0:
             clone._search_string = search_string
        # searching on a query set that has a search already set means the search becomes more restrictive
        else:
             clone._search_string = '( ' + self._search_string + ' ) AND ( ' + search_string + ' )'
        return clone

    def filter(self, **kwargs):
        '''
        Returns a clone of the current query set that is filtered by the model field names
        '''

        clone = self._clone()

        model_fields = self.manager.model.TODO_get_meta_fields()

        # build the EAI search string by mapping the api_names
        search_string = []
        for arg in kwargs:

            # handle reserved keywords
            if arg in ('name'):
                key = arg
            elif arg not in model_fields:
                raise Exception('cannot filter on unknown field: %s' % arg)
            else:
                key = model_fields[arg].api_name or arg

            val = kwargs[arg]

            # when generating search fragment, normalize all booleans to use
            # expected 0|1 value
            if val == True:
                search_fragment = '"%s"=1' % key
            elif val == False:
                search_fragment = '"%s"=0' % key
            else:
                search_fragment = '"%s"="%s"' % (key, val)

            search_string.append(search_fragment)

        clone._search_string = ' '.join(search_string)
        return clone

    def _clone(self):
        '''
        Returns a clone of the current object, where the cache, total
        and iterator are invalidated.
        '''

        clone = self.__class__(self.manager, self._count_per_req)
        for prop in self.__dict__:
            if prop not in ['_results_cache', '_total', '_iter']:
                clone.__dict__[prop] = self.__dict__[prop]
        return clone


class SplunkRESTManager(object):
    def __init__(self, cls, host_path=None, sessionKey=None):
        self.model = cls
        self.host_path = host_path
        self.sessionKey = sessionKey

    def all(self, *args, **kwargs):
        '''Convenience method for getting all the entities of a model type.'''
        return SplunkQuerySet(self, **kwargs).all(*args, **kwargs)

    def order_by(self, *args, **kwargs):
        '''
        Convenience method for getting all the entities of a model
        type with a particular ordering.
        '''
        return SplunkQuerySet(self, **kwargs).order_by(*args, **kwargs)

    def search(self, *args, **kwargs):
        '''
        Convenience method for getting all the entities of a model type
        that match a search.
        '''
        return SplunkQuerySet(self, **kwargs).search(*args, **kwargs)

    def _from_entity(self, entity):
        """Construct this model from an entity."""

        obj = self.model(entity.namespace, entity.owner, entity.name, entity)

        obj.from_entity(entity)

        return obj

    def _fix_entity(self, entity):
        """Makes sure that the entity looks right."""

        if not entity.namespace:
            entity.namespace = entity['eai:acl']['app']

        return entity

    def _get_new_entity(self, namespace, owner, host_path=None, sessionKey=None):
        """Loads the new entity."""

        try:
            return splunk.entity.getEntity(self.model.resource, '_new', namespace=namespace, owner=owner, hostPath=host_path, sessionKey=sessionKey)
        except Exception:
            logger.error('unable to retrieve the EAI _new descriptor for entity: %s' % self.model.resource)
            raise

        return None

    def _get_entity(self, id, host_path=None):
        """Loads an entity given an id."""

        if host_path:
            id = host_path.rstrip('/') + '/' + id.lstrip('/')

        return self._fix_entity(splunk.entity.getEntity(self.model.resource, None, sessionKey=self.sessionKey, uri=id))

    def _put_args(self, id, postargs, messages=None, sessionKey=None):
        """Posts arguments and returns the entity or messages."""

        messages = messages or []

        logger.debug('url path: %s' % id)
        logger.debug('body: %s' % postargs)
        serverResponse, serverContent = splunk.rest.simpleRequest(id, postargs=postargs, raiseAllErrors=True, sessionKey=sessionKey)

        if serverResponse.status not in [200, 201]:
            messages.append(serverResponse.messages)
            return None

        try:
            atomEntry = splunk.rest.format.parseFeedDocument(serverContent)
        except Exception as e:
            messages.append({'text': 'Unable to parse feed.', 'type': 'ERROR'})
            return None

        if isinstance(atomEntry, splunk.rest.format.AtomFeed):
            try:
                atomEntry = atomEntry[0]
            except IndexError as e:
                messages.append({'text': 'Empty response.', 'type': 'ERROR'})
                return None

        entity = splunk.entity.Entity(self.model.resource, '', atomEntry.toPrimitive(), 'search')

        try:
            entity.owner = atomEntry.author
            entity.updateTime = atomEntry.updated
            entity.summary = atomEntry.summary
            entity.links = atomEntry.links
            entity.id = atomEntry.id
            entity.name = atomEntry.title
            entity.hostPath = None
        except AttributeError as e:
            messages.append({'text': 'AtomEntry missing property: %s.' % e, 'type': 'ERROR'})
            return None

        return entity

    def _matches_any(self, field, wildcardFields):
         for fieldRegex in wildcardFields:
            if re.match(fieldRegex, field):
              return True
         return False

    def _put_entity(self, id, entity, messages=None, sessionKey=None):
        """Saves an entity given an id."""

        messages = messages or []

        postargs = entity.getCommitProperties()

        # EAI endpoints dynamically declare required and optional fields
        # that can be POSTed.  Make sure that we validate against args
        try:
            entity_template = self._get_new_entity(namespace=entity.namespace, owner=entity.owner, sessionKey=sessionKey)
            allow_fields = entity_template['eai:attributes']['optionalFields']
            allow_fields.extend(entity_template['eai:attributes']['requiredFields'])
            wildcard_fields = entity_template['eai:attributes']['wildcardFields']

            to_delete = []
            for arg in postargs:
                if arg not in allow_fields and not self._matches_any(arg, wildcard_fields) and not arg.startswith('eai:'):
                    messages.append('disallowed field being posted, removing: %s' % arg)
                    logger.info('disallowed field being posted, removing: %s' % arg)
                    to_delete.append(arg)
            for arg in to_delete:
                del postargs[arg]
        except Exception as e:
            logger.info(e)

        return self._put_args(id, postargs, messages, sessionKey=sessionKey)

    def get(self, id=None, host_path=None):
        """Loads a record given an id."""

        if id == None and self.model.resource_default:
            id = self.model.resource_default

        entity = self._get_entity(id, host_path=host_path)

        if not entity:
            return None

        return self._from_entity(entity)

class SplunkRESTModel(object):
    """Model wrapper around splunkd related RESTful resources"""

    resource = ''
    resource_default = None

    @classmethod
    def manager(cls):
        return SplunkRESTManager(cls)

    @classmethod
    def get(cls, id=None, sessionKey=None):
        """For Nate, a shortcut to manager().get()"""
        return SplunkRESTManager(cls, sessionKey=sessionKey).get(id)

    @classmethod
    def all(cls, *args, **kwargs):
        """For Nate, a shortcut to manager().all()"""
        return SplunkRESTManager(cls).all(*args, **kwargs)

    @classmethod
    def order_by(cls, *args, **kwargs):
        return SplunkRESTManager(cls).order_by(*args, **kwargs)

    @classmethod
    def search(cls, *args, **kwargs):
        return SplunkRESTManager(cls).search(*args, **kwargs)

    @classmethod
    def build_id(cls, name, namespace, owner, host_path=None):
        '''
        Generates an id string from an object name and pre-defined resource
        URI path
        '''
        return splunk.entity.buildEndpoint(cls.resource, name, namespace, owner, hostPath=host_path)


    @classmethod
    def TODO_get_meta_fields(cls):
        '''
        This is a shim method to get the static description of a model class.
        This method should go away when this model thing is refactored using
        metaclasses.
        '''
        field_set = {}
        for prop in dir(cls):
            obj = getattr(cls, prop)
            if isinstance(obj, Field):
                field_set[prop] = obj
        return field_set


    @classmethod
    def get_mutable_fields(cls):
        '''
        Returns a list of field names that are mutable (on update)
        '''
        mutable_set = []
        for (key, field) in list(cls.TODO_get_meta_fields().items()):
            if field.get_is_mutable():
                mutable_set.append(key)
        return mutable_set


    @classmethod
    def parse_except_messages(cls, e):
        """
        We raise three variant exception-like objects.
        Does it's best to extract a list of message strings.
        """
        messages = []
        if hasattr(e, 'extendedMessages') and e.extendedMessages:
            if isinstance(e.extendedMessages, splunk.util.string_type):
                messages.append(e.extendedMessages)
            else:
                for item in e.extendedMessages:
                    messages.append(item.get('text'))
        if hasattr(e, 'msg') and e.msg:
            if isinstance(e.msg, splunk.util.string_type):
                messages.append(e.msg)
            elif isinstance(e.msg, list):
                for item in e.msg:
                    if isinstance(item, dict):
                        messages.append(item.get('text'))
                    else:
                        messages.append(e.msg[item])
        if hasattr(e, 'args') and e.args[0]:
            if isinstance(e.args[0], splunk.util.string_type):
                messages.append(e.args[0])
            elif isinstance(e.args[0], list):
                for item in e.args[0]:
                    if isinstance(item, dict):
                        messages.append(item.get('text'))
                    else:
                        messages.append(e.args[0][item])
        return list(set(messages)) 
    
    def set_entity_fields(self, entity):
        for (attr, field) in self.model_fields.items():
            setattr(self, attr, field.from_apidata(entity, attr))

        return True

    def _parse_id(self, entity):
        try:
            self.id = urllib_parse.urlsplit(entity.id)[2]
        except Exception:
            self.id = None

    def _parse_links(self, entity):
        self.action_links = entity.links

    def from_entity(self, entity):
        self._parse_id(entity)
        self._parse_links(entity)

        if not self.id:
            return False

        self.name = entity.name
        # update owner and namespace from the entity
        if 'eai:acl' in entity:
           self.owner     = entity['eai:acl']['owner']
           self.namespace = entity['eai:acl']['app'  ]

        return self.set_entity_fields(entity)

    def delete(self):
        """Delete a matching record"""

        if not self.id:
            return

        response, content = splunk.rest.simpleRequest(self.id, method='DELETE', raiseAllErrors=True)

        if response.status == 200:
            self.id = None
            return True

        return False

    def update(self, fields):
        for field in fields:
            parts = field.split('.')
            base = self
            for part in parts[0:-1]:
                base = getattr(base, part, None)
                if not base:
                    break

            if base:
                setattr(base, parts[-1], fields[field])

    def __init__(self, namespace, owner, name, entity=None, host_path=None, sessionKey=None, **kwargs):
        self.host_path  = host_path
        self.sessionKey = sessionKey
        self.owner      = owner
        self.namespace  = namespace
        self.name       = name
        self.id         = None
        self.entity     = entity
        self.errors     = []

        self.model_fields = {}

        for i in dir(self):
            obj = getattr(self, i, None)

            if not obj:
                continue

            if not isinstance(obj, Field):
                continue

            setattr(self, i, obj.get())
            self.model_fields[i] = obj

        if not self.entity and self.resource:
            self.entity = self.manager()._get_new_entity(self.namespace, self.owner,
                                                         host_path=self.host_path,
                                                         sessionKey=self.sessionKey)

            self.set_entity_fields(self.entity)
            self.entity.id = None


        self.update(kwargs)


    def __str__(self):
        return "Owner: %s, Namespace: %s, Name: %s, Id: %s" % (self.owner, self.namespace, self.name, self.id)

    def __eq__(self, other):
        return isinstance(other, self.__class__) \
            and (self.id is not None and other.id is not None) \
            and self.id == other.id

    def _fill_entity(self, entity, fill_value=''):
        """Stuffs this object into the entity."""

        for attr, attr_value in self.__class__.__dict__.items():
            if isinstance(attr_value, Field):
                attr_value.to_api(getattr(self, attr, None), attr, entity, fill_value)

    def create(self):
        """Creates a new version of this object."""

        if self.id:
            return False

        if not self.entity:
            self.entity = self.manager()._get_new_entity(self.namespace, self.owner,
                                                         host_path=self.host_path,
                                                         sessionKey=self.sessionKey)

        self._fill_entity(self.entity, None)

        self.entity['name'] = self.name

        messages = []
        new_endpoint = splunk.entity.buildEndpoint(self.resource, namespace=self.namespace,
                                                   owner=self.owner, hostPath=self.host_path)
        newEntity = self.manager()._put_entity(new_endpoint, self.entity, messages, sessionKey=self.sessionKey)

        if not newEntity:
            logger.debug(messages)
            return None

        self.entity = newEntity
        self.from_entity(self.entity)

        return True

    def save(self):
        """Save the current object"""

        if not self.id:
            return self.create()

        if not self.entity:
            self.id = None
            return self.create()

        self._fill_entity(self.entity)

        # ensure that non-mutable fields are not passed back to splunkd
        for field in self.model_fields:
            if not self.model_fields[field].get_is_mutable():
                logger.debug('removing non-mutable field: %s' % field)
                try:
                    del self.entity.properties[self.model_fields[field].get_api_name(field)]
                except KeyError:
                    pass

        messages = []
        newEntity = self.manager()._put_entity(self.id, self.entity, messages, sessionKey=self.sessionKey)

        if not newEntity:
            logger.debug(messages)
            return False

        self.entity = newEntity
        return True

    def passive_save(self):
        """
        Returns a boolean over raising an exception and adds text message to error instance member.
        NOTE: Flushes errors instance member before adding messages to avoid duplicate/stale entries.
        """
        self.errors = []
        try:
            self.save()
        except Exception as e:
            error_filter = ['Bad Request']
            regex = re.compile("In handler '[^\']+':")
            self.errors = [re.sub(regex, '', x).lstrip() for x in self.parse_except_messages(e) if x not in error_filter]
            return False
        else:
            return True

    def is_mutable(self, attrname):
        """
        Accessor for mutability of a field. Currently fields are singletons for all model instances.
        TODO: Add richer field object support and deep copy of field objects.
        """
        parts = attrname.split('.')
        field = None
        for index, item in enumerate(parts):
            if index==0:
                field = self.model_fields[item]
            else:
                field = getattr(field, item)
        if not field.is_mutable:
            return False
        return 'eai:attributes' not in self.entity or (field.get_api_name(attrname) in self.entity['eai:attributes']['optionalFields']) or (field.get_api_name(attrname) in self.entity['eai:attributes']['requiredFields']) or (field.get_api_name(attrname) in self.entity['eai:attributes']['wildcardFields'])

class ObjectMetadataModel(SplunkRESTModel):
    can_change_perms = BoolField()
    can_share_app    = BoolField()
    can_share_global = BoolField()
    can_share_user   = BoolField()
    can_write        = BoolField()
    modifiable       = BoolField()
    owner            = Field()
    sharing          = Field(default_value='user')
    perms            = Field()

    def __init__(self, namespace, owner, name, entity=None, host_path=None, sessionKey=None):
        # grab all of the keys from the EAI block
        self.sessionKey = sessionKey
        self.host_path = host_path
        super(ObjectMetadataModel, self).__init__(namespace, owner, name, entity,
                                                  host_path=host_path,
                                                  sessionKey=sessionKey)

    def create(self):
        return False

    def save(self):
        if not self.id:
            return False

        self.postargs = {}
        self.postargs['sharing'] = self.sharing
        self.postargs['owner']   = self.owner

        messages = []
        newEntity = self.manager()._put_args(self.id + "/acl", self.postargs,
                                             messages, sessionKey=self.sessionKey)

        if not newEntity:
            logger.debug(messages)
            return None

        self.entity = newEntity
        self.from_entity(self.entity)

        return True

    def set_entity_fields(self, entity):
        super(ObjectMetadataModel, self).set_entity_fields(entity['eai:acl'])

    def __can_remove(self):
        '''
        Property getter for the remove <link> attribute on EAI objects
        This is populated by the base entity parser
        '''
        for pair in self.action_links:
            if pair[0] == LINK_REMOVE_KEY:
                return True
        return False
    # map property getter method
    can_remove = property(__can_remove)


class SplunkAppObjModel(SplunkRESTModel):
    def __init__(self, namespace, owner, name, entity=None, host_path=None, sessionKey=None, **kwargs):
        self.metadata = ObjectMetadataModel(namespace, owner, name, host_path=host_path, sessionKey=sessionKey)

        super(SplunkAppObjModel, self).__init__(namespace, owner, name, entity,
                                                host_path=host_path, sessionKey=sessionKey, **kwargs)

        self.metadata.from_entity(self.entity)
        self.metadata.set_entity_fields(self.entity)


    def from_entity(self, entity):
        super(SplunkAppObjModel, self).from_entity(entity)

        self.metadata.from_entity(entity)

    def _set_sharing(self, level):
        self.metadata.sharing = level

        if self.metadata.save():
            self.id = self.metadata.id
            return True

        return False

    def share_app(self):
        return self._set_sharing("app")

    def share_global(self):
        return self._set_sharing("global")

    def unshare(self):
        return self._set_sharing("user")

    def create(self):
        if self.metadata.sharing != 'user':
            self.owner = 'nobody'

        if super(SplunkAppObjModel, self).create():
            self.metadata.from_entity(self.entity)
            return True

        return False


if __name__ == '__main__':

    import unittest
    import splunk.auth as auth

    class HostPathTest(unittest.TestCase):

        class TestModel(SplunkAppObjModel):
            resource = 'apps/local'

        def testGetEntityWithHostPath(self):
            '''Test getting an entity using a host_path'''
            sessionKey = auth.getSessionKey('admin', 'changeme')
            manager = SplunkRESTManager(self.TestModel, sessionKey=sessionKey)
            manager.get(id='services/apps/local/search', host_path="%s://%s:%s" % (splunk.getDefault('protocol'), splunk.getDefault('host'), splunk.getDefault('port')))


    # exec all tests
    loader = unittest.TestLoader()
    suites = []
    suites.append(loader.loadTestsFromTestCase(HostPathTest))
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
