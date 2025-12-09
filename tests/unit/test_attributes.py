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
