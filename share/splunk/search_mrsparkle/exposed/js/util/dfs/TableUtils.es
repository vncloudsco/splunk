/**
 * Function that returns an array of objects of the current page
 * @param items - Object. All items
 * @param currentPage - Integer. Current page
 * @param rowPerPage - Integer. the number of rows in each page
 * @returns {[object]}
 */
export const getPaginatedItems = (items, currentPage, rowPerPage) => {
    const firstItem = (currentPage - 1) * rowPerPage;
    const lastItem = firstItem + rowPerPage;
    return items.slice(firstItem, lastItem);
};

export { getPaginatedItems as default };