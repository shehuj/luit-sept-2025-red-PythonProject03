# Check required files
import os
import sys

def check_required_files_os(root_dir, required_files):
    """
    Checks for the presence of required files in a specified root directory
    using the os module.

    Args:
        root_dir (str): The path to the root directory to check.
        required_files (list): A list of strings, where each string is the
                               name of a required file.

    Returns:
        dict: A dictionary where keys are the required file names and values
              are booleans indicating if the file exists (True) or not (False).
    """
    found_status = {}
    for file_name in required_files:
        file_path = os.path.join(root_dir, file_name)
        found_status[file_name] = os.path.isfile(file_path)
    return found_status

# Example usage:
root_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # Or specify a different path like "/path/to/your/project"
files_to_check = [".gitignore", "README.md", "requirements.txt"]

results_os = check_required_files_os(root_directory, files_to_check)
# if file is missing, exit with code 1 and pring missing file
if not all(results_os.values()):
    print("Missing required files:")
    for file, exists in results_os.items():
        if not exists:
            print(f"'{file}'")
    sys.exit(1)
