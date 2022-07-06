import logging

from .base import ParseError

logger = logging.getLogger(__name__)
escapableCharList = '\\;,Nn"'


def stringToTextValues(s, listSeparator=',', charList=None, strict=False):
    """Returns list of strings."""
    if charList is None:
        charList = escapableCharList

    def escapableChar(c):
        return c in charList

    def error(msg):
        if strict:
            raise ParseError(msg)
        else:
            logger.error(msg)

    # vars which control state machine
    charIterator = enumerate(s)
    state        = 'read normal'

    current = []
    results = []

    while True:
        try:
            charIndex, char = next(charIterator)
        except Exception:  # TODO: better exception...
            char = 'eof'

        if state == 'read normal':
            if char == '\\':
                state = 'read escaped char'
            elif char == listSeparator:
                state = 'read normal'
                current = ''.join(current)
                results.append(current)
                current = []
            elif char == 'eof':
                state = 'end'
            else:
                state = 'read normal'
                current.append(char)

        elif state == 'read escaped char':
            if escapableChar(char):
                state = 'read normal'
                if char in 'nN':
                    current.append('\n')
                else:
                    current.append(char)
            else:
                state = 'read normal'
                # leave unrecognized escaped characters for later passes
                current.append('\\' + char)

        elif state == 'end':  # an end state
            if len(current) or len(results) == 0:
                current = ''.join(current)
                results.append(current)
            return results

        elif state == 'error':  # an end state
            return results

        else:
            state = 'error'
            error(f"error: unknown state: '{state}' reached in {s}")
