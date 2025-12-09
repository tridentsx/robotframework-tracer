class RFAttributes:
    """OpenTelemetry semantic conventions for Robot Framework."""

    # Suite attributes
    SUITE_NAME = "rf.suite.name"
    SUITE_SOURCE = "rf.suite.source"
    SUITE_ID = "rf.suite.id"
    SUITE_METADATA = "rf.suite.metadata"

    # Test attributes
    TEST_NAME = "rf.test.name"
    TEST_ID = "rf.test.id"
    TEST_TAGS = "rf.test.tags"
    TEST_TEMPLATE = "rf.test.template"
    TEST_TIMEOUT = "rf.test.timeout"

    # Keyword attributes
    KEYWORD_NAME = "rf.keyword.name"
    KEYWORD_TYPE = "rf.keyword.type"
    KEYWORD_LIBRARY = "rf.keyword.library"
    KEYWORD_ARGS = "rf.keyword.args"

    # Result attributes
    STATUS = "rf.status"
    ELAPSED_TIME = "rf.elapsed_time"
    START_TIME = "rf.start_time"
    END_TIME = "rf.end_time"
    MESSAGE = "rf.message"

    # Framework attributes
    RF_VERSION = "rf.version"


class AttributeExtractor:
    """Extract attributes from Robot Framework objects."""

    @staticmethod
    def from_suite(data, result):
        """Extract attributes from suite data and result."""
        attrs = {
            RFAttributes.SUITE_NAME: data.name,
            RFAttributes.SUITE_ID: result.id,
        }
        if data.source:
            attrs[RFAttributes.SUITE_SOURCE] = str(data.source)

        # Extract suite metadata
        if hasattr(data, "metadata") and data.metadata:
            for key, value in data.metadata.items():
                attrs[f"{RFAttributes.SUITE_METADATA}.{key}"] = str(value)

        # Add timing information
        if hasattr(result, "starttime") and result.starttime:
            attrs[RFAttributes.START_TIME] = result.starttime
        if hasattr(result, "endtime") and result.endtime:
            attrs[RFAttributes.END_TIME] = result.endtime

        return attrs

    @staticmethod
    def from_test(data, result):
        """Extract attributes from test data and result."""
        attrs = {
            RFAttributes.TEST_NAME: data.name,
            RFAttributes.TEST_ID: result.id,
        }
        if data.tags:
            attrs[RFAttributes.TEST_TAGS] = list(data.tags)

        # Add test template if available
        if hasattr(data, "template") and data.template:
            attrs[RFAttributes.TEST_TEMPLATE] = str(data.template)

        # Add test timeout if available
        if hasattr(data, "timeout") and data.timeout:
            attrs[RFAttributes.TEST_TIMEOUT] = str(data.timeout)

        # Add timing information
        if hasattr(result, "starttime") and result.starttime:
            attrs[RFAttributes.START_TIME] = result.starttime
        if hasattr(result, "endtime") and result.endtime:
            attrs[RFAttributes.END_TIME] = result.endtime

        # Add message if available
        if hasattr(result, "message") and result.message:
            attrs[RFAttributes.MESSAGE] = result.message

        return attrs

    @staticmethod
    def from_keyword(data, result, max_arg_length=200):
        """Extract attributes from keyword data and result."""
        attrs = {
            RFAttributes.KEYWORD_NAME: data.name,
            RFAttributes.KEYWORD_TYPE: data.type,
        }
        # Try to get library name (may not always be available)
        if hasattr(data, "libname") and data.libname:
            attrs[RFAttributes.KEYWORD_LIBRARY] = data.libname
        elif hasattr(data, "owner") and data.owner:
            attrs[RFAttributes.KEYWORD_LIBRARY] = (
                data.owner.name if hasattr(data.owner, "name") else str(data.owner)
            )

        if data.args:
            args_str = ", ".join(str(arg)[:max_arg_length] for arg in data.args[:10])
            if len(args_str) > max_arg_length:
                args_str = args_str[:max_arg_length] + "..."
            attrs[RFAttributes.KEYWORD_ARGS] = args_str
        return attrs
