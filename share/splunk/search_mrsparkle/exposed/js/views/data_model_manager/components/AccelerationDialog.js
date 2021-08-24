/**
 * Dialog to edit the acceleration settings of a Data Model.
 *
 * Inputs:
 *
 *     model: {
 *         dataModel {models/services/datamodel/DataModel}
 *         application {models/Application}
 *         user {models/shared/User}
 *    },
 *    collection: {
 *        archives: <collections.services.data.vix.Archives>
 *        workloadManagementStatus: <collections.services.admin.workload_management>
 *        vix: <collections.services.data.vix.indexes>
 *    }
 *
 * @fires AccelerationDialog#action:saveModel
 */
define(
    [
        'jquery',
        'underscore',
        'backbone',
        'models/Base',
        'models/shared/RelativeTimeScheduleWindow',
        'models/datamodel/BackfillTimeScheduleWindow',
        'models/datamodel/MaxTimeWindow',
        'views/data_model_manager/customcontrols/BlockSizeControl',
        'views/shared/dialogs/DialogBase',
        'views/shared/controls/ControlGroup',
        'views/shared/controls/SyntheticCheckboxControl',
        'views/shared/controls/SyntheticSelectControl',
        'views/shared/controls/TextControl',
        'views/shared/controls/SpinnerControl',
        'views/shared/FlashMessages',
        'views/shared/jobcontrols/menu/WorkloadInput',
        'util/splunkd_utils',
        'uri/route',
        'module',
        'views/data_model_manager/components/AccelerationDialog.pcss'
    ],
    function(
        $,
        _,
        Backbone,
        BaseModel,
        RelativeTimeScheduleWindowModel,
        BackfillTimeScheduleWindowModel,
        MaxTimeWindowModel,
        BlockSizeControl,
        DialogBase,
        ControlGroup,
        SyntheticCheckboxControl,
        SyntheticSelectControl,
        TextControl,
        SpinnerControl,
        FlashMessagesView,
        WorkloadInput,
        splunkdUtils,
        route,
        module,
        css
        )
    {
        return DialogBase.extend({
            moduleId: module.id,
            THIRTYTWO_MB: 32*1024*1024,

            initialize: function(options) {
                DialogBase.prototype.initialize.call(this, options);

                this.model.acceleration = this.model.dataModel.entry.content.acceleration;
                var earliest_time = this.model.acceleration.get('earliest_time'),
                    backfill_time = this.model.acceleration.get('backfill_time'),
                    max_time = this.model.acceleration.get('max_time');

                this.model.relativeTimeScheduleWindowModel = new RelativeTimeScheduleWindowModel();
                this.model.backfillTimeScheduleWindowModel = new BackfillTimeScheduleWindowModel();
                this.model.maxTimeWindowModel = new MaxTimeWindowModel();

                if (earliest_time) {
                    this.model.relativeTimeScheduleWindowModel.setScheduleWindow(earliest_time);
                }

                if (!_.isUndefined(backfill_time)) {
                    this.model.backfillTimeScheduleWindowModel.setScheduleWindow(backfill_time);
                }

                if (!_.isUndefined(max_time)) {
                    this.model.maxTimeWindowModel.setScheduleWindow(max_time);
                }

                this.bodyClassName = "form form-horizontal modal-body-scrolling";

                this.children.flashMessages = new FlashMessagesView({
                    model: {
                        dataModel: this.model.dataModel,
                        maxTimeWindowModel: this.model.maxTimeWindowModel
                    }
                });

                this.blockSizeErrorMessageID = _.uniqueId('dfs-blocksize-error-');

                this.children.nameLabel = new ControlGroup({
                    controlType: 'Label',
                    controlOptions: {
                        defaultValue: this.model.dataModel.entry.content.get("displayName")
                    },
                    label: _("Data Model").t()
                });

                this.enabledCheckBox = new SyntheticCheckboxControl({
                    modelAttribute: 'enabled',
                    model: this.model.acceleration,
                    updateModel:false
                });

                this.children.enabledGroup = new ControlGroup({
                    label: _("Accelerate").t(),
                    controls: [this.enabledCheckBox],
                    help:_("Acceleration may increase storage and processing costs.").t()
                });
                this.enabledCheckBox.on("change", this.acceleratedChangeHandler, this);

                /**** Summary Window/Earliest Time controls ****/

                var timeRangeHelpLink = route.docHelp(
                    this.model.application.get('root'),
                    this.model.application.get('locale'),
                    'learnmore.manager.relativetime'
                );

                this.children.earliestTimeGroup = new ControlGroup({
                    controlType: 'SyntheticSelect',
                    label: _("Summary Range").t(),
                    controlOptions: {
                        modelAttribute: 'schedule_window_option',
                        model: this.model.relativeTimeScheduleWindowModel,
                        additionalClassNames: 'earliest-time-selector',
                        toggleClassName: 'btn',
                        menuWidth: 'narrow',
                        items: this.model.relativeTimeScheduleWindowModel.getItems(),
                        popdownOptions: {
                            attachDialogTo: '.modal:visible',
                            scrollContainer: '.modal:visible .modal-body:visible'
                        }
                    },
                    tooltip: _("Sets the range of time (relative to now) for which data is accelerated. " +
                               "Example: 1 Month accelerates the last 30 days of data in your pivots.").t()
                });

                if (!_.isEmpty(this.collection) && !_.isEmpty(this.collection.workloadManagementStatus) && !_.isEmpty(this.model.user)) {
                    this.children.workloadInput = new WorkloadInput({
                        workloadPoolAttribute: 'workload_pool',
                        isRunning: true,
                        includeEmptyOption: true,
                        model: {
                            inmem: this.model.dataModel,
                            user: this.model.user,
                            workloadPool: this.model.dataModel.entry.content.acceleration
                        },
                        collection: {
                            workloadManagementStatus: this.collection.workloadManagementStatus
                        }
                    });
                }

                this.children.customWindow = new ControlGroup({
                    controlType: 'Text',
                    label: _("Earliest Time").t(),
                    controlOptions: {
                        additionalClassNames: 'custom-time-window custom-earliest-time',
                        modelAttribute: 'custom_window',
                        model: this.model.relativeTimeScheduleWindowModel
                    },
                    tooltip: _('Express the custom summary range with a relative time modifier or a fixed date in Unix epoch time format.').t(),
                    help: '<span>' + _('Examples: -1d, -3m, 246925704.000, 905293704').t()  +
                            '</span> <a class="learn-more-link" href="' + _.escape(timeRangeHelpLink) + '" target="_blank">' + _('Learn More').t() + ' <i class="icon-external"></i></a>'
                });

                this.listenTo(this.model.relativeTimeScheduleWindowModel, 'change:schedule_window_option', this.toggleCustomWindow);

                /**** Backfill Time controls ****/

                this.children.backfillTimeGroup = new ControlGroup({
                    controlType: 'SyntheticSelect',
                    label: _("Backfill Range").t(),
                    controlOptions: {
                        modelAttribute: 'schedule_window_option',
                        model: this.model.backfillTimeScheduleWindowModel,
                        additionalClassNames: 'backfill-time-selector',
                        toggleClassName: 'btn',
                        menuWidth: 'narrow',
                        items: this.model.backfillTimeScheduleWindowModel.getItems(),
                        popdownOptions: {
                            attachDialogTo: '.modal:visible',
                            scrollContainer: '.modal:visible .modal-body:visible'
                        }
                    },
                    tooltip: _("Builds the summary in increments when building the summary all at once would tax your system. " +
                               "Example: Set a Backfill Range of 1 Week to build a summary with a Summary Range of 1 Year in weekly increments.").t()
                });

                this.children.customBackfillWindow = new ControlGroup({
                    controlType: 'Text',
                    label: _("Custom Backfill Range").t(),
                    controlOptions: {
                        additionalClassNames: 'custom-time-window custom-backfill-time',
                        modelAttribute: 'custom_window',
                        model: this.model.backfillTimeScheduleWindowModel
                    },
                    tooltip: _('Express the custom Backfill Range with a relative time modifier or a fixed date in Unix epoch time format.').t(),
                    help: '<span>' + _('Examples: -1d, -3m, 246925704.000, 905293704').t()  +
                            '</span> <a class="learn-more-link" href="' + _.escape(timeRangeHelpLink) + '" target="_blank">' + _('Learn More').t() + ' <i class="icon-external"></i></a>'
                });

                this.listenTo(this.model.backfillTimeScheduleWindowModel, 'change:schedule_window_option', this.toggleCustomBackfillWindow);

                /**** Max Time controls ****/

                this.children.maxTimeGroup = new ControlGroup({
                    controlType: 'SyntheticSelect',
                    label: _("Max Summarization Search Time").t(),
                    controlOptions: {
                        modelAttribute: 'schedule_window_option',
                        model: this.model.maxTimeWindowModel,
                        additionalClassNames: 'max-time-selector',
                        toggleClassName: 'btn',
                        menuWidth: 'narrow',
                        items: this.model.maxTimeWindowModel.getItems(),
                        popdownOptions: {
                            attachDialogTo: '.modal:visible',
                            scrollContainer: '.modal:visible .modal-body:visible'
                        }
                    },
                    tooltip: _("Specifies the maximum amount of time that a summary-creating search can run. " +
                               "1 hour ensures proper summary creation for most data models.").t()
                });

                this.children.customMaxTimeWindow = new ControlGroup({
                    controlType: 'Text',
                    label: _("Custom Max Time").t(),
                    controlOptions: {
                        additionalClassNames: 'custom-seconds-window custom-max-time',
                        modelAttribute: 'custom_window',
                        model: this.model.maxTimeWindowModel,
                        validate: false
                    },
                    tooltip: _('Express the custom Max Time in seconds.').t(),
                    help: '<span>' + _('Examples: 600, 1200, 3600').t()  +
                            '</span> <a class="learn-more-link" href="' + _.escape(timeRangeHelpLink) + '" target="_blank">' + _('Learn More').t() + ' <i class="icon-external"></i></a>'
                });

                this.listenTo(this.model.maxTimeWindowModel, 'change:schedule_window_option', this.toggleCustomMaxTimeWindow);

                /**** Max Concurrent Searches ****/

                this.maxConcurrentSpinner = new SpinnerControl({
                    additionalClassNames: 'max-concurrent',
                    modelAttribute: 'max_concurrent',
                    model: this.model.acceleration,
                    menuWidth: 'narrow',
                    integerOnly: true,
                    min: 1,
                    max: 9,
                    updateModel: false
                });

                this.children.maxConcurrentSearches = new ControlGroup({
                    label: _("Maximum Concurrent Summarization Searches").t(),
                    controls: [this.maxConcurrentSpinner],
                    tooltip: _("Sets the maximum number of searches that can run concurrently to generate the summary. " +
                               "Raise this value only if you have the capability to run more concurrent searches.").t()
                });


                /**** Max Time Bucket Polling ****/

                this.pollBucketsCheckBox = new SyntheticCheckboxControl({
                    modelAttribute: 'poll_buckets_until_maxtime',
                    model: this.model.acceleration,
                    updateModel:false
                });

                this.children.pollBucketsEnable = new ControlGroup({
                    label: _("Poll Buckets For Data To Summarize").t(),
                    controls: [this.pollBucketsCheckBox],
                    tooltip: _("Causes the system to search buckets repeatedly until Maximum Summarization Search Time for late-arriving data to summarize. " +
                               "If you have a distributed environment and can run more concurrent searches, " +
                               "enable this for data models that are affected by summarization delays.").t()
                });


                /**** Summarization Period ****/

                this.summarizationPeriodText = new TextControl({
                    additionalClassNames: 'custom-time-window custom-summarization-period',
                    modelAttribute: 'cron_schedule',
                    model: this.model.acceleration,
                    updateModel: false
                });

                this.children.summarizationPeriod = new ControlGroup({
                    label: _("Summarization Period").t(),
                    controls: [this.summarizationPeriodText],
                    tooltip: _('Express the Summarization Period in cron format.').t(),
                    help: '<span>' + _('Examples: */5 * * * *, */30 * * * *').t()  +
                            '</span> <a class="learn-more-link" href="' + _.escape(timeRangeHelpLink) + '" target="_blank">' + _('Learn More').t() + ' <i class="icon-external"></i></a>'
                });

                /**** Manual/Automatic Rebuilds ****/

                this.automaticRebuildsCheckBox = new SyntheticCheckboxControl({
                    modelAttribute: 'manual_rebuilds',
                    model: this.model.acceleration,
                    invertValue: true,
                    updateModel:false
                });

                this.children.automaticRebuildsEnable = new ControlGroup({
                    label: _("Automatic Rebuilds").t(),
                    controls: [this.automaticRebuildsCheckBox],
                    tooltip: _("Enables automatic rebuilds of the data model summary when changes are made to its summarization search. " +
                               "When this setting is disabled for a data model, " +
                               "admins must click Rebuild to rebuild its summary.").t()
                });


                /*** Hunk stuff ***/

                this.isHunk = this.hasVix() || this.hasArchive();

                if (this.isHunk) {
                    // Hunk DMA options
                    this.enableHunkOptionsModel = new BaseModel({
                        'enabled': (this.model.dataModel.entry.content.acceleration.get('hunk.compression_codec') ||
                                    this.model.dataModel.entry.content.acceleration.get('hunk.dfs_block_size') ||
                                    this.model.dataModel.entry.content.acceleration.get('hunk.file_format'))
                    });
                    var enableHunkOptions = new SyntheticCheckboxControl({
                        modelAttribute: 'enabled',
                        model: this.enableHunkOptionsModel
                    });
                    this.listenTo(this.enableHunkOptionsModel, 'change:enabled', this.enableHunkOptionsVisibility);
                    this.children.enableHunkOptionsGroup = new ControlGroup({
                        label: _('Enable Hunk Specific Options').t(),
                        controls: [enableHunkOptions],
                        help: _('Only enable if the Hunk defaults are not what you need.').t()
                    });

                    // File Format
                    var fileFormatItems = [
                        {value: 'orc', label: _('orc').t()},  // Keep orc first, because it is default value.
                        {value: 'parquet', label: _('parquet').t()}
                    ];
                    this.currentFileFormat = this.model.dataModel.entry.content.acceleration.get('hunk.file_format') || 'orc';
                    this.fileFormatModel = new BaseModel({
                        'format': this.currentFileFormat
                    });
                    this.fileFormat = new SyntheticSelectControl({
                        modelAttribute: 'format',
                        model: this.fileFormatModel,
                        items: fileFormatItems,
                        toggleClassName: 'btn',
                        menuWidth: 'narrow',
                        popdownOptions: {
                            attachDialogTo: '.modal:visible',
                            scrollContainer: '.modal:visible .modal-body:visible'
                        }
                    });
                    this.children.fileFormatGroup = new ControlGroup({
                        label: _('File Format').t(),
                        controls: [this.fileFormat],
                        tooltip: _('Sets the file format used for Hunk datamodel acceleration.').t()
                    });
                    this.listenTo(this.fileFormatModel, 'change format', this.updateCompression);

                    // Compression type
                    this.orcCompressionItems = [
                        {value: 'snappy', label: _('snappy').t()},
                        {value: 'zlib', label: _('zlib').t()}
                    ];
                    this.parquetCompressionItems = [
                            {value: 'snappy', label: _('snappy').t()},
                            {value: 'gzip', label: _('gzip').t()}
                        ];
                    var compressionItems = this.orcCompressionItems;
                    if (this.model.dataModel.entry.content.acceleration.get('hunk.file_format') === 'parquet') {
                        compressionItems = this.parquetCompressionItems;
                    }
                    this.compression = new SyntheticSelectControl({
                        modelAttribute: 'hunk.compression_codec',
                        model: this.model.dataModel.entry.content.acceleration,
                        items: compressionItems,
                        toggleClassName: 'btn',
                        menuWidth: 'narrow',
                        updateModel: false,
                        popdownOptions: {
                            attachDialogTo: '.modal:visible',
                            scrollContainer: '.modal:visible .modal-body:visible'
                        }
                    });
                    this.children.compressionGroup = new ControlGroup({
                        label: _('Compression Codec').t(),
                        controls: [this.compression],
                        tooltip: _('Sets the Compression Codec used for Hunk datamodels.').t()
                    });

                    // DFS Block Size
                    this.enableBlockSizeModel = new BaseModel({
                        'enabled': (this.model.dataModel.entry.content.acceleration.get('hunk.dfs_block_size') &&
                                    (this.model.dataModel.entry.content.acceleration.get('hunk.dfs_block_size') >= this.THIRTYTWO_MB))
                    });
                    this.enableBlockSize = new SyntheticCheckboxControl({
                        modelAttribute: 'enabled',
                        model: this.enableBlockSizeModel,
                        label: _('Enable Block Size specification.').t()
                    });
                    this.listenTo(this.enableBlockSizeModel, 'change enabled', this.enableBlockSizeVisibility);
                    this.blockSize = new BlockSizeControl({
                        model: this.model.dataModel.entry.content.acceleration,
                        modelAttribute: 'hunk.dfs_block_size',
                        updateModel: false,
                        enabled: this.enableBlockSizeModel.get('enabled')
                    });
                    this.children.blockSizeGroup = new ControlGroup({
                        label: _('DFS Block Size').t(),
                        controls: [this.enableBlockSize, this.blockSize],
                        tooltip: _('DFS block size, used for Hunk datamodels.').t()
                    });
                }

                this.settings.set("primaryButtonLabel", _("Save").t());
                this.settings.set("cancelButtonLabel", _("Cancel").t());
                this.settings.set("titleLabel", _("Edit Acceleration").t());
            },

            events: {
                'click .advanced-settings-toggle': function(e) {
                    var toggle = this.$('.advanced-settings-toggle > .toggle');

                    if (toggle.hasClass('icon-chevron-right')) {
                        toggle.removeClass('icon-chevron-right').addClass('icon-chevron-down');
                    } else {
                        toggle.removeClass('icon-chevron-down').addClass('icon-chevron-right');
                    }

                    this.$('.advanced-settings').toggle();

                    e.preventDefault();
                }
            },

            /**
             * Return true if the dataModel has a virtual index.
             */
            hasVix: function() {
                return _(this.model.dataModel.entry.content.objects.models).any(function(obj) {
                    if (obj.attributes && obj.attributes.constraints && obj.attributes.constraints.length) {
                        var search = obj.attributes.constraints[0].search || '';
                        var regex = new RegExp('.*index ?= ?([A-Za-z0-9~@#$^*()_-]*).*', 'g');
                        var index = search.replace(regex, '$1');
                        return _(this.collection.vix.models).any(function(vix) {
                            return (index === vix.entry.get('name'));
                        }, this);
                    }
                    return false;
                }, this);
            },

            /**
             * Return true if the dataModel has a virtual index.
             */
            hasArchive: function() {
                return _(this.model.dataModel.entry.content.objects.models).any(function(obj) {
                    if (obj.attributes && obj.attributes.constraints && obj.attributes.constraints.length) {
                        var search = obj.attributes.constraints[0].search || '';
                        var regex = new RegExp('.*index ?= ?([A-Za-z0-9~@#$^*()_-]*).*', 'g');
                        var index = search.replace(regex, '$1');
                        return _(this.collection.archives.models).any(function(archive) {
                            return (index === archive.entry.get('name'));
                        }, this);
                    }
                    return false;
                }, this);
            },

            /**
             * When the enabled checkbox value is changed, toggle the visibility of the Summary Range control
             */
            acceleratedChangeHandler: function(model, value, options) {
                this.updateView();
            },

            updateView: function() {
                if (this.enabledCheckBox.getValue()) {
                    this.children.earliestTimeGroup.$el.show();
                    if (this.children.workloadInput) this.children.workloadInput.$el.show();
                    this.toggleCustomWindow();
                    this.toggleCustomBackfillWindow();
                    this.toggleCustomMaxTimeWindow();
                    if (this.isHunk) {
                        this.children.enableHunkOptionsGroup.$el.show();
                        this.enableHunkOptionsVisibility();
                    }
                } else {
                    this.children.earliestTimeGroup.$el.hide();
                    if (this.children.workloadInput) this.children.workloadInput.$el.hide();
                    this.children.customWindow.$el.hide();
                    if (this.isHunk) {
                        this.children.enableHunkOptionsGroup.$el.hide();
                        this.children.flashMessages.$el.hide();
                        this.children.fileFormatGroup.$el.hide();
                        this.children.compressionGroup.$el.hide();
                        this.children.blockSizeGroup.$el.hide();
                    }
                }
            },

            toggleCustomWindow: function() {
                if (this.model.relativeTimeScheduleWindowModel.isCustom()) {
                    this.children.customWindow.$el.show();
                } else {
                    this.children.customWindow.$el.hide();
                }
            },

            toggleCustomBackfillWindow: function() {
                if (this.model.backfillTimeScheduleWindowModel.isCustom()) {
                    this.children.customBackfillWindow.$el.show();
                } else {
                    this.children.customBackfillWindow.$el.hide();
                }
            },

            toggleCustomMaxTimeWindow: function() {
                if (this.model.maxTimeWindowModel.isCustom()) {
                    this.children.customMaxTimeWindow.$el.show();
                } else {
                    this.children.customMaxTimeWindow.$el.hide();
                }
            },

            enableHunkOptionsVisibility: function() {
                if (this.enableHunkOptionsModel.get('enabled')) {
                    if (this.enableBlockSizeModel.get('enabled')) {
                        this.children.flashMessages.$el.show();
                    }
                    this.children.fileFormatGroup.$el.show();
                    this.children.compressionGroup.$el.show();
                    this.children.blockSizeGroup.$el.show();
                } else {
                    this.children.flashMessages.$el.hide();
                    this.children.fileFormatGroup.$el.hide();
                    this.children.compressionGroup.$el.hide();
                    this.children.blockSizeGroup.$el.hide();
                }
            },

            updateCompression: function() {
                var newFileFormat = this.fileFormat.getValue();
                if (this.currentFileFormat !== newFileFormat) {
                    if (newFileFormat === 'parquet') {
                       this.compression.setItems(this.parquetCompressionItems);
                    } else {
                        this.compression.setItems(this.orcCompressionItems);
                    }
                   this.compression.setValue('snappy');
                   this.currentFileFormat = newFileFormat;
                }
            },

            enableBlockSizeVisibility: function() {
                if (this.enableBlockSizeModel.get('enabled')) {
                    this.children.flashMessages.$el.show();
                    this.blockSize.enable();
                } else {
                    this.children.flashMessages.$el.hide();
                    this.blockSize.disable();
                }
            },

            primaryButtonClicked: function() {
                if (!this.model.maxTimeWindowModel.validate()) {
                    DialogBase.prototype.primaryButtonClicked.apply(this, arguments);

                    this.model.acceleration.set('earliest_time', this.model.relativeTimeScheduleWindowModel.getScheduleWindow());
                    this.model.acceleration.set('backfill_time', this.model.backfillTimeScheduleWindowModel.getScheduleWindow());
                    this.model.acceleration.set('max_time', parseInt(this.model.maxTimeWindowModel.getScheduleWindow(), 10));

                    if (this.isHunk && this.enableHunkOptionsModel.get('enabled') &&
                        this.enableBlockSizeModel.get('enabled')) {
                        if (_.isNaN(this.blockSize.getValueFromChildren()) ||
                            this.blockSize.getValueFromChildren() < this.THIRTYTWO_MB) {
                            this.children.flashMessages.flashMsgHelper.addGeneralMessage(this.blockSizeErrorMessageID, {
                                type: splunkdUtils.ERROR,
                                html: _('DFS Block Size must be a number greater than or equal to 32MB.').t()
                            });
                            return;
                        } else {
                            this.children.flashMessages.flashMsgHelper.removeGeneralMessage(this.blockSizeErrorMessageID);
                        }
                    }

                    this.enabledCheckBox.updateModel();
                    this.pollBucketsCheckBox.updateModel();
                    this.maxConcurrentSpinner.updateModel();
                    this.summarizationPeriodText.updateModel();
                    this.automaticRebuildsCheckBox.updateModel();
                    if (this.isHunk) {
                        if (this.enableHunkOptionsModel.get('enabled')) {
                            //this.fileFormat.updateModel();
                            this.model.dataModel.entry.content.acceleration.set('hunk.file_format', this.fileFormatModel.get('format'));
                            this.compression.updateModel();
                            if (this.enableBlockSizeModel.get('enabled')) {
                                this.blockSize.updateModel();
                            } else {
                                this.model.dataModel.entry.content.acceleration.set('hunk.dfs_block_size', '');
                            }
                        } else {
                            // unset all the Hunk options
                            this.model.dataModel.entry.content.acceleration.set('hunk.file_format', '');
                            this.model.dataModel.entry.content.acceleration.set('hunk.compression_codec', '');
                            this.model.dataModel.entry.content.acceleration.set('hunk.dfs_block_size', '');
                        }
                    }

                    // Save the results into our object
                    /**
                     * Save the Data Model
                     *
                     * @event AccelerationDialog#action:saveModel
                     * @param {string} data model name
                     */
                    this.trigger("action:saveModel", true);
                    this.stopListening(this.model.dataModel, 'sync', this.hide);
                    this.listenToOnce(this.model.dataModel, 'sync', this.hide);
                }
            },

            renderBody : function($el) {
                var html = _(this.bodyTemplate).template({
                    _: _
                });
                $el.html(html);
                $el.find('.error-message').append(this.children.flashMessages.render().el);
                $el.find(".nameLabel-placeholder").replaceWith(this.children.nameLabel.render().el);
                $el.find(".accelerate-checkbox-placeholder").replaceWith(this.children.enabledGroup.render().el);
                $el.find(".summary-range-dropdown-placeholder").replaceWith(this.children.earliestTimeGroup.render().el);
                $el.find(".custom-summary-range-placeholder").replaceWith(this.children.customWindow.render().el);
                if (this.children.workloadInput) $el.find(".workload-placeholder").replaceWith(this.children.workloadInput.render().el);
                $el.find(".backfill-window").replaceWith(this.children.backfillTimeGroup.render().el);
                $el.find(".custom-backfill-window").replaceWith(this.children.customBackfillWindow.render().el);
                $el.find(".maxtime-window").replaceWith(this.children.maxTimeGroup.render().el);
                $el.find(".custom-maxtime-window").replaceWith(this.children.customMaxTimeWindow.render().el);
                $el.find(".max-concurrent-searches").replaceWith(this.children.maxConcurrentSearches.render().el);
                $el.find(".poll-buckets").replaceWith(this.children.pollBucketsEnable.render().el);
                $el.find(".summarization-period").replaceWith(this.children.summarizationPeriod.render().el);
                $el.find(".automatic-rebuilds").replaceWith(this.children.automaticRebuildsEnable.render().el);

                if (this.isHunk) {
                    $el.find('.hunk-advanced-options').replaceWith(this.children.enableHunkOptionsGroup.render().el);
                    $el.find('.hunk-file-format').replaceWith(this.children.fileFormatGroup.render().el);
                    $el.find('.hunk-compression-codec').replaceWith(this.children.compressionGroup.render().el);
                    $el.find('.hunk-dfs-block-size').replaceWith(this.children.blockSizeGroup.render().el);
                }

                this.updateView();
                if (this.isHunk){
                    this.enableBlockSizeVisibility();
                }

                $el.find('.advanced-settings').hide();
            },

            bodyTemplate: '\
                <div class="error-message"></div>\
                <div class="nameLabel-placeholder"></div>\
                <div class="accelerate-checkbox-placeholder"></div>\
                <div class="summary-range-dropdown-placeholder"></div>\
                <div class="custom-summary-range-placeholder"></div>\
                <div class="workload-placeholder"></div>\
                <div class="advanced-settings-toggle-container">\
                    <a href="#" class="advanced-settings-toggle"><i class="toggle icon-chevron-right"></i><span class="advanced-settings-text"><%- _("Advanced Settings").t() %></span></a>\
                </div>\
                <div class="advanced-settings">\
                    <div class="advanced-settings-warning"><%- _("Change the following settings only if you are experiencing summary creation issues.").t() %>\
                        <a class="learn-more-link" href="#" target="_blank"><%- _("Learn More").t() %><i class="icon-external"></i></a>\
                    </div>\
                    <div class="backfill-window"></div>\
                    <div class="custom-backfill-window"></div>\
                    <div class="maxtime-window"></div>\
                    <div class="custom-maxtime-window"></div>\
                    <div class="max-concurrent-searches"></div>\
                    <div class="poll-buckets"></div>\
                    <div class="summarization-period"></div>\
                    <div class="automatic-rebuilds"></div>\
                    <div class="hunk-advanced-options"></div>\
                    <div class="hunk-file-format"></div>\
                    <div class="hunk-compression-codec"></div>\
                    <div class="hunk-dfs-block-size"></div>\
                </div>\
        '

        });

    });
