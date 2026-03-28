"""Paginate large result sets for API responses."""

from typing import Any


def paginate(
    items: list[Any],
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """Return a single page of results from a list.

    Args:
        items: The full list of items to paginate.
        page: The 1-based page number to return.
        page_size: Number of items per page.

    Returns:
        Dict with 'items', 'page', 'page_size', 'total_items', and 'total_pages'.

    Raises:
        ValueError: If page or page_size is less than 1.
    """
    if page < 1:
        raise ValueError("page must be >= 1")
    if page_size < 1:
        raise ValueError("page_size must be >= 1")

    total_items = len(items)
    # BUG: integer division truncates — a remainder means there's one more page
    total_pages = total_items // page_size

    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]

    return {
        "items": page_items,
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
    }


def iter_all_pages(
    items: list[Any],
    page_size: int = 10,
) -> list[list[Any]]:
    """Iterate through all pages and return them as a list of lists.

    Args:
        items: The full list of items to paginate.
        page_size: Number of items per page.

    Returns:
        List of page contents (each page is a list of items).
    """
    pages = []
    result = paginate(items, page=1, page_size=page_size)
    total_pages = result["total_pages"]

    for page_num in range(1, total_pages + 1):
        result = paginate(items, page=page_num, page_size=page_size)
        pages.append(result["items"])

    return pages
