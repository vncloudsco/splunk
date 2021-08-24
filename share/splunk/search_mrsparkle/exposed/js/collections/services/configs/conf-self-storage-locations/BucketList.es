/*
 * @author jsolis
 * @date 6/14/17
 */

import BucketList from 'models/services/configs/conf-self-storage-locations/BucketList';
import SplunkDsBaseCollection from 'collections/SplunkDsBase';

export default SplunkDsBaseCollection.extend({
    model: BucketList,
    url: 'configs/conf-self-storage-locations',
});

