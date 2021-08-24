define(
    [
        '../custom_controls/SimpleDraggablePopTart',
        'module'
    ],
    function (SimpleDraggablePopTart, module) {
        return SimpleDraggablePopTart.extend({
            moduleId: module.id
        });
    }
);
