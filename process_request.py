"""Preparees working directory and runs haedless fiji.

Downloads and uploads files to a storage bucket based on
the configuration and calls fiji headless.  Output results
are stored in /tmp/fiji.out.

This function tries to clean-up the home directory for 'fiji'
as well as the working directory.
"""

import json
import os

# file i/o constants
RUNDIR = "/opt/fiji_run"
HOMEDIR = "/home/fiji"
FIJIOUT = "/tmp/fiji.out"
FIJIERR = "/tmp/fiji.err"
CONFIGFILE = "/tmp/config.json"

# execute fiji here
os.chdir(RUNDIR)

try:
    # save bash cnofig
    with open(f"{HOMEDIR}/.bashrc") as fin:
        bashrc = fin.read()
    config = json.load(open(CONFIGFILE))
   
    # read from cloud (only gbucket for now)
    if "input-map" in config:
        for fname, cloud_src in config["input-map"].items():
            if not cloud_src.startswith("gs://"):
                raise RuntimeError("only supports cloud sources with gs:// prefix")
            
            # read from google bucket gs://[bucket name]/[path + file name]
            from google.cloud import storage
            bucket_file = cloud_src[5:]
            bucket_file_arr = bucket_file.split('/')
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_file_arr[0])
            file_loc = "/".join(bucket_file_arr[1:])
            blob1 = bucket.blob(file_loc)
            
            # write file
            if os.path.dirname(fname) != "":
                os.makedirs(os.path.dirname(fname), exist_ok=True)
            blob1.download_to_filename(fname)

    # load any embedded scripts
    if "input-str" in config:
        for fname, value in config["input-str"].items():
            # create directory if it doesn't exist
            if os.path.dirname(fname) != "":
                os.makedirs(os.path.dirname(fname), exist_ok=True)
            with open(fname, 'w') as fout:
                fout.write(value)

    # run command
    res = os.system("(ImageJ-linux64 " + config["command"] + f") > {FIJIOUT} 2> {FIJIERR}")
    
    # write to the cloud (only gbucket for now)
    if "output-map" in config:
        for fname, cloud_src in config["output-map"].items():
            # only write file if it exists
            if os.path.exists(fname):
                if not cloud_src.startswith("gs://"):
                    raise RuntimeError("only supports cloud sources with gs:// prefix")
                
                # read from google bucket gs://[bucket name]/[path + file name]
                from google.cloud import storage
                bucket_file = cloud_src[5:]
                bucket_file_arr = bucket_file.split('/')
                storage_client = storage.Client()
                bucket = storage_client.bucket(bucket_file_arr[0])
                file_loc = "/".join(bucket_file_arr[1:])
                blob1 = bucket.blob(file_loc)
            
                # write file to cloud
                blob1.upload_from_file(open(fname))

    # delete everything that might have been modified
    os.system("rm -rf .* * 2> /dev/null")
    os.system(f"rm -rf {HOMEDIR}/.* {HOMEDIR}/* 2> /dev/null")

    # restore the bash configuration
    with open(f"{HOMEDIR}/.bashrc", 'w') as fout:
        fout.write(bashrc)
    
    # errors should have already been written
    if res > 0:
        if not os.path.exists(FIJIERR):
            os.system(f"echo \"fiji failed\" > {FIJIERR}")
        exit(1)
    else:
        os.system(f"rm -rf {FIJIERR}")

except Exception as e:
    # overwrite error output if there is an actual python exception
    # ensure fiji.err file exists
    # if not os.path.exists(FIJIERR):
    os.system(f"echo \"{str(e)}\" > {FIJIERR}")
    exit(1)

