#!/usr/bin/env python3
"""
Script to identify Jupyter notebooks with outdated links in the google-gemini/cookbook repo.
This tool scans for GitHub links that need to be updated to relative paths,
while ignoring exceptions (gemini-1.5-archive, folder links, external links).
"""

import json
import re
import glob
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def scan_notebook_for_links(filepath: str) -> list:
    """Scan a notebook for GitHub links that need updating."""
    found_links = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            notebook = json.load(f)
        
        for cell_idx, cell in enumerate(notebook.get('cells', [])):
            if cell.get('cell_type') != 'markdown':
                continue
            
            for line_idx, line in enumerate(cell.get('source', [])):
                # Match GitHub links with expanded patterns
                github_pattern = r'https://github\.com/google-gemini/cookbook/blob/([0-9a-f]{7,40}|main|master|old)/([^\s\)\"]*)'
                
                # Skip special cases
                if 'gemini-1.5-archive' in line or '/tree/' in line or ('https://' in line and 'google-gemini/cookbook' not in line):
                    continue
                
                matches = re.findall(github_pattern, line)
                if matches:
                    found_links.append({
                        'cell': cell_idx,
                        'line': line_idx,
                        'content': line.strip(),
                        'matches': matches
                    })
        
        return found_links
    except Exception as e:
        logger.error(f"Failed to scan {filepath}: {e}")
        return []

def main():
    """Scan all notebooks in the repository for outdated links."""
    notebooks = glob.glob("**/*.ipynb", recursive=True)
    logger.info(f"Found {len(notebooks)} notebooks to process.")
    
    files_with_links = {}
    total_links = 0
    
    for filepath in notebooks:
        links = scan_notebook_for_links(filepath)
        if links:
            files_with_links[filepath] = links
            total_links += len(links)
    
    logger.info(f"Found {total_links} links that need updating in {len(files_with_links)} files:")
    
    # Output all files with links
    for filepath, links in files_with_links.items():
        logger.info(f"\n{filepath}: {len(links)} links")
        for idx, link_info in enumerate(links, 1):
            if idx <= 3:  # Show up to 3 examples per file
                logger.info(f"  Example {idx}: {link_info['content']}")
            elif idx == 4:
                logger.info(f"  ... and {len(links) - 3} more")
                break
    
    # Create a summary file
    with open('links_to_update.txt', 'w', encoding='utf-8') as f:
        f.write(f"Found {total_links} links that need updating in {len(files_with_links)} files:\n\n")
        for filepath in sorted(files_with_links.keys()):
            f.write(f"{filepath}: {len(files_with_links[filepath])} links\n")
    
    logger.info(f"\nSummary written to links_to_update.txt")

if __name__ == "__main__":
    main()
