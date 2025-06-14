import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin, quote
import Src.Utilities.config as config
from scrapers.base_scraper import BaseScraper

class AnimeUnityScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "AnimeUnity"
        self.base_url = config.AU_DOMAIN
        self.enabled = config.AU == "1"
        self.api_url = f"{self.base_url}/api"
        
    def search(self, query):
        if not self.enabled:
            return []
            
        try:
            # Prova prima con API JSON se disponibile
            try:
                api_search_url = f"{self.api_url}/search"
                params = {'q': query, 'limit': 10}
                response = self.make_request(api_search_url, params=params)
                
                if response.headers.get('content-type', '').startswith('application/json'):
                    data = response.json()
                    if 'records' in data and data['records']:
                        results = []
                        for anime in data['records']:
                            anime_id = anime.get('id')
                            slug = anime.get('slug', '')
                            title = anime.get('title', anime.get('title_ita', ''))
                            
                            if anime_id and title:
                                results.append({
                                    'title': title,
                                    'url': f"{self.base_url}/anime/{anime_id}-{slug}",
                                    'image': anime.get('imageurl', anime.get('cover')),
                                    'site': 'animeunity',
                                    'anime_id': anime_id
                                })
                        return results[:10]
            except Exception as api_error:
                print(f"AnimeUnity API search failed: {api_error}")
            
            # Fallback HTML search
            return self._search_html(query)
            
        except Exception as e:
            print(f"AnimeUnity search error: {e}")
            return []
    
    def _search_html(self, query):
        """Ricerca HTML fallback"""
        try:
            search_url = f"{self.base_url}/anime"
            params = {'search': query}
            response = self.make_request(search_url, params=params)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            
            # Cerca card anime con vari selettori
            selectors = [
                '.card',
                '.anime-card', 
                'div[class*="card"]',
                '.col-md-3',
                'a[href*="/anime/"]'
            ]
            
            anime_cards = []
            for selector in selectors:
                anime_cards = soup.select(selector)
                if anime_cards:
                    break
            
            for card in anime_cards[:10]:
                try:
                    if card.name == 'a':
                        link_elem = card
                        title = card.get('title', '') or card.text.strip()
                    else:
                        link_elem = card.find('a', href=re.compile(r'/anime/'))
                        if not link_elem:
                            continue
                        
                        # Cerca titolo con vari selettori
                        title_selectors = ['h5', 'h4', 'h3', '.card-title', '.title', '.anime-title']
                        title = ''
                        for sel in title_selectors:
                            title_elem = card.find(sel)
                            if title_elem:
                                title = title_elem.text.strip()
                                break
                    
                    if not title or not link_elem:
                        continue
                        
                    url = urljoin(self.base_url, link_elem.get('href', ''))
                    
                    # Cerca immagine
                    img_elem = card.find('img')
                    image = None
                    if img_elem:
                        img_src = img_elem.get('src') or img_elem.get('data-src')
                        if img_src and not img_src.startswith('data:'):
                            image = urljoin(self.base_url, img_src)
                    
                    # Filtra risultati rilevanti
                    if query.lower() in title.lower() and '/anime/' in url:
                        results.append({
                            'title': title,
                            'url': url,
                            'image': image,
                            'site': 'animeunity'
                        })
                        
                except Exception as e:
                    print(f"Error parsing AnimeUnity card: {e}")
                    continue
                    
            return results
            
        except Exception as e:
            print(f"AnimeUnity HTML search error: {e}")
            return []
    
    def get_episodes(self, anime_url):
        if not self.enabled:
            return []
            
        try:
            response = self.make_request(anime_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            episodes = []
            
            # Metodo 1: Cerca script con dati episodi JSON
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and ('episodes' in script.string or 'episodi' in script.string):
                    # Pattern per trovare array episodi
                    patterns = [
                        r'episodes["\']?\s*:\s*(\[.*?\])',
                        r'episodi["\']?\s*:\s*(\[.*?\])',
                        r'var\s+episodes\s*=\s*(\[.*?\]);',
                        r'let\s+episodes\s*=\s*(\[.*?\]);'
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, script.string, re.DOTALL)
                        if match:
                            try:
                                episodes_data = json.loads(match.group(1))
                                for ep in episodes_data:
                                    if isinstance(ep, dict):
                                        ep_num = ep.get('number', ep.get('episodio', len(episodes) + 1))
                                        episodes.append({
                                            'number': int(ep_num),
                                            'title': f"Episodio {ep_num}",
                                            'url': f"{anime_url}/episodio-{ep_num}"
                                        })
                                    elif isinstance(ep, (int, str)):
                                        episodes.append({
                                            'number': int(ep),
                                            'title': f"Episodio {ep}",
                                            'url': f"{anime_url}/episodio-{ep}"
                                        })
                                break
                            except (json.JSONDecodeError, ValueError) as e:
                                print(f"Error parsing episodes JSON: {e}")
                                continue
                    
                    if episodes:
                        break
            
            # Metodo 2: Cerca link episodi diretti
            if not episodes:
                episode_selectors = [
                    'a[href*="/episodio-"]',
                    'a[href*="episode"]',
                    '.episode-link',
                    '.ep-link'
                ]
                
                for selector in episode_selectors:
                    episode_links = soup.select(selector)
                    if episode_links:
                        for link in episode_links:
                            href = link.get('href', '')
                            # Estrai numero episodio dall'URL
                            ep_match = re.search(r'episodio-(\d+)', href)
                            if ep_match:
                                ep_num = int(ep_match.group(1))
                                episode_url = urljoin(self.base_url, href)
                                episodes.append({
                                    'number': ep_num,
                                    'title': f"Episodio {ep_num}",
                                    'url': episode_url
                                })
                        break
            
            # Metodo 3: Genera episodi basandosi su pattern URL
            if not episodes:
                # Prova a determinare il numero di episodi dalla pagina
                episode_count = self._extract_episode_count(soup)
                if episode_count:
                    for i in range(1, episode_count + 1):
                        episodes.append({
                            'number': i,
                            'title': f"Episodio {i}",
                            'url': f"{anime_url}/episodio-{i}"
                        })
            
            # Se non trova nulla, crea almeno un episodio
            if not episodes:
                episodes = [{
                    'number': 1,
                    'title': 'Episodio 1',
                    'url': anime_url
                }]
            
            return sorted(episodes, key=lambda x: x['number'])[:100]  # Limita a 100 episodi
            
        except Exception as e:
            print(f"AnimeUnity episodes error: {e}")
            return []
    
    def _extract_episode_count(self, soup):
        """Estrae il numero totale di episodi dalla pagina"""
        try:
            # Cerca indicatori del numero di episodi
            indicators = [
                soup.find(text=re.compile(r'(\d+)\s*episod', re.I)),
                soup.find('span', text=re.compile(r'episod', re.I)),
                soup.find('div', text=re.compile(r'episod', re.I))
            ]
            
            for indicator in indicators:
                if indicator:
                    match = re.search(r'(\d+)', str(indicator))
                    if match:
                        return min(int(match.group(1)), 100)  # Massimo 100 episodi
            
            return None
        except:
            return None
    
    def get_stream_links(self, episode_url):
        if not self.enabled:
            return []
            
        try:
            response = self.make_request(episode_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            streams = []
            
            # Metodo 1: Cerca iframe video
            iframes = soup.find_all('iframe')
            for iframe in iframes:
                src = iframe.get('src')
                if src and any(host in src.lower() for host in ['vixcloud', 'streamingaw', 'animeworld', 'mixdrop', 'streamtape']):
                    if not src.startswith('http'):
                        src = urljoin(self.base_url, src)
                    
                    streams.append({
                        'url': src,
                        'quality': 'HD',
                        'type': 'iframe',
                        'server': self._extract_server_name(src)
                    })
            
            # Metodo 2: Cerca video tag diretti
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
                            'type': 'direct',
                            'server': 'Direct'
                        })
            
            # Metodo 3: Cerca nei script JavaScript
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Pattern per trovare URL video
                    patterns = [
                        r'(?:file|src|url)["\']?\s*:\s*["\']([^"\']+\.(?:mp4|m3u8|mkv))["\']',
                        r'https?://[^\s"\']+\.(?:mp4|m3u8|mkv)',
                        r'["\']([^"\']*vixcloud[^"\']*)["\']',
                        r'["\']([^"\']*streamingaw[^"\']*)["\']'
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, script.string, re.I)
                        for match in matches:
                            url = match if isinstance(match, str) else match[0]
                            if url and url.startswith('http'):
                                streams.append({
                                    'url': url,
                                    'quality': 'HD',
                                    'type': 'direct',
                                    'server': 'Script'
                                })
            
            # Rimuovi duplicati
            seen_urls = set()
            unique_streams = []
            for stream in streams:
                if stream['url'] not in seen_urls:
                    seen_urls.add(stream['url'])
                    unique_streams.append(stream)
            
            return unique_streams[:5]  # Limita a 5 stream
            
        except Exception as e:
            print(f"AnimeUnity stream error: {e}")
            return []
    
    def _extract_server_name(self, url):
        """Estrae il nome del server dall'URL"""
        url_lower = url.lower()
        if 'vixcloud' in url_lower:
            return 'VixCloud'
        elif 'streamingaw' in url_lower:
            return 'StreamingAW'
        elif 'animeworld' in url_lower:
            return 'AnimeWorld'
        elif 'mixdrop' in url_lower:
            return 'MixDrop'
        elif 'streamtape' in url_lower:
            return 'StreamTape'
        else:
            return 'Unknown'
