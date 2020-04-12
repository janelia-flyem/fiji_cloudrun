# fiji_cloudrun

This package creates a docker container that wraps fiji with a web interface so that
fiji headless commands can be called via an http REST interface.
Furthermore, it cam be deployed into a managed serverless system such
as Google cloud run (which is like a Amazon lambda but using arbitrary containers).
Finally, it provides an interface for initializing inputs and storing
outputs using cloud storage (currently only Google storage endpoints are supported).

Google cloud run enables users to execute hundreds of concurrent requests, effectively
auto-scaling from 0 to up to 1000 parallel requests.  This enables massive fiji batch jobs
to be run with minimial infrastructural costs.

## Local installation instructions (for local testing)

(to install this container using Google please see "Deploying on cloud run" below)

This is a docker container that can be built locally using

% docker build . -t fiji

and the container launched with

% docker run -e "PORT=8080" -p 8080:8080 -v $GOOGLE_APPLICATION_CREDENTIALS:/tmp/keys/FILE_NAME.json:ro  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/FILE_NAME.json fiji

This will start up a web client that listens to 127.0.0.1:8080.  The GOOGLE_APPLICATION_CREDENTIALS is an environment variable
that allows you to use google cloud storage locally.  The -v and -e options can be omitted if you are not using this feature.

## Using fiji for cloud headless commands

To run fiji through the web service simply post a JSON (configuration details below):

% curl -X POST -H "Content-type: application/json" --data-binary @examples/config.json 127.0.0.1:8080 

The examples/config.json is a simple hello world fiji command.  Because fiji is run on a stateless
container, the configuration file specifies which files should be uploaded to this container
and which outputs should be exported.  Configuration file format:

```json
{
	"command": " add argument string used with fiji",
	"input-str": {
		"local file": "content for local file.
		...
	},
	"input-map": {
		"file1": "gs://[google bucket]/[file object]",
		...
	},
	"output-map": {
		"filex": "gs://[google bucket]/[file object]"
	}
}
```

This file allows users to specify output to be written to specified cloud storage locations.  The
standard output for the command is returned as simple html/text.

After results are sent to the caller, the container deletes any intermediate files to keep
it stateless.  This application should not be called with concurrent processes.  To enable concurrency,
by having multiple containers, deploy on cloud run.

## Deploying on cloud run

Create a google cloud account and install gcloud.

Build the container and store in cloud.

% gcloud builds submit --tag gcr.io/[PROJECT_ID]/fiji_headless

If a container already exists, one can build faster from cache with this command
([PROJECT_ID] should be replaced in the YAML with the appropriate project id).

% gcloud builds submit --config cloudbuild.yaml

Once the container is built, deploy to cloud run with the following command.
The instance is created with a maximum 2GB of memory and sets the concurrency to 1
per instance to avoid conflicts between jobs on the same filesytem.  You should make
the endpoint private to avoid unauthorized use.

% gcloud run deploy --memory 2048Mi --concurrency 1 --cpu 2 --image gcr.io/[PROJECT_ID]/fiji_headless --platform managed 

## Invoking cloud run

The resulting endpoint can be invoked through its HTTP api.  One must specify
a bearer token for authentication.  For convenience, when testing the API with curl
one can make an alias that is authenticateed with the following:

% alias gcurl='curl --header "Authorization: Bearer $(gcloud auth print-identity-token)"'

To run a simple hello world:

% gcurl -H "Content-Type: application/json" -X POST --data-binary @example/config.json  https://[CLOUD RUN ADDR]
