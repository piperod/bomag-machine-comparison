#!/usr/bin/env python3
"""
download_logos.py
----------------

Download manufacturer logos from various sources.
"""

import os
import requests
from pathlib import Path
import cairosvg
import io

# Define headers for the requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Define logo URLs for each manufacturer
LOGO_URLS = {
    'bomag': 'https://www.bomag.com/ww-en/wp-content/themes/bomag/assets/images/logo.svg',
    'caterpillar': 'https://logos-world.net/wp-content/uploads/2020/08/Caterpillar-Logo-700x394.png',
    'hamm': 'https://logos-world.net/wp-content/uploads/2023/03/Hamm-Logo-500x281.png',
    'dynapac': 'https://www.dynapac.com/wp-content/uploads/2019/03/dynapac-logo.png',
    'ammann': 'https://www.ammann.com/wp-content/uploads/2019/03/ammann-logo.png',
    'jcb': 'https://www.jcb.com/~/media/jcb/global/logos/jcb-logo.svg',
    'wacker_neuson': 'https://www.wackerneuson.com/~/media/wackerneuson/logos/wacker-neuson-logo.svg'
}

def download_logo(name: str, url: str, output_dir: Path) -> None:
    """Download a logo from the given URL and save it to the output directory."""
    try:
        print(f"Downloading {name} logo from {url}")
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        
        output_path = output_dir / f"{name}.png"
        
        # If the URL ends with .svg, convert to PNG
        if url.lower().endswith('.svg'):
            png_data = cairosvg.svg2png(bytestring=response.content)
            with open(output_path, 'wb') as f:
                f.write(png_data)
        else:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
        print(f"Saved {name} logo to {output_path}")
    except Exception as e:
        print(f"Error downloading {name} logo: {e}")

def main():
    """Main entry point."""
    # Create logos directory if it doesn't exist
    output_dir = Path('assets/logos')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Download each logo
    for name, url in LOGO_URLS.items():
        download_logo(name, url, output_dir)

if __name__ == "__main__":
    main() 