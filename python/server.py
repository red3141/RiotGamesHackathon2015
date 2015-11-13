import string, cgi, time, os
from os import curdir, sep
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import json
import numpy as np
from copy import deepcopy
from ChampionMastery import getSummonerId, getChampionMastery, getChampionMasteryByRank
import MySQLdb
import cPickle as pickle
import os.path
from urllib2 import HTTPError

NUM_CHAMPS = 127
IMAGE_PREFIX = 'http://ddragon.leagueoflegends.com/cdn/5.2.1/img/champion/'
#QUERY = 'SELECT (SELECT COUNT(*) FROM (SELECT masteryPoints, masteryRank, region, summonerId, championId FROM summoner GROUP BY masteryPoints, masteryRank, region, summonerId, championId) a WHERE masteryRank >= 3 AND (championId = {0} OR championId = {1})) - (SELECT COUNT(DISTINCT summonerId) FROM summoner WHERE masteryRank >= 3 AND (championId = {0} OR championId = {1})) AS difference'
QUERY = 'SELECT (SELECT COUNT(*) FROM summoner WHERE masteryRank >= {2} AND (championId = {0} OR championId = {1})) - (SELECT COUNT(DISTINCT summonerId) FROM summoner WHERE masteryRank >= {2} AND (championId = {0} OR championId = {1})) AS difference'

HOST = 'localhost'
USER = 'root'
PASSWD = 'root'
DB = 'riothackaton'

PICKLE_FILE = 'matrix.p'

def print_response(response):
    print("Top: %s, %s, %s" % (response['top'][0]['displayName'], response['top'][1]['displayName'], response['top'][2]['displayName']))
    print("Jungle: %s, %s, %s" % (response['jungle'][0]['displayName'], response['jungle'][1]['displayName'], response['jungle'][2]['displayName']))
    print("Mid: %s, %s, %s" % (response['mid'][0]['displayName'], response['mid'][1]['displayName'], response['mid'][2]['displayName']))
    print("ADC: %s, %s, %s" % (response['adc'][0]['displayName'], response['adc'][1]['displayName'], response['adc'][2]['displayName']))
    print("Support: %s, %s, %s" % (response['support'][0]['displayName'], response['support'][1]['displayName'],response['support'][2]['displayName']))
    """
    print("Top: %s" % response['top']['displayName'])
    print("Jungle: %s" % response['jungle']['displayName'])
    print("Mid: %s" % response['mid']['displayName'])
    print("ADC: %s" % response['adc']['displayName'])
    print("Support: %s" % response['support']['displayName'])
    """

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

        # Load pickle file if it exists, otherwise generate it
        if os.path.isfile(PICKLE_FILE):
            data = pickle.load(open(PICKLE_FILE, 'rb'))

            self.champ_matrix = data
        else:
            # build the data
            self.build_matrix()

            pickle.dump(self.champ_matrix, open(PICKLE_FILE, 'wb'))

        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

    def print_chart(self):
        for i,row in enumerate(self.champ_matrix):
            print(self.champion_list[i][0] + " " + str(row))


    def build_matrix(self):
        # Loop through one triangle of the matrix
        for i in range(NUM_CHAMPS):
            for j in range(i):
                if i != j:
                    print("row: %s column: %s" % (i,j))
                    #k=4 
                    for k in [3,4,5]:
                        sql_query = QUERY.format(self.champion_list[i][2],self.champion_list[j][2],k)

                        # Run SQL Query
                        self.cur.execute(sql_query)

                        result = self.cur.fetchone()[0]

                        # Save to matrix
                        self.champ_matrix[i][j] += result
                        self.champ_matrix[j][i] += result

        #normalize columns (2nd index)
        for j in range(NUM_CHAMPS):
            total = sum(self.champ_matrix[:][j])
            self.champ_matrix[:][j] /= total
            #total = sum(self.champ_matrix[j][:])
            #self.champ_matrix[j][:] /= total
                
    def do_POST(self):
        if self.path == '/suggestions':
            #summoner_name = self.path.split('/suggestions/',1)[1]
            content_len = int(self.headers.getheader('content-length', 0))
            summoner_name = self.rfile.read(content_len)

            # Cut out the 'summonerName=' part
            summoner_name = summoner_name[13:]
            response = self.retrieve_data(summoner_name)
            if response is None:
              self.send_response(404)
              self.end_headers()
              return
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            print_response(response)

            #json.dump(response, open('test.json', 'wb'))

            # send response
            #self.wfile.write(summoner_name)
            json.dump(response, self.wfile)

            return

        elif self.path == "/" or self.path.endswith('.html'):
            
            #Open the static file requested and send it
            #f = open(curdir + sep + self.path + '../index.html') 
            f = open(curdir + sep + self.path + '../Frontend/html/site.html') 
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()
            self.wfile.write(f.read())
            f.close()
        else:
            f = open(self.path) 
            self.send_response(200)
            self.send_header('Content-type','text/css')
            self.end_headers()
            self.wfile.write(f.read())
            f.close()
    
    def do_GET(self):

        if self.path == '/chart':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            chart = '<table style="width:100%">'
            
            # Put in the titles
            chart += '<tr><td></td>'
            for i in range(NUM_CHAMPS):
                chart += '<td>%s</td>' % self.champion_list[i][0]
            chart += '</tr>'

            for i in range(NUM_CHAMPS):
                chart += '<tr><td>%s</td>' % self.champion_list[i][0]
                for j in range(NUM_CHAMPS):
                    chart += '<td>%s</td>' % self.champ_matrix[i][j]
                chart += '</tr>'
            chart += '</table>'

            # send response
            self.wfile.write(chart)
        elif self.path == "/":
            
            #Open the static file requested and send it
            #f = open(curdir + sep + self.path + '../index.html') 
            f = open(curdir + sep + self.path + '../Frontend/html/site.html') 
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()
            self.wfile.write(f.read())
            f.close()
        elif self.path.endswith('.css'):
            f = open(curdir + './Frontend' +self.path) 
            self.send_response(200)
            self.send_header('Content-type','text/css')
            self.end_headers()
            self.wfile.write(f.read())
            f.close()
        elif self.path.endswith('.js'):
            f = open(curdir + './Frontend' +self.path) 
            self.send_response(200)
            self.send_header('Content-type','text/js')
            self.end_headers()
            self.wfile.write(f.read())
            f.close()
        elif self.path.endswith('.png'):
            f = open(curdir + './Frontend' +self.path) 
            self.send_response(200)
            self.send_header('Content-type','image/png')
            self.end_headers()
            self.wfile.write(f.read())
            f.close()
        elif self.path.endswith('.jpg'):
            f = open(curdir + './Frontend' +self.path) 
            self.send_response(200)
            self.send_header('Content-type','image/jpg')
            self.end_headers()
            self.wfile.write(f.read())
            f.close()

    def retrieve_data(self, summoner_name):
        # Do the api call to get the summoner's "main" champions
        try:
          summoner_id = getSummonerId(summoner_name)
        except HTTPError as e:
          return None

        played_champs_id = getChampionMasteryByRank(summoner_id, 3) # all champs above X mastery
        main_champs = getChampionMastery(summoner_id, 5) # top X champs

        played_champs = [self.id_to_index[str(x)] for x in played_champs_id]
        top_champs = [self.id_to_index[str(x)] for x in main_champs]

        # Figure out suggestions
        #condensed = deepcopy(self.champ_matrix[top_champs][:])

        # Weighted sum version
        #condensed = np.zeros((NUM_CHAMPS),dtype=np.float64)
        condensed = np.zeros((NUM_CHAMPS))
        weight = 5
        for i in top_champs:
            condensed += self.champ_matrix[i][:]*weight
            weight -= 1

        # Sum their top 5 champs together for an aggregate score
        #condensed = np.sum(condensed, axis=0)

        # Zero-out champs that they already play a lot
        #for i in top_champs:
        for i in played_champs:
            #condensed[:][i] = 0
            condensed[i] = 0

        # record the top n for each role
        n = 3

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

        n_top = [max_top]
        n_mid = [max_mid]
        n_jungle = [max_jungle]
        n_support = [max_support]
        n_adc = [max_adc]
        for i in range(n-1):
            top[max_top] = 0
            max_top = np.argmax(top)
            n_top.append(max_top)
            
            mid[max_mid] = 0
            max_mid = np.argmax(mid)
            n_mid.append(max_mid)
            
            jungle[max_jungle] = 0
            max_jungle = np.argmax(jungle)
            n_jungle.append(max_jungle)
            
            support[max_support] = 0
            max_support = np.argmax(support)
            n_support.append(max_support)
            
            adc[max_adc] = 0
            max_adc = np.argmax(adc)
            n_adc.append(max_adc)

        print("TOP:")
        print([self.champion_list[x][0] for x in n_top])
        print("MID:")
        print([self.champion_list[x][0] for x in n_mid])
        print("JUNGLE:")
        print([self.champion_list[x][0] for x in n_jungle])
        print("SUPPORT:")
        print([self.champion_list[x][0] for x in n_support])
        print("ADC:")
        print([self.champion_list[x][0] for x in n_adc])
        """
        print("TOP: %s, %s, %s"% ((self.champion_list[x][0] for x in n_top)))
        print("MID: %s, %s, %s"% [self.champion_list[x][0] for x in n_mid])
        print("JUNGLE: %s, %s, %s"% [self.champion_list[x][0] for x in n_jungle])
        print("SUPPORT: %s, %s, %s"% [self.champion_list[x][0] for x in n_support])
        print("ADC: %s, %s, %s"% [self.champion_list[x][0] for x in n_adc])
        """
            
        return {'top':[{"displayName":self.champion_list[x][0],
                       "url":IMAGE_PREFIX+self.id_to_url[str(self.champion_list[x][2])]} for x in n_top],
                'mid':[{"displayName":self.champion_list[x][0],
                       "url":IMAGE_PREFIX+self.id_to_url[str(self.champion_list[x][2])]} for x in n_mid],
                'jungle':[{"displayName":self.champion_list[x][0],
                          "url":IMAGE_PREFIX+self.id_to_url[str(self.champion_list[x][2])]} for x in n_jungle],
                'support':[{"displayName":self.champion_list[x][0],
                           "url":IMAGE_PREFIX+self.id_to_url[str(self.champion_list[x][2])]} for x in n_support],
                'adc':[{"displayName":self.champion_list[x][0],
                       "url":IMAGE_PREFIX+self.id_to_url[str(self.champion_list[x][2])]} for x in n_adc]
                }

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

