from typing import Iterable, Dict, Any

class SourcePlugin:
    """Base class for a data source plugin."""
    name = "base"

    def fetch(self, **kwargs) -> Iterable[Dict[str, Any]]:
        """Yield dicts representing 'policy items' in a common schema.
        Schema suggestion (keys optional as appropriate):
        {
          'source': 'rss'|'openstates'|...,
          'jurisdiction': 'CA' or 'California' or None,
          'title': str,
          'summary': str,
          'url': str,
          'status': 'ANNOUNCEMENT'|'EFFECTIVE'|'ENACTED'|'NOTICE'|...,
          'effective_date': 'YYYY-MM-DD'|None,
          'updated_at': 'YYYY-MM-DD',
          'topic_labels': 'ai,privacy' (comma string),
        }
        """
        raise NotImplementedError
