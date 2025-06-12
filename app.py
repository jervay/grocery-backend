import os
from flask import Flask, jsonify
from flask_caching import Cache

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Add this health check endpoint
@app.route('/')
def health_check():
    return "App is running!", 200

@app.route('/search')
def search():
    # Your existing search logic here
    return jsonify({"status": "working"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

# Store URLs and selectors for each supermarket
STORES = {
    "paknsave": {
        "url": "https://www.paknsave.co.nz/shop/search?q={query}",
        "item_selector": "div.fs-product-card",
        "name_selector": "div.fs-product-card__title",
        "price_selector": "span.fs-product-card__price",
        "stock_selector": "div.fs-product-card__stock-flag"
    },
    "newworld": {
        "url": "https://www.newworld.co.nz/shop/search?q={query}",
        "item_selector": "div.product-tile",
        "name_selector": "div.product-tile__details__name",
        "price_selector": "span.product-price__dollars",
        "stock_selector": "div.product-tile__details__availability"
    },
    "countdown": {
        "url": "https://www.countdown.co.nz/shop/searchproducts?search={query}",
        "item_selector": "div.product",
        "name_selector": "div.product-title",
        "price_selector": "span.product-price",
        "stock_selector": "div.product-in-stock"
    }
}

def scrape_store(store, query):
    try:
        config = STORES[store]
        url = config["url"].format(query=query)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        products = []
        
        for item in soup.select(config["item_selector"]):
            name_elem = item.select_one(config["name_selector"])
            price_elem = item.select_one(config["price_selector"])
            stock_elem = item.select_one(config["stock_selector"])
            
            if not name_elem or not price_elem:
                continue
                
            name = name_elem.text.strip()
            price_text = price_elem.text.strip()
            
            # Clean price text (remove $ and other non-numeric characters)
            price = float(re.sub(r'[^\d.]', '', price_text))
            
            # Check stock status
            in_stock = True
            if stock_elem:
                stock_text = stock_elem.text.strip().lower()
                if "out of stock" in stock_text or "unavailable" in stock_text:
                    in_stock = False
            
            products.append({
                "name": name,
                "price": price,
                "store": store,
                "in_stock": in_stock
            })
        
        return products
    
    except Exception as e:
        print(f"Error scraping {store}: {str(e)}")
        return []

@app.route('/search', methods=['GET'])
def search():
    item = request.args.get('item', '')
    suburb = request.args.get('suburb', '')
    
    if not item or not suburb:
        return jsonify({"error": "Both item and suburb are required"}), 400
    
    try:
        all_products = []
        
        # Scrape each store in parallel (but we'll do it simple for now)
        for store in STORES:
            products = scrape_store(store, item)
            for product in products:
                if product["in_stock"]:
                    all_products.append({
                        "name": product["name"],
                        "price": product["price"],
                        "store": store.capitalize(),
                        "location": suburb
                    })
        
        # Sort by price and get top 5 cheapest
        all_products.sort(key=lambda x: x["price"])
        results = all_products[:5]
        
        return jsonify({"results": results})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()
