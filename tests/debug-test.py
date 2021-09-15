
import os
import sys
import asyncio

cur_dir_name = os.path.dirname(__file__)
parent_dir_path = os.path.dirname(cur_dir_name)
sys.path.append(parent_dir_path)

# import cryptofeed directly from local directory
repo_dir_path = os.path.dirname(parent_dir_path)
cryptofeed_dir_path = repo_dir_path + '/cryptofeed@loopyluffy'
sys.path.append(cryptofeed_dir_path)

# to import pyx file
import pyximport
pyximport.install()

# use UTC time zone @weaver
os.environ['TZ'] = 'UTC'

from cryptostore.bin import cryptostore

# test@logan
if __name__ == "__main__":

    # -- multiprocessing issue on linux/mac
   import multiprocessing
   multiprocessing.set_start_method('spawn', True)
    # --

   cryptostore.main()


# test normalizer batch @weaver
# from cryptostore.batch import normalizer

# if __name__ == "__main__":

#     host = 'https://search-mcs-staging-es-rqrrqce3bhqovwwknib2brm3la.ap-northeast-2.es.amazonaws.com'
#     index = 'weaver.test04-raw-live-bitmex-trades'
#     date = '2019-11-12'
#     feed = 'BITMEX'
#     ch = 'trades'
#     book_depth = 25
#     prefix = 'weaver.test04-'
#     force = True

#     async def run():
#         await normalizer.run(host=host,index=index, date=date, feed=feed, ch=ch, book_depth=book_depth, prefix=prefix, force=force)
    
#     asyncio.run(run())


