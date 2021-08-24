export function getModule(moduleId = '') {
    return `splunk-core:/${moduleId.replace(/\s/g, '')}`;
}

/**
 * Returns an object that can be passed as props to a react component for setting standard test
 * hooks for automated testing.
 *
 * @param {String} moduleId - unique id of this module. Usually can be retrieved via 'module.id'
 * @param {String} subModuleId - uniqie id of sub module. Sometimes it's required to provide sub module id
 * for repeating testable element
 * @returns {Object}

 * Example:
    test/Foo.js

    function () {
        return (
            <div {...createTestHook(module.id)}>
                <button type='button' {...createTestHook(module.id, 'button1')}/>
                <button type='button' {...createTestHook(module.id, 'button2')}/>
            </div>
        )
    }

    This will turn into

    <div data-component='splunk-core:/test/Foo'>
        <button type='button' data-component='splunk-core:/test/Foo' data-component-name='button1'>
        <button type='button' data-component='splunk-core:/test/Foo' data-component-name='button2'>
    </div>
 */
export function createTestHook(moduleId = '', subModuleId = '') {
    const attrs = {};
    if (moduleId) {
        Object.assign(attrs, {
            'data-component': getModule(moduleId),
        });
    }
    if (subModuleId) {
        Object.assign(attrs, {
            'data-component-name': subModuleId,
        });
    }
    return attrs;
}
