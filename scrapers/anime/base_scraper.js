/**
 * Base Scraper class that provides common functionality for all anime scrapers
 */
class BaseScraper {
  constructor(config) {
    this.config = config;
    this.name = '';
    this.baseUrl = '';
    this.headers = {};
    this.selectors = {};
    this.cache = new Map();
    this.cacheTimeout = 3600000; // 1 hour cache
  }

  /**
   * Helper method to make HTTP requests with proper error handling and retries
   */
  async makeRequest(url, options = {}, retries = 3) {
    // Check cache first
    const cacheKey = url + JSON.stringify(options);
    const cachedData = this.getCachedData(cacheKey);
    if (cachedData) {
      return cachedData;
    }

    const fetchOptions = {
      method: 'GET',
      headers: { ...this.headers, ...(options.headers || {}) },
      ...options
    };

    try {
      console.log(`[${this.name}] Fetching: ${url}`);
      const response = await fetch(url, fetchOptions);
      
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      
      let data;
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }
      
      this.cacheData(cacheKey, data);
      return data;
    } catch (error) {
      console.error(`[${this.name}] Request failed: ${url}`, error.message);
      
      if (retries > 0) {
        const backoffDelay = Math.pow(2, 4 - retries) * 1000;
        await new Promise(resolve => setTimeout(resolve, backoffDelay));
        return this.makeRequest(url, options, retries - 1);
      }
      
      throw error;
    }
  }

  // ... (altri metodi comuni)
}

module.exports = BaseScraper;
