import io
import pickle
import re
import uuid

import bedrock_agent
import boto3
import streamlit as st
from PIL import Image

with open("variables.pkl", "rb") as f:
    variables = pickle.load(f)

agent_id = variables["agent_id"]
agent_alias_id = variables["agent_alias_id"]
default_bucket = variables["bucket_name"]
bedrock = bedrock_agent.BedrockAgent(agent_id, agent_alias_id)

# To resolve 403 issue with uploading: https://discuss.streamlit.io/t/axioserror-request-failed-with-status-code-403/38112/12

st.set_page_config(layout="wide", page_title="Fashion Assistant", page_icon="🛍️")
st.session_state.setdefault("img", None)
st.session_state.setdefault("previous_img", None)
st.session_state.setdefault("s3_key", None)
st.session_state.setdefault("img_displayed", False)

st.title("Fashion Assistant")
INIT_MESSAGE = {
    "role": "assistant",
    "content": "Hi! I'm the AI Stylist chat bot. You can ask me question about clothes to wear!",
}

if "chat_history" not in st.session_state or len(st.session_state["chat_history"]) == 0:
    st.session_state["chat_history"] = [INIT_MESSAGE]


def new_chat() -> None:
    """
    Resets streamlit session states.
    """
    st.session_state["chat_history"] = [INIT_MESSAGE]
    st.session_state["img"] = None
    st.session_state["img_displayed"] = False
    st.session_state["previous_img"] = None
    st.session_state["s3_key"] = None
    st.session_state["user_image"] = None
    bedrock.new_session()


def upload_to_s3(bucket_name, s3_key):
    """
    This function uploads the image to S3.
    """
    s3 = boto3.client("s3")
    image = Image.open(st.session_state["img"])
    max_size = 1024, 1024
    min_size = 256, 256
    original_width, original_height = image.size
    if original_width > max_size[0] or original_height > max_size[1]:
        image.thumbnail(max_size)
    if original_width < min_size[0] or original_height < min_size[1]:
        image = image.resize(min_size)
    image_bytes = io.BytesIO()
    image.save(image_bytes, format=image.format)
    image_bytes.seek(0)
    s3.upload_fileobj(image_bytes, bucket_name, s3_key)
    st.session_state["s3_key"] = s3_key


def download_from_s3(bucket_name, key):
    """
    This function downloads the image from S3.
    """
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket_name, Key=key)
    img_bytes = response["Body"].read()
    img = Image.open(io.BytesIO(img_bytes))
    return img


with st.sidebar:
    st.sidebar.button("New Chat", on_click=new_chat, type="primary")
    st.session_state["img"] = st.file_uploader(
        "Upload an image", type=["png", "jpeg"], label_visibility="collapsed"
    )

if st.session_state["img"] is not None:
    if st.session_state["img"] != st.session_state["previous_img"]:
        folder = "blogpost/"
        random_s3_key = folder + str(uuid.uuid4()) + ".png"
        upload_to_s3(default_bucket, random_s3_key)
        st.session_state["previous_img"] = st.session_state["img"]
        st.session_state["img_displayed"] = False
        st.session_state["user_image"] = st.session_state["img"]
        st.session_state["random_s3_key"] = random_s3_key
        print(f"uploaded to S3 {default_bucket} with key {random_s3_key}")
else:
    st.session_state["user_image"] = None

if "user_image" in st.session_state and st.session_state["user_image"] is not None:
    st.image(st.session_state["user_image"], caption="Uploaded Image", width=200)

for index, chat in enumerate(st.session_state["chat_history"]):
    with st.chat_message(chat["role"]):
        if index <= 1:
            col1, space, col2 = st.columns((7, 1, 2))
            col1.markdown(chat["content"])

        elif chat["role"] == "assistant":
            col1, col2, col3 = st.columns((5, 4, 1))

            col1.markdown(chat["content"], unsafe_allow_html=True)

            # Display the generated image if it exists in the chat history
            if "image" in chat:
                col1.image(chat["image"], caption="Generated Image", width=200)
                buffer = io.BytesIO()
                chat["image"].save(buffer, format="PNG")
                col1.download_button(
                    label="Download Image",
                    data=buffer,
                    file_name="generated_image.png",
                    mime="image/png",
                    key=str(uuid.uuid4()),
                )

            if "trace" in chat and col3.checkbox(
                "Trace", value=False, key=index, label_visibility="visible"
            ):
                col2.subheader("Trace")
                col2.markdown(chat["trace"])
        else:
            st.markdown(chat["content"])

if prompt := st.chat_input("Start your conversation..."):
    st.session_state["chat_history"].append({"role": "human", "content": prompt})

    with st.chat_message("human"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        col1, col2, col3 = st.columns((5, 4, 1))

        if col3.checkbox(
            "Trace",
            value=True,
            key=len(st.session_state["chat_history"]),
            label_visibility="visible",
        ):
            col2.subheader("Trace")
        if st.session_state["user_image"] is not None:
            random_key = st.session_state["random_s3_key"]
            input_s3_uri = f"s3://{default_bucket}/{random_key}"
            content = (
                prompt
                + "The image I'm talking about is stored in S3 here: "
                + f"<input_s3_uri>{input_s3_uri}<input_s3_uri>"
            )
            print("Final Prompt", content)
            response_text, trace_text = bedrock.invoke_agent(content, col2)

        else:
            response_text, trace_text = bedrock.invoke_agent(prompt, col2)
        if "s3://" in response_text:
            s3_uri = bedrock.response_parser(
                response_text, "<generated_s3_uri>", "</generated_s3_uri>"
            )
            bucket, generated_s3_key = s3_uri.replace("s3://", "").split("/", 1)
            generated_img = download_from_s3(bucket, generated_s3_key)

            # Display the generated image in the chat message
            col1.image(generated_img, caption="Generated Image", width=200)
            buffer = io.BytesIO()
            generated_img.save(buffer, format="PNG")
            col1.download_button(
                label="Download Image",
                data=buffer,
                file_name="generated_image.png",
                mime="image/png",
                key=str(uuid.uuid4()),
            )

            # Add the generated image to the chat history
            st.session_state["chat_history"].append(
                {
                    "role": "assistant",
                    "content": response_text,
                    "trace": trace_text,
                    "image": generated_img,
                }
            )
        else:
            st.session_state["chat_history"].append(
                {"role": "assistant", "content": response_text, "trace": trace_text}
            )

        col1.markdown(
            re.sub(r"(<[^>]+>)(.*?)(</[^>]+>)", r"\2", response_text),
            unsafe_allow_html=True,
        )
