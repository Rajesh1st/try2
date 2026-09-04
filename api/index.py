from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import os
import json
from urllib.parse import urljoin, urlparse
import time

app = Flask(__name__, static_folder='../static', static_url_path='')
CORS(app)

# Base URL of the site
BASE_URL = "https://asiaflix.vip"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

# ============================================
# SERVE STATIC FILES (Frontend)
# ============================================
@app.route('/')
def serve_index():
    """Serve homepage"""
    return send_from_directory('../static', 'index.html')

@app.route('/drama/<path:path>')
def serve_drama(path):
    """Serve drama page"""
    return send_from_directory('../static', 'drama.html')

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('../static', path)

# ============================================
# API ROUTES
# ============================================

# 1. GET LATEST DRAMAS
@app.route('/api/latest', methods=['GET'])
def get_latest_dramas():
    try:
        response = requests.get(BASE_URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        dramas = []
        
        shelf_tracks = soup.find_all('div', class_='shelf-track')
        for track in shelf_tracks:
            cards = track.find_all('div', class_='shelf-tile')
            for card in cards:
                link = card.find('a')
                if link:
                    drama_data = extract_drama_from_card(link, card)
                    if drama_data:
                        dramas.append(drama_data)
        
        return jsonify({
            'success': True,
            'count': len(dramas),
            'data': dramas
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 2. SEARCH DRAMAS
@app.route('/api/search', methods=['GET'])
def search_dramas():
    query = request.args.get('q', '')
    if not query:
        return jsonify({'success': False, 'error': 'Search query required'}), 400
    
    try:
        search_url = f"{BASE_URL}/?s={query}"
        response = requests.get(search_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        cards = soup.find_all('div', class_='shelf-tile')
        
        for card in cards:
            link = card.find('a')
            if link:
                drama_data = extract_drama_from_card(link, card)
                if drama_data:
                    results.append(drama_data)
        
        return jsonify({
            'success': True,
            'query': query,
            'count': len(results),
            'data': results
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 3. GET DRAMA DETAILS
@app.route('/api/drama/<slug>', methods=['GET'])
def get_drama_details(slug):
    try:
        drama_url = f"{BASE_URL}/drama/{slug}"
        response = requests.get(drama_url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        drama_info = extract_drama_info(soup)
        episodes = extract_episodes(soup, slug)
        
        if episodes and len(episodes) > 0:
            first_ep = episodes[0]
            video_data = extract_video_from_episode(slug, first_ep['number'])
            if video_data:
                episodes[0]['video'] = video_data
        
        drama_data = {
            'title': drama_info.get('title', ''),
            'description': drama_info.get('description', ''),
            'poster': drama_info.get('poster', ''),
            'genres': drama_info.get('genres', []),
            'country': drama_info.get('country', ''),
            'status': drama_info.get('status', ''),
            'type': drama_info.get('type', ''),
            'views': drama_info.get('views', 0),
            'episodes': episodes
        }
        
        return jsonify({
            'success': True,
            'data': drama_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 4. GET EPISODE VIDEO
@app.route('/api/episode', methods=['GET'])
def get_episode_video():
    slug = request.args.get('drama')
    episode = request.args.get('episode', 1)
    
    if not slug:
        return jsonify({'success': False, 'error': 'Drama slug required'}), 400
    
    try:
        video_data = extract_video_from_episode(slug, int(episode))
        if video_data:
            return jsonify({'success': True, 'data': video_data})
        else:
            return jsonify({'success': False, 'error': 'Video not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 5. GET BY CATEGORY
@app.route('/api/category/<category>', methods=['GET'])
def get_by_category(category):
    try:
        category_url = f"{BASE_URL}/?content_type=drama&type={category}"
        response = requests.get(category_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        dramas = []
        cards = soup.find_all('div', class_='shelf-tile')
        for card in cards:
            link = card.find('a')
            if link:
                drama_data = extract_drama_from_card(link, card)
                if drama_data:
                    dramas.append(drama_data)
        
        return jsonify({
            'success': True,
            'category': category,
            'count': len(dramas),
            'data': dramas
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 6. GET FEATURED DRAMAS
@app.route('/api/featured', methods=['GET'])
def get_featured_dramas():
    try:
        response = requests.get(BASE_URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        featured = []
        hero_slider = soup.find('div', id='heroSlider')
        
        if hero_slider:
            slides = hero_slider.find_all('a', class_='hero-slide')
            for slide in slides:
                bg_style = slide.find('div', class_='hero-slide-bg')
                image = ''
                if bg_style:
                    style = bg_style.get('style', '')
                    match = re.search(r"background-image:url\('([^']+)'\)", style)
                    if match:
                        image = match.group(1)
                
                title_elem = slide.find('h2', class_='hero-slide-title')
                title = title_elem.text.strip() if title_elem else ''
                
                tag_elem = slide.find('div', class_='hero-slide-tag')
                tag = tag_elem.text.strip() if tag_elem else ''
                
                href = slide.get('href', '')
                slug = href.split('/')[-1] if href else ''
                
                featured.append({
                    'slug': slug,
                    'title': title,
                    'image': image,
                    'tag': tag,
                    'url': href
                })
        
        return jsonify({
            'success': True,
            'count': len(featured),
            'data': featured
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 7. HEALTH CHECK
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'AsiaFlix Scraper API',
        'version': '1.0.0'
    })

# ============================================
# HELPER FUNCTIONS
# ============================================

def extract_drama_from_card(link, card):
    try:
        href = link.get('href', '')
        if not href or href == '#':
            return None
        
        slug = href.split('/')[-1] if href else ''
        title_elem = card.find('span', class_='kk-tile-title')
        title = title_elem.text.strip() if title_elem else ''
        ep_elem = card.find('span', class_='kk-tile-ep')
        episode = ep_elem.text.strip() if ep_elem else ''
        img = card.find('img')
        image = img.get('src', '') if img else ''
        
        return {
            'slug': slug,
            'title': title,
            'image': image,
            'episode': episode,
            'url': href
        }
    except:
        return None

def extract_drama_info(soup):
    info = {}
    try:
        title_elem = soup.find('h1', class_='wi-title')
        if title_elem:
            info['title'] = title_elem.text.strip()
        
        desc_elem = soup.find('p', class_='wi-desc-text')
        if desc_elem:
            info['description'] = desc_elem.text.strip()
        
        genres = []
        genre_elems = soup.find_all('span', class_='wi-chip')
        for genre in genre_elems:
            genres.append(genre.text.strip())
        info['genres'] = genres
        
        meta_elem = soup.find('div', class_='wi-meta')
        if meta_elem:
            meta_parts = meta_elem.text.strip().split('|')
            if len(meta_parts) >= 3:
                info['country'] = meta_parts[0].strip()
                info['status'] = meta_parts[1].strip()
                info['type'] = meta_parts[2].strip()
        
        poster_elem = soup.find('img', class_='poster-state-bg')
        if poster_elem:
            info['poster'] = poster_elem.get('src', '')
        
        stats_elem = soup.find('div', class_='wi-desc-stats')
        if stats_elem:
            view_text = stats_elem.text
            match = re.search(r'(\d+)\s*views', view_text)
            if match:
                info['views'] = int(match.group(1))
    except Exception as e:
        print(f"Error extracting info: {e}")
    return info

def extract_episodes(soup, slug):
    episodes = []
    try:
        ep_list = soup.find('div', class_='ep-list')
        if ep_list:
            ep_links = ep_list.find_all('a', class_='ep-cell')
            for link in ep_links:
                ep_num = link.text.strip()
                if ep_num.isdigit():
                    episodes.append({
                        'number': int(ep_num),
                        'url': link.get('href', ''),
                        'has_subtitles': 'closed-captioning' in str(link)
                    })
    except Exception as e:
        print(f"Error extracting episodes: {e}")
    return episodes

def extract_video_from_episode(slug, episode):
    try:
        episode_url = f"{BASE_URL}/drama/{slug}?episode={episode}"
        response = requests.get(episode_url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        video_data = {
            'videoUrl': None,
            'poster': None,
            'subtitles': []
        }
        
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                match = re.search(r"var videoUrl = '([^']+)';", script.string)
                if match:
                    video_data['videoUrl'] = match.group(1)
                
                match = re.search(r"var posterUrl = '([^']+)';", script.string)
                if match:
                    video_data['poster'] = match.group(1)
                
                subtitle_matches = re.findall(r"file: '([^']+)',\s*label: '([^']+)'", script.string)
                for sub_url, label in subtitle_matches:
                    video_data['subtitles'].append({
                        'url': sub_url,
                        'language': label,
                        'kind': 'captions'
                    })
        
        return video_data if video_data['videoUrl'] else None
    except Exception as e:
        print(f"Error extracting video: {e}")
        return None

# ============================================
# VERCEL SERVERLESS HANDLER
# ============================================
from mangum import Mangum
handler = Mangum(app)
