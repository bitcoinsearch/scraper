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


def download_dumps(path, page_visited_count, max_page_count=1):
    if page_visited_count > max_page_count: return
    page_visited_count += 1
    logger.info(f"Page {page_visited_count}: {path}")
    with urllib.request.urlopen(f"{path}") as f:
        soup = BeautifulSoup(f, "html.parser")
        pre_tags = soup.find_all('pre')
        if len(pre_tags) < 1:
            return

        next_page_link = f"{ORIGINAL_URL}{soup.find('a', {'rel': 'next'}).get('href')}"
        for tag in pre_tags[1].find_all('a'):
            try:
                date = tag.next_sibling.strip()[:7]
                date = date.strip().split('-')
                # date = tag.next_sibling.strip()[:8]
                if len(date) < 2:
                    continue
                year = int(date[0])
                mon = int(date[1])
                month = month_dict.get(int(date[1]))
                if year < 2024 or (year == 2024 and mon == 1):
                    return

                href = tag.get('href')
                file_name = f"{year}-{month}-{href.strip().split('/')[0]}.html"

                save_web_page(href, file_name)

            except Exception as e:
                logger.error(e)
                logger.error(tag)
                continue
        logger.info('----------------------------------------------------------\n')
        if next_page_link:
            download_dumps(next_page_link, page_visited_count)


def get_thread_structure(soup):
    """Parse the thread structure from the thread overview section"""
    thread_structure = []
    
    logger.info("🧵 THREADING: Starting thread structure extraction...")
    
    # Find the thread overview section
    thread_overview = None
    
    # Look for the thread overview in different ways
    # Method 1: Look for <b id="t">Thread overview:</b> 
    thread_b_tag = soup.find('b', id='t')
    if thread_b_tag and "Thread overview:" in thread_b_tag.text:
        # Find the parent container (usually a <pre> tag containing the thread structure)
        thread_overview = thread_b_tag.find_parent('pre')
        if thread_overview:
            logger.info("🔍 THREADING: Found thread overview section via <b id='t'> tag")
    
    # Method 2: Fallback to searching in pre tags
    if not thread_overview:
        for pre_tag in soup.find_all('pre'):
            if "Thread overview:" in pre_tag.text:
                thread_overview = pre_tag
                logger.info("🔍 THREADING: Found thread overview section via pre tag search")
                break
    
    if not thread_overview:
        logger.warning("⚠️ THREADING: No thread overview section found!")
        return []
    
    # Get all text from the thread overview section
    full_text = thread_overview.text
    
    # Split into two sections if they exist
    strict_section = full_text
    loose_section = ""
    
    # Check if there are both strict and loose matches
    loose_marker = "-- strict thread matches above, loose matches on Subject: below --"
    if loose_marker in full_text:
        parts = full_text.split(loose_marker)
        strict_section = parts[0]
        loose_section = parts[1] if len(parts) > 1 else ""
        logger.info("🔍 THREADING: Found both strict and loose thread matches")
    else:
        logger.info("🔍 THREADING: Found only strict thread matches")
    
    # Parse both sections
    lines = strict_section.split('\n')
    logger.info(f"📄 THREADING: Processing {len(lines)} lines in strict thread section")
    
    # Process strict thread matches (properly threaded)
    thread_structure.extend(_parse_thread_lines(lines, "strict"))
    
    # Process loose matches if they exist
    if loose_section:
        loose_lines = loose_section.split('\n')
        logger.info(f"📄 THREADING: Processing {len(loose_lines)} lines in loose subject matches")
        thread_structure.extend(_parse_thread_lines(loose_lines, "loose"))
    
    logger.success(f"✅ THREADING: Total extracted {len(thread_structure)} messages from both sections")
    
    # Log the thread hierarchy
    if thread_structure:
        logger.info("🎯 THREADING: Combined thread hierarchy:")
        strict_count = len([t for t in thread_structure if t.get('section_type') == 'strict'])
        loose_count = len([t for t in thread_structure if t.get('section_type') == 'loose'])
        logger.info(f"    📊 Strict thread matches: {strict_count}")
        logger.info(f"    📊 Loose subject matches: {loose_count}")
        
        for i, item in enumerate(thread_structure[:10]):  # Show first 10
            indent = "  " * item['depth']
            section_indicator = "🔗" if item.get('section_type') == 'strict' else "📄"
            logger.info(f"    {section_indicator} {indent}#{i}: {item['author']} (depth: {item['depth']})")
        
        if len(thread_structure) > 10:
            logger.info(f"    ... and {len(thread_structure) - 10} more messages")
    
    return thread_structure


def _parse_thread_lines(lines, section_type):
    """Parse thread lines from either strict or loose section"""
    thread_structure = []
    
    logger.info(f"📧 THREADING: Parsing {section_type} thread section")
    
    for line in lines:
        if "-- links below jump to the message on this page --" in line:
            continue
        
        # Match pattern like: "2025-08-31 22:25 ` Ben Westgate' via Bitcoin Development Mailing List"
        # Look for date pattern
        date_pattern = r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})'
        
        date_match = re.search(date_pattern, line)
        
        if date_match:
            # Find the position after the timestamp
            after_date_pos = date_match.end()
            after_date = line[after_date_pos:]
            
            # Check for backtick to determine if this is a reply or original post
            space_before_backtick = re.search(r'^(\s*)`', after_date)
            
            if space_before_backtick:
                # This is a reply - count spaces to determine thread depth
                spaces = len(space_before_backtick.group(1))
                if spaces == 0:
                    thread_depth = 0  # Original post  
                elif spaces == 1:
                    thread_depth = 1  # Direct reply
                elif spaces == 2:
                    thread_depth = 2  # Reply to reply
                elif spaces >= 4:
                    # For 4+ spaces, assume every 2 additional spaces = 1 more depth level
                    thread_depth = 2 + ((spaces - 2) // 2)
                else:
                    thread_depth = 1  # Default fallback
                
                # Extract author (everything after the ` character)
                author_part = after_date[space_before_backtick.end():].strip()
            else:
                # No backtick means this is likely the original post
                # For loose matches, treat as separate threads (depth 0)
                thread_depth = 0 if section_type == "loose" else 0
                # Extract author from the remaining text
                author_part = after_date.strip()
                
            # Remove any HTML tags and get clean author name
            author = re.sub(r'<[^>]+>', '', author_part).strip()
            # Remove quotes around author names and clean up
            author = author.strip("'\"").strip()
            # Remove common suffixes
            author = re.sub(r'\s+via\s+Bitcoin\s+Development\s+Mailing\s+List.*$', '', author, re.IGNORECASE).strip()
            
            if author:  # Only process if we found a valid author
                timestamp = date_match.group(1)
                
                # Since this HTML doesn't have anchor IDs in the thread overview, 
                # we'll create a synthetic anchor based on timestamp and author
                import hashlib
                anchor_content = f"{timestamp}-{author}-{section_type}"
                anchor_id = hashlib.md5(anchor_content.encode()).hexdigest()[:32]
                
                logger.info(f"📧 THREADING ({section_type}): Found message - Author: '{author}', Depth: {thread_depth}, Time: {timestamp}, Spaces: {spaces if space_before_backtick else 0}")
                
                thread_structure.append({
                    'timestamp': timestamp,
                    'anchor_id': f"#{anchor_id}",
                    'author': author,
                    'depth': thread_depth,
                    'line': line.strip(),
                    'section_type': section_type
                })
            else:
                logger.info(f"📧 THREADING ({section_type}): Skipping line (no author found): {line.strip()}")
    
    logger.success(f"✅ THREADING ({section_type}): Extracted {len(thread_structure)} messages")
    
    return thread_structure


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
            logger.info(f"📧 AUTHOR: Extracted author from header: '{author}'")
            return author
    
    # Fallback: try the old method but with better filtering
    text = content_soup.get_text()
    lines = text.split('\n')
    for line in lines[:10]:  # Only check first 10 lines for headers
        if line.startswith('From:') and '@' in line and 'UTC' in line:
            from_match = re.search(r'From:\s*(.+?)\s+@\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+UTC', line)
            if from_match:
                author = from_match.group(1).strip()
                author = author.replace("'", "").replace("via Bitcoin Development Mailing List", "").strip()
                logger.info(f"📧 AUTHOR: Extracted author from From line: '{author}'")
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


def parse_dumps():
    doc = []
    for root, dirs, files in os.walk(DOWNLOAD_PATH):
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
                
                logger.info(f"🔗 THREADING: Creating thread map for {len(thread_structure)} messages")
                
                # Create a mapping of anchor_id to thread info
                thread_map = {}
                for thread_info in thread_structure:
                    anchor_id = thread_info['anchor_id'].replace('#', '')
                    thread_map[anchor_id] = thread_info
                    logger.info(f"📍 THREADING: Mapped anchor '{anchor_id}' -> author '{thread_info['author']}' depth {thread_info['depth']}")

                urls_with_date = get_thread_urls_with_date(soup.find_all('pre'))
                
                for index, (url, date) in enumerate(urls_with_date):
                    try:
                        year, month = get_year_month(date)
                        if year < 2024 or (year == 2024 and month == 1):
                            continue

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

                        # Scraping author from the content soup (before text extraction)
                        author = get_author(content)

                        doc_id = f"mailing-list-{year}-{month:02d}-{anchor_id}"
                        
                        # Get threading information by matching author and timestamp
                        thread_info = None
                        thread_depth = 0
                        
                        # Try to match this document with thread structure by author
                        parsed_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                        doc_timestamp = parsed_date.strftime('%Y-%m-%d %H:%M')
                        
                        logger.info(f"📧 THREADING DOC: Processing {anchor_id} - Author: '{author}', Looking for timestamp: {doc_timestamp}")
                        
                        # Find matching thread info by author (relaxed timestamp matching)
                        for thread_item in thread_structure:
                            # Match by author name (case insensitive, flexible matching)
                            thread_author = thread_item['author'].lower().strip()
                            doc_author = author.lower().strip()
                            
                            # Try exact match first
                            if thread_author == doc_author:
                                thread_info = thread_item
                                thread_depth = thread_item.get('depth', 0)
                                logger.success(f"✅ THREADING DOC: Exact author match! '{author}' -> depth {thread_depth}")
                                break
                            # Try partial match (in case of name variations)
                            elif thread_author in doc_author or doc_author in thread_author:
                                thread_info = thread_item
                                thread_depth = thread_item.get('depth', 0)
                                logger.success(f"✅ THREADING DOC: Partial author match! '{author}' ≈ '{thread_item['author']}' -> depth {thread_depth}")
                                break
                        
                        if not thread_info:
                            logger.warning(f"⚠️ THREADING DOC: No thread match found for '{author}' at {doc_timestamp}")
                            logger.info(f"📋 THREADING DOC: Available thread authors: {[t['author'] for t in thread_structure]}")
                        
                        # Determine parent relationship
                        parent_id = None
                        reply_to_author = None
                        thread_position = index
                        
                        if thread_depth > 0 and thread_structure and thread_info:
                            logger.info(f"🔍 THREADING DOC: Looking for parent (target depth: {thread_depth - 1})")
                            # Find the parent by looking for the previous message with depth-1
                            target_depth = thread_depth - 1
                            current_index = next((i for i, info in enumerate(thread_structure) if info == thread_info), -1)
                            
                            logger.info(f"📍 THREADING DOC: Current index in thread: {current_index}")
                            
                            if current_index > 0:
                                for i in range(current_index - 1, -1, -1):
                                    prev_info = thread_structure[i]
                                    logger.info(f"    Checking previous message {i}: depth={prev_info['depth']}, author='{prev_info['author']}'")
                                    if prev_info['depth'] == target_depth:
                                        # We'll need to find the actual anchor_id for this parent
                                        # For now, create a placeholder that will be resolved later
                                        parent_id = f"mailing-list-{year}-{month:02d}-PARENT-{i}"
                                        reply_to_author = prev_info['author']
                                        logger.success(f"✅ THREADING DOC: Found parent! '{author}' -> '{reply_to_author}' (parent_index: {i})")
                                        break
                                
                                if not parent_id:
                                    logger.warning(f"⚠️ THREADING DOC: No parent found for depth {thread_depth} message")
                        else:
                            logger.info(f"🌟 THREADING DOC: This is a root message (depth: {thread_depth})")

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
                        
                        # Log the final document with threading data
                        logger.info(f"📝 THREADING DOC: Created document {doc_id}")
                        logger.info(f"    📊 Threading Data: depth={thread_depth}, position={thread_position}")
                        logger.info(f"    🔗 Parent: {parent_id} (reply_to: {reply_to_author})")
                        logger.info(f"    🏷️ Type: {document['type']}, Author: {author}")
                            
                        doc.append(document)
                        
                    except Exception as e:
                        logger.info(f"{e} \nORIGINAL_URL: {main_url}\n{traceback.format_exc()}")
                        continue
    return doc


def index_documents(docs):
    logger.info(f"🗃️ INDEXING: Starting to index {len(docs)} documents with threading data")
    
    # Check if this is one of our test threads (Quantum Recovery or Post Quantum Migration)
    is_quantum_recovery_thread = any("Against-Allowing-Quantum-Recovery-of-Bitcoin" in doc.get('title', '') or 
                                    "Against Allowing Quantum Recovery" in doc.get('title', '') for doc in docs)
    
    is_post_quantum_thread = any("A Post Quantum Migration Proposal" in doc.get('title', '') or
                                "Post Quantum Migration" in doc.get('title', '') for doc in docs)
    
    is_test_thread = is_quantum_recovery_thread or is_post_quantum_thread
    
    if is_test_thread:
        if is_quantum_recovery_thread:
            logger.success("🎯 QUANTUM RECOVERY THREAD DETECTED: Processing ALL documents for testing!")
        if is_post_quantum_thread:
            logger.success("🎯 POST QUANTUM MIGRATION THREAD DETECTED: Processing ALL documents for testing!")
    else:
        logger.warning("🚫 NON-TEST THREAD: Skipping all processing for safety!")
        logger.warning("📋 Only Quantum Recovery and Post Quantum Migration threads will be processed until testing is complete")
        return  # Skip processing entirely for non-test threads
    
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
            # Process all new documents in Quantum thread
            _ = document_add(index_name=INDEX_NAME, doc=doc, doc_id=doc['id'])
            new_docs += 1
            
            logger.success(f'✅ INDEXING: Successfully added document! ID: {doc["id"]}')
            logger.success(f'🎯 DOCUMENT DETAILS:')
            logger.success(f'    📰 Title: {doc.get("title", "N/A")}')
            logger.success(f'    👤 Author: {doc.get("authors", ["N/A"])[0]}')
            logger.success(f'    🔗 URL: {doc.get("url", "N/A")}')
            logger.success(f'    📅 Created: {doc.get("created_at", "N/A")}')
            
            if has_threading:
                logger.success(f'    🧵 THREADING DATA:')
                logger.success(f'        - Depth: {doc.get("thread_depth", 0)}')
                logger.success(f'        - Position: {doc.get("thread_position", 0)}') 
                logger.success(f'        - Parent ID: {doc.get("parent_id", "None")}')
                logger.success(f'        - Reply to: {doc.get("reply_to_author", "None")}')
                logger.success(f'        - Type: {doc.get("type", "N/A")}')
            else:
                logger.warning(f'    ⚠️ NO THREADING DATA found for this document')
        else:
            existing_docs += 1
            logger.info(f"📄 INDEXING: Document already exists! ID: {doc['id']}")
            
            # Update all existing documents in Quantum thread with threading data
            logger.warning(f"🧪 UPDATING: Existing document with threading data!")
            
            # Update the existing document with new threading fields
            _ = document_add(index_name=INDEX_NAME, doc=doc, doc_id=doc['id'])
            updated_docs += 1
            
            logger.success(f'✅ UPDATED: Successfully updated document! ID: {doc["id"]}')
            logger.success(f'🎯 UPDATED DOCUMENT DETAILS:')
            logger.success(f'    📰 Title: {doc.get("title", "N/A")}')
            logger.success(f'    👤 Author: {doc.get("authors", ["N/A"])[0]}')
            logger.success(f'    🔗 URL: {doc.get("url", "N/A")}')
            logger.success(f'    📅 Created: {doc.get("created_at", "N/A")}')
            
            if has_threading:
                logger.success(f'    🧵 THREADING DATA UPDATED:')
                logger.success(f'        - Depth: {doc.get("thread_depth", 0)}')
                logger.success(f'        - Position: {doc.get("thread_position", 0)}') 
                logger.success(f'        - Parent ID: {doc.get("parent_id", "None")}')
                logger.success(f'        - Reply to: {doc.get("reply_to_author", "None")}')
                logger.success(f'        - Type: {doc.get("type", "N/A")}')
                logger.success(f'        - Anchor ID: {doc.get("anchor_id", "N/A")}')
            else:
                logger.warning(f'    ⚠️ NO THREADING DATA to update')
    
    logger.success("📊 INDEXING SUMMARY:")
    logger.success(f"    📝 Total documents processed: {len(docs)}")
    logger.success(f"    ✅ New documents added: {new_docs}")
    logger.success(f"    📄 Existing documents: {existing_docs}")
    logger.success(f"    🔄 Documents updated: {updated_docs}")
    logger.success(f"    🧵 Documents with threading data: {threading_docs}")
    
    # Show which test thread mode is active
    if is_quantum_recovery_thread:
        logger.success(f"    🎯 Test thread mode: QUANTUM RECOVERY")
    elif is_post_quantum_thread:
        logger.success(f"    🎯 Test thread mode: POST QUANTUM MIGRATION")
    else:
        logger.success(f"    🎯 Test thread mode: OFF")


if __name__ == "__main__":
    logger.warning("🚨🚨🚨 TEST THREADS ONLY MODE 🚨🚨🚨")
    logger.warning("📋 PROCESSING RULES:")
    logger.warning("    - Only processing 1 page (most recent)")
    logger.warning("    - QUANTUM RECOVERY THREAD: All documents will be processed")
    logger.warning("    - POST QUANTUM MIGRATION THREAD: All documents will be processed")
    logger.warning("    - ALL OTHER THREADS: Completely skipped for maximum safety")
    logger.warning("    - Improved threading detection with flexible author matching")
    logger.warning("🎯 ONLY test threads (Quantum Recovery + Post Quantum Migration) will be processed!")
    
    if not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH)

    download_dumps(ORIGINAL_URL, page_visited_count=0)
    documents = parse_dumps()
    index_documents(documents)
