import json
from moviepy.video.io.VideoFileClip import VideoFileClip
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import io, base64
from IPython.display import display, HTML
import sys, os


def read_json_on_s3(s3_uri, s3_client):
    # Parse s3 bucket and key from s3 uri
    s3_bucket = s3_uri.split('/')[2]
    s3_key = s3_uri.replace(f's3://{s3_bucket}/','')
    
    # Read BDA output_config file on S3
    response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
    file_content = response['Body'].read().decode('utf-8')  # Read the content and decode it to a string
    # Convert the content to JSON
    return json.loads(file_content)

def delete_s3_folder(bucket_name, folder_prefix, s3_client):
    """
    Delete all objects within an S3 folder.

    :param bucket_name: Name of the S3 bucket
    :param folder_prefix: Folder path (prefix) to delete (must end with '/')
    """
    
    # List all objects with the given prefix (folder)
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=folder_prefix)
    
    if 'Contents' in response:
        objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
        
        # Delete all objects in the folder
        s3_client.delete_objects(Bucket=bucket_name, Delete={'Objects': objects_to_delete})
        print(f"Deleted folder: {folder_prefix} in bucket: {bucket_name}")
    else:
        print(f"No objects found in folder: {folder_prefix}")

def plot_text(sample_video_movie, result_data, chapter_index):
    # Save the original stdout and stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    # Suppress stdout and stderr
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')
    
    # plot all frames with boundingbox in the given scene
    width = result_data["metadata"]["frame_width"]
    height = result_data["metadata"]["frame_height"]
    
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from PIL import Image, ImageDraw
    import matplotlib.pyplot as plt
    
    with VideoFileClip(sample_video_movie) as video_clip:
        for chapter in result_data["chapters"]:
            if chapter["chapter_index"] == chapter_index:
                for frame in chapter["frames"]:
                    bboxes = []
                    if frame.get("text_lines"):
                        for tl in frame["text_lines"]:
                            if tl["confidence"] < 0.5:
                                continue
                            for l in tl["locations"]:
                                bbox = l["bounding_box"]
                                if bbox:
                                    bboxes.append(
                                        {"bbox":(
                                                    width*bbox["left"], 
                                                    height*bbox["top"], 
                                                    width * (bbox["width"]+bbox["left"]), 
                                                    height * (bbox["height"] + bbox["top"])
                                                ),
                                         "text": f"{tl['text']}"})
                    if bboxes:
                        timestamp = frame["timestamp_millis"]/1000
                        frame = video_clip.get_frame(timestamp)  
                        frame_image = Image.fromarray(frame)
                        draw = ImageDraw.Draw(frame_image)
    
                        txts = []
                        for box in bboxes:
                            draw.rectangle(box["bbox"], outline="yellow", width=2)
                            if box["text"] not in txts:
                                txts.append(box['text'])
    
                        plt.figure(figsize=(10, 6))
                        plt.imshow(frame_image)
                        plt.title(f"At {timestamp} s, logo: {','.join(txts)}")
                        plt.axis("off")
                        plt.show()
    # Restore the original stdout and stderr
    sys.stdout = original_stdout
    sys.stderr = original_stderr

def plot_logo(sample_video_movie, result_data, chapter_index):
    # Save the original stdout and stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    # Suppress stdout and stderr
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

    width = result_data["metadata"]["frame_width"]
    height = result_data["metadata"]["frame_height"]
    
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from PIL import Image, ImageDraw
    import matplotlib.pyplot as plt
    
    with VideoFileClip(sample_video_movie) as video_clip:
        for chapter in result_data["chapters"]:
            if chapter["chapter_index"] == chapter_index:
                for frame in chapter["frames"]:
                    bboxes = []
                    if frame.get("logos"):
                        for tl in frame["logos"]:
                            for l in tl["locations"]:
                                bbox = l["bounding_box"]
                                if bbox:
                                    bboxes.append(
                                        {"bbox":(
                                                    width*bbox["left"], 
                                                    height*bbox["top"], 
                                                    width * (bbox["width"]+bbox["left"]), 
                                                    height * (bbox["height"] + bbox["top"])
                                                ),
                                         "text": f"{tl['name']}"})
                    if bboxes:
                        timestamp = frame["timestamp_millis"]/1000
                        frame = video_clip.get_frame(timestamp)  
                        frame_image = Image.fromarray(frame)
                        draw = ImageDraw.Draw(frame_image)
    
                        txts = []
                        for box in bboxes:
                            draw.rectangle(box["bbox"], outline="yellow", width=2)
                            if box["text"] not in txts:
                                txts.append(box['text'])
    
                        plt.figure(figsize=(10, 6))
                        plt.imshow(frame_image)
                        plt.title(f"At {timestamp} s, logo: {','.join(txts)}")
                        plt.axis("off")
                        plt.show()
    # Restore the original stdout and stderr
    sys.stdout = original_stdout
    sys.stderr = original_stderr

def plot_content_moderation(sample_video_path, result_data, chapter_index):
    # Save the original stdout and stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    # Suppress stdout and stderr
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

    with VideoFileClip(sample_video_path) as video_clip:
        for chapter in result_data["chapters"]:
            for frame in chapter["frames"]:
                if frame.get("content_moderation"):
                    for cm in frame["content_moderation"]:
                        timestamp = frame["timestamp_millis"]/1000
                        img_frame = video_clip.get_frame(timestamp)  
                        frame_image = Image.fromarray(img_frame)
        
                        plt.figure(figsize=(10, 6))
                        plt.imshow(frame_image)
                        plt.title(f"Frame at {timestamp} seconds, {cm['category']}  ({cm['confidence']*100}%) ")
                        plt.axis("off")
                        plt.show()
                    
    # Restore the original stdout and stderr
    sys.stdout = original_stdout
    sys.stderr = original_stderr

def generate_shot_images(sample_video_movie, result_data, image_width = 120):
    # Save the original stdout and stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    # Suppress stdout and stderr
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

    # Generate shot images
    width = result_data["metadata"]["frame_width"]
    height = result_data["metadata"]["frame_height"]
    
    images = []
    def find_chapter_by_shot_index(shot_index):
        # Loop through chapters and return the first match
        idx = 0
        for chapter in result_data["chapters"]:
            if shot_index and shot_index in chapter["shot_indices"]:
                chapter["chapter_index"] = idx
                return chapter
            idx += 1
        return None
    
    with VideoFileClip(sample_video_movie) as video_clip:
        chapter_index = None
        for shot in result_data["shots"]:
            frame = video_clip.get_frame(shot["start_timestamp_millis"]/1000)  
            image = Image.fromarray(frame)
            image = image.resize((image_width, int(image.height * image_width / image.width)))
            ci = find_chapter_by_shot_index(shot["shot_index"])
            if ci and chapter_index != ci["chapter_index"]:
                chapter_index = ci["chapter_index"]
            else:
                ci = None
            images.append({
                "image": image,
                "shot": f'shot {shot["shot_index"]}',
                "chapter": "" if ci is None else f"chapter {ci['chapter_index']}"
            })
    # Restore the original stdout and stderr
    sys.stdout = original_stdout
    sys.stderr = original_stderr

    return images

def plot_shots(images):
    # HTML to display images in a table
    html_content = "<table style='border-collapse: collapse;'>"
    
    def pil_to_base64(pil_image):
        buffered = io.BytesIO()
        pil_image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    # Loop to create rows
    for i in range(0, len(images), 10):
        html_content += "<tr>"
        
        # Loop to add images and texts in each row
        for j in range(10):
            if i + j < len(images):
                html_content += f"""
                    <td style="padding: 1px; text-align: center;vertical-align:top;">
                        <div style="display:inline;position:relative;min-height:18px;border:solid 1px white;">{images[i + j]['chapter']}</div>
                        <img style="display:block" src="data:image/png;base64,{pil_to_base64(images[i + j]['image'])}" />
                        <div style="display:inline;position:relative;top:-20px; height:0px; color: white;">{images[i + j]['shot']}</div>
                    </td>
                """
        html_content += "</tr>"
    
    html_content += "</table>"
    
    # Display the HTML
    display(HTML(html_content))