import _ from 'underscore';
import PropTypes from 'prop-types';
import React from 'react';
import AddNewButton from 'dashboard/components/shared/AddNewButton';
import TokenExpression from 'dashboard/components/editor/drilldown/tokens/TokenExpression';
import Link from '@splunk/react-ui/Link';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import FormMessage from 'dashboard/components/shared/FormMessage';
import { createTestHook } from 'util/test_support';

const TokensActionEditor = ({
    items,
    error,
    candidateTokens,
    onUpdateTokens,
    learnMoreLinkForTokenUsage,
}) => {
    const onAddToken = newItem => onUpdateTokens([...items, newItem]);

    const onChangeToken = (newItem, index) => onUpdateTokens([
        ...items.slice(0, index),
        newItem,
        ...items.slice(index + 1),
    ]);

    const onRemoveToken = index => onUpdateTokens([
        ...items.slice(0, index),
        ...items.slice(index + 1),
    ]);

    const tokenExpressions = items.map((item, index) => (
        <TokenExpression
            key={index} // eslint-disable-line react/no-array-index-key
            type={item.type}
            token={item.token}
            value={item.value}
            candidateTokens={candidateTokens}
            onTypeChange={newType => onChangeToken({
                type: newType,
                token: item.token,
                value: item.value,
            }, index)}
            onTokenChange={newToken => onChangeToken({
                type: item.type,
                token: newToken,
                value: item.value,
            }, index)}
            onValueChange={newValue => onChangeToken({
                type: item.type,
                token: item.token,
                value: newValue,
            }, index)}
            onRemove={() => onRemoveToken(index)}
        />
    ));

    return (
        <div {...createTestHook(module.id)}>
            <ControlGroup label="" controlsLayout="none" {...createTestHook(null, 'learnMoreAboutTokens')}>
                {_('Use <set>, <eval>, and <unset> to update token values. This can help you ' +
                    'create responsive content or display changes in dashboards and forms.').t()}
                {' '}
                <Link to={learnMoreLinkForTokenUsage} openInNewContext>{_('Learn more').t()}</Link>
            </ControlGroup>
            <FormMessage active={!!error} type="error" message={error || ''} />
            <ControlGroup
                label=""
                controlsLayout="none"
                help={_('Example: form.host = $click.value2$ or host = $row.host$').t()}
                {...createTestHook(null, 'editTokenValues')}
            >
                {tokenExpressions}
                <AddNewButton
                    onClick={() => onAddToken({
                        type: items.length > 0 ? items[items.length - 1].type : 'set',
                        token: '',
                        value: '',
                    })}
                    error={!!error}
                />
            </ControlGroup>
        </div>
    );
};

TokensActionEditor.propTypes = {
    items: PropTypes.arrayOf(PropTypes.shape({
        type: PropTypes.string.isRequired,
        token: PropTypes.string.isRequired,
        value: PropTypes.string,
    })).isRequired,
    error: PropTypes.string,
    candidateTokens: PropTypes.arrayOf(PropTypes.shape({
        token: PropTypes.string.isRequired,
        description: PropTypes.string,
    })).isRequired,
    onUpdateTokens: PropTypes.func.isRequired,
    learnMoreLinkForTokenUsage: PropTypes.string.isRequired,
};

TokensActionEditor.defaultProps = {
    error: '',
};

export default TokensActionEditor;
