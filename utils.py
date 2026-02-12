import unicodedata
import re

def clean_name(name):
    """Removes emojis and special chars."""
    name = unicodedata.normalize('NFKD', name)
    return "".join(c for c in name if c.isalnum() or c in " -_.,")

def get_smart_name_map(guild):
    """Maps various username formats (steve, @steve, 🔥steve) to User IDs."""
    name_map = {}
    for member in guild.members:
        uid = str(member.id)
        # 1. Lowercase Display Name
        name_map[member.display_name.lower().strip()] = uid
        # 2. Lowercase Username
        name_map[member.name.lower().strip()] = uid
        # 3. Global Name
        if member.global_name:
            name_map[member.global_name.lower().strip()] = uid
        # 4. Cleaned Display Name
        clean = clean_name(member.display_name).lower().strip()
        if clean:
            name_map[clean] = uid
    return name_map

def parse_wordle_message(content, name_map, fail_penalty):
    """Extracts scores and user IDs from a message."""
    score_pattern = re.compile(r"([X\d])/6:(.*)")
    mention_pattern = re.compile(r"<@!?(\d+)>")
    results = []
    
    if "Your group is on a" in content:
        for line in content.split('\n'):
            line = line.strip()
            match = score_pattern.search(line)
            if match:
                raw_score = match.group(1)
                user_part = match.group(2)
                score = fail_penalty if raw_score == 'X' else int(raw_score)
                found_users = set()
                
                # Direct Mentions
                mentions = mention_pattern.findall(user_part)
                for uid in mentions: 
                    found_users.add(uid)
                    user_part = user_part.replace(f"<@{uid}>", "").replace(f"<@!{uid}>", "")
                
                # Fuzzy Text Matching
                normalized_text = user_part.replace('@', ' ').replace(',', ' ')
                for chunk in normalized_text.split():
                    raw_text = chunk.strip().lower()
                    if not raw_text: continue
                    
                    if raw_text in name_map:
                        found_users.add(name_map[raw_text])
                        continue
                    clean_text = clean_name(raw_text)
                    if clean_text in name_map:
                        found_users.add(name_map[clean_text])

                for uid in found_users: results.append((uid, score))
    return results