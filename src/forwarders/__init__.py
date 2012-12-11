"""
Forwarder classes form the middle layer between the outer HTTP object and the
internal layer processors. The HTTP parses enough of the request to know where
to forward it to, and send the nessesary data to the correct forwarder. The
forwarder does additional parsing, then invokes the layer with the correct
parameters, and returns the result to the HTTP handler.

The various

@author: Nathan
"""

import sign_direct
import json

layers = {'sign-direct': sign_direct}