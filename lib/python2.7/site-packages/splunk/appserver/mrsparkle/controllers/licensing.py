from __future__ import division
from builtins import range
from past.utils import old_div
import cgi
import datetime
import json
import logging
import operator
import os
import tempfile
import sys
import time

import cherrypy

import splunk
import splunk.auth
import splunk.rest
import splunk.util
from splunk.appserver.mrsparkle.controllers import BaseController
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
from splunk.appserver.mrsparkle.lib import cached
from splunk.appserver.mrsparkle.lib import util
from splunk.models.license import License, Pool, Stack, Slave, Message, SelfConfig, Group
from splunk.appserver.mrsparkle.lib.capabilities import Capabilities

logger = logging.getLogger('splunk.appserver.controllers.licensing')

# define default stack name
DEFAULT_STACK_NAME = 'enterprise'

# define set of license groups that allow pool creation
POOLABLE_GROUPS = ['Enterprise']

# define the model value for a pool's catch-all slave list
CATCHALL_SLAVE_LIST = ['*']

def capability_error_mask(fn):
    """
    Decorator for HTTP request methods. Handles all
    splunk.AuthorizationFailed exceptions by delegating
    to the `deny_access` method.
    """
    def mask(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except splunk.AuthorizationFailed as ex:
            self.deny_access()
    return mask

class LicensingController(BaseController, Capabilities):
    """
    Handle licensing messaging and modifications
    """

    def supports_blacklist_validation(self):
        """
        Overridden method from BaseController!
        """
        return True

    #
    # attach common template args
    #

    def render_template(self, template_path, template_args = {}):
        template_args['appList'] = self.get_app_manifest()
        return super(LicensingController, self).render_template(template_path, template_args)
    
        
    def get_app_manifest(self):
        '''
        Returns a dict of all available apps to current user
        '''
        
        output = cached.getEntities('apps/local', search=['disabled=false', 'visible=true'], count=-1)
                
        return output

    #
    # trial -> free switching
    #
    
    @expose_page(methods=['GET', 'POST'])
    @capability_error_mask
    def expired(self, formset_mode=None, return_to=None, **unused):
        
        template_args = {
            'can_change_license': False,
            'return_to': self.make_url(['manager', 'system', 'licensing'])
        }
        
        free_group = None
        try:
            free_group = Group.get(Group.build_id(
                'Free',
                namespace=None,
                owner=None
            ))
            template_args['can_change_license'] = True
        except splunk.AuthorizationFailed:
            pass
        except Exception as e:
            logger.exception(e)
            template_args['controller_exception'] = e

        if cherrypy.request.method == 'POST' and free_group:
            
            if formset_mode == 'free':
                try:
                    free_group = Group.get(Group.build_id(
                        'Free',
                        namespace=None,
                        owner=None
                    ))
                    free_group.is_active = True
                    free_group.save()

                    template_args['is_success'] = True
                
                except Exception as e:
                    logger.exception(e)
                    template_args['controller_exception'] = e

            elif formset_mode == 'add_license':
                
                return self.redirect_to_url(
                    ['manager', 'system', 'licensing', 'licenses', 'new']
                )


        return self.render_template('licensing/expired.html', template_args)



    #
    # overview
    #

    @route('/')
    @expose_page(methods=['GET'])
    @capability_error_mask
    def show_summary(self, **unused):
        '''
        Renders the new license summary page
        '''
        # Access Control
        
        self.checkServerInfo()

        # Note: no need for ".prod_lite" suffix, 
        # this finds the right file based on the splunk type.
        if not self.can_access_manager_xml_file('licensing_stacks'):
            self.deny_access()

        #

        # retrieve data
        #

        # get local slave info
                
        if util.isLite():
             return self.render_template('pages/system.html', {'app': None, 'page':'licensing', 'dashboard': '', 'splunkd': {}})

        self_config = SelfConfig.get()

        local_master_uri = None 
        if self_config.master_uri.lower() not in ['', 'self']:
            return self.show_slave_summary()

        # get all slaves, and find the local one in the mix
        slave_label_map = {}
        slaves = Slave.all(count_per_req=10000)
        local_slave = None
        for slave in slaves:
            slave_label_map[slave.name] = slave.label
            if slave.name == self_config.slave_name:
                local_slave = slave
        if not local_slave:
            raise Exception('Could not retrieve slave information for slave name: %s' % self_config.slave_name)
        slave_count = len(slaves)
    
        # get active group
        active_group = Group.all().filter(is_active=True)
        if len(active_group) == 0:
            logger.warn('no active license groups found; redirecting user to "add license" page')
            self.redirect_to_url(['manager', 'system', 'licensing', 'licenses', 'new'])

        active_group = active_group[0]

        # get associated stacks
        stack_query = Stack.all()
        stacks = []
        for stack in stack_query:
            if stack.name in active_group.stack_names:
                stacks.append(stack)

        # get associated pools
        pool_query = Pool.all()
        pools = []
        catchall_pool_names = []
        for pool in pool_query:
            if pool.stack_name in [s.name for s in stacks]:
                pools.append(pool)
                if pool.slaves == CATCHALL_SLAVE_LIST:
                    catchall_pool_names.append(pool.name)

        licenses = License.all()
        messages = Message.all()


        #
        # generate output info
        #

        stack_table = []
        for stack in stacks:
            #if not stack.quota_bytes:
            #    remaining_perc = None
            #else:
            #    remaining_perc = stack.remaining_bytes / stack.quota_bytes
            stack_table.append({
                'name': stack.name,
                'quota_bytes': stack.quota_bytes,
                'label': stack.label,
                'is_unlimited': stack.is_unlimited
                #'remaining_bytes': stack.remaining_bytes,
                #'remaining_perc': remaining_perc
            })

        # compile a summary list of messages by category
        hard_messages = {}
        soft_messages = {}
        for message in messages:
            if message.severity == 'WARN':
                message_type = hard_messages
            else: 
                message_type = soft_messages   

            message_type.setdefault(message.category, {
                'severity': message.severity.lower(),
                'count': 0, 
                'latest_time': datetime.datetime.fromtimestamp(0, splunk.util.localTZ), 
                'slaves': set()}
            )
            message_type[message.category]['count'] += 1
            message_type[message.category]['latest_time'] = max(
                message.create_time,
                message_type[message.category]['latest_time']
            )
            message_type[message.category]['slaves'].add(slave_label_map.get(message.slave_name, message.slave_name))




        # loop over the per-slave data embedded in each pool descriptor
        pool_table = []
        slave_table = []
        local_used_bytes = 0.0
        for pool in pools:

            effective_global_quota = pool.quota_bytes['byte_value']
            if pool.quota_bytes['value_mode'] == 'MAX':
                for stack in stacks:
                    if pool.stack_name == stack.name:
                        effective_global_quota = stack.quota_bytes
                        break
                
            pool_table.append({
                'name': pool.name,
                'stack_name': pool.stack_name,
                'used_bytes': pool.used_bytes,
                'quota_bytes': effective_global_quota,
                'quota_mode': pool.quota_bytes['value_mode'],
                'is_unlimited': pool.is_unlimited
            })

            for slave in sorted(pool.slaves_usage_bytes):
                tmp_slave_bytes = float(pool.slaves_usage_bytes[slave])
                
                # accum the usage for the local slave
                if slave == self_config.slave_name:
                    local_used_bytes += tmp_slave_bytes
                
                if not effective_global_quota:
                    used_perc = None
                else:
                    used_perc = old_div(tmp_slave_bytes, effective_global_quota)

                slave_table.append({
                    'pool_name': pool.name,
                    'name': slave_label_map.get(slave, slave),
                    'used_bytes': tmp_slave_bytes,
                    'used_perc': used_perc
                })

        license_table = []
        for license in licenses:
            license_table.append({
                'name': license.name,
                'label': license.label,
                'type': license.type,
                'stack_name': license.stack_name,
                'quota_bytes': license.quota_bytes,
                'expiration_time': license.expiration_time,
                'status': license.status.upper(),
                'can_remove': license.metadata.can_remove,
                'is_unlimited': license.is_unlimited
            })
        license_table.sort(key=operator.itemgetter('expiration_time'))


        # the UI will only support managing pools within the enterprise stack
        if active_group.name in POOLABLE_GROUPS:
            can_edit_pools = True
        else:
            can_edit_pools = False
        
        # assemble into mako dict
        template_args = {
            'local_slave_name': local_slave.label,
            'local_used_bytes': local_used_bytes,
            'local_warning_count': local_slave.warning_count,
            'local_master_uri': local_master_uri,
            'active_group_name': active_group.name,
            'default_stack_name': DEFAULT_STACK_NAME,
            'slave_count': slave_count,
            'pool_table': pool_table,
            'stack_table': stack_table,
            'slave_table': slave_table,
            'license_table': license_table,
            'hard_messages': hard_messages,
            'soft_messages': soft_messages,
            'can_edit_pools': can_edit_pools,
            'catchall_pool_names': catchall_pool_names,
            'can_be_remote_master': self_config.features.get('CanBeRemoteMaster') == 'ENABLED',
            'showLicenseUsage': (cherrypy.config['product_type'] != 'hunk')
        }

        return self.render_template('/licensing/overview.html', template_args)



    
    def show_slave_summary(self):
        '''
        sub-method to render overview page when server is in slave mode;
        called from show_summary() method above
        '''

        # get local slave info
        self_config = SelfConfig.get()

        return self.render_template('/licensing/slave.html', {'self_config': self_config})




    #
    # pools
    #

    @route('/:path=pools/:action')
    @expose_page(methods=['GET', 'POST'])
    @capability_error_mask
    def edit_pool(self, 
        action,
        stack_name=DEFAULT_STACK_NAME, 
        pool_name=None, 
        return_to=None,
        formset_name=None,
        formset_quota_mode=None,
        formset_quota_value=None,
        formset_quota_units=None,
        formset_description=None,
        formset_slaves=None,
        formset_slave_mode=None,
        **unused
    ):
        '''
        Handles adding a new pool or editing an existing pool
        '''

        
        # setup mako args
        template_args = {
            'action': action,
            'return_to': self.make_url(['manager', 'system', 'licensing']),
            'stack_name': stack_name,
            'is_success': False
        }

        # check that desired stack exists
        try:
            stack_id = Stack.build_id(stack_name, namespace=None, owner=None)
            stack = Stack.get(stack_id)
            stack_label = stack.label

        except splunk.ResourceNotFound as e:
            logger.exception(e)
            raise cherrypy.HTTPError(400, 'The "%s" stack was not found.  This interface only supports managing pools within that stack.' % DEFAULT_STACK_NAME)

        # determine unallocated volume
        pools = Pool.all().filter(stack_name=stack_name)
        total_pool_bytes = sum([p.quota_bytes['byte_value'] for p in pools])
        unallocated_bytes = stack.quota_bytes - total_pool_bytes
        template_args['unallocated_bytes'] = unallocated_bytes

        # determine correct model object init
        if action == 'edit':
            pool_id = Pool.build_id(pool_name, namespace=None, owner=None)
            pool_object = Pool.get(pool_id)

        elif action == 'add':
            pool_object = Pool(namespace=None, owner=None, name=formset_name)
            pool_object.quota_bytes['value_mode'] = 'MAX'
        
        else:
            raise Exception('unrecognized endpoint: %s' % action)
    
        # determine allocation mode
        if pool_object.quota_bytes['value_mode'] == 'MAX':
            quota_mode = 'all'
        else:
            quota_mode = 'explicit'

        # normalize the output to MB
        # the API always returns values in bytes so we have no idea what
        # units the user may have specified; therefore all display on this
        # page defaults to MB
        if action == 'add' and not pool_object.quota_bytes['byte_value']:
            quota_value = max(0, unallocated_bytes // 2**20)
        else:
            quota_value = (pool_object.quota_bytes['byte_value'] or 0) // 2**20
        quota_units = 'MB'

        # determine if another pool already has catch-all
        can_be_catch_all = True 
        for pool in pools:
            if pool.slaves == CATCHALL_SLAVE_LIST and pool.name != pool_object.name:
                can_be_catch_all = False
                break

        # determine indexer selection mode
        if not len(pool_object.slaves) and can_be_catch_all:
            slave_mode = 'catchall'
        else:
            slave_mode = 'explicit'

        # get list of pools that maintain true exclusivity on slaves as
        # opposed to listing them due to auto-inclusion via catch-all mechanism
        restrictive_pools = set([p.name for p in pools if (p.slaves != CATCHALL_SLAVE_LIST and (p.slaves != []))])

        # get list of available indexers that could be assigned
        slaves = Slave.all(count_per_req=10000)
        slave_list = []
        slave_label_map = {}
        for slave in slaves:
            slave_label_map[slave.name] = slave.label
            slave_is_eligible = True

            # slaves that are explicitly assigned to pool within the same
            # stack cannot be assigned again; slaves that are registered
            # with a catch-all pool are still eligible to be explicitly set
            if (stack_name in slave.stack_names) \
                    and (set(slave.pool_names) & restrictive_pools) \
                    and pool_object.name not in slave.pool_names:
                slave_is_eligible = False

            slave_list.append([
                slave.name,
                slave.label,
                slave_is_eligible
            ])

        # get list of assigned slaves (really just to map labels)
        assigned_slave_list = []
        for slave in pool_object.slaves:
            assigned_slave_list.append([
                slave,
                slave_label_map.get(slave, slave)
            ])
        assigned_slave_list.sort(key=operator.itemgetter(1))
        

        #
        # handle save action
        #

        if cherrypy.request.method == 'POST':
            pool_object.description = formset_description
            pool_object.stack_name = stack_name

            if formset_quota_mode == 'all':
                pool_object.quota_bytes['value_mode'] = 'MAX'

            else:
                pool_object.quota_bytes['value_mode'] = 'NORMAL'
                # try to peg value to actual stack quota; this is mostly
                # to handle rounding issues on write
                capped_quota = stack.quota_bytes
                try:
                    user_quota = util.convert_to_bytes(formset_quota_value + formset_quota_units)
                    capped_quota = min(capped_quota, user_quota)
                except:
                    pass

                pool_object.quota_bytes['relative_value'] = capped_quota
                pool_object.quota_bytes['units'] = None


            # deal with multi-select input for slaves
            if formset_slave_mode == 'catchall':
                pool_object.slaves = CATCHALL_SLAVE_LIST
            
            else:
                if not formset_slaves:
                    pool_object.slaves = []
                elif isinstance(formset_slaves, list):
                    pool_object.slaves = formset_slaves
                else:
                    pool_object.slaves = [formset_slaves]

            try:
                pool_object.save()
                template_args['is_success'] = True

            except Exception as e:
                logger.exception(e)
                template_args['controller_exception'] = e    


        #
        # paint
        #

        # clear the slaves list if in catchall mode so that the accumulator
        # doesn't show the *
        if pool_object.slaves == CATCHALL_SLAVE_LIST:
            assigned_slave_list = []

        template_args['stack_label'] = stack_label
        template_args['isUnlimited'] = splunk.util.normalizeBoolean(stack.is_unlimited)
        template_args['slave_list'] = slave_list
        template_args['slave_mode'] = formset_slave_mode or slave_mode
        template_args['assigned_slave_list'] = assigned_slave_list
        template_args['pool_object'] = pool_object
        template_args['pool_quota_mode'] = formset_quota_mode or quota_mode
        template_args['pool_quota_value'] = formset_quota_value or quota_value
        template_args['pool_quota_units'] = formset_quota_units or quota_units
        template_args['pool_quota_enum'] = [['MB', 'MB'], ['GB', 'GB'], ['TB', 'TB']] 
        template_args['can_be_catch_all'] = can_be_catch_all
        template_args['stack_quota_bytes'] = stack.quota_bytes
        return self.render_template('/licensing/pools/add.html', template_args)
                


    @route('/:path=pools/:action=delete')
    @expose_page(methods=['GET', 'POST'])
    @capability_error_mask
    def delete_pool(self, pool_name, return_to=None, **unused):

        template_args = {
            'return_to': self.make_url(['manager', 'system', 'licensing']),
            'was_deleted': False,
            'pool_name': pool_name,
            'slave_table': []
        }

        # check that desired stack exists
        try:
            pool_id = Pool.build_id(pool_name, namespace=None, owner=None)
            pool = Pool.get(pool_id)
            template_args['pool'] = pool

            # get server labels from GUID
            slave_table = []
            slaves = Slave.all(count_per_req=10000)
            for slave in pool.slaves_usage_bytes:
                for so in slaves:
                    if so.name == slave:
                        slave_table.append(so.label)
                        break

            template_args['slave_table'] = slave_table

            # handle save action
            if cherrypy.request.method == 'POST':
                
                pool.delete()
                template_args['was_deleted'] = True

        except splunk.AuthorizationFailed:
            raise
        except Exception as e:
            logger.exception(e)
            template_args['controller_exception'] = e    

        return self.render_template('/licensing/pools/delete.html', template_args)
        


    #
    # licenses
    #

    @route('/:path=licenses')
    @expose_page(methods=['GET'])
    @capability_error_mask
    def list_license(self, return_to=None, **kw):
        '''
        Handles the license listing page
        '''
        if util.isLite():
            raise cherrypy.HTTPError(404, _('Splunk cannot find "%s".' % cherrypy.request.path_info)) #Return page not found

        licenses = License.all()
        self_config = SelfConfig.get()

        template_args = {
            'licenses': licenses or [],
            'return_to': self.make_url(['manager', 'system', 'licensing']),
            'server_name': self_config.slave_label
        }
        return self.render_template('/licensing/licenses/list.html', template_args)



    @route('/:path=licenses/:action=view')
    @expose_page(methods=['GET'])
    @capability_error_mask
    def view_license(self, license_name, **kw):
        '''
        Handles the license view page
        '''

        template_args = {
            'license_name': license_name,
            'license': None
        }

        try:
            # first check that the license is valid
            license_object = License.get(License.build_id(
                license_name,
                namespace=None,
                owner=None
            ))
            template_args['license'] = license_object

        except splunk.AuthorizationFailed:
            raise
        except Exception as e:
            template_args['controller_exception'] = e

        return self.render_template('/licensing/licenses/details.html', template_args)



    @route('/:path=licenses/:action=new')
    @expose_page(methods=['GET', 'POST'])
    @capability_error_mask
    def add_license(self, licenseFile=None, formset_pasted_license=None, return_to=None, prompt_restart=False, **kw):
        '''
        Handles the license add/edit page
        '''

        self_config = SelfConfig.get()

        if util.isLite():
            raise cherrypy.HTTPError(404, _('Splunk cannot find "%s".' % cherrypy.request.path_info)) #Return page not found

        license_table = []
        template_name = '/licensing/licenses/add.html'
        template_args = {
            'return_to': self.make_url(['manager', 'system', 'licensing']),
            'prompt_restart': splunk.util.normalizeBoolean(prompt_restart),
            'is_success': False,
            'pasted_license': formset_pasted_license or '',
            'current_group': None,
            'new_group': None
        }

        try:
            licenses = License.all()
            for license in licenses:
                license_table.append({
                    'type': license.type,
                    'label': license.label
                })
        except Exception as e:
            logger.exception(e)
            template_args['controller_exception'] = e

        template_args['license_table'] = license_table

        # get current active group
        group = Group.all().filter(is_active=True)
        if group:
            template_args['current_group'] = group[0].name

        # handle uploads via cherrypy's built in file handling facilities
        if cherrypy.request.method == 'POST':
        
            license_object = None

            # process uploaded file first; if not there, then check for inline
            # XML being pasted in
            if isinstance(licenseFile, cherrypy._cpreqbody.Part) and licenseFile.filename:

                logger.info('processing incoming license to add: %s' % licenseFile.filename)

                # pull license into stringbuffer
                license_contents = []
                for i in range(32):
                    license_contents.append(licenseFile.file.read(8192))

                license_object = License(name=licenseFile.filename, namespace=None, owner=None)
                license_object.payload = b''.join(license_contents)

                # check for clear text; fake a new exception to notify user
                try:
                    if sys.version_info >= (3, 0):
                        license_object.payload = license_object.payload.decode('utf-8')
                    else:
                        splunk.util.unicode(license_object.payload, 'utf-8')
                except Exception as e:
                    template_args['controller_exception'] = ValueError('Invalid license file submitted')
                    license_object = None
                    
            
            elif formset_pasted_license:
                license_object = License(name=('web_%s.lic' % time.time()), namespace=None, owner=None)
                license_object.payload = formset_pasted_license


            if license_object:
                try:
                    # check if reset license type matches current license type in Light
                    if util.isLite() and '<feature>ResetWarnings</feature>' in license_object.payload and group[0].name not in license_object.payload:
                        template_args['controller_exception'] = ValueError('The reset license you are trying to apply is not a Splunk Light reset license. Please check the license to ensure that you are using the correct reset license type and try again.')
                        return self.render_template(template_name, template_args)
                    
                    license_object.create()
                    template_args['is_success'] = True

                    # check if server switched groups
                    new_group = Group.all().filter(is_active=True)
                    if new_group:
                        template_args['new_group'] = new_group[0].name

                    # or just assume that the source group can sufficiently
                    # determine if a restart is required
                    if template_args['current_group'] in ['Free', 'Forwarder', 'Trial']:
                        template_args['prompt_restart'] = True

                except Exception as e:
                    template_args['controller_exception'] = e
                    logger.exception(e)

        return self.render_template(template_name, template_args)



    @route('/:path=licenses/:action=delete')
    @expose_page(methods=['GET', 'POST'])
    @capability_error_mask
    def delete_license(self, license_id, return_to=None, **kwargs):
        '''
        Deletes a specific license
        '''

        template_args = {
            'return_to': self.make_url(['manager', 'system', 'licensing']),
            'was_deleted': False
        }

        try:
            # first check that the license is valid
            marked_license = License.get(License.build_id(
                license_id,
                namespace=None,
                owner=None
            ))
            template_args['license'] = marked_license

            # handle delete
            if cherrypy.request.method == 'POST':
                marked_license.delete()
                template_args['was_deleted'] = True
            
        except Exception as e:
            template_args['controller_exception'] = e

        return self.render_template('/licensing/licenses/delete.html', template_args)
            

    #
    # slaves
    #

    @route('/:path=indexers')
    @expose_page(methods=['GET'])
    @capability_error_mask
    def list_indexers(self, return_to=None, **kw):
        '''
        Handles the indexer listing page
        '''

        if util.isLite():
            raise cherrypy.HTTPError(404, _('Splunk cannot find "%s".' % cherrypy.request.path_info)) #Return page not found

        slaves = Slave.all(count_per_req=10000)
        self_config = SelfConfig.get()

        template_args = {
            'slaves': slaves or [],
            'return_to': self.make_url(['manager', 'system', 'licensing']),
            'server_name': self_config.slave_label
        }
        return self.render_template('/licensing/slaves/list.html', template_args)



    #
    # messages
    #

    @route('/:path=messages')
    @route('/:path=messages/:category')
    @expose_page(methods=['GET'])
    @capability_error_mask
    def list_messages(self, category=None, return_to=None, **kw):
        '''
        Handles the message listing page
        '''

        if util.isLite():
            raise cherrypy.HTTPError(404, _('Splunk cannot find "%s".' % cherrypy.request.path_info)) #Return page not found

        messages = Message.all()
        self_config = SelfConfig.get()

        if category:
            messages = messages.filter(category=category)

        # get list of available indexers that could be assigned
        slaves = Slave.all(count_per_req=10000)
        slave_label_map = {}
        for slave in slaves:
            slave_label_map[slave.name] = slave.label

        soft_messages = []
        hard_messages = []
        all_messages = []
        for message in messages:
                       
            newMessage = {
                'text': message.description,
                'create_time': message.create_time,
                'severity': message.severity.lower(),
                'pool_name': message.pool_name,
                'slave_name': slave_label_map.get(message.slave_name, message.slave_name),
                'stack_name': message.stack_name,
                'category': message.category
            }

            all_messages.append(newMessage)

            if message.category == 'license_window':
                hard_messages.append(newMessage)
            else: 
                soft_messages.append(newMessage)

        soft_messages.sort(key=operator.itemgetter('create_time'), reverse=True)
        hard_messages.sort(key=operator.itemgetter('create_time'), reverse=True)
        all_messages.sort(key=operator.itemgetter('create_time'), reverse=True)

        template_args = {
            'category': category,
            'soft_messages': soft_messages,
            'hard_messages': hard_messages,
            'all_messages': all_messages,
            'return_to': self.make_url(['manager', 'system', 'licensing']),
            'server_name': self_config.slave_label
        }
        return self.render_template('/licensing/messages/list.html', template_args)



    #
    # general license handlers
    #

    @route('/:path=self')
    @expose_page(methods=['GET', 'POST'])
    @capability_error_mask
    def edit_self(self, formset_master_server_uri=None, formset_master_server_mode=None, return_to=None, **unused):
        '''
        Changes the properties of the local slave
        '''

        if util.isLite():
            raise cherrypy.HTTPError(404, _('Splunk cannot find "%s".' % cherrypy.request.path_info)) #Return page not found

        OWN_MASTER_URI = 'self'

        is_success = False
        controller_exception = None

        # splunkd only uses one key to ID the master server; if value == self
        # then the local licenser is activated
        self_config = SelfConfig.get()

        if self_config.master_uri == OWN_MASTER_URI:
            is_own_master = True
            master_server_uri = 'https://'
            master_server_mode = 'this_server'
        else:
            is_own_master = False
            master_server_uri = self_config.master_uri
            master_server_mode = 'other_server'


        if cherrypy.request.method == 'POST':

            # empty values are assumed to be 'self'
            if formset_master_server_mode == 'this_server' or not formset_master_server_uri:
                self_config.master_uri = OWN_MASTER_URI
            else:
                self_config.master_uri = formset_master_server_uri

            try:
                self_config.save()
                is_success = True
            except Exception as e:
                logger.exception(e)
                controller_exception = e


        # generate template args; be sure to preserve form state
        template_args = {
            'is_success' : is_success,
            'return_to': self.make_url(['manager', 'system', 'licensing']),
            'controller_exception': controller_exception,
            'local_slave_name': self_config.slave_label,
            'master_server_uri': formset_master_server_uri or master_server_uri,
            'master_server_mode': formset_master_server_mode or master_server_mode,
            'is_own_master': is_own_master,
            'requires_restart': util.check_restart_required()
        }

        return self.render_template('/licensing/self.html', template_args)





    @expose_page(methods=['GET', 'POST'])
    @capability_error_mask
    def switch(self, license_group=None, return_to=None, **unused):

        if util.isLite():
            raise cherrypy.HTTPError(404, _('Splunk cannot find "%s".' % cherrypy.request.path_info)) #Return page not found

        template_args = {
            'is_success': False,
            'return_to': self.make_url(['manager', 'system', 'licensing']),
            'available_groups': [],
            'license_group': None,
            'license_map': {}
        }

        active_group = None

        # get all data
        licenses = License.all()
        groups = Group.all()
        
        # No endpoint is being hit that will raise the AuthorizationFailed
        # error for missing capabilities so check the licenses & groups results.
        if len(licenses) == 0 and len(groups) == 0:
            self.deny_access()

        # get the active group and all licenses associated with it
        for group in groups:
        
            template_args['available_groups'].append(group.name)
            if group.is_active:
                active_group = group.name

            template_args['license_map'][group.name] = []
            for license in licenses:
                if license.stack_name in group.stack_names and license.status == 'VALID':
                    template_args['license_map'][group.name].append(license.label)


        if cherrypy.request.method == 'POST':

            # redirect user to add license if newly activated group
            # does not have any licenses
            if len(template_args['license_map'].get(license_group, '')) == 0:
                logger.info('0 licenses found; redirecting user to "add license" page')
                self.redirect_to_url(
                    ['manager', 'system', 'licensing', 'licenses', 'new'], 
                    _qs={
                        'prompt_restart': 1
                    }
                )
            
            try:
                for group in groups:
                    if license_group == group.name:
                        group.is_active = True
                        group.save()
                        template_args['is_success'] = True
                        active_group = group.name
                        break
                else:
                    raise Exception('cannot activate unknown license group: %s' % license_group)

            except Exception as e:
                template_args['controller_exception'] = e


        # set tempalte sticky state
        template_args['license_group'] = license_group or active_group

        return self.render_template('/licensing/switch.html', template_args)
