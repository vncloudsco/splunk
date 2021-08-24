define(
    [
        'jquery',
        'underscore',
        'module',
        'views/shared/Modal',
        'views/shared/controls/SyntheticCheckboxControl',
        'splunk.util',
        './DatasetsAddonInstallDialog.pcss'
    ],
    function(
        $,
        _,
        module,
        BaseModal,
        SyntheticCheckboxControl,
        splunkUtils,
        css
    ) {
        return BaseModal.extend({
            moduleId: module.id,
            className: BaseModal.CLASS_NAME + ' ' + BaseModal.CLASS_MODAL_WIDE + ' dataset-addon-prompt',

            initialize: function(options) {
                BaseModal.prototype.initialize.apply(this, arguments);

                this.children.dontShowAgainControl = new SyntheticCheckboxControl({
                    label: _('Do not show this again').t(),
                    additionalClassNames: 'dont-show-again-control',
                    model: this.model.userPref.entry.content,
                    modelAttribute: 'datasets:showInstallDialog',
                    invertValue: true
                });

                this.on('hidden', function() {
                    if (!splunkUtils.normalizeBoolean(this.model.userPref.entry.content.get('datasets:showInstallDialog'))) {
                        this.model.userPref.save();
                    }
                }.bind(this));
            },

            render: function() {
                var addonAppUrl = this.model.datasetsAddonRemote.get('path');

                this.$el.html(BaseModal.TEMPLATE);

                this.$(BaseModal.HEADER_TITLE_SELECTOR).html(_('Datasets').t());
                $(_.template(this.template, {
                    _: _
                })).appendTo(this.$(BaseModal.BODY_SELECTOR));

                this.children.dontShowAgainControl.render().appendTo(this.$(BaseModal.FOOTER_SELECTOR));
                this.$(BaseModal.FOOTER_SELECTOR).append(BaseModal.BUTTON_CLOSE);
                this.$(BaseModal.FOOTER_SELECTOR).append('<a href="' + addonAppUrl + '" class="btn btn-primary modal-btn-primary" target="_blank">' + _('Get the Datasets Add-on').t() + '</a>');

                return this;
            },

            template: '\
                <div class="left-pane">\
                    <h4><%= _("Datasets Listing Page").t() %></h4>\
                    <div class="left-pane-intro">\
                        <%= _("The Datasets listing page displays all prepared dataset types that are accessible to you for viewing, analysis, sharing, and reporting.").t() %>\
                        <%= _("The dataset types include lookups, data models, and table datasets (tables).").t() %>\
                    </div>\
                    <div class="left-pane-image"></div>\
                    <ul>\
                        <li>\
                            <%= _("Use the <span class=\\\"bold\\\">Explorer view</span> to inspect the contents of existing data models and lookups, analyze field values, create scheduled reports based on datasets, and more.").t() %>\
                        </li>\
                        <li>\
                            <%= _("Open any dataset in <span class=\\\"bold\\\">Pivot</span>, where it becomes the foundation for visualization-rich reports and dashboard panels.").t() %>\
                        </li>\
                        <li>\
                            <%= _("Investigate datasets in <span class=\\\"bold\\\">Search</span>, add modifications, and save your changes.").t() %>\
                        </li>\
                    </ul>\
                </div>\
                <div class="right-pane">\
                    <h4><%= _("Datasets Add-on").t() %></h4>\
                    <div class="right-pane-intro">\
                        <%= _("Tables provide a structured view of data in a common table format. The Table Editor makes it simple to rapidly build, edit, and analyze tables without using SPL.").t() %>\
                        <%= _("The Table Editor is seamlessly integrated into Splunk Enterprise when you install the Splunk Datasets Add-on.").t() %>\
                    </div>\
                    <div class="right-pane-image"></div>\
                    <ul>\
                        <li>\
                            <%= _("Build sophisticated tables with ease by converting source data and search results into the <span class=\\\"bold\\\">tables</span> dataset type.").t() %>\
                        </li>\
                        <li>\
                            <%= _("Design your tables with the <span class=\\\"bold\\\">Table Editor</span>, which lets you filter events, add fields, edit field values, and more.").t() %>\
                        </li>\
                        <li>\
                            <%= _("Analyze your field values with the <span class=\\\"bold\\\">Summarize Fields</span> view.").t() %>\
                        </li>\
                        <li>\
                            <%= _("Accelerate tables to improve the performance of reports and dashboards that use them.").t() %>\
                        </li>\
                    </ul>\
                </div>\
            '
        });
    });
