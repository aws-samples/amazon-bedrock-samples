import requests
import streamlit as st
import json
import os
import base64
from PIL import Image
from io import BytesIO
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Set the title with an enterprise-friendly emoji and styling
st.markdown("<h1 style='text-align: center; color: #4CAF50;'>💼 Octank Financial Generative AI Assistant</h1>", unsafe_allow_html=True)

# Add a formal description or instructions
st.write("Welcome to the Octank Financial Generative AI-powered solution.")

# Add a separator
st.markdown("---")

# Input text area for the user with a placeholder
st.markdown("#### 📝 Ask Your Query")
user_input = st.text_area("User Input", "", label_visibility="collapsed")

# Dropdown for selecting the action
action = st.selectbox(
    "Select Task:",
    options=[ "Ask Knowledge Base", "Generate with Foundation Model"],
    help="Choose whether to generate response using the knowledge base or directly generate it using the model."
)


# Add a button with a subtle icon and formal style
if st.button('Submit Request'):
    # Get the API Gateway endpoint
    api_gateway_url = os.getenv("APIGATEWAY_ENDPOINT", "") + "/invoke"
    
    # Check for errors in input or environment variables
    if not api_gateway_url:
        st.error("⚠️ API Gateway URL is not set in the environment.")
    elif not user_input.strip():
        st.error("⚠️ Please enter a query.")
    else:
        # Call the API Gateway
        try:
            # API call
            response = requests.post(api_gateway_url, json={'prompt': user_input, 'action': "model" if action == "Run Model Task" else "knowledge"})
            
            # Handle the API response
            if response.status_code == 200:
                data = response.json()
                # print("data from API Gateway:", data)
                # logger.info("data from API Gateway:", data)
                assistant_response = data.get('generatedResponse', 'No response available')
                logger.info(f"Assistant response: {assistant_response}")

                citations = data.get('citations', [])
                # print("citations:", citations)
                logger.info(f"References: {citations}")

                # Display assistant's response with a success box
                # st.success("Response:")
                # st.write(assistant_response)

                   # Display assistant's response in a special box
                 # Display assistant's response in a special box with custom font
                st.markdown(f"""
                <div style="border: 1px solid #e0e0e0; padding: 10px; background-color: #f9f9f9; border-radius: 5px; font-family: 'Arial', sans-serif; font-size: 16px;">
                    <strong>Response:</strong>
                    <p>{assistant_response}</p>
                </div>
                """, unsafe_allow_html=True)

                # Add a separator
                st.markdown("---")

                # Display references, if available
                if citations:
                    st.markdown("### 📄 Supporting References")
                    
                    # CSS for multi-column scrollable references
                    st.markdown("""
                    <style>
                    .reference-container {
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                        gap: 20px;
                        padding: 20px;
                    }
                    .reference-box {
                        border: 1px solid #ccc;
                        padding: 15px;
                        max-height: 300px;
                        overflow-y: auto;
                        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                    }
                    .reference-image {
                        max-width: 100%;
                        height: auto;
                        margin-bottom: 10px;
                    }
                    .location-info {
                        font-weight: bold;
                        color: #333;
                        margin-top: 5px;
                    }
                    </style>
                    """, unsafe_allow_html=True)

                    # Create the reference container
                    st.markdown('<div class="reference-container">', unsafe_allow_html=True)

                    # for i, citation in enumerate(citations):
                    #     print("/n i:", i)
                    # references = citations.get('retrievedReferences', [])

                    
                    print("citations before loop:", citations)
                    k = 0
                    # Iterate through each citation
                    for citation in citations:

                        
                        # Get the generated response part (optional, for context)
                        generated_text = citation['generatedResponsePart']['textResponsePart']['text']
                        print(f"Generated Response: {generated_text}")
                        
                        # Retrieve the references
                        references = citation.get('retrievedReferences', [])
                        print(f"References: {references}")
                        
                        # Loop through the references and print the content
                        if references:
                            k += 1

                            for j, ref in enumerate(references):
                                # Begin each reference block
                                # st.markdown('<div class="reference-box">', unsafe_allow_html=True)

                                # Display the reference title and content using markdown to allow HTML rendering
                                st.markdown(f"**Reference :** {ref.get('content', {}).get('text', 'No content available')}", unsafe_allow_html=True)

                                # Display the location information using markdown to allow HTML rendering
                                location = ref.get('location', {}).get('s3Location', {}).get('uri', 'No location available')
                                st.markdown(f"<p class='location-info'>Source Location: {location}</p>", unsafe_allow_html=True)

                                # Display the image if metadata contains it
                                base64_image = ref.get('metadata', {}).get('base64Image')
                                if base64_image:
                                    try:
                                        image_data = base64.b64decode(base64_image)
                                        image = Image.open(BytesIO(image_data))
                                        st.image(image, caption=f"Image from Reference {j+1}", use_column_width=True)
                                    except Exception as e:
                                        st.error(f"Error displaying image: {str(e)}")

                            # End each reference block
                            st.markdown('</div>', unsafe_allow_html=True)

                    # Close the reference container
                    st.markdown('</div>', unsafe_allow_html=True)

            else:
                st.error(f"API Error: {response.status_code} - {response.text}")

        except Exception as e:
            st.error(f"Error calling the API: {str(e)}")


# if st.checkbox("Show Logs"):
#     st.text_area("Logs", value=open("streamlit_app.log").read(), height=200)

# Add a footer or custom message at the bottom of the app
st.markdown("<hr><center>Powered by Octank Financial AI Solutions</center>", unsafe_allow_html=True)