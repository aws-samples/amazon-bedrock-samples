"""
Comprehensive utility file for Amazon Bedrock Data Automation Object Detection.
This file provides utilities for video processing, object detection, and business-friendly visualization.
"""

import boto3
import json
import uuid
import time
import os
import matplotlib.pyplot as plt
from datetime import datetime
from IPython.display import Video, clear_output, HTML, display, Markdown
from moviepy.video.io.VideoFileClip import VideoFileClip
import numpy as np
import pandas as pd
import seaborn as sns
from wordcloud import WordCloud
from collections import Counter
import matplotlib.cm as cm
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patches as patches
import sagemaker

class BDAObjectDetectionUtils:
    def __init__(self):
        # Initialize AWS session and clients
        self.session = sagemaker.Session()
        self.current_region = boto3.session.Session().region_name
        
        self.sts = boto3.client('sts')
        self.account_id = self.sts.get_caller_identity()['Account']
        
        # Initialize BDA clients
        self.bda_client = boto3.client('bedrock-data-automation')
        self.bda_runtime_client = boto3.client('bedrock-data-automation-runtime')
        self.s3_client = boto3.client('s3')
        
        # Define bucket name using workshop convention
        self.bucket_name = f"bda-workshop-{self.current_region}-{self.account_id}"
        
        # Define S3 locations
        self.data_prefix = "bda-workshop/video"
        self.output_prefix = "bda-workshop/video/output"
        
        # Create bucket if it doesn't exist
        self.create_bucket_if_not_exists()
    
    def download_video(self, url, output_path):
        """
        Download a video from a URL with enhanced error handling.
        
        Args:
            url (str): URL of the video to download
            output_path (str): Local path to save the video
            
        Returns:
            str: Path to the downloaded video
        """
        try:
            # Create directories if needed
            dir_name = os.path.dirname(output_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
                
            # Try using curl command which has better SSL handling
            try:
                import subprocess
                result = subprocess.run(['curl', '-s', '-L', '-o', output_path, url], check=True)
                print(f"Downloaded {url} to {output_path}")
                return output_path
            except (subprocess.CalledProcessError, ImportError):
                # Fall back to requests if curl fails
                import requests
                response = requests.get(url, timeout=30)
                response.raise_for_status()  # Raise an exception for HTTP errors
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"Downloaded {url} to {output_path}")
                return output_path
        except Exception as e:
            print(f"Error downloading video: {e}")
            raise
    
    def create_bucket_if_not_exists(self):
        """Create S3 bucket if it doesn't exist for storing videos and processing results."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            print(f"Bucket {self.bucket_name} already exists")
        except:
            print(f"Creating bucket: {self.bucket_name}")
            if self.current_region == 'us-east-1':
                self.s3_client.create_bucket(Bucket=self.bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=self.bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.current_region}
                )
            print(f"Bucket {self.bucket_name} created successfully")
    
    def upload_to_s3(self, local_path, s3_key):
        """
        Upload a local file to S3.
        
        Args:
            local_path (str): Local path of the file to upload
            s3_key (str): S3 key where the file should be stored
            
        Returns:
            str: S3 URI of the uploaded file
        """
        self.s3_client.upload_file(local_path, self.bucket_name, s3_key)
        return f's3://{self.bucket_name}/{s3_key}'
    
    def read_json_from_s3(self, s3_uri):
        """
        Read and parse a JSON file from S3.
        
        Args:
            s3_uri (str): S3 URI of the JSON file
            
        Returns:
            dict: Parsed JSON content
        """
        bucket, key = self.get_bucket_and_key(s3_uri)
        response = self.s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')
        return json.loads(content)
    
    def get_bucket_and_key(self, s3_uri):
        """
        Extract bucket and key from an S3 URI.
        
        Args:
            s3_uri (str): S3 URI (e.g. s3://bucket-name/path/to/file)
            
        Returns:
            tuple: (bucket_name, key)
        """
        path_parts = s3_uri.replace("s3://", "").split("/")
        bucket = path_parts[0]
        key = "/".join(path_parts[1:])
        return bucket, key
    
    def delete_s3_folder(self, prefix):
        """
        Delete a folder and its contents from S3.
        
        Args:
            prefix (str): Prefix (folder path) to delete
        """
        objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
        if 'Contents' in objects:
            for obj in objects['Contents']:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=obj['Key'])
    
    def wait_for_completion(self, get_status_function, status_kwargs, completion_states, 
                           error_states, status_path_in_response, max_iterations=15, delay=10):
        """
        Wait for an asynchronous operation to complete.
        
        Args:
            get_status_function: Function to call to check status
            status_kwargs: Arguments to pass to the status function
            completion_states: List of states indicating completion
            error_states: List of states indicating error
            status_path_in_response: Path to status in the response
            max_iterations: Maximum number of status checks
            delay: Seconds to wait between status checks
            
        Returns:
            dict: Final response
        """
        for i in range(max_iterations):
            response = get_status_function(**status_kwargs)
            
            # Extract status from response using the provided path
            status = response
            for key in status_path_in_response.split('.'):
                status = status.get(key, {})
            
            print(f"Current status: {status}")
            
            if status in completion_states:
                print(f"Process completed with status: {status}")
                return response
            elif status in error_states:
                print(f"Process failed with status: {status}")
                return response
            
            print(f"Waiting {delay} seconds...")
            time.sleep(delay)
        
        print(f"Maximum iterations reached. Last status: {status}")
        return response
    
    def generate_shot_images(self, video_path, result_data, image_width=120):
        """
        Generate images for each shot in the video.
        
        Args:
            video_path (str): Path to the video file
            result_data (dict): BDA results data
            image_width (int): Width of the generated images
            
        Returns:
            list: List of (timestamp, image) tuples
        """
        images = []
        
        # Load the video
        clip = VideoFileClip(video_path)
        
        # Extract shots
        shots = result_data.get("shots", [])
        
        # Generate an image for each shot
        for shot in shots:
            start_time = shot["start_timestamp_millis"] / 1000  # Convert to seconds
            frame = clip.get_frame(start_time)
            images.append((start_time, frame))
        
        clip.close()
        return images
    
    def plot_shots(self, images):
        """
        Plot shot images in a grid with enhanced visualization.
        
        Args:
            images: List of (timestamp, image) tuples
        """
        if not images:
            print("No shots to display")
            return
        
        # Calculate grid dimensions
        n_images = len(images)
        cols = 5
        rows = (n_images + cols - 1) // cols
        
        # Create figure with improved styling
        plt.figure(figsize=(15, rows * 3))
        
        # Plot each image with enhanced annotations
        for i, (time, img) in enumerate(images):
            plt.subplot(rows, cols, i + 1)
            plt.imshow(img)
            plt.title(f"Shot {i+1}: {time:.2f}s", fontsize=10, fontweight='bold')
            
            # Add subtle border to highlight the shot
            plt.gca().spines['bottom'].set_color('#1f77b4')
            plt.gca().spines['top'].set_color('#1f77b4')
            plt.gca().spines['right'].set_color('#1f77b4')
            plt.gca().spines['left'].set_color('#1f77b4')
            plt.gca().spines['bottom'].set_linewidth(2)
            plt.gca().spines['top'].set_linewidth(2)
            plt.gca().spines['right'].set_linewidth(2)
            plt.gca().spines['left'].set_linewidth(2)
            
            plt.axis('off')
        
        plt.suptitle(f"Video Shot Analysis: {n_images} Distinct Visual Segments Detected", fontsize=16)
        plt.tight_layout()
        plt.subplots_adjust(top=0.95)  # Add room for the title
        plt.show()
        
        print("This capability enables precise navigation, content indexing, and context-aware understanding of your video.")
    
    def plot_content_moderation(self, video_path, result_data, chapter_index):
        """
        Plot frames with content moderation labels with enhanced visualization.
        
        Args:
            video_path (str): Path to the video file
            result_data (dict): BDA results data
            chapter_index (int): Index of the chapter to analyze
        """
        if chapter_index >= len(result_data["chapters"]):
            print(f"Chapter index {chapter_index} out of range")
            return
        
        chapter = result_data["chapters"][chapter_index]
        clip = VideoFileClip(video_path)
        
        moderation_frames = []
        
        for frame in chapter.get("frames", []):
            if "content_moderation" in frame:
                # Get frame time
                frame_time = frame["timestamp_millis"] / 1000
                
                # Get frame image
                frame_img = clip.get_frame(frame_time)
                
                # Get moderation categories
                categories = []
                confidences = []
                
                for mod in frame["content_moderation"]:
                    categories.append(mod["category"])
                    confidences.append(float(mod["confidence"]))
                
                moderation_frames.append((frame_time, frame_img, categories, confidences))
        
        clip.close()
        
        if not moderation_frames:
            print("No content moderation data found in this chapter")
            return
        
        # Create a more sophisticated visualization
        for frame_time, frame_img, categories, confidences in moderation_frames:
            plt.figure(figsize=(15, 6))
            
            # Left: Plot the video frame
            plt.subplot(1, 2, 1)
            plt.imshow(frame_img)
            plt.title(f"Frame at {frame_time:.2f}s", fontweight='bold')
            plt.axis('off')
            
            # Right: Plot content moderation data with improved styling
            ax = plt.subplot(1, 2, 2)
            bars = plt.barh(categories, confidences, color='#FF9999')
            
            # Add threshold line
            plt.axvline(x=0.5, color='red', linestyle='--', alpha=0.7)
            plt.text(0.51, -0.5, 'Risk Threshold (0.5)', color='red', fontsize=9)
            
            # Highlight bars exceeding threshold
            for i, confidence in enumerate(confidences):
                if confidence > 0.5:
                    bars[i].set_color('#FF3333')
                    plt.text(confidence + 0.02, i, f"{confidence:.2f}", va='center', fontweight='bold')
                else:
                    plt.text(confidence + 0.02, i, f"{confidence:.2f}", va='center')
            
            plt.title("Content Moderation Analysis", fontweight='bold')
            plt.xlabel("Confidence Score")
            plt.xlim(0, 1.1)
            plt.grid(axis='x', linestyle='--', alpha=0.3)
            
            plt.tight_layout()
            plt.show()
            
        print("This powerful moderation capability helps ensure content safety and compliance.")
    
    def visualize_chapters(self, result_data, figsize=(14, 6)):
        """
        Visualize chapters timeline with summaries.
        
        Args:
            result_data (dict): BDA results data
            figsize (tuple): Figure size
        """
        if "chapters" not in result_data or not result_data["chapters"]:
            print("No chapter data available for visualization")
            return
            
        chapters = result_data["chapters"]
        
        # Create figure
        plt.figure(figsize=figsize)
        
        # Calculate chapter durations and positions
        total_duration = 0
        for chapter in chapters:
            start = chapter.get("start_timestamp_millis", 0) / 1000  # in seconds
            end = chapter.get("end_timestamp_millis", 0) / 1000
            if end > total_duration:
                total_duration = end
                
        # Create color palette for chapters
        colors = plt.cm.viridis(np.linspace(0, 0.9, len(chapters)))
        
        # Plot chapters as segments on a timeline
        y_pos = 0
        for i, chapter in enumerate(chapters):
            start = chapter.get("start_timestamp_millis", 0) / 1000  # in seconds
            end = chapter.get("end_timestamp_millis", 0) / 1000
            duration = end - start
            width = duration / total_duration
            
            # Plot chapter bar
            plt.barh(y_pos, width, left=start/total_duration, height=0.6, color=colors[i], alpha=0.7)
            
            # Add chapter label
            plt.text(start/total_duration + width/2, y_pos, f"Ch.{i+1}", 
                    ha='center', va='center', color='white', fontweight='bold')
            
            # Plot start/end times
            plt.text(start/total_duration, y_pos+0.5, f"{start:.1f}s", ha='center', va='bottom', fontsize=8)
            plt.text(min((start/total_duration + width), 0.98), y_pos+0.5, f"{end:.1f}s", ha='center', va='bottom', fontsize=8)
        
        # Configure plot
        plt.yticks([])
        plt.xticks([])
        plt.xlim(0, 1)
        plt.ylim(-0.5, 1)
        plt.title("Video Chapter Structure", fontweight='bold')
        
        # Add chapter summaries table below
        plt.figtext(0.5, -0.05, "Chapter summaries:", ha='center', fontsize=12, fontweight='bold')
        for i, chapter in enumerate(chapters):
            summary = chapter.get("summary", "No summary available")
            if len(summary) > 100:
                summary = summary[:100] + "..."
            plt.figtext(0.5, -0.15 - (i*0.07), f"Chapter {i+1}: {summary}", ha='center', fontsize=9)
        
        plt.tight_layout()
        
        # Adjust figure size to accommodate summaries
        fig = plt.gcf()
        fig.subplots_adjust(bottom=0.1 + (len(chapters) * 0.07))
        
        plt.show()
        
        print(f"\n BDA automatically divided the video into {len(chapters)} meaningful chapters!")
        print("This capability enables semantic understanding, improved navigation, and content structuring.")
    
    def visualize_iab_categories(self, result_data):
        """
        Visualize IAB categories detected in the video.
        
        Args:
            result_data (dict): BDA results data
        """
        if "chapters" not in result_data or not result_data["chapters"]:
            print("No chapter data available for IAB visualization")
            return
            
        # Collect all IAB categories
        category_counts = {}
        
        for chapter in result_data["chapters"]:
            if "iab_categories" in chapter:
                for iab in chapter["iab_categories"]:
                    category = iab["category"]
                    confidence = float(iab.get("confidence", 0))
                    
                    if confidence > 0.5:  # Only count high-confidence categories
                        if category in category_counts:
                            category_counts[category] += 1
                        else:
                            category_counts[category] = 1
        
        if not category_counts:
            print("No IAB categories detected with confidence > 0.5")
            return
            
        # Sort categories by count
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        categories = [x[0] for x in sorted_categories]
        counts = [x[1] for x in sorted_categories]
        
        # Create visualization
        plt.figure(figsize=(10, 6))
        
        # Create horizontal bars for better readability of category names
        colors = plt.cm.tab20c(np.linspace(0, 1, len(categories)))
        bars = plt.barh(categories, counts, color=colors)
        
        # Add count labels
        for bar in bars:
            width = bar.get_width()
            plt.text(width + 0.1, bar.get_y() + bar.get_height()/2, 
                    f"{int(width)}", ha='left', va='center')
        
        plt.title("Internet Advertising Bureau (IAB) Categories Detected", fontweight='bold')
        plt.xlabel("Number of Occurrences")
        plt.tight_layout()
        plt.show()
        
        print("\n BDA automatically classified your video content into IAB categories!")
        print("This enables improved content discovery, ad targeting, and content recommendations.")

    # NEW METHOD: Visualize objects with bounding boxes
    def visualize_objects_with_bounding_boxes(self, video_path, result_data, chapter_index, confidence_threshold=0.5):
        """
        Visualize detected objects with bounding boxes for a specific chapter.
        
        Args:
            video_path (str): Path to the video file
            result_data (dict): BDA results data
            chapter_index (int): Index of the chapter to analyze
            confidence_threshold (float): Minimum confidence threshold for displaying objects
        """
        if chapter_index >= len(result_data["chapters"]):
            print(f"Chapter index {chapter_index} out of range")
            return
        
        chapter = result_data["chapters"][chapter_index]
        
        # Check if chapter has frames
        if "frames" not in chapter:
            print("No frames data found in this chapter")
            return
        
        # Find a frame with object detection data
        target_frame = None
        for frame in chapter["frames"]:
            if "inference_result" in frame and "targeted-object-detection" in frame["inference_result"]:
                if frame["inference_result"]["targeted-object-detection"]:
                    target_frame = frame
                    break
        
        if not target_frame:
            print("No objects detected in this chapter")
            return
        
        # Get detected objects for this specific frame only
        detected_objects = target_frame["inference_result"]["targeted-object-detection"]
        
        # Get frame timestamp
        frame_time = target_frame.get("timestamp_millis", 0) / 1000  # Convert to seconds
        
        # Load the video
        clip = VideoFileClip(video_path)
        
        # Extract frame
        frame = clip.get_frame(frame_time)
        height, width = frame.shape[0], frame.shape[1]
        
        # Create figure for visualization
        plt.figure(figsize=(12, 8))
        
        # Display the frame
        plt.imshow(frame)
        
        # Create a colormap for confidence levels
        cmap = plt.cm.RdYlGn  # Red (low confidence) to Green (high confidence)
        
        # Track objects for legend
        legend_entries = {}
        
        # Draw bounding boxes for each detected object
        objects_above_threshold = 0
        for obj in detected_objects:
            # Check if object has the expected structure
            if isinstance(obj, dict) and "label" in obj and "bounding_box" in obj and "confidence" in obj:
                label = obj["label"]
                confidence = obj["confidence"]
                bbox = obj["bounding_box"]
                
                # Skip if below confidence threshold
                if confidence < confidence_threshold:
                    continue
                    
                objects_above_threshold += 1
                
                # Extract bounding box coordinates
                # BDA returns normalized coordinates (0-1)
                x = bbox["left"] * width
                y = bbox["top"] * height
                w = bbox["width"] * width
                h = bbox["height"] * height
                
                # Create rectangle with color based on confidence
                color = cmap(confidence)
                rect = patches.Rectangle((x, y), w, h, linewidth=2, edgecolor=color, facecolor='none')
                
                # Add rectangle to plot
                plt.gca().add_patch(rect)
                
                # Add label with confidence score
                plt.text(x, y-5, f"{label} ({confidence:.2f})", 
                         color='white', fontsize=10, fontweight='bold',
                         bbox=dict(facecolor=color, alpha=0.8, boxstyle='round,pad=0.2'))
                
                # Add to legend entries
                if label not in legend_entries:
                    legend_entries[label] = confidence
        
        # Add legend for object types
        if legend_entries:
            # Sort by confidence
            sorted_entries = sorted(legend_entries.items(), key=lambda x: x[1], reverse=True)
            legend_patches = [patches.Patch(color=cmap(conf), label=f"{label} ({conf:.2f})") 
                             for label, conf in sorted_entries]
            plt.legend(handles=legend_patches, loc='upper right', title="Detected Objects")
        
        plt.title(f"Object Detection - Chapter {chapter_index+1} at {frame_time:.2f}s", fontsize=16)
        plt.axis('off')
        plt.tight_layout()
        plt.show()
        
        # Close the video clip
        clip.close()
        
        print(f"\nBDA detected {objects_above_threshold} objects with precise bounding boxes!")
        print("Bounding boxes enable pixel-perfect object localization for advanced video analytics.")
    
    # NEW METHOD: Get frame with bounding boxes for a specific timestamp
    def get_frame_with_bounding_boxes(self, video_path, result_data, timestamp, confidence_threshold=0.5):
        """
        Get a video frame with detected objects highlighted using bounding boxes.
        
        Args:
            video_path (str): Path to the video file
            result_data (dict): BDA results data
            timestamp (float): Timestamp in seconds
            confidence_threshold (float): Minimum confidence threshold for displaying objects
            
        Returns:
            tuple: (frame with bounding boxes, list of detected objects)
        """
        # Find the chapter containing the timestamp
        target_chapter = None
        for chapter in result_data.get("chapters", []):
            start_time = chapter.get("start_timestamp_millis", 0) / 1000  # Convert to seconds
            end_time = chapter.get("end_timestamp_millis", 0) / 1000  # Convert to seconds
            
            if start_time <= timestamp <= end_time:
                target_chapter = chapter
                break
        
        if not target_chapter:
            print(f"No chapter found containing timestamp {timestamp}s")
            return None, []
        
        # Check if chapter has frames
        if "frames" not in target_chapter:
            print("No frames data found in this chapter")
            return None, []
        
        # Find the closest frame to the timestamp and get its objects
        closest_frame = None
        min_diff = float('inf')
        
        for frame in target_chapter["frames"]:
            frame_time = frame.get("timestamp_millis", 0) / 1000
            diff = abs(frame_time - timestamp)
            if diff < min_diff:
                min_diff = diff
                closest_frame = frame
        
        if not closest_frame:
            print("No frames found in this chapter")
            return None, []
            
        # Get detected objects
        detected_objects = []
        if ("inference_result" in closest_frame and 
            "targeted-object-detection" in closest_frame["inference_result"]):
            detected_objects = closest_frame["inference_result"]["targeted-object-detection"]
        
        # Load the video and get the frame
        clip = VideoFileClip(video_path)
        frame = clip.get_frame(timestamp)
        height, width = frame.shape[0], frame.shape[1]
        clip.close()
        
        # Create a copy of the frame for drawing
        import cv2
        frame_rgb = frame.copy()
        
        # Create a colormap for confidence levels
        colors = plt.cm.RdYlGn(np.linspace(0, 1, 10))  # 10 colors from red to green
        colors = (colors[:, :3] * 255).astype(np.uint8)  # Convert to RGB 0-255
        
        # Objects to return
        objects_with_confidence = []
        
        # Draw bounding boxes
        for obj in detected_objects:
            # Check if object has the expected structure
            if isinstance(obj, dict) and "label" in obj and "bounding_box" in obj and "confidence" in obj:
                label = obj["label"]
                confidence = obj["confidence"]
                bbox = obj["bounding_box"]
                
                # Skip if below threshold
                if confidence < confidence_threshold:
                    continue
                
                # Track object
                objects_with_confidence.append({
                    "label": label,
                    "confidence": confidence,
                    "bounding_box": bbox
                })
                
                # Extract bounding box coordinates (normalized to pixels)
                x = int(bbox["left"] * width)
                y = int(bbox["top"] * height)
                w = int(bbox["width"] * width)
                h = int(bbox["height"] * height)
                
                # Get color based on confidence
                color_idx = min(int(confidence * 10) - 1, 9)  # Map confidence to color index
                color = tuple(map(int, colors[color_idx]))  # RGB tuple
                
                # Draw rectangle
                cv2.rectangle(frame_rgb, (x, y), (x + w, y + h), color, 2)
                
                # Create label text
                label_text = f"{label}: {confidence:.2f}"
                
                # Get text size
                text_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                
                # Draw text background
                cv2.rectangle(frame_rgb, (x, y - text_size[1] - 5), (x + text_size[0], y), color, -1)
                
                # Draw text
                cv2.putText(frame_rgb, label_text, (x, y - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame_rgb, objects_with_confidence

    # Enhanced Object Detection Visualization Functions
    def create_object_search_function(self, result_data):
        """
        Create and return a function to search for objects in the video.
        
        Args:
            result_data (dict): BDA results data
            
        Returns:
            function: Function to search for objects
        """
        def search_video_objects(search_term, confidence_threshold=0.5):
            """Search for objects in the video"""
            print(f"Searching for '{search_term}' in video...")
            found_objects = []
            
            for chapter_idx, chapter in enumerate(result_data.get("chapters", [])):
                if "frames" not in chapter:
                    continue
                    
                for frame in chapter["frames"]:
                    if "inference_result" in frame and "targeted-object-detection" in frame["inference_result"]:
                        objects = frame["inference_result"]["targeted-object-detection"]
                        
                        # Filter objects that match the search term
                        for obj in objects:
                            if isinstance(obj, dict) and "label" in obj and search_term.lower() in obj["label"].lower():
                                if obj.get("confidence", 0) >= confidence_threshold:
                                    found_objects.append({
                                        "chapter": chapter_idx + 1,
                                        "time": frame.get("timestamp_millis", 0) / 1000,
                                        "object": obj
                                    })
            
            if not found_objects:
                print(f"No objects matching '{search_term}' found in the video.")
                return
            
            print(f"Found {len(found_objects)} instances of '{search_term}' in the video:")
            for i, obj in enumerate(found_objects):
                print(f"{i+1}. Chapter {obj['chapter']} at {obj['time']:.2f}s - " +
                     f"Confidence: {obj['object']['confidence']:.2f}")
                  
        return search_video_objects
        
    def display_video_level_insights(self, result_data):
        """
        Display comprehensive video-level insights from BDA analysis using a business-friendly approach.
        
        Args:
            result_data: The BDA video analysis results JSON
        """
        # Extract video-level insights
        inference_result = result_data.get("inference_result", {})
        
        # Create styled header
        display(HTML("""
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #007bff; margin-bottom: 20px;">
                <h2 style="color: #007bff; margin-top: 0;">Video Content Analysis Summary</h2>
                <p style="font-style: italic; color: #6c757d;">Analyzing video content and metadata using Amazon Bedrock Data Automation</p>
            </div>
        """))
        
        # 1. Content Type and Genre
        display(HTML("""
            <div style="margin-bottom: 15px;">
                <h3 style="color: #343a40;">📹 Content Classification</h3>
            </div>
        """))
        
        video_type = inference_result.get("video-type", "Unknown")
        genre = inference_result.get("genre", "Unknown")
        
        # Create a styled classification display
        display(HTML(f"""
            <div style="display: flex; margin-bottom: 20px;">
                <div style="flex: 1; background-color: #e9ecef; padding: 15px; border-radius: 8px; margin-right: 10px; text-align: center;">
                    <h4>Content Type</h4>
                    <p style="font-size: 18px; font-weight: bold; color: #007bff;">{video_type}</p>
                </div>
                <div style="flex: 1; background-color: #e9ecef; padding: 15px; border-radius: 8px; text-align: center;">
                    <h4>Genre</h4>
                    <p style="font-size: 18px; font-weight: bold; color: #007bff;">{genre}</p>
                </div>
            </div>
        """))
        
        # 2. Content Keywords
        if "keywords" in inference_result and inference_result["keywords"]:
            keywords = inference_result["keywords"]
            
            display(HTML("""
                <div style="margin-bottom: 15px;">
                    <h3 style="color: #343a40;">🔑 Content Keywords</h3>
                    <p>Key themes and elements identified across the video:</p>
                </div>
            """))
            
            # Generate wordcloud of keywords
            if len(keywords) > 0:
                # Create word cloud
                wordcloud = WordCloud(
                    width=800, 
                    height=400, 
                    background_color='white',
                    colormap='viridis',
                    max_words=100
                ).generate(' '.join(keywords))
                
                plt.figure(figsize=(10, 5))
                plt.imshow(wordcloud, interpolation='bilinear')
                plt.axis("off")
                plt.title("Content Keywords Analysis", fontsize=16, pad=20)

    def analyze_chapter_objects(self, result_data):
        """
        Analyze and visualize object detection across video chapters.
        
        Args:
            result_data: The BDA video analysis results JSON
        """
        display(HTML("""
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #28a745; margin-bottom: 20px;">
                <h2 style="color: #28a745; margin-top: 0;">Object Detection Analysis</h2>
                <p style="font-style: italic; color: #6c757d;">Analyzing objects detected across video chapters</p>
            </div>
        """))
        
        # Collect all objects from frames in each chapter
        all_objects = []
        chapter_objects = {}
        
        for i, chapter in enumerate(result_data.get("chapters", [])):
            chapter_idx = i + 1
            chapter_name = f"Chapter {chapter_idx}"
            chapter_objects[chapter_name] = []
            
            if "frames" not in chapter:
                continue
            
            for frame in chapter["frames"]:
                if "inference_result" in frame and "targeted-object-detection" in frame["inference_result"]:
                    objects = frame["inference_result"]["targeted-object-detection"]
                    frame_time = frame.get("timestamp_millis", 0) / 1000  # Convert to seconds
                    
                    for obj in objects:
                        if isinstance(obj, dict) and "label" in obj and "confidence" in obj:
                            # Add to objects list
                            all_objects.append({
                                "label": obj["label"],
                                "chapter": chapter_name,
                                "time": frame_time,
                                "confidence": obj["confidence"]
                            })
                            
                            # Add to chapter-specific list
                            chapter_objects[chapter_name].append(obj["label"])
        
        if not all_objects:
            display(HTML("""
                <div style="padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
                    <p>No object detection results found in any chapter frames.</p>
                </div>
            """))
            return
            
        display(HTML("""
            <div style="margin-bottom: 15px;">
                <h3 style="color: #343a40;">🎯 Object Detection Results</h3>
                <p>Objects detected across video chapters:</p>
            </div>
        """))
            
        # Create DataFrame for analysis
        df = pd.DataFrame(all_objects)
        
        # Count object occurrences by chapter
        object_counts = df.groupby(['label', 'chapter']).size().unstack(fill_value=0)
        
        # Show objects that appear in multiple chapters
        multi_chapter_objects = object_counts[object_counts.sum(axis=1) > 1]
        
        if not multi_chapter_objects.empty:
            plt.figure(figsize=(12, max(3, len(multi_chapter_objects)/3 + 2)))
            sns.heatmap(multi_chapter_objects, cmap="YlGnBu", linewidths=.5, cbar_kws={"label": "Occurrences"})
            plt.title("Objects Appearing in Multiple Chapters", fontsize=16)
            plt.ylabel("Object Type", fontsize=12)
            plt.xlabel("Video Chapter", fontsize=12)
            plt.tight_layout()
            plt.show()
            
        # Most common objects
        top_objects = df['label'].value_counts().head(10).reset_index()
        top_objects.columns = ['Object', 'Count']
        
        plt.figure(figsize=(10, 6))
        bars = plt.barh(top_objects['Object'], top_objects['Count'], color=plt.cm.viridis(np.linspace(0, 0.8, len(top_objects))))
        plt.title("Most Frequently Detected Objects", fontsize=16)
        plt.xlabel("Number of Detections", fontsize=12)
        plt.ylabel("Object Type", fontsize=12)
        
        # Add count labels
        for i, bar in enumerate(bars):
            width = bar.get_width()
            plt.text(width + 0.3, i, f"{width}", va='center')
            
        plt.tight_layout()
        plt.show()
        
        # Show object confidence distribution
        plt.figure(figsize=(10, 6))
        
        avg_confidence = df.groupby('label')['confidence'].mean().sort_values(ascending=False).head(10)
        bars = plt.barh(avg_confidence.index, avg_confidence.values, color=plt.cm.viridis(np.linspace(0, 0.8, len(avg_confidence))))
        plt.title("Average Confidence by Object Type", fontsize=16)
        plt.xlabel("Average Confidence Score", fontsize=12)
        plt.ylabel("Object Type", fontsize=12)
        plt.xlim(0, 1)
        
        # Add confidence labels
        for i, bar in enumerate(bars):
            width = bar.get_width()
            plt.text(width + 0.02, i, f"{width:.2f}", va='center')
            
        plt.tight_layout()
        plt.show()
        
        # Create summary table for top objects
        object_summary = df.groupby('label').agg({
            'confidence': ['mean', 'min', 'max'],
            'chapter': 'nunique',
            'time': 'count'
        }).sort_values(('time', 'count'), ascending=False).head(10)
        
        object_summary.columns = ['Avg Confidence', 'Min Confidence', 'Max Confidence', 'Chapters', 'Occurrences']
        object_summary = object_summary.reset_index()
        
        # Generate HTML table
        rows_html = ""
        for _, row in object_summary.iterrows():
            # Get list of chapters where this object appears
            chapters = df[df['label'] == row['label']]['chapter'].unique()
            chapters_str = ", ".join(sorted(chapters))
            
            rows_html += f"""
                <tr>
                    <td>{row['label']}</td>
                    <td>{row['Occurrences']}</td>
                    <td>{row['Avg Confidence']:.2f}</td>
                    <td>{row['Min Confidence']:.2f}</td>
                    <td>{row['Max Confidence']:.2f}</td>
                    <td>{chapters_str}</td>
                </tr>
            """
        
        display(HTML(f"""
            <div style="margin: 20px 0; overflow-x: auto;">
                <h4>Most Common Object Detections</h4>
                <table style="width:100%; border-collapse: collapse; margin-top: 15px;">
                    <thead style="background-color: #f8f9fa;">
                        <tr>
                            <th style="padding: 12px; border: 1px solid #dee2e6; text-align: left;">Object</th>
                            <th style="padding: 12px; border: 1px solid #dee2e6; text-align: left;">Occurrences</th>
                            <th style="padding: 12px; border: 1px solid #dee2e6; text-align: left;">Avg Confidence</th>
                            <th style="padding: 12px; border: 1px solid #dee2e6; text-align: left;">Min Confidence</th>
                            <th style="padding: 12px; border: 1px solid #dee2e6; text-align: left;">Max Confidence</th>
                            <th style="padding: 12px; border: 1px solid #dee2e6; text-align: left;">Chapters</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
        """))
        
        # Business insights
        display(HTML("""
            <div style="background-color: #e9ecef; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h4 style="color: #495057;">💡 Insights for Video Content Management</h4>
                <p>The object detection analysis reveals key content elements that can be used for:</p>
                <ul>
                    <li><strong>Smart Search:</strong> Enable viewers to find scenes containing specific objects</li>
                    <li><strong>Content Tagging:</strong> Automatically generate metadata tags based on detected objects</li>
                    <li><strong>Navigation:</strong> Create chapter markers based on significant object appearances</li>
                </ul>
            </div>
        """))
