# firefox-omnisearch

A quick and dirty workaround to improve the current state of Firefox search engines.

## Installation

1. Start `server.py` on the machine where Firefox is.
2. In Firefox, open Browser Console (`Ctrl+Shift+j`), and then run `Services.search.addEngine("file:///PATH/TO/firefox-omnisearch/engine.xml", null, null, false)`
3. Make sure no keywords in bookmarks or One-Click Search Engines overlap with the ones in `engines/` (if you want them to work).
4. Make omnisearch the default search engine and optionally enable search suggestions for it.

## Adding search engines

When `server.py` starts, it automatically loads every search engine definition in `engines/`.
The keyword will be the filename without the extension. Default search engine is defined by 
adding `.default` before the file extension. Default search engine is used when the query 
doesn't match a keyword.

If search suggestions aren't of the format `["query", ["result1", "result2"]]`, their parsing 
has to be implemented separately in `server.py`.
