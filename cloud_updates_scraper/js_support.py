# Import the js_scraper module if available
try:
    from . import js_scraper
    JS_SCRAPER_AVAILABLE = True
except ImportError:
    try:
        import js_scraper
        JS_SCRAPER_AVAILABLE = True
    except ImportError:
        JS_SCRAPER_AVAILABLE = False
