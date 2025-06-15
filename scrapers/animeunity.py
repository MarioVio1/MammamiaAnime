import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin, quote, urlparse, parse_qs
import Src.Utilities.config as config
from scrapers.base_scraper import BaseScraper

class AnimeUnityScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "AnimeUnity"
        self.base_url = "https://www.animeunity.so"
        self.enabled = getattr(config, 'AU', '0') == "1"
        
    def search(self, query):
        if not self.enabled:
            return []
            
        try:
            print(f"🔍 AnimeUnity searching for: {query}")
            
            # METODO 1: API di ricerca
            try:
                api_url = f"{self.base_url}/api/search"
                params = {'q': query, 'limit': 15}
                
                response = self.make_request(api_url, params=params)
                print(f"API Response status: {response.status_code}")
                print(f"API Response headers: {response.headers.get('content-type', 'unknown')}")
                
                if response.status_code == 200 and 'application/json' in response.headers.get('content-type', ''):
                    data = response.json()
                    print(f"API Response data keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
                    
                    results = []
                    records = data.get('records', data.get('data', data.get('results', [])))
                    
                    for anime in records:
                        anime_id = anime.get('id')
                        slug = anime.get('slug', '')
                        title = anime.get('title', anime.get('title_ita', anime.get('name', '')))
                        
                        if anime_id and title:
                            anime_url = f"{self.base_url}/anime/{anime_id}"
                            if slug:
                                anime_url += f"-{slug}"
                            
                            results.append({
                                'title': title,
                                'url': anime_url,
                                'image': anime.get('imageurl', anime.get('cover', anime.get('poster'))),
                                'site': 'animeunity',
                                'anime_id': anime_id
                            })
                    
                    if results:
                        print(f"✅ AnimeUnity API found {len(results)} results")
                        return results[:10]
                    else:
                        print("❌ AnimeUnity API returned empty results")
                else:
                    print(f"❌ AnimeUnity API failed: {response.status_code}")
            
            except Exception as api_error:
                print(f"❌ AnimeUnity API error: {api_error}")
            
            # METODO 2: Ricerca HTML fallback
            print("🔄 Trying AnimeUnity HTML search...")
            search_url = f"{self.base_url}/anime"
            params = {'search': query}
            
            response = self.make_request(search_url, params=params)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            
            # Selettori multipli per AnimeUnity
            selectors_to_try = [
                'div.card',
                'div.anime-card',
                'article.card',
                '.col-md-3',
                '.col-sm-6',
                'a[href*="/anime/"]'
            ]
            
            cards = []
            for selector in selectors_to_try:
                cards = soup.select(selector)
                if cards:
                    print(f"✅ AnimeUnity HTML found {len(cards)} cards with: {selector}")
                    break
            
            if not cards:
                # Fallback estremo
                all_links = soup.find_all('a')
                cards = [link for link in all_links if '/anime/' in link.get('href', '')]
                print(f"🔄 AnimeUnity fallback found {len(cards)} anime links")
            
            for card in cards[:10]:
                try:
                    if card.name == 'a':
                        link = card
                        title = card.get('title', '').strip() or card.text.strip()
                    else:
                        link = card.find('a')
                        if not link:
                            continue
                        
                        # Cerca titolo con vari selettori
                        title_selectors = ['h5.card-title', 'h4', 'h3', '.title', '.anime-title']
                        title = ''
                        for sel in title_selectors:
                            title_elem = card.select_one(sel)
                            if title_elem:
                                title = title_elem.text.strip()
                                break
                        
                        if not title:
                            title = link.get('title', '').strip() or link.text.strip()
                    
                    if not title or not link:
                        continue
                    
                    href = link.get('href', '')
                    if not href or '/anime/' not in href:
                        continue
                    
                    url = urljoin(self.base_url, href)
                    
                    # Cerca immagine
                    img_elem = card.find('img')
                    image = None
                    if img_elem:
                        img_src = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy')
                        if img_src and not img_src.startswith('data:'):
                            image = urljoin(self.base_url, img_src)
                    
                    if len(title) > 2:
                        print(f"   Found: {title} - {url}")
                        results.append({
                            'title': title,
                            'url': url,
                            'image': image,
                            'site': 'animeunity'
                        })
                        
                except Exception as e:
                    print(f"Error parsing AnimeUnity card: {e}")
                    continue
            
            print(f"🎯 AnimeUnity HTML found {len(results)} results")
            return results
            
        except Exception as e:
            print(f"AnimeUnity search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_episodes(self, anime_url):
        if not self.enabled:
            return []
            
        try:
            print(f"📺 Getting AnimeUnity episodes from: {anime_url}")
            response = self.make_request(anime_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            episodes = []
            
            # METODO 1: Cerca episodi in script JSON
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and ('episodes' in script.string or 'episodi' in script.string):
                    try:
                        # Cerca array episodi nel JavaScript
                        episodes_patterns = [
                            r'episodes["\']?\s*:\s*(\[.*?\])',
                            r'episodi["\']?\s*:\s*(\[.*?\])',
                            r'var\s+episodes\s*=\s*(\[.*?\]);',
                            r'let\s+episodes\s*=\s*(\[.*?\]);',
                            r'episodes\s*=\s*(\[.*?\]);'
                        ]
                        
                        for pattern in episodes_patterns:
                            match = re.search(pattern, script.string, re.DOTALL)
                            if match:
                                try:
                                    episodes_data = json.loads(match.group(1))
                                    for ep in episodes_data:
                                        if isinstance(ep, dict):
                                            ep_num = ep.get('number', ep.get('episodio', ep.get('episode_number', len(episodes) + 1)))
                                            episodes.append({
                                                'number': int(ep_num),
                                                'title': f"Episodio {ep_num}",
                                                'url': f"{anime_url}/episodio-{ep_num}"
                                            })
                                        elif isinstance(ep, (int, str)):
                                            ep_num = int(ep)
                                            episodes.append({
                                                'number': ep_num,
                                                'title': f"Episodio {ep}",
                                                'url': f"{anime_url}/episodio-{ep}"
                                            })
                                    break
                                except json.JSONDecodeError:
                                    continue
                        
                        if episodes:
                            break
                    except:
                        continue
            
            # METODO 2: Cerca link episodi diretti
            if not episodes:
                episode_links = soup.find_all('a', href=re.compile(r'/episodio-'))
                for link in episode_links:
                    href = link.get('href', '')
                    ep_match = re.search(r'episodio-(\d+)', href)
                    if ep_match:
                        ep_num = int(ep_match.group(1))
                        episode_url = urljoin(self.base_url, href)
                        episodes.append({
                            'number': ep_num,
                            'title': f"Episodio {ep_num}",
                            'url': episode_url
                        })
            
            # METODO 3: Se non trova episodi, crea almeno il primo
            if not episodes:
                # Estrai ID anime dall'URL
                anime_id_match = re.search(r'/anime/(\d+)', anime_url)
                if anime_id_match:
                    anime_id = anime_id_match.group(1)
                    episodes = [{
                        'number': 1,
                        'title': 'Episodio 1',
                        'url': f"{self.base_url}/anime/{anime_id}/episodio-1"
                    }]
            
            print(f"📺 AnimeUnity found {len(episodes)} episodes")
            return sorted(episodes, key=lambda x: x['number'])[:50]
            
        except Exception as e:
            print(f"AnimeUnity episodes error: {e}")
            return []
    
    def get_stream_links(self, episode_url):
        if not self.enabled:
            return []
            
        try:
            print(f"🔗 Getting AnimeUnity streams from: {episode_url}")
            response = self.make_request(episode_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            streams = []
            page_content = response.text
            
            # METODO 1: Cerca link scws-content.net nei script (PRIORITÀ)
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Pattern specifici per AnimeUnity MP4 diretti
                    patterns = [
                        r'https://au-d\d+-\d+\.scws-content\.net/download/[^"\']*\.mp4[^"\']*',
                        r'https://[^"\']*\.scws-content\.net/[^"\']*\.mp4[^"\']*',
                        r'(?:file|src|url|download|video)["\']?\s*:\s*["\']([^"\']*scws-content[^"\']*\.mp4[^"\']*)["\']',
                        r'["\']([^"\']*au-d\d+-\d+\.scws-content\.net[^"\']*\.mp4[^"\']*)["\']'
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, script.string, re.I)
                        for match in matches:
                            url = match if isinstance(match, str) else match[0]
                            if url and url.startswith('http') and 'scws-content.net' in url and '.mp4' in url:
                                print(f"   ✅ Found AnimeUnity MP4: {url}")
                                
                                # Estrai qualità dal path
                                quality = 'HD'
                                if '1080p' in url:
                                    quality = '1080p'
                                elif '720p' in url:
                                    quality = '720p'
                                elif '480p' in url:
                                    quality = '480p'
                                
                                streams.append({
                                    'url': url,
                                    'quality': quality,
                                    'type': 'direct'
                                })
            
            # METODO 2: Cerca iframe AnimeUnity
            iframes = soup.find_all('iframe')
            for iframe in iframes:
                src = iframe.get('src')
                if src and ('animeunity' in src.lower() or 'scws-content' in src.lower()):
                    if not src.startswith('http'):
                        src = urljoin(self.base_url, src)
                    
                    streams.append({
                        'url': src,
                        'quality': 'HD',
                        'type': 'iframe'
                    })
            
            # METODO 3: Cerca video tag diretti
            video_tags = soup.find_all('video')
            for video in video_tags:
                sources = video.find_all('source')
                for source in sources:
                    src = source.get('src')
                    if src and 'scws-content.net' in src:
                        streams.append({
                            'url': src,
                            'quality': source.get('data-quality', 'HD'),
                            'type': 'direct'
                        })
            
            print(f"🎯 AnimeUnity found {len(streams)} streams")
            return streams[:5]
            
        except Exception as e:
            print(f"❌ AnimeUnity stream error: {e}")
            return []
