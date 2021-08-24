'''
Represents models for indexs
'''

from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field, BoolField, EpochField, IntField, ListField, FloatField, FloatByteField, IntByteField, DictField


class Index(SplunkAppObjModel):
    '''
    Represents an Splunk index
    '''

    resource                  = 'data/indexes'

    assureUTF8                = BoolField()
    blockSignatureDatabase    = Field()
    blockSignSize             = IntField()
    bucketRebuildMemoryHint   = Field()
    coldPath                  = Field()
    coldPath_expanded         = Field()
    coldToFrozenDir           = Field()
    coldToFrozenScript        = Field()
    compressRawdata           = BoolField()
    currentDBSizeMB           = IntField()
    defaultDatabase           = Field()
    disabled                  = BoolField()

    enableOnlineBucketRepair  = BoolField()
    enableRealtimeSearch      = BoolField()
    frozenTimePeriodInSecs    = IntField()
    homePath                  = Field()
    homePath_expanded         = Field()
    indexThreads              = Field()
    isInternal                = BoolField()
    isReady                   = BoolField()
    isVirtual                 = BoolField()
    lastInitSequenceNumber	  = IntField()
    lastInitTime              = EpochField()
    maxBloomBackfillBucketAge = Field()
    maxBucketSizeCacheEntries = IntField()
    maxConcurrentOptimizes    = IntField()
    maxDataSize	              = Field()
    maxHotBuckets	          = IntField()
    maxHotIdleSecs            = IntField()
    maxHotSpanSecs            = IntField()
    maxMemMB                  = IntField()
    maxMetaEntries            = IntField()
    maxRunningProcessGroups   = IntField()
    maxRunningProcessGroupsLowPriority = IntField()
    maxTime	                  = Field()
    maxTimeUnreplicatedNoAcks = IntField()
    maxTimeUnreplicatedWithAcks = IntField()
    maxTotalDataSizeMB        = IntField()
    maxWarmDBCount            = IntField()
    memPoolMB                 = Field()
    minRawFileSyncSecs        = Field()
    minStreamGroupQueueSize   = IntField()
    minTime                   = Field()
    partialServiceMetaPeriod  = IntField()
    processTrackerServiceInterval = IntField()
    quarantineFutureSecs      = IntField()
    quarantinePastSecs        = IntField()
    rawChunkSizeBytes         = IntByteField()
    repFactor	              = IntField()
    rotatePeriodInSecs        = IntField()
    serviceMetaPeriod         = IntField()
    serviceOnlyAsNeeded       = BoolField()
    serviceSubtaskTimingPeriod = IntField()
    suppressBannerList        = BoolField()
    sync                      = BoolField()
    syncMeta                  = BoolField()
    thawedPath                = Field()
    thawedPath_expanded       = Field()
    throttleCheckPeriod       = IntField()
    totalEventCount           = IntField()
