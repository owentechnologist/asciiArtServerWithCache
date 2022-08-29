from socketserver import DatagramRequestHandler
import urllib.request
from html.parser import HTMLParser
import redis, time, sys

# to implement caching with redis - make sure you have installed: 
# https://github.com/redis/redis-py
# https://redis-py.readthedocs.io/en/stable/

# TODO: fix the host and port to match your redis database endpoint:
redis_proxy = redis.Redis(host='192.168.1.20', port=12000, decode_responses=True)

class DataHTMLParser(HTMLParser):

    def get_data_list(self):
        global choices_list
        print(f'choices_list length == {len(choices_list)}')
        string_data_list = ''
        for i in choices_list:
            string_data_list=string_data_list+' '+str(i)
        return string_data_list

    def handle_data(self, data: str) -> None:
        global shouldProcess
        if(shouldProcess):
            global choices_list
            if(bool(data.splitlines()[0].strip())):
                if(bool(data.splitlines()[0].strip(' . '))):
                    choices_list.append(data.splitlines())
    
    def handle_starttag(self, tag, attrs):
        global shouldProcess

        if(tag.startswith('a')):
            for i in attrs:
                x = str(i)
                y = x.split('.')
                if(len(y))>1:
                    if((y[1])[0] == ('t')):
                        shouldProcess = True
        else:
            shouldProcess = False

    def handle_endtag(self, tag):
        pass

    def handle_comment(self, data):
        pass

    def handle_entityref(self, name):
        pass

    def handle_charref(self, name):
        pass

    def handle_decl(self, data):
        pass

def selectAsciiArtChoice(payload):
    input('\nPlease type an ascii art image label from this list: \n (hit enter when you are ready to see the list)')
    choice = input(f"\n\n {payload}\n\nType your choice from the list above (do not include quotes or []):")
    return choice

def code_of_site_decoded(url):
    weburl = urllib.request.urlopen(url)
    code = weburl.read()
    return code.decode("utf8")

def extractAsciiArtListFromCode(parser,code):
    asciiartData = parser.feed(code)
    #print(asciiartData)
    return asciiartData

# Check if the asciiart choices key has been stored in Redis: 
def is_redis_empty_of_asciiart_choices_key():
    global choices_key_name
    test=redis_proxy.exists(choices_key_name)
    result = False
    if(test==0):
        result=True
    return result
    
def clear_redis__choices_cache():
    redis_proxy.delete(choices_key_name)

# variables for our use:
choices_key_name = 'asciiart_choices'
choices_list = list()
asciiart = '' # <-- placeholder for the asciiart to be displayed
parser = DataHTMLParser() # custom class in this file
shouldProcess = False
choices_string = '' # <-- placeholder for our choices string
time_to_check_redis_keys = 0 # <-- placeholder for measuring app-to-redis latency
time_measured_without_redis = 0 # <-- placeholder for measuring non-redis workflow latency
temp_time_bucket = 0 # <-- in case we need to subtract time taken by one path
user_time = 0

if __name__ == "__main__":
    if len(sys.argv)>1:
        #assume the extra arg means the user wanted to clear the redis cache
        clear_redis__choices_cache()

    
    print(f'redis does *not* have the choices key? {is_redis_empty_of_asciiart_choices_key()}')
    #the fun begins:    
    start_time = time.time() 
    if(is_redis_empty_of_asciiart_choices_key()):
        time_to_check_redis_keys=time.time()-start_time
        extractAsciiArtListFromCode(parser,code_of_site_decoded("http://www.ascii-art.de/ascii"))
        choices_string = parser.get_data_list()
        temp_time_bucket = time.time()
        redis_proxy.set(choices_key_name,choices_string) # <-- this could be done asynchronously
        time_to_check_redis_keys = time_to_check_redis_keys+time.time()-temp_time_bucket
    else: # <-- the choices key exists and we can get it from Redis:
        temp_time_bucket = time.time()
        choices_string = redis_proxy.get(choices_key_name)
        time_to_check_redis_keys = time_to_check_redis_keys + time.time()-temp_time_bucket
    
    # slowest operation involves the user and all times are affected equally:
    temp_time_bucket=time.time()
    user_choice = selectAsciiArtChoice(choices_string)    
    user_time=time.time()-temp_time_bucket

    #formulate new url to fetch specific asciiart user selected:
    newurl = 'http://www.ascii-art.de/ascii/ab/'+str(user_choice)+'.txt'

    # implement a check to see if: 
    # there is a string in Redis that has the value of newurl as its keyname
    temp_time_bucket=time.time()
    test=redis_proxy.exists(newurl)
    time_to_check_redis_keys = time_to_check_redis_keys + time.time()-temp_time_bucket
    if(test==1):
        # if test resolves to True: The key is in redis. 
        # populate asciiart with value of the key:
        temp_time_bucket=time.time()
        asciiart = redis_proxy.get(newurl)
        time_to_check_redis_keys = time_to_check_redis_keys + time.time()-temp_time_bucket
    else:
        asciiart = str(code_of_site_decoded(newurl)) 
        ## FIXME FIXME FIXME !! ##
        # create a new key in redis using the value of newurl as the keyname
        # and store the content of asciiart as the value for your new key 
        # redis_proxy.set(newurl,asciiart) # <--solution
    try:
        print(f'\n\n'+asciiart)
    except:
        print('some bad characters got into the asciiart -try a different one next time')
    
    time_measured_without_redis = time_measured_without_redis + time.time()-(start_time+time_to_check_redis_keys+user_time)
    
    print('\n\nNB: ***\nThe following time measurements both *exclude* the time spent by the user when selecting asciiart')
    print(f'\n\nTotal time taken in seconds by redis operations: {round(time_to_check_redis_keys, 9)}')
    print(f'Total time taken in seconds by non-redis operations: {round(time_measured_without_redis, 9)}')
    print(f'TOTAL PROGRAM EXECUTION TIME (without user time) == {time_measured_without_redis+time_to_check_redis_keys}')
    
