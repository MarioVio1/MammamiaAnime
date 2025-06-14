const BaseScraper = require('./base_scraper');
const cheerio = require('cheerio');

class GogoAnimeScraper extends BaseScraper {
  constructor(config) {
    super(config);
    this.init('GogoAnime', config.gogoanime);
  }

  async search(query) {
    try {
      const encodedQuery = encodeURIComponent(query);
      const searchUrl = `${this.baseUrl}/search.html?keyword=${encodedQuery}`;
      
      const html = await this.makeRequest(searchUrl);
      const $ = cheerio.load(html);
      const results = [];

      $(this.selectors.search_results).each((index, element) => {
        const $el = $(element);
        const $link = $el.find(this.selectors.anime_title);
        const title = $link.text().trim();
        const link = $link.attr('href');
        const image = $el.find('img').attr('src');
        
        if (title && link) {
          results.push({
            id: this.extractIdFromUrl(link),
            title: title,
            url: link.startsWith('http') ? link : this.baseUrl + link,
            image: image ? (image.startsWith('http') ? image : this.baseUrl + image) : null,
            site: 'gogoanime'
          });
        }
      });

      return results;
    } catch (error) {
      console.error(`[${this.name}] Search error:`, error.message);
      return [];
    }
  }

  // ... (gestione episodi con AJAX)
}

module.exports = GogoAnimeScraper;
