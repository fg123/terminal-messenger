import client
import logging

logging.basicConfig(
    filename='messenger.log', level=logging.CRITICAL, filemode='w')

client.Client()
