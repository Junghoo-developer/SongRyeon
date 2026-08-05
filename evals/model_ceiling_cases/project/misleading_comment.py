"""A comment and executable value deliberately disagree."""

# The feature is always enabled in production.
FEATURE_ENABLED = False


def is_enabled():
    return FEATURE_ENABLED
