import os


def strip_comments_from_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        in_multiline_string = False
        quote_char = None

        for line in lines:
            stripped = line.strip()

            if not in_multiline_string:
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    if stripped.count('"""') == 1 or stripped.count("'''") == 1:
                        in_multiline_string = True
                        quote_char = '"""' if '"""' in stripped else "'''"
                    continue

                if "#" in line:
                    idx = line.find("#")
                    if (
                        line[:idx].count("'") % 2 == 0
                        and line[:idx].count('"') % 2 == 0
                    ):
                        line = line[:idx].rstrip() + "\n"

                if line.strip():
                    new_lines.append(line)
            else:
                if quote_char in stripped:
                    in_multiline_string = False
                continue

        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        print(f"Error processing {filepath}: {e}")


def process_directories(directories):
    for directory in directories:
        for root, dirs, files in os.walk(directory):
            if "__pycache__" in root:
                continue
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    print(f"Processing {filepath}")
                    strip_comments_from_file(filepath)


if __name__ == "__main__":
    target_dirs = ["app", "core", "models", "tools", "feedback"]
    # Also include root files
    process_directories(target_dirs)
    for f in os.listdir("."):
        if f.endswith(".py"):
            print(f"Processing root file {f}")
            strip_comments_from_file(f)
