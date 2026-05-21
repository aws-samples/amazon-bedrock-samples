import ipywidgets as widgets
from PIL import Image
import io
import pandas as pd
from urllib.parse import urlparse
import boto3
from IPython.display import HTML, display, JSON
from pdf2image import convert_from_bytes
import uuid
import html, markdown, textwrap
from PIL import Image, ImageDraw, ImageFont

s3 = boto3.client('s3')

def load_image(uri):
    if uri.startswith('s3://'):
        bucket, key = urlparse(uri).netloc, urlparse(uri).path.lstrip('/')
        file_content = s3.get_object(Bucket=bucket, Key=key)['Body'].read()
    else:
        file_content = open(uri, 'rb').read()
    
    if uri.lower().endswith('.pdf'):
        img_io = io.BytesIO()
        convert_from_bytes(file_content)[0].save(img_io, format='JPEG')
        return img_io.getvalue()
    
    img = Image.open(io.BytesIO(file_content))
    if img.format != 'JPEG':
        img_io = io.BytesIO()
        img.save(img_io, format='JPEG')
        return img_io.getvalue()
    return file_content


def parse_s3_uri(s3_uri):
    """Parse S3 URI into bucket and key"""
    parsed = urlparse(s3_uri)
    if parsed.scheme != 's3':
        raise ValueError(f"Invalid S3 URI scheme. Expected 's3', got '{parsed.scheme}'")
    
    bucket = parsed.netloc
    # Remove leading '/' from key
    key = parsed.path.lstrip('/')
    return bucket, key

def get_image_from_s3(s3_uri):
    """Get image from S3 using URI and return as PIL Image"""
    bucket, key = parse_s3_uri(s3_uri)
    s3_client = boto3.client('s3')
    response = s3_client.get_object(Bucket=bucket, Key=key)
    image_bytes = response['Body'].read()
    
    # Convert bytes to PIL Image
    image = Image.open(io.BytesIO(image_bytes))
    return image


def display_html(data, root='root', expanded=True, bg_color='#f0f0f0'):
    html = f"""
        <div class="custom-json-output" style="background-color: {bg_color}; padding: 10px; border-radius: 5px;">
            <button class="toggle-btn" style="margin-bottom: 10px;">{'Collapse' if expanded else 'Expand'}</button>
            <pre class="json-content" style="display: {'block' if expanded else 'none'};">{data}</pre>
        </div>
        <script>
        (function() {{
            var toggleBtn = document.currentScript.previousElementSibling.querySelector('.toggle-btn');
            var jsonContent = document.currentScript.previousElementSibling.querySelector('.json-content');
            toggleBtn.addEventListener('click', function() {{
                if (jsonContent.style.display === 'none') {{
                    jsonContent.style.display = 'block';
                    toggleBtn.textContent = 'Collapse';
                }} else {{
                    jsonContent.style.display = 'none';
                    toggleBtn.textContent = 'Expand';
                }}
            }});
        }})();
        </script>
        """
    display(HTML(html))


def onclick_function():
    return """
        <script>
            function handleClick(event) {
                var row = event.target;
                if (!row) return;  // Click wasn't on a row

                // Get the bbox data from the row
                var bbox = row.getAttribute('data-bbox');
                if (!bbox) return;  // No bbox data found
                row.style.backgroundColor = '#ffe0e0';
                
                // Parse the bbox string back to array
                //bbox = JSON.parse(bbox);
                row.style.backgroundColor = '#fff0f0';

                // Send custom event to Python
                var event = new CustomEvent('bbox_click', { detail: bbox });
                document.dispatchEvent(event);
                row.style.backgroundColor = '#ffe0e0';
                
                
                // First, reset all rows to default background
                var rows = document.getElementsByClassName('kc-item');
                for(var i = 0; i < rows.length; i++) {
                    rows[i].style.backgroundColor = '#f8f8f8';
                }
                
                // Then highlight only the clicked row
                row.style.backgroundColor = '#e0e0e0';
            }
        </script>
    """

def create_form_view(forms_data):

    styles = """
    <style>
        .kv-container{display:flex;flex-direction:column;gap:4px;margin:4px;width:100%}
        .kv-box{border:0px solid #e0e0e0;border-radius:4px;padding:4px;margin:0;background-color:#f8f9fa;width:auto}
        .kv-item{display:flex;justify-content:space-between;align-items:center;margin-bottom:2px}
        .kc-item{background-color:#fff;display:flex;justify-content:space-between;align-items:center;margin-bottom:2px}
        .key{font-weight:600;padding:1px 4px;font-size:.85em;color:#333}
        .value{background-color:#fff;padding:1px 4px;border-radius:4px;font-size:.85em;color:#666;margin-top:1px}
        .confidence{padding:1px 4px;border-radius:4px;font-size:.85em;color:#2196F3}
        .nested-container{margin-left:8px;margin-top:4px;border-left:2px solid #e0e0e0;padding-left:4px}
        .parent-key{color:#6a1b9a;font-size:.9em;font-weight:600;margin-bottom:2px}
    </style>
    """

    def render_nested_keys(data):
        if not isinstance(data, dict): return f'<div class="value">{data}</div>'
        html = ""
        for key, value in data.items():
            if isinstance(value, dict) and 'value' in value:
                conf = value.get('confidence', 0) * 100
                html += f"""
                    <div class='kv-box'>
                        <div class='kv-item'><div class='key'>{key}</div></div>
                        <div class='kc-item' onclick=handleClick(event) data-bbox='(10,40,110,200)'>
                            <div class="value">{value['value']}</div>
                            <div class='confidence'>{conf:.1f}%</div>
                        </div>
                    </div>"""
            else:
                html += f"""
                    <div class='kv-box'>
                        <div class='kv-item'><div class='key'>{key}</div></div>
                        <div class="nested-container">{render_nested_keys(value)}</div>
                    </div>"""
        return html

    return HTML(f"{styles}<script>function handleClick(e){{console.log(e.currentTarget.dataset.bbox)}}</script><div class='kv-container'>{render_nested_keys(forms_data)}</div>")


def create_table_view(tables_data):
    styles = """
    <style>
        .table-wrapper {
            width: 100%;
            overflow-x: auto;
            white-space: nowrap;
            -webkit-overflow-scrolling: touch;
        }
        .table-container{margin:20px}
        .table-view{
            width: auto;
            min-width: 100%;
            border-collapse:collapse;
            background-color:white;
            table-layout: auto;
        }
        .table-view th{
            background-color:#f8f9fa;
            padding:12px;
            text-align:left;
            font-size:0.85em;
            border:1px solid #dee2e6;
            white-space: nowrap;
        }
        .table-view td{
            padding:12px;
            border:1px solid #dee2e6;
            font-size:0.8em;
            white-space: nowrap;
        }
        .confidence{color:#2196F3;font-size:0.9em}
    </style>
    """
    
    def process_table(table_data):
        def format_cell(cell):
            if isinstance(cell, dict) and 'value' in cell:
                conf = f"<span class='confidence'>({cell.get('confidence', 0):.1%})</span>" if 'confidence' in cell else ""
                return f"{cell['value']}{conf}"
            return str(cell)
        
        return pd.DataFrame([{k: format_cell(v) for k, v in row.items()} for row in table_data])
    
    tables_html = "".join(
        f"""
        <div class="table-container">
            <h3>{table_name}</h3>
            <div class="table-wrapper">
                {process_table(table_data).to_html(classes='table-view', index=False, escape=False)}
            </div>
        </div>
        """
        for table_name, table_data in tables_data.items() if table_data
    )
    
    return HTML(f"{styles}{tables_html}")


def get_view(data, display_function=None):
    out = widgets.Output()
    with out:
        if callable(display_function):
            display_function(data)
        else:
            display(data)
    return out


def segment_view(document_image_uris, inference_result):
    # Create the layout with top alignment
    main_hbox_layout = widgets.Layout(
        width='100%',
        display='flex',
        flex_flow='row nowrap',
        align_items='stretch',
        margin='0'
    )
    image_widget = widgets.Image(
        value=b'',
        format='png',
        width='auto',
        height='auto'
    )
    image_widget.value = load_image(uri=document_image_uris[0])
    image_container = widgets.VBox(
        children=[image_widget],
        layout=widgets.Layout(
            border='0px solid #888',
            padding='1px',
            margin='2px',
            width='60%',
            flex='0 0 60%',
            min_width='300px',
            height='auto',
            display='flex',
            align_items='stretch',
            justify_content='center'
        )
    )
    
    
    # Create tabs for different views
    tab = widgets.Tab(
        layout=widgets.Layout(
            width='40%',
            flex='0 0 40%',
            min_width='300px',
            height='auto'
        )
    )
    form_view = widgets.Output()
    table_view = widgets.Output()
    
    with form_view:
        display(create_form_view(inference_result['forms']))
        
    with table_view:
        display(create_table_view(inference_result['tables']))
    
    tab.children = [form_view, table_view]
    tab.set_title(0, 'Key Value Pairs')
    tab.set_title(1, 'Tables')

    
    # Add custom CSS for scrollable container
    custom_style = """
    <style>
        .scrollable-vbox {
            max-height: 1000px;
            overflow-y: auto;
            overflow-x: hidden;
        }
        .main-container {
            display: flex;
            height: 1000px;  /* Match with max-height above */
        }
        .jupyter-widgets-output-area .p-TabBar-tab {
            min-width: fit-content !important;
            max-width: fit-content !important;
            padding: 6px 10px !important;
    </style>
    """
    display(HTML(custom_style))
    
    # Create the main layout
    main_layout = widgets.HBox(
        children=[image_container, tab],
        layout=main_hbox_layout
    )

    
    # Add the scrollable class to the right VBox
    main_layout.add_class('main-container')
    return main_layout


def display_collapsable(data, title):
    accordion = widgets.Accordion(children=[widgets.Output()])
    accordion.set_title(0, title)
    
    with accordion.children[0]:
        display(data)
    
    return accordion
    

def display_multiple(views, view_titles = None):
    main_tab = widgets.Tab()
    for i, view in enumerate(views):
        main_tab.children = (*main_tab.children, view)
        tab_title = view_titles[i] if view_titles and view_titles[i] else f'Document {i}'
        main_tab.set_title(i, title=tab_title)
    display(main_tab)


def get_s3_presigned_url(s3_uri, expiration=3600):
    """Generate a presigned URL for the S3 object"""
    try:
        # Parse S3 URI
        parsed = urlparse(s3_uri)
        bucket = parsed.netloc
        key = parsed.path.lstrip('/')
        
        # Create presigned URL
        s3_client = boto3.client('s3')
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket,
                'Key': key,
                'ResponseContentType': 'image/png',  # Set appropriate content type
                'ResponseContentDisposition': 'inline'  # Force inline display            
            },
            ExpiresIn=expiration
        )
        return presigned_url
    except Exception as e:
        print(f"Error generating presigned URL: {e}")
        return None


def get_figure_view(figure,model_id, frame_id):
    figure_df = get_figure_summary(figure,model_id, frame_id)
    return get_view(HTML(figure_df.to_html(index=False, escape=False)))
        
def get_figure_summary(figure,model_id, frame_id):
    figure_df = pd.json_normalize(figure)
    s3_uri = figure['crop_images'][0]
    image = get_image_from_s3(s3_uri)
    width, height = image.size
    presigned_url = get_s3_presigned_url(s3_uri) if s3_uri else None
    figure_df['Image Link'] = presigned_url
    figure_df['Width'] = width
    figure_df['Height'] = height
    
    # Function to create view image link
    def make_view_image_link(row):
        if pd.isna(row['Image Link']):
            return 'No image available'
        # Escape single quotes in URL
        escaped_url = row['Image Link'].replace("'", "\\'")
        return f'<a class="image-link" onclick="showModal(\'{model_id}\',\'{frame_id}\', \'{escaped_url}\',{row["Width"]}, {row["Height"]});return false;">View Image</a>'

    # Add View Image column
    figure_df['crop_images'] = figure_df.apply(make_view_image_link, axis=1)
    figure_df['representation.html'] = figure_df['representation.html'].apply(html.escape).apply(lambda x: textwrap.shorten(str(x), width=500, placeholder='...'))
    figure_df['representation.markdown'] = figure_df['representation.markdown'].apply(lambda x: textwrap.shorten(str(x), width=500, placeholder='...'))
    figure_df['representation.text'] = figure_df['representation.text'].apply(lambda x: textwrap.shorten(x, width=500, placeholder='...')).apply(lambda x: x.replace('$', '\$').replace('_', '\_').replace('#', '\#'))

    # Drop the hidden image data column
    figure_df = figure_df.drop(['Image Link','Width','Height'], axis=1)        
    figure_df = figure_df.T
    figure_df= figure_df.style.hide(axis='columns').set_properties(**{
        'text-align': 'left',
        'white-space': 'pre-wrap',
        'padding': '10px',
        'border': '1px solid #ddd'
    }).set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', '#f2f2f2'),
            ('text-align', 'left'),
            ('padding', '10px'),
            ('border', '1px solid #ddd')
        ]},
        {'selector': 'tr:nth-of-type(even)', 'props': [
            ('background-color', '#f9f9f9')
        ]},
        {'selector': 'tr:hover', 'props': [
            ('background-color', '#f5f5f5')
        ]}
    ])       
    return figure_df


def get_page_view(page, modal_id, frame_id):
    page_df = get_page_summary(page, modal_id, frame_id)
    return get_view(page_df)
        
def get_page_summary(page, modal_id, frame_id):
    page_df = pd.json_normalize(page)
    s3_uri = page['asset_metadata'].get('rectified_image', None)
    presigned_url = get_s3_presigned_url(s3_uri) if s3_uri else None
    page_df['Image Link'] = presigned_url
    page_df['Width'] = page['asset_metadata'].get('rectified_image_width_pixels', 0)
    page_df['Height'] = page['asset_metadata'].get('rectified_image_height_pixels', 0)
    
    # Function to create view image link
    def make_view_image_link(row):
        if pd.isna(row['Image Link']):
            return 'No image available'
        # Escape single quotes in URL
        escaped_url = row['Image Link'].replace("'", "\\'")
        return f'<a class="image-link" onclick="showModal(\'{modal_id}\', \'{frame_id}\', \'{escaped_url}\', {row["Width"]}, {row["Height"]});return false;">View Image</a>'

    # Add View Image column
    page_df['asset_metadata.rectified_image'] = page_df.apply(make_view_image_link, axis=1)
    page_df['representation.html'] = page_df['representation.html'].apply(html.escape).apply(lambda x: textwrap.shorten(str(x), width=500, placeholder='...'))
    page_df['representation.markdown'] = page_df['representation.markdown'].apply(lambda x: textwrap.shorten(str(x), width=500, placeholder='...'))
    page_df['representation.text'] = page_df['representation.text'].apply(lambda x: textwrap.shorten(x, width=500, placeholder='...')).apply(lambda x: x.replace('$', '\$').replace('_', '\_').replace('#', '\#'))
    # Drop the hidden image data column
    page_df = page_df.drop(['Image Link','Width','Height'], axis=1)        
    page_df = page_df.T
    page_df= page_df.style.hide(axis='columns').set_properties(**{
        'text-align': 'left',
        'white-space': 'pre-wrap',
        'padding': '10px',
        'border': '1px solid #ddd'
    }).set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', '#f2f2f2'),
            ('text-align', 'left'),
            ('padding', '10px'),
            ('border', '1px solid #ddd')
        ]},
        {'selector': 'tr:nth-of-type(even)', 'props': [
            ('background-color', '#f9f9f9')
        ]},
        {'selector': 'tr:hover', 'props': [
            ('background-color', '#f5f5f5')
        ]}
    ])       
    return page_df


def get_view(data, display_function=None):
    out = widgets.Output()
    with out:
        if callable(display_function):
            display_function(data)
        else:
            display(data)
    return out


def display_multiple(views, view_titles=None):
    main_tab = widgets.Tab()
    for i, view in enumerate(views):
        main_tab.children = (*main_tab.children, view)
        tab_title = view_titles[i] if view_titles and view_titles[i] else f'Document {i}'
        main_tab.set_title(i, title=tab_title)
    display(main_tab)

def display_modal():
    modal_id = f"imageModal_{uuid.uuid4().hex}"
    frame_id = f"imageFrame_{uuid.uuid4().hex}"    
    html_content = f"""
        <div id="{modal_id}" class="modal">
            <span class="close" onclick="closeModal('{modal_id}', '{frame_id}')">&times;</span>
            <iframe id="{frame_id}" class="modal-content"></iframe>
        </div>
    """
    html_content += """
        <style>
        .modal {
            display: none;
            position: fixed;
            z-index: 9999;
            top: 5vh;
            left: 50%;
            transform: translateX(-50%);
            background-color: rgba(255,255,255,1.0);
            margin: auto;
            box-shadow: 0 0 20px rgba(0,0,0,0.2);
            box-sizing: border-box;
            overflow: auto;
            padding: 0px;
            width: 70%;
            height: 90vh;
            max-width: calc(90% - 20px); 
            max-height: calc(90vh - 40px);
        }
        .modal-content {
            object-fit: contain;
            display: block;
            margin: 20px auto; /* Center horizontally and add some vertical space */
            padding: 10px;
            max-width: calc(90% - 20px); /* 90% of viewport width minus padding */
            max-height: calc(90vh - 40px); /* 90% of viewport height minus padding */
            border: none;
            background: white; /* Optional: adds background to frame */
        }

        .close {
            position: absolute; /* Changed from fixed to absolute */
            color: white;
            top: 10px; /* Distance from the top of the modal */
            right: 10px; /* Distance from the right of the modal */
            font-size: 30px;
            font-weight: bold;
            cursor: pointer;
            z-index: 10000;
            background: rgba(0,0,0,0.5);
            padding: 5px 15px;
            border-radius: 5px;
            width: 10px;
            height: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            text-decoration: none;
        }
        
        .close:hover {
            background: rgba(0,0,0,0.8);
        }        
        .image-link {
            color: #0366d6;
            text-decoration: none;
            cursor: pointer;
        }
        .image-link:hover {
            text-decoration: underline;
        }
        </style>
        <script>
            
            function showModal(modalId, frameId, imageUrl, originalWidth, originalHeight) {
                console.log('Show Modal Called with url:', imageUrl);
                
                const modal = document.getElementById(modalId);
                const frame = document.getElementById(frameId);            

                // Calculate viewport dimensions
                const viewportWidth = window.innerWidth;
                const viewportHeight = window.innerHeight;
                
                // Calculate maximum available space (90% of viewport)
                const maxWidth = viewportWidth * 0.9;
                const maxHeight = viewportHeight * 0.9;
                
                // Calculate dimensions while maintaining aspect ratio
                let newWidth = originalWidth;
                let newHeight = originalHeight;
                const aspectRatio = originalWidth / originalHeight;
                
                if (newWidth > maxWidth) {
                    newWidth = maxWidth;
                    newHeight = newWidth / aspectRatio;
                }
                
                if (newHeight > maxHeight) {
                    newHeight = maxHeight;
                    newWidth = newHeight * aspectRatio;
                }
                // Add padding for modal (40px total - 20px each side)
                const modalWidth = newWidth + 40;
                const modalHeight = newHeight + 40;
    
                // Apply dimensions to frame
                frame.style.width = `${Math.round(newWidth)}px`;
                frame.style.height = `${Math.round(newHeight)}px`;

                // Apply dimensions to frame
                modal.style.width = `${Math.round(modalWidth)}px`;
                modal.style.height = `${Math.round(modalHeight)}px`;
                
                // Show modal and set source
                modal.style.display = "block";
                frame.src = imageUrl;
                
                // Event handlers
                modal.onclick = function(event) {
                    if (event.target === modal || event.target.className === 'modal') {
                        closeModal();
                    }
                };
            }
            
            function closeModal(modalId, frameId) {
                var modal = document.getElementById(modalId);
                var frame = document.getElementById(frameId);
                frame.src = '';
                modal.style.display = "none";
            }

            // Update window click handler
            window.onclick = function(event) {
                if (event.target.classList.contains('modal')) {
                    event.target.style.display = "none";
                }
            }        
        </script>    
    """
    display(HTML(html_content))
    return modal_id, frame_id

def create_page_viewer(s3_uri, text_elements):
    global handle_index
    
    # Create widgets
    image_widget = widgets.Image(layout=widgets.Layout(
        width='100%',
        height='900px',
        object_fit='contain'
    ))
    
    # Get image from S3
    page_image = get_image_from_s3(s3_uri)
    original_image = page_image.copy()
 
    def draw_bounding_box_with_subtype(image, bbox, subType):
        draw = ImageDraw.Draw(image)
        width, height = image.size
        
        # Calculate bbox coordinates
        left = bbox['left'] * width
        top = bbox['top'] * height
        box_width = bbox['width'] * width
        box_height = bbox['height'] * height
        
        # Draw rectangle
        draw.rectangle(
            [(left, top), (left + box_width, top + box_height)],
            outline='red',
            width=2
        )
        
        # Add text label for subType
        font_size = 30
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            # Fallback to default font if arial is not available
            font = ImageFont.load_default()
        
        # Draw text background
        text_bbox = draw.textbbox((left, top-font_size), subType, font=font)
        draw.rectangle(text_bbox, fill='red')
        
        # Draw text
        draw.text(
            (left, top-font_size),
            subType,
            fill='white',
            font=font
        )
        
        return image
    
    def pil_to_bytes(img):
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()
    
    # Set initial image
    image_widget.value = pil_to_bytes(original_image)
    
    # Create a hidden text widget for communication
    comm_text = widgets.Text(value='', layout=widgets.Layout(display='none'))
    comm_text.add_class('comm-text')
    
    # Define JavaScript functions
    display(HTML("""
    <script>
        function handleTextClick(idx) {
            var textWidget = document.querySelector('.comm-text input');
            console.log('handlingTextClick');
            if (textWidget) {
                console.log('updating text widget');
                textWidget.value = idx;
                textWidget.dispatchEvent(new Event('change',{ bubbles: true }));
                textWidget.dispatchEvent(new Event('input',{ bubbles: true }));
            }
        };
    </script>
    """))
    
    # Create HTML for text elements
    text_html = ""
    for idx, elem in enumerate(text_elements):
        text = elem['representation']['text']
        subtype = elem['sub_type']
        text_html += f'<div class="text-elem" data-id="{idx}" onclick="handleTextClick({idx})" title={subtype}>{text}</div>'
    
    # Style the text elements
    html_content = f"""
    <style>
        .text-container {{
            width: 100%;
            height: 800px;
            overflow-y: auto;
            padding: 10px;
            box-sizing: border-box;
        }}
        .text-elem {{
            padding: 5px;
            margin: 2px;
            cursor: pointer;
            border: 1px solid #ddd;
        }}
        .text-elem:hover {{
            background-color: #f0f0f0;
        }}
    </style>
    <div class="text-container">{text_html}</div>
    """
    
    text_area = widgets.HTML(
        value=html_content,
        layout=widgets.Layout(
            width='100%',
            height='900px'
        )
    )
    
    def handle_index(idx):
        img_copy = original_image.copy()
        bbox = text_elements[idx]['locations'][0]['bounding_box']
        subtype = text_elements[idx]['sub_type']
        img_with_box = draw_bounding_box_with_subtype(img_copy, bbox, subtype)
        image_widget.value = pil_to_bytes(img_with_box)
    
    output = widgets.Output()
    def on_value_change(change):
        with output:
            if change['new']:
                try:
                    idx = int(change['new'])
                    handle_index(idx)
                except ValueError:
                    pass
    # Register the text widget callback
    comm_text.observe(on_value_change, names='value')

    # Create headings
    left_heading = widgets.HTML(
        value='<h3 style="text-align: center;">Page Image</h3>'
    )
    right_heading = widgets.HTML(
        value='<h3 style="text-align: center;">Extracted Text</h3>'
    )
    
    # Create VBox containers with headings
    left_vbox = widgets.VBox([
            left_heading,
            image_widget
        ],
        layout=widgets.Layout(width='55%')                          
    )
    
    right_vbox = widgets.VBox([
            right_heading,
            text_area
        ],
        layout=widgets.Layout(width='45%')                          
    )

    # Create the layout
    hbox = widgets.HBox(
        [left_vbox, right_vbox],
        layout=widgets.Layout(
            width='100%',
            height='900px',  # Increased height to accommodate headings
            display='flex',
            border='1px',
            flex_flow='row nowrap',
            justify_content='space-between'
        )
    )    
    
    
    # Display everything
    display(HTML("""
        <style>
            .widget-html { overflow-y: auto !important; }
            .widget-image {
                display: flex !important;
                justify-content: center !important;
                align-items: center !important;
            }
        </style>
    """))
    
    display(comm_text)
    display(hbox, output)

