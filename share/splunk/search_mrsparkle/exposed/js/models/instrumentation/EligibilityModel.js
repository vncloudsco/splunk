/**
 * Checks Eligibility of opt in.
 */
define(
    [
        'underscore',
        'models/Base',
        'splunk.util'
    ],
    function(_, BaseModel, SplunkUtil) {
        return BaseModel.extend({
            url: function() {
                /** The optInVersion passed into this endpoint is the optin pop-up's version.
                 *  This version is checked against the optInVersion in telemetry.conf to enable eligibility. 
                 */
                return SplunkUtil.make_url('/splunkd/__raw/servicesNS/nobody/splunk_instrumentation/instrumentation_controller/' +
                                           'instrumentation_eligibility?optInVersion=4');
            },
            initialize: function(options) {
                BaseModel.prototype.initialize.apply(this, arguments);

                this.root = '';
                if (options && options.application) {
                    var root = options.application.get('root');
                    if (root) {
                        this.root = '/' + root;
                    }
                }
            },
            isEligible: function() {
                return this.get('is_eligible');
            }
        });
    }
);
