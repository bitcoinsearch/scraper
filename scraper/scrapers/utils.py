from datetime import datetime
from typing import Optional


def parse_standard_date_formats(date_str: str) -> Optional[str]:
    """Try to parse date string using common formats, return ISO format if successful."""
    # List of common date formats to try
    formats = [
        # Standard dates
        "%Y-%m-%d",  # 2024-03-13
        "%Y/%m/%d",  # 2024/03/13
        # Full month name
        "%B %d, %Y",  # March 13, 2024
        "%d %B %Y",  # 13 March 2024
        # Abbreviated month
        "%b %d, %Y",  # Jan 16, 2024
        "%d %b %Y",  # 16 Jan 2024
        # With times
        "%Y-%m-%d %H:%M:%S",  # 2024-03-13 14:30:00
        "%Y-%m-%d %H:%M",  # 2024-03-13 14:30
        "%B %d, %Y, %I:%M:%S %p",  # March 13, 2024, 02:30:00 PM
        "%B %d, %Y, %I:%M %p",  # March 13, 2024, 02:30 PM
        "%b %d, %Y, %I:%M:%S %p",  # Jan 13, 2024, 02:30:00 PM
        "%b %d, %Y, %I:%M %p",  # Jan 13, 2024, 02:30 PM
        "%d %B %Y %H:%M:%S",  # 13 March 2024 14:30:00
        "%d %B %Y %H:%M",  # 13 March 2024 14:30
        "%d %b %Y %H:%M:%S",  # 13 Jan 2024 14:30:00
        "%d %b %Y %H:%M",  # 13 Jan 2024 14:30
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).isoformat()
        except ValueError:
            continue
    return None
