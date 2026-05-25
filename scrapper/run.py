#!/usr/bin/env python3
"""
Playwright-based scraper for HappyHippieYoga.nl products.
Handles Cloudflare + Elementor + WooCommerce dynamic loading.
"""
import json, csv, os, re, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

CATEGORY_URL = "https://happyhippieyoga.nl/yoga-pilates-sokken/"

def scrape():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ])
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            locale='nl-NL',
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        page.set_default_timeout(120000)

        # Add route interceptor to handle consent/blockers
        page.route("**/*", lambda route: route.continue_())

        # Load category page - use domcontentloaded first
        print("Loading category page...")
        page.goto(CATEGORY_URL, wait_until='domcontentloaded', timeout=120000)
        
        # Wait for Cloudflare to finish and trigger WP Rocket lazy loading
        print("Waiting for page to fully load...")
        try:
            page.wait_for_timeout(8000)
            
            # Try to accept cookies
            accept_btns = page.query_selector_all('.cmplz-accept, [aria-label*="accepteren"], .cc-accept, .accept, #cn-accept-cookie')
            if accept_btns:
                accept_btns[0].click()
                print("Accepted cookies")
                page.wait_for_timeout(2000)
        except:
            pass
            
        # Trigger WP Rocket lazy loading by simulating user interaction
        print("Triggering page interactions to load dynamic content...")
        page.evaluate('''() => {
            // Dispatch multiple events that WP Rocket listens for
            const events = ['mousemove', 'keydown', 'touchstart', 'scroll', 'click'];
            events.forEach(type => {
                document.dispatchEvent(new Event(type, {bubbles: true}));
            });
            // Scroll to trigger lazy loading
            window.scrollBy(0, 100);
        }''')
        page.wait_for_timeout(5000)

        # Wait for network to settle
        try:
            page.wait_for_load_state('networkidle', timeout=45000)
        except:
            print("  Network didn't fully settle, continuing...")
        
        page.wait_for_timeout(3000)

        # Scroll to bottom to trigger lazy loaded images/products
        for _ in range(5):
            page.evaluate('window.scrollBy(0, 600)')
            page.wait_for_timeout(1000)
        page.wait_for_timeout(3000)

        # Save what we have
        html = page.content()
        with open('category_rendered.html', 'w', encoding='utf-8') as f:
            f.write(html)
        page.screenshot(path='category_screenshot.png', full_page=True)
        print(f"HTML saved ({len(html)} bytes), screenshot saved")

        # Try multiple methods to find product URLs
        product_urls = []
        
        # Method 1: Extract from JavaScript data or via evaluate
        print("Attempting to extract products from page...")
        
        # Look for Elementor product grid
        product_data = page.evaluate('''() => {
            const results = new Set();
            
            // Method A: All links with product in href
            document.querySelectorAll('a').forEach(a => {
                try {
                    if (a.href && a.href.includes('/product/')) {
                        results.add(a.href);
                    }
                } catch(e) {}
            });
            
            // Method B: WooCommerce product items
            document.querySelectorAll('li.product, .product-item, [class*="product_"], ' +
                '.elementor-product, [data-product-id], .wc-block-grid__product').forEach(el => {
                const link = el.querySelector('a[href]');
                if (link) try { results.add(link.href); } catch(e) {}
            });
            
            // Method C: WooCommerce block grid
            document.querySelectorAll('.wc-block-grid__product-link, .wp-block-button__link').forEach(a => {
                try { if (a.href) results.add(a.href); } catch(e) {}
            });
            
            return Array.from(results);
        }''')
        
        print(f"  Found {len(product_data)} potential product links")
        
        if product_data:
            product_urls = list(dict.fromkeys([u for u in product_data if '/product/' in u]))
        
        if not product_urls:
            print("  No /product/ links found. Checking page structure...")
            
            # Get all unique hrefs
            all_hrefs = page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a[href]'))
                    .map(a => a.href)
                    .filter(h => h && !h.startsWith('javascript'))
                    .filter((v,i,a) => a.indexOf(v) === i);
            }''')
            
            print(f"  Total unique links: {len(all_hrefs)}")
            for h in all_hrefs[:10]:
                print(f"    {h}")
            
            # Check if the content is iframe/object loaded
            all_src = page.evaluate('''() => {
                const el = document.querySelector('[class*="elementor"]');
                return el ? el.outerHTML.substring(0, 500) : 'No elementor found';
            }''')
            print(f"  Elementor check: {all_src[:200]}")
            
            # Try scrolling to trigger lazy load
            print("  Scrolling to trigger lazy loading...")
            page.evaluate('''() => {
                window.scrollTo(0, document.body.scrollHeight);
            }''')
            page.wait_for_timeout(3000)
            
            # Check again
            product_data = page.evaluate('''() => {
                const links = new Set();
                document.querySelectorAll('a').forEach(a => {
                    try { if (a.href && a.href.includes('/product/')) links.add(a.href); } catch(e) {}
                });
                return Array.from(links);
            }''')
            product_urls = product_data
            print(f"  After scroll: {len(product_urls)} product links")
        
        product_urls = product_urls[:24]
        
        if not product_urls:
            print("\nCRITICAL ERROR: No products found on the page.")
            print("The site likely uses Ajax-loaded products that require interaction.")
            print("Checking for any WooCommerce data in source...")
            
            # Check if WooCommerce REST API is accessible
            api_products = page.evaluate('''async () => {
                try {
                    const r = await fetch('/wp-json/wc/store/products?per_page=24');
                    if (r.ok) {
                        const data = await r.json();
                        return data.map(p => ({title: p.name, url: p.permalink}));
                    }
                    return [{error: 'Status ' + r.status}];
                } catch(e) { return [{error: e.message}]; }
            }''')
            print(f"  API result: {api_products}")
            browser.close()
            return []
        
        print(f"\nProceeding to scrape {len(product_urls)} products")
        
        # STEP 2: Scrape each product
        products = []
        for i, url in enumerate(product_urls):
            print(f"\n[{i+1}/{len(product_urls)}] {url}")
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=60000)
                page.wait_for_timeout(5000)
                try:
                    page.wait_for_load_state('networkidle', timeout=15000)
                except:
                    pass
                page.wait_for_timeout(2000)
                
                product = page.evaluate('''() => {
                    const p = {
                        url: window.location.href, title: '', sku: '',
                        regular_price: '', sale_price: '', description: '',
                        short_description: '', categories: [], tags: [], images: [],
                        attributes: [], variations: [], specifications: {},
                        weight: '', dimensions: '', stock_status: ''
                    };
                    
                    const titleEl = document.querySelector('.product_title') || document.querySelector('h1');
                    if (titleEl) p.title = titleEl.innerText.trim();
                    
                    const priceEl = document.querySelector('.price');
                    if (priceEl) {
                        const amts = priceEl.querySelectorAll('.amount, .woocommerce-Price-amount');
                        if (amts.length >= 2) {
                            p.sale_price = amts[0].innerText.trim();
                            p.regular_price = amts[1].innerText.trim();
                        } else if (amts.length === 1) {
                            p.regular_price = amts[0].innerText.trim();
                        } else {
                            p.regular_price = priceEl.innerText.trim();
                        }
                    }
                    
                    const skuEl = document.querySelector('.sku');
                    if (skuEl) p.sku = skuEl.innerText.trim();
                    
                    const sd = document.querySelector('.woocommerce-product-details__short-description');
                    if (sd) p.short_description = sd.innerHTML.trim();
                    
                    const desc = document.querySelector('.woocommerce-Tabs-panel--description, #tab-description');
                    if (desc) p.description = desc.innerHTML.trim();
                    
                    const catEl = document.querySelector('.posted_in');
                    if (catEl) {
                        p.categories = Array.from(catEl.querySelectorAll('a')).map(a => a.innerText.trim());
                    }
                    
                    const tagEl = document.querySelector('.tagged_as');
                    if (tagEl) {
                        p.tags = Array.from(tagEl.querySelectorAll('a')).map(a => a.innerText.trim());
                    }
                    
                    const mainImg = document.querySelector('.wp-post-image');
                    if (mainImg) p.main_image = mainImg.getAttribute('data-src') || mainImg.src || '';
                    const galleryImgs = document.querySelectorAll('.woocommerce-product-gallery__image img');
                    p.gallery = Array.from(galleryImgs)
                        .map(img => img.getAttribute('data-src') || img.src || '')
                        .filter(s => s && s !== p.main_image);
                    p.images = [p.main_image, ...p.gallery].filter(s => s);
                    
                    const specTable = document.querySelector('.woocommerce-product-attributes.shop_attributes, ' +
                        '.woocommerce-Tabs-panel--additional_information table.shop_attributes');
                    if (specTable) {
                        specTable.querySelectorAll('tr').forEach(row => {
                            const th = row.querySelector('th');
                            const td = row.querySelector('td');
                            if (th && td) p.specifications[th.innerText.trim()] = td.innerText.trim();
                        });
                    }
                    
                    const wEl = document.querySelector('.product_weight');
                    if (wEl) p.weight = wEl.innerText.trim();
                    const dEl = document.querySelector('.product_dimensions');
                    if (dEl) p.dimensions = dEl.innerText.trim();
                    
                    const sEl = document.querySelector('.stock');
                    if (sEl) p.stock_status = sEl.innerText.trim();
                    
                    return p;
                }''')
                
                if not product or not product.get('title'):
                    print("  ✗ No product data found on page")
                    continue
                
                # Clean prices
                for pk in ['regular_price', 'sale_price']:
                    val = product.get(pk, '')
                    if val:
                        val = val.replace('€', '').replace(',', '.').replace(' ', '').strip()
                        m = re.search(r'(\d+\.?\d*)', val)
                        if m: product[pk] = m.group(1)
                
                # Extract variations
                variations = page.evaluate('''() => {
                    const form = document.querySelector('.variations_form');
                    if (!form) return [];
                    const data = form.getAttribute('data-product_variations');
                    if (!data) return [];
                    try {
                        return JSON.parse(data.replace(/"/g, '"').replace(/&#034;/g, '"'));
                    } catch(e) { return []; }
                }''')
                
                if variations:
                    processed_vars = []
                    for v in variations:
                        pv = {
                            'sku': v.get('sku', ''),
                            'price': str(v.get('display_price', v.get('price', ''))),
                            'regular_price': str(v.get('display_regular_price', v.get('regular_price', ''))),
                            'sale_price': str(v.get('display_sale_price', v.get('sale_price', ''))),
                            'stock': str(v.get('max_qty', v.get('stock_quantity', '') or '')),
                            'in_stock': v.get('is_in_stock', True),
                            'image': v.get('image', {}).get('url', '') if isinstance(v.get('image'), dict) else '',
                            'weight': v.get('weight', ''),
                            'dimensions': '',
                            'attributes': {}
                        }
                        dims = v.get('dimensions', {})
                        if isinstance(dims, dict) and any(dims.get(k) for k in ('length','width','height')):
                            pv['dimensions'] = ' x '.join(filter(None, [dims.get('length',''), dims.get('width',''), dims.get('height','')]))
                        
                        for key, val in v.items():
                            if key.startswith('attribute_'):
                                clean_key = key.replace('attribute_pa_','').replace('attribute_','').replace('-',' ').title()
                                pv['attributes'][clean_key] = val
                        processed_vars.append(pv)
                    
                    product['variations'] = processed_vars
                    print(f"  Found {len(processed_vars)} variations")
                
                # Extract attributes from selects
                attrs = page.evaluate('''() => {
                    const result = [];
                    document.querySelectorAll('.variations select').forEach(sel => {
                        const name = sel.getAttribute('data-attribute_name') || sel.name || sel.id || '';
                        const clean = name.replace(/^attribute_/, '').replace(/^pa_/, '').replace(/-/g, ' ').replace(/\\b\\w/g, c => c.toUpperCase()).trim();
                        const opts = Array.from(sel.options).map(o => o.value).filter(v => v);
                        if (clean && opts.length) result.push({name: clean, options: opts});
                    });
                    return result;
                }''')
                
                if attrs:
                    product['attributes'] = attrs
                
                print(f"  ✓ {product['title'][:55]}")
                print(f"    Price: €{product.get('regular_price', '')} | SKU: {product.get('sku', 'N/A')}")
                
                products.append(product)
                time.sleep(2)
                
            except Exception as e:
                print(f"  ✗ Error: {e}")
                continue
        
        browser.close()
        return products


def export(products):
    if not products:
        print("No products to export")
        return

    # JSON
    with open('products.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    print(f"\nProducts JSON saved: {len(products)} products")

    # WooCommerce CSV
    wc_fields = [
        'ID', 'Type', 'SKU', 'Name', 'Description', 'Short description', 'Price',
        'Regular price', 'Sale price', 'Categories', 'Images', 'Stock', 'Stock status',
        'Weight', 'Dimensions',
        'Attribute 1 name', 'Attribute 1 value(s)', 'Attribute 1 visible', 'Attribute 1 global',
        'Attribute 2 name', 'Attribute 2 value(s)', 'Attribute 2 visible', 'Attribute 2 global'
    ]
    
    with open('woocommerce_products.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        w.writerow(wc_fields)
        
        for p in products:
            attrs = p.get('attributes', [])
            is_var = len(p.get('variations', [])) > 0
            desc = BeautifulSoup(p.get('description', ''), 'html.parser').get_text(strip=True) if p.get('description') else ''
            sdesc = BeautifulSoup(p.get('short_description', ''), 'html.parser').get_text(strip=True) if p.get('short_description') else ''
            
            row = [
                '', 'variable' if is_var else 'simple', p.get('sku', ''), p.get('title', ''),
                desc, sdesc,
                p.get('sale_price', '') or p.get('regular_price', ''),
                p.get('regular_price', ''), p.get('sale_price', ''),
                ', '.join(p.get('categories', [])),
                p.get('images', [''])[0] if p.get('images') else '',
                '', 'instock', p.get('weight', ''), p.get('dimensions', '')
            ]
            for i in range(2):
                if i < len(attrs):
                    row.extend([attrs[i].get('name', ''), ', '.join(attrs[i].get('options', [])), '1', '1'])
                else:
                    row.extend(['', '', '', ''])
            w.writerow(row)
            
            for var in p.get('variations', []):
                var_attrs = var.get('attributes', {})
                var_name = f"{p['title']} - {' / '.join(f'{k}:{v}' for k,v in var_attrs.items())}"
                var_row = [
                    '', 'variation', var.get('sku', ''), var_name, '', '',
                    var.get('sale_price', '') or var.get('price', ''),
                    var.get('regular_price', '') or var.get('price', ''),
                    var.get('sale_price', ''),
                    '', var.get('image', ''), var.get('stock', ''),
                    'instock' if var.get('in_stock', True) else 'outofstock',
                    var.get('weight', ''), var.get('dimensions', '')
                ]
                for i in range(2):
                    if i < len(attrs):
                        an = attrs[i].get('name', '')
                        var_row.extend([an, var_attrs.get(an, ''), '1', '1'])
                    else:
                        var_row.extend(['', '', '', ''])
                w.writerow(var_row)
    
    print(f"WooCommerce CSV saved")

    # Simple CSV
    with open('products.csv', 'w', encoding='utf-8', newline='') as f:
        fields = ['title', 'sku', 'regular_price', 'sale_price', 'url', 'categories']
        if products:
            max_a = max(len(p.get('attributes', [])) for p in products) or 0
            max_v = max(len(p.get('variations', [])) for p in products) or 0
            for i in range(max_a):
                fields.extend([f'attr_{i+1}_name', f'attr_{i+1}_options'])
            for i in range(max_v):
                fields.extend([f'var_{i+1}_sku', f'var_{i+1}_price', f'var_{i+1}_stock'])
        
        w = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        w.writerow(fields)
        
        for p in products:
            row = [
                p.get('title', ''), p.get('sku', ''), p.get('regular_price', ''),
                p.get('sale_price', ''), p.get('url', ''),
                ', '.join(p.get('categories', []))
            ]
            for attr in p.get('attributes', []):
                row.extend([attr.get('name', ''), ', '.join(attr.get('options', []))])
            for var in p.get('variations', []):
                row.extend([var.get('sku', ''), var.get('price', ''), var.get('stock', '')])
            w.writerow(row)
    
    print(f"Products CSV saved")


if __name__ == '__main__':
    from bs4 import BeautifulSoup
    print("="*60 + "\n  HappyHippieYoga Product Scraper\n  Category: Yoga Pilates Sokken\n" + "="*60)
    
    products = scrape()
    
    if products:
        export(products)
        print(f"\nSUCCESS: {len(products)} products scraped")
        for p in products:
            print(f"  - {p['title'][:50]}")
    else:
        print("\nFAILED: No products scraped")