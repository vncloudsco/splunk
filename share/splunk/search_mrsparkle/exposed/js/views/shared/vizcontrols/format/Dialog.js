/*
 * This view provides the popdown dialog wrapper and workflow buttons for editing a visualization.
 * The contents of the dialog body are rendered by the component child view.
 */

define(
    [
        '../custom_controls/SimpleDraggablePopTart',
        'module'
    ],
    function (SimpleDraggablePopTart, module) {

        return SimpleDraggablePopTart.extend({
            moduleId: module.id,
            warningMessageTemplate: '\
                <div class="vizformat-message">\
                    <i class="icon icon-warning"></i>\
                    <span class="message-text"><%- message %></span>\
                    <% if (hasLearnMoreLink) {%>\
                    <a class="learn-more external" href="<%- link %>"><%- learn_more %></a>\
                    <% } %>\
                </div>\
            '
        });
    }
);
