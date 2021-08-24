import SplunkdUtils from 'util/splunkd_utils';
import ModSetupScript from 'models/modsetup/ModSetupScript';
import SplunkDsBaseCollections from 'collections/SplunkDsBase';

export default SplunkDsBaseCollections.extend({

    model: ModSetupScript,
    url() {
        return SplunkdUtils.fullpath(this.scriptUrl, {
            app: this.bundleId,
            owner: 'nobody',
        });
    },
});