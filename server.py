import string, cgi, time, os
from os import curdir, sep
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import json
import numpy as np


class SuggestServer(BaseHTTPRequestHandler):

    def __init__(self, *args, **kwargs):

        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)
        
        # Load lane dictionary
        with open('lanes.json') as data_file:
            self.lane_dict = json.load(data_file)

        print(self.lane_dict)

        # Set up relation matrix

    def do_POST(self):
        if self.path == '/suggestions':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            #self.send_header('Content-type', 'text/html')
            self.end_headers()

            #summoner_name = self.path.split('/suggestions/',1)[1]
            content_len = int(self.headers.getheader('content-length', 0))
            summoner_name = self.rfile.read(content_len)

            # Cut out the 'summonerName=' part
            summoner_name = summoner_name[13:]
            
            print(summoner_name)
            response = self.retrieve_data(summoner_name)

            # send response
            #self.wfile.write(summoner_name)
            json.dump(response, self.wfile)

            return

        elif self.path == "/" or self.path.endswith('.html'):
            
            #Open the static file requested and send it
            f = open(curdir + sep + self.path + 'index.html') 
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()
            self.wfile.write(f.read())
            f.close()
    
    def do_GET(self):

        if self.path == "/" or self.path.endswith('.html'):
            
            #Open the static file requested and send it
            f = open(curdir + sep + self.path + 'index.html') 
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()
            self.wfile.write(f.read())
            f.close()

    def retrieve_data(self, summoner_name):
        #TODO: temp
        return {"summoner_name": summoner_name}

def main():
    try:
        # you can specify any port you want by changing '8000'
        server = HTTPServer(('', 8000), SuggestServer)
        print 'starting httpserver...'
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down server'
        server.socket.close()

if __name__ == '__main__':
    main()

