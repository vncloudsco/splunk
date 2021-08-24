define([
    'jquery',
    'underscore',
    'module',
    'uri/route',
    'views/shared/Modal',
    'views/shared/controls/SyntheticCheckboxControl',
    'models/instrumentation/OptInModel',
    'models/instrumentation/EligibilityModel',
    './Master.pcss'
],
function (
    $,
    _,
    module,
    route,
    Modal,
    SyntheticCheckboxControl,
    OptInModel,
    EligibilityModel,
    css
) {
    return Modal.extend({
        moduleId: module.id,
        className: Modal.CLASS_NAME + " opt-in-dialog",
        initialize: function() {
            Modal.prototype.initialize.apply(this, arguments);
            this.forceHide = false;
            this.deferreds = {};
            this.deferreds.optIn = $.Deferred();
            this.deferreds.eligibility = $.Deferred();

            this._loadModels();
        },
        events: $.extend({}, Modal.prototype.events, {
            'click .modal-btn-primary': function(e) {
                e.preventDefault();
                this.submitSelection(true);
            },
            'click .modal-btn-cancel': function(e) {
                e.preventDefault();
                this.submitSelection(false);
            },
            'click .close': function(e) {
                e.preventDefault();
                this.submitSelection(false);
            }
        }),
        constants: {
            anonymous: {
                send: 'sendAnonymizedUsage',
                checked: 'precheckSendAnonymizedUsage'
            },
            support: {
                send: 'sendSupportUsage',
                checked: 'precheckSendSupportUsage'
            },
            license: {
                send: 'sendLicenseUsage'
            },
            webAnalytics: {
                send: 'sendAnonymizedWebAnalytics'
            },
            showModal: 'showOptInModal',
            optInVersion: 'optInVersion'
        },
        hide: function(forceHide) {
            this.forceHide = forceHide;
            Modal.prototype.hide.call(this);
        },
        _getDefaultValue: function(attr) {
            var value = 0;
            if (this.model.optIn && this.model.optIn.attributes && this.model.optIn.attributes.entry && this.model.optIn.attributes.entry[0] && this.model.optIn.attributes.entry[0].content){
                value = this.model.optIn.attributes.entry[0].content[attr];
            }
            return value;
        },
        _loadModels: function() {
            this.model.optIn = new OptInModel();

            this.model.eligibility = new EligibilityModel({
                application: this.model.application
            });

            this.model.optIn.fetch({
                data: { output_mode: 'json' },
                success: function() {
                    this.deferreds.optIn.resolve();
                }.bind(this),
                error: function() {
                    this.deferreds.optIn.reject();
                }.bind(this)
            });
            this.model.eligibility.fetch({
                success: function() {
                    this.deferreds.eligibility.resolve();
                }.bind(this),
                error: function() {
                    this.deferreds.eligibility.reject();
                }.bind(this)
            });
        },
        checkIfModalIsShown: function(){
            if (this.forceHide) {
                return false;
            }

            // Check eligibility first (verifies server roles & user capability)
            if (!(this.model.eligibility && this.model.eligibility.isEligible())) {
                return false;
            }

            // Check if this host has already confirmed this version
            if (!this.model.optIn.isAcknowledgementRequired()) {
                return false;
            }

            // Check if this user has already dismissed the modal
            if (!this.model.userPref.showInstrumentationOptInModal(
                  this.model.optIn.currentVersion())) {
                return false;
            }

            return true;
        },
        dontShowModalForUser: function() {
            var currentVersion = this.model.optIn.currentVersion();
            if (this.model.userPref.showInstrumentationOptInModal(currentVersion)) {
                this.model.userPref.entry.content.set("hideInstrumentationOptInModal", 1);
                this.model.userPref.entry.content.set("dismissedInstrumentationOptInVersion",
                                                      currentVersion);
                this.model.userPref.save();
            }
        },
        submitSelection: function(confirm) {
            var optInModel = this.model.optIn,
                currentVersion = optInModel.currentVersion(),
                supportChoice = true;

            var data = this.constants.anonymous.send + "=" + supportChoice +
                "&" + this.constants.support.send + "=" + supportChoice +
                "&" + this.constants.license.send + "=" + supportChoice +
                    // The anonymous data toggle in the opt-in modal controls the
                    // UI analytics setting as well as the normal anonymous data.
                "&" + this.constants.webAnalytics.send + "=" + supportChoice;
            
            if (confirm && optInModel) {
                // Note: showOptInModal is deprecated in favor of optInVersionAcknowledged.
                //       However, we continue to set the legacy flag in case of a
                //       heterogenous deployment with respect to splunk versions.
                data += "&showOptInModal=0" + "&optInVersionAcknowledged=" + currentVersion;
            }
            
            if (optInModel) {
                this.model.optIn.save({},{
                    contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
                    data: data
                });
            }
            // Never show modal if user closes it or presses ok.
            this.dontShowModalForUser();
            this.hide();
        },
        createDocLink: function(page) {
            return route.docHelp(this.model.application.get("root"), this.model.application.get("locale"), page);
        },
        onModalHide: function() {
            // If modal is not allowed to shown, run function if it were to be hidden.
            if (this.options.onHide) {
                this.options.onHide();
            }
        },
        render: function() {
            this.$el.html(Modal.TEMPLATE);
            this.$(Modal.HEADER_TITLE_SELECTOR).html(_("Helping You Get More Value from Splunk Software").t());
            this.$(Modal.BUTTON_CLOSE_SELECTOR).remove();
            this.$(Modal.BODY_SELECTOR).show();
            this.$(Modal.BODY_SELECTOR).append(Modal.FORM_HORIZONTAL);

            var settingsPageUrl = route.instrumentation(this.model.application.get("root"),
                    this.model.application.get("locale"));

            this.$(Modal.BODY_FORM_SELECTOR).html(_(this.dialogFormBodyTemplate).template({
                model: this.model,
                instrumentationLink: this.createDocLink('learnmore.instrumentation.performance'),
                settingsPageUrl: settingsPageUrl
            }));
            var buttonOkay = Modal.BUTTON_SAVE;

            this.$(Modal.FOOTER_SELECTOR).append(buttonOkay);

            this.$('.btn.modal-btn-primary').text(_('Got it!').t());

            $.when(this.deferreds.optIn, this.deferreds.eligibility).done(function() {
                var hasAcknowledgedAnyVersion = this.model.optIn.hasAcknowledgedAnyVersion();
                if (hasAcknowledgedAnyVersion) {
                    this.$(".usage-details.install").remove();
                } else {
                    this.$(".usage-details.upgrade").remove();
                }
                // Wait till eligibility modal is loaded and check if modal is shown.
                if (this.checkIfModalIsShown()){
                    this.show();
                    if (this.options.onHide) {
                        // Run passed in function when modal is hidden.
                        this.on('hide', this.options.onHide, this);
                    }
                }
                else {
                    this.onModalHide();
                }
            }.bind(this)).fail(function() {
                this.onModalHide();
            }.bind(this));

            return this;
        },
        dialogFormBodyTemplate: '\
            <div class="instrumentation-opt-in-modal-body">\
                <div class="message-container">\
                    <div class="usage-details upgrade">\
                        <p>\
                            <%= _("Splunk\'s data collection practices have changed. ").t() %>\
                            <b><%= _("Sharing of product usage data from this deployment is now set to \
                            ON.").t() %> </b>\
                            <%= _(" You can change your data collection preferences at any time in your ").t() %>\
                            <a class="learn-more-link" href="<%= settingsPageUrl %>" target="_blank">\
                                <%= _("Instrumentation Settings.").t() %>\
                            </a>\
                        </p>\
                    </div>\
                    <div class="update-details">\
                        <p><%= _("Splunk Inc. collects aggregated product usage data so that we can \
                        enhance the value of your investment in Splunk software. This product usage \
                        data does not include any data you ingest into your deployment. \
                        Examples of what we collect:").t() %>\
                            <ul>\
                                <li><%= _("Feature usage").t() %></li>\
                                <li><%= _("Deployment topology").t() %></li>\
                                <li><%= _("Infrastructure and operating environment").t() %></li>\
                                <li><%= _("Performance").t() %></li>\
                            </ul>\
                        </p>\
                        <p><%= _("We use this data to optimize your deployment, prioritize our features, improve \
                        your experience, notify you of patches, and develop high quality product functionality.").t() %>\
                        </p>\
                    </div>\
                    <div class="usage-details install">\
                        <p>\
                            <b><%= _("Sharing of product usage data from this deployment is now set to \
                            ON.").t() %> </b>\
                            <%= _(" You can change your data collection preferences at any time in your ").t() %>\
                            <a class="learn-more-link" href="<%= settingsPageUrl %>" target="_blank">\
                                <%= _("Instrumentation Settings.").t() %>\
                            </a>\
                        </p>\
                    </div>\
                    <div class="privacy-details">\
                        <a class="learn-more-link external" href="<% instrumentationLink %>" target="_blank">\
                            <%= _("Learn more").t() %>\
                        </a>\
                        <%= _(" about what we collect, how we securely transmit data, and how we store the data.\
                            For details on Splunk\'s data practices, see the ").t() %>\
                        <a class="learn-more-link external" href="http://www.splunk.com/r/privacy" target="_blank">\
                            <%= _("Splunk Privacy Policy").t() %>\
                        </a>\
                        .\
                    </div>\
                    <p>\
                        <%= _("We are dedicated to helping you get the most out of your investment. \
                        Thank you for helping us make Splunk\'s products even better.").t() %> \
                    </p>\
                </div>\
            </div>\
        '
    });
});
