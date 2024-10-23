FROM public.ecr.aws/lambda/python:3.12

# Install required dependencies
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copy the source code from the web image over here, that way we won't require
# installing composer in this image, too
COPY . .

# Run the main script
CMD [ "lambda_function.handler" ]
