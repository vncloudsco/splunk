define(
    [
        'ace/ace',
        'script-loader!contrib/ace-editor/mode-spl'
    ],
    function(Ace) {
        return (Ace.require('ace/mode/spl'));
});
