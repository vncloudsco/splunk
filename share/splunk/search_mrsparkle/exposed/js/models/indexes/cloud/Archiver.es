/**
 * @author jsolis
 * @date 7/17/17
 * Cloud-specific endpoint that is only available if the Cloud Archives app has been installed
 */

import SplunkDBaseModel from 'models/SplunkDBase';
import { validationObj } from 'models/indexes/cloud/CloudIndexValidation';
import _ from 'underscore';

const COLD_STORAGE_PROVIDER = 'Glacier';

export default SplunkDBaseModel.extend({
    url: 'cluster_blaster_indexes/sh_indexes_manager',
    urlRoot: 'cluster_blaster_indexes/sh_indexes_manager',
    defaults: {
        name: '',
        datatype: 'event',
        maxIndexSizeFormat: 'GB',
        'archiver.coldStorageRetentionPeriod': '',
    },
    getColdStorageProvider: () => COLD_STORAGE_PROVIDER,
    validation: {
        ...validationObj,
        'archiver.coldStorageRetentionPeriod': [{
            fn(value, attr, computedState) {
                if (computedState['archiver.coldStorageProvider'] === COLD_STORAGE_PROVIDER && !value) {
                    return _('Archive Retention Period is required.').t();
                }
                return '';
            },
        }],
    },
});