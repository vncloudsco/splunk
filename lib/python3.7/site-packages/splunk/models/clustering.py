'''
Represents models for cluster management
'''

from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field, BoolField, EpochField, IntField, ListField, FloatField, FloatByteField, IntByteField, DictField


class ClusterMasterPeer(SplunkAppObjModel):
    '''
    Represents a master's cluster peer state
    '''

    resource             = 'cluster/master/peers' 

    active_bundle_id     = Field(is_mutable=False)
    apply_bundle_status  = DictField(is_mutable=False)
    base_generation_id   = IntField(is_mutable=False)
    bucket_count         = IntField(is_mutable=False)
    bucket_count_by_index = DictField(is_mutable=False)
    delayed_buckets_to_discard = ListField(is_mutable=False)
    fixup_set            = ListField(is_mutable=False)
    host_port_pair       = Field(is_mutable=False)
    is_searchable        = BoolField(is_mutable=False)        
    label                = Field(is_mutable=False)
    last_heartbeat       = EpochField(is_mutable=False)
    latest_bundle_id     = Field(is_mutable=False)
    pending_job_count    = IntField(is_mutable=False)
    primary_count        = IntField(is_mutable=False)
    primary_count_remote = IntField(is_mutable=False)
    replication_count    = IntField(is_mutable=False)
    replication_port     = IntField(is_mutable=False)
    replication_use_ssl  = BoolField(is_mutable=False)
    search_state_counter = DictField(is_mutable=False)
    site                 = Field(is_mutable=False)
    status               = Field(is_mutable=False)
    status_counter       = DictField(is_mutable=False)

class ClusterMasterGeneration(SplunkAppObjModel):
    '''
    Represents a master's generation info
    '''

    resource             = '/cluster/master/generation'

    generation_id        = IntField(is_mutable=False)
    generation_peers     = DictField(is_mutable=False)
    last_complete_generation_id = IntField(is_mutable=False)
    multisite_error      = Field(is_mutable=False)
    pending_generation_id = IntField(is_mutable=False)
    pending_last_attempt = IntField(is_mutable=False)
    pending_last_reason  = Field(is_mutable=False)
    replication_factor_met = BoolField(is_mutable=False)
    search_factor_met    = BoolField(is_mutable=False)
    was_forced           = BoolField(is_mutable=False)

class ClusterMasterBucket(SplunkAppObjModel):
    '''
    Represents a master's cluster bucket state
    '''

    resource             = 'cluster/master/buckets'

    bucket_size          = IntField(is_mutable=False)
    constrain_to_origin_site = BoolField(is_mutable=False)
    force_roll           = BoolField(is_mutable=False)
    frozen               = BoolField(is_mutable=False)
    index                = Field(is_mutable=False)
    origin_site          = Field(is_mutable=False)    
    peers                = DictField(is_mutable=False)
    primaries_by_site    = DictField(is_mutable=False)
    rep_count_by_site    = DictField(is_mutable=False)
    search_count_by_site = DictField(is_mutable=False)
    service_after_time   = IntField(is_mutable=False)
    standalone           = BoolField(is_mutable=False)

class ClusterMasterInfo(SplunkAppObjModel):
    '''
    Represents a master node's state
    '''

    resource             = 'cluster/master/info'

    active_bundle        = DictField(is_mutable=False)
    apply_bundle_status  = DictField(is_mutable=False)
    indexing_ready_flag  = BoolField(is_mutable=False)
    initialized_flag     = BoolField(is_mutable=False)
    label                = Field(is_mutable=False)
    latest_bundle        = DictField(is_mutable=False)
    maintenance_mode     = BoolField(is_mutable=False)
    multisite            = BoolField(is_mutable=False)
    rolling_restart_flag = BoolField(is_mutable=False)
    service_ready_flag   = BoolField(is_mutable=False)
    start_time           = IntField(is_mutable=False)

class ClusterMasterSite(SplunkAppObjModel):
    '''
    Represents a master's cluster sites
    '''
    resource             = 'cluster/master/sites'

    peers                = ListField(is_mutable=False) 

class ClusterMasterSearchhead(SplunkAppObjModel):
    '''
    Represents search heads
    '''
    resource             = 'cluster/master/searchheads'

    host_port_pair       = Field(is_mutable=False)
    label                = Field(is_mutable=False)
    site                 = Field(is_mutable=False)
    status               = Field(is_mutable=False)

class ClusterMasterIndex(SplunkAppObjModel):
    '''
    Represents a master's cluster indexes
    '''
    resource                   = 'cluster/master/indexes'

    buckets_with_excess_copies = IntField(is_mutable=False)
    buckets_with_excess_searchable_copies = IntField(is_mutable=False)
    index_size                 = IntField(is_mutable=False)
    is_searchable              = BoolField(is_mutable=False)
    num_buckets                = IntField(is_mutable=False)
    replicated_copies_tracker  = ListField(is_mutable=False)
    searchable_copies_tracker  = ListField(is_mutable=False)
    sort_order                 = IntField(is_mutable=False)
    total_excess_bucket_copies = IntField(is_mutable=False)
    total_excess_searchable_copies = IntField(is_mutable=False)

class ClusterSearchheadGeneration(SplunkAppObjModel):
    '''
    Represents a searchhead node's state
    '''

    resource               = 'cluster/searchhead/generation'

    generation_error       = Field(is_mutable=False)
    generation_id          = Field(is_mutable=False)
    generation_peers       = DictField(is_mutable=False)
    is_searchable          = BoolField(is_mutable=False)
    multisite_error        = IntField(is_mutable=False)
    replication_factor_met = BoolField(is_mutable=False)
    search_factor_met      = BoolField(is_mutable=False)
    status                 = BoolField(is_mutable=False)
    was_forced             = BoolField(is_mutable=False)

class ClusterSearchheadConfig(SplunkAppObjModel):
    '''
    Represents a searchhead node's state
    '''

    resource               = 'cluster/searchhead/searchheadconfig'

    master_uri             = Field(is_mutable=False) 
    secret                 = Field(is_mutable=False)
    site                   = Field(is_mutable=False)

class ClusterSlaveBucket(SplunkAppObjModel):
    '''
    Represents a slave's cluster bucket state
    '''

    resource               = 'cluster/slave/buckets'

    checksum               = Field(is_mutable=False)
    earliest_time          = IntField(is_mutable=False)
    generations            = DictField(is_mutable=False)
    index                  = Field(is_mutable=False)
    latest_time            = IntField(is_mutable=False)
    search_state           = Field(is_mutable=False)
    status                 = Field(is_mutable=False)

class ClusterSlaveInfo(SplunkAppObjModel):
    '''
    Represents a slave node's state
    TODO
    '''
    resource               = 'cluster/slave/info'

    active_bundle          = DictField(is_mutable=False)
    base_generation_id     = IntField(is_mutable=False) 
    is_registered          = BoolField(is_mutable=False)
    last_heartbeat_attempt = IntField(is_mutable=False)
    latest_bundle          = DictField(is_mutable=False)
    maintenance_mode       = IntField(is_mutable=False)
    restart_state          = Field(is_mutable=False)
    site                   = Field(is_mutable=False)
    status                 = Field(is_mutable=False)

class ClusterSlaveControl(SplunkAppObjModel):
    '''
    Represents a slave control endpoint
    TODO
    '''
    resource               = 'cluster/slave/control'

class ClusterConfig(SplunkAppObjModel):
    '''
    Represents the current node
    '''
    resource               = 'cluster/config'

    cxn_timeout            = IntField()
    disabled               = BoolField()
    forwarderdata_rcv_port = IntField()
    forwarderdata_use_ssl  = BoolField()
    heartbeat_period       = IntField()
    heartbeat_timeout      = IntField()
    master_uri             = Field()    
    max_peer_build_load    = IntField()
    max_peer_rep_load      = IntField()
    mode                   = Field()
    multisite              = BoolField()
    percent_peers_to_restart = IntField()
    ping_flag              = BoolField()
    quiet_period           = IntField()
    rcv_timeout            = IntField()
    register_forwarder_address = Field()
    register_replication_address = Field()
    register_search_address = Field()
    rep_cxn_timeout        = IntField()
    rep_max_rcv_timeout    = IntField()
    rep_max_send_timeout   = IntField()
    rep_rcv_timeout        = IntField()
    rep_send_timeout       = IntField()
    replication_factor     = IntField()
    replication_port       = IntField()
    replication_use_ssl    = BoolField()
    restart_timeout        = IntField()
    search_factor          = IntField()
    search_files_retry_timeout = IntField()
    secret                 = Field()
    send_timeout           = IntField()
    site                   = Field()