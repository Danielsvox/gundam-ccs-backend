from django.core.management.base import BaseCommand
from django.utils import timezone
from payments.services.exchange_rate_service import exchange_rate_service
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fetch and store current USD to VES exchange rate'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force fetch even if recent rate exists',
        )
        parser.add_argument(
            '--source',
            type=str,
            help='Specific source to fetch from (google_finance, exchangerate_host, open_exchange_rates)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output',
        )

    def handle(self, *args, **options):
        """Handle the command execution."""
        self.stdout.write("=" * 60)
        self.stdout.write("GUNDAM CCS - Exchange Rate Fetcher")
        self.stdout.write("=" * 60)
        
        try:
            # Check if we should force fetch
            force_fetch = options.get('force', False)
            verbose = options.get('verbose', False)
            
            if verbose:
                self.stdout.write(f"Timestamp: {timezone.now().isoformat()}")
                self.stdout.write(f"Force fetch: {force_fetch}")
            
            # Fetch current rate
            self.stdout.write("Fetching current exchange rate...")
            
            rate_data = exchange_rate_service.get_current_rate(force_fetch=force_fetch)
            
            if rate_data:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Exchange rate fetched successfully!"
                    )
                )
                self.stdout.write(f"  Rate: {rate_data['usd_to_ves']} VES per USD")
                self.stdout.write(f"  Source: {rate_data['source']}")
                self.stdout.write(f"  Last updated: {rate_data['last_updated']}")
                
                if rate_data.get('change_percentage') is not None:
                    change = rate_data['change_percentage']
                    change_indicator = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                    self.stdout.write(f"  Change: {change_indicator} {change}%")
                
                # Show alerts if any
                self._show_recent_alerts(verbose)
                
            else:
                self.stdout.write(
                    self.style.ERROR(
                        "✗ Failed to fetch exchange rate"
                    )
                )
                return
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error: {str(e)}")
            )
            logger.error(f"Exchange rate fetch command failed: {str(e)}")
            return
        
        self.stdout.write("=" * 60)
        self.stdout.write("Exchange rate fetch completed")
        self.stdout.write("=" * 60)
    
    def _show_recent_alerts(self, verbose=False):
        """Show recent exchange rate alerts."""
        try:
            from payments.models import ExchangeRateAlert
            from datetime import timedelta
            
            # Get alerts from last 24 hours
            since = timezone.now() - timedelta(hours=24)
            recent_alerts = ExchangeRateAlert.objects.filter(
                created_at__gte=since
            ).order_by('-created_at')[:5]
            
            if recent_alerts.exists():
                self.stdout.write("\n📢 Recent Alerts (Last 24h):")
                self.stdout.write("-" * 40)
                
                for alert in recent_alerts:
                    alert_icon = {
                        'high_change': '⚠️',
                        'fetch_error': '❌',
                        'manual_override': '👤',
                        'source_fallback': '🔄'
                    }.get(alert.alert_type, '🔔')
                    
                    status = "✅ Acknowledged" if alert.acknowledged else "🔔 Pending"
                    
                    self.stdout.write(
                        f"  {alert_icon} {alert.get_alert_type_display()} - {status}"
                    )
                    
                    if verbose:
                        self.stdout.write(f"     {alert.message}")
                        self.stdout.write(f"     Time: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                self.stdout.write("")
            
        except Exception as e:
            if verbose:
                self.stdout.write(f"Note: Could not fetch recent alerts: {str(e)}")
    
    def _show_rate_history(self, days=7):
        """Show recent rate history."""
        try:
            from payments.models import ExchangeRateLog
            from datetime import timedelta
            
            since = timezone.now() - timedelta(days=days)
            recent_rates = ExchangeRateLog.objects.filter(
                timestamp__gte=since,
                fetch_success=True
            ).order_by('-timestamp')[:10]
            
            if recent_rates.exists():
                self.stdout.write(f"\n📊 Rate History (Last {days} days):")
                self.stdout.write("-" * 50)
                
                for rate in recent_rates:
                    change_str = ""
                    if rate.change_percentage is not None:
                        change_str = f" ({rate.change_percentage:+.2f}%)"
                    
                    self.stdout.write(
                        f"  {rate.timestamp.strftime('%m/%d %H:%M')} - "
                        f"{rate.usd_to_ves} VES{change_str} "
                        f"({rate.source})"
                    )
                self.stdout.write("")
                
        except Exception as e:
            self.stdout.write(f"Note: Could not fetch rate history: {str(e)}") 