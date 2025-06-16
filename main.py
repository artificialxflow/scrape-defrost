import requests
from bs4 import BeautifulSoup
import json
import streamlit as st
import time
import os
import re

BASE_URL = "https://defrost.ir"
CATEGORY_URL = f"{BASE_URL}/shop/product-category/spare-parts-for-refrigerators/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def slugify(text):
    # تبدیل نام دسته به اسلاگ برای نام فایل
    text = re.sub(r'[\s\u200c]+', '_', text.strip())
    text = re.sub(r'[^\w\-_]', '', text)
    return text

def get_soup(url):
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")

def get_subcategories(soup):
    cats = []
    sidebar = soup.find("aside", class_="widget_product_categories")
    if sidebar:
        for li in sidebar.find_all("li", class_="cat-item"):
            a = li.find("a", href=True)
            if a:
                cats.append({
                    "name": a.get_text(strip=True),
                    "url": a["href"]
                })
    return cats

def get_main_image_from_product(product_url):
    try:
        prod_soup = get_soup(product_url)
        # تصویر اصلی گالری یا شاخص
        img = prod_soup.find("figure", class_="woocommerce-product-gallery__wrapper")
        if img:
            main_img = img.find("img")
            if main_img and main_img.has_attr("src"):
                return main_img["src"]
        # حالت fallback: اولین img بزرگ در صفحه
        main_img = prod_soup.find("img", src=True)
        if main_img:
            return main_img["src"]
    except Exception as e:
        return None
    return None

def get_products_from_category(category_url):
    products = []
    page_url = category_url
    while page_url:
        soup = get_soup(page_url)
        product_blocks = soup.select('div.product-block, div.product')
        for block in product_blocks:
            a = block.find("a", class_="product-image", href=True)
            if not a:
                continue
            name = a.get("title") or a.get_text(strip=True)
            url = a["href"]
            # لینک عکس اصلی از صفحه تکی محصول
            image = get_main_image_from_product(url)
            # توضیحات از صفحه تکی محصول
            desc = ""
            try:
                prod_soup = get_soup(url)
                desc_div = prod_soup.find("div", class_="woocommerce-product-details__short-description")
                if desc_div:
                    desc = desc_div.get_text(strip=True)
            except Exception as e:
                desc = ""
            products.append({
                "name": name,
                "url": url,
                "image": image,
                "description": desc
            })
        # صفحه بعد
        next_page = soup.find("a", class_="next")
        if next_page and next_page.has_attr("href"):
            page_url = next_page["href"]
            time.sleep(1)
        else:
            break
    return products

def crawl_and_stream_download(progress_bar=None, status=None, count_box=None):
    soup = get_soup(CATEGORY_URL)
    categories = get_subcategories(soup)
    total_products = 0
    cat_count = len(categories)
    all_products = []
    
    # Create a container for download buttons
    download_container = st.container()
    
    for idx, cat in enumerate(categories):
        if status:
            status.text(f"در حال استخراج دسته {idx+1} از {cat_count}: {cat['name']}")
        cat_products = get_products_from_category(cat["url"])
        total_products += len(cat_products)
        
        # Store category data
        category_data = {
            "category_name": cat["name"],
            "category_url": cat["url"],
            "products": cat_products
        }
        all_products.append(category_data)
        
        # Save individual category file
        fname = slugify(cat["name"]) + ".json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(category_data, f, ensure_ascii=False, indent=2)
            
        # Update progress and count
        if progress_bar:
            progress_bar.progress((idx+1)/cat_count)
        if count_box:
            count_box.info(f"تعداد محصولات استخراج‌شده تا این لحظه: {total_products}")
            
        # Add download button to container
        with download_container:
            with open(fname, "rb") as f:
                st.download_button(
                    label=f"دانلود {fname}",
                    data=f,
                    file_name=fname,
                    mime="application/json",
                    key=f"download_{idx}"  # Unique key for each button
                )
    
    # Save and provide combined download
    combined_data = {
        "total_products": total_products,
        "categories": all_products
    }
    combined_filename = "all_products.json"
    with open(combined_filename, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, ensure_ascii=False, indent=2)
    
    with download_container:
        st.markdown("---")
        with open(combined_filename, "rb") as f:
            st.download_button(
                label="دانلود همه محصولات در یک فایل",
                data=f,
                file_name=combined_filename,
                mime="application/json",
                key="download_all"
            )
    
    return total_products

# Streamlit UI
st.set_page_config(page_title="Defrost Scraper", layout="wide")
st.title("🧊 استخراج محصولات یدکی یخچال و فریزر - Defrost.ir")

if st.button("شروع استخراج محصولات!"):
    progress_bar = st.progress(0)
    status = st.empty()
    count_box = st.empty()
    with st.spinner("در حال جمع‌آوری اطلاعات محصولات و آماده‌سازی دانلود هر دسته..."):
        total_products = crawl_and_stream_download(progress_bar, status, count_box)
    st.success(f"استخراج کامل شد! مجموع محصولات: {total_products}")
else:
    st.info("برای شروع استخراج، روی دکمه بالا کلیک کنید.") 