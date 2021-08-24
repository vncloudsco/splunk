/**
 * @author jsolis
 * @date 7/11/17
 */
import $ from 'jquery';
import _ from 'underscore';
import BaseView from 'views/Base';
import ControlGroup from 'views/shared/controls/ControlGroup';
import FlashMessages from 'views/shared/FlashMessages';
import SyntheticSelectControl from 'views/shared/controls/SyntheticSelectControl';
import 'bootstrap.tooltip';
import '../cloud/SelfStorageInput.pcss';

export default BaseView.extend({
    moduleId: module.id,
    initialize(options = {}) {
        BaseView.prototype.initialize.call(this, options);
        if (!options.isNew) {
            this.model.addEditIndexModel.set({
                'archiver.selfStorageBucketPath': this.model.entity.getBucketPath(),
            });
        }

        this.children.noSelfStorageflashMessage = new FlashMessages();
        this.children.noSelfStorageflashMessage.flashMsgCollection.push({
            type: 'warning',
            html: _(`Events older than ${this.model.addEditIndexModel.get('frozenTimePeriodInDays')}
        day(s), will be deleted.`).t(),
        });

        $.when(this.options.deferreds.bucketList).done(() => {
            let bucketItemsList = [];
            let buckets = [{
                label: _('Please select an option').t(),
                value: '',
            }];

            if (this.collection.bucketList.length > 0) {
                bucketItemsList = _.map(this.collection.bucketList.models, (model) => {
                    const name = model.entry.get('name');
                    return { label: name, value: name };
                });
            }

            if (!_.isUndefined(bucketItemsList)) {
                buckets = _.union(buckets, bucketItemsList);
            }

            this.children.bucketListSelect = new SyntheticSelectControl({
                model: this.model.addEditIndexModel,
                modelAttribute: 'archiver.selfStorageBucketPath',
                toggleClassName: 'btn',
                items: buckets,
                popdownOptions: { attachDialogTo: 'body' },
            });

            this.children.bucketList = new ControlGroup({
                className: 'control-group',
                controlClass: 'controls-block',
                controls: [this.children.bucketListSelect],
                label: _('Self storage location').t(),
                help: `<a href='${this.model.stateModel.get('selfStorageLocationsUrl')}' class='help-link'
                          target='_blank'> ${_('Edit self storage locations').t()} <i class='icon-external'></i></a>`,
            });

            this.listenTo(this.children.bucketListSelect, 'change', this.onSelfStorageBucketSelected);
        });

        this.listenTo(this.model.stateModel, 'change:dynamicStorageOption', () => {
            if (this.model.stateModel.get('dynamicStorageOption') === this.options.selfStorageConst) {
                this.debouncedRender();
            }
        });
        this.listenTo(this.model.stateModel, 'change:selfStorageConfigured', this.debouncedRender);
    },

    onSelfStorageBucketSelected(selectedValue = '') {
        this.trigger('onSelfStorageBucketSelected', selectedValue);
    },

    render() {
        if (!this.el.innerHTML) {
            this.$el.html(this.compiledTemplate({
                selfStorageLocationsUrl: this.model.stateModel.get('selfStorageLocationsUrl'),
            }));

            this.children.noSelfStorageflashMessage.render().appendTo(
                this.$('.data-will-be-deleted-msg-placeholder'));

            $.when(this.options.deferreds.bucketList).done(() => {
                if (this.collection.bucketList.length > 0) {
                    this.children.bucketList.render().appendTo(this.$('.bucket-list-placeholder'));
                }
            });
        }

        if (this.model.stateModel.get('dynamicStorageOption') === this.options.selfStorageConst) {
            this.$el.find('.bucket-list-placeholder').show();
            this.$el.find('.data-will-be-deleted-msg-placeholder').hide();
        } else {
            this.$el.find('.bucket-list-placeholder').hide();
            if (!this.options.isNew) {
                this.$el.find('.data-will-be-deleted-msg-placeholder').show();
            }
        }

        if (this.model.stateModel.get('selfStorageConfigured') ||
            this.model.stateModel.get('dynamicStorageOption') !== this.options.selfStorageConst) {
            this.$el.find('.no-self-storage-msg-placeholder').hide();
        } else {
            this.$el.find('.no-self-storage-msg-placeholder').show();
        }

        return this;
    },

    template: `
        <div class='self-storage-placeholder'></div>
        <div class='hide no-self-storage-msg-placeholder alert-warning alert'>
            <i class='icon-alert'></i>
            <div class='strong'><%- _('No self storage locations have been created yet').t() %></div>
           <a href='<%- selfStorageLocationsUrl %>' class='help-link' target='_blank'>
    ${_('Create a self storage location').t()}</a> <i class='icon-external'></i>
        </div>
        <div class='hide data-will-be-deleted-msg-placeholder'></div>
        <div class='hide bucket-list-placeholder'></div>
    `,

});
