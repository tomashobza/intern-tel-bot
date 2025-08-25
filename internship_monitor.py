#!/usr/bin/env python3
"""
Internship Monitoring Bot
A comprehensive VPS-based bot for monitoring software engineering internships
from target companies and sending consolidated updates via Telegram.

Target Companies: Apple, Microsoft, Google, Meta, Nvidia, Spotify, Palantir, Rheinmetall
Geographic Scope: EU and UK only
Focus: Software Engineering/Programming internships exclusively
"""

import os
import logging
import requests
import time
import random
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import jobpilot
from jobpilot.scrapers import LinkedInScraper, ScraperInput

# Load environment variables
load_dotenv()

@dataclass
class InternshipListing:
    """Data structure for internship listings"""
    company: str
    title: str
    location: str
    url: str
    posted_date: Optional[str] = None

class InternshipMonitor:
    """Main class for monitoring internship opportunities"""
    
    def __init__(self):
        self.setup_logging()
        self.load_config()
        self.session = self.create_session()
        self.internships = []
        
        # User agents for rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0"
        ]
        
        # EU and UK location keywords for filtering - comprehensive coverage
        self.target_locations = [
            'london', 'dublin', 'berlin', 'munich', 'amsterdam', 'paris', 'madrid', 'barcelona',
            'milan', 'rome', 'stockholm', 'copenhagen', 'oslo', 'helsinki', 'zurich', 'vienna',
            'prague', 'budapest', 'warsaw', 'brussels', 'lisbon', 'athens', 'bucharest', 'sofia',
            'zagreb', 'bratislava', 'ljubljana', 'tallinn', 'riga', 'vilnius', 'luxembourg',
            'valletta', 'nicosia', 'uk', 'united kingdom', 'germany', 'france', 'italy', 'spain',
            'netherlands', 'sweden', 'denmark', 'norway', 'finland', 'switzerland', 'austria',
            'belgium', 'portugal', 'ireland', 'poland', 'czech republic', 'czechia', 'hungary',
            'greece', 'romania', 'bulgaria', 'croatia', 'slovakia', 'slovenia', 'estonia',
            'latvia', 'lithuania', 'luxembourg', 'malta', 'cyprus', 'europe', 'emea', 'eu',
            'european union'
        ]
        
        # Software engineering keywords - expanded and more inclusive
        self.swe_keywords = [
            'software', 'engineer', 'developer', 'programming', 'coding', 'backend', 'frontend',
            'fullstack', 'full-stack', 'mobile', 'web', 'python', 'java', 'javascript', 'react',
            'node.js', 'c++', 'c#', 'go', 'rust', 'kotlin', 'swift', 'android', 'ios',
            'machine learning', 'ai', 'data science', 'devops', 'cloud', 'infrastructure',
            'tech', 'technology', 'it', 'computer', 'digital', 'platform', 'api', 'database',
            'angular', 'vue', 'php', 'ruby', 'scala', 'typescript', 'html', 'css', 'sql',
            'mongodb', 'postgresql', 'mysql', 'redis', 'docker', 'kubernetes', 'aws', 'azure',
            'gcp', 'microservices', 'agile', 'scrum', 'git', 'github', 'gitlab', 'ci/cd',
            'selenium', 'testing', 'qa', 'quality assurance', 'automation', 'linux', 'unix'
        ]

    def setup_logging(self):
        """Configure logging for the application"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('internship_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def load_config(self):
        """Load and validate configuration from environment variables"""
        self.config = {
            'telegram_bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
            'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID'),
            'request_timeout': int(os.getenv('REQUEST_TIMEOUT', '30')),
            'rate_limit_delay': float(os.getenv('RATE_LIMIT_DELAY', '2.0')),
            'max_retries': int(os.getenv('MAX_RETRIES', '3'))
        }
        
        # Validate required configuration
        if not self.config['telegram_bot_token']:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not self.config['telegram_chat_id']:
            raise ValueError("TELEGRAM_CHAT_ID is required")
            
        self.logger.info("Configuration loaded successfully")

    def create_session(self):
        """Create HTTP session with proper headers and timeout"""
        session = requests.Session()
        session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        return session

    def get_random_user_agent(self):
        """Get a random user agent for request rotation"""
        return random.choice(self.user_agents)

    def make_request(self, url: str, retries: int = None, params: dict = None) -> Optional[requests.Response]:
        """Make HTTP request with error handling and retries"""
        if retries is None:
            retries = self.config['max_retries']
            
        self.session.headers.update({'User-Agent': self.get_random_user_agent()})
        
        for attempt in range(retries + 1):
            try:
                response = self.session.get(
                    url, 
                    params=params,
                    timeout=self.config['request_timeout'],
                    allow_redirects=True
                )
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request failed for {url} (attempt {attempt + 1}): {e}")
                if attempt < retries:
                    time.sleep(self.config['rate_limit_delay'] * (attempt + 1))
                    
        self.logger.error(f"Failed to fetch {url} after {retries + 1} attempts")
        return None

    def is_target_location(self, location: str) -> bool:
        """Check if location matches EU/UK criteria"""
        if not location:
            return False
            
        location_lower = location.lower()
        return any(keyword in location_lower for keyword in self.target_locations)

    def is_swe_role(self, title: str, description: str = "") -> bool:
        """Check if role is software engineering related"""
        if not title:
            return False
            
        text_to_check = f"{title} {description}".lower()
        return any(keyword in text_to_check for keyword in self.swe_keywords)

    def scrape_apple_careers(self) -> List[InternshipListing]:
        """Scrape Apple careers page for internships"""
        internships = []
        self.logger.info("Scraping Apple careers...")
        
        try:
            # Apple careers search URL with EU/UK locations and internship filter
            search_url = "https://jobs.apple.com/cs-cz/search"
            params = {
                'search': 'software engineer',
                'sort': 'relevance',
                'location': 'united-kingdom-GBR+czechia-CZE+germany-DEU+ireland-IRL+france-FRA+italy-ITA+spain-ESP+netherlands-NLD+sweden-SWE+denmark-DNK+norway-NOR+finland-FIN+belgium-BEL+austria-AUT+switzerland-CHE+poland-POL',
                'team': 'internships-STDNT-INTRN'
            }
            
            response = self.make_request(search_url, params=params)
            if not response:
                return internships
                
            soup = BeautifulSoup(response.text, 'html.parser')
            job_cards = soup.find_all('tr', {'data-job-id': True})
            
            for card in job_cards:
                title_elem = card.find('a', class_='table--advanced-search__title')
                location_elem = card.find('td', {'data-table-col-name': 'locations'})
                
                if title_elem and location_elem:
                    title = title_elem.get_text(strip=True)
                    location = location_elem.get_text(strip=True)
                    url = urljoin('https://jobs.apple.com', title_elem['href'])
                    
                    if self.is_swe_role(title):
                        internships.append(InternshipListing(
                            company="Apple",
                            title=title,
                            location=location,
                            url=url
                        ))
                    
        except Exception as e:
            self.logger.error(f"Error scraping Apple careers: {e}")
            
        self.logger.info(f"Found {len(internships)} Apple internships")
        return internships

    def scrape_microsoft_careers(self) -> List[InternshipListing]:
        """Scrape Microsoft careers page for internships"""
        internships = []
        self.logger.info("Scraping Microsoft careers...")
        
        try:
            # Microsoft careers API
            api_url = "https://careers.microsoft.com/professionals/us/en/search-results"
            params = {
                'keywords': 'intern',
                'location': 'Europe',
                'rt': 'university'
            }
            
            response = self.make_request(api_url, params=params)
            if not response:
                return internships
                
            soup = BeautifulSoup(response.text, 'html.parser')
            job_cards = soup.find_all('div', {'data-ph-at-id': 'job-result-item'})
            
            for card in job_cards:
                title_elem = card.find('a', {'data-ph-at-id': 'job-result-title'})
                location_elem = card.find('span', {'data-ph-at-id': 'job-result-location'})
                
                if title_elem and location_elem:
                    title = title_elem.get_text(strip=True)
                    location = location_elem.get_text(strip=True)
                    url = urljoin('https://careers.microsoft.com', title_elem['href'])
                    
                    if (self.is_target_location(location) and 
                        self.is_swe_role(title)):
                        
                        internships.append(InternshipListing(
                            company="Microsoft",
                            title=title,
                            location=location,
                            url=url
                        ))
                        
        except Exception as e:
            self.logger.error(f"Error scraping Microsoft careers: {e}")
            
        self.logger.info(f"Found {len(internships)} Microsoft internships")
        return internships

    def scrape_google_careers(self) -> List[InternshipListing]:
        """Scrape Google careers page for internships"""
        internships = []
        self.logger.info("Scraping Google careers...")
        
        try:
            # Google careers search URL with specific parameters
            search_url = "https://www.google.com/about/careers/applications/jobs/results/"
            params = {
                'company': ['Fitbit', 'Google', 'YouTube'],
                'distance': '50',
                'employment_type': 'INTERN',
                'location': ['United Kingdom', 'Ireland', 'Germany', 'France', 'Netherlands', 'Sweden', 'Denmark', 'Norway', 'Finland', 'Belgium', 'Austria', 'Switzerland', 'Poland', 'Spain', 'Italy', 'Czech Republic']
            }
            
            # Build URL with multiple location and company parameters
            url_params = []
            for company in params['company']:
                url_params.append(f"company={company}")
            for location in params['location']:
                url_params.append(f"location={location}")
            url_params.extend([
                f"distance={params['distance']}",
                f"employment_type={params['employment_type']}"
            ])
            
            full_url = f"{search_url}?{'&'.join(url_params)}"
            response = self.make_request(full_url)
            if not response:
                return internships
                
            soup = BeautifulSoup(response.text, 'html.parser')
            job_cards = soup.find_all('div', {'data-job-id': True})
            
            for card in job_cards:
                title_elem = card.find('h3') or card.find('a', {'data-gtm-event-name': 'job-click'})
                location_elem = card.find('span', class_='job-location')
                link_elem = card.find('a', href=True)
                
                if title_elem and location_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    location = location_elem.get_text(strip=True)
                    url = urljoin('https://www.google.com', link_elem['href'])
                    
                    if self.is_swe_role(title):
                        internships.append(InternshipListing(
                            company="Google",
                            title=title,
                            location=location,
                            url=url
                        ))
                    
        except Exception as e:
            self.logger.error(f"Error scraping Google careers: {e}")
            
        self.logger.info(f"Found {len(internships)} Google internships")
        return internships

    def scrape_meta_careers(self) -> List[InternshipListing]:
        """Scrape Meta careers page for internships"""
        internships = []
        self.logger.info("Scraping Meta careers...")
        
        try:
            # Meta careers URL with specific university teams and UK office
            search_url = "https://www.metacareers.com/jobs"
            params = {
                'teams[0]': 'University Grad - Business',
                'teams[1]': 'University Grad - Engineering, Tech & Design', 
                'teams[2]': 'University Grad - PhD & Postdoc',
                'offices[0]': 'London, UK'
            }
            
            response = self.make_request(search_url, params=params)
            if not response:
                return internships
                
            soup = BeautifulSoup(response.text, 'html.parser')
            job_cards = soup.find_all('div', {'data-testid': 'job-card'}) or soup.find_all('a', class_='job-card')
            
            for card in job_cards:
                title_elem = card.find('h3') or card.find('div', class_='job-title')
                location_elem = card.find('span', class_='location') or card.find('div', class_='job-location')
                link_elem = card if card.name == 'a' else card.find('a')
                
                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    location = location_elem.get_text(strip=True) if location_elem else 'London, UK'
                    
                    # Extract job ID from href
                    href = link_elem.get('href', '')
                    if '/jobs/' in href:
                        url = urljoin('https://www.metacareers.com', href)
                    else:
                        continue
                    
                    if ('intern' in title.lower() or 'university' in title.lower()) and self.is_swe_role(title):
                        internships.append(InternshipListing(
                            company="Meta",
                            title=title,
                            location=location,
                            url=url
                        ))
                        
        except Exception as e:
            self.logger.error(f"Error scraping Meta careers: {e}")
            
        self.logger.info(f"Found {len(internships)} Meta internships")
        return internships

    def scrape_nvidia_careers(self) -> List[InternshipListing]:
        """Scrape Nvidia careers page for internships"""
        internships = []
        self.logger.info("Scraping Nvidia careers...")
        
        try:
            # Nvidia careers search with job family group filter
            search_url = "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"
            params = {
                'jobFamilyGroup': '0c40f6bd1d8f10ae43ffbd1459047e84'  # From the provided URL
            }
            
            response = self.make_request(search_url, params=params)
            if not response:
                return internships
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for job listings in Workday format
            job_cards = (soup.find_all('li', {'data-automation-id': 'jobListItem'}) or
                        soup.find_all('div', class_='job-card') or
                        soup.find_all('a', {'data-automation-id': 'jobTitle'}))
            
            for card in job_cards:
                # Extract title
                title_elem = (card.find('a', {'data-automation-id': 'jobTitle'}) or
                             card.find('h3') or 
                             card.find('span', {'data-automation-id': 'jobTitle'}))
                
                # Extract location
                location_elem = (card.find('span', {'data-automation-id': 'jobLocation'}) or
                               card.find('div', class_='job-location'))
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    location = location_elem.get_text(strip=True) if location_elem else ''
                    
                    # Get job URL
                    if title_elem.name == 'a':
                        url = urljoin('https://nvidia.wd5.myworkdayjobs.com', title_elem.get('href', ''))
                    else:
                        link_elem = card.find('a')
                        url = urljoin('https://nvidia.wd5.myworkdayjobs.com', link_elem.get('href', '')) if link_elem else ''
                    
                    # Filter for internships in EU/UK
                    if (('intern' in title.lower() or 'student' in title.lower()) and 
                        self.is_swe_role(title) and
                        self.is_target_location(location) and
                        url):
                        
                        internships.append(InternshipListing(
                            company="Nvidia",
                            title=title,
                            location=location,
                            url=url
                        ))
                        
        except Exception as e:
            self.logger.error(f"Error scraping Nvidia careers: {e}")
            
        self.logger.info(f"Found {len(internships)} Nvidia internships")
        return internships

    def scrape_spotify_careers(self) -> List[InternshipListing]:
        """Scrape Spotify careers page for internships"""
        internships = []
        self.logger.info("Scraping Spotify careers...")
        
        try:
            # Spotify students page
            careers_url = "https://www.lifeatspotify.com/students"
            response = self.make_request(careers_url)
            if not response:
                return internships
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for job cards or listing containers
            job_cards = (soup.find_all('div', class_='job-card') or 
                        soup.find_all('a', class_='job-link') or
                        soup.find_all('div', {'data-testid': 'job-listing'}) or
                        soup.find_all('li', class_='job-item'))
            
            # If no specific job cards, look for any links with job-related patterns
            if not job_cards:
                job_cards = soup.find_all('a', href=True)
                job_cards = [card for card in job_cards if 
                           ('job' in card.get('href', '').lower() or 
                            'career' in card.get('href', '').lower() or
                            'intern' in card.get_text().lower())]
            
            for card in job_cards:
                # Extract title from various possible elements
                title_elem = (card.find('h3') or card.find('h2') or card.find('h4') or 
                             card.find('span', class_='title') or card.find('div', class_='title'))
                
                if not title_elem and card.name == 'a':
                    title_elem = card
                
                # Extract location
                location_elem = (card.find('span', class_='location') or 
                               card.find('div', class_='location') or
                               card.find('p', class_='location'))
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    location = location_elem.get_text(strip=True) if location_elem else ''
                    
                    # Get URL
                    if card.name == 'a':
                        url = urljoin('https://www.lifeatspotify.com', card.get('href', ''))
                    else:
                        link_elem = card.find('a')
                        url = urljoin('https://www.lifeatspotify.com', link_elem.get('href', '')) if link_elem else ''
                    
                    # Check if it's an internship and SWE role
                    if (('intern' in title.lower() or 'student' in title.lower()) and 
                        self.is_swe_role(title) and
                        url):
                        
                        # Default to Stockholm if no location specified
                        if not location:
                            location = 'Stockholm, Sweden'
                            
                        internships.append(InternshipListing(
                            company="Spotify",
                            title=title,
                            location=location,
                            url=url
                        ))
                    
        except Exception as e:
            self.logger.error(f"Error scraping Spotify careers: {e}")
            
        self.logger.info(f"Found {len(internships)} Spotify internships")
        return internships

    def scrape_palantir_careers(self) -> List[InternshipListing]:
        """Scrape Palantir careers page for internships"""
        internships = []
        self.logger.info("Scraping Palantir careers...")
        
        try:
            # Palantir careers API
            api_url = "https://jobs.lever.co/palantir"
            response = self.make_request(api_url)
            if not response:
                return internships
                
            soup = BeautifulSoup(response.text, 'html.parser')
            job_postings = soup.find_all('div', class_='posting')
            
            for posting in job_postings:
                title_elem = posting.find('h5')
                location_elem = posting.find('span', class_='sort-by-location')
                link_elem = posting.find('a')
                
                if title_elem and location_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    location = location_elem.get_text(strip=True)
                    url = link_elem['href']
                    
                    if ('intern' in title.lower() and 
                        self.is_target_location(location) and 
                        self.is_swe_role(title)):
                        
                        internships.append(InternshipListing(
                            company="Palantir",
                            title=title,
                            location=location,
                            url=url
                        ))
                        
        except Exception as e:
            self.logger.error(f"Error scraping Palantir careers: {e}")
            
        self.logger.info(f"Found {len(internships)} Palantir internships")
        return internships


    async def _search_linkedin_async(self) -> List[InternshipListing]:
        """Async method to search LinkedIn using jobpilot library"""
        internships = []
        
        try:
            # Enable jobpilot logging
            jobpilot.enable_logging()
            
            # Initialize LinkedIn scraper
            scraper = LinkedInScraper()
            
            # EU/UK locations to search - comprehensive coverage
            locations = [
                "United Kingdom", "Ireland", "Germany", "France", "Netherlands", 
                "Sweden", "Denmark", "Norway", "Finland", "Switzerland",
                "Austria", "Belgium", "Italy", "Spain", "Poland", "Czech Republic",
                "Hungary", "Portugal", "Greece", "Romania", "Bulgaria", "Croatia",
                "Slovakia", "Slovenia", "Estonia", "Latvia", "Lithuania", "Luxembourg",
                "Malta", "Cyprus"
            ]
            
            # Broader search keywords to catch various internship naming patterns
            keywords = [
                "software intern",
                "developer intern", 
                "engineering intern",
                "tech intern",
                "programming intern",
                "backend intern",
                "frontend intern",
                "fullstack intern",
                "python intern",
                "java intern",
                "javascript intern",
                "react intern",
                "node intern"
            ]
            
            # Search for internships across different locations and keywords
            # Limit searches to avoid rate limits: 8 locations × 4 keywords = 32 searches
            for location in locations[:8]:  # First 8 EU countries for broad coverage
                for keyword in keywords[:4]:  # Top 4 most effective keywords
                    try:
                        self.logger.info(f"Searching LinkedIn: {keyword} in {location}")
                        
                        # Create scraper input
                        scraper_input = ScraperInput(
                            location=location,
                            keywords=keyword,
                            limit=15
                        )
                        
                        # Search jobs using jobpilot
                        jobs = await scraper.scrape(scraper_input, job_details=False)
                        
                        for job in jobs:
                            company = job.company if hasattr(job, 'company') else ''
                            title = job.title if hasattr(job, 'title') else ''
                            job_location = job.location if hasattr(job, 'location') else location
                            url = job.url if hasattr(job, 'url') else ''
                            
                            # Filter out target companies (already scraped directly)
                            excluded_companies = ['Apple', 'Microsoft', 'Google', 'Meta', 'Nvidia', 'Spotify', 'Palantir']
                            
                            # More flexible internship detection
                            internship_keywords = [
                                'intern', 'internship', 'trainee', 'graduate', 
                                'entry level', 'junior', 'student', 'placement',
                                'apprentice', 'stage', 'praktikum', 'stagiaire'  # EU language variants
                            ]
                            
                            is_internship = any(keyword in title.lower() for keyword in internship_keywords)
                            
                            if (company not in excluded_companies and 
                                self.is_swe_role(title) and 
                                is_internship and
                                url):
                                
                                internships.append(InternshipListing(
                                    company=company,
                                    title=title,
                                    location=job_location,
                                    url=url
                                ))
                        
                        # Rate limiting between searches
                        await asyncio.sleep(self.config['rate_limit_delay'])
                        
                    except Exception as e:
                        self.logger.warning(f"Error searching LinkedIn for '{keyword}' in '{location}': {e}")
                        continue
                        
        except Exception as e:
            self.logger.error(f"Error in LinkedIn async search: {e}")
            
        return internships

    def search_linkedin_jobs(self) -> List[InternshipListing]:
        """Search LinkedIn using jobpilot library for additional SWE internships"""
        self.logger.info("Searching LinkedIn for internships using jobpilot...")
        
        try:
            # Run the async LinkedIn search
            internships = asyncio.run(self._search_linkedin_async())
            
            # Remove duplicates based on URL
            seen_urls = set()
            unique_internships = []
            for internship in internships:
                if internship.url not in seen_urls:
                    seen_urls.add(internship.url)
                    unique_internships.append(internship)
                    
            self.logger.info(f"Found {len(unique_internships)} unique LinkedIn internships")
            return unique_internships
            
        except Exception as e:
            self.logger.error(f"Error searching LinkedIn jobs: {e}")
            return []

    def collect_all_internships(self) -> List[InternshipListing]:
        """Collect internships from all sources"""
        all_internships = []
        
        # Define scraping functions for target companies
        scrapers = [
            self.scrape_apple_careers,
            self.scrape_microsoft_careers,
            self.scrape_google_careers,
            self.scrape_meta_careers,
            self.scrape_nvidia_careers,
            self.scrape_spotify_careers,
            self.scrape_palantir_careers
        ]
        
        # Scrape each company with rate limiting
        for scraper in scrapers:
            try:
                internships = scraper()
                all_internships.extend(internships)
                time.sleep(self.config['rate_limit_delay'])
            except Exception as e:
                self.logger.error(f"Error in scraper {scraper.__name__}: {e}")
                
        # Add LinkedIn results as fallback
        linkedin_internships = self.search_linkedin_jobs()
        all_internships.extend(linkedin_internships)
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_internships = []
        for internship in all_internships:
            if internship.url not in seen_urls:
                seen_urls.add(internship.url)
                unique_internships.append(internship)
                
        self.logger.info(f"Total unique internships found: {len(unique_internships)}")
        return unique_internships

    def format_telegram_message(self, internships: List[InternshipListing]) -> str:
        """Format internships into a Telegram message"""
        if not internships:
            return f"🤖 Internship Monitor Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nNo new internships found in this run."
            
        # Group internships by company
        by_company = {}
        for internship in internships:
            if internship.company not in by_company:
                by_company[internship.company] = []
            by_company[internship.company].append(internship)
            
        # Format message
        message_parts = [
            f"🚀 Internship Monitor Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Found {len(internships)} SWE internships in EU/UK:\n"
        ]
        
        for company, company_internships in sorted(by_company.items()):
            message_parts.append(f"**{company}** ({len(company_internships)} positions):")
            for internship in company_internships:
                location_text = f" - {internship.location}" if internship.location else ""
                message_parts.append(f"  • {internship.title}{location_text} - [Apply]({internship.url})")
            message_parts.append("")
            
        return "\n".join(message_parts)

    def send_telegram_message(self, message: str) -> bool:
        """Send message via Telegram bot"""
        try:
            telegram_url = f"https://api.telegram.org/bot{self.config['telegram_bot_token']}/sendMessage"
            
            payload = {
                'chat_id': self.config['telegram_chat_id'],
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            
            response = self.session.post(telegram_url, json=payload, timeout=self.config['request_timeout'])
            response.raise_for_status()
            
            self.logger.info("Telegram message sent successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send Telegram message: {e}")
            return False

    def run(self):
        """Main execution flow"""
        self.logger.info("Starting internship monitoring run...")
        
        try:
            # Collect all internships
            internships = self.collect_all_internships()
            
            # Format and send message
            message = self.format_telegram_message(internships)
            success = self.send_telegram_message(message)
            
            if success:
                self.logger.info(f"Monitoring run completed successfully. Found {len(internships)} internships.")
            else:
                self.logger.error("Failed to send Telegram notification")
                
        except Exception as e:
            self.logger.error(f"Error in main execution: {e}")
            
            # Send error notification
            error_message = f"🚨 Internship Monitor Error - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nError: {str(e)}"
            self.send_telegram_message(error_message)

def main():
    """Entry point for the script"""
    try:
        monitor = InternshipMonitor()
        monitor.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1
    return 0

if __name__ == "__main__":
    exit(main())