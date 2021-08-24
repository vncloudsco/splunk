define([
        'jquery',
        'underscore',
        'module',
        'splunk.util',
        'util/general_utils',
        'util/indexes/RollupUtils',
        'util/indexes/AddEditIndexPanelConstants',
        'collections/services/catalog/metricstore/Metrics',
        'collections/services/catalog/metricstore/Dimensions',
        'collections/services/data/Indexes',
        'models/Base',
        'models/services/catalog/metricstore/Rollup',
        'models/indexes/AddEditIndex',
        'views/shared/Modal',
        'views/indexes/core/AddEditIndexPanels',
        'views/shared/waitspinner/Master',
        './AddEditIndexModal.pcss'
    ],

    function(
        $,
        _,
        module,
        splunkutil,
        general_utils,
        RollupUtils,
        PANEL_CONSTANTS,
        MetricsCollection,
        DimensionsCollection,
        IndexesCollection,
        BaseModel,
        RollupModel,
        AddEditIndexModel,
        Modal,
        AddEditIndexPanels,
        WaitSpinner,
        css
    ) {
        return Modal.extend({
            moduleId: module.id,
            /**
             * @constructor
             * @memberOf views
             * @name AddEditIndexModal
             * @extends {views.Modal}
             * @description Modal for creating/editing indexes
             *
             * @param {Object} options
             * @param {Object} options.model The model supplied to this class
             * @param {Boolean} options.isNew Whether or not this is a new index
             * @param {Object} options.collection The collection supplied to this class
             */
            initialize: function(options) {
                Modal.prototype.initialize.call(this, arguments);
                $.fn.modal.Constructor.prototype.enforceFocus = function(){};
                _(options).defaults({
                    isNew: true,
                    disabled: splunkutil.normalizeBoolean(this.model.entity.entry.content.get("disabled"))
                });
                var metricName = this.model.entity.entry.get('name');
                this.model.content = new BaseModel({
                    activePanelId: PANEL_CONSTANTS.ADD_EDIT,
                    transition: 'forward',
                    isNew: this.options.isNew,
                    disabled: this.options.disabled
                });
                this.buildAddEditIndexModel(options);
                if (!this.options.isNew) {
                    this.buildRollupModel(metricName);
                } else {
                    this.model.rollup = undefined;
                }
                this.initializeCollections();
                this.textMap = {};
                this.textMap[PANEL_CONSTANTS.ADD_EDIT] = {
                    headerText: this.model.content.get('isNew')
                        ? _('New Index').t()
                        : splunkutil.sprintf(_('Edit Index: %s').t(), _.escape(metricName)),
                    primaryText: _('Save').t(),
                    secondaryText: _('Cancel').t(),
                };
                this.textMap[PANEL_CONSTANTS.ROLLUP_SETTINGS] = {
                    headerText: splunkutil.sprintf(_('New Rollup Policy for %s').t(), _.escape(metricName)),
                    primaryText: _('Create Policy').t(),
                    secondaryText: _('Cancel').t(),
                };
                this.textMap[PANEL_CONSTANTS.ROLLUP_SETTINGS_EDIT] = {
                    headerText: splunkutil.sprintf(_('Edit Rollup Policy for %s').t(), _.escape(metricName)),
                    primaryText: _('Edit Policy').t(),
                    secondaryText: _('Cancel').t(),
                };
                this.textMap[PANEL_CONSTANTS.CONFIRM_EDIT_ROLLUP] = {
                    headerText: _('Warning to Edit the Policy').t(),
                    primaryText: _('Continue to Change Policy').t(),
                    secondaryText: _('Cancel').t(),
                };
                this.textMap[PANEL_CONSTANTS.CONFIRM_DELETE_ROLLUP] = {
                    headerText: _('Warning to Delete the Policy').t(),
                    primaryText: _('Continute to Delete Policy').t(),
                    secondaryText: _('Cancel').t(),
                };
                this.children.panels = new AddEditIndexPanels({
                    model: {
                        content: this.model.content,
                        rollup: this.model.rollup,
                        entity: this.model.entity,
                        addEditIndexModel: this.model.addEditIndexModel,
                        user: this.model.user,
                        application: this.model.application
                    },
                    collection: {
                        appLocals: this.collection.appLocals,
                        metrics: this.collection.metrics,
                        dimensions: this.collection.dimensions,
                        indexes: this.collection.indexes
                    }
                });
                this.children.waitSpinner = new WaitSpinner({});
                this.startListening();
            },

            startListening: function() {
                this.listenTo(this.model.content, 'change:activePanelId', this.render);
                if (this.model.rollup) {
                    this.listenTo(this.model.rollup, 'change:toRollupTransitioning', this.handleRollupTransitionChange);
                }
            },

            getMetricModelByName: function(dataType, metricName) {
                if (dataType !== 'metric' && dataType !== 'rollup') {
                    return null;
                }
                return this.collection.entities.filter(function(model) {
                    return model.entry.get('name') === metricName;
                })[0];
            },

            buildRollupModel: function(metricName) {
                var dataType = this.model.entity.getDataType();
                var model = this.getMetricModelByName(dataType, metricName);
                if (dataType === 'metric') {
                    var rollupUIProps = model.entry.content.get('rollupUIProps');
                    this.model.rollup = new RollupModel({
                        rollupTimes: [],
                        name: metricName,
                        hasViewCapability: rollupUIProps.hasViewCapability,
                        hasEditCapability: rollupUIProps.hasEditCapability,
                        minSpanAllowed: rollupUIProps.minSpanAllowed
                    });
                } else if (dataType === 'rollup') {
                    var attrs = model.entry.content.get('rollupUIProps');
                    attrs.name = metricName;
                    this.model.rollup = new RollupModel(attrs);
                }
            },

            initializeCollections: function() {
                this.collection.metrics = new MetricsCollection();
                this.collection.dimensions = new DimensionsCollection();
                this.collection.indexes = new IndexesCollection();
            },

            handleRollupTransitionChange: function() {
                if (this.model.rollup.get('toRollupTransitioning')) {
                    this.$('.shared-waitspinner').show();
                } else {
                    this.$('.shared-waitspinner').hide();
                }
            },

            events: $.extend({}, Modal.prototype.events, {
                'click .btn-primary': function(e) {
                    this.handlePrimaryClick();
                },
                'click .btn-secondary': function(e) {
                    this.handleSecondaryClick();
                },
            }),

            buildAddEditIndexModel: function(options) {
                var applicationApp = (!options.isNew && this.model && this.model.entity) ?
                                        this.model.entity.entry.acl.get('app') :
                                        options.model.application.get('app'),
                    useApplicationApp = false,
                    appItems = [];

                // Initialize the working model
                if (options.isNew) {

                    if (this.model.user.canUseApps()){
                        // Filter out the app list to hold apps the user can write to
                        this.collection.appLocals.each(function(model){
                            if (model.entry.acl.get("can_write")) {
                                appItems.push({
                                    label: model.entry.content.get('label'),
                                    value: model.entry.get('name')
                                });
                                if (model.entry.get('name') == applicationApp)
                                    useApplicationApp = true;
                            }
                        }, this);

                        // Use the current app unless user can't write to it
                        if (!useApplicationApp && appItems.length > 0) {
                            applicationApp = appItems[0].value;
                        }
                    }
                    else {
                        applicationApp = undefined;
                    }
                    this.model.addEditIndexModel = new AddEditIndexModel({
                        isNew: true,
                        app: applicationApp
                    });
                }
                else {
                    var name = this.model.entity.entry.get("name"),
                        dataType = this.model.entity.getDataType(),
                        homePath = this.model.entity.entry.content.get("homePath"),
                        coldPath = this.model.entity.entry.content.get("coldPath"),
                        thawedPath = this.model.entity.entry.content.get("thawedPath"),
                        frozenPath = this.model.entity.entry.content.get("coldToFrozenDir"),
                        enableDataIntegrityControl = this.model.entity.entry.content.get('enableDataIntegrityControl'),
                        maxDataSize = this.model.entity.entry.content.get("maxDataSize"),
                        maxIndexSizeObject = general_utils.formatSize(this.model.entity.entry.content.get("maxTotalDataSizeMB")),
                        maxIndexSize = maxIndexSizeObject.size,
                        maxIndexSizeFormat = maxIndexSizeObject.format,
                        maxBucketSizeObject = general_utils.formatSize(this.model.entity.entry.content.get("maxDataSize")),
                        maxBucketSize = maxBucketSizeObject.size,
                        maxBucketSizeFormat = maxBucketSizeObject.format,
                        enableTsidxReduction = splunkutil.normalizeBoolean(this.model.entity.entry.content.get("enableTsidxReduction")),
                        tsidxReductionPeriod = this.model.entity.entry.content.get("tsidxReductionCheckPeriodInSec"),
                        tsidxReductionFreqObj = general_utils.convertSecondsToPeriod(this.model.entity.entry.content.get("timePeriodInSecBeforeTsidxReduction"));

                    this.model.addEditIndexModel = new AddEditIndexModel({
                        isNew: false,
                        dataType: dataType,
                        app: applicationApp,
                        homePath: homePath,
                        coldPath: coldPath,
                        thawedPath: thawedPath,
                        frozenPath: frozenPath,
                        enableDataIntegrityControl: enableDataIntegrityControl,
                        maxDataSize: maxDataSize,
                        maxIndexSize: maxIndexSize,
                        maxIndexSizeFormat: maxIndexSizeFormat,
                        maxBucketSize: maxBucketSize,
                        maxBucketSizeFormat: maxBucketSizeFormat,
                        enableTsidxReduction: enableTsidxReduction,
                        tsidxReductionCheckPeriodInSec: tsidxReductionPeriod,
                        timePeriodInSecBeforeTsidxReduction: tsidxReductionFreqObj.value,
                        tsidxAgeFormat: tsidxReductionFreqObj.format
                    });
                }
                this.isMetrics = this.model.entity.getDataType() === 'metric' || this.model.entity.getDataType() === 'rollup';
            },

            getModalTexts: function() {
                var activePanelId = this.model.content.get('activePanelId');
                return this.textMap[activePanelId];
            },

            handleRollupCreate: function() {
                var errorTab = this.model.rollup.updateErrors();
                if (errorTab !== null) {
                    this.model.content.set({
                        tabIndex: errorTab
                    });
                    return;
                }
                var generalPolicy = this.model.rollup.get('tabs')[0];
                var summaries = generalPolicy.summaries;
                var rollupTimes = RollupUtils.getTimes(summaries);
                var tabs = this.model.rollup.sanitizeTabs();
                var tabIndex = this.model.content.get('tabIndex');
                this.model.content.set({
                    tabIndex: tabIndex >= tabs.length ? 0 : tabIndex,
                    activePanelId: PANEL_CONSTANTS.ADD_EDIT,
                    transition: 'backward'
                });
                this.model.rollup.set({
                    tabs: tabs,
                    rollupTimes: rollupTimes
                });
            },

            handlePrimaryClick: function() {
                var activePanelId = this.model.content.get('activePanelId');
                switch (activePanelId) {
                    case PANEL_CONSTANTS.ADD_EDIT:
                        var dataType = this.model.entity.getDataType();
                        var isValidRollupDataType = dataType === 'metric' || dataType === 'rollup';
                        var isRollupEdit = dataType === 'rollup';
                        if (isValidRollupDataType && this.model.rollup && this.model.rollup.exists()) {
                            if (!this.model.rollup.get('hasEditCapability')) {
                                this.handleAddEditIndex();
                            } else {
                                this.handleRollupSave(isRollupEdit).done(function() {
                                    this.handleAddEditIndex();
                                }.bind(this));
                            }
                        } else if (isRollupEdit) {
                            if (!this.model.rollup.get('hasEditCapability')) {
                                this.handleAddEditIndex();
                            } else {
                                var deleteRollupDfd = this.model.rollup.destroy({wait:true});
                                $.when(deleteRollupDfd).done(function() {
                                    this.handleAddEditIndex();
                                }.bind(this));
                            }
                        } else {
                            this.handleAddEditIndex();
                        }
                        break;
                    case PANEL_CONSTANTS.ROLLUP_SETTINGS:
                    case PANEL_CONSTANTS.ROLLUP_SETTINGS_EDIT:
                        this.handleRollupCreate();
                        break;
                    case PANEL_CONSTANTS.CONFIRM_EDIT_ROLLUP:
                        this.model.content.set({
                            activePanelId: PANEL_CONSTANTS.ROLLUP_SETTINGS_EDIT,
                            transition: 'forward'
                        });
                        this.model.rollup.set({
                            preEditTabs: this.model.rollup.get('tabs'),
                        });
                        break;
                    case PANEL_CONSTANTS.CONFIRM_DELETE_ROLLUP:
                        this.model.content.set({
                            activePanelId: PANEL_CONSTANTS.ADD_EDIT,
                            transition: 'backward'
                        });
                        this.model.rollup.set({
                            rollupTimes: [],
                            tabs: []
                        });
                        break;
                    default:
                        break;
                }
            },

            handleSecondaryClick: function() {
                var activePanelId = this.model.content.get('activePanelId');
                switch (activePanelId) {
                    case PANEL_CONSTANTS.ADD_EDIT:
                        this.hide();
                        break;
                    case PANEL_CONSTANTS.ROLLUP_SETTINGS:
                        this.model.content.set({
                            activePanelId: PANEL_CONSTANTS.ADD_EDIT,
                            transition: 'backward',
                            tabIndex: 0
                        });
                        this.model.rollup.set({
                            tabs: []
                        });
                        break;
                    case PANEL_CONSTANTS.ROLLUP_SETTINGS_EDIT:
                        this.model.content.set({
                            activePanelId: PANEL_CONSTANTS.ADD_EDIT,
                            transition: 'backward',
                            tabIndex: 0
                        });
                        this.model.rollup.set({
                            tabs: this.model.rollup.get('preEditTabs')
                        });
                        break;
                    case PANEL_CONSTANTS.CONFIRM_EDIT_ROLLUP:
                        this.model.content.set({
                            activePanelId: PANEL_CONSTANTS.ADD_EDIT,
                            transition: 'backward',
                        });
                        break;
                    case PANEL_CONSTANTS.CONFIRM_DELETE_ROLLUP:
                        this.model.content.set({
                            activePanelId: PANEL_CONSTANTS.ADD_EDIT,
                            transition: 'backward',
                        });
                        break;
                    default:
                        break;
                }
            },

            handleRollupSave: function(isRollupEdit) {
                var saveOptions = {
                    data: {
                        app: this.model.entity.entry.acl.get('app'),
                        owner: this.model.entity.entry.acl.get('owner')
                    }
                };
                return isRollupEdit
                    ? this.model.rollup.update(saveOptions)
                    : this.model.rollup.save(saveOptions);
            },

            handleAddEditIndex: function() {
                if (this.model.addEditIndexModel.set({}, {validate:true})) {
                    // Copy addEditIndexModel attributes to this.model
                    var name = this.model.addEditIndexModel.get("name"),
                        dataType = this.model.addEditIndexModel.get("dataType"),
                        app = this.model.addEditIndexModel.get("app"),
                        homePath = this.model.addEditIndexModel.get("homePath"),
                        coldPath = this.model.addEditIndexModel.get("coldPath"),
                        thawedPath = this.model.addEditIndexModel.get("thawedPath"),
                        frozenPath = this.model.addEditIndexModel.get("frozenPath"),
                        enableDataIntegrityControl = this.model.addEditIndexModel.get("enableDataIntegrityControl"),
                        maxIndexSize = general_utils.formatSizeForSave(this.model.addEditIndexModel.get("maxIndexSize"), this.model.addEditIndexModel.get("maxIndexSizeFormat")),
                        maxBucketSize = general_utils.formatSizeForSave(this.model.addEditIndexModel.get("maxBucketSize"), this.model.addEditIndexModel.get("maxBucketSizeFormat")),
                        enableTsidxReduction = splunkutil.normalizeBoolean(this.model.addEditIndexModel.get("enableTsidxReduction")),
                        tsidxReductionCheckPeriodInSec = this.model.addEditIndexModel.get("tsidxReductionCheckPeriodInSec"),
                        timePeriodInSecBeforeTsidxReduction = general_utils.convertPeriodToSec(this.model.addEditIndexModel.get("timePeriodInSecBeforeTsidxReduction"), this.model.addEditIndexModel.get("tsidxAgeFormat"));

                    var indexParams= {
                        name: this.model.content.get('isNew') ? name : undefined,
                        datatype: dataType,
                        homePath: homePath,
                        coldPath: coldPath,
                        thawedPath: thawedPath,
                        maxTotalDataSizeMB: maxIndexSize,
                        maxDataSize: maxBucketSize,
                        coldToFrozenDir: frozenPath
                    };

                    if (!this.isMetrics) {
                        _.extend(indexParams, {
                            enableDataIntegrityControl: enableDataIntegrityControl,
                            enableTsidxReduction: enableTsidxReduction,
                            tsidxReductionCheckPeriodInSec: enableTsidxReduction ? tsidxReductionCheckPeriodInSec : undefined,
                            timePeriodInSecBeforeTsidxReduction: enableTsidxReduction ? timePeriodInSecBeforeTsidxReduction : undefined
                        });
                    }

                    this.model.entity.entry.content.set(indexParams);

                    var indexDeferred = this.model.content.get('isNew') ? this.model.entity.save({}, {
                        data: {
                            app: app
                        }
                    }) : this.model.entity.save();

                    $.when(indexDeferred).done(_(function() {
                        this.trigger("entitySaved", name);
                        this.hide();
                    }).bind(this));
                }
            },

            updateModalItems: function() {
                var modalTexts = this.getModalTexts();
                this.$(Modal.HEADER_TITLE_SELECTOR).html(_(modalTexts.headerText).t());
                this.$(Modal.FOOTER_SELECTOR).empty();
                var primaryBtn = '<a href="#" role="button" class="btn btn-primary modal-btn-primary">' + modalTexts.primaryText + '</a>';
                var secondaryBtn = '<a href="#" role="button" class="btn cancel btn-secondary modal-btn-cancel">' + modalTexts.secondaryText + '</a>';
                this.$(Modal.FOOTER_SELECTOR).append(primaryBtn);
                this.$(Modal.FOOTER_SELECTOR).append(secondaryBtn);
                this.$(Modal.FOOTER_SELECTOR).append(this.children.waitSpinner.render().el);
                this.children.waitSpinner.start();
                this.$('.shared-waitspinner').hide();
            },

            updateModalClasses: function() {
                var activePanelId = this.model.content.get('activePanelId');
                if (activePanelId === PANEL_CONSTANTS.ROLLUP_SETTINGS || activePanelId === PANEL_CONSTANTS.ROLLUP_SETTINGS_EDIT) {
                    this.$el.addClass('rollup-settings-modal');
                    this.$el.removeClass(Modal.CLASS_MODAL_WIDE);
                } else {
                    this.$el.addClass(Modal.CLASS_MODAL_WIDE);
                    this.$el.removeClass('rollup-settings-modal');
                }
            },

            render: function() {
                if (!this.el.innerHTML) {
                    this.$el.html(Modal.TEMPLATE);
                    this.$(Modal.BODY_SCROLLING_SELECTOR).css({'padding': '0px'});
                    this.$(Modal.BODY_SELECTOR).show();
                    this.$(Modal.BODY_SELECTOR).append(Modal.FORM_HORIZONTAL);
                    this.$(Modal.BODY_FORM_SELECTOR).html(_(this.dialogFormBodyTemplate).template({}));
                    this.children.panels.render().appendTo(this.$(".modal-content"));
                } else {
                    this.children.panels.render();
                }
                this.updateModalItems();
                this.updateModalClasses();
                return this;
            },

            dialogFormBodyTemplate: '\
                <div class="modal-content">\
            '
        });
    });
