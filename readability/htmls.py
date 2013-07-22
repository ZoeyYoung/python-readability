from .cleaners import normalize_spaces, clean_attributes
from .encoding import decode_html
from lxml.html import document_fromstring
from lxml.html import tostring
from lxml.html import soupparser
import logging
import re


logging.getLogger().setLevel(logging.DEBUG)

# utf8_parser = lxml.html.HTMLParser(encoding='utf-8')


def build_doc(page):
    """解析HTML
    @para page: 爬取的页面
    @return <class 'lxml.html.HtmlElement'> 类型对象
    """
    # lxml.html.document_fromstring(string): Parses a document from the given string. This always creates a correct HTML document, which means the parent node is <html>, and there is a body and possibly a head.
    doc = document_fromstring(decode_html(page))
    try:
        tostring(doc, encoding='unicode')
    except UnicodeDecodeError:
        """Using soupparser as a fallback
        """
        print("Using soupparser as a fallback")
        doc = soupparser.fromstring(decode_html(page))
    return doc


def js_re(src, pattern, flags, repl):
    return re.compile(pattern, flags).sub(src, repl.replace('$', '\\'))


def normalize_entities(cur_title):
    entities = {
        '\u2014': '-',
        '\u2013': '-',
        '&mdash;': '-',
        '&ndash;': '-',
        '\u00A0': ' ',
        '\u00AB': '"',
        '\u00BB': '"',
        '&quot;': '"',
    }
    for c, r in list(entities.items()):
        if c in cur_title:
            cur_title = cur_title.replace(c, r)

    return cur_title


def norm_title(title):
    return normalize_entities(normalize_spaces(title))


def get_title(doc):
    title = doc.find('.//title')
    if title is None or len(title.text) == 0:
        return '[no-title]'

    return norm_title(title.text)


def get_description(doc):
    description = doc.xpath("//meta[translate(@name, 'ABCDEFGHJIKLMNOPQRSTUVWXYZ', 'abcdefghjiklmnopqrstuvwxyz')='description']")
    if len(description) <= 0:
        return '[no-description]'

    return description[0].attrib["content"]


def get_keywords(doc):
    keywords = doc.xpath("//meta[translate(@name, 'ABCDEFGHJIKLMNOPQRSTUVWXYZ', 'abcdefghjiklmnopqrstuvwxyz')='keywords']")
    if len(keywords) <= 0:
        return ''

    return keywords[0].attrib["content"]


def add_match(collection, text, orig):
    text = norm_title(text)
    if len(text.split()) >= 2 and len(text) >= 15:
        if text.replace('"', '') in orig.replace('"', ''):
            collection.add(text)


def shorten_title(doc):
    title = doc.find('.//title')
    if title is None or title.text is None or len(title.text) == 0:
        return ''

    title = orig = norm_title(title.text)

    candidates = set()

    for item in ['.//h1', './/h2', './/h3']:
        for e in list(doc.iterfind(item)):
            if e.text:
                add_match(candidates, e.text, orig)
            if e.text_content():
                add_match(candidates, e.text_content(), orig)

    for item in ['#title', '#head', '#heading', '.pageTitle', '.news_title', '.title', '.head', '.heading', '.contentheading', '.small_header_red']:
        for e in doc.cssselect(item):
            if e.text:
                add_match(candidates, e.text, orig)
            if e.text_content():
                add_match(candidates, e.text_content(), orig)

    if candidates:
        title = sorted(candidates, key=len)[-1]
    else:
        for delimiter in [' | ', ' - ', ' :: ', ' / ']:
            if delimiter in title:
                parts = orig.split(delimiter)
                if len(parts[0].split()) >= 4:
                    title = parts[0]
                    break
                elif len(parts[-1].split()) >= 4:
                    title = parts[-1]
                    break
        else:
            if ': ' in title:
                parts = orig.split(': ')
                if len(parts[-1].split()) >= 4:
                    title = parts[-1]
                else:
                    title = orig.split(': ', 1)[1]

    if not 15 < len(title) < 150:
        return orig

    return title


def get_body(doc):
    [elem.drop_tree() for elem in doc.xpath('.//script | .//link | .//style')]
    # raw_html = str(tostring(doc.body or doc))
    raw_html = tostring(doc.body or doc).strip()
    cleaned = clean_attributes(raw_html)
    try:
        # BeautifulSoup(cleaned) #FIXME do we really need to try loading it?
        return cleaned
    except Exception:  # FIXME find the equivalent lxml error
        logging.error("cleansing broke html content: %s\n---------\n%s" %
                      (raw_html, cleaned))
        return raw_html
