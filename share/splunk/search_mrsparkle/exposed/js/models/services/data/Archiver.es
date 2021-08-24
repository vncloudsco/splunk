/*
 * @author jsolis
 * @date 6/13/17
 */
import SplunkDBaseModel from 'models/SplunkDBase';
import { validationObj } from 'models/indexes/cloud/CloudIndexValidation';

export default SplunkDBaseModel.extend({
    url: 'data/archiver',
    urlRoot: 'data/archiver',
    defaults: {
        name: '',
        maxIndexSize: '',
        maxIndexSizeFormat: 'GB',
        frozenTimePeriodInDays: '',
        'archive.enabled': false,
        'archive.provider': '',
        datatype: 'event',
    },
    validation: validationObj,
});
