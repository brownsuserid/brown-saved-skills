"""Tests for paginator module."""

import pytest
from src.paginator import iter_all_pages, paginate


class TestPaginate:
    def test_first_page(self):
        items = list(range(25))
        result = paginate(items, page=1, page_size=10)
        assert result["items"] == list(range(10))
        assert result["page"] == 1
        assert result["total_items"] == 25

    def test_middle_page(self):
        items = list(range(25))
        result = paginate(items, page=2, page_size=10)
        assert result["items"] == list(range(10, 20))

    def test_exact_multiple(self):
        items = list(range(20))
        result = paginate(items, page=1, page_size=10)
        assert result["total_pages"] == 2

    def test_invalid_page(self):
        with pytest.raises(ValueError, match="page must be >= 1"):
            paginate([1, 2, 3], page=0)

    def test_invalid_page_size(self):
        with pytest.raises(ValueError, match="page_size must be >= 1"):
            paginate([1, 2, 3], page_size=0)

    def test_empty_list(self):
        result = paginate([], page=1, page_size=10)
        assert result["items"] == []
        assert result["total_items"] == 0


class TestIterAllPages:
    def test_exact_pages(self):
        items = list(range(20))
        pages = iter_all_pages(items, page_size=10)
        assert len(pages) == 2
        assert pages[0] == list(range(10))
        assert pages[1] == list(range(10, 20))

    def test_single_page(self):
        items = [1, 2, 3]
        pages = iter_all_pages(items, page_size=10)
        assert len(pages) == 1
        assert pages[0] == [1, 2, 3]

    def test_empty_list(self):
        pages = iter_all_pages([], page_size=10)
        assert pages == []
