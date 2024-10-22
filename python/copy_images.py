import os
import shutil

def main():
    """Prompts the user for file information and copies files to a new subdirectory."""

    # 1. Prompt for the current directory
    while True:
        print(f"Current directory is: {os.path.abspath(os.getcwd())}")
        confirm = input(f"Is this the correct directory? (yes/no): ").lower()
        if confirm == 'yes':
            current_dir = os.path.abspath(os.getcwd())
            break
        elif confirm == 'no':
            current_dir = input("Enter the path to the directory you want to copy from: ")
            if os.path.isdir(current_dir):
                break
            else:
                print("Invalid directory path. Please enter a valid directory.")
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")

    # 2. Get available extensions in the current directory (ensure unique, omit blank)
    available_extensions = []
    seen_extensions = set()  # Keep track of seen extensions

    for f in os.listdir(current_dir):
        if os.path.isfile(os.path.join(current_dir, f)):
            ext = os.path.splitext(f)[1][1:]
            if ext and ext not in seen_extensions:  # Check if ext is not blank
                available_extensions.append(ext)
                seen_extensions.add(ext)

    # 3. Prompt for the desired extension using a numbered list
    print("Which extension do you want to use?")
    print("Availabel extensions are:")
    for i, ext in enumerate(available_extensions):
        print(f"{i+1}. {ext}")

    while True:
        try:
            chosen_index = int(input(f"Enter the number of the desired extension: ")) - 1
            if 0 <= chosen_index < len(available_extensions):
                chosen_extension = available_extensions[chosen_index]
                print(f"You have chosen: {chosen_extension}")
                break
            else:
                print("Invalid choice. Please enter a number from the list.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    # 4. Get the list of file numbers from the user
    while True:
        file_numbers_str = input("Enter file numbers separated by commas (e.g., 1,3,5): ")
        # Remove any trailing commas before splitting
        file_numbers_str = file_numbers_str.rstrip(',') 
        try:
            # Split by commas and convert to integers
            file_numbers = [int(x.strip()) for x in file_numbers_str.split(',')]
            break
        except ValueError:
            print("Invalid input. Please enter numbers separated by commas.")

    # 5. Check if there is a prefix for the file names
    prefix = None
    while True:
        confirm = input(f"Are there any prefixes for the file names? (yes/no): ").lower()
        if confirm == 'no':
            break
        elif confirm == 'yes':
            prefix = input("What is the prefix for the file names?: ")
            print(f"You have provided: {prefix}")
            break
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")


    # 6. Prompt for the new subdirectory name
    new_dir_name = input("Enter the name for the new subdirectory: ")
    print(f"You have provided: {new_dir_name}")


    # 7. Create the new subdirectory within the chosen directory
    new_dir_path = os.path.join(current_dir, new_dir_name)
    os.makedirs(new_dir_path, exist_ok=True)

    # 8. Copy the selected files
    files_copied = 0
    for number in file_numbers:
        if prefix:
            filename = f"{prefix}{number}.{chosen_extension}"
        else:
            filename = f"{number}.{chosen_extension}"
        source_path = os.path.join(current_dir, filename) 
        destination_path = os.path.join(new_dir_path, filename)

        if os.path.exists(source_path):
            shutil.copy(source_path, destination_path)
            print(f"Copied {filename} to {new_dir_name}")
            files_copied += 1
        else:
            print(f"File not found: {filename}")
    print(f"Total files copied: {files_copied} \n\n Done!")

if __name__ == "__main__":
    main()
