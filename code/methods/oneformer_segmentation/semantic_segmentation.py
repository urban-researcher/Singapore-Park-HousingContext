import os
import json
import torch
import cv2
# from PIL import Image
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

from transformers import OneFormerProcessor, OneFormerForUniversalSegmentation
import numpy as np
import argparse

# importing files
from image_to_segmented import segment_images
from segment_to_overlay import image_overlay, generate_class_percentages

def parse_args():
    parser = argparse.ArgumentParser(description="OneFormer Segmentation")
    parser.add_argument(
        "-i", "--input",
        help="Path to input folder containing the images.",
    )
    parser.add_argument(
        "-o", "--output", 
        type=str,
        help="Path to output folder.",
    )
    opt = parser.parse_args()
    return opt

opt = parse_args()

def main():
    # segment_images(opt.input, opt.output)
    # image_overlay(opt.input, opt.output)
    generate_class_percentages(opt.output)

if __name__ == "__main__":
    main()

