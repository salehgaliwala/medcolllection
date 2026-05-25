#!/usr/bin/env python3
"""
HappyHippieYoga Products Scraper
Scrapes https://happyhippieyoga.nl/yoga-pilates-sokken/ for all product details.
Outputs: JSON, CSV, and WooCommerce-ready CSV formats.
"""

import cloudscraper
from bs4 import BeautifulSoup
import json
import csv
import re
import time
import os
from urllib.parse import urljoin

CATEGORY_URL = "https://happyhippieyoga.nl/yoga-pilates-sokken/"
BASE_URL = "https://happyhippieyoga.nl"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Create cloudscraper instance with retries
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True,
    }
)

def safe_request(url, max_retries=3):
    """Make a request with retries and rate limiting."""
    for attempt in range(max_retries):
        try:
            resp = scraper.get(url, timeout=30)
            if resp.status_code == 200:
                return resp
            print(f"  Attempt {attempt + 1}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"  Attempt {attempt + 1} failed: {e}")
        time.sleep(2)
    return None

def extract_product_urls():
    """Extract all product URLs from the category page."""
    print(f"Fetching category page: {CATEGORY_URL}")
    resp = safe_request(CATEGORY_URL)
    if not resp:
        print("ERROR: Could not fetch category page!")
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Also save the HTML for debugging
    with open(os.path.join(OUTPUT_DIR, 'category_page.html'), 'w', encoding='utf-8') as f:
        f.write(resp.text)

    product_urls = []
    
    # Method 1: Look for WooCommerce product links via href
    for a_tag in soup.find_all('a', href=re.compile(r'/product/')):
        href = a_tag.get('href', '')
        if href and href not in product_urls:
            product_urls.append(href)
    
    # Method 2: Look for li.product elements
    if not product_urls:
        for li in soup.find_all('li', class_=lambda c: c and 'product' in c.split()):
            a = li.find('a', href=re.compile(r'/product/'))
            if a:
                href = a.get('href')
                if href and href not in product_urls:
                    product_urls.append(href)
    
    # Method 3: Look in Elementor products widget
    if not product_urls:
        for a_tag in soup.find_all('a', href=re.compile(r'product', re.I)):
            href = a_tag.get('href', '')
            if href and '/product/' in href and href not in product_urls:
                product_urls.append(href)
    
    # Deduplicate and clean
    product_urls = list(dict.fromkeys([url.strip() for url in product_urls]))
    
    print(f"Found {len(product_urls)} unique product URLs")
    for url in product_urls[:5]:
        print(f"  {url}")
    if len(product_urls) > 5:
        print(f"  ... and {len(product_urls) - 5} more")
    
    return product_urls[:24]  # Limit to 24 products

def extract_product_details(url):
    """Extract full details from a single product page."""
    print(f"  Fetching: {url}")
    resp = safe_request(url)
    if not resp:
        print(f"  ERROR: Could not fetch {url}")
        return None
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    product = {
        'url': url,
        'title': '',
        'sku': '',
        'regular_price': '',
        'sale_price': '',
        'description': '',
        'short_description': '',
        'categories': [],
        'images': [],
        'attributes': [],
        'variations': [],
        'specifications': {},
        'weight': '',
        'dimensions': '',
        'stock_status': '',
        'additional_info': {}
    }
    
    # --- Title ---
    title_el = soup.find('h1', class_='product_title') or soup.find('h1')
    if title_el:
        product['title'] = title_el.get_text(strip=True)
    
    # --- Price ---
    price_el = soup.find('p', class_='price') or soup.find('span', class_='price')
    if price_el:
        price_text = price_el.get_text(strip=True)
        # Extract regular and sale prices
        price_spans = price_el.find_all('span', class_='amount')
        if len(price_spans) >= 2:
            product['regular_price'] = price_spans[1].get_text(strip=True).replace('€', '').replace(',', '.').strip()
            product['sale_price'] = price_spans[0].get_text(strip=True).replace('€', '').replace(',', '.').strip()
        elif len(price_spans) == 1:
            product['regular_price'] = price_spans[0].get_text(strip=True).replace('€', '').replace(',', '.').strip()
        else:
            # Try extracting from text directly
            prices = re.findall(r'€?\s*(\d+[,\.]\d{2})', price_text)
            if prices:
                product['regular_price'] = prices[0].replace(',', '.')
                if len(prices) > 1:
                    product['sale_price'] = prices[1].replace(',', '.')
    
    # --- SKU ---
    sku_el = soup.find('span', class_='sku')
    if sku_el:
        product['sku'] = sku_el.get_text(strip=True)
    
    # --- Short Description (Excerpt) ---
    excerpt_div = soup.find('div', class_='woocommerce-product-details__short-description')
    if excerpt_div:
        product['short_description'] = excerpt_div.decode_contents().strip()
    
    # --- Description ---
    desc_div = soup.find('div', class_='woocommerce-Tabs-panel--description')
    if desc_div:
        product['description'] = desc_div.decode_contents().strip()
    else:
        # Try to find description tab content
        desc_tab = soup.find('div', id='tab-description')
        if desc_tab:
            product['description'] = desc_tab.decode_contents().strip()
    
    # --- Categories ---
    cat_meta = soup.find('span', class_='posted_in')
    if cat_meta:
        cat_links = cat_meta.find_all('a')
        product['categories'] = [a.get_text(strip=True) for a in cat_links]
    
    # --- Images ---
    main_img = soup.find('img', class_='wp-post-image') or soup.find('div', class_='woocommerce-product-gallery__image')
    if main_img:
        img_tag = main_img.find('img') if main_img.name != 'img' else main_img
        if img_tag:
            for attr in ['data-src', 'src', 'data-large_image', 'data-lazy-src']:
                src = img_tag.get(attr, '')
                if src and src not in product['images']:
                    product['images'].append(src)
    
    # Gallery images
    gallery = soup.find('div', class_='woocommerce-product-gallery')
    if gallery:
        for img in gallery.find_all('img'):
            for attr in ['data-src', 'src', 'data-large_image']:
                src = img.get(attr, '')
                if src and src not in product['images']:
                    product['images'].append(src)
    
    # --- Attributes (Specifications Table) ---
    additional_info = soup.find('div', class_='woocommerce-Tabs-panel--additional_information') or \
                     soup.find('h2', string='Additional information')
    if additional_info:
        info_div = additional_info.find_parent('div', class_='woocommerce-Tabs-panel--additional_information') or \
                   additional_info.find_next('div', class_='woocommerce-Tabs-panel--additional_information')
        if not info_div:
            info_div = additional_info.find_next('table', class_='woocommerce-product-attributes')
        if not info_div:
            info_div = additional_info.parent
        
        attr_table = info_div.find('table', class_='woocommerce-product-attributes') or \
                     info_div.find('table', class_='shop_attributes')
        if attr_table:
            for row in attr_table.find_all('tr'):
                th = row.find('th')
                td = row.find('td')
                if th and td:
                    key = th.get_text(strip=True)
                    value = td.get_text(strip=True)
                    product['specifications'][key] = value
                    product['additional_info'][key] = value
    
    # --- Attributes from product meta (taxonomies) ---
    for attr_term in soup.find_all('span', class_=lambda c: c and 'attribute_' in c):
        # These are selected attribute values in variations
        pass
    
    # Parse attributes from the variation form
    attr_selects = soup.find_all('select', id=re.compile(r'^pa_'))
    if not attr_selects:
        attr_selects = soup.find_all('select', class_=lambda c: c and 'attribute' in c if c else False)
    
    for select in attr_selects:
        attr_name = select.get('name', '')
        attr_id = select.get('id', '')
        clean_name = attr_id.replace('pa_', '').replace('attribute_', '').replace('-', ' ').title().strip()
        options = []
        for option in select.find_all('option'):
            val = option.get('value', '').strip()
            if val:
                options.append(val)
        if options:
            product['attributes'].append({
                'name': clean_name,
                'options': options
            })
    
    # Also parse attributes from the product meta
    meta_attrs = soup.find_all('div', class_=lambda c: c and 'woocommerce-attribute' in c if c else False)
    for meta in meta_attrs:
        label = meta.find('label')
        if label:
            attr_name = label.get_text(strip=True).replace(':', '')
            values = meta.get_text(strip=True).replace(label.get_text(strip=True), '').strip().split(',')
            values = [v.strip() for v in values if v.strip()]
            if values:
                product['attributes'].append({
                    'name': attr_name,
                    'options': values
                })
    
    # --- Weight and Dimensions ---
    weight_el = soup.find('span', class_='product_weight')
    if weight_el:
        product['weight'] = weight_el.get_text(strip=True)
    
    dim_el = soup.find('span', class_='product_dimensions')
    if dim_el:
        product['dimensions'] = dim_el.get_text(strip=True)
    
    # --- Stock Status ---
    stock_el = soup.find('p', class_='stock')
    if stock_el:
        product['stock_status'] = stock_el.get_text(strip=True)
    
    # --- Variations Data (extracted from JS variable if available) ---
    # Look for variations data in embedded JSON/JS
    variation_scripts = soup.find_all('script', type='text/template')
    for script in variation_scripts:
        if 'variation' in script.get('id', '').lower():
            product['variation_template'] = script.string[:200] if script.string else ''
    
    # Look for wc_variation_form data
    var_data_patterns = [
        r'var wc_add_to_cart_variation_params\s*=\s*({.*?});',
        r'var wc_product_block_data\s*=\s*({.*?});',
        r'\"variations\":\s*(\[[^\]]+\])',
        r'variations\s*:\s*(\[[^\]]+\])'
    ]
    for pattern in var_data_patterns:
        match = re.search(pattern, resp.text, re.DOTALL)
        if match:
            try:
                data_str = match.group(1)
                # Try to parse as JSON
                parsed = json.loads(data_str)
                product['raw_variations_data'] = parsed
                break
            except:
                pass
    
    return product

def extract_variations_manually(soup, product_url):
    """Try to extract variations by looking at data attributes or embedded data."""
    variations = []
    
    # Look for variation data in the HTML
    var_forms = soup.find_all('form', class_='variations_form')
    for form in var_forms:
        var_data = form.get('data-product_variations', '')
        if var_data:
            try:
                var_data = var_data.replace('"', '"').replace('&#034;', '"')
                var_list = json.loads(var_data)
                for v in var_list:
                    variation = {
                        'sku': v.get('sku', ''),
                        'price': str(v.get('display_price', v.get('price', ''))),
                        'regular_price': str(v.get('display_regular_price', v.get('regular_price', ''))),
                        'sale_price': str(v.get('display_sale_price', v.get('sale_price', ''))),
                        'stock': v.get('max_qty', v.get('stock_quantity', '')),
                        'in_stock': v.get('is_in_stock', True),
                        'image': v.get('image', {}).get('url', '') if isinstance(v.get('image'), dict) else '',
                        'attributes': {}
                    }
                    for key, val in v.items():
                        if key.startswith('attribute_'):
                            clean_key = key.replace('attribute_pa_', '').replace('attribute_', '').replace('-', ' ').title()
                            variation['attributes'][clean_key] = val
                    
                    # Add dimension values if available
                    if v.get('dimensions'):
                        dims = v['dimensions']
                        if dims.get('width') or dims.get('height') or dims.get('length'):
                            variation['dimensions'] = f"{dims.get('length', '')} x {dims.get('width', '')} x {dims.get('height', '')}".strip(' x ')
                    if v.get('weight'):
                        variation['weight'] = v['weight']
                    
                    variations.append(variation)
            except json.JSONDecodeError as e:
                print(f"    Could not parse variations JSON: {e}")
    
    return variations

def clean_html(html_content):
    """Clean HTML content: remove extra whitespace, normalize tags."""
    if not html_content:
        return ''
    soup = BeautifulSoup(html_content, 'html.parser')
    return str(soup)

def export_to_json(products, filepath):
    """Export products to JSON file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    print(f"  Exported JSON to: {filepath}")

def export_to_csv(products, filepath):
    """Export products to CSV file with all fields."""
    if not products:
        print("  No products to export to CSV")
        return
    
    # Determine all possible fields
    fields = ['title', 'sku', 'regular_price', 'sale_price', 'url', 'categories', 
              'stock_status', 'weight', 'dimensions', 'short_description', 'description']
    
    # Add attribute fields
    max_attrs = 0
    for p in products:
        if len(p.get('attributes', [])) > max_attrs:
            max_attrs = len(p['attributes'])
    
    for i in range(max_attrs):
        fields.append(f'attribute_{i+1}_name')
        fields.append(f'attribute_{i+1}_options')
    
    # Add specification fields
    all_specs = set()
    for p in products:
        all_specs.update(p.get('specifications', {}).keys())
    for spec in sorted(all_specs):
        fields.append(f'spec_{spec}')
    
    # Add variation fields
    max_vars = 0
    for p in products:
        if len(p.get('variations', [])) > max_vars:
            max_vars = len(p['variations'])
    
    for i in range(max_vars):
        fields.append(f'variation_{i+1}_sku')
        fields.append(f'variation_{i+1}_price')
        fields.append(f'variation_{i+1}_stock')
    
    fields.extend(['image_1', 'image_2', 'image_3'])
    
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        
        for product in products:
            row = {}
            for field in fields:
                if field.startswith('attribute_'):
                    idx = int(field.split('_')[1]) - 1
                    subfield = field.split('_', 2)[2]
                    attrs = product.get('attributes', [])
                    if idx < len(attrs):
                        if subfield == 'name':
                            row[field] = attrs[idx].get('name', '')
                        elif subfield == 'options':
                            row[field] = ', '.join(attrs[idx].get('options', []))
                elif field.startswith('spec_'):
                    spec_name = field[5:]
                    row[field] = product.get('specifications', {}).get(spec_name, '')
                elif field.startswith('variation_'):
                    parts = field.split('_')
                    idx = int(parts[1]) - 1
                    subfield = '_'.join(parts[2:])
                    vars_list = product.get('variations', [])
                    if idx < len(vars_list):
                        row[field] = vars_list[idx].get(subfield, '')
                elif field == 'categories':
                    row[field] = ', '.join(product.get('categories', []))
                elif field == 'short_description':
                    text = BeautifulSoup(product.get('short_description', ''), 'html.parser').get_text(strip=True)
                    row[field] = text
                elif field == 'description':
                    text = BeautifulSoup(product.get('description', ''), 'html.parser').get_text(strip=True)
                    row[field] = text
                elif field.startswith('image_'):
                    idx = int(field.split('_')[1]) - 1
                    images = product.get('images', [])
                    if idx < len(images):
                        row[field] = images[idx]
                else:
                    row[field] = product.get(field, '')
            
            writer.writerow(row)
    
    print(f"  Exported CSV to: {filepath}")

def export_woocommerce_csv(products, filepath):
    """Export products in WooCommerce CSV import format."""
    if not products:
        return
    
    fields = [
        'ID', 'Type', 'SKU', 'Name', 'Description', 'Short description',
        'Price', 'Regular price', 'Sale price', 'Categories', 'Images',
        'Stock', 'Stock status', 'Weight', 'Dimensions',
        'Attribute 1 name', 'Attribute 1 value(s)', 'Attribute 1 visible',
        'Attribute 1 global', 'Attribute 2 name', 'Attribute 2 value(s)',
        'Attribute 2 visible', 'Attribute 2 global'
    ]
    
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        
        for product in products:
            attrs = product.get('attributes', [])
            
            row = [
                '',  # ID
                'variable' if len(product.get('variations', [])) > 0 else 'simple',  # Type
                product.get('sku', ''),
                product.get('title', ''),
                BeautifulSoup(product.get('description', ''), 'html.parser').get_text(strip=True),
                BeautifulSoup(product.get('short_description', ''), 'html.parser').get_text(strip=True),
                product.get('sale_price', '') or product.get('regular_price', ''),
                product.get('regular_price', ''),
                product.get('sale_price', ''),
                ', '.join(product.get('categories', [])),
                ', '.join(product.get('images', [])),
                '',  # Stock
                product.get('stock_status', ''),
                product.get('weight', ''),
                product.get('dimensions', ''),
            ]
            
            # Add up to 2 attributes
            for i in range(2):
                if i < len(attrs):
                    row.append(attrs[i].get('name', ''))
                    row.append(', '.join(attrs[i].get('options', [])))
                    row.append('1')  # visible
                    row.append('1')  # global
                else:
                    row.extend(['', '', '', ''])
            
            writer.writerow(row)
            
            # Write variation rows
            for var in product.get('variations', []):
                var_attrs = var.get('attributes', {})
                var_row = [
                    '',  # ID
                    'variation',
                    var.get('sku', ''),
                    f"{product.get('title', '')} - {' / '.join(f'{k}: {v}' for k, v in var_attrs.items())}",
                    '', '',  # description
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
                
                # Add variation attributes
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
    
    print(f"  Exported WooCommerce CSV to: {filepath}")

def main():
    print("=" * 60)
    print("HappyHippieYoga Products Scraper")
    print("=" * 60)
    
    # Step 1: Get all product URLs
    product_urls = extract_product_urls()
    if not product_urls:
        print("ERROR: No products found. The site may be blocking the scraper.")
        return
    
    print(f"\nScraping up to {len(product_urls)} products...")
    
    # Step 2: Scrape each product
    products = []
    for i, url in enumerate(product_urls):
        print(f"\n[{i+1}/{len(product_urls)}] Scraping product...")
        product = extract_product_details(url)
        if product:
            # Try to extract variations
            resp = safe_request(url)
            if resp:
                soup = BeautifulSoup(resp.text, 'html.parser')
                variations = extract_variations_manually(soup, url)
                if variations:
                    product['variations'] = variations
                    print(f"    Found {len(variations)} variations")
            
            # Clean HTML fields
            product['description'] = clean_html(product.get('description', ''))
            product['short_description'] = clean_html(product.get('short_description', ''))
            
            products.append(product)
            print(f"    ✓ {product['title'][:60]}")
        
        # Rate limiting
        time.sleep(1.5)
    
    print(f"\n{'=' * 60}")
    print(f"Scraped {len(products)} products successfully!")
    print(f"{'=' * 60}")
    
    if not products:
        print("No products were scraped. Check the category page HTML for selectors.")
        return
    
    # Step 3: Export data
    json_path = os.path.join(OUTPUT_DIR, 'products.json')
    csv_path = os.path.join(OUTPUT_DIR, 'products.csv')
    wc_csv_path = os.path.join(OUTPUT_DIR, 'woocommerce_products.csv')
    
    export_to_json(products, json_path)
    export_to_csv(products, csv_path)
    export_woocommerce_csv(products, wc_csv_path)
    
    # Print summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    for p in products:
        attrs = ', '.join([a['name'] for a in p.get('attributes', [])])
        vars_count = len(p.get('variations', []))
        specs_count = len(p.get('specifications', {}))
        print(f"  • {p['title'][:50]}")
        print(f"    Price: €{p['regular_price']} | SKU: {p.get('sku', 'N/A')} | "
              f"Variations: {vars_count} | Specs: {specs_count} | Attrs: {attrs}")
    
    print(f"\n{'=' * 60}")
    print("Output Files:")
    print(f"  • {json_path}")
    print(f"  • {csv_path}")
    print(f"  • {wc_csv_path}")
    print(f"{'=' * 60}")

if __name__ == '__main__':
    main()