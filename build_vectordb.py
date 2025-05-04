#!/usr/bin/env python3
# coding: utf-8
"""
构建 GAF 承包商信息的向量数据库
"""

import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import pickle
from scrape_gaf_multiple import fetch_html, extract_data, URLS, scrape_contractors
import os

def create_contractor_text(contractor: Dict, url: str) -> str:
    """将承包商信息转换为文本"""
    text_parts = [
        f"Company Name: {contractor['name']}",
        f"Address: {contractor['address']}",
        f"Phone: {contractor['phone']}",
        f"URL: {url}",
    ]
    
    if 'about_us' in contractor:
        text_parts.append(f"About Us: {contractor['about_us']}")
    
    if 'years_in_business' in contractor:
        text_parts.append(f"Years in Business: {contractor['years_in_business']}")
    
    if 'number_of_employees' in contractor:
        text_parts.append(f"Number of Employees: {contractor['number_of_employees']}")
    
    if 'state_license_number' in contractor:
        text_parts.append(f"State License Number: {contractor['state_license_number']}")
    
    if 'certifications' in contractor and contractor['certifications']:
        text_parts.append(f"Certifications: {', '.join(contractor['certifications'])}")
    
    return " | ".join(text_parts)

def build_vector_db():
    """Build and save the vector database"""
    # Load pre-trained model
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Get contractor data
    contractors = scrape_contractors()
    
    # Create output directory
    os.makedirs("vectordb", exist_ok=True)
    
    # Prepare text data
    texts = []
    for contractor in contractors:
        text = f"{contractor.get('name', '')} {contractor.get('about_us', '')} {contractor.get('address', '')}"
        texts.append(text)
    
    # Generate vectors
    embeddings = model.encode(texts)
    embeddings = np.array(embeddings).astype('float32')
    
    # Create FAISS index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    
    # Save index and metadata
    faiss.write_index(index, "vectordb/index.faiss")
    
    # Save metadata
    metadata = {
        "texts": texts,
        "contractors": contractors,
        "urls": [c.get("url", "") for c in contractors]
    }
    with open("vectordb/metadata.pkl", "wb") as f:
        pickle.dump(metadata, f)

def get_contractors() -> tuple[List[Dict], List[str]]:
    """获取所有承包商数据"""
    contractors = []
    urls = []
    for url in URLS:
        print(f"[i] 处理URL: {url}")
        html = fetch_html(url, "Preferred Exterior Corp _ GAF Residential Roofers.html")
        contractor = extract_data(html)
        contractors.append(contractor)
        urls.append(url)
    return contractors, urls

def main():
    # Get contractor data
    contractors = scrape_contractors()
    
    # Build vector database
    build_vector_db()
    print("[i] Vector database built and saved")

if __name__ == "__main__":
    main() 