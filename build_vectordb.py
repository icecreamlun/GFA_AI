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
from scrape_gaf_multiple import fetch_html, extract_data, URLS
import os

# 加载预训练模型
model = SentenceTransformer('all-MiniLM-L6-v2')

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

def build_vectordb(contractors: List[Dict], urls: List[str], output_dir: str = "vectordb"):
    """构建向量数据库"""
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 准备文本数据
    texts = [create_contractor_text(contractor, url) for contractor, url in zip(contractors, urls)]
    
    # 生成向量
    embeddings = model.encode(texts)
    
    # 创建 FAISS 索引
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings.astype('float32'))
    
    # 保存索引和元数据
    faiss.write_index(index, f"{output_dir}/index.faiss")
    
    # 保存元数据
    metadata = {
        'texts': texts,
        'contractors': contractors,
        'urls': urls
    }
    with open(f"{output_dir}/metadata.pkl", 'wb') as f:
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
    # 获取承包商数据
    contractors, urls = get_contractors()
    
    # 构建向量数据库
    build_vectordb(contractors, urls)
    print("[i] 向量数据库构建完成")

if __name__ == "__main__":
    main() 