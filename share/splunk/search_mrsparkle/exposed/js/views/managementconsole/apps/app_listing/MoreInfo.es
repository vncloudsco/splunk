import _ from 'underscore';
import BaseView from 'views/Base';

export default BaseView.extend({
    moduleId: module.id,
    tagName: 'tr',
    className: 'more-info',

    initialize(...args) {
        BaseView.prototype.initialize.apply(this, args);

        this.model = this.model || {};
        this.appsLocalMap = this.options.appsLocalMap;
        this.model.appLocal = this.appsLocalMap[this.model.entity.entry.get('name')];

        this.syncAppsLocal = this.options.syncAppsLocal.bind(this);

        this.$el.addClass((this.options.index % 2 === 0) ? 'odd' : 'even');
        this.$el.css('display', 'none');

        if (!_.isUndefined(this.model.appLocal)) {
            this.listenTo(this.model.appLocal, 'sync', this.render);
        }
        this.listenTo(this.collection.appsLocal, 'syncAppsLocal', this.syncAppsLocal);
    },

    events: {
        /**
         * mouseenter and mouseleave events required to add css styling to
         * the entire row regardless of whether the main row component or
         * moreInfo row component are hovered, the same styling is applied
         * to both components. CSS does not support a previous sibling selector,
         * therefore, must apply this logic through javascript
         */
        mouseenter(e) {
            e.preventDefault();
            const $listItem = this.$el.prev('tr.list-item');
            $listItem.addClass('hover');
        },
        mouseleave(e) {
            e.preventDefault();
            const $listItem = this.$el.prev('tr.list-item');
            $listItem.removeClass('hover');
        },
    },

    render() {
        this.$el.html(this.compiledTemplate({
            viewObjectsUrl: this.model.entity.getViewObjectsUrl(),
            isExternal: this.model.entity.isExternal(),
            isPrivate: this.model.entity.isPrivate(),
            isIndexerOnly: this.model.entity.isIndexerOnly(),
            installLocationLabel: this.model.entity.getInstallLocationLabel(),
            description: this.model.entity.getDescription(),
            isDisabled: this.model.appLocal && this.model.appLocal.isDisabled(),
            releaseNoteLink: this.model.entity.getReleaseNotesURI(),
            installedBy: this.model.entity.getDeployedBy(),
            installedOn: this.model.entity.getDeployedOn(),
            appTemplate: this.model.entity.getTemplate(),
        }));

        return this;
    },

    /* eslint-disable no-multi-str */
    template: ' \
        <td colspan="10"> \
            <dl class="list-dotted"> \
                <% if (!isIndexerOnly) { %> \
                    <dt>View objects</dt> \
                    <% if (isDisabled) { %> \
                        <dd class="disabled"><%- _("Enable app to view objects").t() %></dd> \
                    <% } else { %> \
                        <dd> \
                            <a href="<%- viewObjectsUrl %>"><%- _("Click here to view objects").t() %> \
                            </a> \
                        </dd> \
                    <% } %> \
                <% } %> \
                <% if (releaseNoteLink) { %>\
                    <dt><%- _("Vew release notes").t() %></dt> \
                    <dd> \
                        <a href="<%- releaseNoteLink %>" target=_blank class="release-notes-link"> \
                            <%- _("Click here to view release notes").t() %> \
                            <i class="icon-external"></i> \
                        </a> \
                    </dd> \
                <% } %> \
                <dt>Install type</dt><dd><%- isExternal ? _("Splunk").t() : _("Self-Service").t() %></dd> \
                <dt>Install location</dt><dd><%- installLocationLabel %></dd> \
                <% if (installedBy) { %> \
                    <dt>Installed by</dt><dd><%- installedBy %></dd> \
                <% } %> \
                <% if (installedOn) { %> \
                    <dt>Installed on</dt><dd><%- installedOn %></dd> \
                <% } %> \
                <dt>Description</dt><dd><%- description %></dd> \
                <% if (appTemplate) { %> \
                    <dt>Template</dt><dd><%- appTemplate %></dd> \
                <% } %> \
            </dl> \
        </td> \
    ',
    /* eslint-enable no-multi-str */
});
