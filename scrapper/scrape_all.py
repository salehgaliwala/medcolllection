#!/usr/bin/env python3
"""
HappyHippieYoga - Scrape 24 Yoga Pilates Sokken products using Playwright
Outputs: products.json, products.csv, woocommerce_products.csv
"""

import sys
import os
import json
import csv
import re
import time

# Make sure we're in the right directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

from playwright.sync_api import sync_playwright

CATEGORY_URL = "https://happyhippieyoga.nl/yoga-pilates-sokken/"
BASE_URL = "https://happyhippieyoga.nl"

def get_page_content(page, url, wait_seconds=15):
    """Navigate to URL and wait for Cloudflare challenge to complete."""
    print(f"  Navigating to: {url}")
    page.goto(url, timeout=90000, wait_until='domcontentloaded')
    page.wait_for_timeout(wait_seconds * 1000)
    
    # Check if we got real content
    title = page.title()
    body_text = page.evaluate('() => document.body.innerText')
    
    print(f"  Title: {title[:80]}")
    print(f"  Body text length: {len(body_text)}")
    
    # Detect if still on Cloudflare challenge
    if 'just a moment' in body_text.lower() or 'checking your browser' in body_text.lower():
        print("  ⚠ Still on Cloudflare challenge, waiting more...")
        page.wait_for_timeout(20000)
        body_text = page.evaluate('() => document.body.innerText')
        print(f"  After extra wait - body text length: {len(body_text)}")
    
    return body_text

def find_product_urls(page):
    """Extract all product URLs from the category page."""
    print(f"\n{'='*60}")
    print(f"STEP 1: Finding product URLs")
    print(f"{'='*60}")
    
    body_text = get_page_content(page, CATEGORY_URL, wait_seconds=20)
    
    # Save page HTML for debugging
    html = page.content()
    with open(os.path.join(SCRIPT_DIR, 'category.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    
    # Take screenshot
    page.screenshot(path=os.path.join(SCRIPT_DIR, 'category.png'), full_page=True)
    print("  Saved category.png and category.html")
    
    # Method 1: Get all links with /product/
    urls = page.evaluate('''() => {
        const anchors = Array.from(document.querySelectorAll('a'));
        return anchors.map(a => a.href).filter(h => h.includes('/product/'));
    }''')
    
    # Method 2: Try WooCommerce products widget
    if not urls:
        urls = page.evaluate('''() => {
            const items = document.querySelectorAll('.elementor-products-grid .product a, ' +
                '.products .product a, li.product a, [class*=\"product\"] a[href*=\"/product/\"]');
            return Array.from(items).map(a => a.href).filter(h => h.includes('/product/'));
        }''')
    
    # Method 3: Look for data attributes
    if not urls:
        urls = page.evaluate('''() => {
            const items = document.querySelectorAll('[data-product-id], [data-product_sku]');
            return Array.from(items).map(el => {
                const link = el.closest('a') || el.querySelector('a');
                return link ? link.href : '';
            }).filter(h => h.includes('/product/'));
        }''')
    
    # Deduplicate
    unique_urls = list(dict.fromkeys([u.strip() for u in urls if u.strip()]))
    
    print(f"  Found {len(unique_urls)} product URLs")
    for u in unique_urls[:5]:
        print(f"    • {u}")
    if len(unique_urls) > 5:
        print(f"    ... and {len(unique_urls)-5} more")
    
    # Check body text for product names
    print(f"\n  Body text preview (first 500 chars):")
    print(f"  {body_text[:500]}")
    
    return unique_urls[:24]

def extract_single_product(page, url):
    """Extract full details from a single product page."""
    print(f"\n  {'─'*50}")
    print(f"  Fetching product: {url}")
    
    try:
        body_text = get_page_content(page, url, wait_seconds=8)
    except Exception as e:
        print(f"  ✗ Error loading page: {e}")
        return None
    
    # Get the full page HTML
    html = page.content()
    
    product = {
        'url': url,
        'title': '',
        'sku': '',
        'regular_price': '',
        'sale_price': '',
        'description': '',
        'short_description': '',
        'categories': [],
        'tags': [],
        'images': [],
        'attributes': [],
        'variations': [],
        'specifications': {},
        'weight': '',
        'dimensions': '',
        'stock_status': '',
        'reviews_count': 0,
        'rating': '',
    }
    
    # Extract using JavaScript evaluation
    data = page.evaluate('''() => {
        const result = {};
        
        // Title
        const titleEl = document.querySelector('.product_title') || document.querySelector('h1');
        result.title = titleEl ? titleEl.innerText.trim() : '';
        
        // Price
        const priceEl = document.querySelector('.price');
        if (priceEl) {
            const amounts = priceEl.querySelectorAll('.amount, .woocommerce-Price-amount');
            if (amounts.length >= 2) {
                result.sale_price = amounts[0].innerText.trim();
                result.regular_price = amounts[1].innerText.trim();
            } else if (amounts.length === 1) {
                result.regular_price = amounts[0].innerText.trim();
            } else {
                result.regular_price = priceEl.innerText.trim();
            }
        }
        
        // SKU
        const skuEl = document.querySelector('.sku');
        result.sku = skuEl ? skuEl.innerText.trim() : '';
        
        // Short description
        const shortDesc = document.querySelector('.woocommerce-product-details__short-description');
        result.short_description = shortDesc ? shortDesc.innerHTML.trim() : '';
        
        // Description
        const desc = document.querySelector('.woocommerce-Tabs-panel--description, #tab-description');
        result.description = desc ? desc.innerHTML.trim() : '';
        
        // Categories
        const catEl = document.querySelector('.posted_in');
        if (catEl) {
            const links = catEl.querySelectorAll('a');
            result.categories = Array.from(links).map(a => a.innerText.trim());
        }
        
        // Tags
        const tagEl = document.querySelector('.tagged_as');
        if (tagEl) {
            const links = tagEl.querySelectorAll('a');
            result.tags = Array.from(links).map(a => a.innerText.trim());
        }
        
        // Images
        const mainImg = document.querySelector('.wp-post-image');
        if (mainImg) {
            result.main_image = mainImg.getAttribute('data-src') || mainImg.src || '';
        } else {
            result.main_image = '';
        }
        
        // Gallery
        const galleryImgs = document.querySelectorAll('.woocommerce-product-gallery__image img, .flex-control-nav img');
        result.gallery = Array.from(galleryImgs).map(img => img.getAttribute('data-src') || img.src || '').filter(s => s);
        
        // Combined images
        result.images = [result.main_image, ...result.gallery].filter(s => s);
        
        // Weight and dimensions
        const weightEl = document.querySelector('.product_weight');
        result.weight = weightEl ? weightEl.innerText.trim() : '';
        const dimEl = document.querySelector('.product_dimensions');
        result.dimensions = dimEl ? dimEl.innerText.trim() : '';
        
        // Stock
        const stockEl = document.querySelector('.stock');
        result.stock_status = stockEl ? stockEl.innerText.trim() : '';
        
        // Rating / reviews
        const ratingEl = document.querySelector('.woocommerce-product-rating .average, .star-rating');
        result.rating = ratingEl ? (ratingEl.innerText || ratingEl.getAttribute('aria-label') || '').trim() : '';
        const reviewsCountEl = document.querySelector('.woocommerce-review-link');
        result.reviews_count = reviewsCountEl ? parseInt(reviewsCountEl.innerText.match(/\\d+/)?.[0] || '0') : 0;
        
        // Additional information table (specifications)
        const specTable = document.querySelector('.woocommerce-product-attributes.shop_attributes, ' +
            '.woocommerce-Tabs-panel--additional_information table.shop_attributes');
        result.specifications = {};
        if (specTable) {
            specTable.querySelectorAll('tr').forEach(row => {
                const th = row.querySelector('th');
                const td = row.querySelector('td');
                if (th && td) {
                    result.specifications[th.innerText.trim()] = td.innerText.trim();
                }
            });
        }
        
        // Variation attributes (select dropdowns)
        result.attributes = [];
        const attrSelects = document.querySelectorAll('.variations select, select[data-attribute_name]');
        attrSelects.forEach(select => {
            const name = select.getAttribute('data-attribute_name') || select.name || select.id || '';
            const cleanName = name.replace(/^attribute_/, '').replace(/^pa_/, '').replace(/-/g, ' ').replace(/\\b\\w/g, c => c.toUpperCase()).trim();
            const options = Array.from(select.options).map(o => o.value).filter(v => v);
            if (cleanName && options.length) {
                result.attributes.push({ name: cleanName, options: options });
            }
        });
        
        // If no selects, check for swatches/buttons
        if (!result.attributes.length) {
            const swatchLabels = document.querySelectorAll('.variations .label, .attribute-options, [class*=\"swatch\"]');
            // Try WooCommerce attribute labels
            const attrLabels = document.querySelectorAll('.attribute-pa_\\w+');
            attrLabels.forEach(el => {
                const text = el.innerText.trim();
                // Try to identify attribute name
            });
        }
        
        return result;
    }''')
    
    # Merge extracted data
    for key, val in data.items():
        if val is not None:
            product[key] = val
    
    # --- Extract variations from data-product_variations attribute ---
    variations = page.evaluate('''() => {
        const form = document.querySelector('.variations_form');
        if (!form) return [];
        
        const data = form.getAttribute('data-product_variations');
        if (!data) return [];
        
        try {
            const vars = JSON.parse(data.replace(/"/g, '"').replace(/&#034;/g, '"'));
            return vars.map(v => ({
                sku: v.sku || '',
                price: v.display_price !== undefined ? String(v.display_price) : (v.price || ''),
                regular_price: v.display_regular_price !== undefined ? String(v.display_regular_price) : (v.regular_price || ''),
                sale_price: v.display_sale_price !== undefined ? String(v.display_sale_price) : (v.sale_price || ''),
                stock: v.max_qty !== undefined ? String(v.max_qty) : (v.stock_quantity !== undefined ? String(v.stock_quantity) : ''),
                in_stock: v.is_in_stock !== undefined ? v.is_in_stock : true,
                image: (v.image && v.image.url) ? v.image.url : '',
                weight: v.weight || '',
                dimensions: v.dimensions ? [v.dimensions.length, v.dimensions.width, v.dimensions.height].filter(d => d).join(' x ') : '',
                attributes: Object.fromEntries(
                    Object.entries(v).filter(([k]) => k.startsWith('attribute_')).map(([k, val]) => [
                        k.replace(/^attribute_pa_/, '').replace(/^attribute_/, '').replace(/-/g, ' ').replace(/\\b\\w/g, c => c.toUpperCase()),
                        val
                    ])
                )
            }));
        } catch(e) {
            return [];
        }
    }''')
    
    if variations:
        product['variations'] = variations
        print(f"  → Found {len(variations)} variations")
    
    # Clean prices (remove € and normalize)
    for price_key in ['regular_price', 'sale_price']:
        val = product.get(price_key, '')
        if val:
            val = val.replace('€', '').replace(',', '.').replace(' ', '').strip()
            # Extract first price number
            match = re.search(r'(\d+\.?\d*)', val)
            if match:
                product[price_key] = match.group(1)
    
    # --- Extract attributes from additional information table ---
    if not product['attributes'] and product['specifications']:
        for spec_name, spec_val in product['specifications'].items():
            # Check if this looks like a product attribute
            if any(kw in spec_name.lower() for kw in ['maat', 'size', 'kleur', 'color', 'materiaal', 'material']):
                vals = [v.strip() for v in spec_val.split(',') if v.strip()]
                if vals:
                    product['attributes'].append({
                        'name': spec_name,
                        'options': vals
                    })
    
    # Clean description HTML
    desc = product.get('description', '')
    if desc:
        # Clean excessive whitespace
        product['description'] = re.sub(r'>\s+<', '><', desc)
    
    short_desc = product.get('short_description', '')
    if short_desc:
        product['short_description'] = re.sub(r'>\s+<', '><', short_desc)
    
    # Print summary
    print(f"  ✓ {product['title'][:60]}")
    print(f"    Price: €{product['regular_price']} | SKU: {product['sku'] or 'N/A'} | "
          f"Variations: {len(product['variations'])} | Attrs: {len(product['attributes'])}")
    
    return product


def export_to_json(products, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    print(f"\n  ✓ Exported JSON: {filepath}")

def export_to_csv(products, filepath):
    if not products:
        return
    
    fields = ['title', 'sku', 'regular_price', 'sale_price', 'url', 'categories', 'stock_status',
              'weight', 'dimensions', 'short_description', 'description', 'main_image']
    
    # Dynamic attribute fields
    max_attrs = max((len(p.get('attributes', [])) for p in products), default=0)
    for i in range(max_attrs):
        fields.append(f'attr_{i+1}_name')
        fields.append(f'attr_{i+1}_options')
    
    # Specification fields
    all_specs = set()
    for p in products:
        all_specs.update(p.get('specifications', {}).keys())
    for spec in sorted(all_specs):
        fields.append(f'spec_{spec}')
    
    # Variation fields
    max_vars = max((len(p.get('variations', [])) for p in products), default=0)
    for i in range(max_vars):
        fields.append(f'var_{i+1}_sku')
        fields.append(f'var_{i+1}_price')
        fields.append(f'var_{i+1}_stock')
    
    # Gallery images
    max_imgs = max((len(p.get('images', [])) for p in products), default=0)
    for i in range(2, max_imgs + 1):
        fields.append(f'image_{i}')
    
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore', delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        
        for product in products:
            row = {}
            for field in fields:
                if field.startswith('attr_'):
                    parts = field.split('_')
                    idx = int(parts[1]) - 1
                    sub = parts[2]
                    attrs = product.get('attributes', [])
                    if idx < len(attrs):
                        row[field] = ', '.join(attrs[idx].get(sub, '')) if sub == 'options' else attrs[idx].get(sub, '')
                elif field.startswith('spec_'):
                    row[field] = product.get('specifications', {}).get(field[5:], '')
                elif field.startswith('var_'):
                    parts = field.split('_')
                    idx = int(parts[1]) - 1
                    sub = '_'.join(parts[2:])
                    vars_list = product.get('variations', [])
                    if idx < len(vars_list):
                        row[field] = str(vars_list[idx].get(sub, ''))
                elif field.startswith('image_'):
                    idx = int(field.split('_')[1]) - 1
                    imgs = product.get('images', [])
                    row[field] = imgs[idx] if idx < len(imgs) else ''
                elif field == 'categories':
                    row[field] = ', '.join(product.get('categories', []))
                elif field == 'main_image':
                    imgs = product.get('images', [])
                    row[field] = imgs[0] if imgs else ''
                elif field in ('short_description', 'description'):
                    txt = BeautifulSoup(product.get(field, ''), 'html.parser').get_text(strip=True) if product.get(field) else ''
                    row[field] = txt
                else:
                    row[field] = str(product.get(field, ''))
            writer.writerow(row)
    
    print(f"  ✓ Exported CSV: {filepath}")

def export_woocommerce_csv(products, filepath):
    if not products:
        return
    
    # Build WooCommerce import format
    fields = [
        'ID', 'Type', 'SKU', 'Name', 'Description', 'Short description', 'Price',
        'Regular price', 'Sale price', 'Categories', 'Images', 'Stock', 'Stock status',
        'Weight', 'Dimensions',
        'Attribute 1 name', 'Attribute 1 value(s)', 'Attribute 1 visible', 'Attribute 1 global',
        'Attribute 2 name', 'Attribute 2 value(s)', 'Attribute 2 visible', 'Attribute 2 global'
    ]
    
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writerow(fields)
        
        for product in products:
            attrs = product.get('attributes', [])
            is_variable = len(product.get('variations', [])) > 0
            
            # Clean description
            desc = BeautifulSoup(product.get('description', ''), 'html.parser').get_text(strip=True) if product.get('description') else ''
            short_desc = BeautifulSoup(product.get('short_description', ''), 'html.parser').get_text(strip=True) if product.get('short_description') else ''
            
            main_row = [
                '',  # ID
                'variable' if is_variable else 'simple',  # Type
                product.get('sku', ''),
                product.get('title', ''),
                desc,
                short_desc,
                product.get('sale_price', '') or product.get('regular_price', ''),  # Price
                product.get('regular_price', ''),
                product.get('sale_price', ''),
                ', '.join(product.get('categories', [])),
                product.get('images', [''])[0] if product.get('images') else '',
                '',  # Stock
                'instock',
                product.get('weight', ''),
                product.get('dimensions', ''),
            ]
            
            # Attributes
            for i in range(2):
                if i < len(attrs):
                    main_row.append(attrs[i].get('name', ''))
                    main_row.append(', '.join(attrs[i].get('options', [])))
                    main_row.append('1')
                    main_row.append('1')
                else:
                    main_row.extend(['', '', '', ''])
            
            writer.writerow(main_row)
            
            # Write variation rows
            for var in product.get('variations', []):
                var_attrs = var.get('attributes', {})
                var_name_parts = [f"{k}: {v}" for k, v in var_attrs.items()]
                var_name = f"{product['title']} - {' / '.join(var_name_parts)}"
                
                var_row = [
                    '',
                    'variation',
                    var.get('sku', ''),
                    var_name,
                    '',  # description
                    '',
                    var.get('sale_price', '') or var.get('price', ''),
                    var.get('regular_price', '') or var.get('price', ''),
                    var.get('sale_price', ''),
                    '',  # categories
                    var.get('image', ''),
                    var.get('stock', ''),
                    'instock' if var.get('in_stock', True) else 'outofstock',
                    var.get('weight', ''),
                    var.get('dimensions', ''),
                ]
                
                # Variation attributes
                for i in range(2):
                    if i < len(attrs):
                        attr_name = attrs[i].get('name', '')
                        var_row.append(attr_name)
                        var_row.append(var_attrs.get(attr_name, ''))
                        var_row.append('1')
                        var_row.append('1')
                    else:
                        var_row.extend(['', '', '', ''])
                
                writer.writerow(var_row)
    
    print(f"  ✓ Exported WooCommerce CSV: {filepath}")


def main():
    print("=" * 60)
    print("  HappyHippieYoga - Product Scraper")
    print("  Scraping: Yoga Pilates Sokken")
    print("=" * 60)
    
    from bs4 import BeautifulSoup
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            locale='nl-NL',
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=1,
        )
        page = context.new_page()
        page.set_default_timeout(60000)
        
        # STEP 1: Get product URLs
        product_urls = find_product_urls(page)
        
        if not product_urls:
            print("\n✗ No products found! The site may be blocking the scraper or the page structure differs.")
            print("  Check category.png and category.html for analysis.")
            browser.close()
            return
        
        print(f"\n{'='*60}")
        print(f"STEP 2: Scraping {len(product_urls)} products")
        print(f"{'='*60}")
        
        # STEP 2: Scrape each product
        products = []
        for i, url in enumerate(product_urls):
            print(f"\n  [{i+1}/{len(product_urls)}]")
            product = extract_single_product(page, url)
            if product:
                products.append(product)
            time.sleep(2)  # Rate limiting
        
        browser.close()
    
    print(f"\n{'='*60}")
    print(f"RESULTS: {len(products)} products scraped")
    print(f"{'='*60}\n")
    
    if not products:
        print("No products were scraped successfully.")
        return
    
    # Export
    json_path = os.path.join(SCRIPT_DIR, 'products.json')
    csv_path = os.path.join(SCRIPT_DIR, 'products.csv')
    wc_csv_path = os.path.join(SCRIPT_DIR, 'woocommerce_products.csv')
    
    export_to_json(products, json_path)
    export_to_csv(products, csv_path)
    export_woocommerce_csv(products, wc_csv_path)
    
    # Summary
    print(f"\n{'='*60}")
    print("PRODUCT SUMMARY")
    print(f"{'='*60}")
    for p in products:
        cats = ', '.join(p.get('categories', []))
        attrs = ', '.join([a['name'] for a in p.get('attributes', [])])
        vars_n = len(p.get('variations', []))
        specs_n = len(p.get('specifications', {}))
        print(f"  {p['title'][:55]}")
        print(f"    Price: €{p['regular_price']} | SKU: {p.get('sku','N/A')} | "
              f"Vars: {vars_n} | Attrs: {attrs or 'N/A'} | Specs: {specs_n}")
        print(f"    Cats: {cats}")
    
    print(f"\n{'='*60}")
    print("OUTPUT FILES")
    print(f"{'='*60}")
    print(f"  • {json_path}")
    print(f"  • {csv_path}")
    print(f"  • {wc_csv_path}")
    print(f"  • category.png (screenshot)")
    print(f"  • category.html (page source)")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()