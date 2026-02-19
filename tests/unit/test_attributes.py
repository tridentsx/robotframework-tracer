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


def test_from_suite_with_metadata():
    """Test extracting suite attributes with metadata."""
    data = Mock()
    data.name = "Suite"
    data.source = "/path/to/suite.robot"
    data.metadata = {"Version": "2.0", "Team": "QA"}

    result = Mock()
    result.id = "s1"
    result.starttime = None
    result.endtime = None

    attrs = AttributeExtractor.from_suite(data, result)
    assert attrs["rf.suite.metadata.Version"] == "2.0"
    assert attrs["rf.suite.metadata.Team"] == "QA"


def test_from_test_with_template():
    """Test extracting test attributes with template."""
    data = Mock()
    data.name = "Templated Test"
    data.tags = []
    data.template = "My Template Keyword"
    data.timeout = "30s"

    result = Mock()
    result.id = "t1"
    result.starttime = None
    result.endtime = None
    result.message = ""

    attrs = AttributeExtractor.from_test(data, result)
    assert attrs[RFAttributes.TEST_TEMPLATE] == "My Template Keyword"
    assert attrs[RFAttributes.TEST_TIMEOUT] == "30s"


def test_from_test_with_lineno():
    """Test extracting test attributes with line number (RF 5+)."""
    data = Mock()
    data.name = "Test With Line"
    data.tags = []
    data.lineno = 42

    result = Mock()
    result.id = "t1"

    attrs = AttributeExtractor.from_test(data, result)
    assert attrs[RFAttributes.TEST_LINENO] == 42


def test_from_test_without_lineno():
    """Test extracting test attributes without line number (RF <5)."""
    data = Mock(spec=["name", "tags"])  # No lineno attribute
    data.name = "Test Without Line"
    data.tags = []

    result = Mock()
    result.id = "t1"

    attrs = AttributeExtractor.from_test(data, result)
    assert RFAttributes.TEST_LINENO not in attrs


def test_from_keyword_with_lineno():
    """Test extracting keyword attributes with line number (RF 5+)."""
    data = Mock()
    data.name = "My Keyword"
    data.type = "KEYWORD"
    data.libname = "MyLib"
    data.args = []
    data.lineno = 15

    result = Mock()

    attrs = AttributeExtractor.from_keyword(data, result)
    assert attrs[RFAttributes.KEYWORD_LINENO] == 15


def test_from_keyword_without_lineno():
    """Test extracting keyword attributes without line number (RF <5)."""
    data = Mock(spec=["name", "type", "args"])  # No lineno attribute
    data.name = "My Keyword"
    data.type = "KEYWORD"
    data.args = []

    result = Mock()

    attrs = AttributeExtractor.from_keyword(data, result)
    assert RFAttributes.KEYWORD_LINENO not in attrs
