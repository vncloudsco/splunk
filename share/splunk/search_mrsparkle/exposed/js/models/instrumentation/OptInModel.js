/**
 * Model of Opt In Modal
 */
define(
    [
        'underscore',
        'models/Base',
        'util/splunkd_utils',
        'splunk.util'
    ],
    function(_, BaseModel, splunkd_utils, splunkUtil) {
        return BaseModel.extend({
            initialize: function() {
                BaseModel.prototype.initialize.apply(this, arguments);
            },
            isAcknowledgementRequired: function () {
                var currentVersion = this.currentVersion();
                var acknowledgedVersion = this.acknowledgedVersion();

                if (currentVersion === null) {
                    // Something is going wrong if this is happening.
                    // Most likely, the conf file entry for our opt-in version
                    // was removed by hand. Rather than throw an error, just
                    // say no opt in required and move on. They can always opt
                    // in via the instrumentation page.
                    return false;
                } else if (acknowledgedVersion === null) {
                    return true;
                }
                
                return currentVersion > acknowledgedVersion;
            },
            hasAcknowledgedAnyVersion: function () {
                var acknowledgedVersion = this.acknowledgedVersion();
                return acknowledgedVersion && acknowledgedVersion > 0;
            },
            currentVersion: function () {
                var optInVersion = this.attributes.entry[0].content.optInVersion;
                if (optInVersion === undefined || optInVersion === null) {
                    // optInVersion was added at v2. If version is not present, must be v1.
                    optInVersion = 1;
                } else if (typeof optInVersion != 'number') {
                    optInVersion = null;
                }
                return optInVersion;
            },
            acknowledgedVersion: function () {
                var optInVersionAcknowledged = this.attributes.entry[0].content.optInVersionAcknowledged;

                // At v1, we noted any acknowledgement with a simple boolean flag.
                var acknowledgedVersionOne = !this.attributes.entry[0].content.showOptInModal;

                if (typeof optInVersionAcknowledged != 'number') {
                    if (acknowledgedVersionOne) {
                        optInVersionAcknowledged = 1;
                    } else {
                        optInVersionAcknowledged = null;
                    }
                }
                return optInVersionAcknowledged;
            },
            url: function() {
                return splunkd_utils.fullpath('admin/telemetry/general', {
                    app: 'splunk_instrumentation',
                    owner: 'nobody'
                });
            }
        });
    }
);
