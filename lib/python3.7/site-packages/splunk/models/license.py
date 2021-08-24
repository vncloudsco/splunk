'''
Represents models for license management
'''

from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field, BoolField, EpochField, IntField, ListField, FloatField, FloatByteField, IntByteField, DictField


class License(SplunkAppObjModel):
    '''
    Represents a single license object
    '''

    resource = 'licenser/licenses' 

    creation_time       = EpochField()
    expiration_time     = EpochField()
    features            = ListField()
    hash                = Field(api_name='license_hash')
    label               = Field()
    max_violations      = IntField()
    payload             = Field()
    quota_bytes         = FloatField(api_name='quota')
    sourcetypes         = ListField()
    stack_name          = Field(api_name='stack_id')
    status              = Field()
    type                = Field()
    window_period       = IntField()
    is_unlimited        = BoolField()



class Stack(SplunkAppObjModel):
    '''
    Represents a license stack container
    '''

    resource = 'licenser/stacks'

    is_unlimited    = BoolField()
    label           = Field()
    quota_bytes     = FloatField(api_name='quota')
    type            = Field()
    


class Pool(SplunkAppObjModel):
    '''
    Represents a license pool container
    '''

    resource = 'licenser/pools'

    description         = Field()
    is_catch_all        = BoolField()
    penalty             = IntField()
    quota_bytes         = IntByteField(api_name='quota')
    slaves              = ListField()
    slaves_usage_bytes  = DictField(is_mutable=False)
    stack_name          = Field(api_name='stack_id', is_mutable=False)
    used_bytes          = FloatField()
    is_unlimited        = BoolField()



class SelfConfig(SplunkAppObjModel):
    '''
    Represents a Splunk license tracker (master) server
    '''

    resource = 'licenser/localslave'
    resource_default = 'licenser/localslave/license'

    connection_timeout                  = IntField(is_mutable=False)
    guid                                = ListField(is_mutable=False)
    features                            = DictField(is_mutable=False)
    last_master_contact_attempt_time    = EpochField(is_mutable=False)
    last_master_contact_success_time    = EpochField(is_mutable=False)
    last_trackerdb_service_time         = EpochField(is_mutable=False)
    license_keys                        = ListField(is_mutable=False)
    master_guid                         = Field(is_mutable=False)
    master_uri                          = Field()
    receive_timeout                     = IntField(is_mutable=False)
    send_timeout                        = IntField(is_mutable=False)
    slave_name                          = Field(api_name='slave_id', is_mutable=False)
    slave_label                         = Field(is_mutable=False)
    squash_threshold                    = IntField(is_mutable=False)



class Slave(SplunkAppObjModel):
    '''
    Represents a Splunk license slave server
    '''

    resource = 'licenser/slaves'

    added_usage_parsing_warnings    = BoolField()
    active_pool_names               = ListField(api_name='active_pool_ids', is_mutable=False)
    pool_names                      = ListField(api_name='pool_ids', is_mutable=False)
    stack_names                     = ListField(api_name='stack_ids', is_mutable=False)
    warning_count                   = IntField()
    label                           = Field()


class Message(SplunkAppObjModel):
    '''
    Represnts a licenser message
    '''

    resource = 'licenser/messages'

    category        = Field(is_mutable=False)
    create_time     = EpochField()
    description     = Field()
    pool_name       = Field(api_name='pool_id')
    severity        = Field(default_value='ERROR')
    slave_name      = Field(api_name='slave_id')
    stack_name      = Field(api_name='stack_id')



class Group(SplunkAppObjModel):
    '''
    Represents a license group object
    '''

    resource = 'licenser/groups'

    is_active       = BoolField()
    stack_names     = ListField(api_name='stack_ids', is_mutable=False)

