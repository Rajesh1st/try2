from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import os
import json
import time
from urllib.parse import urljoin, urlparse

app = Flask(__name__, static_folder='../static', static_url_path='')
CORS(app)

# Base URL
BASE_URL = "https://asiaflix.vip"

# Better headers - Mimic real browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1'
}

# ============================================
# SERVE STATIC FILES
# ============================================
@app.route('/')
def serve_index():
    return send_from_directory('../static', 'index.html')

@app.route('/drama/<path:path>')
def serve_drama(path):
    return send_from_directory('../static', 'drama.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('../static', path)

# ============================================
# API ROUTES - IMPROVED SCRAPING
# ============================================

@app.route('/api/latest', methods=['GET'])
def get_latest_dramas():
    try:
        print("🔄 Fetching latest dramas...")
        response = requests.get(BASE_URL, headers=HEADERS, timeout=20)
        print(f"✅ Status Code: {response.status_code}")
        
        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'Failed to fetch page: {response.status_code}'
            }), 500
        
        soup = BeautifulSoup(response.text, 'html.parser')
        dramas = []
        
        # Method 1: Find shelf-tile cards
        cards = soup.find_all('div', class_='shelf-tile')
        print(f"🔍 Found {len(cards)} shelf-tile cards")
        
        for card in cards:
            link = card.find('a')
            if link:
                drama_data = extract_drama_from_card(link, card)
                if drama_data:
                    dramas.append(drama_data)
        
        # Method 2: If no cards found, try alternative selectors
        if len(dramas) == 0:
            print("⚠️ No cards found with 'shelf-tile', trying alternative...")
            
            # Try finding drama cards from other classes
            alt_cards = soup.find_all(['div', 'article'], class_=re.compile(r'(drama|card|item|movie|show)'))
            for card in alt_cards:
                link = card.find('a')
                if link:
                    drama_data = extract_drama_from_card(link, card)
                    if drama_data:
                        dramas.append(drama_data)
        
        # Method 3: Look for any links with drama in href
        if len(dramas) == 0:
            print("⚠️ Still no cards found, looking for drama links...")
            all_links = soup.find_all('a', href=re.compile(r'/drama/'))
            for link in all_links[:20]:  # Limit to 20
                title = link.text.strip()
                if title:
                    img = link.find('img')
                    image = img.get('src', '') if img else ''
                    href = link.get('href', '')
                    slug = href.split('/')[-1] if href else ''
                    
                    dramas.append({
                        'slug': slug,
                        'title': title,
                        'image': image,
                        'episode': 'New',
                        'url': href
                    })
        
        print(f"✅ Total dramas found: {len(dramas)}")
        
        return jsonify({
            'success': True,
            'count': len(dramas),
            'data': dramas[:20]  # Limit to 20
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/search', methods=['GET'])
def search_dramas():
    query = request.args.get('q', '')
    if not query:
        return jsonify({'success': False, 'error': 'Search query required'}), 400
    
    try:
        print(f"🔍 Searching for: {query}")
        search_url = f"{BASE_URL}/?s={query}"
        response = requests.get(search_url, headers=HEADERS, timeout=20)
        
        if response.status_code != 200:
            return jsonify({'success': False, 'error': 'Failed to fetch search results'}), 500
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Find search results
        cards = soup.find_all('div', class_='shelf-tile')
        for card in cards:
            link = card.find('a')
            if link:
                drama_data = extract_drama_from_card(link, card)
                if drama_data:
                    results.append(drama_data)
        
        # If no results, try finding drama links
        if len(results) == 0:
            all_links = soup.find_all('a', href=re.compile(r'/drama/'))
            for link in all_links[:20]:
                title = link.text.strip()
                if title and query.lower() in title.lower():
                    img = link.find('img')
                    image = img.get('src', '') if img else ''
                    href = link.get('href', '')
                    slug = href.split('/')[-1] if href else ''
                    
                    results.append({
                        'slug': slug,
                        'title': title,
                        'image': image,
                        'episode': 'New',
                        'url': href
                    })
        
        print(f"✅ Search results: {len(results)}")
        
        return jsonify({
            'success': True,
            'query': query,
            'count': len(results),
            'data': results
        })
        
    except Exception as e:
        print(f"❌ Search error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/drama/<slug>', methods=['GET'])
def get_drama_details(slug):
    try:
        print(f"📺 Fetching drama: {slug}")
        drama_url = f"{BASE_URL}/drama/{slug}"
        response = requests.get(drama_url, headers=HEADERS, timeout=20)
        
        if response.status_code != 200:
            return jsonify({'success': False, 'error': 'Drama not found'}), 404
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        drama_info = extract_drama_info(soup)
        episodes = extract_episodes(soup, slug)
        
        if episodes and len(episodes) > 0:
            first_ep = episodes[0]
            video_data = extract_video_from_episode(slug, first_ep['number'])
            if video_data:
                episodes[0]['video'] = video_data
        
        drama_data = {
            'title': drama_info.get('title', slug.replace('-', ' ').title()),
            'description': drama_info.get('description', 'No description available'),
            'poster': drama_info.get('poster', ''),
            'genres': drama_info.get('genres', []),
            'country': drama_info.get('country', 'Unknown'),
            'status': drama_info.get('status', 'Ongoing'),
            'type': drama_info.get('type', 'TV Series'),
            'views': drama_info.get('views', 0),
            'episodes': episodes
        }
        
        print(f"✅ Drama loaded: {drama_data['title']}, {len(episodes)} episodes")
        
        return jsonify({
            'success': True,
            'data': drama_data
        })
        
    except Exception as e:
        print(f"❌ Drama error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/episode', methods=['GET'])
def get_episode_video():
    slug = request.args.get('drama')
    episode = request.args.get('episode', 1)
    
    if not slug:
        return jsonify({'success': False, 'error': 'Drama slug required'}), 400
    
    try:
        print(f"🎬 Fetching episode {episode} of {slug}")
        video_data = extract_video_from_episode(slug, int(episode))
        
        if video_data and video_data.get('videoUrl'):
            return jsonify({
                'success': True,
                'data': video_data
            })
        else:
            # Try alternative method - search for video in page
            episode_url = f"{BASE_URL}/drama/{slug}?episode={episode}"
            response = requests.get(episode_url, headers=HEADERS, timeout=20)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for video element
            video = soup.find('video')
            if video:
                source = video.find('source')
                if source:
                    video_url = source.get('src', '')
                    if video_url:
                        return jsonify({
                            'success': True,
                            'data': {
                                'videoUrl': video_url,
                                'poster': '',
                                'subtitles': []
                            }
                        })
            
            return jsonify({
                'success': False,
                'error': 'Video not found for this episode'
            }), 404
            
    except Exception as e:
        print(f"❌ Episode error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
        
        # If no featured found, return latest dramas
        if len(featured) == 0:
            return get_latest_dramas()
        
        return jsonify({
            'success': True,
            'count': len(featured),
            'data': featured
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dramas', methods=['GET'])
def get_all_dramas():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    
    try:
        # Try to get from latest first
        response = requests.get(BASE_URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        all_dramas = []
        cards = soup.find_all('div', class_='shelf-tile')
        
        for card in cards:
            link = card.find('a')
            if link:
                drama_data = extract_drama_from_card(link, card)
                if drama_data:
                    all_dramas.append(drama_data)
        
        # Remove duplicates
        seen = set()
        unique_dramas = []
        for drama in all_dramas:
            if drama['slug'] not in seen:
                seen.add(drama['slug'])
                unique_dramas.append(drama)
        
        start = (page - 1) * limit
        end = start + limit
        paginated = unique_dramas[start:end]
        
        return jsonify({
            'success': True,
            'page': page,
            'limit': limit,
            'total': len(unique_dramas),
            'data': paginated
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'AsiaStream Scraper API',
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
        
        # Try multiple ways to get title
        title_elem = card.find('span', class_='kk-tile-title')
        if not title_elem:
            title_elem = card.find(['h3', 'h4', 'div'], class_=re.compile(r'(title|name)'))
        title = title_elem.text.strip() if title_elem else ''
        
        # If no title, try getting from link text
        if not title:
            title = link.text.strip()
        
        # Get episode
        ep_elem = card.find('span', class_='kk-tile-ep')
        if not ep_elem:
            ep_elem = card.find(['span', 'div'], class_=re.compile(r'(ep|episode)'))
        episode = ep_elem.text.strip() if ep_elem else 'New'
        
        # Get image
        img = card.find('img')
        image = img.get('src', '') if img else ''
        
        # If no image, try background image
        if not image:
            style = card.get('style', '')
            match = re.search(r"background-image:url\(['\"]?([^'\"\s)]+)", style)
            if match:
                image = match.group(1)
        
        return {
            'slug': slug,
            'title': title or slug.replace('-', ' ').title(),
            'image': image,
            'episode': episode,
            'url': href
        }
    except Exception as e:
        print(f"Error extracting card: {e}")
        return None

def extract_drama_info(soup):
    info = {}
    try:
        # Title
        title_elem = soup.find('h1', class_='wi-title')
        if not title_elem:
            title_elem = soup.find('h1')
        if title_elem:
            info['title'] = title_elem.text.strip()
        
        # Description
        desc_elem = soup.find('p', class_='wi-desc-text')
        if not desc_elem:
            desc_elem = soup.find(['p', 'div'], class_=re.compile(r'(desc|summary|about)'))
        if desc_elem:
            info['description'] = desc_elem.text.strip()
        
        # Genres
        genres = []
        genre_elems = soup.find_all('span', class_='wi-chip')
        if not genre_elems:
            genre_elems = soup.find_all(['span', 'a'], class_=re.compile(r'(genre|tag)'))
        for genre in genre_elems:
            genres.append(genre.text.strip())
        info['genres'] = genres
        
        # Meta
        meta_elem = soup.find('div', class_='wi-meta')
        if meta_elem:
            meta_parts = meta_elem.text.strip().split('|')
            if len(meta_parts) >= 3:
                info['country'] = meta_parts[0].strip()
                info['status'] = meta_parts[1].strip()
                info['type'] = meta_parts[2].strip()
        
        # Poster
        poster_elem = soup.find('img', class_='poster-state-bg')
        if not poster_elem:
            poster_elem = soup.find('img', class_=re.compile(r'(poster|cover|thumbnail)'))
        if poster_elem:
            info['poster'] = poster_elem.get('src', '')
        
        # Views
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
        
        # Method 1: Look in script tags
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
        
        # Method 2: Look for video element
        if not video_data['videoUrl']:
            video = soup.find('video')
            if video:
                source = video.find('source')
                if source:
                    video_data['videoUrl'] = source.get('src', '')
        
        return video_data if video_data['videoUrl'] else None
    except Exception as e:
        print(f"Error extracting video: {e}")
        return None

# ============================================
# VERCEL SERVERLESS HANDLER
# ============================================
from mangum import Mangum
handler = Mangum(app)
