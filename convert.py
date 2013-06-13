#!/usr/bin/python
import sys
import logging
import binascii

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

inp = sys.argv[1]
log.info("Working with input: %s", inp)

def str_to_dec(s):
	digits = [ord(d) for d in s]
	return digits

def str_to_hex(s):
	digits = [ord(d) for d in s]
	h = [hex(d) for d in digits]
	return ' '.join(h)
	

log.info("Result decimal %s", str_to_dec(inp))
log.info("Result hex %s", str_to_hex(inp))
