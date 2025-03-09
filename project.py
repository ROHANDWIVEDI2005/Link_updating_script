#!/usr/bin/env python3
"""
Script to update outdated links in Jupyter notebooks in the google-gemini/cookbook repo.
Fixes issue #492 by converting commit-specific and old branch links to relative links,
preserving absolute links for gemini-1.5-archive, folders, and external sites.
Note: This aligns with @markmcd's suggestion to use relative links where possible,
with exceptions for gemini-1.5-archive, folders, and external links as requested.
"""

import os
import json
import re
import glob
import logging
from pprint import pformat

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Base directory for relative links (relative to notebook location)
BASE_DIR = "."  # Can be adjusted based on notebook depth

def convert_to_relative_path(full_path, notebook_path):
    """Convert a GitHub absolute path to a relative path based on notebook location."""
    # Extract the path after /blob/<branch or commit>/ 
    repo_path = re.sub(r'.*?/blob/[^/]+/', '', full_path)
    
    # Get the directory of the notebook
    notebook_dir = os.path.dirname(notebook_path)
    
    # Calculate the relative path
    if notebook_dir:
        # Determine how many directory levels to go up
        levels_up = len(notebook_dir.split('/'))
        prefix = '../' * levels_up if levels_up > 0 else './'
        return f"{prefix}{repo_path}"
    else:
        # If notebook is at the root
        return f"./{repo_path}"

def update_links_in_notebook(filepath: str, dry_run: bool = False) -> bool:
    """Update links in a Jupyter notebook based on the new strategy."""
    modified = False
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            notebook = json.load(f)
        
        for cell_index, cell in enumerate(notebook.get('cells', [])):
            if cell.get('cell_type') != 'markdown':
                continue
            
            source_lines = cell.get('source', [])
            updated_lines = []
            
            for line_index, line in enumerate(source_lines):
                original_line = line
                
                # More comprehensive patterns to match GitHub links
                github_link_pattern = r'(https://github\.com/google-gemini/cookbook/blob/([0-9a-f]{7,40}|main|master|old)/([^\s\)\]]*))' 
                folder_link_pattern = r'(https://github\.com/google-gemini/cookbook/tree/[^/\s]+/[^\s\)\]]*)'
                
                # Check for special cases to preserve
                if 'gemini-1.5-archive' in line:
                    updated_lines.append(line)
                    continue
                
                # Check for folder links to preserve
                if re.search(folder_link_pattern, line):
                    updated_lines.append(line)
                    continue
                
                # Check for external links (not google-gemini/cookbook)
                if 'https://' in line and 'google-gemini/cookbook' not in line:
                    updated_lines.append(line)
                    continue
                
                # Process links that need conversion
                def replace_github_link(match):
                    full_url = match.group(1)
                    branch_or_commit = match.group(2)
                    path = match.group(3)
                    
                    # Calculate relative path from notebook to the target file
                    rel_path = convert_to_relative_path(full_url, filepath)
                    
                    # For Markdown links, preserve the link format
                    if "[" in line and "](" in line:
                        # Check if this is part of a markdown link
                        link_text_match = re.search(r'\[(.*?)\]\(' + re.escape(full_url) + r'\)', line)
                        if link_text_match:
                            link_text = link_text_match.group(1)
                            return f"[{link_text}]({rel_path})"
                    
                    # For plain URLs, just return the relative path
                    return rel_path
                
                # Apply the link conversion
                new_line = re.sub(github_link_pattern, replace_github_link, line)
                
                if new_line != original_line:
                    modified = True
                    logger.info(f"Updated link in {filepath} (cell {cell_index}, line {line_index}):")
                    logger.info(f"  OLD: {original_line.strip()}")
                    logger.info(f"  NEW: {new_line.strip()}")
                
                updated_lines.append(new_line)
            
            cell['source'] = updated_lines
        
        if modified and not dry_run:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(notebook, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved updated notebook: {filepath}")
        
        return modified
    except Exception as e:
        logger.error(f"Failed to process {filepath}: {e}")
        logger.error(f"Exception details: {str(e)}")
        return False

def scan_for_github_links(filepath: str) -> list:
    """Scan notebook for GitHub links without modifying."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            notebook = json.load(f)
        
        github_links = []
        
        for cell_index, cell in enumerate(notebook.get('cells', [])):
            if cell.get('cell_type') != 'markdown':
                continue
            
            source_lines = cell.get('source', [])
            
            for line_index, line in enumerate(source_lines):
                github_pattern = r'https://github\.com/google-gemini/cookbook/blob/[^/\s]+/[^\s\)\]]+'
                matches = re.findall(github_pattern, line)
                if matches:
                    github_links.append({
                        'cell': cell_index,
                        'line': line_index,
                        'content': line.strip(),
                        'links': matches
                    })
        
        return github_links
    except Exception as e:
        logger.error(f"Failed to scan {filepath}: {e}")
        return []

def main():
    """Process all notebooks in the repository."""
    notebooks = glob.glob("**/*.ipynb", recursive=True)
    if not notebooks:
        logger.warning("No .ipynb files found. Check the directory.")
        return
    
    logger.info(f"Found {len(notebooks)} notebooks to process.")
    
    # First, scan all notebooks for GitHub links to verify we're finding them
    all_links = {}
    for filepath in notebooks:
        links = scan_for_github_links(filepath)
        if links:
            all_links[filepath] = links
    
    if not all_links:
        logger.warning("No GitHub links found in any notebooks. Double-check patterns.")
        return
    
    logger.info(f"Found GitHub links in {len(all_links)} notebooks.")
    logger.info(f"Sample of links found:")
    sample_count = 0
    for filepath, links in all_links.items():
        if sample_count >= 5:
            break
        logger.info(f"  In {filepath}:")
        for link_info in links[:2]:  # Show at most 2 links per file
            logger.info(f"    Cell {link_info['cell']}, Line: {link_info['content']}")
            sample_count += 1
            if sample_count >= 5:
                break
    
    # Now process notebooks to update links
    modified_files = []
    for filepath in notebooks:
        if update_links_in_notebook(filepath):
            modified_files.append(filepath)
    
    if modified_files:
        logger.info("Successfully modified files:")
        for filepath in modified_files:
            logger.info(f"  - {filepath}")
        logger.info(f"Total files modified: {len(modified_files)}")
    else:
        logger.info("No links were updated. This could be because:")
        logger.info("1. All links already follow the desired format")
        logger.info("2. All links match the exception criteria (archive/folders/external)")
        logger.info("3. The pattern matching needs adjustment")

if __name__ == "__main__":
    main()