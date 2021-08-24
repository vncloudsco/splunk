/**
 * Use this flag to conditionally run code only for debugging, such as setting global variables
 * for access via the browser console.
 * @type {boolean}
 */
export const DEBUG = process.env.NODE_ENV !== 'production';

/**
 * Use this flag to conditionally run code only in production, such as disabling load timeouts.
 * @type {boolean}
 */
export const PRODUCTION = process.env.NODE_ENV === 'production';