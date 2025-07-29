import requests
import logging
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)


class ExchangeRateService:
    """Service to fetch and manage USD to VES exchange rates from multiple sources."""
    
    # Cache keys
    CACHE_KEY_CURRENT_RATE = 'exchange_rate:current'
    CACHE_KEY_LAST_FETCH = 'exchange_rate:last_fetch'
    CACHE_TIMEOUT = 3600  # 1 hour
    
    # Rate change threshold for alerts (5%)
    ALERT_THRESHOLD = Decimal('5.0')
    
    # Fallback rate (used when all sources fail)
    FALLBACK_RATE = Decimal('38.0')  # Conservative fallback
    
    def __init__(self):
        self.sources = [
            self._fetch_from_exchangerate_host,  # Most reliable free API
            self._fetch_from_google_finance,
            self._fetch_from_open_exchange_rates,
        ]
    
    def get_current_rate(self, force_fetch: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get the current USD to VES exchange rate.
        
        Args:
            force_fetch: Force fetch from external sources instead of cache
            
        Returns:
            Dict with rate information or None if all sources fail
        """
        # Try cache first if not forcing fetch
        if not force_fetch:
            cached_rate = cache.get(self.CACHE_KEY_CURRENT_RATE)
            if cached_rate:
                logger.info("Returning cached exchange rate")
                return cached_rate
        
        # Try to get from database
        from payments.models import ExchangeRateLog
        current_rate = ExchangeRateLog.get_current_rate()
        
        # Check if database rate is fresh (less than 1 hour old)
        if current_rate and not force_fetch:
            age = timezone.now() - current_rate.timestamp
            if age < timedelta(hours=1):
                rate_data = {
                    'usd_to_ves': float(current_rate.usd_to_ves),
                    'last_updated': current_rate.timestamp.isoformat(),
                    'source': current_rate.source,
                    'change_percentage': float(current_rate.change_percentage) if current_rate.change_percentage else None
                }
                cache.set(self.CACHE_KEY_CURRENT_RATE, rate_data, self.CACHE_TIMEOUT)
                return rate_data
        
        # Fetch fresh rate
        return self.fetch_and_store_rate()
    
    def fetch_and_store_rate(self) -> Optional[Dict[str, Any]]:
        """
        Fetch rate from external sources and store in database.
        
        Returns:
            Dict with rate information or None if all sources fail
        """
        from payments.models import ExchangeRateLog, ExchangeRateAlert
        
        rate = None
        source = None
        error_messages = []
        
        # Try each source in order
        for fetch_func in self.sources:
            try:
                logger.info(f"Trying to fetch from {fetch_func.__name__}")
                result = fetch_func()
                if result and result.get('rate'):
                    rate = Decimal(str(result['rate']))
                    source = result['source']
                    logger.info(f"Successfully fetched rate {rate} from {source}")
                    break
                else:
                    logger.warning(f"No valid result from {fetch_func.__name__}")
            except Exception as e:
                error_msg = f"Error fetching from {fetch_func.__name__}: {str(e)}"
                error_messages.append(error_msg)
                logger.error(error_msg)
        
        # If all sources failed, use fallback
        if rate is None:
            rate = self.FALLBACK_RATE
            source = 'fallback'
            error_msg = "All sources failed, using fallback rate"
            error_messages.append(error_msg)
            logger.warning(error_msg)
        
        # Store rate in database
        try:
            exchange_rate_log = ExchangeRateLog.objects.create(
                usd_to_ves=rate,
                source=source,
                fetch_success=source != 'fallback',
                error_message='; '.join(error_messages) if error_messages else '',
                is_active=True
            )
            
            # Check for significant rate changes and create alerts
            self._check_rate_alerts(exchange_rate_log)
            
            # Prepare response data
            rate_data = {
                'usd_to_ves': float(rate),
                'last_updated': exchange_rate_log.timestamp.isoformat(),
                'source': source,
                'change_percentage': float(exchange_rate_log.change_percentage) if exchange_rate_log.change_percentage else None
            }
            
            # Cache the result
            cache.set(self.CACHE_KEY_CURRENT_RATE, rate_data, self.CACHE_TIMEOUT)
            cache.set(self.CACHE_KEY_LAST_FETCH, timezone.now().isoformat(), self.CACHE_TIMEOUT)
            
            logger.info(f"Stored exchange rate: {rate} VES per USD from {source}")
            return rate_data
            
        except Exception as e:
            logger.error(f"Error storing exchange rate: {str(e)}")
            return None
    
    def _fetch_from_exchangerate_host(self) -> Optional[Dict[str, Any]]:
        """
        Fetch USD to VES rate from Exchangerate.host (free API).
        
        Returns:
            Dict with rate and source or None if failed
        """
        try:
            # Try the latest rates endpoint first (no API key required)
            url = "https://api.exchangerate.host/latest"
            params = {
                'base': 'USD',
                'symbols': 'VES'
            }
            
            logger.info(f"Fetching from Exchangerate.host: {url}")
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Exchangerate.host response: {data}")
            
            if data.get('success') and 'rates' in data and 'VES' in data['rates']:
                rate = float(data['rates']['VES'])
                if rate > 0:
                    logger.info(f"Successfully got rate {rate} from Exchangerate.host")
                    return {
                        'rate': rate,
                        'source': 'exchangerate_host'
                    }
            
            # Fallback to convert endpoint
            url = "https://api.exchangerate.host/convert"
            params = {
                'from': 'USD',
                'to': 'VES',
                'amount': 1
            }
            
            logger.info(f"Trying convert endpoint: {url}")
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Convert endpoint response: {data}")
            
            if data.get('success') and data.get('result'):
                rate = float(data['result'])
                if rate > 0:
                    logger.info(f"Successfully got rate {rate} from Exchangerate.host convert")
                    return {
                        'rate': rate,
                        'source': 'exchangerate_host'
                    }
            
            raise ValueError(f"Invalid response from Exchangerate.host: {data}")
            
        except Exception as e:
            logger.error(f"Exchangerate.host fetch failed: {str(e)}")
            raise
    
    def _fetch_from_google_finance(self) -> Optional[Dict[str, Any]]:
        """
        Fetch USD to VES rate from Google Finance.
        
        Returns:
            Dict with rate and source or None if failed
        """
        try:
            url = "https://www.google.com/finance/quote/USD-VES"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            logger.info(f"Fetching from Google Finance: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for the price element (Google Finance uses various selectors)
            price_selectors = [
                '[data-last-price]',
                '.YMlKec.fxKbKc',
                '.kf1m0',
                '.YMlKec',
                '[data-last-price]',
                '.fxKbKc'
            ]
            
            rate = None
            for selector in price_selectors:
                price_element = soup.select_one(selector)
                if price_element:
                    price_text = price_element.get('data-last-price') or price_element.text.strip()
                    logger.info(f"Found price element with text: {price_text}")
                    # Clean and extract numeric value
                    rate_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                    if rate_match:
                        rate = float(rate_match.group())
                        logger.info(f"Extracted rate {rate} from Google Finance")
                        break
            
            if rate and rate > 0:
                return {
                    'rate': rate,
                    'source': 'google_finance'
                }
            else:
                raise ValueError("Could not extract valid rate from Google Finance")
                
        except Exception as e:
            logger.error(f"Google Finance fetch failed: {str(e)}")
            raise
    
    def _fetch_from_open_exchange_rates(self) -> Optional[Dict[str, Any]]:
        """
        Fetch USD to VES rate from Open Exchange Rates API.
        Note: Requires API key in settings.
        
        Returns:
            Dict with rate and source or None if failed
        """
        try:
            api_key = getattr(settings, 'OPEN_EXCHANGE_RATES_API_KEY', None)
            if not api_key:
                raise ValueError("Open Exchange Rates API key not configured")
            
            url = f"https://openexchangerates.org/api/latest.json"
            params = {
                'app_id': api_key,
                'symbols': 'VES'
            }
            
            logger.info(f"Fetching from Open Exchange Rates")
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if 'rates' in data and 'VES' in data['rates']:
                rate = float(data['rates']['VES'])
                if rate > 0:
                    logger.info(f"Successfully got rate {rate} from Open Exchange Rates")
                    return {
                        'rate': rate,
                        'source': 'open_exchange_rates'
                    }
            
            raise ValueError("VES rate not found in Open Exchange Rates response")
            
        except Exception as e:
            logger.error(f"Open Exchange Rates fetch failed: {str(e)}")
            raise
    
    def _check_rate_alerts(self, exchange_rate_log):
        """
        Check for significant rate changes and create alerts.
        
        Args:
            exchange_rate_log: The newly created ExchangeRateLog instance
        """
        from payments.models import ExchangeRateAlert
        
        try:
            # Check for high percentage changes
            if (exchange_rate_log.change_percentage and 
                abs(exchange_rate_log.change_percentage) >= self.ALERT_THRESHOLD):
                
                ExchangeRateAlert.objects.create(
                    alert_type='high_change',
                    exchange_rate=exchange_rate_log,
                    threshold_value=exchange_rate_log.change_percentage,
                    message=f"Exchange rate changed by {exchange_rate_log.change_percentage}% "
                           f"from previous rate. New rate: {exchange_rate_log.usd_to_ves} VES per USD."
                )
                logger.warning(f"High change alert: {exchange_rate_log.change_percentage}% change")
            
            # Check for fetch errors
            if not exchange_rate_log.fetch_success:
                ExchangeRateAlert.objects.create(
                    alert_type='fetch_error',
                    exchange_rate=exchange_rate_log,
                    message=f"Failed to fetch exchange rate from external sources. "
                           f"Using fallback rate: {exchange_rate_log.usd_to_ves} VES per USD. "
                           f"Error: {exchange_rate_log.error_message}"
                )
            
            # Check for source fallback
            if exchange_rate_log.source == 'fallback':
                ExchangeRateAlert.objects.create(
                    alert_type='source_fallback',
                    exchange_rate=exchange_rate_log,
                    message=f"All exchange rate sources failed. Using fallback rate: "
                           f"{exchange_rate_log.usd_to_ves} VES per USD."
                )
                
        except Exception as e:
            logger.error(f"Error creating exchange rate alerts: {str(e)}")
    
    def convert_usd_to_ves(self, usd_amount: Decimal, rate: Optional[Decimal] = None) -> Decimal:
        """
        Convert USD amount to VES using current or provided rate.
        
        Args:
            usd_amount: Amount in USD to convert
            rate: Optional specific rate to use (if None, uses current rate)
            
        Returns:
            Amount in VES
        """
        if rate is None:
            current_rate_data = self.get_current_rate()
            if current_rate_data:
                rate = Decimal(str(current_rate_data['usd_to_ves']))
            else:
                rate = self.FALLBACK_RATE
                logger.warning(f"Using fallback rate for conversion: {rate}")
        
        return usd_amount * rate
    
    def convert_ves_to_usd(self, ves_amount: Decimal, rate: Optional[Decimal] = None) -> Decimal:
        """
        Convert VES amount to USD using current or provided rate.
        
        Args:
            ves_amount: Amount in VES to convert
            rate: Optional specific rate to use (if None, uses current rate)
            
        Returns:
            Amount in USD
        """
        if rate is None:
            current_rate_data = self.get_current_rate()
            if current_rate_data:
                rate = Decimal(str(current_rate_data['usd_to_ves']))
            else:
                rate = self.FALLBACK_RATE
                logger.warning(f"Using fallback rate for conversion: {rate}")
        
        return ves_amount / rate
    
    def set_manual_rate(self, rate: Decimal, user=None) -> Dict[str, Any]:
        """
        Set a manual exchange rate override.
        
        Args:
            rate: The manual rate to set
            user: User who set the manual rate (optional)
            
        Returns:
            Dict with rate information
        """
        from payments.models import ExchangeRateLog, ExchangeRateAlert
        
        try:
            # Create manual rate entry
            exchange_rate_log = ExchangeRateLog.objects.create(
                usd_to_ves=rate,
                source='manual',
                fetch_success=True,
                is_active=True
            )
            
            # Create alert for manual override
            ExchangeRateAlert.objects.create(
                alert_type='manual_override',
                exchange_rate=exchange_rate_log,
                message=f"Exchange rate manually set to {rate} VES per USD"
                       f"{f' by {user.email}' if user else ''}."
            )
            
            # Clear cache to force refresh
            cache.delete(self.CACHE_KEY_CURRENT_RATE)
            
            rate_data = {
                'usd_to_ves': float(rate),
                'last_updated': exchange_rate_log.timestamp.isoformat(),
                'source': 'manual',
                'change_percentage': float(exchange_rate_log.change_percentage) if exchange_rate_log.change_percentage else None
            }
            
            cache.set(self.CACHE_KEY_CURRENT_RATE, rate_data, self.CACHE_TIMEOUT)
            
            logger.info(f"Manual exchange rate set: {rate} VES per USD")
            return rate_data
            
        except Exception as e:
            logger.error(f"Error setting manual rate: {str(e)}")
            raise


# Singleton instance
exchange_rate_service = ExchangeRateService() 