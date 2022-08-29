#from msilib import type_string
#from socketserver import DatagramRequestHandler
import urllib.request
from html.parser import HTMLParser
import redis, time, sys

# to implement caching with redis - make sure you have installed: 
# https://github.com/redis/redis-py
# https://redis-py.readthedocs.io/en/stable/

# TODO: fix the host and port to match your redis database endpoint:
redis_proxy = redis.Redis(host='192.168.1.20', port=12000, decode_responses=True)

class DataHTMLParser(HTMLParser):

    def __init__(self):
        super(). __init__()
        self.choices_list = list()
        self.should_process = False

    def get_data_list(self):
        print(f'choices_list length == {len(self.choices_list)}')
        string_data_list = ''
        for i in self.choices_list:
            string_data_list=string_data_list+' '+str(i)
        return string_data_list

    def handle_data(self, data: str) -> None:
        if(self.should_process):
            if(bool(data.splitlines()[0].strip())):
                if(bool(data.splitlines()[0].strip(' . '))):
                    self.choices_list.append(data.splitlines())
    
    def handle_starttag(self, tag, attrs):
        if(tag.startswith('a')):
            for i in attrs:
                x = str(i)
                y = x.split('.')
                if(len(y))>1:
                    if((y[1])[0] == ('t')):
                        self.should_process = True
        else:
            self.should_process = False


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
    return asciiartData

# Check if the asciiart choices key has been stored in Redis: 
def is_redis_empty_of_asciiart_choices_key(choices_key_name):
    test=redis_proxy.exists(choices_key_name)
    result = False
    if(test==0):
        result=True
    return result

# remove the keys in Redis that cache the list of choices and ascii art: 
def clear_ascii_art_keys_from_redis(choices_key_name):
    redis_proxy.unlink(choices_key_name)
    print(f'\nUnlinked key: {choices_key_name}')
    for i in redis_proxy.scan_iter(match='http://www.ascii-art.de*',count=10000):
        redis_proxy.unlink(i)
        print(f'Unlinked key: {i}')

# variables for our use:
choices_key_name = 'asciiart_choices'
asciiart = '' # <-- placeholder for the asciiart to be displayed
parser = DataHTMLParser() # <-- custom class in this file that parses specific webpage content
ascii_choices_string = '' # <-- placeholder for our choices string
time_to_check_redis_keys = 0 # <-- placeholder for measuring app-to-redis latency
time_measured_without_redis = 0 # <-- placeholder for measuring non-redis workflow latency
temp_time_bucket = 0 # <-- used to calculate timing for isolated events
user_time = 0 # <-- used to measure the time a user spends choosing an ascii art image name

if __name__ == "__main__":
    if len(sys.argv)>1:
        #assume the extra arg means the user wanted to clear the redis cache
        clear_ascii_art_keys_from_redis(choices_key_name)

    print(f'\t*** ascii_art_cache in redis is empty?  {is_redis_empty_of_asciiart_choices_key(choices_key_name)}')
    #the fun and program execution timing begins:    
    start_time = time.time() 
    if(is_redis_empty_of_asciiart_choices_key(choices_key_name)):
        time_to_check_redis_keys=time.time()-start_time
        extractAsciiArtListFromCode(parser,code_of_site_decoded("http://www.ascii-art.de/ascii"))
        ascii_choices_string = parser.get_data_list()
        temp_time_bucket = time.time()
        redis_proxy.set(choices_key_name,ascii_choices_string) # <-- this could be done asynchronously
        time_to_check_redis_keys = time_to_check_redis_keys+time.time()-temp_time_bucket
    else: # <-- the choices key exists and we can get it from Redis:
        temp_time_bucket = time.time()
        ascii_choices_string = redis_proxy.get(choices_key_name)
        time_to_check_redis_keys = time_to_check_redis_keys + time.time()-temp_time_bucket
    
    # slowest operation involves the user and all times are affected equally:
    temp_time_bucket=time.time()
    user_choice = selectAsciiArtChoice(ascii_choices_string)    
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
        # redis_proxy.set(newurl,asciiart) # <-- uncomment this for solution
    try:
        print(f'\n\n'+asciiart)
    except:
        print('some bad characters got into the asciiart -try a different one next time')
    
    time_measured_without_redis = time_measured_without_redis + time.time()-(start_time+time_to_check_redis_keys+user_time)
    
    print('\n\nNB: ***\nThe following time measurements both *exclude* the time spent by the user:')
    print(f'\n\nTotal time taken in seconds by redis operations: {round(time_to_check_redis_keys, 9)}')
    print(f'Total time taken in seconds by non-redis operations: {round(time_measured_without_redis, 9)}')
    print(f'TOTAL PROGRAM EXECUTION TIME (without user time) == {time_measured_without_redis+time_to_check_redis_keys}')
    
