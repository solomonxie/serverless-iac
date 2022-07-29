# TODO: HAS TO BE OUR OWN IMAGE REPO
FROM public.ecr.aws/sam/build-python3.8:latest

# Copy function code
# COPY app.py ${LAMBDA_TASK_ROOT}

# Install the function's dependencies using file requirements.txt
# from your project folder.

COPY requirements.txt  .
RUN  pip3 install -r requirements.txt
# RUN  pip3 install -r requirements.txt --target "python/lib/python3.8/site-packages/"

CMD ["bash"]
