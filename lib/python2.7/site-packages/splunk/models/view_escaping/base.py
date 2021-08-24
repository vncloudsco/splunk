#
#  View object search mode enums
#
#  Many view objects can request search data from the backend.  In this view
#  object model, each search aware object must declare a single search
#  mode in which to operate.
#

# define ad-hoc search string mode
STRING_SEARCH_MODE = 'string'

# define saved search run mode
SAVED_SEARCH_MODE = 'saved'

# define form search template run mode
TEMPLATE_SEARCH_MODE = 'template'

# define search post process mode
POST_SEARCH_MODE = 'postsearch'

SEARCH_NODE_MAP = [
    ('searchString', TEMPLATE_SEARCH_MODE),
    ('searchName', SAVED_SEARCH_MODE),
    ('searchTemplate', TEMPLATE_SEARCH_MODE),
    ('searchPostProcess', POST_SEARCH_MODE)
]

DEFAULT_SEARCH_ID = 'global'
