#!/usr/bin/env python3
"""
Initialize App Settings
Run this script once after deploying to initialize default settings
"""
import sys
import os

# Add the current directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env if running locally
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from utils import AppSettingsDB

def main():
    """Initialize app settings with default values"""
    print("=" * 60)
    print("Initializing App Settings")
    print("=" * 60)

    try:
        # Initialize settings
        AppSettingsDB.initialize_settings()

        print("\n✓ App settings initialized successfully!")

        # Display current settings
        print("\nCurrent settings:")
        print("-" * 60)

        settings = AppSettingsDB.get_all_settings()

        # Filter out internal settings
        public_settings = {
            k: v for k, v in settings.items()
            if not k.startswith('_')
        }

        for key, value in sorted(public_settings.items()):
            print(f"  {key}: {value}")

        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error initializing settings: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
