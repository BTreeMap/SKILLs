"""The network boundary: who a request is from, and how a response fails.

Nothing here knows which service is being called. A caller that does adds
its own parameters and its own reading of a status code.
"""
