import $ from 'jquery';
import _ from 'underscore';
import Backbone from 'backbone';
import BaseView from 'views/Base';
import route from 'uri/route';
import './VizPicker.pcss';


const VizPicker = BaseView.extend({
    moduleId: module.id,
    className: 'viz-picker-container',
    /**
     * @constructor
     * @param options {
     *     model: {
     *         application: <models.shared.Application>
     *         viz: <models.base>
     *         user: <models.shared.User>
     *     }
     *     items: <Array> array of viz definitions in the form
     *         {
     *              id: <string>,
     *              label: <string>,
     *              icon: <string>,
     *              categories: <array> of category strings,
     *              description: <string>,
     *              searchHint: <string>,
     *              thumbnailPath: <string> url,
     *         }
     * }
     */
    initialize(options) {
        BaseView.prototype.initialize.call(this, options);
        this.vizModel = this.model.viz || new Backbone.Model();
        this.userModel = this.model.user;
        this.applicationModel = this.model.application;
        this.items = this.options.items || [];
        this.compiledListTemplate = _.template(this.listSectionTemplate);
    },
    events: {
        'click .viz-picker-list-item': function click(e) {
            e.preventDefault();
            const vizItem = this.findItemById($(e.target).closest('a').data('vizId'));
            this.vizModel.set(_.extend({}, vizItem));
            this.trigger('vizSelected', vizItem);
        },
        'mouseover .viz-picker-list-item': function mouseover(e) {
            e.preventDefault();
            const vizItem = this.findItemById($(e.target).closest('a').data('vizId'));
            this.setInfoTextForItem(vizItem);
        },

        'focus .viz-picker-list-item': function focus(e) {
            e.preventDefault();
            const vizItem = this.findItemById($(e.target).closest('a').data('vizId'));
            this.setInfoTextForItem(vizItem);
        },

        'mouseleave .list-container': function leaveContainer(e) {
            e.preventDefault();
            this.setDefaultText();
        },

        mouseleave: function leave(e) {
            e.preventDefault();
            this.setDefaultText();
        },
    },
    setDefaultText() {
        if (this.vizModel.has('id')) {
            this.setInfoTextForItem(this.findItemById(this.vizModel.get('id')));
        }
    },

    setInfoTextForItem(vizItem) {
        this.clearInfoText();
        this.$('.viz-picker-info-label').text(vizItem.label);
        this.$('.viz-picker-info-details').text(vizItem.description);

        if (vizItem.searchHint) {
            this.$('.viz-picker-info-search-hint-container').css('display', 'block');
            this.$('.viz-picker-info-search-hint-text').text(vizItem.searchHint);
        }
    },
    clearInfoText() {
        this.$('.viz-picker-info-label').text('');
        this.$('.viz-picker-info-details').text('');
        this.$('.viz-picker-info-search-hint-text').text('');
        this.$('.viz-picker-info-search-hint-container').css('display', 'none');
    },
    findItemById(vizId) {
        const vizItem = _.filter(this.items, viz => (
            viz.id === vizId
        ));
        return vizItem[0];
    },
    render() {
        const isLite = this.userModel.serverInfo && this.userModel.serverInfo.isLite();
        this.$el.append(this.compiledTemplate({
            showFindMoreLink: this.userModel.canUseApps() && this.userModel.canViewRemoteApps() && !isLite,
            findMoreHref: route.appsRemote(
                this.applicationModel.get('root'),
                this.applicationModel.get('locale'),
                this.applicationModel.get('app'),
                { data: { content: 'visualizations', type: 'app' } },
            ),
        }));
        if (this.options.warningMsg) {
            const html = _.template(this.warningMessageTemplate, {
                hasLearnMoreLink: this.options.warningLearnMoreLink != null,
                message: this.options.warningMsg,
                learn_more: _('Learn More').t(),
                link: this.options.warningLearnMoreLink,
            });
            $(html).appendTo(this.$('.viz-selector-body'));
        }
        const sections = {
            recommended: {
                header: _('Recommended').t(),
                items: [],
                className: 'list-section-recommended',
            },
            splunk: {
                header: _('Splunk Visualizations').t(),
                items: [],
                className: 'list-section-splunk',
            },
            more: {
                header: _('More').t(),
                items: [],
                className: 'list-section-more',
            },
        };
        _.each(this.items, (vizItem) => {
            // Find recommended
            if (_.contains(vizItem.categories, 'recommended')) {
                sections.recommended.items.push(vizItem);
            }

            // Everything goes in either splunk, or more
            if (_.contains(vizItem.categories, 'external')) {
                sections.more.items.push(vizItem);
            } else {
                sections.splunk.items.push(vizItem);
            }
        });

        // Iterate over the sections in reversed order since they are going to
        // be prepended to the dialog body.
        _.each([sections.more, sections.splunk, sections.recommended], (section) => {
            if (section.items && section.items.length > 0) {
                this.$('.viz-picker-body').prepend(
                    this.compiledListTemplate({
                        sectionHeader: section.header,
                        listItems: section.items,
                        sectionClassName: section.className || '',
                    }),
                );
            }
        });

        const defaultThumbnailPath = this.options.defaultThumbnailPath;
        this.$('.viz-picker-list-item img').on('error', function onError() {
            this.src = defaultThumbnailPath;
            return false;
        });

        // Set the selected item if there is one
        if (this.vizModel.has('id')) {
            this.setDefaultText();
            const selectedDOMElement = this.$(`*[data-viz-id="${this.vizModel.get('id')}"]`);
            selectedDOMElement.addClass('viz-picker-selected-viz-item');
        }
        this.$('.viz-picker-info-search-hint-container').css('display', 'none');
        return this;
    },
    listSectionTemplate: `
            <div class="viz-picker-list-section <%- sectionClassName %>">
                <p> <%- sectionHeader %> </p>
                <div class="list-item-container">
                    <% _.each(listItems, function(listItem) { %>
                        <a href="#" class="viz-picker-list-item" data-viz-id="<%- listItem.id %>"
                            aria-label="<%- listItem.label %>">
                            <img class="viz-picker-img" src="<%- listItem.thumbnailPath %>"
                                alt="<%- _('Preview of').t() %> <%- listItem.label %>" />
                        </a>
                    <% }); %>
                </div>
            </div>
            <div class="viz-picker-clear-fix"></div>`,
    warningMessageTemplate: `
            <div class="vizpicker-message">
                <i class="icon icon-warning"></i>
                <span class="message-text">
                    <%- message %>
                    <% if (hasLearnMoreLink) {%>
                    <a class="learn-more external" href="<%- link %>"><%- learn_more %></a>
                    <% } %>
                </span>
            </div>`,
    template: `
            <div class="viz-picker-body">
                <% if (showFindMoreLink) { %>
                    <a class="viz-picker-find-more-link" href="<%- findMoreHref %>" target="_blank">
                        <%- _("Find more visualizations").t() %>
                        <i class="icon-external"></i>
                    </a>
                <% } %>
            </div>
            <div class="viz-picker-footer">
                <h5 class="viz-picker-info-label"></h5>
                <p class="viz-picker-info-details"></p>
                <div class="viz-picker-info-search-hint-container">
                    <p class="viz-picker-info-search-hint-header"> <%- _("Search Fragment").t() %> </p>
                    <p class="viz-picker-info-search-hint-text"></p>
                </div>
            </div>`,
});

export default VizPicker;
