import os
import shutil
import zipfile


def prep_data(main_folder):
    
    # Directory containing the zip file
    source_dir = './Data'
    # Main folder to be created

    # Path to the main folder
    main_folder_path = os.path.join(source_dir, main_folder)

    # Path to the zip file
    zip_file_path = os.path.join(source_dir, f'{main_folder}.zip')

    # Check if the main folder exists, and if so, delete it
    if os.path.exists(main_folder_path):
        shutil.rmtree(main_folder_path)

    # Unzip the file directly to the source_dir to prevent nested folders with the same name
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(source_dir)

    # Rename the unzipped main folder if it creates an extra unwanted level
    extracted_main_folder_path = os.path.join(source_dir, main_folder)
    if os.path.exists(extracted_main_folder_path) and os.path.isdir(extracted_main_folder_path):
        # List contents to see if there is an unwanted nested structure
        contents = os.listdir(extracted_main_folder_path)
        if len(contents) == 1 and os.path.isdir(os.path.join(extracted_main_folder_path, contents[0])):
            nested_folder_path = os.path.join(extracted_main_folder_path, contents[0])
            # Move contents from nested folder to correct location
            for item in os.listdir(nested_folder_path):
                shutil.move(os.path.join(nested_folder_path, item), extracted_main_folder_path)
            # Remove the now empty nested directory
            os.rmdir(nested_folder_path)

    # Optionally, now move and organize files into their respective folders as needed
    for root, dirs, files in os.walk(extracted_main_folder_path, topdown=False):
        for name in files:
            if name.endswith('.csv'):
                file_path = os.path.join(root, name)
                folder_name = name[:-4]
                new_folder_path = os.path.join(root, folder_name)
                if not os.path.exists(new_folder_path):
                    os.makedirs(new_folder_path)
                shutil.move(file_path, os.path.join(new_folder_path, name))

    print("Files have been organized in nested folders correctly.")


