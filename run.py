from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from Src.API.filmpertutti import filmpertutti
from Src.API.streamingcommunity import streaming_community
from Src.API.tantifilm import tantifilm
from Src.API.lordchannel import lordchannel
from Src.API.streamingwatch import streamingwatch
from Src.API.ddlstream import ddlstream
from Src.API.cb01 import cb01
from Src.API.guardaserie import guardaserie
from Src.API.guardahd import guardahd
import Src.Utilities.config as config
import logging
from Src.API.okru import okru_get_url
from Src.API.animeworld import animeworld
from Src.Utilities.dictionaries import okru, STREAM, extra_sources, webru_vary, webru_dlhd, provider_map, skystreaming
from Src.API.epg import tivu, tivu_get, epg_guide, convert_bho_1, convert_bho_2, convert_bho_3
from Src.API.webru import webru, get_skystreaming
from Src.API.onlineserietv import onlineserietv
from curl_cffi.requests import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from static.static import HTML
from urllib.parse import unquote
from Src.Utilities.m3u8 import router as m3u8_clone
import urllib.parse

# Configure Env Vars
Global_Proxy = config.Global_Proxy
if Global_Proxy == "1":
    from Src.Utilities.loadenv import load_env
    env_vars = load_env()
    PROXY_CREDENTIALS = env_vars.get('PROXY_CREDENTIALS')
    proxies = {
        "http": PROXY_CREDENTIALS,
        "https": PROXY_CREDENTIALS
    }
else:
    proxies = {}

# Configure config
MYSTERIUS = config.MYSTERIUS
DLHD = config.DLHD
SC = config.SC
SC_DOMAIN = config.SC_DOMAIN
FT = config.FT
TF = config.TF
LC = config.LC
SW = config.SW
AW = config.AW
SKY = config.SKY
CB = config.CB
DDL = config.DDL
GS = config.GS
GHD = config.GHD
OST = config.OST
HOST = config.HOST
PORT = int(config.PORT)
Icon = config.Icon
Name = config.Name
SKY_DOMAIN = config.SKY_DOMAIN
Remote_Instance = config.Remote_Instance

if MYSTERIUS == "1":
    from Src.API.cool import cool

DDL_DOMAIN = config.DDL_DOMAIN

# INIZIALIZZA FASTAPI CON CORS
app = FastAPI()

# AGGIUNGI CORS MIDDLEWARE - CRUCIALE PER STREMIO
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(m3u8_clone)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
User_Agent = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0"

# MANIFEST CONFORME ALLA SPECIFICA UFFICIALE STREMIO
MANIFEST = {
    "id": "org.stremio.mammamia",
    "version": "1.5.0",
    "name": Name,
    "description": "Addon providing HTTPS Streams for Italian Movies, Series, and Live TV! Note that you need to have Kitsu Addon installed in order to watch Anime",
    "logo": "https://creazilla-store.fra1.digitaloceanspaces.com/emojis/49647/pizza-emoji-clipart-md.png",
    "resources": ["stream", "catalog", "meta"],
    "types": ["movie", "series", "tv"],
    "catalogs": [
        {
            "type": "tv",
            "id": "tv_channels",
            "name": "MammaMia",
            "behaviorHints": {
                "configurable": True,
                "configurationRequired": True
            },
            "extra": [
                {
                    "name": "genre",
                    "isRequired": False,
                    "options": ["Rai", "Mediaset", "Sky", "Euronews", "La7", "Warner Bros", "FIT", "Sportitalia", "RSI", "DAZN", "Rakuten", "Pluto", "A+E", "Paramount", "Chill"]
                }
            ]
        }
    ]
}

def respond_with(data):
    """Helper function come da esempio ufficiale Stremio"""
    resp = JSONResponse(data)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = '*'
    return resp

async def transform_mfp(mfp_stream_url, client):
    try:
        response = await client.get(mfp_stream_url)
        data = response.json()
        url = data['mediaflow_proxy_url'] + "?api_password=" + data['query_params']['api_password'] + "&d=" + urllib.parse.quote(data['destination_url'])
        for i in data['request_headers']:
            url += f"&h_{i}={urllib.parse.quote(data['request_headers'][i])}"
        return url
    except Exception as e:
        print("Transforming MFP failed", e)
        return None

# ENDPOINT MANIFEST - OBBLIGATORIO SECONDO DOCUMENTAZIONE
@app.get('/manifest.json')
def addon_manifest():
    """Endpoint manifest come da specifica ufficiale Stremio"""
    print("📋 Manifest request received")
    return respond_with(MANIFEST)

@app.get('/config')
def config_redirect():
    return RedirectResponse(url="/")

@app.get('/{config:path}/manifest.json')
def addon_manifest_config(config: str):
    print(f"📋 Manifest with config: {config}")
    manifest_copy = MANIFEST.copy()
    
    if "LIVETV" in config:
        return respond_with(manifest_copy)
    elif "LIVETV" not in config:
        manifest_copy["catalogs"] = []
        if "catalog" in manifest_copy["resources"]:
            manifest_copy["resources"].remove("catalog")
        return respond_with(manifest_copy)

@app.get('/', response_class=HTMLResponse)
def root(request: Request):
    forwarded_proto = request.headers.get("x-forwarded-proto")
    scheme = forwarded_proto if forwarded_proto else request.url.scheme
    instance_url = f"{scheme}://{request.url.netloc}"
    html_content = HTML.replace("{instance_url}", instance_url)
    return html_content

# RESTO DEL CODICE ORIGINALE (catalogs, meta, stream)
async def addon_catalog(type: str, id: str, genre: str = None):
    if type != "tv":
        raise HTTPException(status_code=404)
    
    catalogs = {"metas": []}
    
    for channel in STREAM["channels"]:
        if genre and genre not in channel.get("genres", []):
            continue
        
        description = f'Watch {channel["title"]}'
        catalogs["metas"].append({
            "id": channel["id"],
            "type": "tv",
            "name": channel["title"],
            "poster": channel["poster"],
            "description": description,
            "genres": channel.get("genres", [])
        })

    return catalogs

@app.get('/{config:path}/catalog/{type}/{id}.json')
@limiter.limit("5/second")
async def first_catalog(request: Request, type: str, id: str, genre: str = None):
    catalogs = await addon_catalog(type, id, genre)
    return respond_with(catalogs)

@app.get('/{config:path}/catalog/{type}/{id}/genre={genre}.json')
async def catalog_with_genre(type: str, id: str, genre: str = None):
    catalogs = await addon_catalog(type, id, genre)
    return respond_with(catalogs)

@app.get('/{config:path}/meta/tv/{id}.json')
@limiter.limit("20/second")
async def addon_meta(request: Request, id: str):
    channel = next((ch for ch in STREAM['channels'] if ch['id'] == id), None)
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    async with AsyncSession(proxies=proxies) as client:
        if channel["id"] in convert_bho_1 or channel["id"] in convert_bho_2 or channel["id"] in convert_bho_3:
            description, title = await epg_guide(channel["id"], client)
        elif channel["id"] in tivu:
            description = await tivu_get(channel["id"], client)
            title = ""
        else:
            description = f'Watch {channel["title"]}'
            title = ""
    
    meta = {
        'meta': {
            'id': channel['id'],
            'type': 'tv',
            'name': channel['name'],
            'poster': channel['poster'],
            'posterShape': 'landscape',
            'description': title + "\n" + description,
            'background': channel['poster'],
            'logo': channel['poster'],
            'genres': channel.get('genres', []),
        }
    }
    if 'url' in channel:
        meta['meta']['url'] = channel['url']
    return respond_with(meta)

@app.get('/{config:path}/stream/{type}/{id}.json')
@limiter.limit("5/second")
async def addon_stream(request: Request, config, type, id):
    if type not in MANIFEST['types']:
        raise HTTPException(status_code=404)
    
    streams = {'streams': []}
    
    if "|" in config:
        config_providers = config.split('|')
    elif "%7C" in config:
        config_providers = config.split('%7C')
    else:
        config_providers = []
        
    provider_maps = {name: "0" for name in provider_map.values()}
    for provider in config_providers:
        if provider in provider_map:
            provider_name = provider_map[provider]
            provider_maps[provider_name] = "1"
    
    MFP = "0"
    MFP_CREDENTIALS = None
    
    if "MFP[" in config:
        mfp_data = config.split("MFP[")[1].split(")")[0]
        MFP_url, MFP_password = mfp_data.split(",")
        MFP_password = MFP_password[:-2]
        MFP_CREDENTIALS = [MFP_url, MFP_password]
        if MFP_url and MFP_password:
            MFP = "1"
    
    async with AsyncSession(proxies=proxies) as client:
        if type == "tv":
            # TUTTO IL CODICE TV ORIGINALE
            for channel in STREAM["channels"]:
                if channel["id"] == id:
                    i = 0
                    if 'url' in channel:
                        i = i+1
                        streams['streams'].append({
                            'title': f"{Icon}Server {i} " + f" "+ channel['name'] + " " + channel['title'] ,
                            'url': channel['url']
                        })     
                    # ... resto del codice TV originale ...
            
            if not streams['streams']:
                raise HTTPException(status_code=404)
            return respond_with(streams)
            
        elif "tt" in id or "tmdb" in id or "kitsu" in id:
            # TUTTO IL CODICE FILM/SERIE ORIGINALE
            print(f"Handling movie or series: {id}")
            # ... resto del codice originale ...
            
        if not streams['streams']:
            raise HTTPException(status_code=404)

    return respond_with(streams)

if __name__ == '__main__':
    import uvicorn
    print(f"🚀 Starting server on {HOST}:{PORT}")
    print(f"📋 Manifest URL: http://{HOST}:{PORT}/manifest.json")
    uvicorn.run("run:app", host=HOST, port=PORT, log_level="info")
