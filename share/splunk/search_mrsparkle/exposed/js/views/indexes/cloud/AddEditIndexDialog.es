/**
 * @author lbudchenko/jszeto/jsolis
 * @date 2/11/15
 */

import $ from 'jquery';
import _ from 'underscore';
import SelfStorageInput from 'views/indexes/cloud/SelfStorageInput';
import DynamicDataOptions from 'views/indexes/cloud/dynamic_data_storage/Master';
import ControlGroup from 'views/shared/controls/ControlGroup';
import FlashMessages from 'views/shared/FlashMessages';
import Modal from 'views/shared/Modal';
import Spinner from 'views/shared/waitspinner/Master';
import route from 'uri/route';
import splunkutil from 'splunk.util';
import '../shared/AddEditIndexView.pcss';

export default Modal.extend({
    moduleId: module.id,
    className: `${Modal.CLASS_NAME} ${Modal.CLASS_MODAL_WIDE} indexes-modal`,

    initialize(options = {}) {
        Modal.prototype.initialize.call(this, options);
        _(options).defaults({ isNew: true });
        // deferreds
        this.deferreds = options.deferreds || {};

        this.isArchiverAppInstalled = !_.isUndefined(this.model.stateModel.get('isArchiverAppInstalled'));
        this.isS2 = this.isS2();

        // set temporary self storage toggle to actual value from backend
        this.model.stateModel.set('selfStorageLocationsUrl', route.dynamic_data(
            this.model.application.get('root'),
            this.model.application.get('locale')));

        // Initialize the working model
        if (options.isNew) {   // new mode
            this.addEditIndexModel = new this.options.archiverModelClass({ // eslint-disable-line new-cap
                isNew: true,
                dataType: 'event',
            });

            if (!this.isArchiverAppInstalled && !this.model.controller.get('singleInstance')) {
                this.addEditIndexModel.set('maxIndexSize', 0xFFFFFFFF);
                this.addEditIndexModel.set('maxIndexSizeFormat', 'MB');
            }
        } else {  // edit mode
            const maxIndexSizeObject = this.isS2 || this.isArchiverAppInstalled ?
                this.formatSize(this.model.entity.entry.content.get('maxGlobalRawDataSizeMB')) :
                this.formatSize(this.model.entity.entry.content.get('maxTotalDataSizeMB'));
            const maxIndexSizeValue = maxIndexSizeObject.size;
            const maxIndexSizeFormatValue = maxIndexSizeObject.format;
            const frozenTimePeriodInDaysValue = Math.floor(
                this.model.entity.entry.content.get('frozenTimePeriodInSecs') / (60 * 60 * 24));

            this.addEditIndexModel = new this.options.archiverModelClass({ // eslint-disable-line new-cap
                id: this.model.entity.entry.get('name'),
                name: this.model.entity.entry.get('name'),
                isNew: false,
                maxIndexSize: maxIndexSizeValue,
                maxIndexSizeFormat: maxIndexSizeFormatValue,
                frozenTimePeriodInDays: frozenTimePeriodInDaysValue,
                'archiver.selfStorageBucket':
                    this.model.entity.entry.content.get('archiver.selfStorageBucket'),
                'archiver.selfStorageProvider':
                    this.model.entity.entry.content.get('archiver.selfStorageProvider'),
                'archiver.coldStorageProvider':
                    this.model.entity.entry.content.get('archiver.coldStorageProvider'),
                'archiver.coldStorageRetentionPeriod':
                    this.model.entity.entry.content.get('archiver.coldStorageRetentionPeriod'),
            });

            if (this.addEditIndexModel.get('archiver.coldStorageProvider')) {
                this.model.stateModel.set('dynamicStorageOption', this.options.ARCHIVE);
            } else if (this.addEditIndexModel.get('archiver.selfStorageProvider')) {
                this.model.stateModel.set('dynamicStorageOption', this.options.SELF_STORAGE);
            } else {
                this.model.stateModel.set('dynamicStorageOption', this.options.NONE);
            }

            this.deferreds.fetchIndex = $.Deferred();
            $.when(this.addEditIndexModel.fetch()).done(() => {
                this.deferreds.fetchIndex.resolve();
                this.toggleSave();
            });
        }

        // Self storage input
        if (this.isArchiverAppInstalled) {
            this.children.selfStorageInput = new SelfStorageInput({
                isNew: options.isNew,
                deferreds: this.deferreds,
                collection: {
                    bucketList: this.collection.bucketList,
                },
                model: {
                    entity: this.model.entity,
                    application: this.model.application,
                    stateModel: this.model.stateModel,
                    addEditIndexModel: this.addEditIndexModel,
                },
                modalFooter: this.$(Modal.FOOTER_SELECTOR),
                selfStorageConst: this.options.SELF_STORAGE,
            });
            this.listenTo(
              this.children.selfStorageInput,
              'onSelfStorageBucketSelected',
              this.onSelfStorageBucketSelected);

            // Enable/disable DynamicDataArchive feature
            this.toggleArchiveControls();
        }

        // Create flash messages view
        this.children.flashMessagesView = new FlashMessages({
            model: this.addEditIndexModel,
            helperOptions: {
                postProcess: this.postProcess,
            } });

        /*
         ---- Create the form controls -----
        */
        this.children.inputName = new ControlGroup({
            controlType: 'Text',
            controlOptions: {
                modelAttribute: 'name',
                model: this.addEditIndexModel,
            },
            controlClass: 'controls-block',
            label: _('Index name').t(),
            help: '',
        });

        // Data Type
        this.children.switchDataType = new ControlGroup({
            controlType: 'SyntheticRadio',
            controlOptions: {
                modelAttribute: 'dataType',
                model: this.addEditIndexModel,
                items: [
                    {
                        label: _('Events').t(),
                        icon: 'event',
                        value: 'event',
                    },
                    {
                        label: _('Metrics').t(),
                        icon: 'metric',
                        value: 'metric',
                    },
                ],
                save: false,
            },
            controlClass: 'controls-halfblock',
            label: _('Index Data Type').t(),
            help: _('The type of data to store (event-based or metrics).').t(),
        });

        // Defining byte format dropdown items.
        const byteFormatOptions = [{
            value: 'MB',
            label: _('MB').t(),
        }, {
            value: 'GB',
            label: _('GB').t(),
            description: _('1GB = 1024MB').t(),
        }, {
            value: 'TB',
            label: _('TB').t(),
            description: _('1TB = 1024GB').t(),
        }];
        // Set correct label and help text.
        let inputMaxSizeLabel = _('Max raw data size').t();
        let inputMaxSizeHelp = _(`Maximum aggregated size of raw data (uncompressed) contained in index.
                Set this to 0 if you want unlimited.`).t();
        if (this.model.controller.get('singleInstance') && !this.isS2 && !this.isArchiverAppInstalled) {
            inputMaxSizeLabel = _('Max data size').t();
            inputMaxSizeHelp = _(`Maximum aggregated size of data contained in index.
            Set this to 0 if you want unlimited.`).t();
        }

        this.children.inputMaxSize = new ControlGroup({
            label: inputMaxSizeLabel,
            help: inputMaxSizeHelp,
            controls: [{
                type: 'Text',
                options: {
                    modelAttribute: 'maxIndexSize',
                    model: this.addEditIndexModel,
                },
            }, {
                type: 'SyntheticSelect',
                options: {
                    menuWidth: 'narrow',
                    modelAttribute: 'maxIndexSizeFormat',
                    model: this.addEditIndexModel,
                    items: byteFormatOptions,
                    toggleClassName: 'btn',
                    popdownOptions: { attachDialogTo: this.$el },
                },
            }],
        });

        // Input Retention
        this.children.inputRetention = new ControlGroup({
            controlType: 'Text',
            controlOptions: {
                modelAttribute: 'frozenTimePeriodInDays',
                model: this.addEditIndexModel,
            },
            controlClass: 'controls-block',
            label: _('Searchable time (days)').t(),
            help: _('Number of days the data is searchable').t(),
        });

        // Spinner
        this.children.spinner = new Spinner({
            color: 'green',
            size: 'medium',
            frameWidth: 19,
        });

        this.listenTo(this.model.stateModel, 'change:selfStorageConfigured', this.debouncedRender);
        this.listenTo(this.model.stateModel, 'change:dynamicStorageOption',
            this.showSelectedStorageView);
        this.listenTo(this.model.stateModel, 'change:archiverConfigSet', () => {
            this.toggleArchiveControls();
            this.$el.find('.dynamic-data-options').replaceWith(this.children.dynamicDataOptions.render().el);
            this.$el.find('.SelfStorage').replaceWith(this.children.selfStorageInput.render().el);
        });
    },

    events: $.extend({}, Modal.prototype.events, {
        'click .btn-primary'() { // eslint-disable-line object-shorthand
            this.onSubmit();
        },
    }),

    // This should be moved up to the page controller.
    // For now I am trying to minimize potential breakage.
    isS2() {
        return this.collection.entities.some(entity => entity.entry.content.get('remotePath'));
    },

    toggleArchiveControls() {
        this.hasArchiveLicense = this.model.stateModel.get('isDataArchiveEnabled');
        // Convert maxArchiveRetention from seconds to days for readability
        this.maxArchiveRetentionDays = this.model.stateModel.get('maxArchiveRetention') ?
            Math.floor(this.model.stateModel.get('maxArchiveRetention') / (3600 * 24)) : 0;
        if (this.options.isNew) {
            if (this.hasArchiveLicense) {
                this.model.stateModel.set('dynamicStorageOption', this.options.ARCHIVE);
            } else {
                this.model.stateModel.set('dynamicStorageOption', this.options.NONE);
            }
            this.model.stateModel.set('archiveRetentionUnit', 'years');
        } else {
            this.model.stateModel.set('archiveRetentionUnit', 'days');
        }
        // Show the dynamic storage options only for users with 'indexes_edit capability and
        // only for S2 cloud customers (indirectly checked by is archiverapp installed)
        if (this.model.user.canEditIndexes() && this.isArchiverAppInstalled) {
            this.children.dynamicDataOptions = new DynamicDataOptions({
                model: {
                    state: this.model.stateModel,
                    addEditIndexModel: this.addEditIndexModel,
                },
                constants: {
                    SELF_STORAGE: this.options.SELF_STORAGE,
                    ARCHIVE: this.options.ARCHIVE,
                    NONE: this.options.NONE,
                },
                archiveLicense: this.hasArchiveLicense,
                maxRetention: this.maxArchiveRetentionDays,
            });
        }
    },

    onSubmit() {
        if (!this.addEditIndexModel.set({}, { validate: true })) {
            return;
        }

        this.children.spinner.start();
        this.children.spinner.$el.show();

        // Copy addEditIndexModel attributes to this.modelToUpdate
        const maxIndexSize = this.formatSizeForSave(
            this.addEditIndexModel.get('maxIndexSize'),
            this.addEditIndexModel.get('maxIndexSizeFormat'));
        const frozenTimePeriodInSecsValue = this.addEditIndexModel.get('frozenTimePeriodInDays') *
            (60 * 60 * 24);
        const dataType = this.addEditIndexModel.get('dataType');

        this.modelToUpdate = this.addEditIndexModel;

        // Non-s2 single instance cloud: use maxTotalDataSizeMB
        if (this.model.controller.get('singleInstance') && !this.isS2 && !this.isArchiverAppInstalled) {
            this.modelToUpdate.entry.content.set({
                name: this.addEditIndexModel.get('name'),
                datatype: dataType,
                maxGlobalRawDataSizeMB: 0,
                maxTotalDataSizeMB: maxIndexSize,
                maxGlobalDataSizeMB: 0,
                frozenTimePeriodInSecs: frozenTimePeriodInSecsValue,
            });
        } else {
            // S2 single instance cloud or cloud stack: use maxGlobalRawDataSizeMB
            this.modelToUpdate.entry.content.set({
                name: this.addEditIndexModel.get('name'),
                datatype: dataType,
                maxGlobalRawDataSizeMB: maxIndexSize,
                maxTotalDataSizeMB: 0,
                maxGlobalDataSizeMB: 0,
                frozenTimePeriodInSecs: frozenTimePeriodInSecsValue,
            });
        }

        // add the appropriate disable flag when storage type was changed from archive/SS to none.
        if (this.model.stateModel.get('dynamicStorageOption') === this.options.NONE) {
            if (this.modelToUpdate.entry.content.get('archiver.selfStorageProvider')) {
                this.modelToUpdate.entry.content.set('archiver.selfStorageDisable', true);
            } else if (this.modelToUpdate.entry.content.get('archiver.coldStorageProvider')) {
                this.modelToUpdate.entry.content.set('archiver.coldStorageDisable', true);
            }
        }

        if (this.model.stateModel.get('dynamicStorageOption') === this.options.SELF_STORAGE) {
            const selectedBucket = this.collection.bucketList.findByEntryName(
                this.addEditIndexModel.get('archiver.selfStorageBucketPath'));

            this.modelToUpdate.entry.content.set({
                'archiver.selfStorageBucket': selectedBucket.entry.content.get('awsBucketName') || '',
                'archiver.selfStorageBucketFolder': selectedBucket.entry.content.get('awsBucketFolder') || '',
                'archiver.selfStorageProvider': 'S3',
            });
            this.modelToUpdate.entry.content.unset('archiver.coldStorageProvider');
            this.modelToUpdate.entry.content.unset('archiver.coldStorageRetentionPeriod');
        } else {
            this.modelToUpdate.entry.content.unset('archiver.selfStorageBucket');
            this.modelToUpdate.entry.content.unset('archiver.selfStorageBucketFolder');
            this.modelToUpdate.entry.content.unset('archiver.selfStorageProvider');

            if (this.model.stateModel.get('dynamicStorageOption') === this.options.ARCHIVE) {
                this.modelToUpdate.entry.content.set({
                    'archiver.coldStorageProvider':
                        this.addEditIndexModel.getColdStorageProvider(),
                    'archiver.coldStorageRetentionPeriod': this.getArchiveRetentionInDays(),
                });
            }
        }

        $.when(this.modelToUpdate.save()).done(() => {
            this.trigger('entitySaved', this.modelToUpdate);
            this.hide();
            this.children.spinner.stop();
        }).fail(() => {
            this.model.stateModel.set('entitySaved', false);
            this.children.spinner.$el.hide();
            this.children.spinner.stop();
        });
    },

    showSelectedStorageView() {
        const storageOption = this.model.stateModel.get('dynamicStorageOption');
        if (storageOption) {
            switch (storageOption) {
                case this.options.ARCHIVE:
                    this.addEditIndexModel.set('archiver.coldStorageProvider',
                        this.addEditIndexModel.getColdStorageProvider());
                    if (this.children.selfStorageInput) {
                        this.children.selfStorageInput.$el.hide();
                    }
                    break;
                case this.options.SELF_STORAGE:
                    this.addEditIndexModel.unset('archiver.coldStorageProvider');
                    if (this.isArchiverAppInstalled) {
                        this.children.selfStorageInput.$el.show();
                    }
                    break;
                default:
                    this.addEditIndexModel.unset('archiver.coldStorageProvider');
                    if (this.children.selfStorageInput) {
                        this.children.selfStorageInput.$el.hide();
                    }
                    break;
            }
        }
    },

    getArchiveRetentionInDays() {
        const retentionNumber = parseInt(
            this.addEditIndexModel.get('archiver.coldStorageRetentionPeriod'), 10);
        const retentionUnit = this.model.stateModel.get('archiveRetentionUnit');
        switch (retentionUnit) {
            case 'years':
                return retentionNumber * 365;
            case 'months':
                return retentionNumber * 30;
            default:
                return retentionNumber;
        }
    },

    onSelfStorageBucketSelected(selectedValue = '') {
        this.enableDisablePrimaryBtn(selectedValue);
    },

    enableDisablePrimaryBtn(selectedValue = '') {
        if (_.isEmpty(selectedValue)) {
            this.$(Modal.FOOTER_SELECTOR).find('.btn-primary').addClass('disabled').prop('disabled', true);
        } else {
            this.$(Modal.FOOTER_SELECTOR).find('.btn-primary').removeClass('disabled').prop('disabled', false);
        }
    },

    toggleSave() {
        if (this.model.controller.get('singleInstance') || this.model.controller.get('cloudLight')) {
            this.enableDisablePrimaryBtn('show');
        } else if (!this.options.isNew && this.deferreds.fetchIndex.state() !== 'resolved') {
            this.enableDisablePrimaryBtn();
        } else if (this.isArchiverAppInstalled
                 && this.model.stateModel.get('dynamicStorageOption') === this.options.SELF_STORAGE) {
            const selectedValue = this.addEditIndexModel.get('archiver.selfStorageBucketPath');
            if (!_.isEmpty(selectedValue) && this.collection.bucketList.length === 0) {
                // there is a selected value but either bucketlists need to be configured
                // or the dynamic-data-self-storage-app needs to be shared globally
                // disable submit button
                this.enableDisablePrimaryBtn();
            } else {
                this.enableDisablePrimaryBtn('show');
            }
        } else {
            this.enableDisablePrimaryBtn('show');
        }
    },

    formatSize(inputSize, inputFormat) {
        let result = {
            size: inputSize,
            format: inputFormat || 'MB',
        };
        if (!isNaN(inputSize)) {
            const inputSizeGB = inputSize / 1024;
            const inputSizeTB = inputSizeGB / 1024;
            const isInputSizeMB = inputSizeGB.toString().indexOf('.') !== -1;
            const isInputSizeGB = inputSizeTB.toString().indexOf('.') !== -1;
            if (!isInputSizeGB) {
                result = {
                    size: inputSizeTB,
                    format: 'TB',
                };
            } else if (!isInputSizeMB) {
                result = {
                    size: inputSizeGB,
                    format: 'GB',
                };
            }
        }
        return result;
    },

    formatSizeForSave(inputSize, inputFormat) {
        let result = inputSize;
        if (!isNaN(inputSize)) {
            if (inputFormat === 'TB') {
                result *= 1048576;
            } else if (inputFormat === 'GB') {
                result *= 1024;
            }
            // Ensure input is an integer.
            if (result.toString().indexOf('.') !== -1) {
                result = Math.floor(result);
            }
        }
        return result;
    },

    postProcess(messages) {
        if (messages.length) {
            messages[0].set({ html: _.unescape(messages[0].get('html')) });
        }
        return messages;
    },

    render() {
        if (!this.el.innerHTML) {
            this.$el.html(Modal.TEMPLATE);
            this.$(Modal.HEADER_TITLE_SELECTOR).html(
                this.options.isNew ? _('New Index').t() :
                    splunkutil.sprintf(_('Edit Index: %s').t(),
                        this.model.entity.entry.get('name')));
            this.$(Modal.BODY_SELECTOR).show();
            this.$(Modal.BODY_SELECTOR).append(Modal.FORM_HORIZONTAL);
            this.$(Modal.BODY_FORM_SELECTOR).html(this.compiledTemplate({ model: this.model }));
            this.children.flashMessagesView.render().appendTo(this.$('.flash-messages-view-placeholder'));

            if (this.options.isNew) {
                this.children.inputName.render().appendTo(this.$('.name-placeholder'));
                this.children.switchDataType.render().appendTo(this.$('.data-type-placeholder'));
            }

            if (this.isArchiverAppInstalled || this.model.controller.get('singleInstance')) {
                this.children.inputMaxSize.render().appendTo(this.$('.max-size-placeholder'));
            }
            this.children.inputRetention.render().appendTo(this.$('.retention-placeholder'));
            if (this.addEditIndexModel.get('frozenTimePeriodInDays') === 0) {
                this.children.inputRetention.setHelpText(_('0 means indefinite retention days.').t());
            }
            if (this.children.dynamicDataOptions) {
                this.children.dynamicDataOptions.render().appendTo(this.$('.dynamic-data-options'));
            }

            if (this.children.selfStorageInput) {
                this.children.selfStorageInput.render().appendTo(this.$('.SelfStorage'));
            }

            this.showSelectedStorageView();

            this.$(Modal.FOOTER_SELECTOR).append(this.children.spinner.render().el);
            this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);
            this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_SAVE);
            this.children.spinner.$el.hide();
        }

        this.toggleSave();

        return this;
    },

    template: `
        <div class='flash-messages-view-placeholder'></div>
        <div class='name-placeholder'></div>
        <div class="data-type-placeholder"></div>
        <div class='size-format-placeholder max-size-placeholder'></div>
        <div class='retention-placeholder'></div>
        <div class='dynamic-data-options'></div>
    `,
});
