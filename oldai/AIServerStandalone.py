"""
Script for starting a http server that proxies AI response requests to the ai and returns the result.
Does the same as AiServer.py, but uses standard python only, no Flask.
"""

from http.server import BaseHTTPRequestHandler
import socketserver
import json
import logging
import threading
import random

import AI
from AIServer import calculate_next_move, get_backup_move

show_move = 1 # set to 1 if you're a dirty rotten cheater
PORT = 5001
logger = logging.getLogger("AIServer")

# global ai result variable.
# set by worker thread "calculate_next_move",
# read by ai_retrieve requests.
# initialize to something that is a valid backup input in most cases,
# so eventual ai-retrieve-deadlocks can be resolved with a restart of this server.
ai_result = "move1"
# global handle to actual AI
Artificial = AI.AI()
LastActions = []


class AIServer(BaseHTTPRequestHandler):
    def get_json(self):
        content_len = int(self.headers.get('content-length', 0))
        content = self.rfile.read(content_len)
        return json.loads(content.decode())
    
    def ai_invoke(self):
        global ai_result
        self.send_response(200)
        self.end_headers()
        
        try:
            battle_state = self.get_json()
        except ValueError:
            logger.exception("ai_invoke got called with nothing, or something not json-decodable.")
            battle_state = {}
        logger.info("invoking AI... submitted JSON: %s" % battle_state)
    
        # reset global ai result variable and asynchronously invoke the ai.
        # Doesn't have to be a thread, could also be a greenlet or something,
        # But a thread is easy, in the stdlib and works fine here.
        ai_result = None
        threading.Thread(target=calculate_next_move, args=(battle_state,)).start()

    def do_POST(self):
        if self.path != "/ai_invoke":
            self.send_response(404)
            self.end_headers()
            return
        self.ai_invoke()

    def do_GET(self):
        if self.path == "/ai_retrieve":
            self.send_response(200)
            self.end_headers()
            if ai_result:
                self.wfile.write(ai_result.encode())
        elif self.path == "/ai_invoke":
            self.ai_invoke()
        else:
            self.send_response(404)
            self.end_headers()
            return

if __name__ == "__main__":
    httpd = socketserver.TCPServer(("localhost", PORT), AIServer)
    print("Serving on port {}".format(PORT))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down...")
