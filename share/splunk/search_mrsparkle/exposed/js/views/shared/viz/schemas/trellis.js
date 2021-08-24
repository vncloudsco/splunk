define([
        'underscore',
        './shared_elements'
    ],
    function(
        _,
        SharedElements
    ) {

        return ([
            {
                id: 'trellis',
                title: _('Trellis').t(),
                formElements: [
                    SharedElements.TRELLIS_ENABLED,
                    SharedElements.TRELLIS_SPLIT_FIELD,
                    SharedElements.TRELLIS_SIZE,
                    SharedElements.TRELLIS_AXIS_SHARED
                ]
            }
        ]);

    });
