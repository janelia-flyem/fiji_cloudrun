"""Web server that calls headless fiji.

This web server executes fiji based on the given commands and
the specified locations for inputs and outputs.  This service should
be behind an authenticated service like cloud run.  Even with authentication,
this container attempts to maintain a stateless environment
so that results are idempotent and predictable.  As such,
this function calls another python script as a 'fiji' user
and attempts to erase any files in the home or run directory.

Note: should only handle one request at a time.
"""

import os

from flask import Flask, Response, request, make_response
from flask_cors import CORS
import json
import logging
import pwd

# files containing fiji console output
FIJIOUT = "/tmp/fiji.out"
FIJIERR = "/tmp/fiji.err"
CONFIGFILE = "/tmp/config.json"

app = Flask(__name__)

# TODO: Limit origin list here: CORS(app, origins=[...])
CORS(app)

logger = logging.getLogger(__name__)

# delete temporary files
def cleanup_temp_files():
        """
        try:
            os.remove("/tmp/fiji.out")
        except OSError:
            pass
        try:
            os.remove("/tmp/fiji.err")
        except OSError:
            pass
        try:
            os.remove("/tmp/config.json")
        except OSError:
            pass
        """
        try:
            os.system("rm -rf /tmp/* /tmp/.* 2> /dev/null")
        except Exception:
            pass

@app.route('/', methods=["POST"])
def run_fiji():
    """Run fiji headless command.

    The user can map cloud storage and embedded strings
    as inputs or outputs.

    JSON body:

    {
        "command": "fiji headless commands",
        "input-map": {
            "file1": "bucket/name",
            "file2": "bucket/name2",
        },
        "output-map": {
            "outfile1": "bucket/oname",
            "outfile2": "bucket/oname2",
        }
        "input-str": {
            "file3": "foo bar script"
        }
            

    }
    """

    try:
        # launch fork with for user
        uid = pwd.getpwnam('fiji')[2]
        input_file  = request.get_json()
  
        # write config to /tmp scratchpad
        with open("/tmp/config.json", 'w') as fout:
            fout.write(json.dumps(input_file))

        # run command as fiji user to sandbox
        pid = os.fork()
        if pid == 0:
            try:
                os.setuid(uid)
                os.system("python process_request.py")
            finally:
                os._exit(0)
        os.waitpid(pid, 0)

        if os.path.exists("/tmp/fiji.err"):
            fin = open("/tmp/fiji.err")
            fiji_resp = fin.read()
            return Response(fiji_resp, 400)

        # read results and send
        fin = open("/tmp/fiji.out")
        fiji_resp = fin.read()
      
        # remove temporary files
        cleanup_temp_files()

        r = make_response(fiji_resp.encode())
        r.headers.set('Content-Type', 'text/html')
        return r
    except Exception as e:
        cleanup_temp_files()
        return Response(str(e), 400)

if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0',port=int(os.environ.get('PORT', 8080)))
