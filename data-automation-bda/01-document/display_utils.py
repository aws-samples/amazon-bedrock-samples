import ipywidgets as widgets
from PIL import Image
import io
import pandas as pd
from urllib.parse import urlparse
import boto3
from IPython.display import HTML, display, JSON
from pdf2image import convert_from_bytes


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