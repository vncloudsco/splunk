from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field, StructuredField, BoolField, ListField, DictField, EpochField


class Summarization(SplunkAppObjModel):
    '''
    Represents an auto-summarization for a saved search
    '''
    
    resource = 'admin/summarization' 

    saved_searches                                = DictField('saved_searches', is_mutable=False)
    saved_searches_count                          = Field('saved_searches.count')
    buckets                                       = Field('summary.buckets', is_mutable=False)
    complete                                      = Field('summary.complete', is_mutable=False)

    hash                                          = Field('summary.hash', is_mutable=False)
    regularHash                                   = Field('summary.regularHash', is_mutable=False)
    normHash                                      = Field('summary.normHash', is_mutable=False)

    unique_id                                     = Field('summary.id', is_mutable=False)
    regular_id                                    = Field('summary.regular_id', is_mutable=False)
    normalized_id                                 = Field('summary.normalized_id', is_mutable=False)

    chunks                                        = Field('summary.chunks', is_mutable=False)
    earliest_time                                 = Field('summary.earliest_time', is_mutable=False)
    latest_time                                   = Field('summary.latest_time', is_mutable=False)
    time_range                                    = Field('summary.time_range', is_mutable=False)
    load_factor                                   = Field('summary.load_factor', is_mutable=False)
    total_time                                    = Field('summary.total_time', is_mutable=False)
    run_stats                                     = ListField('summary.run_stats', is_mutable=False)
    last_error                                    = ListField('summary.last_error', is_mutable=False)
    mod_time                                      = Field('summary.mod_time', is_mutable=False)
    access_time                                   = Field('summary.access_time', is_mutable=False)
    access_count                                  = Field('summary.access_count', is_mutable=False)
    size                                          = Field('summary.size', is_mutable=False)
    timespan                                      = Field('summary.timespan', is_mutable=False)
    is_inprogress                                 = BoolField('summary.is_inprogress', is_mutable=False)
    is_suspended                                  = BoolField('summary.is_suspended', is_mutable=False)
    suspend_expiration                            = EpochField('summary.suspend_expiration', is_mutable=False)
    verification_buckets_failed                   = Field('verification_buckets_failed', is_mutable=False)
    verification_buckets_skipped                  = Field('verification_buckets_skipped', is_mutable=False)
    verification_buckets_passed                   = Field('verification_buckets_passed', is_mutable=False)
    verification_state                            = Field('verification_state', is_mutable=False)
    verification_time                             = Field('verification_time', is_mutable=False)
    verification_error                             = Field('verification_error', is_mutable=False)
    verification_progress                         = Field('verification_progress', is_mutable=False)
