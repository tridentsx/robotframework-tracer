class RFAttributes:
    """OpenTelemetry semantic conventions for Robot Framework."""

    # Common attributes
    TYPE = "rf.type"

    # Suite attributes
    SUITE_NAME = "rf.suite.name"
    SUITE_SOURCE = "rf.suite.source"
    SUITE_ID = "rf.suite.id"
    SUITE_METADATA = "rf.suite.metadata"
    SUITE_DOC = "rf.suite.doc"
    SUITE_LINENO = "rf.suite.lineno"
    SUITE_HAS_SETUP = "rf.suite.has_setup"
    SUITE_HAS_TEARDOWN = "rf.suite.has_teardown"

    # Test attributes
    TEST_NAME = "rf.test.name"
    TEST_ID = "rf.test.id"
    TEST_TAGS = "rf.test.tags"
    TEST_TEMPLATE = "rf.test.template"
    TEST_TIMEOUT = "rf.test.timeout"
    TEST_SOURCE = "rf.test.source"
    TEST_DOC = "rf.test.doc"
    TEST_LINENO = "rf.test.lineno"
    TEST_HAS_SETUP = "rf.test.has_setup"
    TEST_HAS_TEARDOWN = "rf.test.has_teardown"

    # Keyword attributes
    KEYWORD_NAME = "rf.keyword.name"
    KEYWORD_TYPE = "rf.keyword.type"
    KEYWORD_LIBRARY = "rf.keyword.library"
    KEYWORD_ARGS = "rf.keyword.args"
    KEYWORD_DOC = "rf.keyword.doc"
    KEYWORD_LINENO = "rf.keyword.lineno"

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
            RFAttributes.TYPE: "suite",
            RFAttributes.SUITE_NAME: data.name,
            RFAttributes.SUITE_ID: result.id,
        }
        if data.source:
            attrs[RFAttributes.SUITE_SOURCE] = str(data.source)
        if hasattr(data, "doc") and data.doc:
            attrs[RFAttributes.SUITE_DOC] = str(data.doc)
        if hasattr(data, "lineno") and data.lineno:
            attrs[RFAttributes.SUITE_LINENO] = data.lineno
        if hasattr(data, "setup") and data.setup:
            attrs[RFAttributes.SUITE_HAS_SETUP] = True
        if hasattr(data, "teardown") and data.teardown:
            attrs[RFAttributes.SUITE_HAS_TEARDOWN] = True

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
            RFAttributes.TYPE: "test",
            RFAttributes.TEST_NAME: data.name,
            RFAttributes.TEST_ID: result.id,
        }
        if hasattr(data, "source") and data.source:
            attrs[RFAttributes.TEST_SOURCE] = str(data.source)
        if hasattr(data, "doc") and data.doc:
            attrs[RFAttributes.TEST_DOC] = str(data.doc)
        if hasattr(data, "lineno") and data.lineno:
            attrs[RFAttributes.TEST_LINENO] = data.lineno
        if data.tags:
            attrs[RFAttributes.TEST_TAGS] = list(data.tags)
        if hasattr(data, "template") and data.template:
            attrs[RFAttributes.TEST_TEMPLATE] = str(data.template)
        if hasattr(data, "timeout") and data.timeout:
            attrs[RFAttributes.TEST_TIMEOUT] = str(data.timeout)
        if hasattr(data, "setup") and data.setup:
            attrs[RFAttributes.TEST_HAS_SETUP] = True
        if hasattr(data, "teardown") and data.teardown:
            attrs[RFAttributes.TEST_HAS_TEARDOWN] = True

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
            RFAttributes.TYPE: "keyword",
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
        if hasattr(data, "doc") and data.doc:
            attrs[RFAttributes.KEYWORD_DOC] = str(data.doc)
        if hasattr(data, "lineno") and data.lineno:
            attrs[RFAttributes.KEYWORD_LINENO] = data.lineno

        if data.args:
            args_str = ", ".join(str(arg)[:max_arg_length] for arg in data.args[:10])
            if len(args_str) > max_arg_length:
                args_str = args_str[:max_arg_length] + "..."
            attrs[RFAttributes.KEYWORD_ARGS] = args_str

        # Add message if available
        if hasattr(result, "message") and result.message:
            attrs[RFAttributes.MESSAGE] = result.message

        return attrs
