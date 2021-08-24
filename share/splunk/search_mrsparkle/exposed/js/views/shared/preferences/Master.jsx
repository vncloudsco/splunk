import React from 'react';
import $ from 'jquery';
import _ from 'underscore';
import ReactAdapterBase from 'views/ReactAdapterBase';
import SplunkdUtils from 'util/splunkd_utils';
import configModel from 'models/config';
import PreferencesDialog from './PreferencesDialog';

export default ReactAdapterBase.extend({
    moduleId: module.id,
    /**
     * @param {Object} options {
     *     model: {
     *         user: <models.shared.User>
     *         application: <models.shared.Application>
     *     },
     *     collection: {
     *         appsVisible: <collections.services.AppLocals> Collection of all enabled and visible apps for this user.
     *         searchBNFs: (Optional) <collections.services.configs.SearchBNFs>
     *     }
     */
    initialize(options) {
        ReactAdapterBase.prototype.initialize.apply(this, options);
        const defaultOptions = {
            showAppSelection: true,
        };
        this.options = _.extend({}, defaultOptions, this.options);
        this.model.inmem = this.model.user.clone();

        this.handleApply = this.handleApply.bind(this);
        this.handleClose = this.handleClose.bind(this);
    },

    handleApply(dialog) {
        // Save model and close the dialog
        return this.model.inmem.save({}, {
            success: function success() {
                this.model.user.fetch({
                    url: SplunkdUtils.fullpath(this.model.user.get(this.model.user.idAttribute)),
                    data: {
                        app: this.model.application.get('app'),
                        owner: this.model.application.get('owner'),
                    },
                });

                // SPL-181033: set SERVER_ZONEINFO after user preference
                // changed.
                $.ajax({
                    url: SplunkdUtils.fullpath('/config/SERVER_ZONEINFO'),
                    type: 'GET',
                    cache: false,
                    contentType: false,
                    processData: false,
                }).done((response) => {
                    configModel.set('SERVER_ZONEINFO', response);
                });

                dialog.close();
            }.bind(this),
        });
    },

    handleClose() {
        _.delay(() => this.remove(), 300);
    },

    getComponent() {
        return (
            <PreferencesDialog
                showAppSelection={this.options.showAppSelection}
                isLite={this.model.serverInfo.isLite()}
                model={this.model}
                collection={this.collection}
                onApply={this.handleApply}
                onClose={this.handleClose}
            />
        );
    },
});
