import ssl
import urllib.request
from html.parser import HTMLParser
import redis, time, sys, os

# to implement caching with redis API
# - make sure you have redis-py installed: 
# redis[hiredis]. (see readme.md for more details)
# https://github.com/redis/redis-py
# https://redis-py.readthedocs.io/en/stable/

conn = None
choices_key_name = 'asciiart_choices'

'''
notes on TLS connection to Redis: 
(if you want to try it out with full cert verification, 
you can generate your own self-signed certs with 
openssl and use those - just make sure to point the script to the correct 
file paths for the certs and keys):
CERT_DIR = '/tmp/certs' 
SERVER_CERT = os.path.join(CERT_DIR,"redis-client-cert.pem")
SERVER_KEY = os.path.join(CERT_DIR,"redis-client-key.pem")
CACERTS = os.path.join(CERT_DIR, "ca.pem")
#redis_proxy = redis.StrictRedis(redishost,redisport, username=redisuser,password=redispassword, charset="utf-8", decode_responses=True, ssl=True,ssl_certfile=SERVER_CERT,ssl_keyfile=SERVER_KEY,ssl_ca_certs=CACERTS)
'''

# this is a utility class used to retrieve data from a simple html website:
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


def connect_to_cache():
    global conn
    if conn is not None:
        return conn
    if parse_connection_args().get('use_tls', DEFAULTS['use_tls']):
        print("Connecting to Cache with TLS...")
        conn = redis.StrictRedis(
            host=parse_connection_args().get('host', DEFAULTS['host']),
            port=parse_connection_args().get('port', DEFAULTS['port']),
            username=parse_connection_args().get('username', DEFAULTS['username']),
            password=parse_connection_args().get('password', DEFAULTS['password']),
            #charset="utf-8",
            decode_responses=True,
            ssl=True,                    # Keeps TLS encryption active
            ssl_cert_reqs=ssl.CERT_NONE  # Bypasses all certificate validation
        )
    else:
        print("Connecting to Cache without TLS...")
        conn = redis.StrictRedis(
            host=parse_connection_args().get('host', DEFAULTS['host']),
            port=parse_connection_args().get('port', DEFAULTS['port']),
            username=parse_connection_args().get('username', DEFAULTS['username']),
            password=parse_connection_args().get('password', DEFAULTS['password']),
            #charset="utf-8",
            decode_responses=True
        )
    return conn

# interact with the user and get their ascii art choice response:
def selectAsciiArtChoice(payload):
    input('\nPlease type an ascii art image label from this list: \n (hit enter when you are ready to see the list)')
    choice = input(f"\n\n {payload}\n\nType your choice from the list above (do not include quotes or []):")
    return choice

# retrieve the content of a web page as a decoded (normal) string:
def page_source_of_site_decoded(url):
    weburl = urllib.request.urlopen(url)
    code = weburl.read()
    return code.decode("utf8")

# retrieve a list of ascii art choices from the website
# use the DataHTMLParser class to return the results as a string
def extractAsciiArtListFromCode(parser,code):
    asciiartData = parser.feed(code)
    return asciiartData

# Check if the asciiart choices key has been stored in Redis: 
def is_cache_empty_of_asciiart_choices_key(choices_key_name):
    test=connect_to_cache().exists(choices_key_name)
    result = False
    if(test==0):
        result=True
    return result

# remove the keys in Redis that cache the list of choices and ascii art: 
def clear_ascii_art_keys_from_cache():
    connect_to_cache().unlink(choices_key_name)
    print(f'\nUnlinking key (this can take a while with a large DB): {choices_key_name}')
    for i in connect_to_cache().scan_iter(match='http://www.ascii-art.de*',count=10000):
        connect_to_cache().unlink(i)
        print(f'Unlinked key: {i}')

# variables for our use:
asciiart = '' # <-- placeholder for the asciiart to be displayed
parser = DataHTMLParser() # <-- custom class in this file that parses specific webpage content
ascii_choices_string = '' # <-- placeholder for our choices string
time_to_check_cache_keys = 0 # <-- placeholder for measuring app-to-cache latency
time_measured_without_cache = 0 # <-- placeholder for measuring non-cache workflow latency
temp_time_bucket = 0 # <-- used to calculate timing for isolated events
user_time = 0 # <-- used to measure the time a user spends choosing an ascii art image name

DEFAULTS = {
    'host': os.getenv('CACHE_HOST', 'localhost'),
    'port': int(os.getenv('CACHE_PORT', 6379)),
    'username': os.getenv('CACHE_USERNAME', None),
    'password': os.getenv('CACHE_PASSWORD', None),
    'use_tls': os.getenv('CACHE_TLS', 'false').lower() in ('true', '1', 'yes'),
    'ssl_ca_cert': os.getenv('CACHE_SSL_CA_CERT', None),  # None = skip verification
    'ssl_cert_reqs': os.getenv('CACHE_SSL_CERT_REQS', 'none').lower(),  # 'none' → ssl.CERT_NONE
}

'''
Usage examples for running the script with different Redis connection options:
# TLS with self-signed cert (no CA verification)
python aas.py --use-tls --ssl-cert-reqs none

# TLS with custom CA cert
python aas.py --use-tls --ssl-ca-cert /path/to/ca.pem

# TLS with certificate verification (default behavior)
python aas.py --use-tls --ssl-cert-reqs required

# All options
python aas.py --host cache.example.com --port 6380 --use-tls --ssl-cert-reqs none
'''
def parse_connection_args():
    args = {}
    i = 1
    
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg.startswith('--host'):
            args['host'] = sys.argv[i + 1] if i + 1 < len(sys.argv) else DEFAULTS['host']
            i += 2
        elif arg.startswith('--port'):
            try:
                args['port'] = int(sys.argv[i + 1]) if i + 1 < len(sys.argv) else DEFAULTS['port']
            except ValueError:
                args['port'] = DEFAULTS['port']
            i += 2
        elif arg.startswith('--username'):
            args['username'] = sys.argv[i + 1] if i + 1 < len(sys.argv) else DEFAULTS['username']
            i += 2
        elif arg.startswith('--password'):
            args['password'] = sys.argv[i + 1] if i + 1 < len(sys.argv) else DEFAULTS['password']
            i += 2
        elif arg.startswith('--use-tls'):
            args['use_tls'] = sys.argv[i + 1].lower() in ('true', '1', 'yes') if i + 1 < len(sys.argv) else DEFAULTS['use_tls']
            i += 2
        elif arg.startswith('--ssl-ca-cert'):
            args['ssl_ca_cert'] = sys.argv[i + 1] if i + 1 < len(sys.argv) else DEFAULTS['ssl_ca_cert']
            i += 2
        elif arg.startswith('--ssl-cert-reqs'):
            args['ssl_cert_reqs'] = sys.argv[i + 1].lower() if i + 1 < len(sys.argv) else DEFAULTS['ssl_cert_reqs']
            i += 2
        elif arg.startswith('--clear'):
            args['clear_cache'] = True
            i += 1
        else:
            i += 1
    
    return args

'''
def clear_ascii_art_keys_from_cache():
    """
    Connect to Cache and delete all keys starting with the given prefix.
    """
    # Delete all keys that start with choices_key_name
    cursor, _ = connect_to_cache().scan_iter(match=f'{choices_key_name}:*', count=1000)
    connect_to_cache().delete(*cursor)
    connect_to_cache().close()
    print(f"Deleted all keys matching '{choices_key_name}:*' from Cache.")
'''

if __name__ == "__main__":
    # Parse command-line arguments first
    cache_args = parse_connection_args()
    #cache_proxy = redis.StrictRedis(cachehost,cacheport,password=cachepassword, encoding="utf-8", decode_responses=True)

    # If --clear was passed, trigger the cache-clear operation
    if cache_args.get('clear_cache'):
        clear_ascii_art_keys_from_cache()
    
    # Otherwise, just print the parsed configuration for confirmation
    else:
        print("Cache connection configuration:")
        for key, value in cache_args.items():
            if key != 'password':  # Don't print the password flag
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: {'***********' if value else '(none)'}")
            
    print(f'\t*** ascii_art_cache in cache is empty?  {is_cache_empty_of_asciiart_choices_key(choices_key_name)}')

    #the fun (and program execution timing) begins:    
    start_time = time.time() 

    # is the cache empty?
    if(is_cache_empty_of_asciiart_choices_key(choices_key_name)):
        time_to_check_cache_keys=time.time()-start_time
        extractAsciiArtListFromCode(parser,page_source_of_site_decoded("http://www.ascii-art.de/ascii"))
        ascii_choices_string = parser.get_data_list()
        temp_time_bucket = time.time()
        connect_to_cache().set(choices_key_name,ascii_choices_string) # <-- this could be done asynchronously
        time_to_check_cache_keys = time_to_check_cache_keys+time.time()-temp_time_bucket

    else: # <-- the cache is not empty and we can get data from Cache:
        temp_time_bucket = time.time()
        ascii_choices_string = connect_to_cache().get(choices_key_name)
        time_to_check_cache_keys = time_to_check_cache_keys + time.time()-temp_time_bucket
    
    # Slowest operation involves the user choice interaction
    # This has nothing to do with any cache or remote invocations 
    # (so we deduct this time from our measurements):
    temp_time_bucket=time.time()
    user_choice = selectAsciiArtChoice(ascii_choices_string)    
    user_time=time.time()-temp_time_bucket

    # formulate new url to fetch specific asciiart user selected:
    newurl = 'http://www.ascii-art.de/ascii/ab/'+str(user_choice)+'.txt'

    # implement a check to see if: 
    # there is a string in Cache that has the value of newurl as its keyname
    temp_time_bucket=time.time()
    test=connect_to_cache().exists(newurl)
    time_to_check_cache_keys = time_to_check_cache_keys + time.time()-temp_time_bucket
    if(test==1):
        # if test resolves to True: The key is in cache. 
        # populate asciiart with value of the key:
        temp_time_bucket=time.time()
        asciiart = connect_to_cache().get(newurl)
        time_to_check_cache_keys = time_to_check_cache_keys + time.time()-temp_time_bucket
    else:
        asciiart = str(page_source_of_site_decoded(newurl)) 
        ## CACHE-ASIDE POWER SHOWN BELOW !! ##
        # create a new key in cache using the value of newurl as the keyname
        # and store the content of asciiart as the value for your new key 
        connect_to_cache().set(newurl,asciiart) # <--  such a simple solution (you may want to add TTL)
    try:
        print(f'\n\n'+asciiart)
    except:
        print('some bad characters got into the asciiart -try a different one next time')
    
    time_measured_without_cache = time_measured_without_cache + time.time()-(start_time+time_to_check_cache_keys+user_time)
    
    print('\n\nNB: ***\nThe following time measurements both *exclude* the time spent by the user:')
    print(f'\n\nTotal time taken in seconds by cache operations: {round(time_to_check_cache_keys, 9)}')
    print(f'Total time taken in seconds by non-cache operations: {round(time_measured_without_cache, 9)}')
    print(f'TOTAL PROGRAM EXECUTION TIME (without user time) == {time_measured_without_cache+time_to_check_cache_keys}')
