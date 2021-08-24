define([
    'ace/ace',
    'script-loader!contrib/ace-editor/ext-language_tools',
    'script-loader!contrib/ace-editor/ext-spl_tools'],
    function(Ace) {
        return Ace.require('ace/ext/spl_tools');
});
