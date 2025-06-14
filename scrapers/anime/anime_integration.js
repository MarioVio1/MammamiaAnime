const AnimeSaturnScraper = require('./animesaturn_scraper');
const AnimeUnityScraper = require('./animeunity_scraper');
const GogoAnimeScraper = require('./gogoanime_scraper');

class AnimeManager {
  constructor() {
    this.scrapers = {};
    this.config = null;
    this.isInitialized = false;
  }

  async initialize() {
    try {
      const configPath = path.join(__dirname, 'anime_sites_config.json');
      this.config = JSON.parse(fs.readFileSync(configPath, 'utf8'));

      this.scrapers.animesaturn = new AnimeSaturnScraper(this.config);
      this.scrapers.animeunity = new AnimeUnityScraper(this.config);
      this.scrapers.gogoanime = new GogoAnimeScraper(this.config);

      this.isInitialized = true;
      console.log('[AnimeManager] Initialized with scrapers:', Object.keys(this.scrapers));
    } catch (error) {
      console.error('[AnimeManager] Initialization error:', error.message);
      throw error;
    }
  }

  async searchAnime(query, sites = null) {
    if (!this.isInitialized) {
      await this.initialize();
    }

    const sitesToSearch = sites || Object.keys(this.scrapers);
    const searchPromises = sitesToSearch.map(async (site) => {
      try {
        if (this.scrapers[site]) {
          const results = await this.scrapers[site].search(query);
          return results.map(result => ({ ...result, source: site }));
        }
        return [];
      } catch (error) {
        console.error(`[AnimeManager] Search error on ${site}:`, error.message);
        return [];
      }
    });

    const allResults = await Promise.all(searchPromises);
    const aggregatedResults = allResults.flat();
    const uniqueResults = this.deduplicateResults(aggregatedResults);
    
    return uniqueResults;
  }

  // ... (altri metodi per gestione stream e cataloghi)
}

module.exports = { animeManager: new AnimeManager(), AnimeManager };
