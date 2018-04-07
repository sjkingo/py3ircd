from exc import InvalidModelineError

def modeline_parser(modeline, existing_set=None):
    """
    Parses a modeline into a set, optionally using the existing
    set given. Returns a new set() as result.
    """

    valid_ops = ('+', '-')
    if modeline[0] not in valid_ops:
        raise InvalidModelineError(modeline)

    current_op = None
    if existing_set is None:
        existing_set = set()
    modeset = existing_set

    for i in modeline:
        if i in valid_ops:
            current_op = i
            continue
        elif i.isalpha():
            if current_op == '+':
                modeset.add(i)
            elif current_op == '-':
                try:
                    modeset.remove(i)
                except KeyError:
                    pass
            continue

        raise InvalidModelineError(modeline)

    return modeset
