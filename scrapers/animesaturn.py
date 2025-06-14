import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, quote
import Src.Utilities.config as config
from scrapers.base_scraper import BaseScraper

class AnimeSaturnScraper(BaseScraper):
    def search(self, query):
        if not self.enabled:
            return []
            
        try:
            # METODO 1: Ricerca diretta
            search_url = f"{self.base_url}/animelist"
            search_params = {'search': query}
            response = self.make_request(search_url, params=search_params)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            
            # SELETTORI AGGIORNATI per AnimeSaturn 2025
            selectors_to_try = [
                'div.item-archivio',
                'div.anime-card',
                'div.card',
                '.anime-item',
                'a[href*="/anime/"]'
            ]
            
            anime_items = []
            for selector in selectors_to_try:
                anime_items = soup.select(selector)
                if anime_items:
                    print(f"✅ Found {len(anime_items)} items with selector: {selector}")
                    break
            
            if not anime_items:
                print("❌ No items found with any selector")
                # FALLBACK: Cerca tutti i link che contengono "anime"
                anime_items = soup.find_all('a', href=re.compile(r'/anime/'))
                print(f"🔄 Fallback found {len(anime_items)} anime links")
            
            for item in anime_items[:10]:
                try:
                    if item.name == 'a':
                        link_elem = item
                        title = item.get('title', '').strip() or item.text.strip()
                    else:
                        link_elem = item.find('a')
                        if not link_elem:
                            continue
                        title = link_elem.get('title', '').strip()
                        if not title:
                            title_elem = item.find(['h3', 'h2', '.title', '.anime-title'])
                            title = title_elem.text.strip() if title_elem else ''
                    
                    if not title or not link_elem:
                        continue
                        
                    url = urljoin(self.base_url, link_elem.get('href', ''))
                    
                    # Cerca immagine
                    img_elem = item.find('img')
                    image = None
                    if img_elem:
                        img_src = img_elem.get('src') or img_elem.get('data-src')
                        if img_src and not img_src.startswith('data:'):
                            image = urljoin(self.base_url, img_src)
                    
                    if title and url and '/anime/' in url:
                        print(f"   Found: {title} - {url}")
                        results.append({
                            'title': title,
                            'url': url,
                            'image': image,
                            'site': 'animesaturn'
                        })
                        
                except Exception as e:
                    print(f"Error parsing item: {e}")
                    continue
            
            print(f"🎯 AnimeSaturn search returned {len(results)} results")
            return results
            
        except Exception as e:
            print(f"AnimeSaturn search error: {e}")
            import traceback
            traceback.print_exc()
            return []

    
    def get_episodes(self, anime_url):
        if not self.enabled:
            return []
            
        try:
            response = self.make_request(anime_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            episodes = []
            episode_links = soup.find_all('a', href=re.compile(r'/ep/'))
            
            for link in episode_links:
                try:
                    episode_url = urljoin(self.base_url, link.get('href'))
                    episode_title = link.text.strip()
                    
                    episode_match = re.search(r'(?:episodio[- ]?|ep[- ]?)(\d+)', episode_title.lower())
                    if episode_match:
                        episode_num = int(episode_match.group(1))
                    else:
                        episode_num = len(episodes) + 1
                    
                    episodes.append({
                        'number': episode_num,
                        'title': episode_title or f"Episodio {episode_num}",
                        'url': episode_url
                    })
                    
                except Exception as e:
                    continue
                    
            return sorted(episodes, key=lambda x: x['number'])
            
        except Exception as e:
            print(f"AnimeSaturn episodes error: {e}")
            return []
    
    def get_stream_links(self, episode_url):  # ← LINEA 173 CORRETTA
        if not self.enabled:  # ← INDENTAZIONE CORRETTA
            return []
            
        try:
            print(f"🔗 Getting streams from: {episode_url}")
            response = self.make_request(episode_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            streams = []
            
            # Cerca iframe video
            iframes = soup.find_all('iframe')
            print(f"📺 Found {len(iframes)} iframes")
            
            for iframe in iframes:
                src = iframe.get('src')
                if src:
                    print(f"   Iframe src: {src}")
                    if any(host in src.lower() for host in ['vixcloud', 'streamingaw', 'streamtape', 'mixdrop', 'doodstream']):
                        if not src.startswith('http'):
                            src = urljoin(self.base_url, src)
                        
                        streams.append({
                            'url': src,
                            'quality': 'HD',
                            'type': 'iframe'
                        })
            
            # Cerca video tag diretti
            video_tags = soup.find_all('video')
            for video in video_tags:
                sources = video.find_all('source')
                for source in sources:
                    src = source.get('src')
                    if src:
                        if not src.startswith('http'):
                            src = urljoin(self.base_url, src)
                        
                        streams.append({
                            'url': src,
                            'quality': source.get('data-quality', 'HD'),
                            'type': 'direct'
                        })
            
            print(f"🎯 Total streams found: {len(streams)}")
            return streams[:5]
            
        except Exception as e:
            print(f"AnimeSaturn stream error: {e}")
            return []
