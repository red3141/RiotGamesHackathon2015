import string, cgi, time, os
from os import curdir, sep
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import json
import numpy as np
from copy import deepcopy
from ChampionMastery import getSummonerId, getChampionMastery, getChampionMasteryByRank
import MySQLdb

NUM_CHAMPS = 127
IMAGE_PREFIX = 'http://ddragon.leagueoflegends.com/cdn/5.2.1/img/champion/'
QUERY = 'SELECT (SELECT COUNT(*) FROM summoner WHERE masteryRank >= 3 AND (championId = {0} OR championId = {1})) - (SELECT COUNT(DISTINCT summonerId) FROM summoner WHERE masteryRank >= 3 AND (championId = {0} OR championId = {1})) AS difference'
#QUERY = 'SELECT COUNT(*) FROM summoner WHERE masteryRank >= 3 AND (championId = {0} OR championId = {1})'
#QUERY2 = 'SELECT COUNT(DISTINCT SummonerId) FROM summoner WHERE masteryRank >= 3 AND (championId = {0} OR championId = {1})'

HOST = 'localhost'
USER = 'root'
PASSWD = 'root'
DB = 'riothackaton'

class SuggestServer(BaseHTTPRequestHandler):

    def __init__(self, *args, **kwargs):

        # Load index-champ-meta-id mapping array
        with open('champion_meta_id.json') as data_file:
            self.champion_list = json.load(data_file)

        # Load Champ ID mapping dictionary
        with open('champion_id.json') as data_file:
            self.champ_id_dict = json.load(data_file)
        
        # Load Champ ID to index mapping dictionary
        with open('id_to_index.json') as data_file:
            self.id_to_index = json.load(data_file)
        
        # Load Champ ID to url mapping dictionary
        with open('id_to_url.json') as data_file:
            self.id_to_url = json.load(data_file)

        # Connect to the database
        self.db = MySQLdb.connect(host=HOST,
                                  user=USER,
                                  passwd=PASSWD,
                                  db=DB)

        self.cur = self.db.cursor()

        # Build lane index masks for the relation matrix
        self.top_mask = np.ones((NUM_CHAMPS), dtype=np.int32)
        self.mid_mask = np.ones((NUM_CHAMPS), dtype=np.int32)
        self.jungle_mask = np.ones((NUM_CHAMPS), dtype=np.int32)
        self.support_mask = np.ones((NUM_CHAMPS), dtype=np.int32)
        self.adc_mask = np.ones((NUM_CHAMPS), dtype=np.int32)

        for i in range(len(self.champ_id_dict)):
            if 'Top' in self.champion_list[i][1]:
                self.top_mask[i] = 0
            if 'Mid' in self.champion_list[i][1]:
                self.mid_mask[i] = 0
            if 'Jungle' in self.champion_list[i][1]:
                self.jungle_mask[i] = 0
            if 'Support' in self.champion_list[i][1]:
                self.support_mask[i] = 0
            if 'ADC' in self.champion_list[i][1]:
                self.adc_mask[i] = 0


        # Set up relation matrix
        self.champ_matrix = np.zeros((NUM_CHAMPS, NUM_CHAMPS))

        # build some data just for testing
        self.build_matrix()

        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

    def build_matrix(self):
        # Loop through one triangle of the matrix
        for i in range(NUM_CHAMPS):
            for j in range(i):
                if i != j:
                    sql_query = QUERY.format(i,j)

                    # Run SQL Query
                    self.cur.execute(sql_query)

                    result = self.cur.fetchone()[0]

                    # Save to matrix
                    self.champ_matrix[i][j] = result
                    self.champ_matrix[j][i] = result

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
            
            response = self.retrieve_data(summoner_name)
            print(response)
            # send response
            #self.wfile.write(summoner_name)
            json.dump(response, self.wfile)

            return

        elif self.path == "/" or self.path.endswith('.html'):
            
            #Open the static file requested and send it
            f = open(curdir + sep + self.path + '../index.html') 
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()
            self.wfile.write(f.read())
            f.close()
    
    def do_GET(self):

        if self.path == "/" or self.path.endswith('.html'):
            
            #Open the static file requested and send it
            f = open(curdir + sep + self.path + '../index.html') 
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()
            self.wfile.write(f.read())
            f.close()

    def retrieve_data(self, summoner_name):
        # Do the api call to get the summoner's "main" champions
        main_champs = getChampionMasteryByRank(getSummonerId(summoner_name), 3)

        top_champs = [self.id_to_index[str(x)] for x in main_champs]

        # Figure out suggestions
        condensed = self.champ_matrix[top_champs][:]

        # Sum their top 5 champs together for an aggregate score
        condensed = np.sum(condensed, axis=0)

        # Zero-out champs that they already play a lot
        for i in top_champs:
            #condensed[:][i] = 0
            condensed[i] = 0

        # Find the top champs for each role
        top = deepcopy(condensed)
        top[self.top_mask==1] = 0
        max_top = np.argmax(top)
        
        mid = deepcopy(condensed)
        mid[self.mid_mask==1] = 0
        max_mid = np.argmax(mid)
        
        jungle = deepcopy(condensed)
        jungle[self.jungle_mask==1] = 0
        max_jungle = np.argmax(jungle)
        
        support = deepcopy(condensed)
        support[self.support_mask==1] = 0
        max_support = np.argmax(support)
        
        adc = deepcopy(condensed)
        adc[self.adc_mask==1] = 0
        max_adc = np.argmax(adc)

        return {'top':{"displayName":self.champion_list[max_top][0],
                       "url":IMAGE_PREFIX+self.id_to_url[str(self.champion_list[max_top][2])]},
                'mid':{"displayName":self.champion_list[max_mid][0],
                       "url":IMAGE_PREFIX+self.id_to_url[str(self.champion_list[max_mid][2])]},
                'jungle':{"displayName":self.champion_list[max_jungle][0],
                          "url":IMAGE_PREFIX+self.id_to_url[str(self.champion_list[max_jungle][2])]},
                'support':{"displayName":self.champion_list[max_support][0],
                           "url":IMAGE_PREFIX+self.id_to_url[str(self.champion_list[max_support][2])]},
                'adc':{"displayName":self.champion_list[max_adc][0],
                       "url":IMAGE_PREFIX+self.id_to_url[str(self.champion_list[max_adc][2])]}
                }

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

