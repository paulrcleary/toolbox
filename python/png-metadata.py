from PIL import Image

data = Image.open("file_path.png")

image = data.info['parameters'] 

print(image)