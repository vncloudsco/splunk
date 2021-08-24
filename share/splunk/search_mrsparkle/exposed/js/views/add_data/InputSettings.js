/**
 * 3rd step in the workflow: Input Settings.
 *
 */
define(
    [
        'jquery',
        'underscore',
        'backbone',
        'module',
        'collections/services/AppLocals',
        'collections/indexes/cloud/Archives',
        'collections/services/configs/conf-self-storage-locations/BucketList',
        'models/indexes/cloud/Archiver',
        'models/services/data/Archiver',
        'models/services/data/Indexes',
        'views/Base',
        'views/indexes/core/AddEditIndexModal',
        'views/indexes/cloud/AddEditIndexDialog',
        'views/shared/controls/ControlGroup',
        'views/shared/knowledgeobjects/SourcetypeMenu',
        'views/shared/waitspinner/Master',
        'views/shared/FlashMessages',
        'uri/route',
        'contrib/text!views/add_data/InputSettings.html',
        'views/shared/Faq',
        'splunk.util',
        './InputSettings.pcss'
    ],
    function (
        $,
        _,
        Backbone,
        module,
        AppLocals,
        ArchivesCollection,
        BucketListCollection,
        ArchiverModel,
        ArchiverSingleInstanceModel,
        IndexModel,
        BaseView,
        AddEditIndexDialogCore,
        AddEditIndexDialogCloud,
        ControlGroup,
        SourcetypeMenu,
        WaitSpinner,
        FlashMessagesView,
        route,
        template,
        Faq,
        util,
        css
        ) {
        /**
         */
        return BaseView.extend({
            template: template,
            moduleId: module.id,
            className: 'input-settings-main input-settings-form-horizontal',
            initialize: function (options) {
                BaseView.prototype.initialize.apply(this, arguments);

                this.deferreds = {};

                var serverName = this.model.serverInfo.getServerName();

                this.isStackmakr = util.isStackmakr(this.model.dmcSettings.isEnabled(), this.model.serverInfo.isCloud());

                // set default app context and host switch position
                var defaults = {
                    appContext: this.model.application.get('app') || 'search',
                    hostSwitch: 'constant',
                    sourcetypeSwitch: 'auto',
                    'ui.host': serverName
                };
                _.defaults(this.model.input.attributes, defaults);

                this.model.stateModel = this.model.stateModel || new Backbone.Model();
                this.model.stateModel.set('isArchiverAppInstalled', this.collection.appLocals.isArchiverAppInstalled());

                // don't let appcontext be in system
                if (this.model.input.get('appContext') === 'system') {
                    this.model.input.set('appContext', 'search');
                }

                if (!this.model.sourcetype.get('ui.category')) {
                    this.model.sourcetype.set({'ui.category': 'Custom'});
                }

                if (['tcp','udp','scripts'].indexOf(this.model.wizard.get('inputType')) > -1) {
                    this.model.input.set({sourcetypeSwitch: 'select'});
                } else if (this.model.input.get('ui.sourcetype') && !this.model.input.get('sourcetypeSwitch')) {
                    this.model.input.set({sourcetypeSwitch: 'select'});
                } else if (this.model.wizard.get('inputType') === 'http' && this.isStackmakr) {
                    this.model.input.set({sourcetypeSwitch: 'select'});
                }

                var filteredAppLocals = this.collection.appLocalsUnfilteredAll.listOnlyWriteableAndNonInternalApps();
                this.collection.filteredAppLocals = new AppLocals(filteredAppLocals);

                this.collection.bucketList = new BucketListCollection();

                this.children.waitSpinner = new WaitSpinner();
                if (this.model.serverInfo.isCloud()){
                    this.children.waitSpinnerArchives = new WaitSpinner();
                }

                this.children.flashMessages = new FlashMessagesView({
                    model: {
                        input: this.model.input,
                        sourcetype: this.model.sourcetype
                    }
                });

                this.children.sourcetypeSwitch = new ControlGroup({
                    className: 'sourcetype-switch control-group',
                    controlType: 'SyntheticRadio',
                    controlOptions: {
                        modelAttribute: 'sourcetypeSwitch',
                        model: this.model.input,
                        items: [
                            {
                                label: _('Automatic').t(),
                                value: 'auto'
                            },
                            {
                                label: _('Select').t(),
                                value: 'select'
                            },
                            {
                                label: _('New').t(),
                                value: 'manual'
                            }
                        ],
                        save: false
                    }
                });

                this.children.sourcetype = new SourcetypeMenu({
                    model: this.model.input,
                    modelAttribute: 'ui.sourcetype',
                    collection: this.collection,
                    addNewSourcetypeLink: false,
                    addLabel: false
                });

                this.children.sourcetypeManual = new ControlGroup({
                    className: 'sourcetype control-group',
                    controlType: 'Text',

                    controlOptions: {
                        modelAttribute: 'ui.sourcetype',
                        model: this.model.input,
                        save: false
                    },
                    label: _('Source Type').t()
                });
                this.children.sourcetypeCategory = new ControlGroup({
                    className: 'sourcetype-category control-group',
                    controlType: 'SyntheticSelect',

                    controlOptions: {
                        modelAttribute: 'ui.category',
                        model: this.model.sourcetype,
                        items: this.collection.sourcetypesCollection.getCategories(),
                        additionalClassNames: 'view-count',
                        menuWidth: 'narrow',
                        toggleClassName: 'btn'
                    },
                    label: _('Source Type Category').t()
                });
                this.children.sourcetypeDescription = new ControlGroup({
                    className: 'sourcetype-desc control-group',
                    controlType: 'Text',

                    controlOptions: {
                        modelAttribute: 'ui.description',
                        model: this.model.sourcetype,
                        save: false
                    },
                    label: _('Source Type Description').t()
                });

                this.children.context = new ControlGroup({
                    className: 'context control-group',
                    controlType: 'SyntheticSelect',

                    controlOptions: {
                        modelAttribute: 'appContext',
                        model: this.model.input,
                        items: this.buildAppItems(),
                        additionalClassNames: 'view-count',
                        toggleClassName: 'btn'
                    },
                    label: _('App Context').t()
                });

                this.children.hostSwitch = new ControlGroup({
                    className: 'host-switch control-group',
                    controlType: 'SyntheticRadio',
                    controlOptions: {
                        modelAttribute: 'hostSwitch',
                        model: this.model.input,
                        showAsButtonGroup: false,
                        items: [
                            {
                                label: _('Constant value').t(),
                                value: 'constant'
                            },
                            {
                                label: _('Regular expression on path').t(),
                                value: 'regex'
                            },
                            {
                                label: _('Segment in path').t(),
                                value: 'segment'
                            }
                        ],
                        save: false,
                        label: _('Specify method for getting host field for events coming from this source.').t()
                    }
                });

                this.children.hostSwitchNet = new ControlGroup({
                    className: 'host-switch-net control-group',
                    controlType: 'SyntheticRadio',
                    controlOptions: {
                        modelAttribute: 'ui.connection_host',
                        model: this.model.input,
                        items: [
                            {
                                label: _('IP').t(),
                                value: 'ip'
                            },
                            {
                                label: _('DNS').t(),
                                value: 'dns'
                            },
                            {
                                label: _('Custom').t(),
                                value: 'none'
                            }
                        ]
                    },
                    label: _('Method').t(),
                    tooltip: _('Specify method for getting host field for events coming from this source.').t()
                });

                this.children.host = new ControlGroup({
                    className: 'host control-group',
                    controlType: 'Text',

                    controlOptions: {
                        modelAttribute: 'ui.host',
                        model: this.model.input,
                        save: false
                    },
                    label: _('Host field value').t()
                });
                this.children.hostRegex = new ControlGroup({
                    className: 'host_regex control-group',
                    controlType: 'Text',

                    controlOptions: {
                        modelAttribute: 'ui.host_regex',
                        model: this.model.input,
                        save: false
                    },
                    tooltip: _('Specify the regular expression the Splunk platform uses to extract host names from the source path.').t(),
                    label: _('Regular expression').t()
                });
                this.children.hostSegment = new ControlGroup({
                    className: 'host_segment control-group',
                    controlType: 'Text',

                    controlOptions: {
                        modelAttribute: 'ui.host_segment',
                        model: this.model.input,
                        save: false
                    },
                    tooltip: _('Specify which segment of the source path to set as the Host field. For example: 3 (sets to "hostname" for the path /var/log/hostname/)').t(),
                    label: _('Segment number').t()
                });

                this.children.faq = new Faq({faqList: this.faqList});

                /* Events */
                this.model.input.on('change:hostSwitch', function() {
                    this.updateFileHostVisibility();
                }, this);

                this.model.input.on('change:ui.connection_host', function() {
                    this.updateNetHostVisibility();
                }, this);

                this.model.input.on('change:sourcetypeSwitch', function() {
                    this.model.input.set({'ui.sourcetype': ''});
                    this.updateSourcetypeVisibility();
                }, this);

                this.collection.indexes.on('reset', function() {
                    this.updateIndexControl();
                    if (this.model.wizard.get('inputType') === 'http') {
                        this.updateAvailableIndexes();
                    }
                }, this);

                // If HTTP Inputs:
                // update default indexes list as allowed list is changed
                this.model.input.on('change:ui.indexes', function(model, uiindexes) {
                    this.updateIndexControl();
                }, this);

            },

            buildAppItems: function() {
                var items = [];
                _(this.collection.appLocalsUnfilteredAll.listOnlyWriteableAndNonInternalApps()).each(function(app){
                    items.push({
                        value: app.entry.get('name'),
                        label: app.getLabel()
                    });
                });
                return _.sortBy(items, function(item){
                    return (item.label||'').toLowerCase();
                });
            },

            updateIndexControlContent: function() {
                // Determines list of indexes to show in 'default index' popdown and selects default one
                var selectedIndex = '', // the selected value of 'default index' dropdown
                    uiindexes = this.model.input.get('ui.indexes');
                this.indexes = []; // 'default index' values
                if (this.model.wizard.get('inputType') === 'http') {
                    if (!uiindexes || !uiindexes.length) { // list of allowed is empty - get all indexes
                        this.indexes.push({label: _('Default').t(), value:''});
                        this.collection.indexes.each(function(model) {
                            var indexName = model.entry.get('name');
                            this.indexes.push({
                                label: indexName,
                                value: indexName,
                                icon: model.getDataType()
                            });
                        }.bind(this));
                        selectedIndex = this.model.input.get('ui.index') ? this.model.input.get('ui.index') : '';
                    } else { // populate 'default index' with selected allowed ones
                        var selectedModels = _.filter(this.collection.indexes.models, function(model) {
                            return _.contains(uiindexes, model.entry.get('name'));
                        });
                        this.indexes = _.map(selectedModels, function(model) {
                            return {
                                label: model.entry.get('name'),
                                value: model.entry.get('name'),
                                icon: model.getDataType()
                            };
                        });
                        selectedIndex = _.contains(uiindexes, this.model.input.get('ui.index')) ?
                            this.model.input.get('ui.index') :
                            uiindexes[0]; // the first in the list will be default
                    }
                    this.model.input.set('ui.index', selectedIndex); // set the selected 'default index'
                } else {
                    this.indexes.push({label: _('Default').t(), value:''});
                    this.collection.indexes.each(function(model) {
                        var indexName = model.entry.get('name');
                        this.indexes.push({
                            label: indexName,
                            value:indexName,
                            icon: model.getDataType()
                        });
                    }.bind(this));
                }
            },

            updateAvailableIndexesContent: function() {
                this.availableIndexes = []; // 'allowed indexes' available values
                this.collection.indexes.each(function(model) {
                    var indexName = model.entry.get('name');
                    this.availableIndexes.push({label: indexName, value:indexName, icon: model.getDataType()});
                }.bind(this));
            },

            updateIndexControl: function() {
                if (this.children.index)
                    this.children.index.detach();

                this.updateIndexControlContent();

                this.children.index = new ControlGroup({
                    className: 'index control-group inline',
                    controlType: 'SyntheticSelect',
                    controlOptions: {
                        modelAttribute: 'ui.index',
                        model: this.model.input,
                        items: this.indexes,
                        additionalClassNames: 'view-count',
                        menuWidth: 'wide',
                        toggleClassName: 'btn',
                        popdownOptions: {
                            minMargin: 120
                        }
                    },
                    label: (this.model.wizard.get('inputType') === 'http') ? _('Default Index').t() : _('Index').t()
                });

                $('.layoutBodyColumns').on('scroll', this.windowScroll.bind(this));

                this.children.waitSpinner.stop();
                this.children.waitSpinner.remove();

                this.$('#index_placeholder').prepend(this.children.index.render().el);
            },

            /** Popdown will adjust position if popdown touches the header SPL-148286 */
            windowScroll: function(e) {
                if (this.children.index && this.children.index.childList && this.children.index.childList[0] &&
                    this.children.index.childList[0].children && this.children.index.childList[0].children.popdown) {
                    var popdown = this.children.index.childList[0].children.popdown;
                    if (popdown && popdown.children && popdown.children.delegate && popdown.children.delegate.isShown) {
                        popdown.adjustPosition();
                    }
                }
            },

            updateAvailableIndexes: function() {
                if (this.children.allowedIndexes)
                    this.children.allowedIndexes.detach();

                this.updateAvailableIndexesContent();

                var availableItems = this.availableIndexes,
                    selectedItems = this.model.input.get('ui.indexes') || [];

                this.children.allowedIndexes = new ControlGroup({
                    className: 'allowed-indexes control-group',
                    controlType: 'Accumulator',

                    controlOptions: {
                        modelAttribute: 'ui.indexes',
                        model: this.model.input,
                        save: false,
                        availableItems: availableItems,
                        selectedItems: selectedItems
                    },
                    label: _('Select Allowed Indexes').t(),
                    help: _('Select indexes that clients will be able to select from.').t()
                });
                this.$('#allowed_indexes_placeholder').html(this.children.allowedIndexes.render().el);
            },

            updateFileHostVisibility: function() {
                var hostSwitch = this.model.input.get('hostSwitch');
                this.children.host.$el.hide();
                this.children.hostRegex.$el.hide();
                this.children.hostSegment.$el.hide();

                if (hostSwitch === 'constant') {
                    this.children.host.$el.show();
                } else if (hostSwitch === 'regex') {
                    this.children.hostRegex.$el.show();
                } else if (hostSwitch === 'segment') {
                    this.children.hostSegment.$el.show();
                }
            },

            updateNetHostVisibility: function() {
                var connectionHost = this.model.input.get('ui.connection_host');
                this.children.host.$el.hide();
                if (connectionHost === 'none') {
                    this.children.host.$el.show();
                } else {
                    this.children.host.$el.hide();
                }
            },

            updateSourcetypeVisibility: function() {
                var mode = this.model.input.get('sourcetypeSwitch'),
                    $controls = this.$('.sourcetype-switch .controls'),
                    $btns = $controls.find('.btn-group');
                $btns.removeClass('hidden-button');
                this.children.sourcetype.$el.hide();
                this.children.sourcetypeManual.$el.hide();
                this.children.sourcetypeCategory.$el.hide();
                this.children.sourcetypeDescription.$el.hide();
                if (mode === 'select') {
                    this.children.sourcetype.$el.show();
                } else if (mode === 'manual') {
                    this.children.sourcetypeManual.$el.show();
                    this.children.sourcetypeCategory.$el.show();
                    this.children.sourcetypeDescription.$el.show();
                }
                if (['tcp','udp','scripts'].indexOf(this.model.wizard.get('inputType')) > -1) {
                    this.$('button[data-value=auto]').hide();
                    $btns.addClass('hidden-button');
                }
                if (this.model.wizard.get('inputType') === 'http' && this.isStackmakr) {
                    this.$('.sourcetype-switch').hide();
                }
            },

            showAddEditDialog: function() {
                var dialogOptions = {};
                dialogOptions.collection = {};

                var isCloud = this.model.serverInfo.isCloud();
                var archiverModelClass = this.options.isSingleInstanceCloud ? ArchiverSingleInstanceModel : ArchiverModel;
                var dialogClass = isCloud ? AddEditIndexDialogCloud : AddEditIndexDialogCore;
                this.collection.archives = isCloud ? new ArchivesCollection() : null;

                $.when(this.fetchArchivesCollection()).then(_(function() {
                    if (this.children.waitSpinnerArchives){
                        this.children.waitSpinnerArchives.stop();
                        this.children.waitSpinnerArchives.$el.hide();
                    }

                    dialogOptions.isNew = true;
                    dialogOptions.model = {
                        application: this.model.application,
                        user: this.model.user,
                        stateModel: this.model.stateModel,
                        entity: new IndexModel()
                    };

                    dialogOptions.collection.appLocals = this.collection.filteredAppLocals;
                    dialogOptions.collection.archives = this.collection.archives;
                    dialogOptions.archiverModelClass = archiverModelClass;
                    // TODO: Enclose the below in an if-block once the backend is ready
                    dialogOptions = $.extend(dialogOptions, {
                        SELF_STORAGE: 'SelfStorage',
                        ARCHIVE: 'Archive',
                        NONE: 'None'
                    });

                    if (isCloud) {
                        dialogOptions.model.controller = new Backbone.Model();
                        dialogOptions.model.controller.set('singleInstance', this.options.isSingleInstanceCloud);
                        dialogOptions.model.controller.set('cloudLight', this.model.serverInfo.isLite());

                        if(!_.isUndefined(this.model.stateModel.get('isArchiverAppInstalled'))) {
                            this.model.stateModel.set('isSelfStorage', false);
                            // fetch bucketlist when showAddEditDialog is called instead of constructor
                            // to avoid fetching bucketlist if not needed
                            this.deferreds.bucketList = new $.Deferred();
                            dialogOptions.collection.bucketList = this.collection.bucketList;
                            dialogOptions.deferreds = {
                                bucketList: this.deferreds.bucketList
                            };
                            this.collection.bucketList.fetch({
                                data: {
                                    count: -1,
                                    owner: this.model.application.get('owner'),
                                    app: this.model.application.get('app')
                                },
                                success: _(function (collection, response) {
                                    if (collection.length > 0) {
                                        this.model.stateModel.set('selfStorageConfigured', true);
                                    } else {
                                        this.model.stateModel.set('selfStorageConfigured', false);
                                    }
                                    this.deferreds.bucketList.resolve();
                                }).bind(this)
                            });
                            this.model.stateModel.set('archiverAppLabel', this.collection.appLocals.archiverAppLabel());
                        }
                    }

                    this.children.editIndexDialog = new dialogClass(dialogOptions);
                    this.listenTo(this.children.editIndexDialog, "entitySaved", this.onIndexSaved);
                    this.listenTo(this.children.editIndexDialog, "hidden", this.onSaveDialogHidden);
                    this.children.editIndexDialog.render().appendTo($("body"));
                    this.children.editIndexDialog.show();
                }).bind(this));
            },

            fetchArchivesCollection: function() {
                if (this.collection.archives && this.model.user.canArchive() && this.model.user.canEditArchives()) {
                    return this.collection.archives.fetch({
                        data: {
                            count: -1
                        }
                    });
                } else {
                    var theDeferred = $.Deferred();
                    theDeferred.resolve();
                    return theDeferred;
                }
            },

            onIndexSaved: function(indexName) {
                // Since we don't get the promise from the controller, just listen for sync before setting the
                // index dropdown to use the newly created index
                this.listenToOnce(this.collection.indexes, "sync", this.onSyncIndexes);
                this.lastCreatedIndex = indexName;
                this.fetchIndexesCollection();
            },

            onSyncIndexes: function() {
                this.model.input.set("ui.index", this.lastCreatedIndex);
            },

            onSaveDialogHidden: function() {
                this.stopListening(this.children.editIndexDialog, "indexSaved", this.fetchIndexesCollection);
                this.stopListening(this.children.editIndexDialog, "hidden", this.onSaveDialogHidden);
            },

            fetchIndexesCollection: function() {
                this.model.wizard.trigger('refreshIndex');
            },

            events: {
                'click #indexRefreshLink': function() {
                    this.$('#index_placeholder .shared-controls-syntheticselectcontrol').html(this.children.waitSpinner.render().el);
                    this.model.wizard.trigger('refreshIndex');
                    this.children.waitSpinner.start();
                },
                'click .create-index-link': function() {
                    if (this.children.waitSpinnerArchives){
                        this.children.waitSpinnerArchives.$el.show();
                        this.children.waitSpinnerArchives.start();
                    }
                    this.showAddEditDialog();
                }
            },

            faqList: [
                {
                    question: _('How do indexes work?').t(),
                    answer: _('Indexes are repositories for data in the Splunk platform, and reside in flat files on the ' +
                    'Splunk platform instance known as the indexer. When the Splunk platform indexes raw event data, ' +
                    'it transforms the data into searchable events and stores those events in the index.').t()
                },
                {
                    question: _('How do I know when to create or use multiple indexes?').t(),
                    answer: _('When you add data to the Splunk platform, consider creating indexes for specific purposes ' +
                    'or domains of data that might require different access privileges, retention periods, or logical ' +
                    'groupings. For optimal performance, limit the number of source types contained within an index to ' +
                    'fewer than 20 if possible.').t()
                }
            ],

            render: function () {
                var appLink = route.docHelp(
                    this.model.application.get('root'),
                    this.model.application.get('locale'),
                    'learnmore.adddata.input.appcontext'
                );
                var hostLink = route.docHelp(
                    this.model.application.get('root'),
                    this.model.application.get('locale'),
                    'learnmore.adddata.input.hosttext'
                );
                var indexLink = route.docHelp(
                    this.model.application.get('root'),
                    this.model.application.get('locale'),
                    'learnmore.adddata.input.indextext'
                );

                var indexesLink = route.manager(
                        this.model.application.get('root'),
                        this.model.application.get('locale'),
                        this.model.application.get('app'),
                        ['data','indexes', '_new'],
                        {data: {action: 'edit'}}
                    ),
                    template = this.compiledTemplate({
                        appLink: appLink,
                        hostLink: hostLink,
                        indexLink: indexLink,
                        indexesLink: indexesLink,
                        canCreateIndex: this.model.user.canEditIndexes() && !this.isStackmakr}),
                    inputType = this.model.wizard.get('inputType');
                this.$el.html(template);
                this.$el.append(this.children.faq.render().el);
                this.$('.header').append(this.children.flashMessages.render().el);
                if (this.children.waitSpinnerArchives){
                    this.$('.newindex_link').append(this.children.waitSpinnerArchives.render().el);
                    this.children.waitSpinnerArchives.$el.hide();
                }

                // Sourcetype
                if ((!this.model.wizard.isPreviewEnabled() && !this.model.wizard.isWindowsInput()) || this.model.wizard.isDirectory()) {
                    this.$('#sourcetype_placeholder').html(this.children.sourcetypeSwitch.render().el);
                    this.$('#sourcetype_placeholder').append(this.children.sourcetype.render().el);
                    this.$('#sourcetype_placeholder').append(this.children.sourcetypeManual.render().el);
                    this.$('#sourcetype_placeholder').append(this.children.sourcetypeCategory.render().el);
                    this.$('#sourcetype_placeholder').append(this.children.sourcetypeDescription.render().el);
                    this.$('.sourcetype-subheader').show();
                } else {
                    this.$('.sourcetype-subheader').hide();
                }
                this.updateSourcetypeVisibility();

                // App Context
                if (this.model.wizard.isLocalMode() && this.model.user.canUseApps()) {
                    this.$('#context_placeholder').html(this.children.context.render().el);
                    this.$('.appcontext-subheader').show();
                } else {
                    this.$('.appcontext-subheader').hide();
                }

                // Host
                if (this.model.wizard.isForwardMode() || inputType === 'http') {
                    this.$('.host-subheader').hide();
                } else {
                    this.$('.host-subheader').show();
                    if (inputType === 'file_monitor' || inputType === 'file_oneshot' || this.model.wizard.isUploadMode()) {
                        this.$('#host_placeholder').html(this.children.hostSwitch.render().el);
                        this.$('#host_placeholder').append(this.children.host.render().el);
                        this.$('#host_placeholder').append(this.children.hostRegex.render().el);
                        this.$('#host_placeholder').append(this.children.hostSegment.render().el);
                        this.updateFileHostVisibility();
                    } else if (inputType === 'tcp' || inputType === 'udp') {
                        this.$('#host_placeholder').html(this.children.hostSwitchNet.render().el);
                        this.$('#host_placeholder').append(this.children.host.render().el);
                        this.updateNetHostVisibility();
                    } else {
                        this.$('#host_placeholder').html(this.children.host.render().el);
                    }
                }

                // Index
                this.updateIndexControl();
                if (this.model.wizard.get('inputType') === 'http') {
                    this.updateAvailableIndexes();
                }

                this.delegateEvents();
                return this;
            }
        });
    }
);
