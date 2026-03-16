from unittest.mock import Mock

from robotframework_tracer.attributes import AttributeExtractor, RFAttributes


def test_from_suite():
    """Test extracting attributes from suite."""
    data = Mock()
    data.name = "Test Suite"
    data.source = "/path/to/suite.robot"
    data.metadata = {}  # Empty dict instead of Mock

    result = Mock()
    result.id = "s1"
    result.starttime = None
    result.endtime = None

    attrs = AttributeExtractor.from_suite(data, result)

    assert attrs[RFAttributes.SUITE_NAME] == "Test Suite"
    assert attrs[RFAttributes.SUITE_ID] == "s1"
    assert attrs[RFAttributes.SUITE_SOURCE] == "/path/to/suite.robot"


def test_from_suite_no_source():
    """Test extracting attributes from suite without source."""
    data = Mock()
    data.name = "Test Suite"
    data.source = None
    data.metadata = {}

    result = Mock()
    result.id = "s1"
    result.starttime = None
    result.endtime = None

    attrs = AttributeExtractor.from_suite(data, result)

    assert attrs[RFAttributes.SUITE_NAME] == "Test Suite"
    assert attrs[RFAttributes.SUITE_ID] == "s1"
    assert RFAttributes.SUITE_SOURCE not in attrs


def test_from_test():
    """Test extracting attributes from test."""
    data = Mock()
    data.name = "Test Case"
    data.tags = ["smoke", "regression"]

    result = Mock()
    result.id = "s1-t1"

    attrs = AttributeExtractor.from_test(data, result)

    assert attrs[RFAttributes.TEST_NAME] == "Test Case"
    assert attrs[RFAttributes.TEST_ID] == "s1-t1"
    assert attrs[RFAttributes.TEST_TAGS] == ["smoke", "regression"]


def test_from_test_no_tags():
    """Test extracting attributes from test without tags."""
    data = Mock()
    data.name = "Test Case"
    data.tags = []

    result = Mock()
    result.id = "s1-t1"

    attrs = AttributeExtractor.from_test(data, result)

    assert attrs[RFAttributes.TEST_NAME] == "Test Case"
    assert attrs[RFAttributes.TEST_ID] == "s1-t1"
    assert RFAttributes.TEST_TAGS not in attrs


def test_from_keyword():
    """Test extracting attributes from keyword."""
    data = Mock()
    data.name = "Log"
    data.type = "KEYWORD"
    data.libname = "BuiltIn"
    data.args = ["Hello World"]

    result = Mock()

    attrs = AttributeExtractor.from_keyword(data, result)

    assert attrs[RFAttributes.KEYWORD_NAME] == "Log"
    assert attrs[RFAttributes.KEYWORD_TYPE] == "KEYWORD"
    assert attrs[RFAttributes.KEYWORD_LIBRARY] == "BuiltIn"
    assert "Hello World" in attrs[RFAttributes.KEYWORD_ARGS]


def test_from_keyword_no_library():
    """Test extracting attributes from keyword without library."""
    data = Mock()
    data.name = "My Keyword"
    data.type = "KEYWORD"
    data.args = []
    # Explicitly set libname and owner to None
    data.libname = None
    data.owner = None

    result = Mock()

    attrs = AttributeExtractor.from_keyword(data, result)

    assert attrs[RFAttributes.KEYWORD_NAME] == "My Keyword"
    assert attrs[RFAttributes.KEYWORD_TYPE] == "KEYWORD"
    assert RFAttributes.KEYWORD_LIBRARY not in attrs


def test_from_keyword_arg_length_limit():
    """Test that keyword arguments are limited in length."""
    data = Mock()
    data.name = "Log"
    data.type = "KEYWORD"
    data.libname = "BuiltIn"
    data.args = ["x" * 300]

    result = Mock()

    attrs = AttributeExtractor.from_keyword(data, result, max_arg_length=100)

    assert len(attrs[RFAttributes.KEYWORD_ARGS]) <= 104  # 100 + "..."


def test_from_suite_with_doc_and_lineno():
    """Test extracting doc, lineno, setup, teardown from suite."""
    data = Mock()
    data.name = "Test Suite"
    data.source = "/path/to/suite.robot"
    data.metadata = {}
    data.doc = "Suite documentation"
    data.lineno = 1
    data.setup = Mock()  # truthy = has setup
    data.teardown = Mock()

    result = Mock()
    result.id = "s1"
    result.starttime = None
    result.endtime = None

    attrs = AttributeExtractor.from_suite(data, result)

    assert attrs[RFAttributes.TYPE] == "suite"
    assert attrs[RFAttributes.SUITE_DOC] == "Suite documentation"
    assert attrs[RFAttributes.SUITE_LINENO] == 1
    assert attrs[RFAttributes.SUITE_HAS_SETUP] is True
    assert attrs[RFAttributes.SUITE_HAS_TEARDOWN] is True


def test_from_suite_without_optional_attrs():
    """Test that optional suite attributes are omitted when not present."""
    data = Mock()
    data.name = "Test Suite"
    data.source = None
    data.metadata = {}
    data.doc = ""
    data.lineno = None
    data.setup = None
    data.teardown = None

    result = Mock()
    result.id = "s1"
    result.starttime = None
    result.endtime = None

    attrs = AttributeExtractor.from_suite(data, result)

    assert attrs[RFAttributes.TYPE] == "suite"
    assert RFAttributes.SUITE_DOC not in attrs
    assert RFAttributes.SUITE_LINENO not in attrs
    assert RFAttributes.SUITE_HAS_SETUP not in attrs
    assert RFAttributes.SUITE_HAS_TEARDOWN not in attrs


def test_from_test_with_all_attrs():
    """Test extracting all attributes from test."""
    data = Mock()
    data.name = "Test Case"
    data.tags = ["smoke"]
    data.source = "/path/to/test.robot"
    data.doc = "Test documentation"
    data.lineno = 10
    data.template = "My Template"
    data.timeout = "30s"
    data.setup = Mock()
    data.teardown = Mock()

    result = Mock()
    result.id = "s1-t1"
    result.starttime = None
    result.endtime = None
    result.message = "All good"

    attrs = AttributeExtractor.from_test(data, result)

    assert attrs[RFAttributes.TYPE] == "test"
    assert attrs[RFAttributes.TEST_SOURCE] == "/path/to/test.robot"
    assert attrs[RFAttributes.TEST_DOC] == "Test documentation"
    assert attrs[RFAttributes.TEST_LINENO] == 10
    assert attrs[RFAttributes.TEST_TEMPLATE] == "My Template"
    assert attrs[RFAttributes.TEST_TIMEOUT] == "30s"
    assert attrs[RFAttributes.TEST_HAS_SETUP] is True
    assert attrs[RFAttributes.TEST_HAS_TEARDOWN] is True
    assert attrs[RFAttributes.MESSAGE] == "All good"


def test_from_test_without_optional_attrs():
    """Test that optional test attributes are omitted when not present."""
    data = Mock()
    data.name = "Test Case"
    data.tags = []
    data.source = None
    data.doc = ""
    data.lineno = None
    data.template = None
    data.timeout = None
    data.setup = None
    data.teardown = None

    result = Mock()
    result.id = "s1-t1"
    result.starttime = None
    result.endtime = None
    result.message = ""

    attrs = AttributeExtractor.from_test(data, result)

    assert attrs[RFAttributes.TYPE] == "test"
    assert RFAttributes.TEST_SOURCE not in attrs
    assert RFAttributes.TEST_DOC not in attrs
    assert RFAttributes.TEST_LINENO not in attrs
    assert RFAttributes.TEST_HAS_SETUP not in attrs
    assert RFAttributes.TEST_HAS_TEARDOWN not in attrs
    assert RFAttributes.MESSAGE not in attrs


def test_from_keyword_with_doc_and_lineno():
    """Test extracting doc, lineno, and message from keyword."""
    data = Mock()
    data.name = "Click Element"
    data.type = "KEYWORD"
    data.libname = "SeleniumLibrary"
    data.args = ["//button"]
    data.doc = "Clicks the given element"
    data.lineno = 42

    result = Mock()
    result.message = "Element clicked"

    attrs = AttributeExtractor.from_keyword(data, result)

    assert attrs[RFAttributes.TYPE] == "keyword"
    assert attrs[RFAttributes.KEYWORD_DOC] == "Clicks the given element"
    assert attrs[RFAttributes.KEYWORD_LINENO] == 42
    assert attrs[RFAttributes.MESSAGE] == "Element clicked"


def test_from_keyword_without_optional_attrs():
    """Test that optional keyword attributes are omitted when not present."""
    data = Mock()
    data.name = "Log"
    data.type = "KEYWORD"
    data.libname = "BuiltIn"
    data.args = []
    data.doc = ""
    data.lineno = None

    result = Mock()
    result.message = ""

    attrs = AttributeExtractor.from_keyword(data, result)

    assert attrs[RFAttributes.TYPE] == "keyword"
    assert RFAttributes.KEYWORD_DOC not in attrs
    assert RFAttributes.KEYWORD_LINENO not in attrs
    assert RFAttributes.MESSAGE not in attrs
