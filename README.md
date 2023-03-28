# Serverless Standard

A simple yet powerful framework to build serverless applications with a well curated standard of best practices.


## What Can / Cannot Be Automated

The framework will only create "General" Serverless infrastructure, which builds the direct-connection between AWS services, and for the indirect-connections we will need to send a ticket to Ops/DBA to manually create.

Examples of `Direct Connections`:
- AWS API Gateway -> Lambda
- Step Function -> Lambda
- EventBridge -> Lambda
- EventBridge -> Step Function

Examples of `Indirect Connections`:
- Anything about S3
- Anything about DB
- Lambda -> API Gateway
- Lambda -> Step Function
- Lambda -> ...


## HOW TO RUN

1. Create an application repo

2. Create a Tag of the application repo

3. Setup AWS account with a profile name on local machine: `~/.aws/credentials`
```
[my-profile-name]
region = us-east-1
aws_access_key_id = abc
aws_secret_access_key = def
```

4. Specify environment variables listed in `envfile`:
    method-1) `$ export AWS_REGION=us-east-1; export xxx=abc`
    method-2) Add variables into `envfile-local`, and run `$ ./scripts/inject_envfile.sh`

5. Run deployment:
```
$ make deploy

#or
$ make deploy-lambda
$ make deploy-rest-api
$ make deploy-stepfunc
$ make deploy-schedules
```


## Naming Convention

- Lambda Function Full NAME: "${StageName}-${StageSubName}-${ApplicationName}-${FunctionName}"
- LAMBDA FUNCTION PATH: "lambda-function/${FunctionFullName}/${BUILD_NO}.zip"
- Lambda Package Layer NAME: "lambda-layer-${ManifestMd5}"
- Lambda Package Layer PATH: "lambda-layer/${ManifestMd5_LEVELED_DIR}/{ManifestMd5}.zip"
- API: "${StageName}-${StageSubName}-${ApplicationName}-${ApiName}"
- ApiStage: only one -> "latest_release", also points to each Lambda's alias "latest_release"


## Staging

- StageName=prod: (having production env variables and vpc settings)
    - StageSubName=main: production release
    - StageSubName=beta: beta release
    - StageSubName=prev: previous release for easy rollback & debug
- StageName=dev: (having dev env variables, developer has R/W permission)
    - StageSubName=feature1: independent deployment CD for each new feature development
    - StageSubName=feature2: independent deployment CD for each new feature development


## Roadmap

TODO:
- [x] Rollback Mechanism
- [x] Lambda deploy a new version, than switch
- [x] ~~Make a "Change Table" first before any deployment~~
- [x] ~~Auto add IAM role/policy~~
- [x] ~~Safe deployment~~
- [x] Add VPC for Lambda
- [x] Create REST API
- [x] API Throttling
- [x] Lambda: IAM Authorizer (Http / Rest)
- [x] Pull application def/code from another repo
- [x] Support Provisioned Concurrency
- [x] Auto-remove very old versions (Lambda has version / storage quota)
- [ ] ~~Enforce IAM Authorizer for every API~~ (Not if we're using REST Private API)
- [ ] Support Lambda Authorizer
- [ ] Auto-remove very old layers (need to redesign "shared-layers" to "in-app-shared-layers")
- [x] Decouple Lambda deployments from App deployments
- [x] Unify definitions for all types of applications
- [x] AppType:Script (Scheduled Event)
- [x] AppType:StateMachine (Step Func)
- [x] Scheduled Lambda
- [x] Scheduled StateMachine
- [ ] Schedules: support more settings (DLQ, logs, roles, retry...)
- [ ] Rest-api: remove unused routes
- [x] Deploy or detect IAM dependencies
- [ ] Check specs before deployment (e.g., VPC validation, IAM validation, Swagger validation...)
- [x] Specify which lambda to deploy
- [x] Support Ephemeral Storage
- [ ] Support resource tags
- [ ] Support Function URL
- [ ] Support Lambda Concurrency
- [ ] Support SNS
- [ ] Support SQS
- [ ] Support DLQ
- [ ] Support REST-API trigger Step Function
- [x] Add stage info to Lambda's environment variables
- [ ] Attach policy for Lambda to call StepFunc
- [x] Support X-ray for Lambda/APIGW
- [x] ~~REST API response code settings~~ -> AWS will auto-create from Swagger definitions
- [ ] Render IAM Policy with resource specs
- [x] Support EventBridge Event Filters
- [x] Support all API Gateway features: including API directly upload to S3
- [x] Inject customized environment variables to Lambda
