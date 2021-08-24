define([
            'jquery',
            'underscore',
            'module',
            'models/shared/Application',
            'models/shared/User',
            'models/search/Job',
            'models/services/datamodel/DataModel',
            'models/pivot/PivotReport',
            'models/pivot/PivotJob',
            'models/pivot/datatable/PivotableDataTable',
            'models/services/summarization/TStatsSummarization',
            'views/extensions/DeclarativeDependencies',
            'views/Base',
            'views/pivot/DataSourceMenu',
            'views/shared/DropDownMenu',
            'views/shared/delegates/Popdown',
            'uri/route'
        ],
        function(
            $,
            _,
            module,
            Application,
            User,
            Job,
            DataModel,
            PivotReport,
            PivotJob,
            PivotableDataTable,
            TStatsSummarization,
            DeclarativeDependencies,
            Base,
            DataSourceMenu,
            DropDownMenu,
            Popdown,
            route
        ) {

    var POLLING_DELAY = 2000;

    var DocumentActionBar = Base.extend({

        moduleId: module.id,

        events: {
            'click .clear-button': function(e) {
                e.preventDefault();
                this.model.report.trigger('clear');
            },
            'click .save-button': function(e) {
                e.preventDefault();
                if (!$(e.target).hasClass('disabled')) {
                    this.model.report.trigger('save');
                }
            }
        },

        /**
         * @constructor
         * @param options {
         *     report <models/pivot/PivotReport> the current report
         *     dataModel <models/services/datamodel/DataModel> the current data model
         *     application <models/shared/Application> the current application state
         *     searchJob <models/pivot/PivotJob> the current pivot job
         * }
         */

        initialize: function() {
            Base.prototype.initialize.apply(this, arguments);

            this.children.createDropDown = new DropDownMenu({
                label: _('Save As...').t(),
                className: 'create-drop-down',
                anchorClassName: 'btn-pill',
                dropdownClassName: 'dropdown-menu-narrow',
                popdownOptions: { attachDialogTo: 'body' },
                items: [
                    { label: _('Report').t(), value: 'report' },
                    { label: _('Dashboard Panel').t(), value: 'panel' }
                ]
            });
            this.children.createDropDown.on('itemClicked', function(type) {
                if(type === 'report') {
                    this.model.report.trigger('saveAsReport');
                }
                else if(type === 'panel') {
                    this.model.report.trigger('saveAsDashboardPanel');
                }
            }, this);

            this.children.popdown = new Popdown({
                el: this.el,
                toggle: '.data-source-button',
                dialog: '.data-source-menu',
                attachDialogTo: 'body'
            });

            this.children.popdown.on('show', this.onDataSourceShow, this);
            this.children.popdown.on('shown', this.onDataSourceShown, this);
            this.children.popdown.on('hidden', this.onDataSourceHidden, this);

            this.initDataSourceMenu();
            // If the search job has not yet been created, it might not have all of the information needed for the
            // data source menu.  Set up a listener that will re-initialize the data source menu when the job has an id.
            if(this.model.searchJob.isNew()) {
                this.listenToOnce(this.model.searchJob, 'change:id', function() {
                    this.initDataSourceMenu();
                    this.children.dataSourceMenu.render().appendTo(this.$('.action-bar'));
                });
            }

            this.model.report.entry.on('change:name', this.updateReportName, this);
            this.model.report.on('change:id', function() {
                if(!this.model.report.isNew()) {
                    this.$('.save-button').show();
                }
                else {
                    this.$('.save-button').hide();
                }
            }, this);
        },

        render: function() {
            var tableIsEditable = this.computeIsEditable(),
                editDatasetHref = tableIsEditable ? this.computeEditDatasetHref() : null;

            this.$el.html(this.compiledTemplate({
                dataTableName: this.model.dataTable.get('displayName'),
                tempDataModel: this.model.dataModel.isTemporary(),
                canSave: this.model.report.canWrite(
                    this.model.user.canScheduleSearch(),
                    this.model.user.canRTSearch()
                ),
                tableIsEditable: tableIsEditable,
                editDatasetHref: editDatasetHref
            }));
            if(this.model.report.isNew()) {
                this.$('.save-button').hide();
            }
            this.updateReportName();
            this.children.createDropDown.render().replaceAll(this.$('.save-as-dropdown-placeholder'));
            this.children.dataSourceMenu.render().appendTo(this.$('.action-bar'));
            return this;
        },

        remove: function() {
            this.onDataSourceHidden();
            return Base.prototype.remove.apply(this, arguments);
        },

        // If the data table is based on a real data model, then it's editable if the data model's ACL permits it.
        // If not, it's editable if it has an ID and the dataset extensions are installed.
        computeIsEditable: function() {
            var tableHasRealDataModel = this.model.dataTable.hasParentDataModel();
            if (tableHasRealDataModel) {
                return this.model.dataModel.entry.acl.canWrite();
            }
            var canTable = this.model.user.canAccessSplunkDatasetExtensions(),
                datasetId = this.model.dataTable.get('fullyQualifiedId');

            return canTable && !!datasetId;
        },

        // If the data table is based on a real data model, link to the data model editor.
        // If not, link to the table UI.
        computeEditDatasetHref: function() {
            var root = this.model.application.get('root'),
                app = this.model.application.get('app'),
                locale = this.model.application.get('locale'),
                tableHasRealDataModel = this.model.dataTable.hasParentDataModel();

            if (tableHasRealDataModel) {
                return route.data_model_editor(root, locale, app, {
                    data: { model: this.model.dataTable.getDataModelId() }
                });
            }
            return route.table(root, locale, app, {
                data: { t: this.model.dataTable.get('fullyQualifiedId') }
            });
        },

        initDataSourceMenu: function() {
            // determine what type of acceleration (if any) the job is using,
            // and create the corresponding model to be passed down to the data source menu
            var accelerationType = this.model.searchJob.getAccelerationType();
            if(accelerationType === PivotJob.ADHOC_ACCELERATION) {
                this.model.collectJob = new Job({ id: this.model.searchJob.getCollectId() }, { delay: POLLING_DELAY });
            }
            else if(accelerationType === PivotJob.MANAGED_ACCELERATION) {
                // TODO [sff] just a hack until we have a way to pass only the data model name
                var tstatsNamespace = "tstats:DM_" + this.model.dataModel.entry.acl.get('app')
                                    + "_" + this.model.dataModel.entry.content.get("modelName"),
                    tStatsId = this.model.dataModel.id.replace("datamodel/model", "admin/summarization")
                                    .replace(this.model.dataModel.entry.content.get("modelName"), tstatsNamespace);

                this.model.tstatsSummarization = new TStatsSummarization({ id: tStatsId });
            }

            if(this.children.dataSourceMenu) {
                this.children.dataSourceMenu.remove();
            }
            this.children.dataSourceMenu = new DataSourceMenu({
                apiResources: this.apiResources.dataSourceMenu,
                model: {
                    collectJob: this.model.collectJob,
                    tstatsSummarization: this.model.tstatsSummarization,
                    user: this.model.user
                }
            });
        },

        updateReportName: function() {
            var $nameHolder = this.$('.report-name'),
                isNew = this.model.report.isNew(),
                reportName = isNew ? _('New Pivot').t() : this.model.report.entry.get('name');

            $nameHolder.empty().text(reportName);
        },

        onDataSourceShow: function() {
            if(this.model.collectJob) {
                this.model.collectJob.startPolling();
            }
            else if(this.model.tstatsSummarization) {
                this.model.tstatsSummarization.startPolling({
                    delay: POLLING_DELAY,
                    condition: function(model) {
                        var complete = model.entry.content.get('summary.complete');
                        return !complete || complete < 1;
                    }
                });
            }
        },

        onDataSourceShown: function() {
            // kind of hacky, but for 508 reach in and focus the first a tag
            this.children.dataSourceMenu.$('a').first().focus();
        },

        onDataSourceHidden: function() {
            if(this.model.collectJob) {
                this.model.collectJob.stopPolling();
            }
            else if(this.model.tstatsSummarization) {
                this.model.tstatsSummarization.stopPolling();
            }
        },

        template: '\
            <h1 class="report-name section-title"></h1>\
            <div class="action-bar pull-right">\
                <a href="#" class="save-button btn-pill <%- canSave ? "" : "disabled" %>">\
                    <%- _("Save").t() %>\
                </a>\
                <div class="report-action-buttons btn-group">\
                    <span class="save-as-dropdown-placeholder"></span>\
                    <a href="#" class="clear-button btn-pill"><%- _("Clear").t() %></a>\
                </div>\
                <% if (tableIsEditable && !tempDataModel) { %>\
                    <a href="<%- editDatasetHref %>" class="edit-dataset-button btn-pill">\
                        <%- _("Edit Dataset").t() %>\
                    </a>\
                <% } %>\
                <a href="#" class="data-source-button btn-pill">\
                    <%- tempDataModel ? _("Acceleration").t() : dataTableName %>\
                    <span class="caret"></span>\
                </a>\
            </div>\
        '

    },
    {
        apiDependencies: {
            report: PivotReport,
            dataModel: DataModel,
            dataTable: PivotableDataTable,
            searchJob: PivotJob,
            user: User,
            application: Application,

            dataSourceMenu: DataSourceMenu
        }
    });

    return DeclarativeDependencies(DocumentActionBar);

});
