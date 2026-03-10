import unicodedata
import re

def clean_name(name):
    """Removes emojis and special chars."""
    name = unicodedata.normalize('NFKD', name)
    return "".join(c for c in name if c.isalnum() or c in " -_.,")

def get_smart_name_map(guild):
    """Maps various username formats to User IDs."""
    name_map = {}
    for member in guild.members:
        uid = str(member.id)
        name_map[member.display_name.lower().strip()] = uid
        name_map[member.name.lower().strip()] = uid
        if member.global_name:
            name_map[member.global_name.lower().strip()] = uid
        clean = clean_name(member.display_name).lower().strip()
        if clean:
            name_map[clean] = uid
    return name_map

def parse_wordle_message(content, name_map, fail_penalty):
    """Extracts scores, user IDs, and the current streak from a message."""
    score_pattern = re.compile(r"([X\d])/6:(.*)")
    mention_pattern = re.compile(r"<@!?(\d+)>")
    streak_pattern = re.compile(r"on a (\d+) day streak")
    
    results = []
    streak = 0
    
    streak_match = streak_pattern.search(content)
    if streak_match:
        streak = int(streak_match.group(1))
    
    if "Your group is on a" in content:
        for line in content.split('\n'):
            line = line.strip()
            match = score_pattern.search(line)
            if match:
                raw_score = match.group(1)
                user_part = match.group(2)
                score = fail_penalty if raw_score == 'X' else int(raw_score)
                found_users = set()
                
                # 1. Direct Mentions (<@12345>)
                mentions = mention_pattern.findall(user_part)
                for uid in mentions: 
                    found_users.add(uid)
                    user_part = re.sub(f"<@!?{uid}>", "", user_part)
                
                # 2. Unpinged Text Names 
                # THE FIX: Split by '@' to cleanly separate multiple un-pinged names on the same line
                for chunk in user_part.split('@'):
                    raw_text = chunk.strip().lower()
                    if not raw_text: continue # Skip empty chunks
                    
                    # Exact Match
                    if raw_text in name_map:
                        found_users.add(name_map[raw_text])
                        continue
                    
                    # Clean Match (removes emojis, trailing spaces)
                    clean_text = clean_name(raw_text).strip()
                    if clean_text in name_map:
                        found_users.add(name_map[clean_text])
                        continue

                for uid in found_users: results.append((uid, score))
                
    return results, streak