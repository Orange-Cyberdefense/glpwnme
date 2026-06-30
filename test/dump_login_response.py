#!/usr/bin/env python3

import json
import argparse
import requests
from glpwnme.exploits.utils import *

class TestHook:
    def __init__(self):
        self.json_res = {}

    def serialize_response(self, response, *args, **kwargs):
        if response.request.method == "POST":
            self.json_res = {
                "status_code": response.status_code,
                "url": response.url,
                "headers": dict(response.headers),
                "text": response.text,
            }

def main():
    parser = argparse.ArgumentParser(
        description="Capture a GLPI login response and save it as JSON."
    )
    parser.add_argument("-t", "--target", help="Base URL of the GLPI instance (e.g. https://glpi.example.com/glpi)")
    parser.add_argument("-u", "--username", help="GLPI username")
    parser.add_argument("-p", "--password", help="GLPI password")
    parser.add_argument("-o", "--outputfile", help="Output JSON file")

    args = parser.parse_args()

    hookable = TestHook()

    session = GlpiSession(args.target, credentials=GlpiCredentials())

    session.sess.hooks['response'].append(hookable.serialize_response)
    session.login(args.username, args.password)

    if hookable.json_res:
        with open(args.outputfile, "w", encoding="utf-8") as f:
            # json.dump(hookable.json_res, fp=f)
            f.write(session.get(session.current_url).text)
    else:
        print(f"Failed recovering response")

if __name__ == "__main__":
    main()
