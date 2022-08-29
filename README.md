### This is a simple example written in python 
### It showcases Redis acting as a cache for a remote website that serves ascii art
## There are two areas you need to edit to get it to work as intended:
## line 10 (make sure you are using proper host and port)
## line 139 (uncomment the code here when you are ready to enable caching the individual ascii-art images)

### the user will be presented with a busy printout of many ascii art choices
### each choice will look like this:
<code>['acorn']</code>

### The user should use the text inside the single quotes to indicate their choice

### To run the program you execute:

<code>
python3 aas.py
</code>

### ^^ assumes you have redis-py installed

## to implement caching with redis - make sure you have this python library installed: 
### https://github.com/redis/redis-py
### https://redis-py.readthedocs.io/en/stable/

## You can start the program with no cached data in Redis by adding an additional argument:

<code>
python3 aas.py clean
</code>


### The first time the program is run you will see results like this:

<code>
Total time taken in seconds by redis operations: 0.00931716

Total time taken in seconds by non-redis operations: 1.080892801

TOTAL PROGRAM EXECUTION TIME (without user time) == 1.0902099609375
</code>

### Then, the main key that lists the options will be in redis and you will see results like this:

<code>
Total time taken in seconds by redis operations: 0.006021738

Total time taken in seconds by non-redis operations: 0.30087924

TOTAL PROGRAM EXECUTION TIME (without user time) == 0.3069009780883789
</code>

### If you then implement the caching of the individual ascii art payloads you will see results like this:

<code>
Total time taken in seconds by redis operations: 0.0131917

Total time taken in seconds by non-redis operations: 0.002849102

TOTAL PROGRAM EXECUTION TIME (without user time) == 0.016040802001953125
</code>

## You should see that using the Cache-aside pattern makes your client experience better 
## The application will also scale much better if you add additional clients -- as they will all share the same cached values.
## The ascii art website will be happier too :) 