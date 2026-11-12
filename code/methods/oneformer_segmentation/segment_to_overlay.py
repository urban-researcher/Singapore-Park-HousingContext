import os
import cv2
import numpy as np

import json
import pandas as pd
from collections import defaultdict
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True


# image_overlay is mostly aesthetic function that merges raw image with
# the image segmentation 

def image_overlay(image_folder, output_folder):
        
        segmentation_folder_path = os.path.join(output_folder, "segmented_imgs")
        if os.path.exists(segmentation_folder_path):

            # iterate over the images in the images folder
            for image_name in os.listdir(image_folder):
                # get the image file path and corresponding segmented file path
                image_path = os.path.join(image_folder, image_name)
                segmented_name = os.path.splitext(image_name)[0] + '.png'
                segmentation_path = os.path.join(segmentation_folder_path, segmented_name)


                # load the image and segmented image
                image = cv2.imread(image_path)
                image_segmentation = cv2.imread(segmentation_path)

                # check if both image and image segmentation has been loaded properly
                if image is None or image_segmentation is None:
                    print(f"Failed to load {image_name} or its corresponding image segmentation.")
                    continue

                # Resize image segmentation to match raw image dimensions
                image_segmentation = cv2.resize(image_segmentation, (image.shape[1], image.shape[0]))

                # Apply Alpha blending to overlay image segmentation onto original image
                alpha = 0.4     # Adjust alpha value to desire transparency
                image_overlay = cv2.addWeighted(image, alpha, image_segmentation, 1 - alpha, 0)

                # Save image overlay to output folder
                overlay_folder = output_folder+'/overlay_imgs'
                os.makedirs(overlay_folder, exist_ok=True)
                
                overlay_path = os.path.join(overlay_folder, image_name)
                cv2.imwrite(overlay_path, image_overlay)

                print(f"'{image_name}' overlay saved successfully.") 


        else:
            print("Please check segmented images folder.")

def generate_class_percentages(output_folder):
    json_file='objectName150_colors150.json'
    with open(json_file, 'r') as f:
        json_data = json.load(f)
    class_color_mapping = {
        label['readable']: tuple(label['color'])
        for label in json_data['labels']
    }
    result = []
    filenames = []
    # result = pd.DataFrame()
    
    # Step 2: Process each image
    segmented_path = output_folder +"/segmented_imgs/"
    for image_file in os.listdir(segmented_path):
        if image_file.endswith('.jpg') or image_file.endswith('.png'):
            # Read segmented image
            image_path = os.path.join(segmented_path, image_file)
            image = Image.open(image_path)

            # Step 3: Classify pixels
            pixels = image.load()
            width, height = image.size
            class_counts = defaultdict(int)
            total_pixels = 0
            for y in range(height):
                for x in range(width):
                    pixel_color = tuple(pixels[x,y])
                    for class_name, class_color in class_color_mapping.items():
                        if pixel_color == class_color:
                            # Step 4: Count pixel occurances
                            class_counts[class_name] += 1
                            total_pixels += 1
                            break
            
            # Step 5: Calculate Percentages
            class_percentages = {
                class_name: count / total_pixels * 100
                for class_name, count in class_counts.items()
            }

            filename = image_file.split(".")[0]

            result.append(class_percentages)
            filenames.append(filename)

            # Step 6: Stores results with image title
            # result[image_file] = {
            #     'class_percentages': class_percentages,
            #     'image_path': image_path
            # }
            print(f"'{image_file} percentages saved successfully.")

    # Step 7: Save results to CSV File
    df1 = pd.DataFrame(filenames, columns=['filename'])
    df2 = pd.DataFrame(result)
    df3 = pd.concat([df1, df2], axis=1)
    df3.fillna(0, inplace=True) 
    df3.to_csv(output_folder+"/class_percentages.csv")



    print(f"Done!")


            






