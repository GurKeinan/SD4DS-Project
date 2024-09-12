from PIL import Image
from gradio_client import Client, file

client = Client("felixrosberg/face-swap")

# Send the images and get the result
result = client.predict(
    target=file("static/image.jpeg"),
    source=file("static/image1.jpeg"),
    slider=100,
    adv_slider=100,
    settings=["Adversarial Defense"],
    api_name="/run_inference"
)

# Temporary path to the result (which is in .webp format)
temp_result_path = result  # Path like "/private/var/.../image.webp"

# Open the .webp image using Pillow
image = Image.open(temp_result_path)

# Save the image as .jpeg
jpeg_save_path = "static/swapped_face_result.jpg"
image.save(jpeg_save_path, "JPEG")

print(f"Image saved as {jpeg_save_path}")