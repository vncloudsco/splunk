import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { _ } from '@splunk/ui-utils/i18n';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Switch from '@splunk/react-ui/Switch';
import P from '@splunk/react-ui/Paragraph';
import { createTestHook } from 'util/test_support';
import AdvancedEditor from './advanced/AdvancedEditor';
import BasicEditor from './basic/BasicEditor';

const USE_ADVANCED_EDITOR = 'search_use_advanced_editor';

class SPLEditor extends Component {
    constructor(props) {
        super(props);
        this.handleChange = this.handleChange.bind(this);
    }

    handleChange(event, { selected }, attr = USE_ADVANCED_EDITOR) {
        this.props.onAttributeChange(attr, !selected);
    }

    render() {
        const useAdvancedEditor = this.props.content[USE_ADVANCED_EDITOR];
        /* eslint max-len: ["error", { "ignoreStrings": true }] */
        return (
            <div {...createTestHook(module.id)} >
                <P style={{ marginBottom: '20px' }}>
                    {_('The advanced editor can provide auto-formatting, line numbers, and highlight search syntax for increased readability. You can also turn off the advanced editor to use the basic search format.')}
                </P>
                <div style={{ marginLeft: '-17px' }}>
                    <ControlGroup
                        label={_('Advanced editor')}
                        {...createTestHook(null, 'editor-control')}
                    >
                        <Switch
                            value={USE_ADVANCED_EDITOR}
                            onClick={this.handleChange}
                            selected={useAdvancedEditor}
                            appearance="toggle"
                            size="small"
                        />
                    </ControlGroup>
                </div>
                {useAdvancedEditor ? (
                    <AdvancedEditor {...this.props} />
                ) : (
                    <BasicEditor {...this.props} />
                )}
            </div>
        );
    }
}

/* eslint-disable react/forbid-prop-types */
SPLEditor.propTypes = {
    content: PropTypes.object.isRequired,
    onAttributeChange: PropTypes.func.isRequired,
};

export default SPLEditor;