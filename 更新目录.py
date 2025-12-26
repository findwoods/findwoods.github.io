import os
import html # 用于转义文件名
import urllib.parse # 用于安全地组合URL
import re

# 设置根文件夹路径
root_folder = '.'  # 当前目录

# 定义输出文件名
output_file_local = 'indexLocal.html'
output_file_github = 'index.html' # 新的GitHub链接版本

# 定义 GitHub Pages 的基础 URL
GITHUB_BASE_URL = "https://findwoods.github.io/"

# 定义要排除的目录和文件
EXCLUDED_DIRECTORIES = ["_layouts"]
EXCLUDED_FILES = ["index0.html", output_file_local, output_file_github] # 排除两个索引文件自身

# 定义顶层目录的期望顺序
PREDEFINED_ORDER = ["线性代数", "MQST", "QCQI", "MathODE", "PhysLab", "ChemLab", "PhysChem", "OrgChem1", "PhysChem1", "Atkins", "PhysAnaChemLab", "APP", "IBM", "时间序列"]

def natural_sort_key(s):
    """
    一个用于自然排序的键函数。
    例如：natural_sort_key("item2.txt") -> ['item', 2, '.txt']
          natural_sort_key("item10.txt") -> ['item', 10, '.txt']
    """
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', str(s))]

def generate_html_for_directory(current_dir_path, root_path_for_links, is_top_level=False, base_url_prefix=""):
    """
    递归地为指定目录生成HTML列表项。

    Args:
        current_dir_path (str): 当前正在处理的目录的绝对或相对路径。
        root_path_for_links (str): index.html 所在的根目录路径，用于生成相对链接。
        is_top_level (bool): 是否是正在处理根目录本身的内容。
        base_url_prefix (str): 可选的URL前缀，用于生成绝对链接。

    Returns:
        str: 代表当前目录内容的HTML字符串。
    """
    html_parts = []
    if not is_top_level or is_top_level:
        html_parts.append("<ul>\n")

    try:
        entries = sorted(os.listdir(current_dir_path), key=natural_sort_key)
    except OSError as e:
        error_message = f"  <li><em>Error accessing {html.escape(current_dir_path)}: {html.escape(str(e))}</em></li>\n"
        html_parts.append(error_message)
        html_parts.append("</ul>\n")
        return "".join(html_parts)

    processed_directories = []
    processed_files = []

    for entry_name in entries:
        if entry_name.startswith('.'):
            continue

        entry_full_path = os.path.join(current_dir_path, entry_name)

        is_output_file = False
        if os.path.abspath(entry_full_path) == os.path.abspath(os.path.join(root_folder, output_file_local)) or \
           os.path.abspath(entry_full_path) == os.path.abspath(os.path.join(root_folder, output_file_github)):
            is_output_file = True

        if is_output_file:
            continue

        is_dir = os.path.isdir(entry_full_path)
        is_file = os.path.isfile(entry_full_path)

        if is_dir and entry_name in EXCLUDED_DIRECTORIES:
            continue
        if is_file and entry_name in EXCLUDED_FILES:
            continue

        if is_dir:
            processed_directories.append(entry_name)
        # --- 修改部分 ---
        # 允许.html和.pdf文件
        elif is_file and entry_name.endswith(('.html', '.pdf')):
        # --- 结束修改 ---
            processed_files.append(entry_name)


    # 对顶层目录应用自定义排序
    if is_top_level:
        ordered_dirs_final = []
        other_dirs_final = []

        predefined_set = set(PREDEFINED_ORDER)
        found_predefined = {dirname: False for dirname in PREDEFINED_ORDER}

        for dirname in processed_directories:
            if dirname in predefined_set:
                found_predefined[dirname] = True
            else:
                other_dirs_final.append(dirname)

        for dirname_in_order in PREDEFINED_ORDER:
            if found_predefined[dirname_in_order]:
                ordered_dirs_final.append(dirname_in_order)

        processed_directories = ordered_dirs_final + other_dirs_final


    # 首先列出子目录
    for dir_name in processed_directories:
        dir_full_path = os.path.join(current_dir_path, dir_name)
        escaped_dir_name = html.escape(dir_name)

        html_parts.append("  <li>\n")
        html_parts.append(f"    <details>\n")
        html_parts.append(f"      <summary><strong>{escaped_dir_name}/</strong></summary>\n")
        html_parts.append(generate_html_for_directory(dir_full_path, root_path_for_links, is_top_level=False, base_url_prefix=base_url_prefix))
        html_parts.append(f"    </details>\n")
        html_parts.append("  </li>\n")

    # 然后列出文件
    for file_name in processed_files:
        file_full_path = os.path.join(current_dir_path, file_name)
        relative_link_path_segment = os.path.relpath(file_full_path, root_path_for_links).replace(os.sep, '/')

        final_link_href = ""
        if base_url_prefix:
            final_link_href = urllib.parse.urljoin(base_url_prefix, relative_link_path_segment)
        else:
            final_link_href = relative_link_path_segment

        escaped_file_name = html.escape(file_name)

        indent = "  "
        html_parts.append(f'{indent}<li><a href="{final_link_href}">{escaped_file_name}</a></li>\n')

    html_parts.append("</ul>\n")

    return "".join(html_parts)

def build_full_html_page(title_display_path, directory_listing_html_content, for_github=False):
    """构建完整的HTML页面字符串"""
    h1_text = f"Index"
    if for_github:
        h1_text = f"Index (<a href='{GITHUB_BASE_URL}' target='_blank'>{html.escape(GITHUB_BASE_URL)}</a>)"
        if title_display_path != GITHUB_BASE_URL.strip('/'):
            root_folder_name = os.path.basename(os.path.abspath(root_folder))
            if root_folder_name :
                 h1_text += f" {html.escape(root_folder_name)}/"


    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Directory Index</title>
  <style>
    body {{ font-family: sans-serif; margin: 20px; }}
    ul {{ list-style-type: none; padding-left: 0; }}
    li {{ margin-bottom: 5px; }}
    details {{ margin-left: 20px; border-left: 1px solid #eee; padding-left: 10px; }}
    details summary {{ cursor: pointer; outline: none; }}
    details summary:hover {{ color: #007bff; }}
    details summary strong {{ font-weight: normal; }}
    details summary > strong {{ font-weight: bold; }}
    details > ul {{ padding-left: 20px; margin-top: 5px; }}
    a {{ text-decoration: none; color: #0066cc; }}
    a:hover {{ text-decoration: underline; }}
    h1 {{ border-bottom: 1px solid #ccc; padding-bottom: 10px; }}
    h1 a {{ color: inherit; text-decoration: none; }}
    h1 a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>{h1_text}</h1>
{directory_listing_html_content}
</body>
</html>
'''

# --- 主程序开始 ---

# 1. 生成 indexLocal.html (本地链接)
print(f"Generating '{output_file_local}' with local links...")
local_dir_listing_html = generate_html_for_directory(
    current_dir_path=root_folder,
    root_path_for_links=root_folder,
    is_top_level=True,
    base_url_prefix=""
)
full_local_html = build_full_html_page(
    title_display_path=os.path.abspath(root_folder),
    directory_listing_html_content=local_dir_listing_html
)
try:
    with open(os.path.join(root_folder, output_file_local), 'w', encoding='utf-8') as f:
        f.write(full_local_html)
    print(f"'{output_file_local}' generated successfully in '{os.path.abspath(root_folder)}'.")
except IOError as e:
    print(f"Error writing file '{output_file_local}': {e}")

print("-" * 30)

# 2. 生成 index.html (GitHub Pages 链接)
print(f"Generating '{output_file_github}' with GitHub Pages links ({GITHUB_BASE_URL})...")
github_dir_listing_html = generate_html_for_directory(
    current_dir_path=root_folder,
    root_path_for_links=root_folder,
    is_top_level=True,
    base_url_prefix=GITHUB_BASE_URL
)
full_github_html = build_full_html_page(
    title_display_path=GITHUB_BASE_URL.strip('/'),
    directory_listing_html_content=github_dir_listing_html,
    for_github=True
)
try:
    with open(os.path.join(root_folder, output_file_github), 'w', encoding='utf-8') as f:
        f.write(full_github_html)
    print(f"'{output_file_github}' generated successfully in '{os.path.abspath(root_folder)}'.")
except IOError as e:
    print(f"Error writing file '{output_file_github}': {e}")