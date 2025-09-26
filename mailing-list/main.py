import os
import re
import sys
import traceback
import urllib.request
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dateutil import tz
from dotenv import load_dotenv
from loguru import logger

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.elasticsearch_utils import document_view, document_add

load_dotenv()

from config.conf import DATA_DIR, INDEX_NAME

DOWNLOAD_PATH = os.path.join(DATA_DIR, "mailing-list/bitcoin-dev")

ORIGINAL_URL = "https://gnusha.org/pi/bitcoindev/"
CUSTOM_URL = "https://mailing-list.bitcoindevs.xyz/bitcoindev/"

# Configuration: Target year(s) to process
# Support both single year and date range
FROM_YEAR = int(os.getenv('FROM_YEAR', os.getenv('TARGET_YEAR', '2023')))
TO_YEAR = int(os.getenv('TO_YEAR', os.getenv('TARGET_YEAR', str(FROM_YEAR))))

# Backwards compatibility
TARGET_YEAR = FROM_YEAR  # For existing code that uses TARGET_YEAR

# Allow flexible year processing
FLEXIBLE_YEAR_PROCESSING = os.getenv('FLEXIBLE_YEAR_PROCESSING', 'true').lower() == 'true'

# Check if we're processing a range
IS_RANGE_MODE = FROM_YEAR != TO_YEAR

month_dict = {
    1: "Jan", 2: "Feb", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "Aug", 9: "Sept", 10: "Oct", 11: "Nov", 12: "Dec"
}


def save_web_page(link, file_name):
    main_url = ORIGINAL_URL + link
    html_response = requests.get(f"{ORIGINAL_URL}{link}")

    soup = BeautifulSoup(html_response.content, 'html.parser')
    main_url_anchor = soup.new_tag("a", href=main_url.replace('#t', ''), id='main_url')
    soup.body.append(main_url_anchor)

    path = os.path.join(DOWNLOAD_PATH, file_name)
    with open(path, 'w', encoding='utf-8') as file:
        logger.info(f'Downloading {file_name}')
        file.write(str(soup))


def download_dumps_range(path, page_visited_count, max_page_count=1, from_year=2023, to_year=2023):
    """Download dumps for a range of years"""
    if page_visited_count > max_page_count: 
        return
    page_visited_count += 1
    logger.info(f"Page {page_visited_count}: {path}")
    
    found_target_range = False
    years_found_in_page = set()
    
    with urllib.request.urlopen(f"{path}") as f:
        soup = BeautifulSoup(f, "html.parser")
        pre_tags = soup.find_all('pre')
        if len(pre_tags) < 1:
            return

        # Get next page link safely
        next_link_element = soup.find('a', {'rel': 'next'})
        next_page_link = f"{ORIGINAL_URL}{next_link_element.get('href')}" if next_link_element else None
        
        for tag in pre_tags[1].find_all('a'):
            try:
                date = tag.next_sibling.strip()[:7]
                date = date.strip().split('-')
                if len(date) < 2:
                    continue
                year = int(date[0])
                month = month_dict.get(int(date[1]))
                
                years_found_in_page.add(year)
                
                # Check if year is in our target range
                if from_year <= year <= to_year:
                    found_target_range = True
                    href = tag.get('href')
                    file_name = f"{year}-{month}-{href.strip().split('/')[0]}.html"
                    save_web_page(href, file_name)
                elif year < from_year:
                    # Stop if we've gone past our target range
                    if found_target_range:
                        logger.info(f"📅 Finished processing range {from_year}-{to_year}, reached {year}")
                        return
                # Continue if year > to_year (we'll find older years on next pages)

            except Exception as e:
                logger.error(e)
                logger.error(tag)
                continue
        
        # Log progress for range processing
        if years_found_in_page:
            years_in_range = [y for y in years_found_in_page if from_year <= y <= to_year]
            if years_in_range:
                logger.info(f"📅 Found years in range: {sorted(years_in_range)}")
        
        logger.info('----------------------------------------------------------\n')
        if next_page_link:
            download_dumps_range(next_page_link, page_visited_count, max_page_count, from_year, to_year)


def download_dumps(path, page_visited_count, max_page_count=1, target_year=2023):
    """Backwards compatibility wrapper - delegates to range function"""
    download_dumps_range(path, page_visited_count, max_page_count, target_year, target_year)


def get_thread_structure(soup):
    """Parse the thread structure from the thread overview section"""
    thread_structure = []
    
    # Find the thread overview section
    thread_overview = None
    
    # Look for the thread overview in different ways
    # Method 1: Look for <b id="t">Thread overview:</b> 
    thread_b_tag = soup.find('b', id='t')
    if thread_b_tag and "Thread overview:" in thread_b_tag.text:
        # Find the parent container (usually a <pre> tag containing the thread structure)
        thread_overview = thread_b_tag.find_parent('pre')
    
    # Method 2: Fallback to searching in pre tags
    if not thread_overview:
        for pre_tag in soup.find_all('pre'):
            if "Thread overview:" in pre_tag.text:
                thread_overview = pre_tag
                break
    
    if not thread_overview:
        logger.warning("⚠️ THREADING: No thread overview section found!")
        return []
    
    # Get all text from the thread overview section
    full_text = thread_overview.text
    
    # Split into lines and process each line
    lines = full_text.split('\n')
    
    # Process each line to extract threading information - USING FIXED VERSION
    thread_structure = _parse_thread_lines_fixed(lines, thread_overview)
    
    logger.success(f"✅ THREADING: Total extracted {len(thread_structure)} messages")
    
    # Log a brief summary of the thread hierarchy for important threads only
    if thread_structure and len(thread_structure) >= 20:  # Only log for larger threads
        logger.info(f"🎯 THREADING: Large thread detected ({len(thread_structure)} messages), max depth: {max(item['depth'] for item in thread_structure)}")
    
    return thread_structure


def _parse_thread_lines_fixed(lines, thread_overview_soup):
    """FIXED: Parse thread lines correctly from the HTML structure"""
    thread_structure = []
    
    # Extract anchor links from the HTML soup for proper anchor ID matching
    anchor_links = []
    if thread_overview_soup:
        anchor_links = thread_overview_soup.find_all('a', href=lambda href: href and href.startswith('#m'))
    
    anchor_link_index = 0  # Track which anchor link we're processing
    
    for line in lines:
        # Skip lines that don't contain thread information
        if ("links below jump to the message" in line or 
            "Thread overview:" in line or
            "download:" in line or
            "mbox.gz" in line or
            "Atom feed" in line or
            "end of thread" in line or
            not line.strip()):
            continue
        
        # Match the pattern: "YYYY-MM-DD HH:MM [optional spaces and backtick] ... Author Name"
        # Example: "2025-07-13 23:19 ` [bitcoindev] " Tadge Dryja"
        
        # First, find the timestamp pattern
        timestamp_pattern = r'(\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2})'
        timestamp_match = re.search(timestamp_pattern, line)
        
        if not timestamp_match:
            continue
        
        timestamp = timestamp_match.group(1)
        
        # Get everything after the timestamp
        after_timestamp = line[timestamp_match.end():]
        
        # Count leading spaces after timestamp to determine depth
        space_match = re.match(r'^(\s*)', after_timestamp)
        leading_spaces = len(space_match.group(1)) if space_match else 0
        
        # Check for backtick to determine if this is a reply
        has_backtick = '`' in after_timestamp
        
        # Calculate thread depth based on spacing
        if has_backtick:
            # Every 2 spaces before backtick increases depth by 1
            # " ` " = depth 1, "   ` " = depth 2, "     ` " = depth 3, etc.
            thread_depth = leading_spaces // 2 + 1 if leading_spaces > 0 else 1
        else:
            # No backtick means original post (depth 0)
            thread_depth = 0
        
        # Extract anchor ID from the corresponding HTML link (FIXED!)
        anchor_id = None
        if anchor_link_index < len(anchor_links):
            href = anchor_links[anchor_link_index].get('href', '')
            anchor_id = href.replace('#', '') if href.startswith('#') else None
            anchor_link_index += 1
        
        if not anchor_id:
            # Fallback: try to extract from the line text
            anchor_match = re.search(r'href="#([^"]+)"', line)
            anchor_id = anchor_match.group(1) if anchor_match else None
        
        if not anchor_id:
            # Create synthetic anchor if still not found
            import hashlib
            anchor_content = f"{timestamp}-{line[:50]}"
            anchor_id = hashlib.md5(anchor_content.encode()).hexdigest()[:32]
        
        # Extract author name - it's typically at the end of the line
        # Remove HTML tags first
        clean_line = re.sub(r'<a[^>]*>.*?</a>', '', after_timestamp)
        clean_line = re.sub(r'<[^>]+>', '', clean_line)
        
        # Clean up HTML entities
        clean_line = clean_line.replace('&#39;', "'").replace('&#34;', '"').replace('&lt;', '<').replace('&gt;', '>')
        
        # The author is typically the last part after removing subject info
        # Remove backtick and [bitcoindev] patterns
        if has_backtick:
            # Split by backtick and take the part after it
            parts = clean_line.split('`', 1)
            if len(parts) > 1:
                author_part = parts[1]
            else:
                author_part = clean_line
        else:
            author_part = clean_line
        
        # Clean up the author name
        author = author_part.strip()
        
        # Remove [bitcoindev] and quote marks
        author = re.sub(r'^\[bitcoindev\]\s*["\s]*', '', author)
        author = re.sub(r'^["\s]*', '', author)
        author = author.strip('\'"` \t')
        
        # Remove "via Bitcoin Development Mailing List" suffix
        author = re.sub(r'\s+via\s+Bitcoin\s+Development\s+Mailing\s+List.*$', '', author, flags=re.IGNORECASE).strip()
        
        # Handle empty author
        if not author or len(author) < 2:
            # Try to extract from the original line more carefully
            # Look for text after all HTML tags
            text_parts = re.sub(r'<[^>]*>', ' ', line).split()
            # Find text parts that look like names (avoid timestamps and technical terms)
            name_candidates = []
            for part in text_parts:
                if (len(part) > 2 and 
                    not re.match(r'\d{4}-\d{2}-\d{2}', part) and
                    not re.match(r'\d{1,2}:\d{2}', part) and
                    part not in ['bitcoindev', 'href', 'id'] and
                    not part.startswith('#')):
                    name_candidates.append(part)
            
            if name_candidates:
                # Take the last 1-2 parts as likely author name
                author = ' '.join(name_candidates[-2:]) if len(name_candidates) >= 2 else name_candidates[-1]
            else:
                author = "Unknown Author"
        
        # Final cleanup
        author = author.strip()
        
        if author and len(author) > 1:
            thread_structure.append({
                'timestamp': timestamp,
                'anchor_id': anchor_id,
                'author': author,
                'depth': thread_depth,
                'line': line.strip(),
                'leading_spaces': leading_spaces,
                'has_backtick': has_backtick
            })
    
    logger.success(f"✅ THREADING: Extracted {len(thread_structure)} messages")
    
    return thread_structure


# Removed old _parse_thread_lines function - no longer needed


def get_thread_urls_with_date(pre_tags):
    urls_dates = []
    date_time_pattern = r'\b\d{4}-\d{2}-\d{2} {1,2}(?:[01]?\d|2[0-3]):[0-5]\d\b'

    for pre_tag in reversed(pre_tags):
        if "links below jump to the message on this page" in pre_tag.text:
            anchor_tags = pre_tag.find_all('a', href=lambda href: href and '#' in href)

            for anchor in anchor_tags:
                date_search = re.search(date_time_pattern, anchor.previous_sibling.text)
                if date_search:
                    date = date_search.group()
                    original_datetime = datetime.strptime(date, '%Y-%m-%d %H:%M')
                    original_datetime = original_datetime.replace(tzinfo=tz.tzutc())
                    dt = original_datetime.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
                    urls_dates.append((anchor, dt))

    # sort the urls_dates list by datetime in ascending order (earliest first)
    urls_dates.sort(key=lambda x: x[1])
    return urls_dates


def get_year_month(date):
    date = date.strip().split('-')
    year = int(date[0])
    month = int(date[1])
    return year, month


def get_author(content_soup):
    """Extract author from the message header, not from quoted email content"""
    # Look for the pattern: <b>@ YYYY-MM-DD HH:MM Author Name</b>
    b_tags = content_soup.find_all('b')
    for b_tag in b_tags:
        text = b_tag.get_text()
        # Pattern: "@ 2025-07-12 21:36 Jameson Lopp"
        author_match = re.search(r'@\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+(.+)', text)
        if author_match:
            author = author_match.group(1).strip()
            # Clean up common artifacts
            author = author.replace("via Bitcoin Development Mailing List", "").strip()
            # Handle special characters
            author = author.replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">")
            return author
    
    # Fallback: try the From: line method
    text = content_soup.get_text()
    lines = text.split('\n')
    for line in lines[:15]:  # Check more lines for headers
        if line.startswith('From:') and '@' in line and 'UTC' in line:
            # Pattern: "From: Jameson Lopp @ 2025-07-12 21:36 UTC"
            from_match = re.search(r'From:\s*(.+?)\s+@\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+UTC', line)
            if from_match:
                author = from_match.group(1).strip()
                author = author.replace("'", "").replace("via Bitcoin Development Mailing List", "").strip()
                # Handle special characters
                author = author.replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">")
                return author
    
    # Enhanced fallback: look for any line with author pattern
    for line in lines[:20]:
        # Look for patterns like: "2025-07-14  2:07   ` Antoine Riard"
        author_pattern = re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+[`\s]*(.+?)(?:\s|$)', line)
        if author_pattern:
            potential_author = author_pattern.group(1).strip()
            # Skip if it looks like a subject line or other metadata
            if not any(skip in potential_author.lower() for skip in ['[bitcoindev]', 'thread overview', 'mbox.gz', 'atom feed', '`']):
                if len(potential_author) > 3 and not potential_author.startswith('http'):
                    author = potential_author.replace("via Bitcoin Development Mailing List", "").strip()
                    author = author.replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">")
                    return author
    
    logger.warning(f"⚠️ AUTHOR: Could not extract author from content")
    return "Unknown Author"


def href_contains_text(tag, search_text):
    return tag.name == 'a' and tag.has_attr('href') and search_text in tag['href']


def preprocess_body_text(text):
    text = text.replace("[|]", "").strip()
    text = re.sub(r'\[not found\] <[^>]+>', "", text)
    text = re.sub(re.compile(
        r'You received this message because you are subscribed to the Google Groups .+? group.\s+'
        r'To unsubscribe from this group and stop receiving emails from it, send an email to .+?\.\s+'
        r'To view this discussion on the web visit .+\.',
        re.DOTALL
    ), '', text)
    return text


def analyze_available_years():
    """Analyze what years are available in the downloaded data"""
    available_years = set()
    
    for root, _, files in os.walk(DOWNLOAD_PATH):
        for file in files:
            with open(f'{os.path.join(root, file)}', 'r', encoding='utf-8') as f:
                html_content = f.read()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                urls_with_date = get_thread_urls_with_date(soup.find_all('pre'))
                for _, date in urls_with_date:
                    year, _ = get_year_month(date)
                    available_years.add(year)
    
    return sorted(available_years)


def parse_dumps():
    doc = []
    
    # First analyze what years are available
    available_years = analyze_available_years()
    if available_years:
        logger.info(f"📅 Available years in archive: {available_years}")
        if TARGET_YEAR not in available_years:
            logger.warning(f"⚠️ Target year {TARGET_YEAR} not found in available data!")
            logger.warning(f"💡 Consider using one of these years: {available_years}")
    
    for root, _, files in os.walk(DOWNLOAD_PATH):
        for file in reversed(files):
            logger.info(f'parsing : {file}')
            with open(f'{os.path.join(root, file)}', 'r', encoding='utf-8') as f:
                u = file[9:].replace(".html", "")
                html_content = f.read()
                soup = BeautifulSoup(html_content, 'html.parser')

                # scrape url
                main_url = soup.find('a', id='main_url')
                main_url = main_url.get('href')

                # Scrape title
                title = soup.find_all('b')[1].text
                title = title.replace("[Bitcoin-development] ", "").replace("[bitcoin-dev] ", "").replace(
                    "[bitcoindev] ", "").replace("\t", "").strip()

                # Get thread structure for threading relationships
                thread_structure = get_thread_structure(soup)
                
                # Create a mapping of anchor_id to thread info
                thread_map = {}
                for thread_info in thread_structure:
                    anchor_id = thread_info['anchor_id'].replace('#', '')
                    thread_map[anchor_id] = thread_info

                urls_with_date = get_thread_urls_with_date(soup.find_all('pre'))
                
                for index, (url, date) in enumerate(urls_with_date):
                    try:
                        year, month = get_year_month(date)
                        # Process data based on range or single year
                        if IS_RANGE_MODE:
                            # Range mode: check if year is within FROM_YEAR to TO_YEAR
                            if not (FROM_YEAR <= year <= TO_YEAR):
                                continue
                        else:
                            # Single year mode: process target year data only, or allow flexible processing
                            if not FLEXIBLE_YEAR_PROCESSING and year != TARGET_YEAR:
                                continue
                            elif FLEXIBLE_YEAR_PROCESSING and year not in available_years:
                                continue  # This shouldn't happen but just in case

                        href = url.get('href')
                        tag_id = url.get('id')
                        anchor_id = href.replace('#', '')
                        
                        content = soup.find(lambda tag: tag.name == "pre" and tag.find('a', href=f"#{tag_id}"))

                        # Scrape Body
                        for c in content.find_all('b'):
                            c.decompose()

                        for c in content.find_all('u'):
                            c.decompose()

                        for c in content.find_all(lambda tag: href_contains_text(tag, href.replace("#", "")[1:])):
                            c.decompose()

                        for c in content.find_all(lambda tag: href_contains_text(tag, u)):
                            c.decompose()

                        body_text = preprocess_body_text(content.text)

                        doc_id = f"mailing-list-{year}-{month:02d}-{anchor_id}"
                        
                        # Get threading information by matching with thread structure
                        thread_info = None
                        thread_depth = 0
                        author = None  # Will be set from thread structure
                        
                        # Parse document timestamp for matching
                        parsed_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                        doc_timestamp = parsed_date.strftime('%Y-%m-%d %H:%M')
                        
                        # Find matching thread info by anchor_id first (most reliable)
                        for thread_item in thread_structure:
                            thread_anchor = thread_item['anchor_id']
                            # Try exact anchor match
                            if thread_anchor == anchor_id:
                                thread_info = thread_item
                                thread_depth = thread_item.get('depth', 0)
                                author = thread_item.get('author')  # Use thread structure author
                                break
                        
                        # Fallback: match by author and timestamp
                        if not thread_info:
                            for thread_item in thread_structure:
                                thread_author = thread_item['author'].lower().strip()
                                doc_author = author.lower().strip()
                                thread_timestamp = thread_item['timestamp']
                                
                                # Try exact author + timestamp match
                                if thread_author == doc_author and thread_timestamp == doc_timestamp:
                                    thread_info = thread_item
                                    thread_depth = thread_item.get('depth', 0)
                                    break
                                # Try author match with close timestamp (within 1 minute)
                                elif thread_author == doc_author:
                                    try:
                                        thread_dt = datetime.strptime(thread_timestamp, '%Y-%m-%d %H:%M')
                                        doc_dt = datetime.strptime(doc_timestamp, '%Y-%m-%d %H:%M')
                                        if abs((thread_dt - doc_dt).total_seconds()) <= 60:  # Within 1 minute
                                            thread_info = thread_item
                                            thread_depth = thread_item.get('depth', 0)
                                            break
                                    except:
                                        pass
                        
                        # Fallback: extract author from content if no thread match
                        if not thread_info or not author:
                            content_author = get_author(content)
                            if not author:
                                author = content_author
                            if not thread_info:
                                logger.warning(f"⚠️ THREADING: No thread match found for '{author}' at {doc_timestamp}")
                        
                        # Note: doc_id_map could be used for parent resolution if needed in the future
                        
                        # Determine parent relationship and thread position
                        parent_id = None
                        reply_to_author = None
                        
                        # Set thread_position based on thread structure order, not URL order
                        if thread_info:
                            thread_position = next((i for i, item in enumerate(thread_structure) if item == thread_info), index)
                        else:
                            thread_position = index  # Fallback to URL order if no thread match
                        
                        if thread_depth > 0 and thread_structure and thread_info:
                            # Find the parent by looking for the previous message with depth-1
                            target_depth = thread_depth - 1
                            current_index = next((i for i, info in enumerate(thread_structure) if info == thread_info), -1)
                            
                            if current_index > 0:
                                for i in range(current_index - 1, -1, -1):
                                    prev_info = thread_structure[i]
                                    if prev_info['depth'] == target_depth:
                                        # Create parent document ID based on the parent's anchor
                                        parent_anchor = prev_info['anchor_id']
                                        parent_id = f"mailing-list-{year}-{month:02d}-{parent_anchor}"
                                        reply_to_author = prev_info['author']
                                        break

                        document = {
                            "id": doc_id,
                            "authors": [author],
                            "title": title,
                            "body": body_text,
                            "body_type": "raw",
                            "created_at": date,
                            "domain": CUSTOM_URL,
                            "thread_url": main_url,
                            "url": f"{main_url}{href}",
                            # Threading fields
                            "thread_depth": thread_depth,
                            "thread_position": thread_position,
                            "parent_id": parent_id,
                            "reply_to_author": reply_to_author,
                            "anchor_id": anchor_id
                        }

                        if index == 0:
                            document['type'] = "original_post"
                        else:
                            document['type'] = "reply"
                        
                        # Log only for significant threading relationships
                        if thread_depth > 2:  # Only log for deeper nested messages
                            logger.info(f"📝 Deep thread: {author} (depth {thread_depth}) -> {reply_to_author}")
                            
                        doc.append(document)
                        
                    except Exception as e:
                        logger.info(f"{e} \nORIGINAL_URL: {main_url}\n{traceback.format_exc()}")
                        continue
    return doc


def index_documents(docs):
    # Process all threads from 2023 onwards (removed test thread restriction)
    if not docs:
        logger.warning("🚫 No documents to process")
        logger.warning(f"🔍 This might be because:")
        logger.warning(f"   1. The target year {TARGET_YEAR} has no data in the archive")
        logger.warning(f"   2. The archive source doesn't go back to {TARGET_YEAR}")
        logger.warning(f"   3. The mailing list wasn't active in {TARGET_YEAR}")
        logger.warning(f"💡 Try a more recent year (2015+) or check available years first")
        return
    
    # Get the year from the first document to show what we're processing
    first_doc_date = docs[0].get('created_at', '')
    if first_doc_date:
        doc_year = first_doc_date[:4]
        logger.success(f"🎯 Processing thread from {doc_year}: {docs[0].get('title', 'Unknown title')[:80]}...")
    else:
        logger.success(f"🎯 Processing thread with {len(docs)} documents")
    
    new_docs = 0
    existing_docs = 0
    threading_docs = 0
    updated_docs = 0
    
    for doc in docs:
        # Check if document has threading data
        has_threading = any([
            doc.get('thread_depth', 0) > 0,
            doc.get('parent_id') is not None,
            doc.get('reply_to_author') is not None,
            doc.get('thread_depth') == 0  # Include root messages too
        ])
        
        if has_threading:
            threading_docs += 1

        resp = document_view(index_name=INDEX_NAME, doc_id=doc['id'])
        if not resp:
            # Process all new documents
            _ = document_add(index_name=INDEX_NAME, doc=doc, doc_id=doc['id'])
            new_docs += 1
            
            if has_threading and doc.get("thread_depth", 0) > 0:
                logger.success(f'✅ Added: {doc.get("authors", ["Unknown"])[0]} (depth {doc.get("thread_depth", 0)})')
            elif not has_threading:
                logger.warning(f'⚠️ No threading data: {doc.get("authors", ["Unknown"])[0]}')
        else:
            existing_docs += 1
            
            # Update the existing document with new threading fields
            _ = document_add(index_name=INDEX_NAME, doc=doc, doc_id=doc['id'])
            updated_docs += 1
            
            if has_threading and doc.get("thread_depth", 0) > 0:
                logger.success(f'✅ Updated: {doc.get("authors", ["Unknown"])[0]} (depth {doc.get("thread_depth", 0)})')
            elif not has_threading:
                logger.warning(f'⚠️ No threading data to update: {doc.get("authors", ["Unknown"])[0]}')
    
    logger.success("📊 INDEXING SUMMARY:")
    logger.success(f"    📝 Total documents processed: {len(docs)}")
    logger.success(f"    ✅ New documents added: {new_docs}")
    logger.success(f"    📄 Existing documents: {existing_docs}")
    logger.success(f"    🔄 Documents updated: {updated_docs}")
    logger.success(f"    🧵 Documents with threading data: {threading_docs}")
    
    # Show processing mode
    if IS_RANGE_MODE:
        logger.success(f"    🎯 Processing mode: {FROM_YEAR}-{TO_YEAR} range (all threads)")
    else:
        logger.success(f"    🎯 Processing mode: {TARGET_YEAR} threads (all threads)")


if __name__ == "__main__":
    logger.info("🚀 Starting mailing list scraper with threading support")
    
    if IS_RANGE_MODE:
        logger.success(f"📅 PROCESSING MODE: Date range {FROM_YEAR} to {TO_YEAR}")
        logger.info(f"🎯 Will process {TO_YEAR - FROM_YEAR + 1} year(s) of data")
    else:
        logger.success(f"📅 PROCESSING MODE: Single year {TARGET_YEAR}")
        
        if FLEXIBLE_YEAR_PROCESSING:
            logger.info("🔄 FLEXIBLE MODE: Will process available years if target year not found")
    
    if not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH)

    # Process with increased page count to find the target year(s)
    if IS_RANGE_MODE:
        download_dumps_range(ORIGINAL_URL, page_visited_count=0, max_page_count=50, 
                           from_year=FROM_YEAR, to_year=TO_YEAR)
    else:
        download_dumps(ORIGINAL_URL, page_visited_count=0, max_page_count=50, target_year=TARGET_YEAR)
    
    documents = parse_dumps()
    
    # If no documents found, provide helpful suggestions
    if not documents:
        if IS_RANGE_MODE:
            logger.error(f"❌ No documents found for range {FROM_YEAR}-{TO_YEAR}")
            logger.error("💡 Try a more recent range (e.g., FROM_YEAR=2020 TO_YEAR=2023)")
        elif not FLEXIBLE_YEAR_PROCESSING:
            logger.error("❌ No documents found. Try running with FLEXIBLE_YEAR_PROCESSING=true to see available years")
            logger.error("💡 Example: FLEXIBLE_YEAR_PROCESSING=true TARGET_YEAR=2023 python mailing-list/main.py")
        logger.error("💡 Or try using a date range: FROM_YEAR=2020 TO_YEAR=2023 python mailing-list/main.py")
    
    index_documents(documents)
