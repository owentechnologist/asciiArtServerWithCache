This is a simple example written in python of Redis acting as a cache for a remote website that serves ascii art.

To run it you can execute:

<code>

python3 aas.py

</code>

^^ assumes you have redis-py installed

# to implement caching with redis - make sure you have this python library installed: 
# https://github.com/redis/redis-py
# https://redis-py.readthedocs.io/en/stable/

You can start the program and clear the main key cached in Redis by adding an additional argument:

<code>

python3 aas.py clean

</code>

Note that additional keys created by the program will have to be deleted/unlinked manually.

The first time the program is run you will see results like this:

<code>

Total time taken in seconds by redis operations: 0.00931716
Total time taken in seconds by non-redis operations: 1.080892801
TOTAL PROGRAM EXECUTION TIME (without user time) == 1.0902099609375

</code>

Then, the main key that lists the options will be in redis and you will see results like this:

<code>

Total time taken in seconds by redis operations: 0.006021738
Total time taken in seconds by non-redis operations: 0.30087924
TOTAL PROGRAM EXECUTION TIME (without user time) == 0.3069009780883789

</code>

If you then implement the caching of the individual ascii art payloads you will see results like this:

<code>

Total time taken in seconds by redis operations: 0.0131917
Total time taken in seconds by non-redis operations: 0.002849102
TOTAL PROGRAM EXECUTION TIME (without user time) == 0.016040802001953125

</code>