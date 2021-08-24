define([
    'underscore',
    'jquery',
    'util/xml'
], function(_,
            $,
            XML) {

    function createEventNodes(evtManagerState, dashboardState, options) {
        var nodes = [];
        _(evtManagerState.getState()["events"] || []).each(function(eventDef) {
            var $eventNode = XML.$tag(eventDef.type);
            // serialize conditions
            _(eventDef.settings.conditions || []).each(function(condition) {
                var $condition = createConditionNode(condition, options);
                $condition && $eventNode.append($condition);
            });
            // serialize actions
            _(eventDef.settings.actions || []).each(function(action) {
                var $action = createActionNode(action, options);
                $action && $eventNode.append($action);
            });
            nodes.push($eventNode);
        });
        return nodes;
    }

    function createConditionNode(condition, options) {
        var $condition = XML.$tag('condition').attr(condition.attr, condition.value);
        _(condition.actions || []).each(function(action) {
            var $action = createActionNode(action, options);
            $action && $condition.append($action);
        });
        return $condition;
    }

    function createActionNode(action, options) {
        var $action = XML.$tag(action.type);
        if (action.value) {
            $action.text(action.value);
        }
        switch (action.type) {
            case 'link':
                action.target && $action.attr('target', action.target);
                action.series && $action.attr('series', action.series);
                action.field && $action.attr('field', action.field);
                break;
            case 'set':
            case 'unset':
            case 'eval':
                action.token && $action.attr('token', action.token);
                action.prefix && $action.attr('prefix', action.prefix);
                action.suffix && $action.attr('suffix', action.suffix);
                break;
        }
        return $action;
    }

    function updateEventNodes($parent, evtManagerState, dashboardState, options) {
        options || (options = {});
        if (evtManagerState && (evtManagerState.isDirty() || options.forceDirty === true)) {
            $parent.find('drilldown,selection').remove();
            _(createEventNodes(evtManagerState, dashboardState, options)).each(function($event) {
                $parent.append($event);
            });
        }
    }

    function removeEventNodes($parent, options) {
        $parent.find('drilldown,selection').remove();
    }

    return {
        createEventNodes: createEventNodes,
        updateEventNodes: updateEventNodes,
        removeEventNodes: removeEventNodes,
        // export for testing purpose
        createActionNode: createActionNode
    };
});
