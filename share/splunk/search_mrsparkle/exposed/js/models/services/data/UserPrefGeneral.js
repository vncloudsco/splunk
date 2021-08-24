define(
    [
        'underscore',
        'models/StaticIdSplunkDBase',
        'splunk.util'
    ],
    function(_, SplunkDBaseModel, splunkUtil) {
        var TWO_WEEKS_IN_MS = 1209600000;

        return SplunkDBaseModel.extend({
            url: 'data/user-prefs',
            initialize: function() {
                SplunkDBaseModel.prototype.initialize.apply(this, arguments);
            },
            showInstrumentationOptInModal: function(currentOptInVersion) {
                var dismissedVersion = this.entry.content.get('dismissedInstrumentationOptInVersion');
                if (dismissedVersion === undefined || dismissedVersion === null || !dismissedVersion.match(/^[0-9]+$/)) {
                    if (splunkUtil.normalizeBoolean(this.entry.content.get('hideInstrumentationOptInModal'))) {
                        dismissedVersion = 1;
                    } else {
                        dismissedVersion = 0;
                    }
                }
                return parseInt(dismissedVersion, 10) < currentOptInVersion;
            },
            /*
             * stanza: notification_python_3_impact
             * status: true, false, or snooze_[timestamp]
             * 
             * this method returns a boolean to determine whether the notificaiton modal should be shown
             */
            shouldShowNotification: function() {
                var shouldShow = splunkUtil.normalizeBoolean(this.entry.content.get('notification_python_3_impact'));
                if (!_.isBoolean(shouldShow)) {
                    shouldShow = this._getNotificationSnoozeTime() <= Date.now();
                }
                return shouldShow;
            },
            /* 
             * This method adds 2 weeks to the original snooze time and returns the correct
             * new snooze status - to be saved to the conf file
             */
            getNewSnoozeStatus: function() {
                var newSnoozeTime = this._getNotificationSnoozeTime() + TWO_WEEKS_IN_MS;
                return 'snooze_' + newSnoozeTime;
            },
            /* 
             * Private helper method:
             * returns the old snooze time
             */
            _getNotificationSnoozeTime: function() {
                var prevTime = this.entry.content.get('notification_python_3_impact') &&
                               this.entry.content.get('notification_python_3_impact').split('_')[1];
                return _.isUndefined(prevTime) ? Date.now() : parseInt(prevTime);
            }
        },
        {
            id: 'data/user-prefs/general'
        });
    }
);
