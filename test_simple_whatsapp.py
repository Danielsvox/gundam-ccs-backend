#!/usr/bin/env python3
"""
Simple WhatsApp configuration test
"""

import os
from twilio.rest import Client
from twilio.base.exceptions import TwilioException


def test_twilio_configuration():
    """Test basic Twilio configuration."""
    print("🔧 Testing Twilio Configuration...")

    # Get configuration from environment
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_number = os.getenv('TWILIO_WHATSAPP_FROM', '+14155238886')
    to_number = os.getenv('STORE_OWNER_WHATSAPP', '+584242263633')

    print(f"Account SID: {'✅ Set' if account_sid else '❌ Missing'}")
    print(f"Auth Token: {'✅ Set' if auth_token else '❌ Missing'}")
    print(f"From Number: {from_number}")
    print(f"To Number: {to_number}")

    if not account_sid or not auth_token:
        print("\n❌ Missing Twilio credentials!")
        print("Please set the following environment variables:")
        print("export TWILIO_ACCOUNT_SID='your_account_sid'")
        print("export TWILIO_AUTH_TOKEN='your_auth_token'")
        return False

    try:
        # Test Twilio client
        client = Client(account_sid, auth_token)

        # Try to send a test message
        message = client.messages.create(
            from_=f"whatsapp:{from_number}",
            body="🧪 Test message from Gundam CCS - WhatsApp notification system is working!",
            to=f"whatsapp:{to_number}"
        )

        print(f"\n✅ Test message sent successfully!")
        print(f"Message SID: {message.sid}")
        print(f"Status: {message.status}")

        return True

    except TwilioException as e:
        print(f"\n❌ Twilio error: {str(e)}")
        print("\nPossible issues:")
        print("1. Invalid Account SID or Auth Token")
        print("2. WhatsApp number not verified with Twilio")
        print("3. Need to join Twilio WhatsApp sandbox")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return False


def main():
    """Main test function."""
    print("🧪 Simple WhatsApp Configuration Test")
    print("=" * 50)

    success = test_twilio_configuration()

    print("\n" + "=" * 50)
    if success:
        print("✅ Configuration test passed!")
        print("📱 Check your WhatsApp for the test message")
    else:
        print("❌ Configuration test failed!")
        print("Please check your Twilio setup")


if __name__ == "__main__":
    main()
