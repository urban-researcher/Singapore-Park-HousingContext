import os
import json
import torch
from PIL import Image
from transformers import OneFormerProcessor, OneFormerForUniversalSegmentation
import numpy as np


def segment_images(image_folder, output_folder):
    # Load Mask2Former fine-tuned on Mapillary Vistas semantic segmentation
    processor = OneFormerProcessor.from_pretrained("shi-labs/oneformer_ade20k_swin_large")
    model = OneFormerForUniversalSegmentation.from_pretrained("shi-labs/oneformer_ade20k_swin_large")

    # processor = OneFormerProcessor.from_pretrained("shi-labs/oneformer_cityscapes_swin_large")
    # model = OneFormerForUniversalSegmentation.from_pretrained("shi-labs/oneformer_cityscapes_swin_large")

    # Load the JSON color map
    # with open("objectName150_colors150.json") as f:
    with open("objectName150_colors150.json") as f:
        color_map_data = json.load(f)

    # Create a mapping between class names and class indices
    class_name_to_index = {}
    for index, label in enumerate(color_map_data["labels"]):
        class_name_to_index[label["name"]] = index

    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Process each image in the input folder
    for filename in os.listdir(image_folder):
        if filename.endswith(".jpg") or filename.endswith(".jpeg") or filename.endswith(".png"):
            image_path = os.path.join(image_folder, filename)
            image = Image.open(image_path).convert("RGB")  # Convert to RGB format
            semantic_inputs = processor(images=image, task_inputs=["semantic"], return_tensors="pt")

            with torch.no_grad():
                semantic_outputs = model(**semantic_inputs)

            # You can pass them to the processor for post-processing
            predicted_semantic_map = processor.post_process_semantic_segmentation(semantic_outputs, target_sizes=[image.size[::-1]])[0]

            # # Apply color mapping to the grayscale segmentation map
            colored_segmentation_map = np.zeros((image.size[1], image.size[0], 3), dtype=np.uint8)
            for label in color_map_data["labels"]:
                class_name = label["name"]
                class_index = class_name_to_index[class_name]
                color = label["color"]
                colored_segmentation_map[predicted_semantic_map == class_index] = color

            # Create a PIL Image from the colored segmentation map
            segmented_image = Image.fromarray(colored_segmentation_map)

            # Save the segmented image with the same filename and "_segmented" suffix in the output folder
            os.makedirs(output_folder+'/segmented_imgs/', exist_ok=True)
            output_path = output_folder+"/segmented_imgs/"
            save_path = os.path.join(output_path, f"{os.path.splitext(filename)[0]}.png")
            segmented_image.save(save_path)

            print(f"Processed image: {filename}, Saved as: {save_path}")


    print(f"done!")


# Specify the input folder path containing the images
# input_images_folder = "input"

# Specify the output folder path for the segmented images
# output_output_folder = "output"

# Call the function to process the images and save the segmented images in the output folder
# process_images(input_images_folder, output_output_folder)



