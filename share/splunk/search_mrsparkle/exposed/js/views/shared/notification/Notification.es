import React from 'react';
import ReactAdapterBase from 'views/ReactAdapterBase';
import Backbone from 'backbone';
import route from 'uri/route';
import Python3Notification from 'views/shared/notification/Python3Notification';

export default ReactAdapterBase.extend({
    moduleId: module.id,
    /**
     * @param {Object} options {
     *     model: {
     *         userPref: this.model.userPref,
     *         application: this.model.application,
     *     },
     * }
     */
    initialize(options) {
        ReactAdapterBase.prototype.initialize.apply(this, options);
        this.model = options.model || {};
        this.model.state = new Backbone.Model({
            open: true,
        });
        this.listenTo(this.model.state, 'change:open', this.render);
        this.handleClose = this.handleClose.bind(this);
        this.makeDocLink = this.makeDocLink.bind(this);
    },

    handleClose(status = this.model.userPref.getNewSnoozeStatus()) {
        this.model.userPref.entry.content.set('notification_python_3_impact', status);
        this.model.userPref.save({});
        this.model.state.set('open', false);
    },

    /**
     * Create a documentation link.
     * @param {String} location - doc string to link to.
     */
    makeDocLink(location) {
        return route.docHelp(
            this.model.application.get('root'),
            this.model.application.get('locale'),
            location,
        );
    },

    getComponent() {
        const props = {
            handleClose: this.handleClose,
            docLink: this.makeDocLink('learnmore.python3migration'),
            open: this.model.state.get('open'),
        };
        return React.createElement(Python3Notification, props);
    },
});
