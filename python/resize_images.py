import os
from PIL import Image

def resize_images_in_directory(directory, resize_percentage):
  """
  Resizes all images in a directory by a given percentage.

  Args:
    directory: The path to the directory containing the images.
    resize_percentage: The percentage to resize the images by.
  """

  # Confirmation prompt before starting the resizing process
  confirm = input(f"Resize all images in {directory} by {resize_percentage}%? (yes/no): ").lower()
  if confirm != 'yes':
    print("Resizing aborted.")
    return

  for filename in os.listdir(directory):
    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):  # Check for common image extensions
      image_path = os.path.join(directory, filename)
      
      try:
        resized_image = resize_image(image_path, resize_percentage)
        resized_image.save(image_path)  # Overwrite the original image
        print(f"Resized: {filename}")
      except Exception as e:
        print(f"Error resizing {filename}: {e}")

def resize_image(image_path, resize_percentage):
  """
  Resizes a single image by a given percentage.

  Args:
    image_path: The path to the image file.
    resize_percentage: The percentage to resize the image by.

  Returns:
    The resized image object.
  """

  image = Image.open(image_path)
  width, height = image.size
  new_width = int(width * resize_percentage / 100)
  new_height = int(height * resize_percentage / 100)
  resized_image = image.resize((new_width, new_height))
  return resized_image

# Example usage:
image_directory = "path/to/your/image/directory"  # Replace with your directory
resize_percentage = 50  # Resize to 50%

resize_images_in_directory(image_directory, resize_percentage)
