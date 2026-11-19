import re

def extract_xml_content(text, tag_name):
    pattern = f'<{tag_name}>(.*?)</{tag_name}>'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        return None