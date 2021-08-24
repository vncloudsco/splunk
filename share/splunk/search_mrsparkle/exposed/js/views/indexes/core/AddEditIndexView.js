/**
 * @author jszeto,
 * @author ecarillo
 * @date 4/24/15
 */

define([
    'jquery',
    'underscore',
    'module',
    'models/indexes/AddEditIndex',
    'views/shared/FlashMessages',
    'views/Base',
    'views/shared/controls/ControlGroup',
    'views/shared/controls/SyntheticSelectControl',
    'views/indexes/shared/rollup/js/RollupSettings',
    'splunk.util',
    'uri/route',
    'views/indexes/shared/AddEditIndexView.pcss'
    ],
    function(
        $,
        _,
        module,
        AddEditIndexModel,
        FlashMessages,
        BaseView,
        ControlGroup,
        SyntheticSelectControl,
        RollupSettings,
        splunkutil,
        route,
        css
    ){
    return BaseView.extend({
        moduleId: module.id,
        /**
         * @constructor
         * @memberOf views
         * @name AddEditIndexView
         * @extends {views.BaseView}
         * @description A view displaying components for adding/editing an index
         *
         * @param {Object} options
         * @param {Object} options.model The model supplied to this class
         * @param {Object} options.collection The collection supplied to this class
         */
        className: 'indexes-modal',
        initialize: function(options) {
            BaseView.prototype.initialize.call(this, arguments);
            options = options || {};
            _(options).defaults({isNew:true});
            options.isNew = this.model.content.get('isNew');
            this.isMetrics = this.model.entity.getDataType() === 'metric' || this.model.entity.getDataType() === 'rollup';
            this._buildLayout(options);
        },

        _buildLayout: function(options) {
            var appItems = [];
            if (this.model.user.canUseApps()) {
                // Filter out the app list to hold apps the user can write to
                this.collection.appLocals.each(function(model){
                    if (model.entry.acl.get("can_write")) {
                        appItems.push({
                            label: model.entry.content.get('label'),
                            value: model.entry.get('name')
                        });
                    }
                });
            }

            // Defining byte format dropdown items.
            var byteFormatOptions = [{
                value: 'MB',
                label: _('MB').t()
            },{
                value: 'GB',
                label: _('GB').t(),
                description: _('1GB = 1024MB').t()
            },{
                value: 'TB',
                label: _('TB').t(),
                description: _('1TB = 1024GB').t()
            }];

            // Units for time period dropdown
            var periodFormatOptions = [{
                value: 'Seconds',
                label: _('Seconds').t()
            },{
                value: 'Minutes',
                label: _('Minutes').t()
            },{
                value: 'Hours',
                label: _('Hours').t()
            },{
                value: 'Days',
                label: _('Days').t()
            }];

            // Create flash messages view
            this.children.flashMessagesView = new FlashMessages({
                model: [this.model.addEditIndexModel, this.model.entity],
                helperOptions: {
                    removeServerPrefix: true,
                    postProcess: this.postProcess
                }
            });

            // Create the form controls
            this.children.inputName = new ControlGroup({
                controlType: 'Text',
                controlOptions: {
                    modelAttribute: 'name',
                    model: this.model.addEditIndexModel
                },
                label: _('Index Name').t(),
                help:_("Set index name (e.g., INDEX_NAME). Search using index=INDEX_NAME.").t()
            });
            this.children.inputHomePath = new ControlGroup({
                controlType: 'Text',
                controlOptions: {
                    modelAttribute: 'homePath',
                    model: this.model.addEditIndexModel,
                    placeholder: 'optional'
                },
                label: _('Home Path').t(),
                help:_("Hot/warm db path. Leave blank for default ($SPLUNK_DB/INDEX_NAME/db).").t(),
                enabled: options.isNew
            });
            this.children.inputColdPath = new ControlGroup({
                controlType: 'Text',
                controlOptions: {
                    modelAttribute: 'coldPath',
                    model: this.model.addEditIndexModel,
                    placeholder: 'optional'
                },
                label: _('Cold Path').t(),
                help:_("Cold db path. Leave blank for default ($SPLUNK_DB/INDEX_NAME/colddb).").t(),
                enabled: options.isNew
            });
            this.children.inputThawedPath = new ControlGroup({
                controlType: 'Text',
                controlOptions: {
                    modelAttribute: 'thawedPath',
                    model: this.model.addEditIndexModel,
                    placeholder: 'optional'
                },
                label: _('Thawed Path').t(),
                help:_("Thawed/resurrected db path. Leave blank for default ($SPLUNK_DB/INDEX_NAME/thaweddb).").t(),
                enabled: options.isNew
            });
            this.children.inputEnableDataIntegrity = new ControlGroup({
                controlType: 'SyntheticRadio',
                controlOptions: {
                    modelAttribute: 'enableDataIntegrityControl',
                    model: this.model.addEditIndexModel,
                    items: [
                        {
                            label: "Enable",
                            value: 1
                        },
                        {
                            label: "Disable",
                            value: 0
                        }
                    ]
                },
                label: _('Data Integrity Check').t(),
                help: _("Enable this if you want Splunk to compute hashes on every slice of your data for the purpose of data integrity.").t()
            });
            this.children.inputMaxIndexSize = new ControlGroup({
                label: _('Max Size of Entire Index').t(),
                help:_("Maximum target size of entire index.").t(),
                controlClass: 'input-append',
                controls: [{
                    type: 'Text',
                    options: {
                        modelAttribute: 'maxIndexSize',
                        model: this.model.addEditIndexModel
                    }
                },{
                    type: 'SyntheticSelect',
                    options: {
                        menuWidth: 'narrow',
                        modelAttribute: 'maxIndexSizeFormat',
                        model: this.model.addEditIndexModel,
                        items: byteFormatOptions,
                        toggleClassName: 'btn'
                    }
                }]
            });
            this.children.inputMaxBucketSize = new ControlGroup({
                label: _('Max Size of Hot/Warm/Cold Bucket').t(),
                help:_("Maximum target size of buckets. Enter 'auto_high_volume' for high-volume indexes.").t(),
                controlClass: 'input-append',
                controls: [{
                    type: 'Text',
                    options: {
                        modelAttribute: 'maxBucketSize',
                        model: this.model.addEditIndexModel
                    }
                },{
                    type: 'SyntheticSelect',
                    options: {
                        menuWidth: 'narrow',
                        modelAttribute: 'maxBucketSizeFormat',
                        model: this.model.addEditIndexModel,
                        items: byteFormatOptions,
                        toggleClassName: 'btn'
                    }
                }]
            });
            this.children.inputFrozenPath = new ControlGroup({
                controlType: 'Text',
                controlOptions: {
                    modelAttribute: 'frozenPath',
                    model: this.model.addEditIndexModel,
                    placeholder: 'optional'
                },
                label: _('Frozen Path').t(),
                help:_("Frozen bucket archive path. Set this if you want Splunk to automatically archive frozen buckets.").t()
            });
            // Hide in lite.
            if (this.model.user.canUseApps()){
                this.children.selectApp = options.isNew ? new ControlGroup({
                    label: _("App").t(),
                    controlType: 'SyntheticSelect',
                    controlOptions: {
                        modelAttribute: "app",
                        model: this.model.addEditIndexModel,
                        toggleClassName: 'btn',
                        menuWidth: 'narrow',
                        items: appItems,
                        popdownOptions: {
                            attachDialogTo: '.modal:visible',
                            scrollContainer: '.modal:visible .modal-body:visible'
                        }
                    }
                }) : new ControlGroup({
                    controlType: 'Text',
                    controlOptions: {
                        modelAttribute: 'app',
                        model: this.model.addEditIndexModel
                    },
                    label: _('App').t(),
                    enabled: false
                });
            }

            if (
                !this.options.isNew &&
                this.isMetrics &&
                this.model.rollup.get('hasViewCapability')
            ) {
                this.children.rollupSettings = new RollupSettings({
                    model: {
                        content: this.model.content,
                        rollup: this.model.rollup,
                    },
                    collection: {
                        dimensions: this.collection.dimensions,
                        metrics: this.collection.metrics,
                        indexes: this.collection.indexes,
                    }
                });
            }

            // Mini-TSIDX controls
            var docRoute = route.docHelp(this.model.application.get("root"), this.model.application.get("locale"), 'learnmore.tsidx_reduction');
            this.children.switchTSDIXReduction = new ControlGroup({
                controlType: 'SyntheticRadio',
                controlOptions: {
                    modelAttribute: 'enableTsidxReduction',
                    model: this.model.addEditIndexModel,
                    items: [
                        {
                            label: _('Enable Reduction').t(),
                            value: true
                        },
                        {
                            label: _('Disable Reduction').t(),
                            value: false
                        }
                    ],
                    save: false
                },
                label: _('Tsidx Retention Policy').t(),
                help:_('<b>Warning</b>: Do not enable reduction without understanding the full implications. It is extremely difficult to rebuild reduced buckets. <a href="'+ docRoute +'" class="external" target="_blank" + title="' + _("Splunk help").t() + '">Learn More</a>').t()
            });

            this.children.switchDateType = new ControlGroup({
                controlType: 'SyntheticRadio',
                controlOptions: {
                    modelAttribute: 'dataType',
                    model: this.model.addEditIndexModel,
                    items: [
                        {
                            label: _('Events').t(),
                            icon: 'event',
                            value: 'event'
                        },
                        {
                            label: _('Metrics').t(),
                            icon: 'metric',
                            value: 'metric'
                        }
                    ],
                    save: false
                },
                label: _('Index Data Type').t(),
                help:_('The type of data to store (event-based or metrics).').t()
            });

            this.children.inputTSDIXReductionAge = new ControlGroup({
                label: _('Reduce tsidx files older than').t(),
                help:_("Age is determined by the latest event in a bucket.").t(),
                controlClass: 'input-append',
                controls: [{
                    type: 'Text',
                    options: {
                        modelAttribute: 'timePeriodInSecBeforeTsidxReduction',
                        model: this.model.addEditIndexModel
                    }
                },{
                    type: 'SyntheticSelect',
                    options: {
                        menuWidth: 'narrow',
                        modelAttribute: 'tsidxAgeFormat',
                        model: this.model.addEditIndexModel,
                        items: periodFormatOptions,
                        toggleClassName: 'btn',
                        popdownOptions: {detachDialog: true}
                    }
                }]

            });

            this.model.addEditIndexModel.on('change:enableTsidxReduction', this.toggleMiniTsidxSettings, this);
            this.model.addEditIndexModel.on('change:dataType', this.toggleVisibility, this);
        },

        postProcess: function(messages) {
            if (messages.length) {
                messages[0].set({'html': _.unescape(messages[0].get('html'))});
            }
            return messages;
        },

        // Toggles display of mini-tsidx configuration
        // based on the value of enableTsidxReduction
        toggleMiniTsidxSettings: function(model, value, options){
            if (value === true){
                this.children.inputTSDIXReductionAge.enable();
            }else{
                this.children.inputTSDIXReductionAge.disable();
            }
        },

        toggleVisibility: function() {
            this.isMetrics = this.model.addEditIndexModel.get('dataType') === 'metric' || this.model.addEditIndexModel.get('dataType') === 'rollup';
            if (this.isMetrics) {
                this.children.inputEnableDataIntegrity.hide();
                this.$('.section-storage-optimization').hide();
            } else {
                this.children.inputEnableDataIntegrity.show();
                this.$('.section-storage-optimization').show();
            }
        },

        render: function() {
            if (!this.el.innerHTML) {
                var template = _.template(this.template, {
                    _: _
                });
                this.$el.html(template);
            }
            this.children.flashMessagesView.render().appendTo(this.$(".flash-messages-view-placeholder"));
            if (this.model.content.get('isNew')) {
                this.children.inputName.render().appendTo(this.$(".name-placeholder"));
                this.children.switchDateType.render().appendTo(this.$(".data-type-placeholder"));
            }
            this.children.inputHomePath.render().appendTo(this.$(".home-path-placeholder"));
            this.children.inputColdPath.render().appendTo(this.$(".cold-path-placeholder"));
            this.children.inputThawedPath.render().appendTo(this.$(".thawed-path-placeholder"));
            this.children.inputEnableDataIntegrity.render().appendTo(this.$(".enable-data-integrity-placeholder"));
            this.children.inputMaxIndexSize.render().appendTo(this.$(".max-index-size-placeholder"));
            this.children.inputMaxBucketSize.render().appendTo(this.$(".max-bucket-size-placeholder"));
            this.children.inputFrozenPath.render().appendTo(this.$(".frozen-path-placeholder"));
            if (this.model.user.canUseApps()){
                this.children.selectApp.render().appendTo(this.$(".application-placeholder"));
            }
            if (this.children.rollupSettings) {
                this.children.rollupSettings.render().appendTo(this.$(".roll-up-settings-placeholder"));
            }

            this.children.switchTSDIXReduction.render().appendTo(this.$(".tsidx-reduction-switch-placeholder"));
            this.children.inputTSDIXReductionAge.render().appendTo(this.$(".tsidx-reduction-age-placeholder"));
            if (!this.model.addEditIndexModel.get('enableTsidxReduction')){
                this.children.inputTSDIXReductionAge.disable();
            }

            this.toggleVisibility();

            return this;
        },

        template: '\
            <p><strong><%- _("General Settings").t() %></strong></p>\
            <div class="flash-messages-view-placeholder"></div>\
            <div class="name-placeholder"></div>\
            <div class="data-type-placeholder"></div>\
            <div class="home-path-placeholder"></div>\
            <div class="cold-path-placeholder"></div>\
            <div class="thawed-path-placeholder"></div>\
            <div class="enable-data-integrity-placeholder"></div>\
            <div class="size-format-placeholder max-index-size-placeholder"></div>\
            <div class="size-format-placeholder max-bucket-size-placeholder"></div>\
            <div class="frozen-path-placeholder"></div>\
            <div class="application-placeholder"></div>\
            <div class="section-storage-optimization">\
                <p><strong><%- _("Storage Optimization").t() %></strong></p>\
                <div class="tsidx-reduction-switch-placeholder"></div>\
                <div class="size-format-placeholder tsidx-reduction-age-placeholder"></div>\
            </div>\
            <div class="roll-up-settings-placeholder"></div>\
            '
    });
});
