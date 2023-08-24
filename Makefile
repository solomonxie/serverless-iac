-include envfile
-include envfile-${APPNAME}
export PYTHONPATH := .
.EXPORT_ALL_VARIABLES:
.PHONY: deploy-all


describe:
	echo ${ENABLE_VPC}
	@.git/venv/bin/python -c "import settings; print(settings.DESCRIPTION)"

deploy-all:
	.git/venv/bin/python deploy/aws/deploy_lambda.py
	.git/venv/bin/python deploy/aws/deploy_rest_api.py
	.git/venv/bin/python deploy/aws/deploy_step_function.py
	.git/venv/bin/python deploy/aws/deploy_eventbridge.py
	# .git/venv/bin/python deploy/aws/deploy_http_api.py

deploy-iam:
	.git/venv/bin/python deploy/aws/deploy_iam.py

deploy-layer:
	.git/venv/bin/python deploy/aws/deploy_lambdalayer.py

deploy-lambda:
	.git/venv/bin/python deploy/aws/deploy_lambda.py

deploy-stepfunc:
	.git/venv/bin/python deploy/aws/deploy_step_function.py

deploy-rest-api:
	.git/venv/bin/python deploy/aws/deploy_rest_api.py

deploy-http-api:
	.git/venv/bin/python deploy/aws/deploy_http_api.py

deploy-event:
	.git/venv/bin/python deploy/aws/deploy_eventbridge.py

destroy:
	.git/venv/bin/python deploy/aws/destroy_app.py


venv:
	[ -e .git ] && [ ! -e .git/venv ] && python3 -m virtualenv -p python3.7 .git/venv ||true
	yes | .git/venv/bin/python -m pip install -r requirements.txt


docker-build:
	docker build -t lambda-python .

docker-into:
	docker run -it --rm -v ${PWD}:/var/task lambda-python bash

docker-test:
	docker run -it --rm -v ${PWD}:/var/task lambda-python pytest -v tests


compile-and-upload:
	# REF: https://aws.amazon.com/premiumsupport/knowledge-center/lambda-layer-simulated-docker/
	# UPLOAD LAYER
	# docker run --rm -v "${PWD}":/var/task "public.ecr.aws/sam/build-python3.8" /bin/sh -c "pip install -r requirements_abc_service.txt -t python/lib/python3.8/site-packages/; exit"
	pip install -r requirements_abc_service.txt -t python/lib/python3.8/site-packages/
	zip -r /tmp/layer.zip python ||true
	rm -rdf python ||true
	# Show CodeSha256
	cat /tmp/layer.zip |sha256sum |cut -d' ' -f1 |xxd -r -p |base64
	# aws s3 cp /tmp/layer.zip s3://${IAC_BUCKET}/lambda/hellofunc1234/prod/layer_latest.zip --profile sam-dev
	rm -rdf python ||true
	# UPLOAD CORE CODE
	(cd services && zip -FSr /tmp/code.zip ./* -x *.pyc)
	# aws s3 cp /tmp/code.zip s3://${IAC_BUCKET}/lambda/hellofunc1234/prod/code_latest.zip --profile sam-dev
	# Show CodeSha256
	cat /tmp/code.zip |sha256sum |cut -d' ' -f1 |xxd -r -p |base64
	# rm /tmp/code.zip ||true
