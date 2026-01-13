"""Tests for utility functions."""

from valerie.models import Supplier
from valerie.utils.helpers import (
    format_risk_level,
    format_supplier_list,
    safe_get,
    truncate_text,
)


class TestFormatSupplierList:
    """Tests for format_supplier_list function."""

    def test_empty_list(self):
        """Test formatting empty supplier list."""
        result = format_supplier_list([])
        assert result == "No suppliers found."

    def test_single_supplier_minimal(self):
        """Test formatting single supplier with minimal data."""
        supplier = Supplier(id="SUP-001", name="Test Supplier")
        result = format_supplier_list([supplier])
        assert "1. **Test Supplier**" in result

    def test_single_supplier_full(self):
        """Test formatting single supplier with all data."""
        supplier = Supplier(
            id="SUP-001",
            name="AeroTech",
            location="Phoenix, AZ",
            capabilities=["heat_treatment", "shot_peening"],
            quality_rate=98.5,
        )
        result = format_supplier_list([supplier])
        assert "1. **AeroTech**" in result
        assert "Phoenix, AZ" in result
        assert "heat_treatment" in result
        assert "98.5%" in result

    def test_multiple_suppliers(self):
        """Test formatting multiple suppliers."""
        suppliers = [
            Supplier(id="SUP-001", name="Supplier A"),
            Supplier(id="SUP-002", name="Supplier B"),
            Supplier(id="SUP-003", name="Supplier C"),
        ]
        result = format_supplier_list(suppliers)
        assert "1. **Supplier A**" in result
        assert "2. **Supplier B**" in result
        assert "3. **Supplier C**" in result


class TestFormatRiskLevel:
    """Tests for format_risk_level function."""

    def test_low_risk(self):
        """Test low risk level."""
        level, color = format_risk_level(0.1)
        assert level == "Low"
        assert color == "green"

    def test_moderate_risk(self):
        """Test moderate risk level."""
        level, color = format_risk_level(0.3)
        assert level == "Moderate"
        assert color == "yellow"

    def test_elevated_risk(self):
        """Test elevated risk level."""
        level, color = format_risk_level(0.5)
        assert level == "Elevated"
        assert color == "orange"

    def test_high_risk(self):
        """Test high risk level."""
        level, color = format_risk_level(0.7)
        assert level == "High"
        assert color == "red"

    def test_critical_risk(self):
        """Test critical risk level."""
        level, color = format_risk_level(0.9)
        assert level == "Critical"
        assert color == "darkred"

    def test_boundary_values(self):
        """Test risk level boundary values."""
        assert format_risk_level(0.0)[0] == "Low"
        assert format_risk_level(0.2)[0] == "Moderate"
        assert format_risk_level(0.4)[0] == "Elevated"
        assert format_risk_level(0.6)[0] == "High"
        assert format_risk_level(0.8)[0] == "Critical"


class TestTruncateText:
    """Tests for truncate_text function."""

    def test_short_text(self):
        """Test text shorter than max length."""
        result = truncate_text("Hello", 100)
        assert result == "Hello"

    def test_exact_length(self):
        """Test text exactly at max length."""
        text = "A" * 100
        result = truncate_text(text, 100)
        assert result == text

    def test_long_text(self):
        """Test text longer than max length."""
        text = "A" * 150
        result = truncate_text(text, 100)
        assert len(result) == 100
        assert result.endswith("...")

    def test_custom_max_length(self):
        """Test with custom max length."""
        result = truncate_text("Hello World", 8)
        assert result == "Hello..."

    def test_empty_string(self):
        """Test empty string."""
        result = truncate_text("", 100)
        assert result == ""


class TestSafeGet:
    """Tests for safe_get function."""

    def test_simple_key(self):
        """Test getting simple key."""
        data = {"name": "test"}
        result = safe_get(data, "name")
        assert result == "test"

    def test_nested_keys(self):
        """Test getting nested keys."""
        data = {"level1": {"level2": {"level3": "value"}}}
        result = safe_get(data, "level1", "level2", "level3")
        assert result == "value"

    def test_missing_key(self):
        """Test missing key returns default."""
        data = {"name": "test"}
        result = safe_get(data, "missing")
        assert result is None

    def test_missing_nested_key(self):
        """Test missing nested key returns default."""
        data = {"level1": {"level2": "value"}}
        result = safe_get(data, "level1", "missing", "level3")
        assert result is None

    def test_custom_default(self):
        """Test custom default value."""
        data = {"name": "test"}
        result = safe_get(data, "missing", default="default_value")
        assert result == "default_value"

    def test_non_dict_intermediate(self):
        """Test non-dict intermediate value."""
        data = {"level1": "not_a_dict"}
        result = safe_get(data, "level1", "level2")
        assert result is None

    def test_empty_dict(self):
        """Test empty dictionary."""
        result = safe_get({}, "key")
        assert result is None
