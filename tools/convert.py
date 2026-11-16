#!/usr/bin/env python3
"""
One-time converter: Squarespace snapshot (_source/) -> clean static site (public/).

It reads the *rendered* DOM snapshots captured from the live site (so client-side
widgets such as forms, galleries and the product page are present), strips every
Squarespace runtime script / attribute / CDN URL, rewrites media to local files and
writes plain HTML pages. Interactive behaviour is re-implemented in
public/assets/js/site.js. Styling: public/assets/css/theme.css is the site's own
theme CSS tree-shaken to what the pages use (see tools/build-css.mjs) and
public/assets/css/site.css holds the hand-written styles for the rebuilt parts.

You normally never need to run this again: edit the HTML in public/ directly.
"""
import json, os, re, sys, shutil, html as htmlmod, urllib.parse, copy
from bs4 import BeautifulSoup, Comment, NavigableString
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, '_source')
OUT = os.path.join(ROOT, 'public')
SITE = 'https://www.thecurltapes.com'
IMG_OUT = os.path.join(OUT, 'assets', 'img')

IMGMAP = json.load(open(os.path.join(SRC, 'imgmap.json')))
VIDEOS = {
    '1a4f2038-5fea-41c2-8e93-9c1effdf1f01': 'brunswick-yellow-flowers',
    '638249be-15e8-4381-bb1a-ba6698604b63': 'brunswick-sadness-is-a-demon',
    '9a8fc0b0-0bb5-4a7a-a933-6a61af0f1640': 'live-at-the-landrys',
}

# (output path, rendered snapshot name, extra options)
PAGES = [
    ('/', 'index', {}),
    ('/thecurltapes', 'index', {'canonical': '/'}),
    ('/thecurltapes/project-one-h346n-gjtmc', 'thecurltapes_project-one-h346n-gjtmc', {}),
    ('/thecurltapes/hayloft', 'thecurltapes_hayloft', {}),
    ('/aboutpage', 'aboutpage', {}),
    ('/aboutpage/colemanmartin', 'aboutpage_colemanmartin', {}),
    ('/aboutpage/blakezuniga', 'aboutpage_blakezuniga', {}),
    ('/aboutpage/mics-and-tape-machines', 'aboutpage_mics-and-tape-machines', {}),
    ('/contact-6', 'contact-6', {}),
    ('/cole-contact', 'cole-contact', {}),
    ('/cole-contact-1', 'cole-contact-1', {}),
    ('/blake-gg', 'blake-gg', {}),
    ('/blake-gg/project-two-ky966-n329z-nnx53-feazs-s32gp-b59d5-ldeaf', 'blake-gg_project-two-ky966-n329z-nnx53-feazs-s32gp-b59d5-ldeaf', {}),
    ('/portfolio', 'portfolio', {}),
    ('/portfolio/new-portfolio-item', 'portfolio_new-portfolio-item', {}),
    ('/cole-bio', 'cole-bio', {}),
    ('/blake-bio', 'blake-bio', {}),
    ('/store', 'store', {}),
    ('/store/p/the-curl-tapes-and-friends-sparrow-nest-theater', 'store_p_the-curl-tapes-and-friends-sparrow-nest-theater', {}),
    ('/cart', 'cart', {'cart': True}),
    ('/404', 'cart', {'notfound': True, 'out': '404.html', 'title': 'Page Not Found — The Curl Tapes', 'canonical': '/'}),
    ('/joon', 'joon', {}),
    ('/joon/project-one-f5w4d-z9nem-s3jda-eyssk-73f62-tmxz9-b5w3t', 'joon_project-one-f5w4d-z9nem-s3jda-eyssk-73f62-tmxz9-b5w3t', {}),
    ('/joon/project-four-l3zw3-dk9py-xcmem-llk7k-y7dbp-gy66a-namzd', 'joon_project-four-l3zw3-dk9py-xcmem-llk7k-y7dbp-gy66a-namzd', {}),
    ('/joon/project-two-ky966-n329z-nnx53-feazs-s32gp-b59d5-a4pr7', 'joon_project-two-ky966-n329z-nnx53-feazs-s32gp-b59d5-a4pr7', {}),
]

NAV = [('About', '/aboutpage'), ('Contact', '/contact-6'), ('Home', '/')]

# attributes that only exist for the Squarespace runtime
DROP_ATTRS = {
    'data-current-context', 'data-current-styles', 'data-block-css', 'data-block-scripts',
    'data-block-json', 'data-controller', 'data-controllers-bound', 'data-image',
    'data-image-dimensions', 'data-image-focal-point', 'data-src', 'data-load', 'data-loader',
    'data-image-component', 'elementtiming', 'data-licensed-asset-preview', 'data-stretch',
    'data-bpo', 'data-breakpoints', 'data-component-id', 'data-website-component-id',
    'data-test', 'data-temporary-legacy-id', 'data-json-schema-section', 'data-config-video',
    'data-config-settings', 'data-config-loading', 'data-sqsp-image-block-image',
    'data-sqsp-image-block-link', 'data-sqsp-image-block-image-container', 'crossorigin',
    'data-block-type', 'data-image-resolution', 'data-parent-ratio', 'data-use-advanced-positioning',
    'data-dynamic-strings', 'data-error-401', 'data-error-404', 'data-error-429', 'data-error-500',
    'data-error-form-key', 'data-error-submit', 'data-error-unknown', 'data-collection-id',
    'data-form-id', 'data-object-name', 'x-autocompletetype', 'data-sqsp-text-block-content',
    'fetchpriority', 'data-edit-main-image', 'data-product-id',
    'data-item-id', 'data-variant-id', 'data-first-section-padding-override',
}

# ---------------------------------------------------------------- media helpers
def norm_url(u):
    if not u:
        return u
    u = htmlmod.unescape(u.strip())
    if u.startswith('//'):
        u = 'https:' + u
    u = u.replace('http://', 'https://')
    return u.split('?')[0].split('#')[0]

_img_cache = {}
def local_image(u):
    """Return dict(src, srcset, w, h) for a Squarespace image URL, copying/resizing locally."""
    key = norm_url(u)
    if key not in IMGMAP:
        # try decoded/encoded variants
        alt = [k for k in IMGMAP if urllib.parse.unquote(k) == urllib.parse.unquote(key)]
        if not alt:
            return None
        key = alt[0]
    if key in _img_cache:
        return _img_cache[key]
    name = IMGMAP[key]
    src_file = os.path.join(SRC, 'img-originals', name)
    os.makedirs(IMG_OUT, exist_ok=True)
    dst = os.path.join(IMG_OUT, name)
    if not os.path.exists(dst):
        shutil.copy2(src_file, dst)
    info = {'src': '/assets/img/' + name, 'srcset': '', 'w': None, 'h': None}
    if name.endswith('.ico'):
        _img_cache[key] = info
        return info
    try:
        im = Image.open(src_file)
        w, h = im.size
        info['w'], info['h'] = w, h
        parts = []
        for tw in (750, 1500):
            if w > tw * 1.15:
                vdir = os.path.join(IMG_OUT, str(tw))
                os.makedirs(vdir, exist_ok=True)
                vpath = os.path.join(vdir, name)
                if not os.path.exists(vpath):
                    th = round(h * tw / w)
                    r = im.convert('RGBA' if name.endswith('.png') else 'RGB').resize((tw, th), Image.LANCZOS)
                    if name.endswith('.png'):
                        r.save(vpath, optimize=True)
                    else:
                        r.save(vpath, quality=84, optimize=True, progressive=True)
                parts.append(f'/assets/img/{tw}/{name} {tw}w')
        parts.append(f'/assets/img/{name} {w}w')
        info['srcset'] = ', '.join(parts)
        # sensible default src: 1500 variant if present (keeps pages light)
        if any(p.startswith('/assets/img/1500/') for p in parts):
            info['src'] = f'/assets/img/1500/{name}'
        info['full'] = '/assets/img/' + name
    except Exception as e:
        print('WARN image', name, e, file=sys.stderr)
    _img_cache[key] = info
    return info

def best_img_url(img):
    for a in ('data-src', 'data-image', 'src'):
        v = img.get(a)
        if v and ('squarespace' in v):
            return v
    return img.get('src')

def rewrite_img(img, eager=False):
    u = best_img_url(img)
    info = local_image(u) if u else None
    if info is None:
        if u and 'squarespace' in u:
            print('WARN unmapped image', u, file=sys.stderr)
        return
    img['src'] = info['src']
    if info.get('srcset'):
        img['srcset'] = info['srcset']
        if not img.get('sizes') or img.get('sizes') in ('0', 'auto'):
            img['sizes'] = '100vw'
        img['sizes'] = img['sizes'].replace('auto, ', '')
    elif img.has_attr('srcset'):
        del img['srcset']
    if info.get('w'):
        img['width'], img['height'] = str(info['w']), str(info['h'])
    img['data-full'] = info.get('full', info['src'])
    img['decoding'] = 'async'
    if eager:
        img['loading'] = 'eager'
        if img.has_attr('loading') and img['loading'] == 'lazy':
            img['loading'] = 'eager'
    else:
        img['loading'] = 'lazy'
    st = img.get('style', '')
    st = re.sub(r'display:\s*none;?', '', st)
    img['style'] = st

def rewrite_style_urls(tag):
    st = tag.get('style')
    if st and 'squarespace' in st:
        def rep(m):
            info = local_image(m.group(2))
            return f"url({m.group(1)}{info['src'] if info else ''}{m.group(1)})"
        tag['style'] = re.sub(r'url\(([\'"]?)([^\'")]+)\1\)', rep, st)

# ---------------------------------------------------------------- generic cleaning
def clean_links(root):
    for a in root.find_all('a', href=True):
        h = a['href']
        for pre in (SITE, 'https://thecurltapes.com', 'http://www.thecurltapes.com', 'http://thecurltapes.com'):
            if h.startswith(pre):
                h = h[len(pre):] or '/'
        a['href'] = h
        if a.get('target') == '_blank':
            a['rel'] = 'noopener'

def strip_runtime(root):
    for t in root.find_all(['script', 'noscript', 'iframe', 'link']):
        t.decompose()
    for c in root.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    for sel in ['.sqs-blockStatus', '.newsletter-form-banner', '.captcha-container',
                '.gallery-lightbox', '.product-image-zoom-duplicate', '.product-payment-method-messaging',
                '.sqs-block-image .image-overlay', '.sqs-cart-dropzone', '.product-list-filters-container',
                '.product-list-filters-drawer-open-button-container', '.product-list-result-count-container',
                '.product-list-category-subnav-container', '.product-list-category-select-container',
                '.product-reviews-section', '.related-products-section', '.form-submission-html',
                '.sqs-form-block-submission-html', '.newsletter-form-spinner', '.cart-loader',
                '.product-restock-notification', '.product-scarcity']:
        for t in root.select(sel):
            t.decompose()

def strip_attrs(root):
    for t in root.find_all(True):
        for a in list(t.attrs):
            if a in DROP_ATTRS or a.startswith('data-config'):
                del t[a]
            elif a == 'data-props' and t.name != 'div':
                del t[a]
        if t.get('class'):
            t['class'] = [c for c in t['class'] if c not in ('}',)]

def fix_inline_styles(root):
    for st in root.find_all('style'):
        txt = st.string or ''
        if 'squarespace' in txt:
            txt = re.sub(r'url\([^)]*squarespace[^)]*\)', 'none', txt)
            st.string = txt
        if not txt.strip():
            st.decompose()
    for t in root.find_all(style=True):
        rewrite_style_urls(t)
    # the theme script pads the first section by the header height; do that in site.js instead
    for sec in root.select('section.page-section'):
        st = sec.get('style') or ''
        if re.search(r'padding-top:\s*[\d.]+px', st):
            st = re.sub(r'padding-top:\s*[\d.]+px;?', '', st).strip()
            if st:
                sec['style'] = st
            else:
                del sec['style']
            sec['data-ct-header-offset'] = ''

# ---------------------------------------------------------------- component transforms
def convert_videos(soup, root):
    for nv in root.select('.sqs-native-video'):
        cfg = None
        # the config lives in the static snapshot; fall back to the block id lookup
        raw = nv.get('data-config-video')
        if raw:
            cfg = json.loads(raw)
        vid = (cfg or {}).get('systemDataId')
        if not vid:
            m = re.search(r'([0-9a-f]{8}-[0-9a-f-]{27})', str(nv))
            vid = m.group(1) if m else None
        name = VIDEOS.get(vid)
        if not name:
            print('WARN unknown video', vid, file=sys.stderr)
            continue
        wrap = soup.new_tag('div', attrs={'class': 'ct-video'})
        v = soup.new_tag('video', attrs={
            'controls': '', 'playsinline': '', 'preload': 'metadata',
            'poster': f'/assets/video/{name}.jpg', 'src': f'/assets/video/{name}.mp4',
            'style': 'aspect-ratio:16/9'})
        v.append(soup.new_tag('source', attrs={'src': f'/assets/video/{name}.mp4', 'type': 'video/mp4'}))
        wrap.append(v)
        nv.replace_with(wrap)

def convert_image_effects(root):
    for ef in root.select('.imageEffectContainer'):
        raw = ef.get('data-effect') or ''
        try:
            d = json.loads(raw)
        except Exception:
            d = {}
        ef.attrs = {'class': ['imageEffectContainer']}
        if d.get('type') == 'filmGrain':
            ef['class'].append('ct-grain')
            ef['style'] = f"--grain-opacity:{min(1, d.get('intensity', 100) / 100) * 0.55:.3f}"
            ef['aria-hidden'] = 'true'
            ef.clear()
        else:
            ef.decompose()

def convert_gallery_grid_links(root):
    for a in root.select('a.gallery-grid-lightbox-link'):
        img = a.find('img')
        if img is not None:
            a['href'] = img.get('data-full') or img.get('src')
        a['data-lightbox'] = ''

def convert_user_items(soup, sec):
    """Rebuild a Squarespace 'user items list' carousel as a simple accessible carousel."""
    ctxel = sec.select_one('[data-current-context]')
    ctx = json.loads(ctxel['data-current-context'])
    opts = ctx.get('options', {})
    items = ctx.get('userItems', [])
    car = soup.new_tag('div', attrs={'class': 'ct-carousel', 'data-ct-carousel': '',
                                     'data-columns': str(opts.get('maxColumns', 3)),
                                     'data-aspect': opts.get('mediaAspectRatio', '1:1').replace(':', '/'),
                                     'style': f"--ct-gap:{opts.get('spaceBetweenSlides',{}).get('value',20)}px;"
                                              f"--ct-pad-top:{opts.get('verticalPaddingTop',{}).get('value',10)}vmax;"
                                              f"--ct-pad-bottom:{opts.get('verticalPaddingBottom',{}).get('value',10)}vmax;"
                                              f"--ct-aspect:{opts.get('mediaAspectRatio','1:1').replace(':','/')}"})
    car['role'] = 'region'
    car['aria-label'] = 'Carousel'
    viewport = soup.new_tag('div', attrs={'class': 'ct-carousel-viewport'})
    track = soup.new_tag('ul', attrs={'class': 'ct-carousel-track'})
    for it in items:
        li = soup.new_tag('li', attrs={'class': 'ct-carousel-slide'})
        im = it.get('image') or {}
        url = im.get('assetUrl')
        info = local_image(url) if url else None
        if info:
            fp = it.get('mediaFocalPoint') or im.get('mediaFocalPoint') or {'x': .5, 'y': .5}
            fig = soup.new_tag('div', attrs={'class': 'ct-carousel-media'})
            a = soup.new_tag('a', attrs={'href': info.get('full', info['src']), 'data-lightbox': ''})
            img = soup.new_tag('img', attrs={'src': info['src'], 'srcset': info['srcset'],
                                             'sizes': '(max-width: 767px) 80vw, 33vw', 'loading': 'lazy',
                                             'decoding': 'async', 'alt': it.get('imageAltText') or '',
                                             'data-full': info.get('full', info['src']),
                                             'style': f"object-position:{fp.get('x',.5)*100:.1f}% {fp.get('y',.5)*100:.1f}%"})
            if info.get('w'):
                img['width'], img['height'] = str(info['w']), str(info['h'])
            a.append(img)
            fig.append(a)
            li.append(fig)
        if opts.get('isTitleEnabled') and it.get('title'):
            h = soup.new_tag('h2', attrs={'class': 'ct-carousel-title'})
            h.string = it['title']
            li.append(h)
        if opts.get('isBodyEnabled') and it.get('description'):
            d = BeautifulSoup(it['description'], 'lxml')
            body = soup.new_tag('div', attrs={'class': 'ct-carousel-body'})
            for c in list((d.body or d).children):
                body.append(c)
            li.append(body)
        track.append(li)
    viewport.append(track)
    car.append(viewport)
    for cls, label, path in (('prev', 'Previous', 'M19 12H5M11 6l-6 6 6 6'), ('next', 'Next', 'M5 12h14M13 6l6 6-6 6')):
        b = soup.new_tag('button', attrs={'class': f'ct-carousel-btn ct-carousel-{cls}', 'type': 'button', 'aria-label': f'{label} slide'})
        b.append(BeautifulSoup(f'<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><path d="{path}" fill="none" stroke="currentColor" stroke-width="1.4"/></svg>', 'html.parser'))
        car.append(b)
    target = sec.select_one('.user-items-list') or sec.select_one('.content') or sec
    target.clear()
    target.append(car)

FORM_RECIPIENT = {'Message Coleman & Blake': 'coleman-and-blake', 'Message Coleman': 'coleman',
                  'Message Blake': 'blake', 'Submit': 'store-questions'}

def static_form_contexts(snap):
    p = os.path.join(SRC, 'static-html', snap + '.html')
    if not os.path.exists(p):
        return []
    s = BeautifulSoup(open(p).read(), 'lxml')
    return [json.loads(sc.string) for sc in s.select('script.sqs-form-block-context')]

def honeypot(soup):
    d = soup.new_tag('div', attrs={'class': 'ct-hp', 'aria-hidden': 'true'})
    i = soup.new_tag('input', attrs={'type': 'text', 'name': 'website', 'tabindex': '-1', 'autocomplete': 'off'})
    d.append(i)
    return d

def convert_forms(soup, root, snap=None):
    """Rendered Squarespace forms -> plain forms handled by site.js."""
    contexts = static_form_contexts(snap) if snap else []
    ci = 0
    for f in root.select('form'):
        if 'newsletter-form' in (f.get('class') or []):
            f['data-ct-form'] = 'newsletter'
            f['action'] = '/api/subscribe'
            f['method'] = 'post'
            f.append(honeypot(soup))
            em = f.select_one('input[type=email]')
            if em:
                em['required'] = ''
            continue
        if f.find_parent(class_='product-detail'):
            continue
        ctx = contexts[ci] if ci < len(contexts) else {}
        ci += 1
        f['data-ct-form'] = 'contact'
        f['action'] = '/api/contact'
        f['method'] = 'post'
        for a in ('data-success-redirect',):
            if f.has_attr(a):
                del f[a]
        btn = f.select_one('button[type=submit]')
        label = btn.get_text(' ', strip=True) if btn else ''
        label = re.sub(r'^(.+?)\s+\1$', r'\1', label)
        if btn:
            for c in list(btn.contents):
                if isinstance(c, NavigableString) and c.strip():
                    pass
        f['data-recipient'] = FORM_RECIPIENT.get(label, 'coleman-and-blake')
        f['data-form-name'] = ctx.get('formName', '')
        # give every control a stable name
        fields = {x.get('type'): x for x in ctx.get('formFields', [])}
        for inp in f.select('input, textarea'):
            iid = inp.get('id', '')
            t = inp.get('type')
            if iid == 'message-field':
                wrap = inp
                while wrap.parent is not None and wrap.parent.name != 'form' and len(wrap.parent.find_all(['input', 'textarea'])) == 1:
                    wrap = wrap.parent
                wrap.decompose()
                continue
            if inp.name == 'textarea':
                inp['name'] = 'message'
            elif t == 'email':
                inp['name'] = 'email'
                inp['autocomplete'] = 'email'
            elif t == 'checkbox':
                inp['name'] = 'newsletter_optin'
                inp['value'] = 'yes'
            elif iid.startswith('phone'):
                inp['name'] = 'phone'
                inp['type'] = 'tel'
                inp['autocomplete'] = 'tel'
            elif 'fname' in iid:
                inp['autocomplete'] = 'given-name'
            elif 'lname' in iid:
                inp['autocomplete'] = 'family-name'
            if inp.get('aria-required') == 'true':
                inp['required'] = ''
        f.append(honeypot(soup))
        msg = (ctx.get('formSubmissionMessage') or {}).get('html') or '<p>Thank you!</p>'
        tpl = soup.new_tag('template', attrs={'class': 'ct-success-html'})
        frag = BeautifulSoup(msg, 'html.parser')
        tpl.append(frag)
        f.append(tpl)

def load_products():
    prods = {}
    for fn in os.listdir(os.path.join(SRC, 'json')):
        if not fn.startswith('store_p_'):
            continue
        try:
            it = json.load(open(os.path.join(SRC, 'json', fn)))['item']
        except Exception:
            continue
        v = (it.get('variants') or [{}])[0]
        form = (it.get('structuredContent') or {}).get('additionalFieldsForm') or {}
        fields = []
        for raw in form.get('fields', []):
            try:
                fd = json.loads(raw)
            except Exception:
                continue
            fields.append({k: fd.get(k) for k in ('id', 'type', 'title', 'description', 'placeholder', 'required')})
        info = local_image(it.get('assetUrl')) if it.get('assetUrl') else None
        prods[it['fullUrl']] = {
            'id': it['urlId'], 'title': it['title'], 'url': it['fullUrl'],
            'price': int(v.get('price', 0)), 'currency': (v.get('priceMoney') or {}).get('currency', 'USD'),
            'sku': v.get('sku'), 'stock': None if v.get('unlimited') else v.get('qtyInStock'),
            'image': info['src'] if info else None,
            'productType': it.get('productType'),
            'formName': (form.get('name') or '').strip(), 'fields': fields,
        }
    return prods

PRODUCTS = None
def convert_products(root):
    global PRODUCTS
    if PRODUCTS is None:
        PRODUCTS = load_products()
    pd = root.select_one('.product-detail')
    if pd is not None:
        for url, p in PRODUCTS.items():
            if root.select_one(f'a[href="{url}"]') is not None:
                pd['data-ct-product'] = json.dumps(p, ensure_ascii=False)
                break
        # quantity buttons: keep markup, site.js wires them
        q = pd.select_one('input[name=quantity-input]')
        if q is not None:
            q['aria-label'] = 'Quantity'
    for li in root.select('.product-list-item'):
        a = li.select_one('a[href^="/store/p/"]')
        if a and a['href'] in PRODUCTS:
            li['data-ct-product'] = json.dumps(PRODUCTS[a['href']], ensure_ascii=False)

def convert_portfolio_hover(root):
    for img in root.select('.portfolio-hover-bg-img img'):
        img['style'] = re.sub(r'display:\s*none;?', '', img.get('style', ''))

# ---------------------------------------------------------------- header
CART_SVG = '<svg class="ct-cart-icon" width="22" height="19" viewBox="0 0 144 125" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="6" d="M4.5 4.5h27l14 82h78l14-60H39"/><circle cx="58" cy="108" r="11" fill="none" stroke="currentColor" stroke-width="6"/><circle cx="111" cy="108" r="11" fill="none" stroke="currentColor" stroke-width="6"/></svg>'

def header_html(path, theme):
    def active(href):
        if href == '/':
            return path == '/' or path.startswith('/thecurltapes')
        return path == href or path.startswith(href + '/')
    links = '\n        '.join(
        f'<a href="{h}"{" class=\"is-active\" aria-current=\"page\"" if active(h) else ""}>{t}</a>' for t, h in NAV)
    mlinks = '\n      '.join(f'<a href="{h}">{t}</a>' for t, h in NAV)
    return f'''<header class="ct-header" data-theme="{theme}">
  <div class="ct-header-inner">
    <a class="ct-site-title" href="/">The Curl Tapes</a>
    <nav class="ct-nav" aria-label="Main">
        {links}
    </nav>
    <a class="ct-cart" href="/cart" aria-label="Cart" hidden>{CART_SVG}<span class="ct-cart-count">0</span></a>
    <button class="ct-burger" type="button" aria-label="Open Menu" aria-expanded="false" aria-controls="ct-menu">
      <span></span><span></span>
    </button>
  </div>
</header>
<div class="ct-menu" id="ct-menu" hidden>
  <nav class="ct-menu-nav" aria-label="Mobile">
      {mlinks}
  </nav>
</div>'''

# ---------------------------------------------------------------- page assembly
def head_html(meta, path, opts):
    title = htmlmod.escape(meta['title'])
    canonical = SITE + (opts.get('canonical') or path)
    lines = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f'<title>{title}</title>',
        f'<link rel="canonical" href="{canonical}">',
        '<link rel="icon" type="image/x-icon" href="/assets/img/favicon-light.ico" media="(prefers-color-scheme: light)">',
        '<link rel="icon" type="image/x-icon" href="/assets/img/favicon-dark.ico" media="(prefers-color-scheme: dark)">',
        '<link rel="icon" type="image/x-icon" href="/favicon.ico">',
    ]
    if meta.get('description'):
        lines.append(f'<meta name="description" content="{htmlmod.escape(meta["description"])}">')
    if meta.get('robots'):
        lines.append(f'<meta name="robots" content="{meta["robots"]}">')
    for k, v in meta.get('og', []):
        lines.append(f'<meta {k[0]}="{k[1]}" content="{htmlmod.escape(v)}">')
    lines += [
        '<link rel="preload" href="/assets/fonts/Newsreader-400-latin.woff2" as="font" type="font/woff2" crossorigin>',
        '<link rel="stylesheet" href="/assets/css/fonts.css">',
        '<link rel="stylesheet" href="/assets/css/theme.css">',
        '<link rel="stylesheet" href="/assets/css/custom.css">',
        '<link rel="stylesheet" href="/assets/css/site.css">',
        '<script src="/assets/js/config.js"></script>',
        '<script src="/assets/js/site.js" defer></script>',
    ]
    for d in meta.get('ld', []):
        lines.append(f'<script type="application/ld+json">{d}</script>')
    return '\n'.join(lines)

def extract_meta(soup):
    meta = {'title': (soup.title.string or 'The Curl Tapes').strip() if soup.title else 'The Curl Tapes'}
    d = soup.find('meta', attrs={'name': 'description'})
    if d and d.get('content'):
        meta['description'] = d['content']
    r = soup.find('meta', attrs={'name': 'robots'})
    if r and r.get('content'):
        meta['robots'] = r['content']
    og = []
    for m in soup.find_all('meta'):
        p = m.get('property') or ''
        n = m.get('name') or ''
        key = None
        if p.startswith('og:'):
            key = ('property', p)
        elif n.startswith('twitter:'):
            key = ('name', n)
        if key and m.get('content') is not None:
            v = m['content']
            if 'squarespace' in v:
                info = local_image(v)
                v = SITE + (info['full'] if info and info.get('full') else info['src']) if info else ''
                if not v:
                    continue
            og.append((key, v))
    meta['og'] = og
    # structured data (JSON-LD) — the rendered snapshot keeps it in <head>
    ld = []
    for sc in soup.find_all('script', attrs={'type': 'application/ld+json'}):
        try:
            d = json.loads(sc.string or sc.get_text())
        except Exception:
            continue
        def fix(o):
            if isinstance(o, dict):
                for k in list(o):
                    v = o[k]
                    if isinstance(v, str) and 'squarespace' in v:
                        info = local_image(v.replace('static1.squarespace.com/static', 'images.squarespace-cdn.com/content').split('?')[0])
                        if info:
                            o[k] = SITE + (info.get('full') or info['src'])
                        else:
                            ogimg = [val for kk, val in og if kk[1] == 'og:image']
                            if ogimg:
                                o[k] = ogimg[0]
                            else:
                                del o[k]
                    else:
                        fix(v)
            elif isinstance(o, list):
                for x in o:
                    fix(x)
        fix(d)
        ld.append(json.dumps(d, ensure_ascii=False).replace('</', '<\\/'))
    meta['ld'] = ld
    return meta

def first_section_theme(main):
    sec = main.select_one('section.page-section')
    if sec is None:
        return 'light'
    th = sec.get('data-section-theme') or ''
    has_bg = bool(sec.select_one('.section-background img, .sqs-section-background img, .portfolio-hover-bg'))
    if th in ('black', 'dark', 'bright-inverse', 'black-bold') :
        return 'dark'
    return 'light'

def convert_page(path, snap, opts):
    soup = BeautifulSoup(open(os.path.join(SRC, 'rendered-html', snap + '.html')).read(), 'lxml')
    meta = extract_meta(soup)
    body_classes = [c for c in (soup.body.get('class') or []) if not c.startswith('header--menu') and c not in ('sqs-edit-mode',)]
    main = soup.select_one('main#page')
    footer = soup.select_one('footer.sections') or soup.select_one('footer')
    parts = []
    for i, root in enumerate((main, footer)):
        if root is None:
            continue
        strip_runtime(root)
        # user items list sections need their context JSON before attributes are stripped
        for sec in root.select('section.user-items-list-section'):
            convert_user_items(soup, sec)
        convert_videos(soup, root)
        convert_image_effects(root)
        for j, img in enumerate(root.find_all('img')):
            rewrite_img(img, eager=(i == 0 and j < 2))
        convert_gallery_grid_links(root)
        convert_forms(soup, root, snap)
        convert_portfolio_hover(root)
        convert_products(root)
        clean_links(root)
        fix_inline_styles(root)
        strip_attrs(root)
    theme = first_section_theme(main)
    main_inner = ''.join(str(c) for c in main.contents)
    footer_inner = ''.join(str(c) for c in footer.contents) if footer else ''
    if opts.get('cart'):
        main_inner = CART_HTML
    if opts.get('notfound'):
        main_inner = NOTFOUND_HTML
        meta = {'title': opts['title'], 'robots': 'noindex'}
        theme = ''
    doc = f'''<!doctype html>
<html lang="en-US">
<head>
{head_html(meta, path, opts)}
</head>
<body class="{' '.join(body_classes)}">
<a class="ct-skip" href="#page">Skip to content</a>
<div class="site-wrapper" id="siteWrapper">
{header_html(path, theme)}
<main id="page" class="container" role="main">
{main_inner}
</main>
<footer class="sections" id="footer-sections" data-footer-sections>
{footer_inner}
</footer>
</div>
</body>
</html>
'''
    doc = tidy(doc)
    if opts.get('out'):
        out = os.path.join(OUT, opts['out'])
    else:
        out = os.path.join(OUT, path.strip('/'), 'index.html') if path != '/' else os.path.join(OUT, 'index.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w').write(doc)
    return out, footer_inner, body_classes

NOTFOUND_HTML = '''
<article class="sections">
<section class="page-section ct-cart-section" data-section-theme="">
  <div class="content-wrapper"><div class="content">
    <div class="system-page ct-system-page">
      <h1>Page Not Found</h1>
      <p>We couldn't find the page you were looking for. This is either because:</p>
      <ul>
        <li>There is an error in the URL entered into your web browser. Please check the URL and try again.</li>
        <li>The page you are looking for has been moved or deleted.</li>
      </ul>
      <p>You can return to our homepage by <a href="/">clicking here</a>.</p>
    </div>
  </div></div>
</section>
</article>
'''

CART_HTML = '''
<article class="sections">
<section class="page-section ct-cart-section" data-section-theme="">
  <div class="content-wrapper"><div class="content">
    <div class="ct-cart-page" data-ct-cart-page>
      <h1 class="ct-cart-title">Shopping Cart</h1>
      <div class="ct-cart-empty" data-cart-empty>
        <p>You have nothing in your shopping cart.</p>
        <a class="sqs-button-element--secondary ct-btn-secondary" href="/">Continue Shopping</a>
      </div>
      <div class="ct-cart-full" data-cart-full hidden>
        <ul class="ct-cart-items" data-cart-items></ul>
        <div class="ct-cart-summary">
          <div class="ct-cart-subtotal"><span>Subtotal</span><span data-cart-subtotal>$0.00</span></div>
          <button class="sqs-button-element--primary ct-btn-primary" type="button" data-cart-checkout>Checkout</button>
          <p class="ct-cart-note" data-cart-note hidden></p>
        </div>
      </div>
    </div>
  </div></div>
</section>
</article>
'''

def tidy(doc):
    # collapse runs of blank lines / whitespace-only lines for readability
    doc = re.sub(r'[ \t]+\n', '\n', doc)
    doc = re.sub(r'\n\s*\n\s*\n+', '\n\n', doc)
    return doc

def main():
    os.makedirs(OUT, exist_ok=True)
    # favicons
    for k, v in IMGMAP.items():
        if v.endswith('.ico'):
            pass
    fav = [k for k in IMGMAP if k.endswith('favicon.ico')]
    light = [k for k in fav if '14752211' in k][0]
    dark = [k for k in fav if '232bb7c6' in k][0]
    os.makedirs(IMG_OUT, exist_ok=True)
    shutil.copy2(os.path.join(SRC, 'img-originals', IMGMAP[light]), os.path.join(IMG_OUT, 'favicon-light.ico'))
    shutil.copy2(os.path.join(SRC, 'img-originals', IMGMAP[dark]), os.path.join(IMG_OUT, 'favicon-dark.ico'))
    shutil.copy2(os.path.join(SRC, 'img-originals', IMGMAP[light]), os.path.join(OUT, 'favicon.ico'))
    footer = None
    for path, snap, opts in PAGES:
        out, footer_inner, body_classes = convert_page(path, snap, opts)
        footer = footer or (footer_inner, body_classes)
        print('wrote', out)
    json.dump({'footer': footer[0], 'body_classes': footer[1]}, open(os.path.join(ROOT, 'tools', '.shared.json'), 'w'))

if __name__ == '__main__':
    main()
